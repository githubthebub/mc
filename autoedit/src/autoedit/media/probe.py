"""ffprobe wrapper."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    duration: float
    width: int
    height: int
    fps: Fraction
    has_audio: bool
    sample_rate: int
    nb_frames: int | None
    video_codec: str | None
    pix_fmt: str | None

    @property
    def fps_str(self) -> str:
        return f"{self.fps.numerator}/{self.fps.denominator}"

    @property
    def fps_float(self) -> float:
        return float(self.fps)


def _run_ffprobe(args: list[str]) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", *args],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def probe(path: str | Path) -> MediaInfo:
    """Probe a media file. Raises FileNotFoundError or subprocess.CalledProcessError."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    data = _run_ffprobe(["-show_format", "-show_streams", str(p)])
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})
    duration = float(fmt.get("duration") or (v or {}).get("duration") or (a or {}).get("duration") or 0.0)
    fps = Fraction(30, 1)
    width = height = 0
    nb_frames = None
    codec = pix_fmt = None
    if v:
        r = v.get("avg_frame_rate") or v.get("r_frame_rate") or "30/1"
        if r and r != "0/0":
            fps = Fraction(r)
        width, height = int(v.get("width", 0)), int(v.get("height", 0))
        if v.get("nb_frames", "").isdigit():
            nb_frames = int(v["nb_frames"])
        codec, pix_fmt = v.get("codec_name"), v.get("pix_fmt")
    sr = int(a.get("sample_rate", 0)) if a else 0
    return MediaInfo(p, duration, width, height, fps, a is not None, sr, nb_frames, codec, pix_fmt)


def count_video_frames(path: str | Path) -> int:
    """Exact frame count by counting packets (fast for intra-only or short files)."""
    data = _run_ffprobe(["-select_streams", "v:0", "-count_packets",
                         "-show_entries", "stream=nb_read_packets", str(path)])
    return int(data["streams"][0]["nb_read_packets"])


def duration_of(path: str | Path) -> float:
    return probe(path).duration
