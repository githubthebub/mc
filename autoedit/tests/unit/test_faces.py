from autoedit.media.faces import FaceBox, FaceTrack, crop_for_zoom, smooth_track


def test_smoothing_removes_jitter_and_holds_deadband():
    raw = [FaceBox(i * 0.1, 100 + (2 if i % 2 else -2), 80, 120, 120) for i in range(40)]
    sm = smooth_track(raw, alpha=0.2, deadband=0.04)
    xs = [b.x for b in sm]
    # a +-2 px jitter (4 px swing) on a 120 px box is inside the 4.8 px deadband: the track does not move
    assert max(xs) - min(xs) < 1.0


def test_smoothing_follows_real_moves():
    raw = [FaceBox(i * 0.1, 100 if i < 20 else 300, 80, 120, 120) for i in range(60)]
    sm = smooth_track(raw, alpha=0.2)
    assert sm[19].x < 110
    assert sm[-1].x > 290          # converges to the new position
    assert 100 < sm[25].x < 300    # eases rather than jumps


def test_gap_resets_instead_of_sliding():
    raw = [FaceBox(0.0, 100, 80, 120, 120), FaceBox(5.0, 400, 80, 120, 120)]
    sm = smooth_track(raw, max_gap=1.0)
    assert sm[1].x == 400


def test_box_at_interpolates_and_respects_gaps():
    tr = FaceTrack(1920, 1080, 0.1, [FaceBox(0.0, 0, 0, 100, 100), FaceBox(1.0, 100, 0, 100, 100), FaceBox(5.0, 500, 0, 100, 100)])
    assert tr.box_at(0.5).x == 50
    assert tr.box_at(3.0) is None            # 4 s gap: no face known
    assert tr.box_at(1.3).x == 100           # near a sample
    assert tr.mean_box(0.0, 1.0).x == 50


def test_crop_keeps_face_screen_position():
    W, H = 1920, 1080
    face = FaceBox(0, 300, 200, 200, 200)    # center (400, 300): upper left
    x, y, w, h = crop_for_zoom(face, W, H, 1.3)
    assert (w, h) == (int(W / 1.3) // 2 * 2, int(H / 1.3) // 2 * 2)
    # the face center must fall at the same relative position inside the crop as it had in the frame
    rel_before = (face.cx / W, face.cy / H)
    rel_after = ((face.cx - x) / w, (face.cy - y) / h)
    assert abs(rel_before[0] - rel_after[0]) < 0.02 and abs(rel_before[1] - rel_after[1]) < 0.02
    # and the face box stays inside the crop
    assert x <= face.x and y <= face.y and face.x + face.w <= x + w and face.y + face.h <= y + h


def test_crop_clamps_at_edges_without_cutting_face():
    W, H = 1920, 1080
    face = FaceBox(0, 1700, 50, 200, 200)    # top-right corner
    x, y, w, h = crop_for_zoom(face, W, H, 1.5)
    assert x + w <= W and y >= 0
    assert x <= face.x and y <= face.y and face.x + face.w <= x + w and face.y + face.h <= y + h


def test_crop_without_face_uses_upper_third():
    x, y, w, h = crop_for_zoom(None, 1920, 1080, 1.2, "top")
    assert y < (1080 - h) / 2
