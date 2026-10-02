"""Picture render: compile the EDL into pieces, render each piece as its own ffmpeg process, concat.

Pieces are split at every zoom boundary and beat so every rendered piece has a static
transform. The timing map is computed before rendering from frame counts, and each
piece's actual frame count is asserted afterwards. Never one big filter graph."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any

from ..edl.resolve import resolve_src
from ..edl.schema import EDL, Card, Segment
from ..edl.transcript import Transcript
from ..log import StageLog
from ..media.faces import FaceTrack, crop_for_zoom
from ..media.ffmpeg import concat_copy, pcm_audio_args, run_ffmpeg, video_encode_args
from ..media.probe import MediaInfo, count_video_frames
from ..media.text import AssDoc, AssStyle, Font, ass_filter
from ..media.timing import TimingMap, frames_between, snap
from ..profile import Profile

MIN_PIECE_S = 0.1


@dataclass
class Piece:
    id: str
    kind: str                                  # source | montage | card
    src_in: float | None = None
    src_out: float | None = None
    rate: float = 1.0
    crop: tuple[int, int, int, int] | None = None
    hold: float = 0.0                          # seconds of frozen last frame appended
    hold_kind: str | None = None               # beat | vo
    hold_ref: str | None = None                # id of the beat / vo slot
    card: dict[str, Any] | None = None
    audio_db: float | None = None              # montage: None = silent
    segment: str | None = None
    frames: int = 0
    hold_frames: int = 0
    out_in: float = 0.0
    file: str | None = None
    zoom: str | None = None
    punch: bool = False
    crop_expr: tuple[str, str, int, int] | None = None     # vertical: x expr, y expr, w, h (face-tracked path)
    vertical_blur: bool = False                             # vertical: blurred-letterbox fallback (no face)

    @property
    def dur(self) -> float:
        return 0.0 if self.src_in is None else (self.src_out - self.src_in) / self.rate  # type: ignore[operator]


@dataclass
class Compiled:
    pieces: list[Piece]
    timing: TimingMap
    events: list[dict[str, Any]] = field(default_factory=list)   # derived SFX / fills in out time
    notes: list[str] = field(default_factory=list)


def montage_chunks(seg: Segment) -> list[tuple[float, float]]:
    """Evenly spaced chunks across the range so every stage of progress is represented (montage.py)."""
    m = seg.montage
    assert m is not None
    x, b = seg.src_in, seg.src_out
    src_per_chunk = m.chunk_s * m.speed
    n = max(2, int(round(m.target_s / m.chunk_s)))
    k = max(1, n)
    span = b - x
    if span <= src_per_chunk * 1.5:
        return [(x, b)]
    step = (span - src_per_chunk) / max(1, k - 1)
    return [(round(x + i * step, 3), round(min(b, x + i * step + src_per_chunk), 3)) for i in range(k)]


def compile_pieces(edl: EDL, tr: Transcript | None, info: MediaInfo, track: FaceTrack | None,
                   profile: Profile, log: StageLog | None = None, allow_punch: bool = True) -> Compiled:
    fps = info.fps
    W, H = info.width, info.height
    tm = TimingMap(fps)
    pieces: list[Piece] = []
    events: list[dict[str, Any]] = []
    notes: list[str] = []
    cards_by_seg: dict[str, list[Card]] = {}
    for c in edl.cards:
        cards_by_seg.setdefault(c.before_segment, []).append(c)

    # zooms and holds in source time
    zooms: list[tuple[float, float, float, str, str]] = []
    for z in edl.zooms:
        a = resolve_src(z.at, tr, edl)
        if a is None:
            continue
        b = resolve_src(z.end, tr, edl) if z.end else a + (z.dur or 2.0)
        if b is None or b <= a:
            b = a + (z.dur or 2.0)
        zooms.append((a, b, z.scale, z.anchor, z.id))
    holds: list[tuple[float, float, str, str, str | None]] = []   # (t_src, dur, kind, id, sfx)
    for bt in edl.beats:
        t = resolve_src(bt.after, tr, edl)
        if t is not None:
            holds.append((t, bt.dur, "beat", bt.id, bt.sfx))
    for vo in edl.voiceover_slots:
        if vo.file and vo.hold:
            t = resolve_src(vo.at, tr, edl)
            if t is not None:
                holds.append((t, vo.hold, "vo", vo.id, None))

    punch_params = profile.dead_air_params()
    punch_scale = float(punch_params.get("punch", 1.0)) if allow_punch else 1.0
    toggle = 0
    for seg in edl.segments:
        for card in cards_by_seg.get(seg.id, []):
            n = max(1, frames_between(0.0, card.dur, fps))
            p = Piece(id=f"card:{card.id}", kind="card", card=card.model_dump(), frames=n, segment=seg.id)
            p.out_in = tm.out_duration
            tm.append_hold(float(Fraction(n) / fps), None, kind="card", id=p.id)
            pieces.append(p)
            if card.sfx:
                events.append({"type": "sfx", "kind": card.sfx, "out": p.out_in, "ref": card.id, "reason": "card appears"})
        if seg.kind == "montage":
            m = seg.montage
            assert m is not None
            for j, (a, b) in enumerate(montage_chunks(seg)):
                a, b = snap(a, fps), snap(b, fps, "round")
                if b - a < MIN_PIECE_S:
                    continue
                p = Piece(id=f"{seg.id}#{j}", kind="montage", src_in=a, src_out=b, rate=m.speed,
                          audio_db=m.keep_audio_db, segment=seg.id)
                sp = tm.append_source(a, b, rate=m.speed, kind="montage", id=p.id)
                p.frames, p.out_in = sp.frames, sp.out_in
                pieces.append(p)
            continue
        # a-roll: split at zoom boundaries and hold points
        a0, b0 = snap(seg.src_in, fps), snap(seg.src_out, fps, "round")
        cuts = {a0, b0}
        seg_zooms = [(max(a0, za), min(b0, zb), sc, an, zid) for za, zb, sc, an, zid in zooms if zb > a0 and za < b0]
        for za, zb, *_ in seg_zooms:
            cuts.update((snap(za, fps, "round"), snap(zb, fps, "round")))
        seg_holds = [(snap(t, fps, "round"), d, k, i, s) for t, d, k, i, s in holds if a0 < t <= b0]
        for t, *_ in seg_holds:
            cuts.add(t)
        bounds = sorted(c for c in cuts if a0 <= c <= b0)
        use_punch = punch_scale > 1.0 and seg.punch is not None or (punch_scale > 1.0 and seg.punch is None and toggle % 2 == 1)
        scale_p = seg.punch.scale if seg.punch else punch_scale
        anchor_p = seg.punch.anchor if seg.punch else "face"
        k = 0
        for a, b in zip(bounds, bounds[1:]):
            if b - a < MIN_PIECE_S:
                continue
            tol = 0.6 / float(fps)   # piece bounds are frame-snapped; zoom bounds are not
            zoom = next((z for z in seg_zooms if z[0] - tol <= a and b <= z[1] + tol), None)
            crop = None
            zid = None
            punched = False
            if zoom is not None:
                face = track.mean_box(a, b) if track else None
                crop = crop_for_zoom(face, W, H, zoom[2], "top" if zoom[3] != "center" else "center")
                zid = zoom[4]
                if track and face is None:
                    notes.append(f"zoom {zid}: no face in {a:.1f}-{b:.1f}, anchored to upper third")
            elif use_punch:
                face = track.mean_box(a, b) if track else None
                crop = crop_for_zoom(face, W, H, scale_p, "top" if anchor_p != "center" else "center")
                punched = True
            p = Piece(id=f"{seg.id}#{k}", kind="source", src_in=a, src_out=b, crop=crop, segment=seg.id,
                      zoom=zid, punch=punched)
            hold = next((h for h in seg_holds if abs(h[0] - b) < 1e-6), None)
            sp = tm.append_source(a, b, kind="source", id=p.id)
            p.frames, p.out_in = sp.frames, sp.out_in
            if hold is not None:
                hs = tm.append_hold(hold[1], b, kind="hold", id=f"{seg.id}#{k}:hold")
                p.hold, p.hold_kind, p.hold_ref, p.hold_frames = hs.out_dur, hold[2], hold[3], hs.frames
                events.append({"type": "hold", "kind": hold[2], "ref": hold[3], "out": hs.out_in,
                               "out_end": hs.out_out, "src": b})
                if hold[4]:
                    events.append({"type": "sfx", "kind": hold[4], "out": hs.out_in, "ref": hold[3], "reason": "beat fill"})
            pieces.append(p)
            k += 1
        toggle += 1
    return Compiled(pieces, tm, events, notes)


# ---- rendering --------------------------------------------------------------------------

def _card_ass(card: dict[str, Any], W: int, H: int, profile: Profile, font: Font, out: Path) -> Path:
    doc = AssDoc(W, H)
    c = profile.cards
    ref = H / 1080.0
    t_size, s_size = max(12, int(round(c.size_px * ref))), max(10, int(round(c.subtitle_size_px * ref)))
    title = AssStyle("CardTitle", font, t_size, primary=profile.colors.text, outline=profile.colors.bg,
                     outline_w=0, shadow=0, alignment=5, margin_v=0)
    sub = AssStyle("CardSub", font, s_size, primary=profile.colors.muted, outline=profile.colors.bg,
                   outline_w=0, shadow=0, alignment=5, margin_v=0)
    doc.add_style(title)
    doc.add_style(sub)
    dur = float(card.get("dur", 2.5))
    accent = profile.colors.accent.lstrip("#")
    acc_ass = f"&H{accent[4:6]}{accent[2:4]}{accent[0:2]}&"
    num = f"{{\\c{acc_ass}}}{card['number']}  {{\\c&HFFFFFF&}}" if card.get("number") is not None else ""
    glow = "\\blur3" if c.glow else ""
    y = H // 2 - (s_size // 2 if card.get("subtitle") else 0)
    doc.add(0, dur, "CardTitle", f"{{\\an5\\pos({W // 2},{y})\\fad(200,250){glow}}}{num}{card['text']}")
    if card.get("subtitle"):
        doc.add(0.25, dur, "CardSub", f"{{\\an5\\pos({W // 2},{y + t_size})\\fad(250,250)}}{card['subtitle']}")
    return doc.write(out)


def render_piece(p: Piece, src: Path, out_dir: Path, info: MediaInfo, profile: Profile, font: Font,
                 crf: int, preset: str, scale_from: tuple[int, int] | None = None,
                 out_size: tuple[int, int] | None = None, threads: int = 2) -> Path:
    """Render one piece to out_dir/<id>.mkv with exactly p.frames + p.hold_frames video frames."""
    W, H = out_size or (info.width, info.height)
    fps = info.fps_str
    out = out_dir / (p.id.replace(":", "_").replace("#", "_") + ".mkv")
    total_frames = p.frames + p.hold_frames
    total_dur = float(Fraction(total_frames) / info.fps)
    if p.kind == "card":
        assert p.card is not None
        ass = _card_ass(p.card, W, H, profile, font, out.with_suffix(".ass"))
        bg = profile.colors.bg.lstrip("#")
        noise = f",noise=alls={profile.cards.noise}:allf=t" if profile.cards.style == "dark-textured" else ""
        vf = f"{ass_filter(ass, font.path.parent)},format=yuv420p"
        run_ffmpeg(["-f", "lavfi", "-i", f"color=c=0x{bg}:s={W}x{H}:r={fps}:d={total_dur + 1}{noise}",
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                    "-vf", vf, "-frames:v", str(total_frames), "-af", f"atrim=0:{total_dur:.6f}",
                    "-t", f"{total_dur:.6f}", *video_encode_args(crf, preset), *pcm_audio_args(),
                    "-threads", str(threads), str(out)])
        return out
    assert p.src_in is not None and p.src_out is not None
    dur = p.src_out - p.src_in
    vf = [f"fps={fps}"]
    if p.rate != 1.0:
        vf.insert(0, f"setpts=PTS/{p.rate}")
    if p.crop_expr:
        xe, ye, w, h = p.crop_expr
        vf.append(f"crop={w}:{h}:x='{xe}':y='{ye}'")
    elif p.crop:
        x, y, w, h = p.crop
        if scale_from:
            sx, sy = W / scale_from[0], H / scale_from[1]
            x, y, w, h = int(x * sx) // 2 * 2, int(y * sy) // 2 * 2, int(w * sx) // 2 * 2, int(h * sy) // 2 * 2
        vf.append(f"crop={w}:{h}:{x}:{y}")
    if p.vertical_blur:
        # no face: the whole frame scaled to width over a blurred, cover-scaled copy
        vf.append(f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20[bg];"
                  f"[b]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    else:
        vf.append(f"scale={W}:{H}:flags=bicubic,setsar=1")
    vf.append(f"tpad=stop_mode=clone:stop_duration={p.hold + 1.0:.3f}")
    af = ["aresample=48000"]
    if p.kind == "montage":
        af.append("volume=0" if p.audio_db is None else f"volume={p.audio_db}dB")
        if p.rate != 1.0:
            af.append(f"atempo={p.rate}")
    af.append(f"apad=whole_dur={total_dur:.6f}")
    af.append(f"atrim=0:{total_dur:.6f}")
    af.append("afade=t=in:d=0.01")
    af.append(f"afade=t=out:st={max(0.0, total_dur - 0.01):.6f}:d=0.01")
    if p.vertical_blur:
        graph = "[0:v]" + ",".join(vf).replace(",split[a][b];", "split[a][b];").replace("overlay=(W-w)/2:(H-h)/2,", "overlay=(W-w)/2:(H-h)/2,") + "[v]"
        run_ffmpeg(["-ss", f"{p.src_in:.6f}", "-t", f"{dur + 0.5:.6f}", "-i", str(src),
                    "-filter_complex", graph, "-map", "[v]", "-map", "0:a", "-frames:v", str(total_frames),
                    "-af", ",".join(af), *video_encode_args(crf, preset), *pcm_audio_args(), "-threads", str(threads), str(out)])
        return out
    run_ffmpeg(["-ss", f"{p.src_in:.6f}", "-t", f"{dur + 0.5:.6f}", "-i", str(src),
                "-vf", ",".join(vf), "-frames:v", str(total_frames), "-af", ",".join(af),
                *video_encode_args(crf, preset), *pcm_audio_args(), "-threads", str(threads), str(out)])
    return out


def render_timeline(compiled: Compiled, src: Path, out_dir: Path, info: MediaInfo, profile: Profile, font: Font,
                    *, workers: int = 3, crf: int = 18, preset: str = "fast", log: StageLog | None = None,
                    preview_size: tuple[int, int] | None = None, source_size: tuple[int, int] | None = None) -> Path:
    """Render every piece (parallel), assert frame counts, concat to out_dir/timeline.mkv."""
    seg_dir = out_dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    pieces = compiled.pieces
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(render_piece, p, src, seg_dir, info, profile, font, crf, preset,
                          source_size, preview_size): p for p in pieces}
        for f in as_completed(futs):
            p = futs[f]
            p.file = str(f.result())
            done += 1
            if log:
                log.progress(done / max(1, len(pieces)) * 0.9, f"piece {p.id}")
    bad = []
    for p in pieces:
        n = count_video_frames(Path(p.file))  # type: ignore[arg-type]
        if n != p.frames + p.hold_frames:
            bad.append((p.id, p.frames + p.hold_frames, n))
    if bad:
        raise RuntimeError(f"frame count mismatch (predicted, actual): {bad[:5]}")
    timeline = out_dir / ("timeline_preview.mkv" if preview_size else "timeline.mkv")
    concat_copy([Path(p.file) for p in pieces], timeline)  # type: ignore[arg-type]
    (out_dir / "pieces.json").write_text(json.dumps([asdict(p) for p in pieces], indent=1))
    (out_dir / "timing_map.json").write_text(json.dumps(compiled.timing.to_json(), indent=1))
    if log:
        log.progress(1.0, "timeline")
    return timeline
