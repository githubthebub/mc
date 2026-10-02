"""Graphics: key-word captions, labels and beat fills as one ASS pass; still and B-roll overlays
composited per piece (bounded filter graphs), sliding in with easing and a whoosh."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..edl.resolve import resolve, resolve_range
from ..edl.schema import EDL
from ..edl.transcript import Transcript
from ..log import StageLog
from ..media.faces import FaceTrack
from ..media.ffmpeg import concat_copy, pcm_audio_args, run_ffmpeg, video_encode_args
from ..media.images import focus_clip
from ..media.probe import MediaInfo
from ..media.text import AssDoc, AssStyle, Font, Rect, ass_color, ass_escape, ass_filter, measure_text, place_text, safe_zone
from ..media.timing import TimingMap
from ..profile import Profile
from .picture import Piece

CAPTION_DEFAULT_S = 1.6


@dataclass
class Placement:
    id: str
    kind: str
    out_in: float
    out_out: float
    box: tuple[int, int, int, int]
    face_box: tuple[int, int, int, int] | None
    overlaps_face: bool
    inside_safe: bool
    text: str


@dataclass
class GraphicsResult:
    video: Path
    ass: Path | None
    placements: list[Placement] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    overlays_rendered: int = 0


def _face_box_out(track: FaceTrack | None, tm: TimingMap, t_out: float, scale: float) -> Rect | None:
    if track is None:
        return None
    t_src = tm.to_src(t_out)
    if t_src is None:
        return None
    b = track.box_at(t_src)
    if b is None:
        return None
    return Rect(b.x * scale, b.y * scale, b.w * scale, b.h * scale)


def _styled_words(words: list[str], emphasis: int | None, accent: str, accent_words: bool) -> str:
    parts = []
    acc = ass_color(accent)
    for i, w in enumerate(words):
        t = ass_escape(w)
        if accent_words and emphasis is not None and i == emphasis:
            parts.append(f"{{\\c{acc}\\blur2}}{t}{{\\c&HFFFFFF&\\blur0}}")
        else:
            parts.append(t)
    return " ".join(parts)


def build_ass(edl: EDL, tr: Transcript | None, tm: TimingMap, track: FaceTrack | None, info: MediaInfo,
              profile: Profile, font: Font, out_size: tuple[int, int], hold_events: list[dict[str, Any]],
              vertical: bool = False) -> tuple[AssDoc, list[Placement]]:
    W, H = out_size
    scale = W / info.width          # source px -> output px (face boxes)
    ref = H / 1080.0                # profile sizes are specified for 1080p
    doc = AssDoc(W, H)
    cap_cfg = profile.captions
    size = max(12, int(round(cap_cfg.size_px * ref)))
    cap = AssStyle("Caption", font, size, primary=profile.colors.text, outline="#000000", outline_w=cap_cfg.outline_px,
                   shadow=0, alignment=7, margin_l=0, margin_r=0, margin_v=0)
    lab = AssStyle("Label", font, max(12, int(size * 0.7)), primary=profile.colors.text, outline="#000000",
                   outline_w=cap_cfg.outline_px, back=profile.colors.bg, back_alpha=0x40, border_style=3,
                   alignment=7, margin_l=0, margin_r=0, margin_v=0)
    doc.add_style(cap)
    doc.add_style(lab)
    zone = safe_zone(W, H, vertical)
    placements: list[Placement] = []
    fade = cap_cfg.fade_ms

    def place(id_: str, kind: str, style: AssStyle, s: float, e: float, text_plain: str, text_ass: str,
              prefer: str) -> None:
        tw, th = measure_text(font, style.size, text_plain)
        tw += int(style.outline_w * 2)
        th += int(style.outline_w * 2)
        mid = (s + e) / 2
        face = _face_box_out(track, tm, mid, scale)
        avoid = [face] if face else []
        x, y = place_text((tw, th), zone, avoid, prefer=prefer)
        box = Rect(x, y, tw, th)
        ok_face = not (face and box.intersects(face))
        placements.append(Placement(id_, kind, s, e, box.as_int(), face.as_int() if face else None,
                                    not ok_face, box.inside(zone), text_plain))
        doc.add(s, e, style.name, f"{{\\an7\\pos({int(x)},{int(y)})\\fad({fade},{fade})}}{text_ass}")

    for c in edl.captions:
        s, e = resolve_range(c.at, c.end, c.dur, tr, edl, tm, CAPTION_DEFAULT_S)
        words = c.words[:cap_cfg.max_words]
        place(c.id, "caption", cap, s.out, e.out, " ".join(words),
              _styled_words(words, c.emphasis, profile.colors.accent, cap_cfg.accent_words), cap_cfg.position)
    for ev in hold_events:
        if ev.get("kind") != "beat":
            continue
        beat = next((b for b in edl.beats if b.id == ev.get("ref")), None)
        if beat and beat.fill == "caption" and beat.text:
            words = beat.text.split()[:cap_cfg.max_words]
            place(f"beat:{beat.id}", "beat_caption", cap, ev["out"], ev["out_end"], " ".join(words),
                  _styled_words(words, len(words) - 1, profile.colors.accent, cap_cfg.accent_words), "middle")
    return doc, placements


def _slide_expr(motion: str, W: int, w: int, x_final: int, t0: float, d: float = 0.35) -> str:
    if motion == "slide_right":
        return f"if(lt(t,{t0}),{W},if(lt(t,{t0 + d}),{W}-({W}-{x_final})*(1-pow(1-(t-{t0})/{d},3)),{x_final}))"
    if motion == "slide_left":
        return f"if(lt(t,{t0}),{-w},if(lt(t,{t0 + d}),{-w}+({x_final}+{w})*(1-pow(1-(t-{t0})/{d},3)),{x_final}))"
    return str(x_final)


def composite_overlays(edl: EDL, tr: Transcript | None, tm: TimingMap, pieces: list[Piece], info: MediaInfo,
                       profile: Profile, out_size: tuple[int, int], work: Path, assets_root: Path,
                       crf: int, preset: str, log: StageLog | None = None) -> tuple[list[dict[str, Any]], list[str], int]:
    """Replace piece files with overlay-composited versions. Returns (events, notes, count)."""
    W, H = out_size
    events: list[dict[str, Any]] = []
    notes: list[str] = []
    n_done = 0
    by_piece: dict[str, list[tuple[float, float, Any]]] = {}
    for ov in edl.overlays:
        r = resolve(ov.at, tr, edl, tm)
        s, e = r.out, r.out + ov.dur
        asset = (assets_root / ov.asset) if not Path(ov.asset).is_absolute() else Path(ov.asset)
        if not asset.exists():
            notes.append(f"overlay {ov.id}: asset not found: {asset}")
            continue
        for p in pieces:
            p_in, p_out = p.out_in, p.out_in + float((p.frames + p.hold_frames) / float(info.fps))
            if s < p_out and e > p_in:
                by_piece.setdefault(p.id, []).append((max(s, p_in) - p_in, min(e, p_out) - p_in, (ov, asset, s)))
        if ov.sfx:
            events.append({"type": "sfx", "kind": ov.sfx, "out": s, "ref": ov.id, "reason": "overlay moves in"})
    ov_dir = work / "overlays"
    ov_dir.mkdir(parents=True, exist_ok=True)
    clip_cache: dict[str, Path] = {}
    for p in pieces:
        items = by_piece.get(p.id)
        if not items:
            continue
        inputs = ["-i", str(p.file)]
        fc = []
        prev = "[0:v]"
        for k, (t0, t1, (ov, asset, s_abs)) in enumerate(sorted(items, key=lambda it: it[0])):
            if ov.kind == "still":
                key = ov.id
                if key not in clip_cache:
                    clip = ov_dir / f"{ov.id}.mp4"
                    focus = ov.focus or (0.2, 0.2, 0.6, 0.6)
                    focus_clip(asset, clip, focus, dur=ov.dur, size=(W, H), tint=ov.tint, glow=ov.glow,
                               mark=ov.mark, accent="0x" + profile.colors.accent.lstrip("#"), fps=int(round(float(info.fps))),
                               crf=crf, preset=preset)
                    clip_cache[key] = clip
                src_clip = clip_cache[key]
            else:
                src_clip = asset
            # the overlay clip starts at its own time 0 at absolute s_abs; inside this piece it starts at t0 and
            # may already be (t0 - local start) seconds in when the piece starts
            skip = max(0.0, (p.out_in + t0) - s_abs)
            inputs += ["-ss", f"{skip:.3f}", "-t", f"{t1 - t0:.3f}", "-i", str(src_clip)]
            idx = k + 1
            fc.append(f"[{idx}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
                      f"fps={info.fps_str},setpts=PTS-STARTPTS+{t0:.3f}/TB[o{k}]")
            x_expr = _slide_expr(ov.motion, W, W, 0, t0) if skip == 0 else "0"
            fc.append(f"{prev}[o{k}]overlay=x='{x_expr}':y=0:enable='between(t,{t0:.3f},{t1:.3f})':eof_action=pass[v{k}]")
            prev = f"[v{k}]"
            n_done += 1
        out = Path(p.file).with_name(Path(p.file).stem + "_ov.mkv")
        run_ffmpeg([*inputs, "-filter_complex", ";".join(fc), "-map", prev, "-map", "0:a",
                    "-frames:v", str(p.frames + p.hold_frames), *video_encode_args(crf, preset), *pcm_audio_args(), str(out)])
        p.file = str(out)
        if log:
            log.info("overlays composited", piece=p.id, count=len(items))
    return events, notes, n_done


def render_graphics(edl: EDL, tr: Transcript | None, tm: TimingMap, pieces: list[Piece], track: FaceTrack | None,
                    info: MediaInfo, profile: Profile, font: Font, out_size: tuple[int, int], work: Path,
                    assets_root: Path, hold_events: list[dict[str, Any]], *, crf: int, preset: str,
                    name: str = "graphics", vertical: bool = False, extra_doc: AssDoc | None = None,
                    log: StageLog | None = None) -> GraphicsResult:
    """ASS captions over the concatenated timeline, after per-piece overlays. Writes work/<name>.mkv."""
    ov_events, notes, n_ov = composite_overlays(edl, tr, tm, pieces, info, profile, out_size, work, assets_root,
                                                crf, preset, log)
    timeline = work / f"{name}_timeline.mkv"
    concat_copy([Path(p.file) for p in pieces], timeline)  # type: ignore[arg-type]
    doc, placements = build_ass(edl, tr, tm, track, info, profile, font, out_size, hold_events, vertical)
    if extra_doc is not None:
        for s in extra_doc.styles:
            doc.add_style(s)
        doc.events.extend(extra_doc.events)
    out = work / f"{name}.mkv"
    ass_path: Path | None = None
    if doc.events:
        ass_path = doc.write(work / f"{name}.ass")
        vf = ass_filter(ass_path, font.path.parent)
        if extra_doc is not None:   # preview: burn the output timecode
            vf += f",drawtext=text='out %{{pts\\:hms}}':x=w-tw-8:y=8:fontsize={max(12, int(out_size[1] * 0.04))}:fontcolor=white:box=1:boxcolor=black@0.5"
        run_ffmpeg(["-i", str(timeline), "-vf", vf, "-c:a", "copy",
                    *video_encode_args(crf, preset), str(out)],
                   total_duration=tm.out_duration, on_progress=(lambda f: log.progress(f, "captions")) if log else None)
    else:
        if out.exists() or out.is_symlink():
            out.unlink()
        os.symlink(timeline, out)
    (work / f"{name}_placements.json").write_text(json.dumps([p.__dict__ for p in placements], indent=1, default=list))
    return GraphicsResult(out, ass_path, placements, ov_events, notes, n_ov)
