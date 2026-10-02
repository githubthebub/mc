"""Verify: an automated QA report per output, with frame grabs, and an honest NOT EXECUTED section."""

from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from ..config import Settings
from ..edl.schema import EDL
from ..edl.techniques import TECHNIQUES
from ..log import StageLog
from ..media.audio import analyze_pauses, measure_loudness, rms_db_windows
from ..media.faces import FaceTrack
from ..media.ffmpeg import extract_frame
from ..media.images import annotate
from ..media.probe import probe
from ..media.text import AssStyle, Rect, render_font_check, resolve_font, safe_zone
from ..media.timing import TimingMap
from ..profile import Profile
from ..project import Project, file_hash

DEAD_AIR_S = 0.5
DROPOUT_MAX_DB = -50.0


def _check(id_: str, status: str, summary: str, measured: Any = None, target: Any = None,
           frames: list[str] | None = None, details: Any = None) -> dict[str, Any]:
    return {"id": id_, "status": status, "summary": summary, "measured": measured, "target": target,
            "frames": frames or [], "details": details}


def scene_changes(video: Path, thresh: float = 0.12) -> list[float]:
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf",
                          f"scale=160:-2,select='gt(scene,{thresh})',showinfo", "-an", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", err)]


def subtitle_mask(ass_file: Path, fonts_dir: Path | None, W: int, H: int, fps: str, t: float, tmp: Path):
    """Boolean ink mask of the ASS subtitles at time t, rendered alone on black."""
    from ..media.text import ass_filter
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-f", "lavfi", "-i",
                        f"color=c=black:s={W}x{H}:r={fps}:d={t + 2:.3f}", "-vf", ass_filter(ass_file, fonts_dir),
                        "-frames:v", "1", str(tmp)], check=True, capture_output=True)
        a = np.asarray(Image.open(tmp).convert("L")) > 60
        tmp.unlink(missing_ok=True)
        return a
    except (subprocess.CalledProcessError, OSError):
        return None


def _face_out(track: FaceTrack | None, tm: TimingMap, t_out: float, scale: float) -> Rect | None:
    if not track:
        return None
    ts = tm.to_src(t_out)
    if ts is None:
        return None
    b = track.box_at(ts)
    return Rect(b.x * scale, b.y * scale, b.w * scale, b.h * scale) if b else None


