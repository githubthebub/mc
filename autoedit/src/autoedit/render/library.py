"""Music and SFX libraries from the profile folders, with synth placeholders as the fallback."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..media.audio import file_lufs, first_pickup
from ..media.synth import MOODS, SFX_KINDS, make_music, make_sfx_kit

AUDIO_EXT = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".aif", ".aiff"}
MOOD_ALIASES = {
    "calm": ["calm", "mellow", "soft", "ambient", "chill", "warm"],
    "tense": ["tense", "suspense", "dark", "mystery", "drone", "serious"],
    "playful": ["playful", "fun", "upbeat", "light", "happy", "quirky"],
    "build": ["build", "rising", "epic", "anticipation", "driving", "energetic"],
    "triumphant": ["triumph", "win", "payoff", "victory", "uplift"],
    "sad": ["sad", "melancholy", "emotional", "piano"],
}


def canonical_mood(mood: str) -> str:
    m = mood.lower().strip()
    for k, al in MOOD_ALIASES.items():
        if m == k or any(a in m for a in al):
            return k
    return m


@dataclass
class Track:
    file: Path
    moods: list[str]
    lufs: float | None = None
    pickup: float | None = None
    placeholder: bool = False


@dataclass
class MusicLibrary:
    root: Path | None
    tracks: list[Track] = field(default_factory=list)
    placeholder_dir: Path | None = None
    _cache: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path | None, placeholder_dir: Path) -> "MusicLibrary":
        lib = cls(root, placeholder_dir=placeholder_dir)
        if root and root.exists():
            meta_file = root / "library.yaml"
            meta = yaml.safe_load(meta_file.read_text()) if meta_file.exists() else {}
            cache_file = root / ".autoedit_cache.json"
            lib._cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
            for f in sorted(root.iterdir()):
                if f.suffix.lower() in AUDIO_EXT:
                    m = (meta or {}).get(f.name, {}) if isinstance(meta, dict) else {}
                    moods = m.get("moods") if isinstance(m, dict) else None
                    if not moods:
                        moods = [canonical_mood(tok) for tok in f.stem.replace("_", "-").split("-")]
                    lib.tracks.append(Track(f, [canonical_mood(x) for x in moods]))
        return lib

    @property
    def available(self) -> bool:
        return bool(self.tracks)

    def pick(self, mood: str, used: set[Path] | None = None) -> Track:
        """A licensed track matching the mood, else a synth placeholder bed for it."""
        m = canonical_mood(mood)
        used = used or set()
        cands = [t for t in self.tracks if m in t.moods and t.file not in used] or \
                [t for t in self.tracks if m in t.moods] or \
                [t for t in self.tracks if t.file not in used]
        if cands:
            return cands[0]
        return self.placeholder(m)

    def placeholder(self, mood: str) -> Track:
        synth_mood = mood if mood in MOODS else {"calm": "playful", "triumphant": "build", "sad": "tense"}.get(mood, "playful")
        assert self.placeholder_dir is not None
        f = self.placeholder_dir / f"placeholder_{synth_mood}.wav"
        if not f.exists():
            make_music(f, synth_mood, dur=120)
        return Track(f, [mood], placeholder=True)

    def measure(self, t: Track) -> Track:
        key = str(t.file)
        c = self._cache.get(key)
        if c and c.get("mtime") == t.file.stat().st_mtime:
            t.lufs, t.pickup = c["lufs"], c.get("pickup")
            return t
        t.lufs = file_lufs(t.file)
        t.pickup = first_pickup(t.file, after=1.0)
        self._cache[key] = {"mtime": t.file.stat().st_mtime, "lufs": t.lufs, "pickup": t.pickup}
        if self.root and self.root.exists():
            try:
                (self.root / ".autoedit_cache.json").write_text(json.dumps(self._cache))
            except OSError:
                pass
        return t


@dataclass
class SfxLibrary:
    root: Path | None
    files: dict[str, list[Path]] = field(default_factory=dict)
    placeholder: bool = False

    @classmethod
    def load(cls, root: Path | None, placeholder_dir: Path) -> "SfxLibrary":
        lib = cls(root)
        if root and root.exists():
            for f in sorted(root.iterdir()):
                if f.suffix.lower() in AUDIO_EXT:
                    kind = next((k for k in SFX_KINDS if k in f.stem.lower()), f.stem.lower().rstrip("0123456789_-"))
                    lib.files.setdefault(kind, []).append(f)
        if not lib.files:
            lib.files = {k: list(v) for k, v in make_sfx_kit(placeholder_dir).items()}
            lib.placeholder = True
        return lib

    def pick(self, kind: str, index: int = 0) -> Path | None:
        k = kind.lower()
        fs = self.files.get(k) or next((v for kk, v in self.files.items() if k in kk or kk in k), None)
        if not fs:
            if k in SFX_KINDS and not self.placeholder:
                return None
            return None
        return fs[index % len(fs)]
