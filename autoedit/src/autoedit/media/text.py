"""Text rendering: ASS documents for libass, font resolution and measurement, safe zones.

libass font sizes did not match expectations in practice, so sizes are verified by
rendering a check frame and measuring the glyphs (see render_font_check)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageFont

from .ffmpeg import run_ffmpeg

DEJAVU_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
DEJAVU = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


@dataclass(frozen=True)
class Font:
    path: Path
    family: str
    bold: bool


def resolve_font(path: str | Path | None, fallback: Path = DEJAVU_BOLD) -> Font:
    """Load a TTF and read its family name (what libass needs in Fontname)."""
    p = Path(path).expanduser() if path else fallback
    if not p.exists():
        if path:
            raise FileNotFoundError(f"font not found: {p}")
        p = fallback
    f = ImageFont.truetype(str(p), 40)
    family, style = f.getname()
    return Font(p, family, "bold" in (style or "").lower())


def measure_text(font: Font, size_px: int, text: str) -> tuple[int, int]:
    f = ImageFont.truetype(str(font.path), size_px)
    l, t, r, b = f.getbbox(text)
    return r - l, b - t


def ass_time(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def ass_color(hex_rgb: str, alpha: int = 0) -> str:
    """'#RRGGBB' -> '&HAABBGGRR' (ASS byte order)."""
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


@dataclass
class AssStyle:
    name: str
    font: Font
    size: int
    primary: str = "#FFFFFF"
    outline: str = "#000000"
    back: str = "#000000"
    back_alpha: int = 0x64
    bold: bool = True
    border_style: int = 1          # 1 outline+shadow, 3 opaque box
    outline_w: float = 2.0
    shadow: float = 0.0
    alignment: int = 2             # numpad: 2 bottom-center, 5 center, 8 top-center
    margin_l: int = 80
    margin_r: int = 80
    margin_v: int = 120

    def line(self) -> str:
        return (f"Style: {self.name},{self.font.family},{self.size},{ass_color(self.primary)},"
                f"{ass_color(self.primary)},{ass_color(self.outline)},{ass_color(self.back, self.back_alpha)},"
                f"{-1 if self.bold else 0},0,0,0,100,100,0,0,{self.border_style},{self.outline_w},{self.shadow},"
                f"{self.alignment},{self.margin_l},{self.margin_r},{self.margin_v},1")


@dataclass
class AssEvent:
    start: float
    end: float
    style: str
    text: str
    layer: int = 0

    def line(self) -> str:
        return f"Dialogue: {self.layer},{ass_time(self.start)},{ass_time(self.end)},{self.style},,0,0,0,,{self.text}"


@dataclass
class AssDoc:
    width: int
    height: int
    styles: list[AssStyle] = field(default_factory=list)
    events: list[AssEvent] = field(default_factory=list)

    def add_style(self, s: AssStyle) -> AssStyle:
        self.styles.append(s)
        return s

    def add(self, start: float, end: float, style: str, text: str, layer: int = 0) -> AssEvent:
        e = AssEvent(start, end, style, text, layer)
        self.events.append(e)
        return e

    def render(self) -> str:
        head = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {self.width}", f"PlayResY: {self.height}",
                "WrapStyle: 2", "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
                "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                "Alignment, MarginL, MarginR, MarginV, Encoding"]
        head += [s.line() for s in self.styles]
        head += ["", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
        head += [e.line() for e in sorted(self.events, key=lambda e: (e.layer, e.start))]
        return "\n".join(head) + "\n"

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")
        return path

    def fonts_dir(self) -> Path | None:
        dirs = {s.font.path.parent for s in self.styles}
        return next(iter(dirs)) if len(dirs) == 1 else None


def ass_filter(ass_path: Path, fonts_dir: Path | None) -> str:
    """The ffmpeg -vf expression for this ASS file (paths escaped for the filter parser)."""
    def esc(p: Path) -> str:
        return str(p).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    expr = f"ass=filename='{esc(ass_path)}'"
    if fonts_dir:
        expr += f":fontsdir='{esc(fonts_dir)}'"
    return expr


# ---- safe zones and placement -------------------------------------------------------

@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h

    def intersects(self, o: "Rect", pad: float = 0.0) -> bool:
        return not (self.x2 + pad <= o.x or o.x2 + pad <= self.x or self.y2 + pad <= o.y or o.y2 + pad <= self.y)

    def inside(self, o: "Rect") -> bool:
        return self.x >= o.x and self.y >= o.y and self.x2 <= o.x2 and self.y2 <= o.y2

    def as_int(self) -> tuple[int, int, int, int]:
        return int(self.x), int(self.y), int(self.w), int(self.h)


def safe_zone(width: int, height: int, vertical: bool) -> Rect:
    """Where text may live. Vertical (Shorts): clear of the bottom 20% and the right 15%."""
    if vertical:
        return Rect(width * 0.05, height * 0.10, width * 0.80, height * 0.70)
    return Rect(width * 0.05, height * 0.05, width * 0.90, height * 0.87)


def place_text(size: tuple[float, float], zone: Rect, avoid: list[Rect], *, prefer: str = "lower",
               pad: float = 12.0) -> tuple[float, float]:
    """Top-left of a text box of `size` inside `zone`, not intersecting any `avoid` rect.

    Candidates are tried from the preferred position outward (lower-center first for
    long-form captions, then upper-center, then the middle), and the first clean one
    wins. If none is clean the candidate farthest from the avoided boxes is used, and
    the caller should report that in QA.
    """
    tw, th = size
    cx = zone.x + (zone.w - tw) / 2
    ys = [zone.y2 - th, zone.y, zone.y + (zone.h - th) / 2]
    if prefer == "upper":
        ys = [ys[1], ys[0], ys[2]]
    elif prefer == "middle":
        ys = [ys[2], ys[0], ys[1]]
    # also try sliding up/down in steps so captions can tuck above or below a face
    cands: list[tuple[float, float]] = []
    for y in ys:
        cands.append((cx, y))
    step = max(8.0, zone.h / 12)
    for k in range(1, 13):
        for y in (ys[0] - k * step, ys[1] + k * step):
            if zone.y <= y <= zone.y2 - th:
                cands.append((cx, y))
    for x, y in cands:
        r = Rect(x, y, tw, th)
        if r.inside(zone) and not any(r.intersects(a, pad) for a in avoid):
            return x, y
    # fallback: maximize distance from avoided boxes
    def dist(c: tuple[float, float]) -> float:
        r = Rect(c[0], c[1], tw, th)
        return min((abs((r.y + r.h / 2) - (a.y + a.h / 2)) for a in avoid), default=1e9)
    best = max(cands, key=dist)
    return best


def render_font_check(style: AssStyle, width: int, height: int, out_png: Path, text: str = "Hxg") -> dict:
    """Render `text` with libass using this style and measure the glyph height in pixels."""
    doc = AssDoc(width, height, [style], [AssEvent(0, 1, style.name, f"{{\\an5\\pos({width // 2},{height // 2})}}{text}")])
    ass = out_png.with_suffix(".ass")
    doc.write(ass)
    run_ffmpeg(["-f", "lavfi", "-i", f"color=c=0x202020:s={width}x{height}:d=0.2", "-vf", ass_filter(ass, doc.fonts_dir()),
                "-frames:v", "1", str(out_png)])
    im = Image.open(out_png).convert("L")
    px = im.load()
    rows = [y for y in range(im.height) if any(px[x, y] > 120 for x in range(0, im.width, 2))]
    measured_h = (rows[-1] - rows[0] + 1) if rows else 0
    # the text's ink height (cap height + descender) measured by Pillow at the same size
    expected_w, expected_h = measure_text(style.font, style.size, text)
    return {"font": style.font.family, "size_px": style.size, "measured_ink_px": measured_h,
            "expected_ink_px": expected_h, "ratio": round(measured_h / expected_h, 3) if expected_h else None}


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def slugify(text: str, max_len: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len].rstrip("-") or "video"
