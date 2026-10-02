"""Vertical (9:16) rendering for Shorts: face-tracked crop paths per piece, word-by-word captions in
the safe zone that never cover the face, and the persistent context label."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..edl.transcript import Transcript
from ..media.faces import FaceTrack
from ..media.probe import MediaInfo
from ..media.text import AssDoc, AssStyle, Font, Rect, ass_color, ass_escape, measure_text, place_text, safe_zone
from ..media.timing import TimingMap
from ..profile import Profile
from .picture import Piece

KEYFRAME_S = 0.5
FACE_Y_IN_CROP = 0.40        # the face center sits at 40% of the crop height
STATIC_TOLERANCE = 0.02      # a path that moves less than 2% of the crop width is made static


@dataclass
class CropPath:
    piece: str
    w: int
    h: int
    keys: list[tuple[float, int, int]]      # (piece-local t, x, y)

    def expr(self) -> tuple[str, str]:
        def build(idx: int) -> str:
            if len(self.keys) == 1:
                return str(self.keys[0][idx])
            e = str(self.keys[-1][idx])
            for (t0, *v0), (t1, *v1) in reversed(list(zip(self.keys, self.keys[1:]))):
                a, b = v0[idx - 1], v1[idx - 1]
                seg = f"{a}+({b}-{a})*(t-{t0:.3f})/{max(1e-3, t1 - t0):.3f}"
                e = f"if(lt(t,{t1:.3f}),{seg},{e})"
            return e
        return build(1), build(2)


def crop_paths(pieces: list[Piece], track: FaceTrack | None, info: MediaInfo, out_size: tuple[int, int]) -> list[dict[str, Any]]:
    """Attach a face-following crop path (or the blurred-letterbox fallback) to every source piece.
    Returns the paths as keyframes in output time for QA."""
    W, H = info.width, info.height
    ow, oh = out_size
    base_w = int(H * ow / oh) // 2 * 2
    if base_w > W:                      # a source narrower than 9:16: no horizontal room
        base_w = W
    base_h = int(base_w * oh / ow) // 2 * 2
    report = []
    for p in pieces:
        if p.src_in is None:
            continue
        scale = 1.0
        if p.crop is not None and p.zoom:       # an emphasis zoom: a tighter window
            scale = W / max(1, p.crop[2])
        cw, ch = int(base_w / scale) // 2 * 2, int(base_h / scale) // 2 * 2
        p.crop = None
        keys: list[tuple[float, int, int]] = []
        if track is not None and track.samples:
            t = p.src_in
            while True:
                b = track.box_at(min(t, p.src_out))
                if b is not None:
                    x = int(min(max(0, b.cx - cw / 2), W - cw)) // 2 * 2
                    y = int(min(max(0, b.cy - ch * FACE_Y_IN_CROP), H - ch)) // 2 * 2
                    keys.append((round(t - p.src_in, 3), x, y))
                if t >= p.src_out:
                    break
                t = min(p.src_out, t + KEYFRAME_S)
        if not keys:
            p.vertical_blur = True
            report.append({"piece": p.id, "out_in": p.out_in, "mode": "blur-letterbox", "keys": []})
            continue
        xs, ys = [k[1] for k in keys], [k[2] for k in keys]
        if max(xs) - min(xs) < STATIC_TOLERANCE * cw and max(ys) - min(ys) < STATIC_TOLERANCE * ch:
            keys = [(0.0, int(sum(xs) / len(xs)) // 2 * 2, int(sum(ys) / len(ys)) // 2 * 2)]
        path = CropPath(p.id, cw, ch, keys)
        xe, ye = path.expr()
        p.crop_expr = (xe, ye, cw, ch)
        report.append({"piece": p.id, "out_in": p.out_in, "mode": "face-tracked", "w": cw, "h": ch,
                       "keys": [(round(p.out_in + t, 3), x, y) for t, x, y in keys]})
    return report


def face_in_vertical_output(track: FaceTrack | None, tm: TimingMap, t_out: float, crop_report: list[dict[str, Any]],
                            info: MediaInfo, out_size: tuple[int, int]) -> Rect | None:
    """The face box in the vertical output's pixel coordinates at output time t_out."""
    W, H = out_size
    if track is None:
        return None
    sp = tm.span_at_out(t_out)
    if sp is None or sp.src_in is None:
        return None
    paths = {r["piece"]: r for r in crop_report}
    r = paths.get(sp.id or "")
    ts = tm.to_src(t_out)
    b = track.box_at(ts) if ts is not None else None
    if b is None:
        return None
    if r and r.get("mode") == "face-tracked":
        keys = r["keys"]
        x, y = keys[0][1], keys[0][2]
        for (t0, x0, y0), (t1, x1, y1) in zip(keys, keys[1:]):
            if t0 <= t_out <= t1:
                f = (t_out - t0) / max(1e-3, t1 - t0)
                x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
                break
            if t_out > t1:
                x, y = x1, y1
        sc = W / r["w"]
        return Rect((b.x - x) * sc, (b.y - y) * sc, b.w * sc, b.h * sc)
    sc = W / info.width
    y0 = (H - info.height * sc) / 2
    return Rect(b.x * sc, y0 + b.y * sc, b.w * sc, b.h * sc)


