"""Shorts: select the best moments (model scores plus energy peaks), derive a vertical EDL for each,
render it face-tracked with word captions and a loop-friendly ending, ready for verify."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import Settings
from ..edl.schema import EDL
from ..edl.transcript import Transcript
from ..llm.client import LLM, LLMUnavailable, load_prompt
from ..llm.schemas import ShortsOut
from ..log import StageLog
from ..media.faces import FaceTrack
from ..media.probe import probe
from ..media.timing import TimingMap
from ..profile import Profile
from ..project import Project, file_hash
from ..render.picture import compile_pieces
from ..shorts.select import build_windows, heuristic_candidates, short_edl
from . import render as render_stage
from .plan import profile_block


def run(project: Project, settings: Settings, profile: Profile, log: StageLog | None = None, *,
        count: int | None = None, llm: str = "auto") -> dict[str, Any]:
    log = log or project.log("shorts")
    project.begin("shorts", file_hash(project.edl_json) if project.edl_json.exists() else None)
    try:
        from ..formats import get_format
        fmt = get_format(project.format)
        if not fmt.captions:   # chat-skit: a 9:16 slice of the chat UI is unreadable; needs its own vertical layout
            rendered = project.dir("render") / "edl.rendered.json"
            if rendered.exists():
                r = EDL.load(rendered)
                r.ensure_ledger()
                for k in ("shorts_face_tracked", "shorts_word_captions", "shorts_loop_ending"):
                    r.mark(k, "not_executed", f"{fmt.name}: vertical recomposition of the chat layout is not implemented yet", "shorts")
                r.save(rendered)
            (project.dir("render") / "shorts").mkdir(parents=True, exist_ok=True)
            (project.dir("render") / "shorts" / "index.json").write_text(json.dumps({"count": 0, "shorts": [], "notes": [f"{fmt.name}: Shorts not supported yet"]}))
            project.finish("shorts", count=0)
            log.done(count=0, skipped=fmt.name)
            return {"count": 0, "shorts": [], "notes": [f"{fmt.name}: Shorts not supported yet"]}
        edl = EDL.load(project.edl_json)
        tr = Transcript.load(project.transcript_json)
        analysis = json.loads(project.analysis_json.read_text())
        if not tr.words:
            rendered = project.dir("render") / "edl.rendered.json"
            if rendered.exists():
                r = EDL.load(rendered)
                r.ensure_ledger()
                for k in ("shorts_face_tracked", "shorts_word_captions", "shorts_loop_ending"):
                    r.mark(k, "not_executed", "no transcript: Shorts need words to pick moments and caption them", "shorts")
                r.save(rendered)
            (project.dir("render") / "shorts").mkdir(parents=True, exist_ok=True)
            (project.dir("render") / "shorts" / "index.json").write_text(json.dumps({"count": 0, "shorts": [], "notes": ["no transcript"]}))
            project.finish("shorts", count=0)
            log.done(count=0, skipped="no transcript")
            return {"count": 0, "shorts": [], "notes": ["no transcript"]}
        info = probe(project.ingest_source)
        track = FaceTrack.load(project.face_track_json) if project.face_track_json.exists() else None
        if track and not track.samples:
            track = None
        tm_path = project.dir("render") / "timing_map.json"
        if tm_path.exists():
            tm = TimingMap.from_json(json.loads(tm_path.read_text()))
        else:
            tm = compile_pieces(edl, tr, info, track, profile).timing
        n = count or profile.shorts.count
        notes: list[str] = []
        client = LLM(settings, project.dir("plan") / "llm", mode=llm, log=log)
        cands = None
        if llm != "off" and client.available:
            peaks = analysis.get("energy_peak_sentences") or []
            user = load_prompt("shorts").format(
                profile_block=profile_block(profile),
                transcript_block=tr.numbered_for_llm({int(k): v for k, v in (analysis.get("sentence_energy_db") or {}).items()}),
                peaks_block=", ".join(f"S{s}" for s in peaks) or "none",
                max_candidates=max(6, n * 3), min_s=profile.shorts.min_s, max_s=profile.shorts.max_s)
            try:
                client._n = 2  # the shorts call is the third saved response (after story pass and decisions)
                cands = client.call("shorts", user, ShortsOut).candidates
            except LLMUnavailable as e:
                notes.append(f"model scoring unavailable ({e}); heuristic scores used")
        if cands is None:
            if llm != "off":
                notes.append("ANTHROPIC_API_KEY not set: heuristic scores (energy, questions, numbers) used")
            cands = heuristic_candidates(tr, analysis, tm, profile)
        windows, wnotes = build_windows(cands, tr, analysis, tm, profile, n)
        notes += wnotes
        log.info("selected", shorts=len(windows), candidates=len(cands))
        out_root = project.dir("render") / "shorts"
        out_root.mkdir(parents=True, exist_ok=True)
        plan_dir = project.dir("plan") / "shorts"
        plan_dir.mkdir(parents=True, exist_ok=True)
        results = []
        for i, w in enumerate(windows):
            sedl = short_edl(edl, tr, w, profile)
            sedl_path = plan_dir / f"{w.id}.edl.json"
            sedl.save(sedl_path)
            out_dir = out_root / w.id
            log.progress(i / max(1, len(windows)), f"rendering {w.id}")
            rep = render_stage.run(project, settings, profile, project.log(f"shorts.{w.id}", quiet=True),
                                   edl_path=sedl_path, out_dir=out_dir, vertical=True, context_label=w.context_label)
            results.append({"id": w.id, "title": w.title, "context_label": w.context_label, "hook_sentence": w.hook_sentence,
                            "from_sentence": w.from_sentence, "to_sentence": w.to_sentence, "src_in": w.src_in,
                            "src_out": w.src_out, "score": w.score, "llm_score": w.llm_score, "energy": w.energy_score,
                            "reason": w.reason, "file": rep["final"], "duration": rep["out_duration"]})
        # mark the shorts techniques on the long-form rendered ledger too
        rendered = project.dir("render") / "edl.rendered.json"
        if rendered.exists():
            r = EDL.load(rendered)
            r.ensure_ledger()
            st = "executed" if windows else "not_executed"
            why = f"{len(windows)} shorts" if windows else "no window of 15-60 s could be selected"
            r.mark("shorts_face_tracked", st if track else ("degraded" if windows else st), why if track else f"{why}; no face track, letterbox fallback", "shorts", len(windows))
            r.mark("shorts_word_captions", st, why, "shorts", len(windows))
            r.mark("shorts_loop_ending", st, why, "shorts", len(windows))
            r.save(rendered)
        index = {"count": len(results), "shorts": results, "notes": notes}
        (out_root / "index.json").write_text(json.dumps(index, indent=1))
        project.finish("shorts", count=len(results))
        log.done(count=len(results))
        return index
    except Exception as e:
        project.fail("shorts", repr(e))
        log.error("failed", error=repr(e))
        raise
