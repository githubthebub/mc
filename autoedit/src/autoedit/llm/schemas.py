"""Response schemas for the planner. The model references sentence and word ids, never raw timestamps.
Constraints that the structured-output grammar may not support (lengths, ranges) are enforced in code
after parsing."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..edl.schema import StoryRow


class HookPlan(BaseModel):
    hook_sentences: list[int] = Field(description="Sentence ids that form the hook, in play order. The most extraordinary moment first: proof, not promise.")
    reorder_to_front: bool = Field(description="True if those sentences are not already at the start and must be moved to the front.")
    premise_restated: bool = Field(description="True if the premise from the title/thumbnail is restated clearly within the hook.")
    rationale: str


class LitmusGap(BaseModel):
    after_sentence: int = Field(description="The voiceover plays right after this sentence.")
    gap: Literal["what_is_happening", "why_it_matters", "what_could_go_wrong"]
    line: str = Field(description="The voiceover line, in the creator's voice, short and specific.")
    reason: str


class MontageRange(BaseModel):
    from_sentence: int
    to_sentence: int
    target_s: float = Field(description="Target montage length in seconds, usually 10-25.")
    reason: str


class BeatPlan(BaseModel):
    after_word: int = Field(description="The voice pauses right after this word id.")
    dur: float = Field(description="Seconds of pause, 0.6-2.5 for a short beat, up to 5 for an emotional break.")
    fill: Literal["none", "caption"]
    text: str | None = Field(description="Up to three words shown during the beat when fill is caption.")
    sfx: Literal["pop", "whoosh", "shutter", "none"]
    reason: str


class ProtectPause(BaseModel):
    after_sentence: int = Field(description="Keep the natural pause after this sentence (anticipation, after a payoff).")
    reason: str


class MusicPlan(BaseModel):
    from_sentence: int
    to_sentence: int
    mood: Literal["calm", "tense", "playful", "build", "triumphant", "sad"]
    pickup_at_sentence: int | None = Field(description="A sentence inside this section where the song's pickup should land (the topic shift), or null.")
    reason: str


class ChapterPlan(BaseModel):
    at_sentence: int
    title: str = Field(description="Short signpost, e.g. 'Fix 2: Sound'.")
    number: int | None
    card: bool = Field(description="Show a chapter card before this sentence.")


class CutSentence(BaseModel):
    sentence: int
    reason: str = Field(description="tangent, repeat, bad take, or a stretch with no conflict and no curiosity")


class ThumbIdea(BaseModel):
    spotlight: Literal["face", "text", "object"]
    text: str | None = Field(description="Up to three words, never an explanation, or null.")
    idea: str
    mood_color: Literal["warm", "cool", "neutral"]


class StoryPassOut(BaseModel):
    experience_fit: str = Field(description="One or two sentences: what these viewers come for and how the edit serves it.")
    story_pass: list[StoryRow] = Field(description="One row per section. time like 'S0-S3 (0:00-0:14)'.")
    hook: HookPlan
    litmus_gaps: list[LitmusGap]
    cut_sentences: list[CutSentence]
    montages: list[MontageRange]
    beats: list[BeatPlan]
    protect_pauses: list[ProtectPause]
    music: list[MusicPlan] = Field(description="Cover the whole video with consecutive sections; one mood each; split at subject or emotion changes.")
    chapters: list[ChapterPlan]
    title_options: list[str] = Field(description="3 to 5 titles: the driving question or the single most intriguing part, key words first, new-viewer language.")
    thumbnail_ideas: list[ThumbIdea]
    biggest_risk: str = Field(description="Where a diehard fan of the niche would click off, and why.")


class CaptionPlan(BaseModel):
    word_from: int
    word_to: int
    words: list[str] = Field(description="The key words to show, three or fewer, as spoken.")
    emphasis: int | None = Field(description="Index into words of the one to color with the accent, or null.")
    reason: str


class DropoutPlan(BaseModel):
    sentence: int
    reason: Literal["punchline", "takeaway", "key_line", "intimate"]


class FadeoutPlan(BaseModel):
    ends_at_sentence: int = Field(description="The section ends after this sentence; the music fades out over the ~20 s before it.")
    reason: str


class SwellPlan(BaseModel):
    into_sentence: int = Field(description="The payoff sentence the swell builds into.")
    db: float = Field(description="Usually 4-8.")
    reason: str


class ZoomPlan(BaseModel):
    word_from: int
    word_to: int
    scale: float = Field(description="1.2 to 1.4.")
    reason: str


class SfxPlan(BaseModel):
    word: int
    kind: Literal["riser", "hit", "whoosh", "pop", "shutter"]
    align: Literal["start", "end"] = Field(description="Risers end ON the moment ('end'); hits land on the word ('start').")
    reason: str


class DecisionsOut(BaseModel):
    captions: list[CaptionPlan]
    dropouts: list[DropoutPlan]
    fadeouts: list[FadeoutPlan]
    swells: list[SwellPlan]
    zooms: list[ZoomPlan]
    sfx: list[SfxPlan]
    notes: list[str] = Field(description="Anything the editor should know: judgment calls, what needs the creator's eyes.")


class ShortCandidate(BaseModel):
    id: str
    hook_sentence: int = Field(description="The strongest line; the short starts on it.")
    from_sentence: int
    to_sentence: int
    hook_strength: float = Field(description="0-10")
    self_contained: float = Field(description="0-10: makes sense with no context")
    payoff: float = Field(description="0-10")
    title: str
    context_label: str = Field(description="A persistent 2-5 word label that tells a cold viewer what this is.")
    reason: str


class ShortsOut(BaseModel):
    candidates: list[ShortCandidate]
