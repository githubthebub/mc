"""Package: the named final file, metadata (title, description, chapters, tags), a thumbnail built around
the face with text clear of it, the thumb_check sheet, and end-screen reservation."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..config import Settings
from ..edl.schema import EDL
from ..log import StageLog
from ..media.faces import FaceTrack
from ..media.ffmpeg import extract_frame
from ..media.images import sharpness, thumb_metrics, thumb_sheet
from ..media.probe import probe
from ..media.text import Rect, hex_to_rgb, resolve_font, slugify
from ..media.timing import TimingMap
from ..profile import Profile
from ..project import Project, file_hash

THUMB_SIZE = (1280, 720)


def _fmt_ts(t: float) -> str:
    t = int(round(t))
    return f"{t // 60:d}:{t % 60:02d}" if t < 3600 else f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}"


def pick_thumbnail_frame(final: Path, track: FaceTrack | None, tm: TimingMap, work: Path,
                         prefer_src_t: float | None = None) -> tuple[Path, Rect | None, float]:
    """The sharpest, largest-face frame among candidates spread over the video (or the requested one)."""
    cands: list[float] = []
    if prefer_src_t is not None:
        t = tm.to_out(prefer_src_t)
        if t is not None:
            cands.append(t)
    D = tm.out_duration
    cands += [D * f for f in (0.05, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9)]
    best: tuple[float, Path, Rect | None, float] | None = None
    for i, t in enumerate(cands):
        f = extract_frame(final, t, work / f"thumb_cand_{i}.png")
        im = Image.open(f)
        face = None
        ts = tm.to_src(t)
        if track and ts is not None:
            b = track.box_at(ts)
            if b:
                sx = im.width / track.width
                face = Rect(b.x * sx, b.y * sx, b.w * sx, b.h * sx)
        score = sharpness(f, face.as_int() if face else None) * (1 + (face.w * face.h / (im.width * im.height) * 20 if face else 0))
        if prefer_src_t is not None and i == 0:
            score *= 10
        if best is None or score > best[0]:
            best = (score, f, face, t)
    assert best is not None
    return best[1], best[2], best[3]


def compose_thumbnail(frame: Path, face: Rect | None, text: str | None, profile: Profile, out: Path) -> dict[str, Any]:
    """Spotlight the face, darken and warm/cool the rest, put short text in the largest empty region."""
    im = Image.open(frame).convert("RGB").resize(THUMB_SIZE, Image.LANCZOS)
    W, H = im.size
    sx, sy = W / Image.open(frame).width, H / Image.open(frame).height
    fr = Rect(face.x * sx, face.y * sy, face.w * sx, face.h * sy) if face else None
    mood = profile.thumbnail.mood_color
    tint = {"warm": (255, 120, 60), "cool": (60, 140, 255), "neutral": (128, 128, 128)}[mood]
    # vignette-style darkening of everything but the face
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    if fr:
        pad = fr.w * 0.6
        md.ellipse([fr.x - pad, fr.y - pad * 1.2, fr.x2 + pad, fr.y2 + pad * 1.6], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(60))
    dark = Image.blend(im, Image.new("RGB", (W, H), (0, 0, 0)), 0.45)
    washed = Image.blend(dark, Image.new("RGB", (W, H), tint), 0.12)
    comp = Image.composite(im, washed, mask)
    placement: dict[str, Any] = {"text": text, "box": None, "overlaps_face": False}
    if text:
        words = text.split()[:profile.thumbnail.text_max_words]
        text = " ".join(words).upper()
        font = resolve_font(profile.fonts.primary)
        size = profile.thumbnail.text_size_px
        f = ImageFont.truetype(str(font.path), size)
        while f.getbbox(text)[2] > W * 0.55 and size > 60:
            size -= 8
            f = ImageFont.truetype(str(font.path), size)
        l, t, r, b = f.getbbox(text)
        tw, th = r - l, b - t
        # candidate regions: left or right of the face, then top/bottom bands; pick the one farthest from the face
        cands = [(60, H - th - 90), (60, 70), (W - tw - 60, H - th - 90), (W - tw - 60, 70), ((W - tw) // 2, H - th - 70)]

        def dist(c: tuple[int, int]) -> float:
            if not fr:
                return 0.0
            r_ = Rect(c[0], c[1], tw, th)
            if r_.intersects(fr, 20):
                return -1.0
            return abs((r_.x + r_.w / 2) - (fr.x + fr.w / 2)) + abs((r_.y + r_.h / 2) - (fr.y + fr.h / 2))
        x, y = max(cands, key=dist)
        box = Rect(x, y, tw, th)
        placement["box"] = box.as_int()
        placement["overlaps_face"] = bool(fr and box.intersects(fr))
        d = ImageDraw.Draw(comp)
        accent = hex_to_rgb(profile.colors.accent)
        for dx in (-5, 5):
            for dy in (-5, 5):
                d.text((x + dx - l, y + dy - t), text, font=f, fill=(0, 0, 0))
        d.text((x - l, y - t), text, font=f, fill=(255, 255, 255))
        # accent underline under the text
        d.rectangle([x, y + th + 14, x + tw, y + th + 26], fill=accent)
    out.parent.mkdir(parents=True, exist_ok=True)
    comp.save(out, quality=92)
    placement["face"] = fr.as_int() if fr else None
    return placement


def run(project: Project, settings: Settings, profile: Profile, log: StageLog | None = None) -> dict[str, Any]:
    log = log or project.log("package")
    work = project.dir("render")
    final = work / "final.mp4"
    project.begin("package", file_hash(final) if final.exists() else None)
    try:
        if not final.exists():
            raise FileNotFoundError("render first: no final.mp4")
        edl = EDL.load(work / "edl.rendered.json")
        resolved = json.loads((work / "resolved.json").read_text())
        tm = TimingMap.from_json(json.loads((work / "timing_map.json").read_text()))
        track = FaceTrack.load(project.face_track_json) if project.face_track_json.exists() else None
        if track and not track.samples:
            track = None
        out = project.dir("package")
        title = edl.title.chosen if edl.title else project.name
        slug = slugify(title)
        dst = out / f"{slug}.mp4"
        shutil.copy2(final, dst)
        # chapters: YouTube needs the first at 0:00 and at least three, 10 s apart
        chapters = sorted(resolved.get("chapters", []), key=lambda c: c["out"])
        ch_lines = []
        if chapters:
            if chapters[0]["out"] > 0.5:
                chapters.insert(0, {"title": "Intro", "out": 0.0})
            chapters[0]["out"] = 0.0
            ch_lines = [f"{_fmt_ts(c['out'])} {c['title']}" for c in chapters]
        vo_lines = [f"[{v.id}] {v.line}  ({v.reason})" for v in edl.voiceover_slots if not v.file]
        desc = "\n".join([edl.title.rationale or "" if edl.title else "", "", "Chapters:" if ch_lines else "", *ch_lines]).strip()
        meta = {"title": title, "alternatives": edl.title.alternatives if edl.title else [], "description": desc,
                "chapters": chapters, "tags": [], "file": str(dst), "duration": tm.out_duration,
                "voiceover_lines_to_record": vo_lines,
                "end_screen": {"seconds": profile.end_screen.seconds, "starts_at": max(0.0, tm.out_duration - profile.end_screen.seconds),
                               "reserve_zone": profile.end_screen.reserve_zone,
                               "note": "add the end-screen element in YouTube Studio inside this window; captions avoid the reserved zone"}}
        # thumbnail
        spec = edl.thumbnail
        frame, face, t_used = pick_thumbnail_frame(final, track, tm, out, spec.frame_src_t if spec else None)
        text = (spec.text if spec else None) or (title.split(":")[0] if len(title.split()) <= 3 else None)
        placement = compose_thumbnail(frame, face, text, profile, out / "thumbnail.png")
        placement["frame_out_t"] = t_used
        metrics = thumb_metrics(out / "thumbnail.png")
        thumb_sheet(out / "thumbnail.png", [], out / "thumb_check.png")
        meta["thumbnail"] = {"file": str(out / "thumbnail.png"), "sheet": str(out / "thumb_check.png"),
                             "metrics": metrics, **placement}
        for f in out.glob("thumb_cand_*.png"):
            f.unlink()
        (out / "metadata.json").write_text(json.dumps(meta, indent=1))
        (out / "description.txt").write_text(desc + "\n")
        edl.mark("thumbnail_spotlight", "degraded" if placement["overlaps_face"] else "executed",
                 ("text overlaps the face box" if placement["overlaps_face"] else
                  f"face spotlight from frame at {t_used:.1f}s, text '{text}' clear of the face") if face else
                 "no face: text-only composition", "package")
        edl.mark("title_driving_question", "executed" if edl.title else "not_executed",
                 f"'{title}'" if edl.title else "no title in the EDL (planner did not run)", "package")
        edl.mark("end_screen_handoff", "executed", f"last {profile.end_screen.seconds:.0f} s reserved ({profile.end_screen.reserve_zone}); no outro added", "package")
        edl.save(work / "edl.rendered.json")
        project.finish("package", file=str(dst), title=title)
        log.done(file=str(dst), thumbnail=str(out / "thumbnail.png"))
        return meta
    except Exception as e:
        project.fail("package", repr(e))
        log.error("failed", error=repr(e))
        raise