def verify_output(final: Path, work: Path, out_dir: Path, edl: EDL, profile: Profile, track: FaceTrack | None,
                  src_width: int, log: StageLog | None = None, vertical: bool = False,
                  label: str = "long") -> dict[str, Any]:
    """Run every check on one rendered output. `work` holds resolved.json, timing_map.json, stems/."""
    frames_dir = out_dir / "frames" / label
    frames_dir.mkdir(parents=True, exist_ok=True)
    resolved = json.loads((work / "resolved.json").read_text())
    tm = TimingMap.from_json(json.loads((work / "timing_map.json").read_text()))
    info = probe(final)
    W, H = info.width, info.height
    scale = W / src_width
    bench = profile.benchmarks()
    checks: list[dict[str, Any]] = []

    def grab(t: float, name: str, boxes: list[tuple[tuple[int, int, int, int], str, str]], title: str) -> str:
        raw = extract_frame(final, t, frames_dir / f"_{name}.png")
        out = annotate(raw, frames_dir / f"{name}.png", boxes, title)
        raw.unlink(missing_ok=True)
        return str(out.relative_to(out_dir))

    src_info = None
    if vertical:
        from ..render.vertical import face_in_vertical_output
        src_info = probe(work.parents[2] / "01_ingest" / "source.mp4") if (work.parents[2] / "01_ingest" / "source.mp4").exists() else None

    def face_at(t: float) -> Rect | None:
        if vertical and src_info is not None:
            return face_in_vertical_output(track, tm, t, resolved.get("crop_paths", []), src_info, (W, H))
        return _face_out(track, tm, t, scale)

    def face_boxes(t: float) -> list[tuple[tuple[int, int, int, int], str, str]]:
        f = face_at(t)
        return [(f.as_int(), "face", "#00FF88")] if f else []

    zone = safe_zone(W, H, vertical)
    zone_box = (zone.as_int(), "safe zone", "#4488FF")

    # ---- 1 dead air ----
    pa = analyze_pauses(final, min_silence=DEAD_AIR_S, noise=-45.0)
    beats = [(b["out"], b["out_end"]) for b in resolved.get("beats", [])]
    cards = [(c["out_in"], c["out_out"]) for c in resolved.get("cards", [])]
    gaps = []
    for s, e in pa.pauses:
        planned = any(a - 0.1 <= s and e <= b + 0.1 for a, b in beats + cards)
        gaps.append({"start": s, "end": e, "dur": round(e - s, 2), "planned_hold": planned})
    unplanned = [g for g in gaps if not g["planned_hold"]]
    limit = bench.get("silent_gaps_max")
    frames = [grab((g["start"] + g["end"]) / 2, f"deadair_{i}", face_boxes((g["start"] + g["end"]) / 2),
                   f"dead air {g['start']:.2f}-{g['end']:.2f}") for i, g in enumerate(unplanned[:6])]
    if limit is None:
        st = "pass" if len(unplanned) <= 10 else "warn"
    else:
        st = "pass" if len(unplanned) <= limit else "fail"
    checks.append(_check("dead_air", st, f"{len(unplanned)} silent gaps > {DEAD_AIR_S}s outside planned holds "
                         f"({len(gaps) - len(unplanned)} inside planned holds without music)",
                         len(unplanned), limit, frames, gaps))

    # ---- 2 loudness and true peak ----
    L = measure_loudness(final)
    ok_i = abs(L.integrated_lufs - profile.audio.lufs) <= 1.0
    checks.append(_check("loudness", "pass" if ok_i else "fail", f"integrated {L.integrated_lufs:.1f} LUFS vs target {profile.audio.lufs}",
                         L.integrated_lufs, f"{profile.audio.lufs} ±1"))
    tp_limit = profile.audio.true_peak + 0.5
    ok_tp = L.true_peak_dbtp is not None and L.true_peak_dbtp <= tp_limit
    checks.append(_check("true_peak", "pass" if ok_tp else "fail", f"true peak {L.true_peak_dbtp} dBTP",
                         L.true_peak_dbtp, f"<= {tp_limit}"))

    # ---- 3 music automation on the music stem ----
    stem = work / "stems" / "music.wav"
    raw_stem = work / "stems" / "music_raw.wav"
    if resolved.get("music") and stem.exists():
        win = 0.5
        # automation is measured on the music bus BEFORE ducking so the voice cannot mask a move
        m = rms_db_windows(raw_stem if raw_stem.exists() else stem, win=win)
        ducked = rms_db_windows(stem, win=win) if raw_stem.exists() else None

        def rms(a: float, b: float) -> list[float]:
            # only windows that lie entirely inside [a, b]
            i0 = max(0, int(math.ceil(a / win - 1e-6)))
            i1 = max(i0 + 1, int(math.floor(b / win + 1e-6)))
            return [float(x) for x in m[i0:i1]]

        det: dict[str, Any] = {"dropouts": [], "fadeouts": [], "swells": [], "pickups": []}
        ok = True
        for d in resolved["dropouts"]:
            a, b = d["out_in"] + 0.25, d["out_out"] - 0.25
            vals = rms(a, b) if b > a else rms(d["out_in"], d["out_out"])
            peak = max(vals) if vals else -120.0
            good = peak <= DROPOUT_MAX_DB
            ok &= good
            det["dropouts"].append({"id": d["id"], "max_db": round(peak, 1), "ok": good})
        for f in resolved["fadeouts"]:
            a, b = f["out_in"], f["out_out"]
            q = max(0.5, (b - a) / 4)
            head, tail = rms(a, a + q), rms(b - q, b)
            drop = (np.mean(head) - np.mean(tail)) if head and tail else 0.0
            good = drop >= 12.0
            ok &= good
            det["fadeouts"].append({"id": f["id"], "drop_db": round(float(drop), 1), "ok": good})
        for s in resolved["swells"]:
            a, b = s["out_in"], s["out_out"]
            q = max(0.5, (b - a) / 4)
            head, tail = rms(a, a + q), rms(a + (b - a) / 2, b)
            # peak of the second half against the opening quarter (a dropout right at the payoff must not hide the swell)
            rise = (max(tail) - np.mean(head)) if head and tail else 0.0
            good = rise >= s["db"] * 0.4
            ok &= good
            det["swells"].append({"id": s["id"], "rise_db": round(float(rise), 1), "ok": good})
        for mu in resolved["music"]:
            if mu.get("pickup_out") is not None:
                p = mu["pickup_out"]
                before, after = rms(p - 2.0, p - 0.25), rms(p + 0.25, p + 2.0)
                step = (np.mean(after) - np.mean(before)) if before and after else 0.0
                good = step >= 2.0
                ok &= good
                det["pickups"].append({"id": mu["id"], "step_db": round(float(step), 1), "ok": good})
        if ducked is not None and len(ducked) == len(m):
            # ducking: while the voice is active the ducked bus must sit under the raw bus
            vstem = work / "stems" / "voice.wav"
            v = rms_db_windows(vstem, win=win) if vstem.exists() else None
            if v is not None and len(v) == len(m):
                active = [i for i in range(len(m)) if v[i] > -40 and m[i] > -60]
                if len(active) >= 4:        # only meaningful when there is a voice to duck under
                    duck_db = float(np.mean([m[i] - ducked[i] for i in active]))
                    det["ducking"] = [{"mean_duck_db_under_voice": round(duck_db, 1), "ok": duck_db >= 2.0}]
                    ok &= duck_db >= 2.0
        n = sum(len(v) for v in det.values())
        checks.append(_check("music_automation", ("pass" if ok else "fail") if n else "not_executed",
                             f"{n} planned music moves measured on the music stem", det, "dropout <= -50 dBFS, fadeout >= 12 dB down, swell >= 40% of planned, pickup >= +2 dB",
                             details=det))
    else:
        checks.append(_check("music_automation", "not_executed", "no music sections rendered"))

    # ---- 4 captions and cards: safe zone and face overlap (geometry + pixels) ----
    caps = list(resolved.get("captions", [])) + list(resolved.get("word_captions", []))
    bad = []
    frames = []
    ass_file = next((work / n for n in ("graphics.ass", "graphics_preview.ass") if (work / n).exists()), None)
    fonts_dir = None
    try:
        fonts_dir = resolve_font(profile.fonts.primary).path.parent
    except Exception:  # noqa: BLE001
        pass
    for i, c in enumerate(caps):
        t = (c["out_in"] + c["out_out"]) / 2
        box = Rect(*c["box"])
        face = face_at(t)
        overlap_px = 0
        if face and ass_file is not None:
            # exact: render the subtitles alone on black at this time and count ink inside the face box
            mask = subtitle_mask(ass_file, fonts_dir, W, H, info.fps_str, t, frames_dir / "_mask.png")
            x, y, w, h = face.as_int()
            if mask is not None and w > 0 and h > 0:
                overlap_px = int(mask[max(0, y):y + h, max(0, x):x + w].sum())
        inside = box.inside(zone)
        overlaps = bool(c.get("overlaps_face")) or overlap_px > 50
        if not inside or overlaps:
            bad.append({"id": c["id"], "inside_safe": inside, "overlaps_face": overlaps, "overlap_px": overlap_px})
        if i < 8:
            boxes = [zone_box, (tuple(int(v) for v in c["box"]), c["id"], "#FFD400"), *face_boxes(t)]
            frames.append(grab(t, f"caption_{c['id']}", boxes, f"{c['kind']} {c['id']} @ {t:.2f}s"))
    checks.append(_check("text_safe_zones", ("pass" if not bad else "fail") if caps else "not_executed",
                         f"{len(caps)} text placements, {len(bad)} outside the safe zone or on the face",
                         bad, "all inside safe zone, none overlapping the face box", frames))

    # ---- 5 faces never cropped by zooms / punches (long-form) or by the crop path (Shorts) ----
    crops = [("zoom", z) for z in resolved.get("zooms", [])] + [("punch", p) for p in resolved.get("punches", [])]
    cropped = []
    frames = []
    if vertical:
        crops = []
        for r in resolved.get("crop_paths", []):
            if r.get("mode") != "face-tracked":
                continue
            for (t_out, x, y) in r["keys"]:
                crops.append(("path", {"id": r["piece"], "out_in": t_out, "crop": [x, y, r["w"], r["h"]]}))
        for k, (kind, z) in enumerate(crops):
            if k % 6 == 0 and len(frames) < 6:
                frames.append(grab(z["out_in"] + 0.05, f"crop_{len(frames)}", face_boxes(z["out_in"] + 0.05), f"crop path @ {z['out_in']:.2f}s"))
    for kind, z in crops:
        if not z.get("crop") or not track:
            continue
        t_out = z["out_in"] + (0.0 if kind == "path" else 0.2)
        ts = tm.to_src(t_out)
        fb = track.box_at(ts) if ts is not None else None
        if fb is None:
            continue
        x, y, w, h = z["crop"]
        inside = fb.x >= x - 2 and fb.y >= y - 2 and fb.x + fb.w <= x + w + 2 and fb.y + fb.h <= y + h + 2
        if not inside:
            cropped.append({"kind": kind, "id": z.get("id") or z.get("piece"), "crop": z["crop"], "face": fb.as_int()})
        if kind == "zoom" and len(frames) < 4:
            frames.append(grab(t_out, f"{kind}_{z.get('id')}", face_boxes(t_out), f"{kind} {z.get('id')} @ {t_out:.2f}s"))
    checks.append(_check("faces_not_cropped", ("pass" if not cropped else "fail") if crops else "not_executed",
                         f"{len(crops)} zoom/punch crops checked against the face track, {len(cropped)} cut the face"
                         if track else "no face track; crops anchored to the upper third",
                         cropped, "face box inside every crop", frames))

    # ---- 6 hook ----
    hook = resolved.get("hook") or {}
    fw = hook.get("first_word_out")
    changes = scene_changes(final)
    marks = sorted(set([round(t, 2) for t in resolved.get("visual_events", [])] +
                       [round(p["out_in"], 2) for p in resolved.get("punches", [])] +
                       [round(z["out_in"], 2) for z in resolved.get("zooms", [])] +
                       [round(c["out_in"], 2) for c in resolved.get("cards", [])] +
                       [round(c["out_in"], 2) for c in caps] + [round(c, 2) for c in changes] +
                       [round(s.out_in, 2) for s in tm.spans[1:]]))
    early = [m for m in marks if 0 < m <= 3.0]
    hook_limit = 1.0 if vertical else 3.0
    if hook.get("voiceless"):
        fw = hook.get("first_event_out")
    ok_hook = fw is not None and fw <= hook_limit
    frames = [grab(t, f"hook_{int(t * 10)}", face_boxes(t), f"hook {t:.1f}s") for t in (0.5, 1.5, 2.5)]
    checks.append(_check("hook", "pass" if ok_hook else "fail",
                         f"first {'event' if hook.get('voiceless') else 'word'} at {fw if fw is None else round(fw, 2)}s; {len(early)} visual changes in the first 3 s",
                         {"first_word_out": fw, "visual_changes_first_3s": len(early)}, f"speech within {hook_limit} s", frames))
    if vertical:
        # loop-friendly ending: no fade to silence in the last half second
        tail = rms_db_windows(final, win=0.25)
        last = float(np.max(tail[-2:])) if len(tail) >= 2 else -120.0
        mstem = work / "stems" / "music.wav"
        mtail = float(np.max(rms_db_windows(mstem, win=0.25)[-2:])) if mstem.exists() else None
        ok_loop = last > -45.0 and (mtail is None or mtail > -45.0)
        checks.append(_check("loop_ending", "pass" if ok_loop else "fail",
                             f"last 0.5 s: mix {last:.1f} dBFS, music {mtail if mtail is None else round(mtail, 1)} dBFS",
                             {"mix_tail_db": round(last, 1), "music_tail_db": mtail}, "no fade to silence (> -45 dBFS)"))

    # ---- 7 pacing vs benchmarks ----
    D = tm.out_duration
    all_changes = sorted(set(marks))
    per_min = len(all_changes) / (D / 60) if D else 0
    first60 = [m for m in all_changes if m <= 60]
    pm60 = len(first60) / (min(D, 60) / 60) if D else 0
    shots = np.diff([0.0, *all_changes, D]) if all_changes else np.array([D])
    avg_shot = float(np.mean(shots)) if len(shots) else D
    longest = float(np.max(shots)) if len(shots) else D
    pacing = {"visual_changes_per_min": round(per_min, 1), "first_60s_per_min": round(pm60, 1),
              "avg_shot_s": round(avg_shot, 1), "longest_shot_s": round(longest, 1), "scene_cuts_detected": len(changes)}
    ok_p = vertical or (per_min >= float(bench["changes_per_min"]) and pm60 >= float(bench["changes_per_min_first60"]) and avg_shot <= float(bench["avg_shot_max_s"]))
    checks.append(_check("pacing", "pass" if ok_p else "warn", f"{pacing['visual_changes_per_min']}/min overall, "
                         f"{pacing['first_60s_per_min']}/min first 60 s, avg shot {pacing['avg_shot_s']} s", pacing,
                         {k: bench[k] for k in ("changes_per_min", "changes_per_min_first60", "avg_shot_max_s")}))

    # ---- 8 font size as rendered ----
    try:
        font = resolve_font(profile.fonts.primary)
        style = AssStyle("Caption", font, int(round(profile.captions.size_px * H / 1080.0)), outline_w=profile.captions.outline_px)
        fc = render_font_check(style, W, H, frames_dir / "font_check.png")
        ratio = fc.get("ratio")
        ok_f = ratio is not None and 0.8 <= ratio <= 1.25
        checks.append(_check("font_size", "pass" if ok_f else "warn", f"caption glyphs render at {fc['measured_ink_px']} px "
                             f"vs {fc['expected_ink_px']} px expected (ratio {ratio})", fc, "ratio 0.8-1.25",
                             [str((frames_dir / "font_check.png").relative_to(out_dir))]))
    except Exception as e:  # noqa: BLE001
        checks.append(_check("font_size", "warn", f"font check failed: {e!r}"))

    # ---- thumbnail at real sizes, text clear of the face ----
    pkg = work.parent / "07_package" / "metadata.json"
    if label == "long" and pkg.exists():
        meta = json.loads(pkg.read_text())
        th = meta.get("thumbnail") or {}
        sheet = th.get("sheet")
        metrics = th.get("metrics") or {}
        ok_t = not th.get("overlaps_face") and bool(th.get("file")) and Path(th["file"]).exists()
        low_contrast = metrics.get("brightness_contrast", 99) < 40
        frames = []
        if sheet and Path(sheet).exists():
            dst = frames_dir / "thumb_check.png"
            dst.write_bytes(Path(sheet).read_bytes())
            frames.append(str(dst.relative_to(out_dir)))
        checks.append(_check("thumbnail", ("pass" if ok_t else "fail") if not low_contrast else "warn",
                             f"text {'clear of' if not th.get('overlaps_face') else 'ON'} the face; contrast {metrics.get('brightness_contrast')}, "
                             f"colorfulness {metrics.get('colorfulness')}, clutter {metrics.get('clutter_edge_density')}%",
                             {"text": th.get("text"), **metrics}, "text never covers the face; brightness contrast >= 40", frames))
    elif label == "long":
        checks.append(_check("thumbnail", "not_executed", "package stage has not run"))

    # ---- ledger / NOT EXECUTED ----
    not_exec = []
    for tid, desc in TECHNIQUES.items():
        t = edl.techniques.get(tid)
        if t is None or t.status in ("not_executed", "planned", "degraded"):
            status = t.status if t else "planned"
            reason = (t.reason if t and t.reason else "no stage handled it")
            if status == "planned":
                reason = "no stage handled it"
            not_exec.append({"id": tid, "status": status, "description": desc, "reason": reason})
    executed = [{"id": tid, "reason": t.reason, "count": t.count} for tid, t in edl.techniques.items() if t.status == "executed"]
    overall = "fail" if any(c["status"] == "fail" for c in checks) else ("warn" if any(c["status"] == "warn" for c in checks) else "pass")
    return {"label": label, "file": str(final), "duration": D, "size": [W, H], "overall": overall, "checks": checks,
            "executed": executed, "not_executed": not_exec}


