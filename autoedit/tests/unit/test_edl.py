import pytest
from pydantic import ValidationError

from autoedit.edl.resolve import resolve
from autoedit.edl.schema import EDL, Anchor, Caption, Card, Meta, Segment, Sfx
from autoedit.edl.transcript import Transcript, Word
from autoedit.edl.validate import validate
from autoedit.media.timing import TimingMap
from fractions import Fraction


def _meta():
    return Meta(project="p", profile="personal", format="talking-head", source="x.mp4", duration=10, fps="30/1", width=1920, height=1080)


def _tr():
    ws = [Word(id=i, text=t, t0=1 + i * 0.5, t1=1.4 + i * 0.5) for i, t in enumerate("one two three. four five six.".split())]
    tr = Transcript(words=ws)
    tr.sentences = Transcript.group_sentences(ws)
    return tr


def test_anchor_requires_exactly_one_field():
    with pytest.raises(ValidationError):
        Anchor()
    with pytest.raises(ValidationError):
        Anchor(word=1, sentence=2)


def test_captions_limited_to_three_words():
    with pytest.raises(ValidationError):
        Caption(id="c", at=Anchor(word=0), words=["a", "b", "c", "d"])


def test_resolve_through_timing_map():
    edl = EDL(meta=_meta(), segments=[Segment(id="s1", src_in=1.0, src_out=2.5), Segment(id="s2", src_in=3.0, src_out=4.0)])
    tm = TimingMap(Fraction(30, 1))
    tm.append_source(1.0, 2.5, id="s1#0")
    tm.append_source(3.0, 4.0, id="s2#0")
    tr = _tr()
    r = resolve(Anchor(word=3), tr, edl, tm)      # word 3 starts at 2.5 (cut) -> snaps to s2 start
    assert r.src == 2.5 and r.out == 1.5
    r = resolve(Anchor(segment="s2", edge="end"), tr, edl, tm)
    assert r.out == 2.5
    r = resolve(Anchor(word=0, edge="end", pad=0.1), tr, edl, tm)
    assert r.out == pytest.approx(0.5)


def test_end_anchor_past_a_segment_end_snaps_back_not_forward():
    """A caption whose padded end lands in a cut must end where its segment ends, not at the next span 20 s later."""
    from autoedit.edl.resolve import resolve_range
    edl = EDL(meta=_meta(), segments=[Segment(id="s1", src_in=1.0, src_out=2.5), Segment(id="s2", src_in=8.0, src_out=9.0)])
    tm = TimingMap(Fraction(30, 1))
    tm.append_source(1.0, 2.5, id="s1#0")
    tm.append_source(8.0, 9.0, id="s2#0")
    tr = _tr()
    s, e = resolve_range(Anchor(word=1), Anchor(word=2, edge="end", pad=0.25), None, tr, edl, tm)
    assert s.out == pytest.approx(0.5)
    assert e.out == pytest.approx(1.5)      # the end of s1, not 1.5 + the cut


def test_pad_never_crosses_into_a_restructured_segment():
    """After a hook move, the segment after the hook's source end plays much later; a padded end stays put."""
    from autoedit.edl.resolve import resolve_range
    edl = EDL(meta=_meta(), segments=[Segment(id="hook", src_in=2.0, src_out=3.0), Segment(id="s1", src_in=1.0, src_out=2.0),
                                      Segment(id="s2", src_in=3.0, src_out=9.0)])
    tm = TimingMap(Fraction(30, 1))
    tm.append_source(2.0, 3.0, id="hook#0")
    tm.append_source(1.0, 2.0, id="s1#0")
    tm.append_source(3.0, 9.0, id="s2#0")
    tr = _tr()                                     # word 2 is 2.0-2.4, word 3 is 2.5-2.9
    s, e = resolve_range(Anchor(word=2), Anchor(word=3, edge="end", pad=0.25), None, tr, edl, tm)
    assert s.out == pytest.approx(0.0)
    assert e.out == pytest.approx(1.0)             # clamped to the hook piece, not 2.0 + ... in s2


def test_validate_reports_bad_references_and_lonely_risers():
    edl = EDL(meta=_meta(), segments=[Segment(id="s1", src_in=0, src_out=10)],
              cards=[Card(id="k", before_segment="nope", text="x")],
              sfx=[Sfx(id="r", kind="riser", at=Anchor(word=2))])
    probs = validate(edl, None, _tr())
    assert any(p.level == "error" and "unknown segment" in p.msg for p in probs)
    assert any("riser" in p.msg for p in probs)


def test_ledger_round_trip(tmp_path):
    edl = EDL(meta=_meta(), segments=[Segment(id="s1", src_in=0, src_out=10)])
    edl.ensure_ledger()
    edl.mark("dead_air_removal", "executed", "x", "plan", 3)
    p = edl.save(tmp_path / "edl.json")
    e2 = EDL.load(p)
    assert e2.techniques["dead_air_removal"].count == 3
    with pytest.raises(KeyError):
        edl.mark("not_a_technique", "executed")
