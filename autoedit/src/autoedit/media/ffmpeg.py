"""Run ffmpeg with progress reporting, and concatenate rendered pieces losslessly."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path


class FFmpegError(RuntimeError):
    pass


def run_ffmpeg(args: Sequence[str], *, total_duration: float | None = None,
               on_progress: Callable[[float], None] | None = None,
               cwd: Path | None = None) -> None:
    """Run `ffmpeg -y <args>`; stream progress; raise FFmpegError with the stderr tail on failure."""
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "error"]
    if on_progress is not None:
        cmd += ["-progress", "pipe:1", "-nostats"]
    cmd += list(args)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd)
    assert proc.stdout is not None
    if on_progress is not None and total_duration:
        for line in proc.stdout:
            if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
                try:
                    us = int(line.split("=", 1)[1])
                    on_progress(min(1.0, us / 1e6 / total_duration))
                except ValueError:
                    pass
    _, err = proc.communicate()
    if proc.returncode != 0:
        tail = "\n".join(err.strip().splitlines()[-15:])
        raise FFmpegError(f"ffmpeg failed ({proc.returncode}): {' '.join(cmd)}\n{tail}")


def concat_copy(files: Sequence[Path], out: Path) -> None:
    """Concatenate identically encoded files with the concat demuxer (no re-encode)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    lst = out.with_suffix(out.suffix + ".list.txt")
    lst.write_text("".join(f"file '{os.path.abspath(f)}'\n" for f in files))
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])


def extract_frame(video: Path, t: float, out: Path, *, height: int | None = None) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    vf = f"scale=-2:{height}" if height else "null"
    run_ffmpeg(["-ss", f"{max(0.0, t):.3f}", "-i", str(video), "-frames:v", "1", "-vf", vf, str(out)])
    return out


def video_encode_args(crf: int = 18, preset: str = "fast") -> list[str]:
    return ["-c:v", "libx264", "-crf", str(crf), "-preset", preset, "-pix_fmt", "yuv420p"]


def pcm_audio_args() -> list[str]:
    """Intermediate pieces carry PCM so durations are exact and concat has no encoder delay."""
    return ["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]
