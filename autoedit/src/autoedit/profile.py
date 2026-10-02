"""Channel profiles (YAML): experience type, fonts, colors, captions, cards, audio, end screen,
thumbnail and Shorts settings. Built-ins live in autoedit/profiles/."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from .paths import BUILTIN_PROFILES_DIR

Experience = Literal["hangout", "informative", "entertainment"]

# cut_silence.py presets by viewer experience; punch defaults to off as in the script
DEAD_AIR_PRESETS: dict[str, dict[str, float]] = {
    "hangout": {"min_silence": 1.5, "pad": 0.35, "punch": 1.0, "min_keep": 0.6},
    "informative": {"min_silence": 0.5, "pad": 0.15, "punch": 1.0, "min_keep": 0.6},
    "entertainment": {"min_silence": 0.25, "pad": 0.08, "punch": 1.12, "min_keep": 0.6},
}

# measured benchmarks from the style guide, adjusted per experience
PACING_BENCHMARKS: dict[str, dict[str, float | None]] = {
    "hangout": {"changes_per_min": 0.5, "changes_per_min_first60": 1.0, "avg_shot_max_s": 90.0, "silent_gaps_max": None},
    "informative": {"changes_per_min": 5.5, "changes_per_min_first60": 7.0, "avg_shot_max_s": 11.0, "silent_gaps_max": 3},
    "entertainment": {"changes_per_min": 12.0, "changes_per_min_first60": 20.0, "avg_shot_max_s": 5.0, "silent_gaps_max": 0},
}


class FontsCfg(BaseModel):
    primary: str | None = None       # path to a TTF (bold preferred); DejaVu Sans Bold when missing
    secondary: str | None = None


class ColorsCfg(BaseModel):
    bg: str = "#141414"
    text: str = "#FFFFFF"
    accent: str = "#3CC8FF"
    muted: str = "#9AA0A6"


class CaptionsCfg(BaseModel):
    style: Literal["keyword", "kinetic"] = "keyword"
    max_words: int = 3
    size_px: int = 64
    position: Literal["lower", "upper", "middle"] = "lower"
    accent_words: bool = True
    outline_px: float = 2.0
    fade_ms: int = 150
    margin_v_px: int = 120


class CardsCfg(BaseModel):
    style: Literal["dark-textured", "flat"] = "dark-textured"
    glow: bool = True
    duration: float = 2.5
    size_px: int = 96
    subtitle_size_px: int = 48
    noise: int = 12


class DeadAirCfg(BaseModel):
    min_silence: float | None = None
    pad: float | None = None
    punch: float | None = None
    min_keep: float | None = None


class AudioCfg(BaseModel):
    music_dir: str | None = None
    sfx_dir: str | None = None
    music_rel_db: float = -10.0
    duck_ratio: float = 8.0
    lufs: float = -14.0
    true_peak: float = -1.5
    voice_clean: Literal["auto", "on", "off"] = "auto"
    fadeout_s: float = 20.0


class EndScreenCfg(BaseModel):
    seconds: float = 15.0
    reserve_zone: Literal["right-third", "none"] = "right-third"
    plate: bool = True
    text: str = "Watch this next"


class ThumbnailCfg(BaseModel):
    style: Literal["face-plus-text", "text-only", "asset"] = "face-plus-text"
    text_max_words: int = 3
    mood_color: Literal["warm", "cool", "neutral"] = "warm"
    text_size_px: int = 140


class ShortsCfg(BaseModel):
    count: int = 4
    min_s: float = 15.0
    max_s: float = 60.0
    context_label: str | None = None
    caption_style: Literal["word-by-word"] = "word-by-word"
    caption_size_px: int = 72
    loop_pad_s: float = 0.25


class ChatCfg(BaseModel):
    """chat-skit look (Discord-style)."""
    chat_bg: str = "#313338"
    panel_bg: str = "#2B2D31"
    text: str = "#DBDEE1"
    name_default: str = "#F2F3F5"
    timestamp: str = "#949BA4"
    highlight: str = "#5865F2"
    card_bg: str = "#3A3C41"
    card_text: str = "#DBDEE1"
    message_size_px: int = 44
    name_size_px: int = 40
    card_size_px: int = 84
    avatar_px: int = 88
    typing_dots_s: float = 1.2
    highlight_fade_s: float = 1.5
    punch_scale: float = 1.18
    assets_dir: str | None = None


class Profile(BaseModel):
    name: str
    format: Literal["talking-head", "chat-skit"] = "talking-head"
    experience: Experience = "informative"
    handle: str | None = None
    voice_notes: str | None = None            # how the creator talks; used for voiceover lines
    fonts: FontsCfg = FontsCfg()
    colors: ColorsCfg = ColorsCfg()
    captions: CaptionsCfg = CaptionsCfg()
    cards: CardsCfg = CardsCfg()
    dead_air: DeadAirCfg = DeadAirCfg()
    audio: AudioCfg = AudioCfg()
    end_screen: EndScreenCfg = EndScreenCfg()
    thumbnail: ThumbnailCfg = ThumbnailCfg()
    shorts: ShortsCfg = ShortsCfg()
    chat: ChatCfg = ChatCfg()
    source_file: str | None = None

    def dead_air_params(self) -> dict[str, float]:
        p = dict(DEAD_AIR_PRESETS[self.experience])
        for k, v in self.dead_air.model_dump().items():
            if v is not None:
                p[k] = v
        return p

    def benchmarks(self) -> dict[str, float | None]:
        return dict(PACING_BENCHMARKS[self.experience])

    def resolve_path(self, p: str | None) -> Path | None:
        if not p:
            return None
        q = Path(p).expanduser()
        if not q.is_absolute() and self.source_file:
            q = Path(self.source_file).parent / q
        return q


def load_profile(name_or_path: str | Path, profiles_dir: Path | None = None) -> Profile:
    p = Path(name_or_path)
    cands = [p] if p.suffix in (".yaml", ".yml") else []
    for d in [profiles_dir, Path.cwd() / "profiles", BUILTIN_PROFILES_DIR]:
        if d:
            cands += [Path(d) / f"{name_or_path}.yaml", Path(d) / f"{name_or_path}.yml"]
    for c in cands:
        if c.exists():
            data = yaml.safe_load(c.read_text()) or {}
            data.setdefault("name", c.stem)
            data["source_file"] = str(c.resolve())
            return Profile.model_validate(data)
    raise FileNotFoundError(f"profile not found: {name_or_path} (looked in {[str(c) for c in cands]})")
