"""Transcribe: faster-whisper with word timestamps. PocketSphinx is the emergency fallback and
marks the transcript degraded. A provided transcript file replays instead (fixtures, hand transcripts)."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import Settings
from ..edl.transcript import Transcript, Word
from ..log import StageLog
from ..project import Project, file_hash


def _whisper(audio: Path, settings: Settings, log: StageLog, duration: float) -> Transcript:
    from faster_whisper import WhisperModel

    wc = settings.whisper
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    log.info("loading whisper", model=wc.model, device=wc.device, compute=wc.compute_type)
    model = WhisperModel(wc.model, device=wc.device, compute_type=wc.compute_type,
                         download_root=str(settings.models_dir))
    segments, info = model.transcribe(str(audio), word_timestamps=True, vad_filter=wc.vad,
                                      beam_size=wc.beam_size, language=wc.language)
    words: list[Word] = []
    for seg in segments:
        for w in seg.words or []:
            text = (w.word or "").strip()
            if not text:
                continue
            words.append(Word(id=len(words), text=text, t0=round(float(w.start), 3), t1=round(float(w.end), 3),
                              p=round(float(w.probability), 3)))
        if duration:
            log.progress(min(0.95, seg.end / duration), f"{len(words)} words")
    tr = Transcript(language=info.language, model=f"faster-whisper:{wc.model}", source_duration=duration, words=words)
    tr.sentences = Transcript.group_sentences(tr.words)
    return tr


def _pocketsphinx(audio: Path, log: StageLog, duration: float) -> Transcript:
    """Rough open transcription with word timings (keyword-spotting quality). Marked degraded."""
    import subprocess
    import tempfile

    from pocketsphinx import AudioFile  # type: ignore

    tmp = Path(tempfile.mkdtemp()) / "ps.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(audio), "-ac", "1", "-ar", "16000", str(tmp)], check=True)
    words: list[Word] = []
    for phrase in AudioFile(audio_file=str(tmp)):
        for seg in phrase.seg():
            if seg.word.startswith("<") or seg.word.startswith("["):
                continue
            t0, t1 = seg.start_frame / 100.0, seg.end_frame / 100.0
            words.append(Word(id=len(words), text=seg.word.split("(")[0], t0=round(t0, 3), t1=round(t1, 3), p=0.5))
    tr = Transcript(language="en", model="pocketsphinx", source_duration=duration, words=words, degraded=True,
                    notes=["PocketSphinx fallback: rough words; word-dependent decisions are degraded"])
    tr.sentences = Transcript.group_sentences(tr.words)
    return tr


def run(project: Project, settings: Settings, log: StageLog | None = None, *,
        transcriber: str = "auto", replay: Path | None = None) -> Transcript:
    log = log or project.log("transcribe")
    audio = project.audio_wav
    project.begin("transcribe", file_hash(audio) if audio.exists() else None)
    try:
        duration = float(json.loads(project.probe_json.read_text()).get("duration", 0.0)) if project.probe_json.exists() else 0.0
        from ..formats import get_format
        fmt_tr = get_format(project.format).transcript_file(project)
        src = replay or fmt_tr or (Path(project.options["transcript"]) if project.options.get("transcript") else None)
        if src is not None:
            log.info("replaying transcript", path=str(src))
            tr = Transcript.load(Path(src))
            if not tr.sentences:
                tr.sentences = Transcript.group_sentences(tr.words)
            tr.source_duration = tr.source_duration or duration
        else:
            tr = None
            if transcriber in ("auto", "whisper"):
                try:
                    tr = _whisper(audio, settings, log, duration)
                except Exception as e:  # noqa: BLE001
                    log.warn("faster-whisper failed", error=str(e)[:300])
                    if transcriber == "whisper":
                        raise
            if tr is None:
                try:
                    log.warn("falling back to PocketSphinx keyword spotting (degraded)")
                    tr = _pocketsphinx(audio, log, duration)
                except ImportError as e:
                    log.error("no transcriber available: faster-whisper failed and pocketsphinx is not installed. "
                              "The edit continues WITHOUT words: dead-air removal only; every word-dependent "
                              "technique is reported as not executed.")
                    tr = Transcript(language="und", model="none", source_duration=duration, degraded=True,
                                    notes=[f"no transcriber available ({e}); install faster-whisper models or pocketsphinx"])
        d = project.dir("transcribe")
        tr.save(project.transcript_json)
        (d / "transcript.srt").write_text(tr.to_srt())
        (d / "transcript.md").write_text(tr.to_markdown())
        project.finish("transcribe", words=len(tr.words), sentences=len(tr.sentences), model=tr.model, degraded=tr.degraded)
        log.done(words=len(tr.words), model=tr.model)
        return tr
    except Exception as e:
        project.fail("transcribe", repr(e))
        log.error("failed", error=repr(e))
        raise
