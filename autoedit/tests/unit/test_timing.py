from fractions import Fraction

from autoedit.media.timing import TimingMap, frames_between, snap


def test_snap_floor_and_round():
    fps = Fraction(30000, 1001)
    assert snap(0.0, fps) == 0.0
    t = snap(1.0, fps)
    assert abs(t - 29 / float(fps)) < 1e-9          # 1.0 s is 29.97 frames -> floor 29
    assert abs(snap(1.0, fps, "round") - 30 / float(fps)) < 1e-9


def test_cuts_compose_and_round_trip():
    tm = TimingMap(Fraction(30, 1))
    tm.append_source(1.0, 3.0, id="s1#0")      # 60 frames
    tm.append_hold(1.0, 3.0, id="s1#0:hold")   # 30 frames
    tm.append_source(5.0, 6.0, id="s2#0")      # 30 frames
    assert tm.total_frames == 120
    assert abs(tm.out_duration - 4.0) < 1e-9
    assert tm.to_out(1.5) == 0.5
    assert tm.to_out(4.0) is None               # cut
    assert tm.to_out_nearest(4.0) == 3.0        # snaps to the next kept moment (after the hold)
    assert abs(tm.to_out(5.5) - 3.5) < 1e-9
    assert tm.to_src(0.5) == 1.5
    assert tm.to_src(2.5) == 3.0                # inside the hold: the frozen source frame
    assert abs(tm.to_src(3.5) - 5.5) < 1e-9
    assert tm.to_src(99) is None


def test_speed_changes_rate():
    tm = TimingMap(Fraction(30, 1))
    s = tm.append_source(0.0, 3.0, rate=1.5, kind="montage")
    assert s.frames == 60 and abs(s.out_dur - 2.0) < 1e-9
    assert abs(tm.to_out(1.5) - 1.0) < 1e-9
    assert abs(tm.to_src(1.0) - 1.5) < 1e-9


def test_frame_accuracy_over_many_segments():
    fps = Fraction(30000, 1001)
    tm = TimingMap(fps)
    t = 0.0
    for i in range(300):
        a, b = snap(t, fps), snap(t + 0.733, fps, "round")
        tm.append_source(a, b, id=f"s{i}")
        t += 1.1
    # the output duration is exactly total_frames / fps, never accumulated float error
    assert abs(tm.out_duration - tm.total_frames / float(fps)) < 1e-6
    assert all(s.frames == frames_between(s.src_in, s.src_out, fps) for s in tm.spans)


def test_json_round_trip():
    tm = TimingMap(Fraction(25, 1))
    tm.append_source(0.0, 2.0, id="a")
    tm.append_hold(0.5, 2.0, kind="card", id="card:x")
    tm2 = TimingMap.from_json(tm.to_json())
    assert tm2.out_duration == tm.out_duration
    assert tm2.span_by_id("card:x").kind == "card"
    assert tm.legacy_triples() == [[0.0, 2.0, 0.0]]
