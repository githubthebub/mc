"""Watch a folder: every new video (or chat-skit script) whose size has been stable for 30 s becomes a
project and a queued `run` job."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from ..config import load_settings
from ..profile import load_profile
from ..project import Project, slugify
from .queue import JobQueue

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".m4v", ".webm", ".avi", ".mts"}
SCRIPT_EXT = {".yaml", ".yml"}
STABLE_S = 30.0


def _registry(watch_dir: Path) -> Path:
    return watch_dir / ".autoedit_seen.json"


def scan_once(watch_dir: Path, profile_name: str, fmt: str | None, queue: JobQueue, projects_dir: Path, *,
              yolo: bool, sizes: dict[str, tuple[int, float]], llm: str = "auto") -> list[str]:
    """Register files that are complete and unseen. `sizes` tracks size and the time it was first seen stable."""
    reg_path = _registry(watch_dir)
    seen: dict[str, str] = json.loads(reg_path.read_text()) if reg_path.exists() else {}
    registered: list[str] = []
    now = time.time()
    for f in sorted(watch_dir.iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue
        ext = f.suffix.lower()
        if ext not in VIDEO_EXT | SCRIPT_EXT:
            continue
        key = f.name
        if key in seen:
            continue
        size = f.stat().st_size
        prev = sizes.get(key)
        if prev is None or prev[0] != size:
            sizes[key] = (size, now)
            continue
        if now - prev[1] < STABLE_S:
            continue
        profile = load_profile(profile_name)
        use_fmt = fmt or profile.format
        name = f.stem
        slug = slugify(name)
        if (projects_dir / slug / "project.yaml").exists():
            slug = slugify(f"{name}-{int(now)}")
            name = f"{name} {int(now)}"
        opts = {"script": str(f.resolve())} if ext in SCRIPT_EXT else {}
        p = Project.create(projects_dir, name, None if ext in SCRIPT_EXT else f, profile_name, use_fmt, options=opts)
        job = queue.add(str(p.root), "run", {"yolo": yolo, "llm": llm})
        seen[key] = str(p.root)
        reg_path.write_text(json.dumps(seen, indent=1))
        registered.append(f"{f.name} -> {p.root} (job {job.id})")
    return registered


def watch(watch_dir: Path, profile_name: str, fmt: str | None, *, yolo: bool = False, once: bool = False,
          interval: float = 10.0, llm: str = "auto") -> int:
    settings = load_settings()
    watch_dir = Path(watch_dir).expanduser().resolve()
    if not watch_dir.is_dir():
        print(f"not a directory: {watch_dir}", file=sys.stderr)
        return 2
    queue = JobQueue(settings.projects_dir / "queue.db")
    sizes: dict[str, tuple[int, float]] = {}
    print(f"watching {watch_dir} (profile {profile_name}, {'yolo' if yolo else 'review gate'}); start `autoedit worker --daemon` to process jobs")
    passes = 0
    while True:
        try:
            for line in scan_once(watch_dir, profile_name, fmt, queue, settings.projects_dir, yolo=yolo, sizes=sizes, llm=llm):
                print(f"registered {line}")
        except Exception as e:  # noqa: BLE001
            print(f"scan error: {e!r}", file=sys.stderr)
        passes += 1
        if once:
            # a file must be seen twice with the same size, STABLE_S apart, before it counts as complete
            if passes == 1 and sizes:
                time.sleep(STABLE_S + 1)
                continue
            return 0
        time.sleep(interval)
