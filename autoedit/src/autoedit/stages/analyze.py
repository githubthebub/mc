"""Analyze: pauses against the noise floor, energy, sentence energy and peaks, scene cuts, the face track."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from ..config import Settings
from ..edl.transcript import Transcript
from ..log import StageLog
from ..media import faces
from ..media.audio import analyze_pauses
from ..media.probe import probe
from ..profile import Profile
from ..project import Project, file_hash

MIN_PAUSE_FOR_LIST = 0.25   # the smallest preset; the planner/cut list filter further


def scene_cuts(video: Path, thresh: float = 0.12) -> list[float]:
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf",
                          f"scale=160:-2,select='gt(scene,{thresh})',showinfo", "-an", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", err)]


def sentence_energies(levels_db: np.ndarray, win: float, tr: Transcript) -> dict[int, float]:
    out: dict[int, float] = {}
    for s in tr.sentences:
        i0, i1 = int(s.t0 / win), max(int(s.t0 / win) + 1, int(s.t1 / win))
        seg = levels_db[i0:i1]
        seg = seg[seg > -90]
        out[s.id] = round(float(np.mean(seg)), 1) if len(seg) else -90.0
    return out


def run(project: Project, settings: Settings, profile: Profile, log: StageLog | None = None) -> dict[str, Any]:
    log = log or project.log("analyze")
    project.begin("analyze", file_hash(project.audio_wav))
    try:
        info = probe(project.ingest_source)
        tr = Transcript.load(project.transcript_json) if project.transcript_json.exists() else None
        log.progress(0.05, "pauses")
        pa = analyze_pauses(project.audio_wav, min_silence=MIN_PAUSE_FOR_LIST)
        energy_1s = [round(x, 1) for x in pa.energy_curve(1.0)]
        sent_e = sentence_energies(pa.levels_db, pa.win, tr) if tr else {}
        peaks: list[int] = []
        if sent_e:
            med = float(np.median(list(sent_e.values())))
            peaks = [sid for sid, e in sorted(sent_e.items(), key=lambda kv: -kv[1]) if e >= med + 2.0][:8]
        log.info("pauses", noise_floor_db=round(pa.noise_floor_db, 1), threshold_db=round(pa.threshold_db, 1),
                 count=len(pa.pauses))
        log.progress(0.3, "scene cuts")
        cuts = scene_cuts(project.proxy)
        log.progress(0.4, "faces")
        track_info: dict[str, Any] = {"available": False, "reason": None}
        try:
            model = faces.ensure_model(settings.models_dir)
            track = faces.build_track(project.proxy, model, src_width=info.width, src_height=info.height,
                                      sample_fps=settings.render.face_sample_fps,
                                      on_progress=lambda f: log.progress(0.4 + 0.55 * f, "faces"))
            track.save(project.face_track_json)
            mb = track.median_box()
            track_info = {"available": len(track.samples) > 0,
                          "reason": None if track.samples else "no face detected",
                          "present_fraction": round(track.present_fraction(info.duration), 3),
                          "samples": len(track.samples),
                          "median_box": [round(mb.x), round(mb.y), round(mb.w), round(mb.h)] if mb else None,
                          "detector": track.detector}
        except faces.FaceModelUnavailable as e:
            track_info = {"available": False, "reason": str(e)}
            log.warn("face model unavailable", error=str(e))
        except Exception as e:  # noqa: BLE001
            track_info = {"available": False, "reason": f"face detection failed: {e!r}"}
            log.warn("face detection failed", error=repr(e))
        speech_start = tr.first_word_time() if tr and tr.words else None
        analysis = {
            "duration": info.duration, "fps": info.fps_str, "width": info.width, "height": info.height,
            "noise_floor_db": round(pa.noise_floor_db, 1), "pause_threshold_db": round(pa.threshold_db, 1),
            "pauses": [[s, e] for s, e in pa.pauses],
            "pause_total_s": round(sum(e - s for s, e in pa.pauses), 2),
            "energy_1s_db": energy_1s,
            "sentence_energy_db": {str(k): v for k, v in sent_e.items()},
            "energy_peak_sentences": peaks,
            "scene_cuts": [round(c, 2) for c in cuts],
            "speech_start": speech_start,
            "face": track_info,
            "transcript": {"words": len(tr.words), "sentences": len(tr.sentences), "degraded": tr.degraded,
                           "model": tr.model} if tr else None,
        }
        project.analysis_json.write_text(json.dumps(analysis, indent=1))
        (project.dir("analyze") / "analysis.md").write_text(_markdown(analysis, tr))
        project.finish("analyze", pauses=len(pa.pauses), face=track_info.get("available"))
        log.done(pauses=len(pa.pauses), face=track_info.get("available"))
        return analysis
    except Exception as e:
        project.fail("analyze", repr(e))
        log.error("failed", error=repr(e))
        raise


def _markdown(a: dict[str, Any], tr: Transcript | None) -> str:
    L = ["# Analysis", "", f"- Duration: {a['duration']:.1f} s, {a['width']}x{a['height']} @ {a['fps']}",
         f"- Noise floor {a['noise_floor_db']} dB, pause threshold {a['pause_threshold_db']} dB",
         f"- Pauses >= {MIN_PAUSE_FOR_LIST} s: {len(a['pauses'])} totalling {a['pause_total_s']} s",
         f"- Scene cuts (lower bound): {len(a['scene_cuts'])}",
         f"- Speech starts at: {a['speech_start']}",
         f"- Face: {a['face']}", ""]
    if tr and a["energy_peak_sentences"]:
        L.append("## Energy peaks (loudest sentences)")
        for sid in a["energy_peak_sentences"]:
            s = tr.sentence(sid)
            L.append(f"- S{sid} [{s.t0:.1f}-{s.t1:.1f}] {a['sentence_energy_db'][str(sid)]} dB: {s.text}")
    L.append("")
    L.append("## Longest pauses")
    for s, e in sorted(a["pauses"], key=lambda p: -(p[1] - p[0]))[:10]:
        L.append(f"- {s:.2f} - {e:.2f} ({e - s:.2f} s)")
    return "\n".join(L) + "\n"
