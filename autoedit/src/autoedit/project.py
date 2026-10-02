"""A project folder: one video, every stage's artifacts, and state.json."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any

import yaml

from .log import StageLog

STAGES = ("ingest", "transcribe", "analyze", "plan", "render", "shorts", "package", "verify")
STAGE_DIRS = {"ingest": "01_ingest", "transcribe": "02_transcribe", "analyze": "03_analyze", "plan": "04_plan",
              "render": "05_render", "shorts": "05_render/shorts", "verify": "06_verify", "package": "07_package"}


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "project"


def file_hash(path: Path, quick: bool = True) -> str:
    """Hash of a file: content for small files, size+mtime+head for big media (quick)."""
    p = Path(path)
    h = hashlib.sha256()
    st = p.stat()
    if quick and st.st_size > 50_000_000:
        h.update(f"{st.st_size}:{int(st.st_mtime)}".encode())
        with p.open("rb") as f:
            h.update(f.read(1_000_000))
    else:
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()[:16]


class Project:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.cfg: dict[str, Any] = yaml.safe_load((self.root / "project.yaml").read_text()) or {}
        sp = self.root / "state.json"
        self.state: dict[str, Any] = json.loads(sp.read_text()) if sp.exists() else {"stages": {}, "approved": False}

    # ---- lifecycle ----
    @classmethod
    def create(cls, projects_dir: Path, name: str, source: Path | None, profile: str, fmt: str,
               copy_source: bool = False, options: dict[str, Any] | None = None) -> "Project":
        root = Path(projects_dir) / slugify(name)
        if root.exists() and (root / "project.yaml").exists():
            raise FileExistsError(f"project exists: {root}")
        root.mkdir(parents=True, exist_ok=True)
        (root / "logs").mkdir(exist_ok=True)
        (root / "assets").mkdir(exist_ok=True)
        src_entry: str | None = None
        if source is not None:
            source = Path(source).expanduser().resolve()
            if not source.exists():
                raise FileNotFoundError(source)
            if copy_source:
                dst = root / "assets" / source.name
                shutil.copy2(source, dst)
                src_entry = str(dst.relative_to(root))
            else:
                src_entry = str(source)
        cfg = {"name": name, "slug": root.name, "source": src_entry, "profile": profile, "format": fmt,
               "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "options": options or {}}
        (root / "project.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
        (root / "state.json").write_text(json.dumps({"stages": {}, "approved": False}, indent=1))
        return cls(root)

    @classmethod
    def open(cls, path: Path) -> "Project":
        p = Path(path)
        if not (p / "project.yaml").exists():
            raise FileNotFoundError(f"not a project folder: {p}")
        return cls(p)

    def save_state(self) -> None:
        (self.root / "state.json").write_text(json.dumps(self.state, indent=1, default=str))

    # ---- paths ----
    @property
    def name(self) -> str:
        return str(self.cfg.get("name", self.root.name))

    @property
    def profile_name(self) -> str:
        return str(self.cfg["profile"])

    @property
    def format(self) -> str:
        return str(self.cfg.get("format", "talking-head"))

    @property
    def options(self) -> dict[str, Any]:
        return dict(self.cfg.get("options") or {})

    @property
    def source(self) -> Path | None:
        s = self.cfg.get("source")
        if not s:
            return None
        p = Path(s)
        return p if p.is_absolute() else self.root / p

    def dir(self, stage: str) -> Path:
        d = self.root / STAGE_DIRS[stage]
        d.mkdir(parents=True, exist_ok=True)
        return d

    def log(self, stage: str, quiet: bool = False) -> StageLog:
        return StageLog(stage, self.root / "logs", quiet=quiet)

    # well-known artifacts
    @property
    def ingest_source(self) -> Path:
        return self.dir("ingest") / "source.mp4"

    @property
    def proxy(self) -> Path:
        return self.dir("ingest") / "proxy.mp4"

    @property
    def audio_wav(self) -> Path:
        return self.dir("ingest") / "audio.wav"

    @property
    def probe_json(self) -> Path:
        return self.dir("ingest") / "probe.json"

    @property
    def transcript_json(self) -> Path:
        return self.dir("transcribe") / "transcript.json"

    @property
    def analysis_json(self) -> Path:
        return self.dir("analyze") / "analysis.json"

    @property
    def face_track_json(self) -> Path:
        return self.dir("analyze") / "face_track.json"

    @property
    def edl_json(self) -> Path:
        return self.dir("plan") / "edl.json"

    @property
    def final_mp4(self) -> Path:
        return self.dir("render") / "final.mp4"

    @property
    def qa_json(self) -> Path:
        return self.dir("verify") / "qa_report.json"

    # ---- stage state ----
    def stage_state(self, stage: str) -> dict[str, Any]:
        return dict(self.state["stages"].get(stage, {}))

    def is_done(self, stage: str) -> bool:
        return self.stage_state(stage).get("status") == "done"

    def begin(self, stage: str, inputs_hash: str | None = None) -> None:
        self.state["stages"][stage] = {"status": "running", "started": time.time(), "inputs_hash": inputs_hash}
        self.save_state()

    def finish(self, stage: str, **info: Any) -> None:
        st = self.state["stages"].setdefault(stage, {})
        st.update({"status": "done", "finished": time.time(), **info})
        # a later stage is stale once an earlier one re-ran
        for later in STAGES[STAGES.index(stage) + 1:]:
            if later in self.state["stages"] and self.state["stages"][later].get("status") == "done":
                self.state["stages"][later]["status"] = "stale"
        if stage in ("plan",):
            self.state["approved"] = False
        self.save_state()

    def fail(self, stage: str, error: str) -> None:
        st = self.state["stages"].setdefault(stage, {})
        st.update({"status": "failed", "finished": time.time(), "error": error[-2000:]})
        self.save_state()

    def approve(self) -> None:
        self.state["approved"] = True
        self.state["approved_at"] = time.time()
        self.state["approved_edl_hash"] = file_hash(self.edl_json) if self.edl_json.exists() else None
        self.save_state()

    @property
    def approved(self) -> bool:
        return bool(self.state.get("approved"))

    def edl_was_hand_edited(self) -> bool:
        """True when edl.json differs from what the plan stage wrote."""
        st = self.stage_state("plan")
        h = st.get("edl_hash")
        return bool(h and self.edl_json.exists() and file_hash(self.edl_json) != h)

    def summary(self) -> dict[str, Any]:
        return {"name": self.name, "root": str(self.root), "profile": self.profile_name, "format": self.format,
                "approved": self.approved,
                "stages": {s: self.stage_state(s).get("status", "pending") for s in STAGES}}
