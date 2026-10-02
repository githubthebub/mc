"""Resolve anchors to source and output times through the transcript and timing map."""

from __future__ import annotations

from dataclasses import dataclass

from ..media.timing import TimingMap
from .schema import EDL, Anchor
from .transcript import Transcript


class AnchorError(ValueError):
    pass


@dataclass(frozen=True)
class Resolved:
    src: float | None
    out: float


def spans_of_segment(tm: TimingMap, sid: str):
    return [s for s in tm.spans if s.id == sid or (s.id or "").startswith(sid + "#")]


def resolve_src(a: Anchor, tr: Transcript | None, edl: EDL) -> float | None:
    """Source time of an anchor, or None when the anchor lives only in output time."""
    if a.src is not None:
        return a.src + a.pad
    if a.word is not None:
        if tr is None:
            raise AnchorError("word anchor without a transcript")
        w = tr.word(a.word)
        return (w.t1 if a.edge == "end" else w.t0) + a.pad
    if a.sentence is not None:
        if tr is None:
            raise AnchorError("sentence anchor without a transcript")
        s = tr.sentence(a.sentence)
        return (s.t1 if a.edge == "end" else s.t0) + a.pad
    if a.segment is not None:
        seg = edl.segment(a.segment)
        return (seg.src_out if a.edge == "end" else seg.src_in) + a.pad
    return None


def resolve(a: Anchor, tr: Transcript | None, edl: EDL, tm: TimingMap) -> Resolved:
    """Resolve to output time (and source time when there is one)."""
    if a.out is not None:
        return Resolved(tm.to_src(a.out + a.pad), a.out + a.pad)
    if a.segment is not None:
        spans = spans_of_segment(tm, a.segment)
        if not spans:
            raise AnchorError(f"segment {a.segment} has no rendered span")
        out = (spans[-1].out_out if a.edge == "end" else spans[0].out_in) + a.pad
        return Resolved(resolve_src(a, tr, edl), out)
    src = resolve_src(a, tr, edl)
    assert src is not None
    out = tm.to_out(src)
    if out is None:
        # the anchored moment was cut (dead air or a trimmed stretch): snap to the next kept moment
        out = tm.to_out_nearest(src)
    return Resolved(src, out)


def resolve_range(start: Anchor, end: Anchor | None, dur: float | None, tr: Transcript | None,
                  edl: EDL, tm: TimingMap, default_dur: float = 1.0) -> tuple[Resolved, Resolved]:
    s = resolve(start, tr, edl, tm)
    if end is not None:
        e = resolve(end, tr, edl, tm)
    else:
        d = dur if dur is not None else default_dur
        e = Resolved(None if s.src is None else s.src + d, s.out + d)
    if e.out <= s.out:
        e = Resolved(e.src, s.out + (dur or default_dur))
    return s, e
