"""Frame-accurate source-to-output timing map.

Every rendered piece is a Span. Source spans map a source range to the output
timeline at a rate (1.0 normal, 1.5 = sped up). Inserted spans (holds, cards)
have no source range but may remember which source time they hold.
"""

from __future__ import annotations

import bisect
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from typing import Any


def snap(t: float, fps: Fraction, mode: str = "floor") -> float:
    """Snap a time to a frame boundary at fps."""
    frames = t * fps
    if mode == "floor":
        n = int(frames) if frames >= 0 else 0
    elif mode == "ceil":
        n = int(-(-frames // 1))
    else:
        n = int(round(float(frames)))
    return float(Fraction(n) / fps)


def frames_between(t0: float, t1: float, fps: Fraction) -> int:
    return max(0, int(round((t1 - t0) * float(fps))))


@dataclass
class Span:
    out_in: float
    out_dur: float
    src_in: float | None = None
    src_out: float | None = None
    rate: float = 1.0
    kind: str = "source"          # source | hold | card | montage
    id: str | None = None
    holds_src: float | None = None  # for holds: the source time of the frozen frame
    frames: int = 0

    @property
    def out_out(self) -> float:
        return self.out_in + self.out_dur

    def contains_src(self, t: float) -> bool:
        return self.src_in is not None and self.src_out is not None and self.src_in <= t < self.src_out

    def contains_out(self, t: float) -> bool:
        return self.out_in <= t < self.out_out

    def to_out(self, t_src: float) -> float:
        assert self.src_in is not None
        return self.out_in + (t_src - self.src_in) / self.rate

    def to_src(self, t_out: float) -> float | None:
        if self.src_in is None:
            return self.holds_src
        return self.src_in + (t_out - self.out_in) * self.rate


@dataclass
class TimingMap:
    fps: Fraction
    spans: list[Span] = field(default_factory=list)

    # ---- construction ----
    def append_source(self, src_in: float, src_out: float, *, rate: float = 1.0,
                      kind: str = "source", id: str | None = None) -> Span:
        n = frames_between(src_in, src_out, self.fps)
        n = max(1, int(round(n / rate)))
        dur = float(Fraction(n) / self.fps)
        s = Span(self.out_duration, dur, src_in, src_out, rate, kind, id, None, n)
        self.spans.append(s)
        return s

    def append_hold(self, dur: float, holds_src: float | None, *, kind: str = "hold",
                    id: str | None = None) -> Span:
        n = max(1, frames_between(0.0, dur, self.fps))
        d = float(Fraction(n) / self.fps)
        s = Span(self.out_duration, d, None, None, 1.0, kind, id, holds_src, n)
        self.spans.append(s)
        return s

    # ---- queries ----
    @property
    def out_duration(self) -> float:
        return self.spans[-1].out_out if self.spans else 0.0

    @property
    def total_frames(self) -> int:
        return sum(s.frames for s in self.spans)

    def source_spans(self) -> list[Span]:
        return [s for s in self.spans if s.src_in is not None]

    def to_out(self, t_src: float) -> float | None:
        """Output time of a source time, or None when that source time was cut."""
        for s in self.spans:
            if s.contains_src(t_src):
                return s.to_out(t_src)
        return None

    def to_out_nearest(self, t_src: float) -> float:
        """Output time of a source time; a cut time snaps to the next kept moment."""
        t = self.to_out(t_src)
        if t is not None:
            return t
        best: float | None = None
        for s in self.source_spans():
            if s.src_in is not None and s.src_in >= t_src:
                cand = s.out_in
                best = cand if best is None else min(best, cand)
        if best is not None:
            return best
        return self.out_duration

    def to_src(self, t_out: float) -> float | None:
        for s in self.spans:
            if s.contains_out(t_out):
                return s.to_src(t_out)
        return None

    def to_out_prev(self, t_src: float) -> float:
        """Output time of a source time; a cut time snaps back to the end of the last kept moment before it."""
        t = self.to_out(t_src)
        if t is not None:
            return t
        best: float | None = None
        for s in self.source_spans():
            if s.src_out is not None and s.src_out <= t_src:
                cand = s.out_out
                best = cand if best is None else max(best, cand)
        if best is not None:
            return best
        return 0.0

    def span_at_out(self, t_out: float) -> Span | None:
        for s in self.spans:
            if s.contains_out(t_out):
                return s
        return None

    def span_by_id(self, id: str) -> Span | None:
        return next((s for s in self.spans if s.id == id), None)

    def is_kept(self, t_src: float) -> bool:
        return self.to_out(t_src) is not None

    # ---- (de)serialization ----
    def to_json(self) -> dict[str, Any]:
        return {"fps": f"{self.fps.numerator}/{self.fps.denominator}",
                "out_duration": round(self.out_duration, 6),
                "total_frames": self.total_frames,
                "note": "out = out_in + (src - src_in) / rate; holds and cards have no src range",
                "spans": [asdict(s) for s in self.spans]}

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "TimingMap":
        tm = cls(Fraction(d["fps"]))
        tm.spans = [Span(**s) for s in d["spans"]]
        return tm

    def legacy_triples(self) -> list[list[float]]:
        """cut_silence.py's [src_start, src_end, out_start] form."""
        return [[s.src_in, s.src_out, s.out_in] for s in self.spans if s.src_in is not None and s.src_out is not None]
