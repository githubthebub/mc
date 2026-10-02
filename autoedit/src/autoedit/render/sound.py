"""The four-layer sound pass (mix_audio.py as a library).

Music gain is relative to the voice after measuring each track's LUFS. Fadeouts, swells and
dropouts are volume automation on the music bus; the bus ducks under the voice bus with a
sidechain compressor; SFX repeats are varied in pitch and speed; then a measured static gain
to the target loudness and a true-peak limiter. loudnorm's second pass is never used because
it silently switches to dynamic mode and reshapes the mix. Stems are exported for QA."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ..log import StageLog
from ..media.audio import file_lufs
from ..media.ffmpeg import FFmpegError

VARIANTS = [1.0, 1.08, 0.93, 1.04, 0.96]


@dataclass
class MusicCue:
    file: Path
    start: float
    end: float
    rel_db: float = -10.0
    offset: float = 0.0            # seconds into the song at `start` (pickup sync)
    lufs: float | None = None
    id: str = ""


@dataclass
class Cue:
    file: Path
    t: float
    gain_db: float = 0.0
    id: str = ""


@dataclass
class MixSpec:
    duration: float
    music: list[MusicCue] = field(default_factory=list)
    dropouts: list[tuple[float, float]] = field(default_factory=list)
    fadeouts: list[tuple[float, float]] = field(default_factory=list)
    swells: list[tuple[float, float, float]] = field(default_factory=list)
    sfx: list[Cue] = field(default_factory=list)
    vo: list[Cue] = field(default_factory=list)
    voice_clean: bool = False
    lufs: float = -14.0
    true_peak: float = -1.5
    duck_ratio: float = 8.0
    fade_in_first: float = 2.0
    loop_end: bool = False          # Shorts: the last track runs to the final frame, no fade to silence


@dataclass
class MixResult:
    measured_lufs: float
    gain_db: float
    measured_true_peak: float | None
    graph: str
    stems: dict[str, Path]


def _graph(spec: MixSpec, with_stems: bool) -> tuple[list[str], list[str], str, list[str]]:
    """Build (inputs, filter chains, pre-mix expression, stem labels)."""
    D = spec.duration
    inputs: list[str] = []
    fc: list[str] = []
    idx = 1
    voice = "[0:a]"
    mixes: list[str] = []
    if spec.voice_clean:
        fc.append(f"{voice}aresample=48000,highpass=f=80,afftdn=nr=12:nf=-45:tn=1,"
                  "acompressor=threshold=0.1:ratio=3:attack=10:release=150:makeup=2[vclean]")
        voice = "[vclean]"
    if spec.vo:
        vos = []
        for v in spec.vo:
            ms = int(v.t * 1000)
            inputs += ["-i", str(v.file)]
            fc.append(f"[{idx}:a]aresample=48000,volume={v.gain_db}dB,adelay={ms}|{ms}[vo{idx}]")
            vos.append(f"[vo{idx}]")
            idx += 1
        fc.append(f"{voice}aresample=48000[orig]")
        fc.append("[orig]" + "".join(vos) + f"amix=inputs={1 + len(vos)}:duration=first:normalize=0[vbus]")
        voice = "[vbus]"
    stems: list[str] = []
    if spec.music:
        fc.append(f"{voice}asplit=3[vox][sc][vstem]" if with_stems else f"{voice}asplit=2[vox][sc]")
        voice = "[vox]"
        tracks = []
        for i, m in enumerate(spec.music):
            st, en = m.start, m.end
            L = max(0.1, en - st)
            fin = 0.5 if st > 0 else spec.fade_in_first
            fout = 0.5 if en < D - 0.05 else (0.03 if spec.loop_end else 2.0)
            lufs = m.lufs if m.lufs is not None else file_lufs(m.file)
            db = (spec.lufs + m.rel_db) - lufs   # absolute gain that lands it relative to the voice
            auto = []
            for A, B in spec.fadeouts:
                # a fadeout belongs to the track(s) whose section ends in it; only when no track ends
                # there does it apply to every track that is playing at A (mix_audio.py behaviour)
                ending = [x for x in spec.music if A <= x.end <= B + 1.0]
                applies = (m in ending) if ending else (st <= A < en)
                if applies and st <= A < en:
                    auto.append(f"volume='if(lt(t,{A}),1,if(lt(t,{B}),1-(t-{A})/{B - A},0))':eval=frame")
            inputs += ["-stream_loop", "-1", "-i", str(m.file)]
            chain = (f"[{idx}:a]aresample=48000,atrim={m.offset}:{m.offset + L},asetpts=PTS-STARTPTS,volume={db:.2f}dB,"
                     f"afade=t=in:d={fin},afade=t=out:st={max(0.0, L - fout):.3f}:d={fout},"
                     f"adelay={int(st * 1000)}|{int(st * 1000)},apad=whole_dur={D}")
            if auto:
                chain += "," + ",".join(auto)
            fc.append(chain + f"[m{i}]")
            tracks.append(f"[m{i}]")
            idx += 1
        bus = "".join(tracks) + (f"amix=inputs={len(tracks)}:normalize=0" if len(tracks) > 1 else "anull")
        for A, B, g in spec.swells:
            bus += f",volume='if(between(t,{A},{B}),pow(10,{g}*(t-{A})/{B - A}/20),1)':eval=frame"
        for A, B in spec.dropouts:
            bus += f",volume=enable='between(t,{A},{B})':volume=0"
        if with_stems:
            fc.append(bus + ",asplit=2[mus][rawstem]")
        else:
            fc.append(bus + "[mus]")
        fc.append(f"[mus][sc]sidechaincompress=threshold=0.02:ratio={spec.duck_ratio}:attack=20:release=400[duckedraw]")
        if with_stems:
            fc.append("[duckedraw]asplit=2[ducked][mstem]")
            stems += ["[vstem]", "[mstem]", "[rawstem]"]
        else:
            fc.append("[duckedraw]anull[ducked]")
        mixes.append("[ducked]")
    elif with_stems:
        fc.append(f"{voice}asplit=2[vox][vstem]")
        voice = "[vox]"
        stems.append("[vstem]")
    # SFX with automatic variation for back-to-back repeats of the same file
    sfx_labels = []
    last = None
    streak = 0
    for s in sorted(spec.sfx, key=lambda c: c.t):
        streak = streak + 1 if s.file == last else 0
        last = s.file
        r = VARIANTS[streak % len(VARIANTS)]
        inputs += ["-i", str(s.file)]
        ms = int(s.t * 1000)
        vary = f"asetrate={int(48000 * r)},aresample=48000," if r != 1.0 else ""
        fc.append(f"[{idx}:a]aresample=48000,{vary}volume={s.gain_db}dB,adelay={ms}|{ms}[s{idx}]")
        sfx_labels.append(f"[s{idx}]")
        idx += 1
    if sfx_labels:
        fc.append("".join(sfx_labels) + (f"amix=inputs={len(sfx_labels)}:normalize=0" if len(sfx_labels) > 1 else "anull")
                  + f",apad=whole_dur={D},atrim=0:{D}" + ("[sfxraw]" if with_stems else "[sfxbus]"))
        if with_stems:
            fc.append("[sfxraw]asplit=2[sfxbus][sstem]")
            stems.append("[sstem]")
        mixes.append("[sfxbus]")
    pre = voice + "".join(mixes)
    mixexpr = pre + (f"amix=inputs={1 + len(mixes)}:duration=first:normalize=0" if mixes else "anull")
    return inputs, fc, mixexpr, stems


def measure(video: Path, spec: MixSpec) -> tuple[float, float | None]:
    inputs, fc, mixexpr, _ = _graph(spec, with_stems=False)
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(video), *inputs, "-filter_complex",
                          ";".join(fc + [mixexpr + f",loudnorm=I={spec.lufs}:TP={spec.true_peak}:LRA=11:print_format=json[x]"]),
                          "-map", "[x]", "-f", "null", "-"], capture_output=True, text=True).stderr
    try:
        m = json.loads(err[err.rfind("{"):err.rfind("}") + 1])
        i = float(m["input_i"])
        tp = float(m.get("input_tp", "nan"))
        return (i if i > -70 else -70.0), (tp if tp == tp else None)
    except (ValueError, KeyError) as e:
        raise FFmpegError(f"loudness measurement failed: {err[-800:]}") from e


def mix(video: Path, out: Path, spec: MixSpec, stems_dir: Path | None = None, log: StageLog | None = None,
        video_codec: list[str] | None = None) -> MixResult:
    """Mix onto `video` (stream-copied) and write `out`; export stems when stems_dir is given."""
    measured, tp = measure(video, spec)
    gain = spec.lufs - measured
    # alimiter works on sample peaks. Limiting at 4x oversampling catches inter-sample peaks, and the
    # ceiling still sits 1 dB under the true-peak target because the AAC encoder overshoots transients.
    limit = 10 ** ((spec.true_peak - 1.0) / 20)
    ln = (f"volume={gain:.2f}dB,aresample=192000,alimiter=limit={limit:.3f}:attack=5:release=50:level=disabled,"
          f"aresample=48000,alimiter=limit={limit:.3f}:attack=2:release=20:level=disabled")
    inputs, fc, mixexpr, stems = _graph(spec, with_stems=stems_dir is not None)
    fc = fc + [mixexpr + f",{ln},aresample=48000[aout]"]
    stem_files: dict[str, Path] = {}
    extra: list[str] = []
    if stems_dir is not None:
        stems_dir.mkdir(parents=True, exist_ok=True)
        names = {"[vstem]": "voice", "[mstem]": "music", "[sstem]": "sfx", "[rawstem]": "music_raw"}
        for lab in stems:
            name = names[lab]
            fc.append(f"{lab}volume={gain:.2f}dB,aresample=48000,apad=whole_dur={spec.duration},atrim=0:{spec.duration}[{name}_out]")
            f = stems_dir / f"{name}.wav"
            stem_files[name] = f
            extra += ["-map", f"[{name}_out]", "-c:a", "pcm_s16le", str(f)]
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-i", str(video), *inputs,
           "-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[aout]", *(video_codec or ["-c:v", "copy"]),
           "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(out), *extra]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise FFmpegError("mix failed:\n" + "\n".join(r.stderr.strip().splitlines()[-15:]))
    if log:
        log.info("mixed", measured_lufs=round(measured, 1), gain_db=round(gain, 2), target=spec.lufs)
    return MixResult(measured, gain, tp, ";".join(fc), stem_files)
