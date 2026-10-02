"""Plan: the story pass and execution decisions with Claude (or a code-only baseline), assembled into
the EDL, plus the review artifacts: story_pass.md, plan_summary.md and a labelled preview.mp4."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from ..config import Settings
from ..edl.build import baseline_edl, cut_list, meta_from, trim_lead_and_tail
from ..edl.schema import (EDL, Anchor, Beat, Caption, Card, Chapter, Dropout, Fadeout, MontageSpec, MusicSection,
                          Segment, Sfx, Swell, ThumbnailSpec, TitleSpec, VoiceoverSlot, Zoom)
from ..edl.transcript import Transcript
from ..edl.validate import validate
from ..llm.client import LLM, LLMUnavailable, load_prompt
from ..llm.schemas import DecisionsOut, StoryPassOut
from ..log import StageLog
from ..profile import Profile
from ..project import Project, file_hash

Range = tuple[float, float]


# ---- range arithmetic -------------------------------------------------------------------

def subtract(ranges: list[Range], cut: Range) -> list[Range]:
    a, b = cut
    out: list[Range] = []
    for x, y in ranges:
        if y <= a or x >= b:
            out.append((x, y))
            continue
        if x < a:
            out.append((x, a))
        if y > b:
            out.append((b, y))
    return [(round(x, 3), round(y, 3)) for x, y in out if y - x >= 0.3]


def intersect(ranges: list[Range], win: Range) -> list[Range]:
    a, b = win
    return [(round(max(x, a), 3), round(min(y, b), 3)) for x, y in ranges if min(y, b) - max(x, a) >= 0.3]


# ---- prompt blocks ----------------------------------------------------------------------

def profile_block(profile: Profile, format_notes: str | None = None) -> str:
    return "\n".join([f"- channel: {profile.name} ({profile.handle or 'no handle'})", f"- format: {profile.format}" + (f": {format_notes}" if format_notes else ""),
                      f"- experience viewers come for: {profile.experience}",
                      f"- creator's voice: {profile.voice_notes or 'not described'}",
                      f"- captions: {profile.captions.style}, max {profile.captions.max_words} words",
                      f"- music library: {'provided' if profile.audio.music_dir else 'none (placeholders)'}"])


def analysis_block(a: dict[str, Any], tr: Transcript) -> str:
    pauses = a.get("pauses", [])
    long_p = sorted(pauses, key=lambda p: -(p[1] - p[0]))[:8]
    face = a.get("face") or {}
    L = [f"- duration {a['duration']:.1f} s, {a['width']}x{a['height']}; speech starts at {a.get('speech_start')} s",
         f"- {len(tr.words)} words in {len(tr.sentences)} sentences ({tr.model}{', DEGRADED transcript' if tr.degraded else ''})",
         f"- {len(pauses)} pauses >= 0.25 s totalling {a.get('pause_total_s')} s; longest: " +
         ", ".join(f"{s:.1f}-{e:.1f}" for s, e in long_p),
         f"- face on screen {face.get('present_fraction', 0) * 100:.0f}% of samples" if face.get("available") else "- no face detected",
         f"- loudest sentences (energy peaks): {a.get('energy_peak_sentences')}",
         "- assets provided: none (no B-roll, no stills) unless listed in the EDL overlays"]
    return "\n".join(L)


def words_block(tr: Transcript) -> str:
    return "\n".join(f"S{s.id}: {tr.words_for_llm(s.w0, s.w1)}" for s in tr.sentences)


def density_block(experience: str) -> str:
    return {
        "hangout": "Very sparse: a caption or zoom only for a genuinely key line; one music mood may run long; dropouts rare.",
        "informative": "A key-word caption roughly every 20-40 s on terms that matter; a zoom on each major takeaway; "
                       "dropouts on takeaways and punchlines (about one per 30 s at most); a fadeout at each section end; "
                       "a riser only before a real reveal.",
        "entertainment": "Dense: captions on punchlines and reactions, frequent zooms, dropouts on every punchline, hits on "
                         "big words, whooshes on graphics.",
    }[experience]


# ---- assembly ---------------------------------------------------------------------------

def assemble(base: EDL, tr: Transcript, analysis: dict[str, Any], profile: Profile, story: StoryPassOut,
             dec: DecisionsOut | None, dead_air: bool = True, captions: bool = True) -> tuple[EDL, list[str]]:
    notes: list[str] = []
    params = profile.dead_air_params()
    pad = float(params["pad"])
    D = base.meta.duration
    pauses = [(float(s), float(e)) for s, e in analysis.get("pauses", [])] if dead_air else []
    sids = {s.id for s in tr.sentences}
    wids = {w.id for w in tr.words}

    def sent(sid: int):
        return tr.sentence(sid) if sid in sids else None

    # protected pauses: the first pause after the sentence end
    protect: list[Range] = []
    for pp in story.protect_pauses:
        s = sent(pp.after_sentence)
        if not s:
            notes.append(f"protect_pauses: unknown sentence {pp.after_sentence}")
            continue
        p = next((p for p in pauses if s.t1 - 0.1 <= p[0] <= s.t1 + 1.0), None)
        if p:
            protect.append(p)
    if dead_air:
        ranges = cut_list(D, pauses, params, protect)
        ranges = trim_lead_and_tail(ranges, tr, pad, D)
    else:
        ranges = [(0.0, D)]
    cut_s = 0.0
    for cs in story.cut_sentences:
        s = sent(cs.sentence)
        if not s:
            notes.append(f"cut_sentences: unknown sentence {cs.sentence}")
            continue
        before = sum(b - a for a, b in ranges)
        ranges = subtract(ranges, (s.t0 - pad, s.t1 + pad))
        cut_s += before - sum(b - a for a, b in ranges)
    montages: list[tuple[float, float, Any]] = []
    for m in story.montages:
        s0, s1 = sent(m.from_sentence), sent(m.to_sentence)
        if not s0 or not s1 or s1.t1 <= s0.t0:
            notes.append(f"montages: bad range S{m.from_sentence}-S{m.to_sentence}")
            continue
        win = (s0.t0 - pad, s1.t1 + pad)
        ranges = subtract(ranges, win)
        montages.append((win[0], win[1], m))
    hook_pieces: list[Range] = []
    reordered = False
    if story.hook.hook_sentences:
        first = sent(story.hook.hook_sentences[0])
        already_first = bool(first and ranges and abs(ranges[0][0] - (first.t0 - pad)) < 1.0)
        if story.hook.reorder_to_front and not already_first:
            for sid in story.hook.hook_sentences:
                s = sent(sid)
                if not s:
                    notes.append(f"hook: unknown sentence {sid}")
                    continue
                win = (s.t0 - pad, s.t1 + pad)
                hook_pieces += intersect(ranges, win)
                ranges = subtract(ranges, win)
            reordered = bool(hook_pieces)
    items: list[tuple[str, float, float, Any]] = [("aroll", a, b, None) for a, b in hook_pieces]
    items += sorted([("aroll", a, b, None) for a, b in ranges] + [("montage", a, b, m) for a, b, m in montages],
                    key=lambda x: x[1])
    segments: list[Segment] = []
    for i, (kind, a, b, m) in enumerate(items):
        seg = Segment(id=f"s{i + 1}", kind=kind, src_in=a, src_out=b)  # type: ignore[arg-type]
        if m is not None:
            seg.montage = MontageSpec(target_s=max(5.0, min(40.0, m.target_s)))
            seg.notes = m.reason
        segments.append(seg)

    edl = base.model_copy(deep=True)
    edl.segments = segments
    edl.story_pass = list(story.story_pass)
    edl.notes = []

    def seg_containing(t: float) -> Segment | None:
        return next((s for s in edl.segments if s.src_in <= t <= s.src_out), None)

    def split_segment_at(t: float) -> Segment | None:
        """Make a segment boundary at source time t; return the segment that starts there."""
        for i, s in enumerate(edl.segments):
            if s.kind != "aroll":
                continue
            if abs(s.src_in - t) < 0.2:
                return s
            if s.src_in < t < s.src_out and t - s.src_in >= 0.3 and s.src_out - t >= 0.3:
                tail = Segment(id=f"{s.id}b", kind="aroll", src_in=round(t, 3), src_out=s.src_out, notes=s.notes)
                s.src_out = round(t, 3)
                edl.segments.insert(i + 1, tail)
                return tail
        return next((s for s in edl.segments if s.src_in >= t), None)

    # chapters and cards
    for ch in story.chapters:
        s = sent(ch.at_sentence)
        if not s:
            notes.append(f"chapters: unknown sentence {ch.at_sentence}")
            continue
        edl.chapters.append(Chapter(title=ch.title, at=Anchor(sentence=s.id)))
        if ch.card:
            target = split_segment_at(s.t0 - pad)
            if target:
                edl.cards.append(Card(id=f"card{len(edl.cards) + 1}", before_segment=target.id, text=ch.title,
                                      number=ch.number, dur=profile.cards.duration))
    # voiceover slots
    for g in story.litmus_gaps:
        s = sent(g.after_sentence)
        if not s:
            notes.append(f"litmus_gaps: unknown sentence {g.after_sentence}")
            continue
        edl.voiceover_slots.append(VoiceoverSlot(id=f"vo{len(edl.voiceover_slots) + 1}", at=Anchor(sentence=s.id, edge="end", pad=0.05),
                                                 line=g.line.strip(), reason=f"{g.gap}: {g.reason}"))
    # beats
    for b in story.beats:
        if b.after_word not in wids:
            notes.append(f"beats: unknown word {b.after_word}")
            continue
        edl.beats.append(Beat(id=f"b{len(edl.beats) + 1}", after=Anchor(word=b.after_word, edge="end"),
                              dur=max(0.5, min(5.0, b.dur)), fill=b.fill if b.text else "none",
                              text=" ".join((b.text or "").split()[:3]) or None,
                              sfx=None if b.sfx == "none" else b.sfx, reason=b.reason))
    # music sections: anchored to segments in OUTPUT order so a hook moved to the front stays covered
    hook_ids = set(story.hook.hook_sentences) if reordered else set()
    n_hook = len(hook_pieces)
    plans = sorted(story.music, key=lambda m: m.from_sentence)
    body = edl.segments[n_hook:]
    for i, m in enumerate(plans):
        s0, s1 = sent(m.from_sentence), sent(m.to_sentence)
        if not s0 or not s1:
            notes.append(f"music: unknown sentence in S{m.from_sentence}-S{m.to_sentence}")
            continue
        cands = [sg for sg in body if sg.src_in >= s0.t0 - pad - 0.1 and sg.src_out <= s1.t1 + pad + 0.1]
        if not cands:
            notes.append(f"music: S{m.from_sentence}-S{m.to_sentence} has no kept segment, skipped")
            continue
        start = Anchor(segment=edl.segments[0].id) if i == 0 else Anchor(segment=cands[0].id)
        end = Anchor(segment=edl.segments[-1].id, edge="end") if i == len(plans) - 1 else Anchor(segment=cands[-1].id, edge="end")
        pick = None
        if m.pickup_at_sentence in sids and m.pickup_at_sentence not in hook_ids:
            pick = Anchor(sentence=m.pickup_at_sentence)
        elif m.pickup_at_sentence is not None:
            notes.append(f"music {i + 1}: pickup sentence S{m.pickup_at_sentence} is in the moved hook, ignored")
        edl.music.append(MusicSection(id=f"m{i + 1}", start=start, end=end, mood=m.mood, pickup_at=pick,
                                      rel_db=profile.audio.music_rel_db, reason=m.reason))
    # execution decisions
    if dec is not None:
        if not captions and dec.captions:
            notes.append(f"{len(dec.captions)} captions dropped: the words are already on screen in this format")
        for c in (dec.captions if captions else []):
            if c.word_from not in wids or c.word_to not in wids or c.word_to < c.word_from:
                notes.append(f"captions: bad word range {c.word_from}-{c.word_to}")
                continue
            words = [w for w in c.words if w.strip()][:profile.captions.max_words]
            if not words:
                continue
            emph = c.emphasis if c.emphasis is not None and 0 <= c.emphasis < len(words) else None
            edl.captions.append(Caption(id=f"c{len(edl.captions) + 1}", at=Anchor(word=c.word_from),
                                        end=Anchor(word=c.word_to, edge="end", pad=0.25), words=words, emphasis=emph, reason=c.reason))
        for d in dec.dropouts:
            s = sent(d.sentence)
            if not s:
                notes.append(f"dropouts: unknown sentence {d.sentence}")
                continue
            edl.dropouts.append(Dropout(id=f"d{len(edl.dropouts) + 1}", start=Anchor(sentence=s.id, pad=-0.15),
                                        end=Anchor(sentence=s.id, edge="end", pad=0.4), reason=d.reason))
        for f in dec.fadeouts:
            s = sent(f.ends_at_sentence)
            if not s:
                notes.append(f"fadeouts: unknown sentence {f.ends_at_sentence}")
                continue
            if s.id in hook_ids:
                notes.append(f"fadeouts: S{s.id} was moved into the hook, fadeout dropped")
                continue
            # fade over ~20 s but never from before the section (or the video) starts
            sec_start = next((sent(m.from_sentence).t0 for m in plans if sent(m.from_sentence) and sent(m.to_sentence)
                              and m.from_sentence <= s.id <= m.to_sentence), None)
            earliest = max(0.5, (sec_start + 2.0) if sec_start is not None else 0.5)
            start_t = max(earliest, s.t1 - profile.audio.fadeout_s)
            if s.t1 - start_t < 4.0:
                notes.append(f"fadeouts: section ending at S{s.id} is too short for a fadeout, dropped")
                continue
            edl.fadeouts.append(Fadeout(id=f"f{len(edl.fadeouts) + 1}", start=Anchor(src=round(start_t, 3)),
                                        end=Anchor(sentence=s.id, edge="end"), reason=f.reason))
        for sw in dec.swells:
            s = sent(sw.into_sentence)
            if not s:
                notes.append(f"swells: unknown sentence {sw.into_sentence}")
                continue
            if s.id in hook_ids:
                notes.append(f"swells: S{s.id} was moved into the hook, swell dropped")
                continue
            sec_start = next((sent(m.from_sentence).t0 for m in plans if sent(m.from_sentence) and sent(m.to_sentence)
                              and m.from_sentence <= s.id <= m.to_sentence), None)
            start_t = max(0.5, (sec_start + 1.0) if sec_start is not None else 0.5, s.t0 - 8.0)
            if s.t0 - start_t < 2.0:
                notes.append(f"swells: no room before S{s.id} for a swell, dropped")
                continue
            edl.swells.append(Swell(id=f"w{len(edl.swells) + 1}", start=Anchor(src=round(start_t, 3)),
                                    end=Anchor(sentence=s.id, pad=-0.05), db=max(2.0, min(10.0, sw.db)), reason=sw.reason))
        for z in dec.zooms:
            if z.word_from not in wids or z.word_to not in wids or z.word_to < z.word_from:
                notes.append(f"zooms: bad word range {z.word_from}-{z.word_to}")
                continue
            edl.zooms.append(Zoom(id=f"z{len(edl.zooms) + 1}", at=Anchor(word=z.word_from), end=Anchor(word=z.word_to, edge="end"),
                                  scale=max(1.15, min(1.5, z.scale)), reason=z.reason))
        for x in dec.sfx:
            if x.word not in wids:
                notes.append(f"sfx: unknown word {x.word}")
                continue
            edl.sfx.append(Sfx(id=f"x{len(edl.sfx) + 1}", at=Anchor(word=x.word, edge="end" if x.align == "end" else "start"),
                               kind=x.kind, align=x.align, reason=x.reason))
        edl.notes += list(dec.notes)
    # packaging
    if story.title_options:
        edl.title = TitleSpec(chosen=story.title_options[0], alternatives=story.title_options[1:], rationale=story.biggest_risk)
    if story.thumbnail_ideas:
        ti = story.thumbnail_ideas[0]
        edl.thumbnail = ThumbnailSpec(spotlight=ti.spotlight, text=" ".join((ti.text or "").split()[:3]) or None,
                                      mood_color=ti.mood_color, idea=ti.idea)
    # ledger
    kept = sum(s.src_out - s.src_in for s in edl.segments)
    edl.mark("story_pass", "executed", f"{len(story.story_pass)} sections; {story.experience_fit}", "plan", len(story.story_pass))
    hs = story.hook.hook_sentences
    edl.mark("hook_proof_early", "executed" if hs else "not_executed",
             (f"opens on S{hs[0]}{' (moved to front)' if reordered else ''}: {story.hook.rationale}") if hs else "planner found no hook moment", "plan")
    edl.mark("litmus_voiceover", "executed" if edl.voiceover_slots else "not_executed",
             f"{len(edl.voiceover_slots)} lines written for the creator to record" if edl.voiceover_slots else "no clarity gaps found", "plan",
             len(edl.voiceover_slots))
    if dead_air:
        edl.mark("dead_air_removal", "executed", f"{profile.experience} preset; {D - kept:.1f} s removed incl. {cut_s:.1f} s of cut sentences; "
                 f"{len(protect)} pauses protected", "plan", len(edl.segments))
    else:
        edl.mark("dead_air_removal", "not_executed", f"scripted format: every pause is deliberate ({cut_s:.1f} s of cut scenes)", "plan")
    edl.mark("montage_compression", "executed" if montages else "not_executed",
             f"{len(montages)} ranges" if montages else "planner found no stretch without conflict or curiosity", "plan", len(montages))
    return edl, notes


def merge_extras(edl: EDL, extras: dict[str, Any], profile: Profile) -> list[str]:
    """Format-requested items: sfx and zooms by source time, a default music mood when the planner gave none."""
    notes: list[str] = []
    for i, x in enumerate(extras.get("sfx", [])):
        edl.sfx.append(Sfx(id=f"fx{i + 1}", at=Anchor(src=float(x["src"])), kind=x.get("kind"), gain_db=float(x.get("gain_db", 0.0)),
                           align=x.get("align", "start"), reason=x.get("reason")))
    for i, z in enumerate(extras.get("zooms", [])):
        edl.zooms.append(Zoom(id=f"fz{i + 1}", at=Anchor(src=float(z["src_in"])), end=Anchor(src=float(z["src_out"])),
                              scale=float(z.get("scale", 1.18)), reason=z.get("reason")))
    if not edl.music and edl.segments and extras.get("music_mood"):
        edl.music.append(MusicSection(id="m1", start=Anchor(segment=edl.segments[0].id),
                                      end=Anchor(segment=edl.segments[-1].id, edge="end"), mood=str(extras["music_mood"]),
                                      rel_db=profile.audio.music_rel_db, reason="format default mood (no planner music)"))
    if extras.get("sfx") or extras.get("zooms"):
        notes.append(f"format extras merged: {len(extras.get('sfx', []))} sfx, {len(extras.get('zooms', []))} zooms")
    return notes


# ---- summary ----------------------------------------------------------------------------

def _t(tr: Transcript, a: Anchor) -> str:
    from ..edl.resolve import resolve_src
    try:
        t = resolve_src(a, tr, None)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return a.describe()
    return f"{t:.1f}s" if t is not None else a.describe()


def write_summary(edl: EDL, tr: Transcript | None, story: StoryPassOut | None, notes: list[str], problems, out: Path,
                  model: str | None) -> None:
    L = [f"# Plan: {edl.meta.project}", "",
         f"- Profile **{edl.meta.profile}** ({edl.meta.experience}); source {edl.meta.duration:.1f} s; planned by {model or 'code only'}",
         f"- Kept {sum(s.src_out - s.src_in for s in edl.segments):.1f} s in {len(edl.segments)} segments "
         f"({len([s for s in edl.segments if s.kind == 'montage'])} montages)", ""]
    if story:
        L += ["## Experience fit", "", story.experience_fit, "", "## Biggest risk", "", story.biggest_risk, ""]
        L += ["## Story pass", "", "| Time | What happens | Green/purple | Conflict | Mood | Litmus gaps | Action |", "|---|---|---|---|---|---|---|"]
        for r in story.story_pass:
            L.append(f"| {r.time} | {r.what_happens} | {r.color} | {r.conflict} | {r.mood} | {'; '.join(r.litmus_gaps)} | {r.action} |")
        L += ["", "## Hook", "", f"Sentences {story.hook.hook_sentences}; reorder to front: {story.hook.reorder_to_front}; "
              f"premise restated: {story.hook.premise_restated}", "", story.hook.rationale, ""]
        if tr:
            for sid in story.hook.hook_sentences:
                try:
                    L.append(f"- S{sid}: {tr.sentence(sid).text}")
                except KeyError:
                    pass
            L.append("")
    if edl.voiceover_slots:
        L += ["## Voiceover lines to record", ""]
        for v in edl.voiceover_slots:
            L.append(f"- **{v.id}** at {_t(tr, v.at) if tr else v.at.describe()} ({v.reason}): \"{v.line}\"")
        L.append("")
    L += ["## Segments (output order)", "", "| id | kind | source | first words |", "|---|---|---|---|"]
    for s in edl.segments:
        first = " ".join(w.text for w in tr.words_in(s.src_in, s.src_in + 2.5))[:50] if tr else ""
        L.append(f"| {s.id} | {s.kind} | {s.src_in:.1f}-{s.src_out:.1f} | {first} |")
    L.append("")

    def section(title: str, rows: list[str]) -> None:
        if rows:
            L.extend([f"## {title}", "", *rows, ""])

    tt = (lambda a: _t(tr, a)) if tr else (lambda a: a.describe())
    section("Cards", [f"- {c.id} before {c.before_segment}: {c.number or ''} {c.text}" for c in edl.cards])
    section("Captions", [f"- {c.id} at {tt(c.at)}: **{' '.join(c.words)}** ({c.reason or ''})" for c in edl.captions])
    section("Zooms", [f"- {z.id} at {tt(z.at)} x{z.scale}: {z.reason or ''}" for z in edl.zooms])
    section("Beats", [f"- {b.id} after {tt(b.after)} for {b.dur}s, fill {b.fill} {b.text or ''}: {b.reason or ''}" for b in edl.beats])
    section("Music", [f"- {m.id} {m.mood} from {tt(m.start)} to {tt(m.end)}" + (f", pickup on {tt(m.pickup_at)}" if m.pickup_at else "") + f": {m.reason or ''}" for m in edl.music])
    section("Dropouts", [f"- {d.id} {tt(d.start)}-{tt(d.end)}: {d.reason or ''}" for d in edl.dropouts])
    section("Fadeouts", [f"- {f.id} {tt(f.start)}-{tt(f.end)}: {f.reason or ''}" for f in edl.fadeouts])
    section("Swells", [f"- {s.id} {tt(s.start)}-{tt(s.end)} +{s.db} dB: {s.reason or ''}" for s in edl.swells])
    section("SFX", [f"- {x.id} {x.kind} at {tt(x.at)} ({x.align}): {x.reason or ''}" for x in edl.sfx])
    section("Chapters", [f"- {tt(c.at)} {c.title}" for c in edl.chapters])
    if edl.title:
        section("Title", [f"- **{edl.title.chosen}**", *[f"- {a}" for a in edl.title.alternatives]])
    if edl.thumbnail:
        section("Thumbnail", [f"- spotlight {edl.thumbnail.spotlight}, text '{edl.thumbnail.text}', {edl.thumbnail.mood_color}: {edl.thumbnail.idea or ''}"])
    section("Planner notes", [f"- {n}" for n in edl.notes + notes])
    section("Validation", [f"- {p.level}: {p.msg}" for p in problems])
    L += ["## Technique ledger (so far)", ""]
    for k, t in edl.techniques.items():
        if t.status != "planned":
            L.append(f"- {k}: **{t.status}** {t.reason or ''}")
    L += ["", "## Next", "", "Watch `preview.mp4` (labels show each decision). Edit `edl.json` if needed, then "
          "`autoedit approve <project>` and `autoedit render <project>`.", ""]
    out.write_text("\n".join(L))


# ---- stage ------------------------------------------------------------------------------

def run(project: Project, settings: Settings, profile: Profile, log: StageLog | None = None, *, llm: str = "auto") -> EDL:
    log = log or project.log("plan")
    project.begin("plan", file_hash(project.transcript_json) if project.transcript_json.exists() else None)
    try:
        tr = Transcript.load(project.transcript_json) if project.transcript_json.exists() else None
        analysis = json.loads(project.analysis_json.read_text())
        meta = meta_from(project.name, profile, project.format, str(project.source), analysis["duration"], analysis["fps"],
                         analysis["width"], analysis["height"])
        from ..formats import get_format
        fmt = get_format(project.format)
        base = baseline_edl(meta, tr, analysis, profile, dead_air=fmt.dead_air)
        d = project.dir("plan")
        story: StoryPassOut | None = None
        dec: DecisionsOut | None = None
        notes: list[str] = []
        model_used: str | None = None
        client = LLM(settings, d / "llm", mode=llm, log=log)
        if llm == "off" or tr is None or not tr.words:
            reason = "planner disabled (--llm off)" if llm == "off" else "no transcript (no transcriber available)"
            notes.append(f"{reason}: baseline EDL (dead-air removal only)")
            edl = base
            edl.mark("story_pass", "not_executed", reason, "plan")
            edl.mark("hook_proof_early", "not_executed", reason, "plan")
            edl.mark("litmus_voiceover", "not_executed", reason, "plan")
        elif llm == "auto" and not client.available:
            notes.append("ANTHROPIC_API_KEY not set: baseline EDL (dead-air removal only). Set the key and re-run `autoedit plan`.")
            log.warn("no API key; planning without the model")
            edl = base
            for k in ("story_pass", "hook_proof_early", "litmus_voiceover"):
                edl.mark(k, "not_executed", "ANTHROPIC_API_KEY not set", "plan")
        else:
            log.progress(0.05, "story pass")
            user1 = load_prompt("story_pass").format(profile_block=profile_block(profile, fmt.planner_notes),
                                                     analysis_block=analysis_block(analysis, tr),
                                                     transcript_block=tr.numbered_for_llm({int(k): v for k, v in (analysis.get("sentence_energy_db") or {}).items()}))
            story = client.call("story_pass", user1, StoryPassOut)
            log.progress(0.45, "decisions")
            user2 = load_prompt("decisions").format(story_pass_json=json.dumps(story.model_dump(mode="json"), indent=1),
                                                    words_block=words_block(tr), experience=profile.experience,
                                                    density_block=density_block(profile.experience))
            dec = client.call("decisions", user2, DecisionsOut)
            model_used = settings.llm.model if llm != "replay" else "replay"
            edl, notes = assemble(base, tr, analysis, profile, story, dec, dead_air=fmt.dead_air, captions=fmt.captions)
            edl.meta.created_by = "llm"
            edl.meta.model = model_used
            (d / "story_pass.json").write_text(json.dumps(story.model_dump(mode="json"), indent=1))
            (d / "decisions.json").write_text(json.dumps(dec.model_dump(mode="json"), indent=1))
        notes += merge_extras(edl, fmt.extras(project), profile)
        problems = validate(edl, project, tr)
        for p in problems:
            (log.warn if p.level == "error" else log.info)(f"validation {p.level}: {p.msg}")
        edl.save(project.edl_json)
        write_summary(edl, tr, story, notes, problems, d / "plan_summary.md", model_used)
        log.progress(0.6, "preview")
        from . import render as render_stage
        try:
            render_stage.run(project, settings, profile, project.log("preview", quiet=True), preview=True)
            prev = project.dir("render") / "preview" / "preview.mp4"
            if prev.exists():
                shutil.copy2(prev, d / "preview.mp4")
        except Exception as e:  # noqa: BLE001
            log.warn("preview render failed", error=repr(e))
            notes.append(f"preview failed: {e!r}")
        project.finish("plan", edl_hash=file_hash(project.edl_json), model=model_used, segments=len(edl.segments),
                       errors=len([p for p in problems if p.level == "error"]))
        log.done(segments=len(edl.segments), captions=len(edl.captions), music=len(edl.music))
        return edl
    except Exception as e:
        project.fail("plan", repr(e))
        log.error("failed", error=repr(e))
        raise
