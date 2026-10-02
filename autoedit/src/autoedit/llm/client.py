"""Claude client for the planner.

- model from config, API key from ANTHROPIC_API_KEY (the SDK reads it)
- the skill references are sent as cached system blocks
- structured outputs via messages.parse with a Pydantic schema
- every request and response is saved under the project's llm/ folder; `replay` reads them back,
  which is how the golden test runs offline
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from ..config import Settings
from ..log import StageLog
from ..paths import find_skill_dir

T = TypeVar("T", bound=BaseModel)

REFERENCE_FILES = ("style-guide.md", "story-and-retention.md", "packaging.md")


class LLMUnavailable(RuntimeError):
    pass


class LLMRefused(RuntimeError):
    pass


def load_prompt(name: str) -> str:
    return (Path(__file__).parent / "prompts" / f"{name}.md").read_text()


def reference_blocks(skill_dir: Path | None) -> list[str]:
    if skill_dir is None:
        return []
    out = []
    for name in REFERENCE_FILES:
        f = skill_dir / "references" / name
        if f.exists():
            out.append(f"<reference name=\"{name}\">\n{f.read_text()}\n</reference>")
    return out


class LLM:
    def __init__(self, settings: Settings, log_dir: Path, mode: str = "auto", log: StageLog | None = None):
        self.settings = settings
        self.mode = mode
        self.dir = log_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.log = log
        self.skill_dir = find_skill_dir(settings.skill_dir)
        self._client = None
        self._n = 0

    @property
    def available(self) -> bool:
        return self.mode == "replay" or bool(os.environ.get("ANTHROPIC_API_KEY"))

    def _client_or_raise(self):
        if self._client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise LLMUnavailable("ANTHROPIC_API_KEY is not set")
            import anthropic
            self._client = anthropic.Anthropic(timeout=self.settings.llm.timeout_s, max_retries=3)
        return self._client

    def system_blocks(self) -> list[dict]:
        blocks = [{"type": "text", "text": load_prompt("system")}]
        for ref in reference_blocks(self.skill_dir):
            blocks.append({"type": "text", "text": ref})
        if self.settings.llm.cache_references:
            blocks[-1]["cache_control"] = {"type": "ephemeral"}
        return blocks

    def call(self, name: str, user: str, schema: type[T], max_tokens: int | None = None) -> T:
        self._n += 1
        stem = f"{self._n:02d}_{name}"
        req_path = self.dir / f"{stem}.request.json"
        resp_path = self.dir / f"{stem}.response.json"
        if self.mode == "replay":
            cands = [resp_path, *sorted(self.dir.glob(f"*_{name}.response.json"))]
            for c in cands:
                if c.exists():
                    data = json.loads(c.read_text())
                    if self.log:
                        self.log.info("replaying llm response", name=name, path=str(c))
                    return schema.model_validate(data["parsed"])
            raise LLMUnavailable(f"replay requested but no saved response for {name} in {self.dir}")
        client = self._client_or_raise()
        system = self.system_blocks()
        req = {"model": self.settings.llm.model, "max_tokens": max_tokens or self.settings.llm.max_tokens,
               "system": system, "messages": [{"role": "user", "content": user}],
               "output_format": schema.__name__}
        req_path.write_text(json.dumps(req, indent=1))
        t0 = time.time()
        if self.log:
            self.log.info("calling claude", name=name, model=self.settings.llm.model, user_chars=len(user))
        resp = client.messages.parse(
            model=self.settings.llm.model,
            max_tokens=max_tokens or self.settings.llm.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema,
        )
        if resp.stop_reason == "refusal":
            details = getattr(resp, "stop_details", None)
            raise LLMRefused(f"the model declined this request ({details})")
        if resp.stop_reason == "max_tokens":
            raise RuntimeError(f"{name}: output truncated at max_tokens; raise llm.max_tokens")
        parsed = resp.parsed_output
        if parsed is None:
            raise RuntimeError(f"{name}: no parsed output (stop_reason={resp.stop_reason})")
        usage = getattr(resp, "usage", None)
        meta = {"model": resp.model, "stop_reason": resp.stop_reason, "elapsed_s": round(time.time() - t0, 1),
                "usage": {k: getattr(usage, k, None) for k in ("input_tokens", "output_tokens",
                                                                 "cache_read_input_tokens", "cache_creation_input_tokens")} if usage else None}
        resp_path.write_text(json.dumps({"meta": meta, "parsed": parsed.model_dump(mode="json")}, indent=1))
        if self.log:
            self.log.info("claude replied", name=name, **{k: v for k, v in (meta["usage"] or {}).items() if v is not None},
                          elapsed_s=meta["elapsed_s"])
        return parsed
