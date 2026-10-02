"""Build a synthetic talking-head sample: a drawn face that moves and talks, speech-like audio
with known pauses, and the matching word-level transcript. Deterministic, no committed media.

Usage: python make_sample.py OUTDIR [--seconds 40] [--size 640x360]
Writes OUTDIR/sample.mp4 and OUTDIR/transcript.json."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SR = 48000
FPS = 30

# The monologue. Sentences become speech bursts; pauses between them are the dead air to cut.
# (pause_after seconds; >0.5 s pauses are the ones the informative preset removes)
SCRIPT: list[tuple[str, float, float]] = [
    # (sentence, pause_after_s, loudness 0..1)
    ("I almost deleted this whole video.", 1.4, 0.9),
    ("Then I found the one mistake that was killing it.", 0.3, 1.0),
    ("Here's the thing.", 0.9, 0.8),
    ("Most videos lose a third of their viewers in thirty seconds.", 0.2, 0.85),
    ("Not because the content is bad.", 0.7, 0.8),
    ("Because the intro doesn't deliver what the thumbnail promised.", 1.8, 0.9),
    ("So I rebuilt the first ten seconds.", 0.4, 0.8),
    ("Proof first, promise second.", 1.1, 0.95),
    ("I showed the result before explaining it.", 0.3, 0.8),
    ("And retention went up by twenty percent.", 2.2, 1.0),
    ("The second fix was sound.", 0.4, 0.75),
    ("I cut the music on the key line.", 0.2, 0.8),
    ("Silence makes people listen.", 1.5, 0.9),
    ("Try it on your next video.", 0.6, 0.8),
]

WORD_S = 0.26          # seconds per spoken word
WORD_GAP = 0.07        # gap between words inside a sentence
NOISE_FLOOR_DB = -58.0


def synth_word(dur: float, loud: float, seed: int) -> np.ndarray:
    """A buzzy, band-limited burst that behaves like a spoken word for RMS analysis."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    f0 = 110 + 40 * rng.random()
    saw = 2 * ((t * f0) % 1.0) - 1
    formant = np.sin(2 * np.pi * (600 + 300 * rng.random()) * t)
    x = 0.6 * saw * (0.5 + 0.5 * formant) + 0.25 * rng.standard_normal(n)
    # simple lowpass by moving average
    k = 8
    x = np.convolve(x, np.ones(k) / k, mode="same")
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.7
    return x * env * (0.25 + 0.55 * loud)


def build(outdir: Path, seconds: float = 48.0, size: tuple[int, int] = (640, 360)) -> tuple[Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    W, H = size
    rng = np.random.default_rng(1)
    total = int(seconds * SR)
    audio = rng.standard_normal(total) * (10 ** (NOISE_FLOOR_DB / 20))
    words: list[dict] = []
    t = 0.8
    wid = 0
    speaking: list[tuple[float, float]] = []
    for si, (sent, pause, loud) in enumerate(SCRIPT):
        toks = sent.split()
        for tok in toks:
            d = WORD_S * (0.7 + 0.6 * min(len(tok), 9) / 9)
            i0 = int(t * SR)
            burst = synth_word(d, loud, wid)
            audio[i0:i0 + len(burst)] += burst[:max(0, total - i0)]
            words.append({"id": wid, "text": tok, "t0": round(t, 3), "t1": round(t + d, 3), "p": 0.97, "s": si})
            speaking.append((t, t + d))
            wid += 1
            t += d + WORD_GAP
        t += pause
    if t > seconds:
        raise SystemExit(f"script needs {t:.1f}s but clip is {seconds}s")
    audio = np.clip(audio, -1, 1)
    wav = outdir / "sample_audio.wav"
    import wave
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())

    # transcript with sentences
    sentences = []
    for si, (sent, _, _) in enumerate(SCRIPT):
        ws = [w for w in words if w["s"] == si]
        sentences.append({"id": si, "t0": ws[0]["t0"], "t1": ws[-1]["t1"], "text": sent,
                          "w0": ws[0]["id"], "w1": ws[-1]["id"]})
    tr = {"language": "en", "model": "fixture", "source_duration": seconds, "words": words,
          "sentences": sentences, "degraded": False, "notes": ["synthetic fixture transcript"]}
    trp = outdir / "transcript.json"
    trp.write_text(json.dumps(tr, indent=1))

    # video frames piped to ffmpeg
    mp4 = outdir / "sample.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-shortest", str(mp4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    n_frames = int(seconds * FPS)
    spk = np.zeros(n_frames, dtype=bool)
    for a, b in speaking:
        spk[int(a * FPS):int(b * FPS) + 1] = True
    for i in range(n_frames):
        tt = i / FPS
        cx = W * 0.5 + 45 * math.sin(tt * 0.35) + 12 * math.sin(tt * 1.7)
        cy = H * 0.46 + 14 * math.sin(tt * 0.5 + 1)
        r = 62 + 6 * math.sin(tt * 0.2)
        im = Image.new("RGB", (W, H), (38, 42, 50))
        d = ImageDraw.Draw(im)
        # room: a shelf line and a lamp glow for scene-change detectors to have something stable
        d.rectangle([0, int(H * 0.72), W, H], fill=(52, 48, 58))
        d.ellipse([W - 120, 20, W - 40, 100], fill=(90, 80, 60))
        # body, neck, head
        d.ellipse([cx - 150, cy + r - 10, cx + 150, cy + r + 220], fill=(70, 60, 90))
        d.rectangle([cx - 25, cy + r - 20, cx + 25, cy + r + 30], fill=(215, 170, 140))
        d.ellipse([cx - r, cy - r * 1.2, cx + r, cy + r * 1.2], fill=(225, 180, 150))
        d.chord([cx - r, cy - r * 1.25, cx + r, cy - r * 0.2], 180, 360, fill=(60, 40, 30))
        for ex in (cx - 28, cx + 28):
            d.ellipse([ex - 14, cy - 20, ex + 14, cy - 4], fill=(255, 255, 255))
            d.ellipse([ex - 6, cy - 17, ex + 6, cy - 6], fill=(40, 30, 30))
            d.line([ex - 16, cy - 30, ex + 16, cy - 30], fill=(60, 40, 30), width=4)
        d.polygon([(cx, cy - 2), (cx - 9, cy + 20), (cx + 9, cy + 20)], fill=(200, 150, 125))
        if spk[i] and (i // 3) % 2 == 0:
            d.ellipse([cx - 20, cy + 22, cx + 20, cy + 46], fill=(120, 40, 50))
        else:
            d.arc([cx - 28, cy + 18, cx + 28, cy + 48], 10, 170, fill=(150, 60, 70), width=5)
        proc.stdin.write(im.tobytes())
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed building the sample")
    return mp4, trp


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--seconds", type=float, default=48.0)
    ap.add_argument("--size", default="640x360")
    a = ap.parse_args()
    w, h = map(int, a.size.split("x"))
    mp4, tr = build(Path(a.outdir), a.seconds, (w, h))
    print(json.dumps({"video": str(mp4), "transcript": str(tr)}))
