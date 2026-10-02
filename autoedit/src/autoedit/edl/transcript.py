"""Word-level transcript model shared by every stage."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

SENTENCE_GAP_S = 0.6
END_PUNCT = (".", "?", "!")


class Word(BaseModel):
    id: int
    text: str
    t0: float
    t1: float
    p: float = 1.0
    s: int = 0          # sentence id


class Sentence(BaseModel):
    id: int
    t0: float
    t1: float
    text: str
    w0: int             # first word id
    w1: int             # last word id (inclusive)
    energy_db: float | None = None


class Transcript(BaseModel):
    language: str = "en"
    model: str = "unknown"
    source_duration: float = 0.0
    words: list[Word] = Field(default_factory=list)
    sentences: list[Sentence] = Field(default_factory=list)
    degraded: bool = False          # True when produced by keyword spotting rather than full ASR
    notes: list[str] = Field(default_factory=list)

    # ---- lookups ----
    def word(self, wid: int) -> Word:
        w = self.words[wid] if 0 <= wid < len(self.words) and self.words[wid].id == wid else None
        if w is None:
            w = next((x for x in self.words if x.id == wid), None)
        if w is None:
            raise KeyError(f"no word {wid}")
        return w

    def sentence(self, sid: int) -> Sentence:
        s = next((x for x in self.sentences if x.id == sid), None)
        if s is None:
            raise KeyError(f"no sentence {sid}")
        return s

    def words_in(self, t0: float, t1: float) -> list[Word]:
        return [w for w in self.words if w.t0 < t1 and w.t1 > t0]

    def sentence_at(self, t: float) -> Sentence | None:
        for s in self.sentences:
            if s.t0 <= t <= s.t1:
                return s
        return None

    def first_word_time(self) -> float | None:
        return self.words[0].t0 if self.words else None

    # ---- construction ----
    @staticmethod
    def group_sentences(words: list[Word], gap: float = SENTENCE_GAP_S) -> list[Sentence]:
        sents: list[Sentence] = []
        cur: list[Word] = []

        def flush() -> None:
            if cur:
                sid = len(sents)
                for w in cur:
                    w.s = sid
                sents.append(Sentence(id=sid, t0=cur[0].t0, t1=cur[-1].t1,
                                      text=" ".join(w.text for w in cur), w0=cur[0].id, w1=cur[-1].id))
                cur.clear()

        for i, w in enumerate(words):
            if cur and (w.t0 - cur[-1].t1 > gap):
                flush()
            cur.append(w)
            if w.text.rstrip('"\')').endswith(END_PUNCT):
                flush()
        flush()
        return sents

    # ---- io ----
    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.model_dump(mode="json"), indent=1))
        return path

    @classmethod
    def load(cls, path: Path) -> "Transcript":
        return cls.model_validate(json.loads(Path(path).read_text()))

    def to_srt(self) -> str:
        def ts(t: float) -> str:
            ms = int(round(t * 1000))
            return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
        return "".join(f"{i + 1}\n{ts(s.t0)} --> {ts(s.t1)}\n{s.text}\n\n" for i, s in enumerate(self.sentences))

    def to_markdown(self) -> str:
        lines = [f"# Transcript ({self.model}, {self.language}){' DEGRADED' if self.degraded else ''}", ""]
        for s in self.sentences:
            lines.append(f"- **[{s.t0:7.2f} - {s.t1:7.2f}] #{s.id}** (words {s.w0}-{s.w1}) {s.text}")
        return "\n".join(lines) + "\n"

    def numbered_for_llm(self, energy: dict[int, float] | None = None) -> str:
        """Sentences with ids, times and word id ranges, as the planner sees them."""
        out = []
        for s in self.sentences:
            e = f" energy={energy[s.id]:+.0f}dB" if energy and s.id in energy else ""
            out.append(f"S{s.id} [{s.t0:.2f}-{s.t1:.2f}] words {s.w0}-{s.w1}{e}: {s.text}")
        return "\n".join(out)

    def words_for_llm(self, w0: int, w1: int) -> str:
        return " ".join(f"{w.text}⟨{w.id}⟩" for w in self.words if w0 <= w.id <= w1)
