from autoedit.edl.build import cut_list, trim_lead_and_tail
from autoedit.edl.transcript import Transcript, Word
from autoedit.profile import DEAD_AIR_PRESETS


def test_cut_list_keeps_pads_and_merges():
    pauses = [(2.0, 3.0), (5.0, 5.3), (7.0, 9.0)]
    keep = cut_list(10.0, pauses, DEAD_AIR_PRESETS["informative"])
    # the 0.3 s pause is under min_silence 0.5 and survives; pads of 0.15 s remain around the others
    assert keep == [(0.0, 2.15), (2.85, 7.15), (8.85, 10.0)]


def test_protected_pause_is_kept():
    pauses = [(2.0, 3.0), (7.0, 9.0)]
    keep = cut_list(10.0, pauses, DEAD_AIR_PRESETS["informative"], protect=[(6.5, 9.5)])
    assert keep == [(0.0, 2.15), (2.85, 10.0)]


def test_hangout_keeps_natural_pauses():
    pauses = [(2.0, 3.0), (7.0, 9.0)]
    keep = cut_list(10.0, pauses, DEAD_AIR_PRESETS["hangout"])
    assert keep == [(0.0, 7.35), (8.65, 10.0)]


def test_trim_lead_and_tail():
    words = [Word(id=0, text="hi", t0=1.0, t1=1.3), Word(id=1, text="there", t0=1.4, t1=1.8)]
    tr = Transcript(words=words)
    assert trim_lead_and_tail([(0.0, 5.0)], tr, 0.15, 5.0) == [(0.85, 1.95)]
