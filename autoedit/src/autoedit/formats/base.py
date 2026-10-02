"""The Format protocol. Add a format by implementing these hooks and registering it in get_format()."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from ..config import Settings
from ..log import StageLog
from ..profile import Profile
from ..project import Project


class Format(Protocol):
    name: str
    dead_air: bool              # remove empty pauses from the source (talking head) or keep every frame (scripted)
    captions: bool              # key-word captions make sense (not when the words are already on screen)
    planner_notes: str          # what the planner must know about this format

    def compose(self, project: Project, settings: Settings, profile: Profile, log: StageLog) -> Path | None:
        """Build the source video from the input when the format is not footage. Return its path, or None
        when the project's source file is used as is."""
        ...

    def transcript_file(self, project: Project) -> Path | None:
        """A transcript the format produced itself (no ASR needed), or None."""
        ...

    def focus_track_file(self, project: Project) -> Path | None:
        """A focus track (what punch-ins and crops anchor to) the format produced itself, or None to detect faces."""
        ...

    def extras(self, project: Project) -> dict[str, Any]:
        """EDL items the format itself asks for (sfx, zooms, music mood), merged by the planner."""
        ...
