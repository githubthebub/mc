"""EDL validation beyond the schema: anchors resolve, segments are sane, skill rules hold."""

from __future__ import annotations

from dataclasses import dataclass

from ..edl.resolve import AnchorError, resolve_src
from ..edl.schema import EDL
from ..edl.transcript import Transcript


@dataclass
class Problem:
    level: str   # error | warn
    msg: str


def validate(edl: EDL, project=None, tr: Transcript | None = None) -> list[Problem]:
    out: list[Problem] = []
    if tr is None and project is not None and project.transcript_json.exists():
        tr = Transcript.load(project.transcript_json)
    D = edl.meta.duration
    ids = [s.id for s in edl.segments]
    if len(ids) != len(set(ids)):
        out.append(Problem("error", "duplicate segment ids"))
    if not edl.segments:
        out.append(Problem("error", "no segments"))
    for s in edl.segments:
        if s.src_in < 0 or s.src_out > D + 0.05:
            out.append(Problem("error", f"segment {s.id} outside the source ({s.src_in}-{s.src_out} of {D})"))
    for a, b in zip(edl.segments, edl.segments[1:]):
        if b.src_in < a.src_out and b.src_in >= a.src_in:
            out.append(Problem("warn", f"segments {a.id} and {b.id} overlap in source time"))
    for c in edl.cards:
        if c.before_segment not in ids:
            out.append(Problem("error", f"card {c.id} references unknown segment {c.before_segment}"))
    for c in edl.captions:
        if len(c.words) > 3:
            out.append(Problem("error", f"caption {c.id} has more than three words"))

    def check(anchor, what: str) -> None:
        try:
            t = resolve_src(anchor, tr, edl)
        except (AnchorError, KeyError) as e:
            out.append(Problem("error", f"{what}: anchor {anchor.describe()} does not resolve ({e})"))
            return
        if t is not None and not any(s.src_in - 0.5 <= t <= s.src_out + 0.5 for s in edl.segments):
            out.append(Problem("warn", f"{what}: anchor {anchor.describe()} at {t:.2f}s lies in a cut stretch"))

    for z in edl.zooms:
        check(z.at, f"zoom {z.id}")
    for b in edl.beats:
        check(b.after, f"beat {b.id}")
    for c in edl.captions:
        check(c.at, f"caption {c.id}")
    for o in edl.overlays:
        check(o.at, f"overlay {o.id}")
    for v in edl.voiceover_slots:
        check(v.at, f"voiceover {v.id}")
    for m in edl.music:
        check(m.start, f"music {m.id} start")
        check(m.end, f"music {m.id} end")
    for d in edl.dropouts:
        check(d.start, f"dropout {d.id}")
    for f in edl.fadeouts:
        check(f.start, f"fadeout {f.id}")
    for s in edl.swells:
        check(s.start, f"swell {s.id}")
    for s in edl.sfx:
        check(s.at, f"sfx {s.id}")
        if (s.kind or "") == "riser":
            t = resolve_src(s.at, tr, edl)
            follow = [x for x in edl.sfx if x.kind in ("hit", "braaam") and resolve_src(x.at, tr, edl) is not None
                      and t is not None and 0 <= resolve_src(x.at, tr, edl) - t <= 1.5]  # type: ignore[operator]
            seg_in = {sg.id: sg.src_in for sg in edl.segments}
            cards = [c for c in edl.cards if t is not None and c.before_segment in seg_in
                     and 0 <= seg_in[c.before_segment] - t <= 1.5]
            drops = [d for d in edl.dropouts if t is not None and abs((resolve_src(d.start, tr, edl) or -99) - t) <= 1.5]
            if not (follow or drops or cards):
                out.append(Problem("warn", f"riser {s.id}: nothing lands after it (no hit, dropout or card); risers need a payoff"))
    # dropout density: more than one per 20 s gets noticed
    if len(edl.dropouts) > max(1, int(D / 20)) + 1:
        out.append(Problem("warn", f"{len(edl.dropouts)} dropouts in {D:.0f}s of source; more than one per 20 s stops being startling"))
    return out
