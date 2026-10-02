"""Structured logging: JSONL per stage in the project, human lines on stderr, progress files."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StageLog:
    stage: str
    log_dir: Path
    quiet: bool = False
    _t0: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.log_dir / f"{self.stage}.jsonl"
        self.progress_path = self.log_dir / f"{self.stage}.progress.json"

    def _write(self, level: str, msg: str, **data: Any) -> None:
        rec = {"ts": round(time.time(), 3), "stage": self.stage, "level": level, "msg": msg, **data}
        with self.path.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        if not self.quiet:
            extra = " ".join(f"{k}={v}" for k, v in data.items()) if data else ""
            print(f"[{self.stage}] {msg} {extra}".rstrip(), file=sys.stderr)

    def info(self, msg: str, **data: Any) -> None:
        self._write("info", msg, **data)

    def warn(self, msg: str, **data: Any) -> None:
        self._write("warn", msg, **data)

    def error(self, msg: str, **data: Any) -> None:
        self._write("error", msg, **data)

    def progress(self, frac: float, msg: str = "") -> None:
        rec = {"stage": self.stage, "frac": round(max(0.0, min(1.0, frac)), 4), "msg": msg,
               "elapsed_s": round(time.time() - self._t0, 1), "ts": round(time.time(), 3)}
        self.progress_path.write_text(json.dumps(rec))

    def done(self, **data: Any) -> None:
        self.progress(1.0, "done")
        self.info("done", elapsed_s=round(time.time() - self._t0, 1), **data)
