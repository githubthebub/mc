"""Resolve anchors to source and output times through the transcript and timing map."""

from __future__ import annotations

from dataclasses import dataclass

from ..media.timing import TimingMap
from .schema import EDL, Anchor
from .transcript import Transcript


COSMETIC_PAD_S = 1.0


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


def resolve(a: Anchor, tr: Transcript | None, edl: EDL, tm: TimingMap, is_end: bool = False) -> Resolved:
    """Resolve to output time (and source time when there is one)."""
    if a.out is not None:
        return Resolved(tm.to_src(a.out + a.pad), a.out + a.pad)
    if a.segment is not None:
        spans = spans_of_segment(tm, a.segment)
        if not spans:
            raise AnchorError(f"segment {a.segment} has no rendered span")
        if a.edge == "end":
            out = spans[-1].out_out + a.pad
        else:
            # a card inserted right before this segment belongs to it (music covers the card)
            first = spans[0]
            idx = tm.spans.index(first)
            while idx > 0 and tm.spans[idx - 1].kind == "card":
                idx -= 1
            out = tm.spans[idx].out_in + a.pad
        return Resolved(resolve_src(a, tr, edl), out)
    # A small pad (up to COSMETIC_PAD_S) is a cosmetic offset applied in OUTPUT time that never
    # crosses into another piece (a padded end must not land in the next segment, which may sit
    # elsewhere after a restructure). A larger pad is structural ("8 s before the payoff") and is
    # applied in source time, then mapped through the cuts.
    cosmetic = abs(a.pad) <= COSMETIC_PAD_S
    bare = a.model_copy(update={"pad": 0.0}) if cosmetic else a
    src = resolve_src(bare, tr, edl)
    assert src is not None
    out = tm.to_out(src)
    if out is None:
        # the anchored moment was cut (dead air or a trimmed stretch): a start snaps forward to the
        # next kept moment, an end snaps back to the previous one
        out = tm.to_out_prev(src) if (a.edge == "end" or is_end) else tm.to_out_nearest(src)
    if a.pad and cosmetic:
        span = tm.span_at_out(out - 1e-6 if (a.edge == "end" or is_end) else out)
        padded = out + a.pad
        if span is not None:
            padded = min(max(padded, span.out_in), span.out_out)
        out = max(0.0, min(padded, tm.out_duration))
        src = src + a.pad
    return Resolved(src, out)


def resolve_range(start: Anchor, end: Anchor | None, dur: float | None, tr: Transcript | None,
                  edl: EDL, tm: TimingMap, default_dur: float = 1.0) -> tuple[Resolved, Resolved]:
    s = resolve(start, tr, edl, tm)
    if end is not None:
        e = resolve(end, tr, edl, tm, is_end=True)
    else:
        d = dur if dur is not None else default_dur
        e = Resolved(None if s.src is None else s.src + d, s.out + d)
    if e.out <= s.out:
        e = Resolved(e.src, s.out + (dur or default_dur))
    return s, e
