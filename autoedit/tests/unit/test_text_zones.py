from autoedit.media.text import Rect, ass_color, ass_time, place_text, safe_zone


def test_ass_helpers():
    assert ass_color("#FF4E2A") == "&H002A4EFF"
    assert ass_time(61.5) == "0:01:01.50"


def test_vertical_safe_zone_clears_bottom_and_right():
    z = safe_zone(1080, 1920, vertical=True)
    assert z.y2 <= 1920 * 0.80 + 1e-6
    assert z.x2 <= 1080 * 0.85 + 1e-6


def test_caption_never_overlaps_face():
    W, H = 1080, 1920
    zone = safe_zone(W, H, True)
    face = Rect(300, 1100, 480, 480)          # a face sitting right where lower captions would go
    x, y = place_text((700, 90), zone, [face], prefer="lower")
    box = Rect(x, y, 700, 90)
    assert box.inside(zone)
    assert not box.intersects(face, 12)


def test_caption_prefers_lower_when_clear():
    W, H = 1920, 1080
    zone = safe_zone(W, H, False)
    face = Rect(800, 100, 300, 300)
    x, y = place_text((600, 70), zone, [face], prefer="lower")
    assert y + 70 == zone.y2
