"""Assemble EDL pieces that code decides: the dead-air cut list from pauses and the profile
preset, and a baseline EDL when no planner output is available."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from ..edl.schema import EDL, Meta, Segment
from ..edl.transcript import Transcript
from ..profile import Profile


def cut_list(duration: float, pauses: list[tuple[float, float]], params: dict[str, float],
             protect: list[tuple[float, float]] | None = None) -> list[tuple[float, float]]:
    """Kept (in, out) ranges after removing empty pauses (cut_silence.py's keep/merge logic).

    params: min_silence (a pause must last this long to be cut), pad (breath kept on each side),
    min_keep (segments shorter than this are dropped or merged)."""
    min_sil, pad, min_keep = params["min_silence"], params["pad"], params.get("min_keep", 0.6)
    prot = protect or []
    pairs = [(s, e) for s, e in pauses if e - s >= min_sil and not any(s < pb and e > pa for pa, pb in prot)]
    keep: list[list[float]] = []
    cur = 0.0
    for s, e in pairs:
        s2 = max(cur, s + pad)
        if s2 - cur > 0:
            keep.append([cur, min(s2, duration)])
        cur = max(0.0, e - pad)
    if cur < duration:
        keep.append([cur, duration])
    merged: list[list[float]] = []
    for k in keep:
        if merged and k[0] - merged[-1][1] < 0.05:
            merged[-1][1] = k[1]
        else:
            merged.append(k)
    merged = [k for k in merged if k[1] - k[0] >= min_keep] or keep
    return [(round(a, 3), round(b, 3)) for a, b in merged if b > a]


def trim_lead_and_tail(ranges: list[tuple[float, float]], tr: Transcript | None, pad: float,
                       duration: float) -> list[tuple[float, float]]:
    """Start on the first word and end after the last word (no silent lead-in or tail)."""
    if not tr or not tr.words or not ranges:
        return ranges
    first, last = tr.words[0].t0 - pad, tr.words[-1].t1 + pad
    out: list[tuple[float, float]] = []
    for a, b in ranges:
        a2, b2 = max(a, first), min(b, last)
        if b2 - a2 > 0.1:
            out.append((round(a2, 3), round(b2, 3)))
    return out or ranges


def segments_from_ranges(ranges: list[tuple[float, float]]) -> list[Segment]:
    return [Segment(id=f"s{i + 1}", src_in=a, src_out=b) for i, (a, b) in enumerate(ranges)]


def baseline_edl(meta: Meta, tr: Transcript | None, analysis: dict[str, Any], profile: Profile,
                 protect: list[tuple[float, float]] | None = None) -> EDL:
    """A code-only EDL: experience preset dead-air removal, nothing else. The planner adds the rest."""
    params = profile.dead_air_params()
    pauses = [(float(s), float(e)) for s, e in analysis.get("pauses", [])]
    ranges = cut_list(meta.duration, pauses, params, protect)
    ranges = trim_lead_and_tail(ranges, tr, params["pad"], meta.duration)
    edl = EDL(meta=meta, segments=segments_from_ranges(ranges))
    edl.ensure_ledger()
    removed = meta.duration - sum(b - a for a, b in ranges)
    edl.mark("experience_fit", "executed", f"{profile.experience} preset: min_silence {params['min_silence']} s, pad {params['pad']} s", "plan")
    edl.mark("dead_air_removal", "executed", f"removed {removed:.1f} s in {len(pauses)} pauses", "plan", count=len(ranges))
    if tr is None:
        edl.mark("transcript_words", "not_executed", "no transcript", "plan")
    elif tr.degraded:
        edl.mark("transcript_words", "degraded", "keyword-spotting transcript; word timings are rough", "plan")
    else:
        edl.mark("transcript_words", "executed", f"{len(tr.words)} words from {tr.model}", "plan")
    return edl


def meta_from(project_name: str, profile: Profile, fmt: str, source: str, duration: float, fps: str | Fraction,
              width: int, height: int, created_by: str = "code", model: str | None = None) -> Meta:
    f = fps if isinstance(fps, str) else f"{fps.numerator}/{fps.denominator}"
    return Meta(project=project_name, profile=profile.name, format=fmt, source=source, duration=duration, fps=f,
                width=width, height=height, created_by=created_by, model=model, experience=profile.experience)
