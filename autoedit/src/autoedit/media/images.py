"""Stills and thumbnails: guided-attention clips (focus_image.py), thumbnail checks (thumb_check.py),
frame grabs with annotation boxes for the QA report."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .ffmpeg import run_ffmpeg, video_encode_args

TINTS = {"red": "colorchannelmixer=rr=1:gg=0.5:bb=0.5",
         "green": "colorchannelmixer=rr=0.65:gg=1:bb=0.65",
         "yellow": "colorchannelmixer=rr=1:gg=0.95:bb=0.5"}


def focus_clip(img: str | Path, out: str | Path, focus: tuple[float, float, float, float], *,
               dur: float = 4.0, size: tuple[int, int] = (1920, 1080), mode: str = "both",
               tint: str | None = None, glow: bool = False, mark: str | None = None,
               push: float = 1.08, reveal: float = 0.6, accent: str = "0x3CC8FF", fps: int = 30,
               crf: int = 18, preset: str = "fast") -> Path:
    """Turn a still into an attention-guiding clip: push-in, darken/blur surroundings, glow, tint, box."""
    W, H = size
    fx, fy, fw, fh = focus
    X, Y = int(fx * W), int(fy * H)
    FW, FH = int(fw * W) // 2 * 2, int(fh * H) // 2 * 2
    FW, FH = max(2, FW), max(2, FH)
    surround = []
    if mode in ("darken", "both"):
        surround.append("eq=brightness=-0.22:saturation=0.7")
    if mode in ("blur", "both"):
        surround.append("boxblur=12:2")
    fc = [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
          f"fps={fps},trim=duration={dur}" + ("," + TINTS[tint] if tint else "") + ",format=yuva420p,split=3[plain][d][f]",
          f"[d]{','.join(surround) or 'null'},fade=t=in:st={reveal}:d=0.4:alpha=1[dark]",
          "[plain][dark]overlay[bg]"]
    fg = f"[f]crop={FW}:{FH}:{X}:{Y}"
    if glow:
        fc.append(fg + ",format=gbrap,split[f1][f2]")
        fc.append("[f2]boxblur=8:1[g]")
        fc.append("[f1][g]blend=all_mode=screen:all_opacity=0.3,format=yuva420p[fgc]")
    else:
        fc.append(fg + "[fgc]")
    fc.append(f"[fgc]fade=t=in:st={reveal}:d=0.01:alpha=1[fgf]")
    chain = f"[bg][fgf]overlay={X}:{Y}"
    if mark == "box":
        chain += f",drawbox=x={X - 4}:y={Y - 4}:w={FW + 8}:h={FH + 8}:color={accent}:t=5:enable='gte(t,{reveal + 0.15})'"
    elif mark == "underline":
        chain += f",drawbox=x={X}:y={Y + FH + 6}:w={FW}:h=6:color={accent}:t=fill:enable='gte(t,{reveal + 0.15})'"
    cx, cy = X + FW / 2, Y + FH / 2
    k = (push - 1) / dur
    chain += (f",scale=w='trunc({W}*(1+{k}*t)/2)*2':h=-2:eval=frame,"
              f"crop={W}:{H}:x='min(max(0,{cx}*(iw/{W})-{W}/2),iw-{W})':y='min(max(0,{cy}*(ih/{H})-{H}/2),ih-{H})',"
              f"format=yuv420p[v]")
    fc.append(chain)
    out = Path(out)
    run_ffmpeg(["-loop", "1", "-i", str(img), "-filter_complex", ";".join(fc), "-map", "[v]",
                "-t", str(dur), *video_encode_args(crf, preset), str(out)])
    return out


# ---- thumbnails -------------------------------------------------------------------

THUMB_SIZES = [("mobile feed", 360, 202), ("desktop home", 246, 138), ("sidebar", 168, 94)]


def thumb_metrics(path: str | Path) -> dict[str, float]:
    """Brightness contrast (luma std), colorfulness (Hasler-Susstrunk), clutter proxy (edge density)."""
    im = Image.open(path).convert("RGB").resize((1280, 720))
    a = np.asarray(im).astype(float)
    L = np.asarray(im.convert("L")).astype(float)
    rg = a[..., 0] - a[..., 1]
    yb = 0.5 * (a[..., 0] + a[..., 1]) - a[..., 2]
    col = np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
    edges = np.asarray(im.convert("L").resize((320, 180)).filter(ImageFilter.FIND_EDGES)).astype(float)
    return {"brightness_contrast": round(float(L.std()), 1), "colorfulness": round(float(col), 1),
            "clutter_edge_density": round(float((edges > 40).mean() * 100), 1)}


def thumb_sheet(thumb: str | Path, compare: list[str | Path], out: str | Path) -> Path:
    """Render the thumbnail at real feed sizes, plus grayscale, next to competitors."""
    items = [Path(thumb), *map(Path, compare)]
    W = 20 + sum(w + 20 for _, w, _ in THUMB_SIZES) + 180
    rowh = max(h for *_, h in THUMB_SIZES) + 40
    sheet = Image.new("RGB", (W, rowh * len(items) + 10), (15, 15, 15))
    d = ImageDraw.Draw(sheet)
    for r, p in enumerate(items):
        im = Image.open(p).convert("RGB")
        x, y = 20, r * rowh + 25
        for name, w, h in THUMB_SIZES:
            sheet.paste(im.resize((w, h), Image.LANCZOS), (x, y))
            if r == 0:
                d.text((x, y - 15), name, fill=(200, 200, 200))
            x += w + 20
        sheet.paste(im.convert("L").convert("RGB").resize((168, 94)), (x, y))
        if r == 0:
            d.text((x, y - 15), "grayscale", fill=(200, 200, 200))
        d.text((x, y + 100), "YOURS" if r == 0 else f"compare {r}", fill=(60, 200, 255))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


# ---- QA frame annotation ----------------------------------------------------------

def annotate(image: str | Path, out: str | Path, boxes: list[tuple[tuple[int, int, int, int], str, str]],
             title: str | None = None) -> Path:
    """Draw labelled boxes ((x, y, w, h), label, color) on a frame grab."""
    im = Image.open(image).convert("RGB")
    d = ImageDraw.Draw(im)
    for (x, y, w, h), label, color in boxes:
        d.rectangle([x, y, x + w, y + h], outline=color, width=3)
        d.text((x + 4, max(0, y - 14)), label, fill=color)
    if title:
        d.rectangle([0, 0, im.width, 18], fill=(0, 0, 0))
        d.text((4, 3), title, fill=(255, 255, 255))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out


def sharpness(image: str | Path, box: tuple[int, int, int, int] | None = None) -> float:
    """Variance of the Laplacian (higher = sharper), optionally inside a box."""
    im = Image.open(image).convert("L")
    if box:
        x, y, w, h = box
        im = im.crop((x, y, x + w, y + h))
    a = np.asarray(im).astype(float)
    if a.shape[0] < 3 or a.shape[1] < 3:
        return 0.0
    lap = (-4 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:])
    return float(lap.var())
