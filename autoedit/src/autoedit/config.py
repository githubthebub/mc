"""Global configuration: an optional autoedit.yaml plus AUTOEDIT_* environment variables."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .paths import DEFAULT_MODELS_DIR, REPO_ROOT


class LLMConfig(BaseModel):
    model: str = "claude-opus-5-5"
    max_tokens: int = 16000
    effort: str = "high"
    cache_references: bool = True
    timeout_s: float = 600.0


class WhisperConfig(BaseModel):
    model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str | None = None
    beam_size: int = 5
    vad: bool = True


class RenderConfig(BaseModel):
    workers: int = Field(default_factory=lambda: max(1, (os.cpu_count() or 2) - 1))
    crf: int = 18
    preset: str = "fast"
    preview_height: int = 360
    preview_preset: str = "ultrafast"
    proxy_height: int = 480
    face_sample_fps: float = 10.0


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTOEDIT_", env_nested_delimiter="__", extra="ignore")

    projects_dir: Path = REPO_ROOT / "projects"
    skill_dir: Path | None = None
    profiles_dir: Path | None = None
    models_dir: Path = DEFAULT_MODELS_DIR
    llm: LLMConfig = LLMConfig()
    whisper: WhisperConfig = WhisperConfig()
    render: RenderConfig = RenderConfig()


def _find_config_file() -> Path | None:
    env = os.environ.get("AUTOEDIT_CONFIG")
    if env:
        return Path(env).expanduser()
    for d in [Path.cwd(), *Path.cwd().parents]:
        f = d / "autoedit.yaml"
        if f.exists():
            return f
    f = REPO_ROOT / "autoedit.yaml"
    return f if f.exists() else None


def load_settings(config_file: Path | None = None) -> Settings:
    """Merge: defaults < autoedit.yaml < AUTOEDIT_* environment variables."""
    f = config_file or _find_config_file()
    data: dict[str, Any] = {}
    if f and f.exists():
        data = yaml.safe_load(f.read_text()) or {}
        base = f.parent
        for key in ("projects_dir", "skill_dir", "profiles_dir", "models_dir"):
            if key in data and data[key]:
                p = Path(str(data[key])).expanduser()
                data[key] = p if p.is_absolute() else (base / p)
    return Settings(**data)
