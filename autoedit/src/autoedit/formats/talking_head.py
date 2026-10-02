"""Talking head: raw camera footage with a voice. Everything is detected."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class TalkingHead:
    name = "talking-head"
    dead_air = True
    captions = True
    planner_notes = "Raw camera footage of one speaker. Pauses are measured; captions, zooms and music moves are yours."

    def compose(self, project, settings, profile, log) -> Path | None:
        return None

    def transcript_file(self, project) -> Path | None:
        return None

    def focus_track_file(self, project) -> Path | None:
        return None

    def extras(self, project) -> dict[str, Any]:
        return {}
