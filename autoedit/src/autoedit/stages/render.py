"""Render: picture (pieces + timing map), graphics, sound; final.mp4 plus stems; everything resolved to
output time is written to resolved.json for verify. Fully deterministic from the EDL."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from ..config import Settings
from ..edl.resolve import resolve, resolve_range, spans_of_segment
from ..edl.schema import EDL
from ..edl.transcript import Transcript
from ..log import StageLog
from ..media.audio import analyze_pauses
from ..media.faces import FaceTrack
from ..media.probe import probe
from ..media.text import resolve_font
from ..profile import Profile
from ..project import Project, file_hash
from ..render.graphics import render_graphics
from ..render.library import MusicLibrary, SfxLibrary
from ..render.picture import compile_pieces, render_timeline
from ..render.sound import Cue, MixSpec, MusicCue, mix
from ..media.probe import duration_of


def _music_cues(edl: EDL, tr: Transcript | None, tm, profile: Profile, lib: MusicLibrary, notes: list[str],
                resolved: dict[str, Any]) -> tuple[list[MusicCue], int, bool]:
    cues: list[MusicCue] = []
    used: set[Path] = set()
    placeholders = False
    pickups = 0
    for sec in edl.music:
        s = resolve(sec.start, tr, edl, tm).out
        e = resolve(sec.end, tr, edl, tm).out
        if e <= s + 0.5:
            notes.append(f"music {sec.id}: empty range after resolution, skipped")
            continue
        if sec.file:
            f = Path(sec.file).expanduser()
            if not f.is_absolute() and profile.resolve_path(profile.audio.music_dir):
                f = profile.resolve_path(profile.audio.music_dir) / f  # type: ignore[operator]
            if f.exists():
                from ..render.library import Track
                track = lib.measure(Track(f, [sec.mood]))
            else:
                notes.append(f"music {sec.id}: file {f} missing, picking by mood")
                track = lib.measure(lib.pick(sec.mood, used))
        else:
            track = lib.measure(lib.pick(sec.mood, used))
        used.add(track.file)
        placeholders = placeholders or track.placeholder
        offset = 0.0
        pickup_out = None
        if sec.pickup_at is not None:
            shift = resolve(sec.pickup_at, tr, edl, tm).out
            song_t = sec.pickup_song_time if sec.pickup_song_time is not None else track.pickup
            if song_t is not None and s <= shift < e:
                # OFF = pickup - (shift - S). When the song's pickup comes sooner than the shift,
                # the song enters later instead (the music "kicks in" at shift - pickup).
                if song_t >= shift - s:
                    offset = song_t - (shift - s)
                else:
                    s = shift - song_t
                    notes.append(f"music {sec.id}: starts at {s:.2f}s so the pickup lands on the shift at {shift:.2f}s")
                pickup_out = shift
                pickups += 1
            else:
                notes.append(f"music {sec.id}: no pickup found in {track.file.name} or shift outside section")
        cues.append(MusicCue(track.file, s, e, sec.rel_db, offset, track.lufs, sec.id))
        resolved["music"].append({"id": sec.id, "out_in": s, "out_out": e, "file": str(track.file), "mood": sec.mood,
                                  "rel_db": sec.rel_db, "offset": offset, "lufs": track.lufs,
                                  "placeholder": track.placeholder, "pickup_out": pickup_out,
                                  "pickup_song_time": track.pickup})
    return cues, pickups, placeholders


def run(project: Project, settings: Settings, profile: Profile, log: StageLog | None = None, *,
        preview: bool = False, edl_path: Path | None = None, out_dir: Path | None = None) -> dict[str, Any]:
    stage = "render"
    log = log or project.log(stage)
    edl_path = edl_path or project.edl_json
    if not preview:
        project.begin(stage, file_hash(edl_path))
    try:
        edl = EDL.load(edl_path)
        edl.ensure_ledger()
        tr = Transcript.load(project.transcript_json) if project.transcript_json.exists() else None
        info = probe(project.ingest_source)
        track = FaceTrack.load(project.face_track_json) if project.face_track_json.exists() else None
        if track is not None and not track.samples:
            track = None
        font = resolve_font(profile.fonts.primary)
        work = out_dir or (project.dir(stage) / "preview" if preview else project.dir(stage))
        work.mkdir(parents=True, exist_ok=True)
        rc = settings.render
        notes: list[str] = []

        # ---- picture ----
        compiled = compile_pieces(edl, tr, info, track, profile, log)
        notes += compiled.notes
        if preview:
            pinfo = probe(project.proxy)
            out_size = (pinfo.width, pinfo.height)
            src = project.proxy
            crf, preset = 28, rc.preview_preset
        else:
            out_size = (info.width, info.height)
            src = project.ingest_source
            crf, preset = rc.crf, rc.preset
        log.info("compiled", pieces=len(compiled.pieces), out_duration=round(compiled.timing.out_duration, 2))
        render_timeline(compiled, src, work, info, profile, font, workers=rc.workers, crf=crf, preset=preset, log=log,
                        preview_size=out_size if preview else None, source_size=(info.width, info.height) if preview else None)
        tm = compiled.timing

        # ---- resolve everything to output time ----
        resolved: dict[str, Any] = {"out_duration": tm.out_duration, "fps": info.fps_str, "size": list(out_size),
                                    "captions": [], "cards": [], "beats": [], "overlays": [], "music": [], "dropouts": [],
                                    "fadeouts": [], "swells": [], "sfx": [], "vo": [], "chapters": [], "zooms": [],
                                    "punches": [], "hook": None}
        for p in compiled.pieces:
            if p.zoom:
                resolved["zooms"].append({"id": p.zoom, "out_in": p.out_in, "out_out": p.out_in + p.dur, "crop": p.crop})
            if p.punch:
                resolved["punches"].append({"piece": p.id, "out_in": p.out_in, "crop": p.crop})
        for c in edl.cards:
            sp = tm.span_by_id(f"card:{c.id}")
            if sp:
                resolved["cards"].append({"id": c.id, "out_in": sp.out_in, "out_out": sp.out_out, "text": c.text})
        hold_events = [e for e in compiled.events if e["type"] == "hold"]
        for ev in hold_events:
            resolved["beats"].append(ev)
        for ch in edl.chapters:
            resolved["chapters"].append({"title": ch.title, "out": resolve(ch.at, tr, edl, tm).out})
        if tr and tr.words:
            fw = tm.to_out(tr.words[0].t0)
            resolved["hook"] = {"first_word_out": fw if fw is not None else tm.to_out_nearest(tr.words[0].t0)}

        # ---- graphics ----
        g = render_graphics(edl, tr, tm, compiled.pieces, track, info, profile, font, out_size, work,
                            project.root / "assets", hold_events, crf=crf, preset=preset,
                            name="graphics_preview" if preview else "graphics", log=log)
        notes += g.notes
        resolved["captions"] = [p.__dict__ for p in g.placements]
        for ov in edl.overlays:
            r = resolve(ov.at, tr, edl, tm)
            resolved["overlays"].append({"id": ov.id, "out_in": r.out, "out_out": r.out + ov.dur, "kind": ov.kind})

        # ---- sound ----
        ph_dir = work / "placeholders"
        mlib = MusicLibrary.load(profile.resolve_path(profile.audio.music_dir), ph_dir)
        slib = SfxLibrary.load(profile.resolve_path(profile.audio.sfx_dir), ph_dir)
        music_cues, pickups, music_placeholder = _music_cues(edl, tr, tm, profile, mlib, notes, resolved)
        spec = MixSpec(duration=tm.out_duration, music=music_cues, lufs=profile.audio.lufs,
                       true_peak=profile.audio.true_peak, duck_ratio=profile.audio.duck_ratio)
        for d in edl.dropouts:
            a, b = resolve_range(d.start, d.end, None, tr, edl, tm, 2.0)
            spec.dropouts.append((a.out, b.out))
            resolved["dropouts"].append({"id": d.id, "out_in": a.out, "out_out": b.out, "reason": d.reason})
        for f in edl.fadeouts:
            a, b = resolve_range(f.start, f.end, None, tr, edl, tm, profile.audio.fadeout_s)
            spec.fadeouts.append((a.out, b.out))
            resolved["fadeouts"].append({"id": f.id, "out_in": a.out, "out_out": b.out})
        for sw in edl.swells:
            a, b = resolve_range(sw.start, sw.end, None, tr, edl, tm, 8.0)
            spec.swells.append((a.out, b.out, sw.db))
            resolved["swells"].append({"id": sw.id, "out_in": a.out, "out_out": b.out, "db": sw.db})
        sfx_placeholder = slib.placeholder
        sfx_events = [{"type": "sfx", "kind": s.kind, "file": s.file, "out": resolve(s.at, tr, edl, tm).out,
                       "gain": s.gain_db, "align": s.align, "ref": s.id, "reason": s.reason} for s in edl.sfx]
        sfx_events += [e for e in compiled.events if e["type"] == "sfx"] + g.events
        kind_counts: dict[str, int] = {}
        cues_used = 0
        for ev in sorted(sfx_events, key=lambda e: e["out"]):
            f = Path(ev["file"]).expanduser() if ev.get("file") else None
            if f is None or not f.exists():
                kind = ev.get("kind") or "pop"
                idx = kind_counts.get(kind, 0)
                kind_counts[kind] = idx + 1
                f = slib.pick(kind, idx)
            if f is None:
                notes.append(f"sfx {ev.get('ref')}: no file for kind {ev.get('kind')}")
                continue
            t = ev["out"]
            if ev.get("align") == "end":
                t = max(0.0, t - duration_of(f))
            if (ev.get("kind") or "") in ("riser", "hit", "braaam", "drone"):
                cues_used += 1
            spec.sfx.append(Cue(f, t, float(ev.get("gain", 0.0)), str(ev.get("ref"))))
            resolved["sfx"].append({"id": ev.get("ref"), "kind": ev.get("kind"), "file": str(f), "out": t,
                                    "reason": ev.get("reason")})
        vo_count = 0
        for vo in edl.voiceover_slots:
            if vo.file:
                f = Path(vo.file).expanduser()
                if not f.is_absolute():
                    f = project.root / "assets" / f
                if f.exists():
                    t = resolve(vo.at, tr, edl, tm).out
                    spec.vo.append(Cue(f, t, 0.0, vo.id))
                    resolved["vo"].append({"id": vo.id, "out": t, "file": str(f)})
                    vo_count += 1
                else:
                    notes.append(f"voiceover {vo.id}: file {f} missing")
        vc = profile.audio.voice_clean
        if vc == "auto":
            floor = analyze_pauses(project.audio_wav, 0.4).noise_floor_db
            spec.voice_clean = floor > -50.0
            notes.append(f"voice clean auto: noise floor {floor:.1f} dB -> {'on' if spec.voice_clean else 'off'}")
        else:
            spec.voice_clean = vc == "on"
        final = work / ("preview.mp4" if preview else "final.mp4")
        stems = None if preview else work / "stems"
        log.progress(0.0, "mixing")
        mr = mix(g.video, final, spec, stems, log)

        # ---- ledger ----
        n_zoom = len(resolved["zooms"])
        n_punch = len(resolved["punches"])
        faces_ok = track is not None
        edl.mark("emphasis_zooms", ("executed" if faces_ok else "degraded") if n_zoom else "not_executed",
                 (f"{n_zoom} zooms, face-anchored" if faces_ok else f"{n_zoom} zooms anchored to the upper third: no face track") if n_zoom else "no zooms in the EDL", stage, n_zoom)
        edl.mark("punch_ins", ("executed" if faces_ok else "degraded") if n_punch else "not_executed",
                 (f"{n_punch} punched pieces, face-anchored" if faces_ok else f"{n_punch} punched pieces, no face track") if n_punch else "punch scale is 1.0 for this profile/experience", stage, n_punch)
        edl.mark("eye_trace_continuity", "executed" if faces_ok and (n_zoom or n_punch) else ("degraded" if (n_zoom or n_punch) else "not_executed"),
                 "crops keep the face at the same screen position across cuts" if faces_ok else "no face track to hold the focal point", stage)
        n_beats = len(resolved["beats"])
        edl.mark("beats_shut_up_show_it", "executed" if n_beats else "not_executed", f"{n_beats} beats" if n_beats else "no beats in the EDL", stage, n_beats)
        n_cap = len([p for p in g.placements if p.kind == "caption"])
        edl.mark("keyword_captions", "executed" if n_cap else "not_executed", f"{n_cap} captions, max {profile.captions.max_words} words" if n_cap else "no captions in the EDL", stage, n_cap)
        n_cards = len(resolved["cards"])
        edl.mark("chapter_cards", "executed" if n_cards else "not_executed", f"{n_cards} cards" if n_cards else "no cards in the EDL", stage, n_cards)
        n_still = len([o for o in edl.overlays if o.kind == "still"])
        n_broll = len([o for o in edl.overlays if o.kind == "broll"])
        edl.mark("guided_attention_stills", "executed" if n_still and g.overlays_rendered else "not_executed",
                 f"{n_still} stills" if n_still else "no still assets in the EDL", stage, n_still)
        edl.mark("broll_every_noun", "executed" if n_broll and g.overlays_rendered else "not_executed",
                 f"{n_broll} B-roll overlays" if n_broll else "no B-roll assets provided", stage, n_broll)
        edl.mark("graphics_motion_in", "executed" if (g.overlays_rendered or n_cards) else "not_executed",
                 "overlays slide in with a whoosh; cards fade with a shutter" if (g.overlays_rendered or n_cards) else "no graphics to animate", stage)
        edl.mark("soundscape_atmosphere", "not_executed", "atmosphere beds under stills/B-roll are not implemented yet", stage)
        n_mus = len(music_cues)
        edl.mark("music_per_section", "executed" if n_mus else "not_executed", f"{n_mus} sections" if n_mus else "no music sections in the EDL", stage, n_mus)
        edl.mark("music_ducking", "executed" if n_mus else "not_executed", f"sidechain ratio {profile.audio.duck_ratio}" if n_mus else "no music", stage)
        edl.mark("music_relative_gain", "executed" if n_mus else "not_executed", f"each track measured, {profile.audio.music_rel_db} dB relative to voice" if n_mus else "no music", stage)
        for key, lst in (("music_dropouts", spec.dropouts), ("music_fadeouts", spec.fadeouts), ("music_swells", spec.swells)):
            edl.mark(key, "executed" if lst and n_mus else "not_executed", f"{len(lst)}" if lst and n_mus else ("no music" if not n_mus else "none in the EDL"), stage, len(lst))
        edl.mark("music_pickup_sync", "executed" if pickups else "not_executed", f"{pickups} pickups synced" if pickups else "no pickup target in the EDL", stage, pickups)
        rep = any(a.file == b.file for a, b in zip(sorted(spec.sfx, key=lambda c: c.t), sorted(spec.sfx, key=lambda c: c.t)[1:]))
        edl.mark("sfx_variation", "executed" if rep else "not_executed", "back-to-back repeats pitch/speed varied" if rep else "no SFX repeated back to back", stage)
        edl.mark("audio_cues", "executed" if cues_used else "not_executed", f"{cues_used} risers/hits" if cues_used else "no risers or hits in the EDL", stage, cues_used)
        edl.mark("voice_clean", "executed" if spec.voice_clean else "not_executed", "highpass + denoise + compression" if spec.voice_clean else "voice judged clean enough (or profile off)", stage)
        edl.mark("loudness_target", "executed", f"measured {mr.measured_lufs:.1f} LUFS, gain {mr.gain_db:+.2f} dB, limiter at {profile.audio.true_peak} dBTP", stage)
        edl.mark("licensed_audio", "not_executed" if (music_placeholder or (sfx_placeholder and spec.sfx)) else ("executed" if (n_mus or spec.sfx) else "not_executed"),
                 ("synth placeholders used: " + ", ".join(k for k, v in (("music", music_placeholder), ("sfx", sfx_placeholder and bool(spec.sfx))) if v)) if (music_placeholder or (sfx_placeholder and spec.sfx)) else ("profile library files" if (n_mus or spec.sfx) else "no audio assets used"), stage)
        n_slots = len(edl.voiceover_slots)
        edl.mark("voiceover_mixed", "executed" if vo_count else "not_executed",
                 f"{vo_count} of {n_slots} slots recorded" if n_slots else "no voiceover slots", stage, vo_count)
        n_mont = len([s for s in edl.segments if s.kind == "montage"])
        edl.mark("montage_compression", "executed" if n_mont else "not_executed", f"{n_mont} montage segments" if n_mont else "no montage ranges in the EDL", stage, n_mont)

        report = {"preview": preview, "final": str(final), "out_duration": tm.out_duration, "pieces": len(compiled.pieces),
                  "measured_lufs_pre_gain": mr.measured_lufs, "gain_db": mr.gain_db, "stems": {k: str(v) for k, v in mr.stems.items()},
                  "notes": notes, "voice_clean": spec.voice_clean, "music_placeholder": music_placeholder,
                  "sfx_placeholder": sfx_placeholder}
        (work / "resolved.json").write_text(json.dumps(resolved, indent=1, default=str))
        (work / "render_report.json").write_text(json.dumps(report, indent=1))
        edl.save(work / "edl.rendered.json")
        if not preview:
            project.finish(stage, out_duration=tm.out_duration, pieces=len(compiled.pieces), final=str(final))
        log.done(final=str(final), duration=round(tm.out_duration, 2))
        return report
    except Exception as e:
        if not preview:
            project.fail(stage, repr(e))
        log.error("failed", error=repr(e))
        raise
