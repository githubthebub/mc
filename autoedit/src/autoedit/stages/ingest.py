"""Ingest: probe the source, link it, build a proxy, extract audio, make a contact sheet."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from ..config import Settings
from ..log import StageLog
from ..media.ffmpeg import run_ffmpeg
from ..media.probe import MediaInfo, probe
from ..project import Project, file_hash


def _link(src: Path, dst: Path) -> None:
    if dst.is_symlink() or dst.exists():
        dst.unlink()
    try:
        os.symlink(src, dst)
    except OSError:
        import shutil
        shutil.copy2(src, dst)


def run(project: Project, settings: Settings, log: StageLog | None = None) -> MediaInfo:
    log = log or project.log("ingest")
    from ..formats import get_format
    from ..profile import load_profile
    fmt = get_format(project.format)
    src = project.source
    composed = None
    project.begin("ingest", file_hash(src) if src and src.exists() else None)
    try:
        if src is None or not src.exists():
            profile = load_profile(project.profile_name, settings.profiles_dir)
            composed = fmt.compose(project, settings, profile, log)
            if composed is None:
                raise FileNotFoundError(f"project has no source media: {src}")
            src = composed
        info = probe(src)
        if not info.has_audio:
            raise RuntimeError("source has no audio stream; a talking-head edit needs the voice")
        if info.width == 0:
            raise RuntimeError("source has no video stream")
        log.info("probed", duration=round(info.duration, 2), size=f"{info.width}x{info.height}", fps=info.fps_str)
        d = project.dir("ingest")
        if composed is None:
            _link(src, project.ingest_source)
        # proxy for analysis and preview
        ph = min(settings.render.proxy_height, info.height)
        log.info("proxy", height=ph)
        run_ffmpeg(["-i", str(src), "-vf", f"scale=-2:{ph}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-ac", "2", "-ar", "48000", str(project.proxy)],
                   total_duration=info.duration, on_progress=lambda f: log.progress(0.1 + 0.6 * f, "proxy"))
        run_ffmpeg(["-i", str(src), "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(project.audio_wav)],
                   total_duration=info.duration, on_progress=lambda f: log.progress(0.7 + 0.2 * f, "audio"))
        sheet = d / "contact_sheet.png"
        run_ffmpeg(["-i", str(project.proxy), "-vf", f"fps={24 / max(1.0, info.duration)},scale=320:-2,tile=6x4",
                    "-frames:v", "1", str(sheet)])
        pj = {k: (str(v) if isinstance(v, Path) else v) for k, v in asdict(info).items()}
        pj["fps"] = info.fps_str
        pj["source_hash"] = file_hash(src)
        project.probe_json.write_text(json.dumps(pj, indent=1))
        project.finish("ingest", duration=info.duration, width=info.width, height=info.height, fps=info.fps_str)
        log.done()
        return info
    except Exception as e:
        project.fail("ingest", repr(e))
        log.error("failed", error=repr(e))
        raise


def load_probe(project: Project) -> MediaInfo:
    """The probe of the ingested source (re-probed if probe.json is missing)."""
    return probe(project.ingest_source)
