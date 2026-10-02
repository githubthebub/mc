"""EDL schema v1 (Pydantic). Times are source seconds unless a field says out_.

Anchors tie decisions to transcript words, sentences, segments, or raw times; the
render stage resolves them through the timing map. The LLM never writes raw
timestamps: it writes word and sentence ids."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .techniques import TECHNIQUES


class Anchor(BaseModel):
    """Exactly one of word, sentence, segment, src, out. `edge` picks the start or end of a word,
    sentence or segment. `pad` shifts the resolved time (seconds, positive = later)."""
    word: int | None = None
    sentence: int | None = None
    segment: str | None = None
    src: float | None = None
    out: float | None = None
    edge: Literal["start", "end"] = "start"
    pad: float = 0.0

    @model_validator(mode="after")
    def _one_of(self) -> "Anchor":
        n = sum(v is not None for v in (self.word, self.sentence, self.segment, self.src, self.out))
        if n != 1:
            raise ValueError("anchor needs exactly one of word, sentence, segment, src, out")
        return self

    def describe(self) -> str:
        for k in ("word", "sentence", "segment", "src", "out"):
            v = getattr(self, k)
            if v is not None:
                s = f"{k}={v}"
                if k in ("word", "sentence", "segment") and self.edge == "end":
                    s += ".end"
                if self.pad:
                    s += f"{self.pad:+.2f}"
                return s
        return "?"


class Punch(BaseModel):
    scale: float = 1.12
    anchor: Literal["face", "center", "top"] = "face"


class MontageSpec(BaseModel):
    target_s: float = 20.0
    chunk_s: float = 1.0
    speed: float = 1.5
    keep_audio_db: float | None = None


class Segment(BaseModel):
    id: str
    kind: Literal["aroll", "montage"] = "aroll"
    src_in: float
    src_out: float
    punch: Punch | None = None
    montage: MontageSpec | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _range(self) -> "Segment":
        if self.src_out <= self.src_in:
            raise ValueError(f"segment {self.id}: src_out must be > src_in")
        if self.kind == "montage" and self.montage is None:
            self.montage = MontageSpec()
        return self


class Zoom(BaseModel):
    id: str
    at: Anchor
    end: Anchor | None = None
    dur: float | None = None
    scale: float = 1.3
    anchor: Literal["face", "center", "top"] = "face"
    reason: str | None = None


class Beat(BaseModel):
    """'Shut up and show it': the picture holds for dur after the anchor."""
    id: str
    after: Anchor
    dur: float = 1.0
    fill: Literal["none", "caption", "still", "broll"] = "none"
    text: str | None = None
    asset: str | None = None
    sfx: str | None = None
    reason: str | None = None


class Caption(BaseModel):
    id: str
    at: Anchor
    end: Anchor | None = None
    dur: float | None = None
    words: list[str] = Field(min_length=1, max_length=3)
    emphasis: int | None = None       # index of the accent-colored word
    style: Literal["keyword", "kinetic", "label"] = "keyword"
    reason: str | None = None


class Card(BaseModel):
    id: str
    before_segment: str
    text: str
    subtitle: str | None = None
    number: int | None = None
    dur: float = 2.5
    style: Literal["chapter", "title", "quote"] = "chapter"
    sfx: str | None = "shutter"


class Overlay(BaseModel):
    id: str
    at: Anchor
    dur: float = 4.0
    asset: str
    kind: Literal["still", "broll"] = "still"
    focus: tuple[float, float, float, float] | None = None
    tint: Literal["red", "green", "yellow"] | None = None
    mark: Literal["box", "underline"] | None = None
    glow: bool = False
    motion: Literal["slide_right", "slide_left", "pop", "cut"] = "slide_right"
    sfx: str | None = "whoosh"
    reason: str | None = None


class VoiceoverSlot(BaseModel):
    id: str
    at: Anchor
    line: str
    reason: str
    file: str | None = None
    hold: float | None = None


class MusicSection(BaseModel):
    id: str
    start: Anchor
    end: Anchor
    mood: str
    file: str | None = None
    rel_db: float = -10.0
    pickup_at: Anchor | None = None
    pickup_song_time: float | None = None
    reason: str | None = None


class Dropout(BaseModel):
    id: str
    start: Anchor
    end: Anchor
    reason: str | None = None


class Fadeout(BaseModel):
    id: str
    start: Anchor
    end: Anchor
    reason: str | None = None


class Swell(BaseModel):
    id: str
    start: Anchor
    end: Anchor
    db: float = 6.0
    reason: str | None = None


class Sfx(BaseModel):
    id: str
    at: Anchor
    kind: str | None = None          # whoosh, pop, riser, hit, shutter, click, or a library name
    file: str | None = None
    gain_db: float = 0.0
    align: Literal["start", "end"] = "start"   # risers end ON the moment
    reason: str | None = None


class Chapter(BaseModel):
    title: str
    at: Anchor


class TitleSpec(BaseModel):
    chosen: str
    alternatives: list[str] = Field(default_factory=list)
    rationale: str | None = None


class ThumbnailSpec(BaseModel):
    spotlight: Literal["face", "text", "object"] = "face"
    text: str | None = None
    mood_color: Literal["warm", "cool", "neutral"] = "warm"
    idea: str | None = None
    frame_src_t: float | None = None
    asset: str | None = None


class ShortSpec(BaseModel):
    id: str
    hook: Anchor
    start: Anchor
    end: Anchor
    context_label: str | None = None
    title: str | None = None
    score: float | None = None
    reason: str | None = None


class Technique(BaseModel):
    status: Literal["planned", "executed", "degraded", "not_executed"] = "planned"
    reason: str | None = None
    stage: str | None = None
    count: int | None = None


class StoryRow(BaseModel):
    time: str
    what_happens: str
    color: Literal["green", "purple", "none"] = "none"
    conflict: str = "none"
    mood: str = ""
    litmus_gaps: list[str] = Field(default_factory=list)
    action: str = "keep"


class Meta(BaseModel):
    project: str
    profile: str
    format: str
    source: str
    duration: float
    fps: str
    width: int
    height: int
    created_by: Literal["llm", "human", "code"] = "code"
    model: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    experience: str = "informative"


class EDL(BaseModel):
    version: int = 1
    meta: Meta
    story_pass: list[StoryRow] = Field(default_factory=list)
    segments: list[Segment] = Field(default_factory=list)
    zooms: list[Zoom] = Field(default_factory=list)
    beats: list[Beat] = Field(default_factory=list)
    captions: list[Caption] = Field(default_factory=list)
    cards: list[Card] = Field(default_factory=list)
    overlays: list[Overlay] = Field(default_factory=list)
    voiceover_slots: list[VoiceoverSlot] = Field(default_factory=list)
    music: list[MusicSection] = Field(default_factory=list)
    dropouts: list[Dropout] = Field(default_factory=list)
    fadeouts: list[Fadeout] = Field(default_factory=list)
    swells: list[Swell] = Field(default_factory=list)
    sfx: list[Sfx] = Field(default_factory=list)
    chapters: list[Chapter] = Field(default_factory=list)
    title: TitleSpec | None = None
    thumbnail: ThumbnailSpec | None = None
    shorts: list[ShortSpec] = Field(default_factory=list)
    techniques: dict[str, Technique] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)

    # ---- ledger helpers ----
    def ensure_ledger(self) -> None:
        for k in TECHNIQUES:
            self.techniques.setdefault(k, Technique())

    def mark(self, tid: str, status: str, reason: str | None = None, stage: str | None = None,
             count: int | None = None) -> None:
        if tid not in TECHNIQUES:
            raise KeyError(f"unknown technique {tid}")
        self.techniques[tid] = Technique(status=status, reason=reason, stage=stage, count=count)

    def segment(self, sid: str) -> Segment:
        for s in self.segments:
            if s.id == sid:
                return s
        raise KeyError(f"no segment {sid}")

    # ---- io ----
    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.model_dump(mode="json"), indent=1))
        return path

    @classmethod
    def load(cls, path: Path) -> "EDL":
        return cls.model_validate(json.loads(Path(path).read_text()))

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        return cls.model_json_schema()
