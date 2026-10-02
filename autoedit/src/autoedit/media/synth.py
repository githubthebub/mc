"""Original placeholder audio (synth_audio.py), used only when a profile has no licensed library.

Quality is basic. Every use is recorded in the technique ledger so the QA report
tells the user to replace them.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 48000
SFX_KINDS = ("whoosh", "pop", "riser", "hit", "shutter", "click")
MOODS = ("playful", "tense", "build")


def save_wav(path: str | Path, x: np.ndarray, stereo: bool = True) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    x = np.clip(x / (np.max(np.abs(x)) + 1e-9) * 0.89, -1, 1)
    y = (x * 32767).astype(np.int16)
    if stereo:
        y = np.stack([y, y], 1).ravel()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2 if stereo else 1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(y.tobytes())
    return path


def env(n: int, a: float = 0.005, d: float = 0.1, s: float = 0.0, r: float = 0.05) -> np.ndarray:
    e = np.ones(n) * s
    A, D = int(a * SR), int(d * SR)
    if A:
        e[:A] = np.linspace(0, 1, A, endpoint=False)
    seg = e[A:A + D]
    seg[:] = np.linspace(1, s, min(D, max(0, n - A)))[:len(seg)]
    R = int(r * SR)
    if 0 < R < n:
        e[-R:] *= np.linspace(1, 0, R)
    return e


def lp(x: np.ndarray, alpha: float | np.ndarray) -> np.ndarray:
    """One-pole lowpass; alpha may vary per sample."""
    y = np.zeros_like(x)
    acc = 0.0
    al = np.broadcast_to(alpha, x.shape)
    for i in range(len(x)):
        acc += al[i] * (x[i] - acc)
        y[i] = acc
    return y


def noise(n: int, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal(n)


def whoosh(d: float = 0.55, seed: int = 0, up: bool = True) -> np.ndarray:
    n = int(d * SR)
    t = np.linspace(0, 1, n)
    cut = (0.02 + 0.25 * t) if up else (0.27 - 0.25 * t)
    x = lp(noise(n, seed), cut) - lp(noise(n, seed), cut * 0.2)
    return x * np.sin(np.pi * t) ** 1.5


def pop(f: float = 900, seed: int = 0) -> np.ndarray:
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    fr = f * np.exp(-t * 25)
    ph = 2 * np.pi * np.cumsum(fr) / SR
    return np.sin(ph) * np.exp(-t * 40)


def riser(d: float = 3.0) -> np.ndarray:
    n = int(d * SR)
    t = np.linspace(0, 1, n)
    fr = 200 + 1800 * t ** 2
    ph = 2 * np.pi * np.cumsum(fr) / SR
    tone = np.sin(ph) * 0.5 + np.sin(ph * 1.5) * 0.2
    nz = lp(noise(n, 3), 0.02 + 0.3 * t)
    x = (tone + nz * 1.5) * t ** 2
    x[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return x


def hit() -> np.ndarray:
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(55 * np.exp(-t * 3) + 35) / SR) * np.exp(-t * 3.5)
    crack = lp(noise(n, 5), 0.4) * np.exp(-t * 18)
    return boom * 1.2 + crack * 0.6


def shutter() -> np.ndarray:
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    c1 = lp(noise(n, 7), 0.6) * np.exp(-t * 90)
    c2 = np.roll(lp(noise(n, 8), 0.5) * np.exp(-t * 70), int(0.07 * SR))
    return c1 + c2 * 0.8


def click(seed: int = 0) -> np.ndarray:
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    return lp(noise(n, seed + 11), 0.7) * np.exp(-t * 200)


def note(f: float, d: float, kind: str = "pluck", vel: float = 1.0) -> np.ndarray:
    n = int(d * SR)
    t = np.arange(n) / SR
    if kind == "pluck":
        x = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) + 0.1 * np.sin(6 * np.pi * f * t)) * np.exp(-t * 6)
    elif kind == "pad":
        x = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t) + 0.25 * np.sin(4 * np.pi * f * t)) * env(n, 0.3, 0.2, 0.8, 0.4)
    elif kind == "stab":
        x = np.sign(np.sin(2 * np.pi * f * t)) * 0.4 * np.exp(-t * 14)
        x = lp(x, 0.15)
    else:  # bass
        x = np.sin(2 * np.pi * f * t) * env(n, 0.005, 0.15, 0.6, 0.05)
    return x * vel


def drum(kind: str, seed: int = 0) -> np.ndarray:
    if kind == "kick":
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        return np.sin(2 * np.pi * np.cumsum(50 + 90 * np.exp(-t * 30)) / SR) * np.exp(-t * 9)
    if kind == "hat":
        n = int(0.06 * SR)
        t = np.arange(n) / SR
        x = noise(n, seed)
        x = x - lp(x, 0.5)
        return x * np.exp(-t * 60) * 0.35
    n = int(0.03 * SR)  # tick
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 150) * 0.25


def music(mood: str, bpm: float = 110, dur: float = 60, key: int = 0) -> np.ndarray:
    """A music bed with a clear PICKUP (drums enter) at bar 3, findable with music_points."""
    beat = 60 / bpm
    n = int(dur * SR)
    out = np.zeros(n + SR * 2)

    def put(x: np.ndarray, t: float) -> None:
        i = int(t * SR)
        out[i:i + len(x)] += x[:max(0, len(out) - i)]

    def mf(m: int) -> float:
        return 440 * 2 ** ((m - 69 + key) / 12)

    prog = [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]] if mood == "playful" \
        else [[57, 60, 64], [53, 57, 60], [50, 53, 57], [52, 56, 59]]
    bars = int(dur / (4 * beat)) + 1
    for b in range(bars):
        ch = prog[b % 4]
        t0 = b * 4 * beat
        put(sum(note(mf(m), 4 * beat, "pad", 0.12) for m in ch), t0)
        if b >= 2:
            put(note(mf(ch[0] - 24), 4 * beat * 0.9, "bass", 0.5), t0)
        for s in range(8):
            t = t0 + s * beat / 2
            if mood == "playful":
                m = ch[[0, 1, 2, 1, 0, 2, 1, 2][s]] + 12
                put(note(mf(m), beat / 2, "pluck", 0.35 if b >= 2 else 0.15), t)
            else:
                if s % 2 == 0 and b >= 2:
                    put(note(mf(ch[0] - 12), beat / 2, "stab", 0.5), t)
                put(drum("tick"), t)
        if b >= 2:
            for q in range(4):
                if mood == "playful" and q in (0, 2):
                    put(drum("kick") * 0.7, t0 + q * beat)
                if mood != "playful" and q == 0:
                    put(drum("kick") * 0.8, t0)
                if mood == "build":
                    for e in range(2):
                        put(drum("hat", b * 8 + q * 2 + e), t0 + q * beat + e * beat / 2)
                    if q == 2:
                        put(drum("kick") * 0.6, t0 + q * beat)
    out = out[:n]
    if mood == "build":
        out *= np.linspace(0.6, 1.0, n)
    out[-int(0.5 * SR):] *= np.linspace(1, 0, int(0.5 * SR))
    return out


def make_sfx_kit(outdir: str | Path) -> dict[str, list[Path]]:
    """Write the placeholder kit; returns kind -> files (variants)."""
    outdir = Path(outdir)
    kit: dict[str, list[Path]] = {k: [] for k in SFX_KINDS}
    for i in range(3):
        kit["whoosh"].append(save_wav(outdir / f"whoosh{i + 1}.wav", whoosh(0.45 + 0.08 * i, seed=i, up=i != 1)))
    for i, f in enumerate([900, 700, 1150]):
        kit["pop"].append(save_wav(outdir / f"pop{i + 1}.wav", pop(f)))
    kit["riser"].append(save_wav(outdir / "riser.wav", riser()))
    kit["hit"].append(save_wav(outdir / "hit.wav", hit()))
    kit["shutter"].append(save_wav(outdir / "shutter.wav", shutter()))
    for i in range(2):
        kit["click"].append(save_wav(outdir / f"click{i + 1}.wav", click(i)))
    return kit


def make_music(out: str | Path, mood: str = "playful", bpm: float = 110, dur: float = 60, key: int = 0) -> Path:
    return save_wav(out, music(mood, bpm, dur, key))
