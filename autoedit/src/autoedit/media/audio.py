"""Audio measurement.

Pause detection uses short RMS windows against the file's own noise floor
(floor + 6 dB), exactly as cut_silence.py did. ffmpeg's silencedetect compares
sample peaks and is brittle on quiet or noisy recordings, so it is not used.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PAUSE_WIN = 0.05           # seconds per RMS window
PAUSE_SR = 16000
FLOOR_PERCENTILE = 0.10    # noise floor = 10th percentile of window levels
FLOOR_MARGIN_DB = 6.0
SMOOTH_WINDOWS = 3         # max-smoothing over 0.15 s so loud single frames don't split pauses
SILENT_DB = -120.0


def decode_pcm(path: str | Path, sr: int = PAUSE_SR, mono: bool = True,
               start: float | None = None, duration: float | None = None) -> np.ndarray:
    """Decode audio to float32 samples in [-1, 1] with ffmpeg."""
    cmd = ["ffmpeg", "-v", "error", "-nostdin"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", str(path)]
    if duration is not None:
        cmd += ["-t", f"{duration:.3f}"]
    cmd += ["-vn", "-ac", "1" if mono else "2", "-ar", str(sr), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    if not mono:
        x = x.reshape(-1, 2)
    return x


def rms_levels(samples: np.ndarray, sr: int = PAUSE_SR, win: float = PAUSE_WIN) -> np.ndarray:
    """RMS level in dBFS per window (silence -> -120)."""
    n = max(1, int(sr * win))
    total = (len(samples) // n) * n
    if total == 0:
        return np.array([SILENT_DB], dtype=np.float64)
    frames = samples[:total].reshape(-1, n).astype(np.float64)
    rms = np.sqrt(np.mean(frames * frames, axis=1))
    with np.errstate(divide="ignore"):
        db = 20.0 * np.log10(rms)
    return np.where(np.isfinite(db), db, SILENT_DB)


def noise_floor_db(levels: np.ndarray) -> float:
    srt = np.sort(levels)
    return float(srt[int(len(srt) * FLOOR_PERCENTILE)]) if len(srt) else -60.0


def pause_threshold_db(levels: np.ndarray, noise: str | float = "auto") -> float:
    if noise == "auto":
        return noise_floor_db(levels) + FLOOR_MARGIN_DB
    return float(str(noise).replace("dB", ""))


def detect_pauses(levels: np.ndarray, thr_db: float, min_silence: float,
                  win: float = PAUSE_WIN, smooth: int = SMOOTH_WINDOWS) -> list[tuple[float, float]]:
    """Return (start, end) of every stretch below thr_db lasting at least min_silence seconds."""
    lv = list(map(float, levels))
    k = smooth
    sm = [max(lv[max(0, i - k // 2): i + k // 2 + 1]) for i in range(len(lv))]
    out: list[tuple[float, float]] = []
    run = None
    for i, x in enumerate(sm + [999.0]):
        if x < thr_db and run is None:
            run = i
        elif x >= thr_db and run is not None:
            if (i - run) * win >= min_silence:
                out.append((round(run * win, 3), round(i * win, 3)))
            run = None
    return out


@dataclass
class PauseAnalysis:
    noise_floor_db: float
    threshold_db: float
    pauses: list[tuple[float, float]]
    win: float
    levels_db: np.ndarray

    def energy_curve(self, bucket: float = 1.0) -> list[float]:
        """Mean level per bucket of seconds, for peak finding."""
        n = max(1, int(round(bucket / self.win)))
        lv = self.levels_db
        return [float(np.mean(lv[i:i + n])) for i in range(0, len(lv), n)]


def analyze_pauses(path: str | Path, min_silence: float = 0.4, noise: str | float = "auto") -> PauseAnalysis:
    samples = decode_pcm(path)
    levels = rms_levels(samples)
    thr = pause_threshold_db(levels, noise)
    return PauseAnalysis(noise_floor_db(levels), thr, detect_pauses(levels, thr, min_silence), PAUSE_WIN, levels)


# ---- loudness ----------------------------------------------------------------

@dataclass(frozen=True)
class Loudness:
    integrated_lufs: float
    loudness_range_lu: float | None
    true_peak_dbtp: float | None


def measure_loudness(path: str | Path, start: float | None = None, duration: float | None = None) -> Loudness:
    """EBU R128 integrated loudness, LRA and true peak via ebur128."""
    cmd = ["ffmpeg", "-hide_banner", "-nostdin"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", str(path)]
    if duration is not None:
        cmd += ["-t", f"{duration:.3f}"]
    cmd += ["-vn", "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    summ = err.split("Summary:")[-1]

    def g(key: str) -> float | None:
        m = re.search(key + r":\s*(-?[\d.]+|-inf)", summ)
        if not m:
            return None
        return SILENT_DB if m.group(1) == "-inf" else float(m.group(1))

    i = g("I")
    return Loudness(i if i is not None else SILENT_DB, g("LRA"), g("Peak"))


def file_lufs(path: str | Path) -> float:
    """Integrated loudness of a whole file (default -14 when unmeasurable), as mix_audio.py did."""
    i = measure_loudness(path).integrated_lufs
    return -14.0 if i <= SILENT_DB + 1 else i


# ---- music structure -----------------------------------------------------------

@dataclass(frozen=True)
class MusicPoint:
    t: float
    kind: str       # "PICKUP" or "DIP"
    delta_db: float


def music_points(path: str | Path, win: float = 0.5, jump: float = 4.0) -> tuple[list[MusicPoint], list[int]]:
    """Find a song's energy pickups and dips (music_points.py). Returns (points, energy per 2 s in dB)."""
    samples = decode_pcm(path, sr=48000)
    vals = list(map(float, rms_levels(samples, sr=48000, win=win)))
    vals = [v if v > -90 else -90.0 for v in vals]
    k = max(1, int(2 / win))
    ds = [0.0] * len(vals)
    for i in range(k, len(vals) - k):
        ds[i] = sum(vals[i:i + k]) / k - sum(vals[i - k:i]) / k
    pts: list[MusicPoint] = []
    for i in range(k, len(vals) - k):
        d = ds[i]
        nb = ds[max(0, i - k): i + k + 1]
        if abs(d) >= jump and abs(d) == max(abs(x) for x in nb):
            if not pts or i * win - pts[-1].t > 2:
                pts.append(MusicPoint(round(i * win, 1), "PICKUP" if d > 0 else "DIP", round(d, 1)))
    energy = [int(sum(vals[i:i + k]) / k) for i in range(0, len(vals), k)]
    return pts, energy


def first_pickup(path: str | Path, after: float = 0.0) -> float | None:
    pts, _ = music_points(path)
    for p in pts:
        if p.kind == "PICKUP" and p.t >= after:
            return p.t
    return None


def rms_db_windows(path: str | Path, win: float = 0.5, sr: int = 48000) -> np.ndarray:
    """RMS dBFS per window over a whole file (used by verify on stems)."""
    return rms_levels(decode_pcm(path, sr=sr), sr=sr, win=win)