def _markdown(rep: dict[str, Any], hand_edited: bool) -> str:
    L = [f"# QA report: {rep['label']}  ({rep['overall'].upper()})", "",
         f"- File: `{rep['file']}`", f"- Duration: {rep['duration']:.2f} s, {rep['size'][0]}x{rep['size'][1]}",
         f"- EDL hand-edited after planning: {'yes' if hand_edited else 'no'}", "", "## Checks", "",
         "| Check | Status | Summary | Target |", "|---|---|---|---|"]
    for c in rep["checks"]:
        L.append(f"| {c['id']} | **{c['status']}** | {c['summary']} | {c['target'] if c['target'] is not None else ''} |")
    L += ["", "## Frames", ""]
    for c in rep["checks"]:
        for f in c["frames"]:
            L.append(f"- {c['id']}: `{f}`")
    L += ["", "## Executed techniques", ""]
    for e in rep["executed"]:
        L.append(f"- {e['id']}: {e['reason'] or ''}")
    L += ["", "## NOT EXECUTED", "", "Every skill technique that was not applied, and why:", ""]
    for n in rep["not_executed"]:
        L.append(f"- **{n['id']}** ({n['status']}): {n['description']}. Reason: {n['reason']}")
    return "\n".join(L) + "\n"


def run(project: Project, settings: Settings, profile: Profile, log: StageLog | None = None) -> dict[str, Any]:
    log = log or project.log("verify")
    work = project.dir("render")
    final = work / "final.mp4"
    project.begin("verify", file_hash(final) if final.exists() else None)
    try:
        if not final.exists():
            raise FileNotFoundError("render first: no final.mp4")
        edl = EDL.load(work / "edl.rendered.json")
        track = FaceTrack.load(project.face_track_json) if project.face_track_json.exists() else None
        if track and not track.samples:
            track = None
        src = probe(project.ingest_source)
        out_dir = project.dir("verify")
        rep = verify_output(final, work, out_dir, edl, profile, track, src.width, log, label="long")
        reports = {"long": rep}
        shorts_dir = work / "shorts"
        if shorts_dir.exists():
            for sd in sorted(p for p in shorts_dir.iterdir() if p.is_dir() and (p / "final.mp4").exists()):
                sedl = EDL.load(sd / "edl.rendered.json") if (sd / "edl.rendered.json").exists() else edl
                reports[sd.name] = verify_output(sd / "final.mp4", sd, out_dir, sedl, profile, track, src.width, log,
                                                 vertical=True, label=sd.name)
        hand = project.edl_was_hand_edited()
        overall = "fail" if any(r["overall"] == "fail" for r in reports.values()) else (
            "warn" if any(r["overall"] == "warn" for r in reports.values()) else "pass")
        full = {"overall": overall, "hand_edited_edl": hand, "outputs": reports}
        project.qa_json.write_text(json.dumps(full, indent=1, default=str))
        md = "\n\n".join(_markdown(r, hand) for r in reports.values())
        (out_dir / "qa_report.md").write_text(md)
        project.finish("verify", overall=overall)
        log.done(overall=overall, checks={c["id"]: c["status"] for c in rep["checks"]})
        return full
    except Exception as e:
        project.fail("verify", repr(e))
        log.error("failed", error=repr(e))
        raise