def word_captions(tr: Transcript, tm: TimingMap, track: FaceTrack | None, info: MediaInfo, profile: Profile,
                  font: Font, out_size: tuple[int, int], crop_report: list[dict[str, Any]],
                  context_label: str | None) -> tuple[AssDoc, list[dict[str, Any]]]:
    """Karaoke-style captions: lines of up to three words, the spoken word in the accent color, placed in
    the vertical safe zone clear of the face. Plus the context label pill at the top."""
    W, H = out_size
    ref = W / 1080.0
    doc = AssDoc(W, H)
    size = max(24, int(round(profile.shorts.caption_size_px * ref)))
    cap = AssStyle("Word", font, size, primary="#FFFFFF", outline="#000000", outline_w=max(2.0, 3.0 * ref), shadow=0,
                   alignment=7, margin_l=0, margin_r=0, margin_v=0)
    lab = AssStyle("Context", font, max(18, int(size * 0.55)), primary="#FFFFFF", outline=profile.colors.accent,
                   back=profile.colors.accent, back_alpha=0, border_style=3, outline_w=max(6.0, 10 * ref), shadow=0,
                   alignment=8, margin_l=0, margin_r=0, margin_v=0)
    doc.add_style(cap)
    doc.add_style(lab)
    zone = safe_zone(W, H, vertical=True)
    acc = ass_color(profile.colors.accent)
    placements: list[dict[str, Any]] = []
    def face_out(t_out: float) -> Rect | None:
        return face_in_vertical_output(track, tm, t_out, crop_report, info, out_size)

    # group kept words into lines
    words = [w for w in tr.words if tm.to_out(w.t0) is not None]
    lines: list[list] = []
    cur: list = []
    for w in words:
        if cur and (len(cur) >= profile.captions.max_words or w.s != cur[-1].s or
                    measure_text(font, size, " ".join(x.text for x in cur + [w]))[0] > zone.w * 0.9):
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    for li, line in enumerate(lines):
        text_plain = " ".join(w.text for w in line)
        tw, th = measure_text(font, size, text_plain)
        tw += int(cap.outline_w * 2)
        th += int(cap.outline_w * 2)
        t_start = tm.to_out(line[0].t0) or 0.0
        t_end = (tm.to_out(line[-1].t1) or tm.to_out_prev(line[-1].t1)) + 0.15
        if li + 1 < len(lines):      # never overlap the next line
            nxt = tm.to_out(lines[li + 1][0].t0)
            if nxt is not None:
                t_end = min(t_end, nxt)
        face = face_out((t_start + t_end) / 2)
        x, y = place_text((tw, th), zone, [face] if face else [], prefer="lower")
        box = Rect(x, y, tw, th)
        placements.append({"id": f"line{li}", "kind": "word_caption", "out_in": t_start, "out_out": t_end,
                           "box": box.as_int(), "face_box": face.as_int() if face else None,
                           "overlaps_face": bool(face and box.intersects(face)), "inside_safe": box.inside(zone),
                           "text": text_plain})
        for k, w in enumerate(line):
            s = tm.to_out(w.t0)
            e = tm.to_out(line[k + 1].t0) if k + 1 < len(line) else None
            if s is None:
                continue
            if e is None or e <= s:
                e = t_end
            parts = [f"{{\\c{acc}}}{ass_escape(x.text)}{{\\c&HFFFFFF&}}" if j == k else ass_escape(x.text) for j, x in enumerate(line)]
            doc.add(s, e, "Word", f"{{\\an7\\pos({int(x)},{int(y)})}}" + " ".join(parts))
    if context_label:
        doc.add(0.0, tm.out_duration, "Context", f"{{\\an8\\pos({W // 2},{int(H * 0.11)})}}{ass_escape(context_label)}", layer=2)
        lw, lh = measure_text(font, lab.size, context_label)
        placements.append({"id": "context_label", "kind": "label", "out_in": 0.0, "out_out": tm.out_duration,
                           "box": (W // 2 - lw // 2, int(H * 0.11), lw, lh), "face_box": None, "overlaps_face": False,
                           "inside_safe": True, "text": context_label})
    return doc, placements
