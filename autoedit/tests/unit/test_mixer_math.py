import math
import subprocess
from pathlib import Path

import numpy as np
import pytest

from autoedit.media.audio import file_lufs, rms_db_windows
from autoedit.media.synth import SR, save_wav
from autoedit.render.sound import Cue, MixSpec, MusicCue, _graph, mix


@pytest.fixture
def tone_video(tmp_path: Path) -> Path:
    """20 s of a 220 Hz voice-like tone, speaking 0-8 s and 12-20 s, on a black video."""
    t = np.arange(20 * SR) / SR
    v = 0.3 * np.sin(2 * np.pi * 220 * t) * (1 + 0.3 * np.sin(2 * np.pi * 3 * t))
    v[int(8 * SR):int(12 * SR)] = 0
    wav = save_wav(tmp_path / "voice.wav", v)
    out = tmp_path / "voice.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=20", "-i", str(wav),
                    "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(out)], check=True)
    return out


@pytest.fixture
def quiet_music(tmp_path: Path) -> Path:
    t = np.arange(30 * SR) / SR
    m = 0.05 * np.sin(2 * np.pi * 110 * t) + 0.02 * np.sin(2 * np.pi * 440 * t)
    return save_wav(tmp_path / "music.wav", m)


def test_relative_gain_formula():
    """A quiet and a loud song must land at the same level relative to the voice target."""
    spec = MixSpec(duration=10, lufs=-14, music=[MusicCue(Path("a.wav"), 0, 10, -10, lufs=-30), MusicCue(Path("b.wav"), 0, 10, -10, lufs=-12)])
    _, fc, _, _ = _graph(spec, with_stems=False)
    gains = [float(s.split("volume=")[1].split("dB")[0]) for s in fc if "atrim=" in s]
    assert gains[0] == pytest.approx(6.0)     # -14 - 10 - (-30)
    assert gains[1] == pytest.approx(-12.0)   # -14 - 10 - (-12)


def test_swell_expression_reaches_target_db():
    spec = MixSpec(duration=10, music=[MusicCue(Path("a.wav"), 0, 10, lufs=-20)], swells=[(2.0, 6.0, 6.0)])
    _, fc, _, _ = _graph(spec, with_stems=False)
    expr = next(s for s in fc if "pow(10," in s)
    assert "between(t,2.0,6.0)" in expr and "6.0*(t-2.0)/4.0/20" in expr


def test_mix_automation_measured(tone_video: Path, quiet_music: Path, tmp_path: Path):
    spec = MixSpec(duration=20, lufs=-16, true_peak=-1.5,
                   music=[MusicCue(quiet_music, 0, 20, rel_db=-8, lufs=file_lufs(quiet_music))],
                   dropouts=[(13.0, 15.0)], fadeouts=[(16.0, 20.0)], swells=[(2.0, 7.0, 6.0)])
    out = tmp_path / "final.mp4"
    res = mix(tone_video, out, spec, stems_dir=tmp_path / "stems")
    assert res.gain_db == pytest.approx(-16 - res.measured_lufs)
    m = rms_db_windows(res.stems["music"], win=0.5)
    # dropout: silent inside
    assert max(m[int(13.25 / 0.5):int(14.75 / 0.5)]) < -50
    # fadeout: ends far below where it started
    assert np.mean(m[int(16 / 0.5):int(17 / 0.5)]) - np.mean(m[int(19 / 0.5):int(20 / 0.5)]) > 12
    # ducking: music under the voice (0-8 s) is quieter than in the gap (8-12 s) -- compare un-swelled stretches
    assert np.mean(m[int(9 / 0.5):int(11.5 / 0.5)]) > np.mean(m[int(0.5 / 0.5):int(1.5 / 0.5)]) + 3
    # final loudness within 1 LU of target and true peak under the ceiling
    from autoedit.media.audio import measure_loudness
    L = measure_loudness(out)
    assert abs(L.integrated_lufs - (-16)) <= 1.0
    assert L.true_peak_dbtp <= -1.0


def test_sfx_variation_on_repeats(tmp_path: Path):
    f = save_wav(tmp_path / "pop.wav", np.sin(np.linspace(0, 200, 4800)))
    spec = MixSpec(duration=5, sfx=[Cue(f, 1.0), Cue(f, 2.0), Cue(f, 3.0)])
    _, fc, _, _ = _graph(spec, with_stems=False)
    rates = [s for s in fc if "asetrate=" in s]
    assert len(rates) == 2                       # the second and third plays are varied, never identical twice in a row
