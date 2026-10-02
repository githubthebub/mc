"""Select Shorts candidates: LLM scores (hook strength, self-contained idea, payoff) combined with
audio energy peaks; each short starts on its strongest line; 15-60 s; non-overlapping."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..edl.schema import EDL
from ..edl.transcript import Transcript
from ..llm.schemas import ShortCandidate, ShortsOut
from ..media.timing import TimingMap
from ..profile import Profile


@dataclass
class Window:
    id: str
    hook_sentence: int
    from_sentence: int
    to_sentence: int
    src_in: float
    src_out: float
    out_len: float             # seconds of kept speech inside the window
    llm_score: float           # 0..10
    energy_score: float        # 0..1
    score: float
    title: str
    context_label: str
    reason: str


def kept_length(tm: TimingMap, a: float, b: float) -> float:
    """Seconds of the long-form output that come from source range [a, b]."""
    total = 0.0
    for s in tm.source_spans():
        lo, hi = max(a, s.src_in), min(b, s.src_out)  # type: ignore[arg-type]
        if hi > lo:
            total += (hi - lo) / s.rate
    return total


def heuristic_candidates(tr: Transcript, analysis: dict[str, Any], tm: TimingMap, profile: Profile,
                         max_candidates: int = 12) -> list[ShortCandidate]:
    """Code-only scoring when the model is unavailable: energy, questions, numbers, strong openers."""
    energy = {int(k): float(v) for k, v in (analysis.get("sentence_energy_db") or {}).items()}
    vals = list(energy.values()) or [0.0]
    med, sd = float(np.median(vals)), float(np.std(vals) or 1.0)
    cands: list[ShortCandidate] = []
    n = len(tr.sentences)
    for i in range(n):
        s0 = tr.sentences[i]
        j = i
        while j + 1 < n and kept_length(tm, s0.t0, tr.sentences[j + 1].t1) <= profile.shorts.max_s:
            j += 1
        if kept_length(tm, s0.t0, tr.sentences[j].t1) < profile.shorts.min_s:
            continue
        text = s0.text
        hook = 5.0 + 2.0 * ((energy.get(i, med) - med) / sd)
        hook += 1.5 if "?" in text else 0.0
        hook += 1.0 if re.search(r"\d", text) else 0.0
        hook += 1.0 if re.search(r"\b(mistake|secret|never|always|nobody|everyone|wrong|truth|why)\b", text, re.I) else 0.0
        hook = max(0.0, min(10.0, hook))
        cands.append(ShortCandidate(id=f"h{i}", hook_sentence=i, from_sentence=i, to_sentence=j, hook_strength=hook,
                                    self_contained=6.0, payoff=5.0 + (1.0 if "." in tr.sentences[j].text else 0.0),
                                    title=text[:60], context_label=profile.shorts.context_label or "", reason="heuristic"))
    cands.sort(key=lambda c: -(c.hook_strength + c.self_contained + c.payoff))
    return cands[:max_candidates]


def energy_scores(tr: Transcript, analysis: dict[str, Any]) -> dict[int, float]:
    energy = {int(k): float(v) for k, v in (analysis.get("sentence_energy_db") or {}).items()}
    if not energy:
        return {}
    vals = np.array(list(energy.values()))
    lo, hi = float(vals.min()), float(vals.max())
    return {k: (v - lo) / (hi - lo) if hi > lo else 0.5 for k, v in energy.items()}


def build_windows(cands: list[ShortCandidate], tr: Transcript, analysis: dict[str, Any], tm: TimingMap,
                  profile: Profile, count: int) -> tuple[list[Window], list[str]]:
    """Combine scores, re-anchor each candidate on its hook line, fit 15-60 s, pick non-overlapping."""
    notes: list[str] = []
    es = energy_scores(tr, analysis)
    sids = {s.id for s in tr.sentences}
    wins: list[Window] = []
    for c in cands:
        if not ({c.hook_sentence, c.from_sentence, c.to_sentence} <= sids):
            notes.append(f"{c.id}: unknown sentence ids, skipped")
            continue
        start = c.hook_sentence                     # a short starts on its strongest line
        end = max(c.to_sentence, start)
        n = len(tr.sentences)

        def length(a: int, b: int) -> float:
            return kept_length(tm, tr.sentence(a).t0, tr.sentence(b).t1)

        while length(start, end) > profile.shorts.max_s and end > start:
            end -= 1
        while length(start, end) < profile.shorts.min_s - 0.5 and end + 1 < n:
            end += 1
        L = length(start, end)
        if not (profile.shorts.min_s - 0.5 <= L <= profile.shorts.max_s + 0.5):
            notes.append(f"{c.id}: cannot fit {profile.shorts.min_s}-{profile.shorts.max_s}s from S{start} ({L:.1f}s), skipped")
            continue
        llm = (c.hook_strength + c.self_contained + c.payoff) / 3.0
        e_peak = max((es.get(s, 0.0) for s in range(start, end + 1)), default=0.0)
        score = 0.65 * (llm / 10.0) + 0.35 * e_peak
        wins.append(Window(c.id, start, start, end, tr.sentence(start).t0, tr.sentence(end).t1, L, llm, e_peak,
                           round(score, 3), c.title, c.context_label or (profile.shorts.context_label or ""), c.reason))
    wins.sort(key=lambda w: -w.score)
    chosen: list[Window] = []
    for w in wins:
        if any(not (w.to_sentence < o.from_sentence or w.from_sentence > o.to_sentence) for o in chosen):
            continue
        chosen.append(w)
        if len(chosen) >= count:
            break
    for i, w in enumerate(chosen):
        w.id = f"short{i + 1}"
    return chosen, notes


def short_edl(long: EDL, tr: Transcript, w: Window, profile: Profile) -> EDL:
    """A linear EDL for one short: the long-form segments clipped to the window (dead air already gone),
    long-form zooms, dropouts, SFX and music mood carried over, an emphasis zoom on the hook line, no cards."""
    from ..edl.schema import Anchor, MusicSection, Segment, ShortSpec, Zoom

    a, b = w.src_in - 0.1, w.src_out + profile.shorts.loop_pad_s
    segs: list[Segment] = []
    for s in sorted(long.segments, key=lambda s: s.src_in):
        if s.kind != "aroll":
            continue
        lo, hi = max(a, s.src_in), min(b, s.src_out)
        if hi - lo >= 0.3:
            segs.append(Segment(id=f"{w.id}_{s.id}", src_in=round(lo, 3), src_out=round(hi, 3), punch=None))
    e = long.model_copy(deep=True)
    e.segments = segs
    e.cards, e.beats, e.overlays, e.voiceover_slots, e.chapters, e.captions, e.fadeouts, e.swells = [], [], [], [], [], [], [], []
    e.story_pass = []
    e.shorts = [ShortSpec(id=w.id, hook=Anchor(sentence=w.hook_sentence), start=Anchor(sentence=w.from_sentence),
                          end=Anchor(sentence=w.to_sentence, edge="end"), context_label=w.context_label, title=w.title,
                          score=w.score, reason=w.reason)]
    inside = lambda t: a <= t <= b  # noqa: E731

    def keep_if_inside(items, key):
        out = []
        for it in items:
            try:
                t = key(it)
            except Exception:  # noqa: BLE001
                continue
            if t is not None and inside(t):
                out.append(it)
        return out

    from ..edl.resolve import resolve_src
    e.zooms = keep_if_inside(long.zooms, lambda z: resolve_src(z.at, tr, long))
    hook = tr.sentence(w.hook_sentence)
    if not any(resolve_src(z.at, tr, long) is not None and abs(resolve_src(z.at, tr, long) - hook.t0) < 1.0 for z in e.zooms):  # type: ignore[operator]
        e.zooms.insert(0, Zoom(id=f"{w.id}_hook", at=Anchor(sentence=hook.id), end=Anchor(sentence=hook.id, edge="end"),
                               scale=1.18, reason="emphasis on the hook line"))
    e.dropouts = keep_if_inside(long.dropouts, lambda d: resolve_src(d.start, tr, long))
    e.sfx = keep_if_inside(long.sfx, lambda x: resolve_src(x.at, tr, long))
    # music: the long-form section whose range covers the hook, else the first; one section, no fadeout
    mood = "playful"
    rel_db = profile.audio.music_rel_db
    for m in long.music:
        try:
            ms, me = resolve_src(m.start, tr, long), resolve_src(m.end, tr, long)
        except Exception:  # noqa: BLE001
            continue
        if ms is not None and me is not None and ms - 0.5 <= hook.t0 <= me + 0.5:
            mood, rel_db = m.mood, m.rel_db
            break
    else:
        if long.music:
            mood, rel_db = long.music[0].mood, long.music[0].rel_db
    e.music = [MusicSection(id=f"{w.id}_m", start=Anchor(segment=segs[0].id), end=Anchor(segment=segs[-1].id, edge="end"),
                            mood=mood, rel_db=rel_db, reason="carried from the long-form section")] if segs else []
    e.notes = [f"short {w.id}: S{w.from_sentence}-S{w.to_sentence}, hook S{w.hook_sentence}, {w.out_len:.1f}s"]
    return e
