import numpy as np

from autoedit.media.audio import PAUSE_SR, PAUSE_WIN, detect_pauses, noise_floor_db, pause_threshold_db, rms_levels


def speech_like(seconds: float, floor_db: float, gaps: list[tuple[float, float]], seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(seconds * PAUSE_SR)
    x = rng.standard_normal(n) * 10 ** (floor_db / 20)
    speech = rng.standard_normal(n) * 0.2 * (1 + 0.5 * np.sin(np.arange(n) / PAUSE_SR * 7))
    mask = np.ones(n, dtype=bool)
    for a, b in gaps:
        mask[int(a * PAUSE_SR):int(b * PAUSE_SR)] = False
    x[mask] += speech[mask]
    return x


def _found(levels, min_silence=0.4):
    thr = pause_threshold_db(levels)
    return detect_pauses(levels, thr, min_silence)


def test_pauses_found_against_quiet_floor():
    x = speech_like(10, -70, [(2.0, 2.8), (5.0, 6.5), (8.0, 8.2)])
    lv = rms_levels(x)
    found = _found(lv)
    assert len(found) == 2
    assert abs(found[0][0] - 2.0) <= PAUSE_WIN * 2 and abs(found[0][1] - 2.8) <= PAUSE_WIN * 2
    assert abs(found[1][0] - 5.0) <= PAUSE_WIN * 2 and abs(found[1][1] - 6.5) <= PAUSE_WIN * 2


def test_threshold_adapts_to_noisy_floor():
    """A fixed -40 dB threshold would see no pauses on a noisy recording; floor + 6 dB still finds them."""
    x = speech_like(10, -38, [(3.0, 4.0), (7.0, 7.9)])
    lv = rms_levels(x)
    assert noise_floor_db(lv) > -42
    fixed = detect_pauses(lv, -40.0, 0.4)
    adaptive = _found(lv)
    assert len(adaptive) == 2
    assert len(fixed) < len(adaptive) or fixed != adaptive


def test_click_inside_a_pause_is_dropped_by_the_cut_list():
    """Detection is faithful to cut_silence.py: a click splits a pause into two. The cut list then
    drops the sub-min_keep sliver, so the whole pause still goes."""
    from autoedit.edl.build import cut_list
    from autoedit.profile import DEAD_AIR_PRESETS

    x = speech_like(6, -70, [(2.0, 3.5)])
    i = int(2.7 * PAUSE_SR)
    x[i:i + int(0.05 * PAUSE_SR)] += 0.3
    lv = rms_levels(x)
    found = _found(lv, min_silence=0.5)
    assert len(found) == 2
    keep = cut_list(6.0, found, DEAD_AIR_PRESETS["informative"])
    assert len(keep) == 2 and keep[0][1] < 2.3 and keep[1][0] > 3.2


def test_min_silence_filters():
    x = speech_like(6, -70, [(1.0, 1.3), (3.0, 4.0)])
    lv = rms_levels(x)
    assert len(_found(lv, 0.5)) == 1
    assert len(_found(lv, 0.2)) == 2
