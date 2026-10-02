"""Well-known locations: the installed package, the autoedit project root, the repo root."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent          # .../autoedit/src/autoedit
AUTOEDIT_ROOT = PACKAGE_DIR.parents[1]                 # .../autoedit
REPO_ROOT = AUTOEDIT_ROOT.parent                       # repository root
BUILTIN_PROFILES_DIR = AUTOEDIT_ROOT / "profiles"
DEFAULT_MODELS_DIR = Path(os.environ.get("AUTOEDIT_MODELS_DIR", "~/.cache/autoedit/models")).expanduser()


def find_skill_dir(explicit: Path | None = None) -> Path | None:
    """Locate the video-editor skill (SKILL.md plus references/).

    Order: the explicit path, the repo copy at .claude/skills/video-editor,
    then any synced copy under ~/.claude/skills.
    """
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit).expanduser())
    candidates.append(REPO_ROOT / ".claude" / "skills" / "video-editor")
    home_skills = Path("~/.claude/skills").expanduser()
    if home_skills.exists():
        candidates.extend(sorted(home_skills.glob("**/video-editor")))
    for c in candidates:
        if (c / "SKILL.md").exists() and (c / "references").is_dir():
            return c
    return None
