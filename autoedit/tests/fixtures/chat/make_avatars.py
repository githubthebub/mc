"""Draw simple avatars for the fixture episode (frog, dan, mia)."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw


def draw(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    s = 256
    # frog: green face with big eyes
    im = Image.new("RGBA", (s, s), (40, 120, 60, 255))
    d = ImageDraw.Draw(im)
    d.ellipse([30, 60, 226, 236], fill=(87, 242, 135))
    for ex in (80, 176):
        d.ellipse([ex - 34, 40, ex + 34, 108], fill=(87, 242, 135))
        d.ellipse([ex - 22, 52, ex + 22, 96], fill=(255, 255, 255))
        d.ellipse([ex - 9, 62, ex + 9, 86], fill=(20, 20, 20))
    d.arc([70, 150, 186, 210], 10, 170, fill=(20, 60, 30), width=8)
    im.save(out / "frog.png")
    # dan: blue circle with a cap
    im = Image.new("RGBA", (s, s), (60, 80, 140, 255))
    d = ImageDraw.Draw(im)
    d.ellipse([40, 60, 216, 236], fill=(225, 180, 150))
    d.chord([40, 50, 216, 150], 180, 360, fill=(40, 40, 120))
    d.ellipse([90, 120, 110, 140], fill=(30, 30, 30))
    d.ellipse([146, 120, 166, 140], fill=(30, 30, 30))
    d.arc([95, 150, 160, 200], 20, 160, fill=(120, 50, 50), width=6)
    im.save(out / "dan.png")
    # mia: pink with dark hair
    im = Image.new("RGBA", (s, s), (160, 60, 120, 255))
    d = ImageDraw.Draw(im)
    d.ellipse([40, 60, 216, 236], fill=(235, 190, 165))
    d.chord([30, 40, 226, 180], 180, 360, fill=(40, 25, 30))
    d.rectangle([30, 110, 60, 220], fill=(40, 25, 30))
    d.rectangle([196, 110, 226, 220], fill=(40, 25, 30))
    d.ellipse([90, 125, 110, 145], fill=(30, 30, 30))
    d.ellipse([146, 125, 166, 145], fill=(30, 30, 30))
    d.arc([95, 160, 160, 205], 20, 160, fill=(150, 50, 70), width=6)
    im.save(out / "mia.png")


if __name__ == "__main__":
    draw(Path(sys.argv[1]))
