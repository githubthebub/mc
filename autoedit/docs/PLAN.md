# autoedit: architecture and milestone plan

Status: **implemented through milestone 5** (see "Implementation notes" at the end for what differs from this plan).

autoedit turns raw talking-head footage, or a chat-skit script, into a
publish-ready long-form YouTube video plus Shorts, by applying the
`video-editor` skill (Learn By Leo's philosophy) mechanically and honestly.

## 0. What was read, and what the environment has

Read in full: `SKILL.md`, `references/style-guide.md`,
`references/story-and-retention.md`, `references/ffmpeg-recipes.md`,
`references/packaging.md`, and all nine scripts (`analyze.py`,
`cut_silence.py`, `focus_image.py`, `insert_beats.py`, `mix_audio.py`,
`montage.py`, `music_points.py`, `synth_audio.py`, `thumb_check.py`).

Where the skill lives: this repo has no `.claude/` directory. The skill is
installed as a synced plugin skill under `~/.claude/skills/synced/.../video-editor/`.
The plan copies it verbatim into the repo at `.claude/skills/video-editor/`
so the path you named is real, and the tool loads the references from a
configurable `skill_dir` that defaults to that path.

Environment facts that shape the design:

| Item | Finding |
|---|---|
| Python | 3.11.15 |
| ffmpeg | 6.1.1 with libass, loudnorm, ebur128, sidechaincompress, afftdn, zoompan, xfade, tpad |
| CPU / RAM / GPU | 4 cores, 15 GB, no GPU. faster-whisper runs on CPU with int8 models |
| Fonts | DejaVu only. Poppins is not installed. Profiles must point at TTF files you provide, with DejaVu as fallback |
| pip | reachable. faster-whisper 1.2.1, mediapipe 1.0.1, opencv-python-headless 5.0, anthropic 1.11, pocketsphinx 5.1 |
| Repo | a Minecraft Fabric mod. autoedit will live in its own `autoedit/` subfolder as a standalone Python project |
| API key | `ANTHROPIC_API_KEY` is not set in this session. Needed for the plan stage demo |

## 1. Design principles

1. **The EDL is the single source of truth.** Every stage is a function from
   artifacts on disk to artifacts on disk. Rendering is deterministic from
   the EDL plus the source files.
2. **Story decisions vs. signal decisions.** The LLM makes story decisions
   using the skill references: hook, green/purple structure, litmus gaps and
   voiceover lines, what to montage, where to add beats, moods, which words
   deserve captions, dropouts on which lines, chapters, title, thumbnail.
   Code makes signal decisions: where pauses actually are, where the face
   is, how loud things are, frame-exact timing. The LLM never emits raw
   timestamps. It references transcript word ids and sentence ids, and code
   resolves them to frames.
3. **Source-anchored EDL, output-realized timing map.** Every planned item
   is anchored to source time (a word) or to a segment ("before segment 7").
   The render stage builds the frame-accurate source-to-output timing map
   and places every graphic and sound through it. Re-planning cuts does not
   invalidate music or caption decisions.
4. **Honest QA.** Every technique the skill prescribes is tracked with a
   status: executed, degraded, or not executed, with the reason.
5. **Fit the experience.** The profile's experience type sets the dead-air
   preset, pacing benchmarks, caption density, SFX density, and music moves.

## 2. Pipeline and project folder

```
ingest -> transcribe -> analyze -> plan -> [review] -> render -> verify -> package
```

```
projects/<slug>/
  project.yaml        name, profile, format, source, options
  state.json          per-stage status, timestamps, input hashes, approval flag
  logs/               JSONL structured logs per stage, progress files
  01_ingest/          source.mp4 (link or normalized), proxy_480p.mp4, audio.wav, probe.json, contact_sheet.png
  02_transcribe/      transcript.json (words: id, text, t0, t1, p; sentences), transcript.srt, transcript.md
  03_analyze/         analysis.json (rms curve, noise floor, pauses, energy peaks, scene cuts),
                      face_track.json (smoothed boxes), analysis.md
  04_plan/            story_pass.json, story_pass.md, decisions.json, edl.json, plan_summary.md,
                      preview.mp4, llm/NN_<call>.request.json + .response.json
  05_render/          segments/, timeline.mp4, timing_map.json, graphics.ass, overlays/,
                      final.mp4, stems/{voice,music,sfx}.wav, render_log.json
  06_verify/          qa_report.json, qa_report.md, frames/*.png
  07_package/         <title-slug>.mp4, shorts/<id>.mp4, thumbnail.png, thumb_check.png,
                      metadata.json (title, description, chapters, tags), end_screen.json
```

`autoedit run` executes every stage. Each stage records the hashes of the
inputs it consumed, so re-running skips up-to-date stages. A hand-edited
`edl.json` is detected by hash and labelled "human-edited" in the QA report.

## 3. The EDL (schema v1)

A Pydantic model, serialized as JSON. Times are source seconds unless the
field name starts with `out_`. Anchors are `{"word": id}`,
`{"sentence": id}`, `{"segment": id, "edge": "start"|"end"}`, or a raw
`{"src": t}` for human edits.

| Section | Contents |
|---|---|
| `meta` | version, project, profile, format, source probe (duration, fps, size), llm model, created_by (llm / human) |
| `story_pass` | the skill's table: time, what happens, green/purple, conflict, mood, litmus gaps, action |
| `segments` | ordered list: id, kind (aroll, montage, beat, card, still, broll), src_in, src_out, speed, punch {scale, anchor: face}, notes. Montage segments carry their chunk list |
| `zooms` | emphasis zooms: anchor word, duration, scale, reason |
| `beats` | "shut up and show it": after anchor, duration, fill (caption, still, broll, none), sfx kind |
| `captions` | key-word captions: anchor word range, words (max 3), style |
| `cards` | chapter and title cards: before segment, text, duration, style |
| `overlays` | stills and B-roll: anchor, duration, asset, focus spec (focus_image), motion (slide, pop), sfx |
| `voiceover_slots` | litmus gap, line text in the creator's voice, anchor, hold duration, recorded file or null |
| `music` | sections: from segment, to segment, mood, file or null, rel_db, pickup {song_time, anchor} |
| `dropouts`, `fadeouts`, `swells` | anchor ranges with reason (punchline, takeaway, section end, payoff) |
| `sfx` | kind or file, anchor, gain |
| `chapters` | title, anchor |
| `title`, `thumbnail` | chosen title, alternatives, thumbnail spec (spotlight element, text, placement rule, mood color) |
| `shorts` | per short: id, hook sentence, src range, context label, caption mode, loop ending policy |
| `timing_map` | written by render: spans `{src_in, src_out, out_in, rate}` plus inserted spans (cards, beats) |
| `techniques` | the skill technique ledger: id, status, reason (filled by plan and render, reported by verify) |

Timing map rules: in and out points are snapped to source frame boundaries
before render, so every segment's frame count is known in advance. The map
is computed before rendering. After rendering, each segment's actual frame
count is asserted equal to the predicted count, so the map is exact by
construction rather than measured after the fact.

## 4. Package layout

```
autoedit/
  pyproject.toml                  package "autoedit", console script "autoedit"
  README.md, docs/PLAN.md
  profiles/personal.yaml, profiles/frogbertsaid.yaml
  src/autoedit/
    cli.py                        new | run | plan | approve | render | verify | package | shorts | batch | worker | serve
    config.py                     pydantic-settings: model name, whisper size, skill_dir, workers, paths
    project.py                    project folder, state.json, stage hashing, locks
    log.py                        structured JSONL logging + progress files
    media/
      ffmpeg.py                   run wrapper with progress parsing, segment render + concat helpers
      probe.py                    duration, dims, fps, streams
      audio.py                    RMS windows, noise floor, pause detection, LUFS and true peak, music points
      timing.py                   TimingMap (snap, compose, to_out, to_src, inserts)
      faces.py                    mediapipe detection, OpenCV fallback, tracking, smoothing, per-range boxes
      images.py                   focus_image clip builder, thumbnail metrics and sheet, annotated frame grabs
      synth.py                    placeholder SFX and music beds (synth_audio port)
      text.py                     ASS generation, font measurement, safe-zone placement
    edl/
      schema.py, validate.py, summary.py
    stages/
      ingest.py, transcribe.py, analyze.py, plan.py, review.py, render.py, verify.py, package.py
    render/
      picture.py                  segments, punch-ins, zooms, montage, beats, cards -> timeline.mp4 + timing map
      graphics.py                 captions, cards text, labels, overlays, focus stills (chunked)
      sound.py                    four-layer mixer, stems, loudness
      vertical.py                 face-tracked 9:16 crop path for Shorts
    formats/
      base.py                     Format protocol
      talking_head.py
      chat_skit.py                script parser + Discord-style frame compositor
    llm/
      client.py                   anthropic SDK wrapper: caching, structured outputs, logging, replay
      prompts/                    story_pass.md, decisions.md, shorts_score.md, packaging.md
      schemas.py                  response schemas (StoryPass, Decisions, ShortsScores, Packaging)
    shorts/
      select.py                   candidate windows, scoring, start-on-strongest-line
    batch/
      queue.py, watcher.py, worker.py
    web/
      app.py, templates/, static/
  scripts/                        thin wrappers that keep the original nine CLIs working
  tests/
    unit/                         timing, pauses, mixer math, faces smoothing, safe zones, EDL validation
    golden/                       full pipeline on a sample clip with recorded LLM responses
    fixtures/
.claude/skills/video-editor/      verbatim copy of the skill
```

## 5. Stage details

### Ingest
Probe the source. Normalize only when needed (variable frame rate, odd
pixel formats): constant fps, yuv420p, 48 kHz stereo audio. Build a 480p
proxy for analysis and preview, extract `audio.wav` at 48 kHz, and a
contact sheet (the `analyze.py --sheet` behaviour).

### Transcribe
faster-whisper with `word_timestamps=True`, VAD filter on, beam size 5.
Model size from config: `small` int8 for this 4-core box, `large-v3` or
`distil-large-v3` recommended on your machine. Words get stable ids, and
sentences are grouped by punctuation and gaps over 0.6 s. PocketSphinx
keyword spotting is only an emergency fallback (`--transcriber pocketsphinx`
or import failure). When it is used, every word-dependent technique is
marked degraded in the technique ledger. For chat-skit, the transcript is
derived from the script, one "sentence" per message.

### Analyze
- **Pauses:** 50 ms RMS windows at 16 kHz, noise floor = 10th percentile,
  threshold = floor + 6 dB, 3-window max smoothing. This is `cut_silence.py`'s
  method, kept exactly. `silencedetect` is not used anywhere.
- **Energy:** 1 s RMS curve and per-sentence energy, for Shorts scoring and
  for the planner's "proof moments" hints.
- **Scene cuts:** `select=gt(scene,0.12)` on the proxy, for pacing stats.
- **Face track:** mediapipe FaceDetector on the proxy at 10 fps. Pick the
  largest face, bridge gaps up to 1 s by interpolation, smooth with an EMA
  plus a deadband so crops do not jitter, convert to source pixels. Output
  per-sample boxes and per-second summaries. OpenCV YuNet is the fallback
  if mediapipe is unavailable. No face found means punch-ins fall back to a
  rule-of-thirds anchor and the ledger says "face-anchored zooms: not
  executed, no face detected".

### Plan (Claude API)
Default model `claude-opus-5-5`, set in config. API key from
`ANTHROPIC_API_KEY`. The three skill references are sent as cached system
blocks so repeated runs pay for them once. Structured outputs
(`output_config.format`) with the Pydantic schemas guarantee schema-valid
JSON. Streaming is used for the long outputs. Refusal fallbacks are enabled.
Every request and response is written to `04_plan/llm/`, and `--replay`
re-uses them, which is how the golden test runs offline.

Calls:
1. **Story pass.** Input: profile (experience, channel voice), analysis
   summary (duration, pauses, energy peaks, face presence), the transcript as
   numbered sentences with times and energy marks. Output: the story pass
   table, hook choice with "proof not promise" rationale, litmus gaps with
   voiceover lines, montage ranges, beat placements, music plan per section,
   chapter list, title options, thumbnail ideas.
2. **Decisions.** Input: story pass plus sentences with word ids. Output:
   every EDL decision as word and sentence anchors: captions (3 words max),
   dropouts, zooms, cards, SFX cues, swells, fadeouts, pickup sync target,
   protected pauses, deliberate breathing room.
3. **Shorts scoring** (milestone 2) and **packaging** (title and thumbnail
   text) share the cached context.

Code then assembles the EDL: the cut list comes from the pauses and the
profile preset (hangout / standard / entertainment), minus protected ranges,
plus montage and beat insertions. Anchors resolve to frame-snapped times.
Validation rejects overlapping segments, out-of-range anchors, captions
longer than three words, risers with nothing after them, and more than one
dropout per 20 s unless the profile allows it.

### Review
`autoedit plan` writes `edl.json`, `plan_summary.md` (the story pass table,
every decision with timestamps and reasons, the technique ledger so far,
title and thumbnail ideas, voiceover lines to record) and `preview.mp4`:
640x360, ultrafast preset, real cuts, captions, cards, placeholder music,
and a burned-in strip showing output time, source time, and the active
decision ("DROPOUT: punchline"). `autoedit approve <project>` marks the EDL
approved. `autoedit render` refuses an unapproved EDL unless `--yolo`.
`autoedit run --yolo` goes end to end.

### Render: picture
- Segments are split at every zoom boundary so each rendered piece has a
  static transform. An abrupt zoom is a cut, which matches the skill.
- Each piece is a separate ffmpeg process with `-ss`/`-t` and an exact frame
  count, rendered by a worker pool. Pieces are concatenated with the concat
  demuxer. No filter graph ever contains more than one piece.
- Punch-ins and zooms are anchored to the face: the crop is placed so the
  face center lands on the same screen coordinates as in the un-zoomed
  frame, clamped to the frame. The eye does not jump across the cut.
- Beats hold the last frame (`tpad` clone) and pad audio.
- Montage segments pick evenly spaced chunks across the range at the
  requested speed, and the chosen source times are stored in the EDL.
- Cards are generated clips (dark textured background, accent glow).
- Output: `timeline.mp4` plus the verified timing map.

### Render: graphics
One ASS file carries captions, card text, labels, and kinetic text, with
styles from the profile. Positions come from safe-zone rules and the face
box at the corresponding source time. Overlays (focus stills, B-roll,
slide-ins with easing and a whoosh) are composited in time chunks of at
most 8 overlays per filter graph, then concatenated. A `font_check.png` is
rendered with the real ASS styles and the glyph height is measured in
pixels with Pillow and reported, because libass sizes do not match
expectations.

### Render: sound
A port of `mix_audio.py`'s graph builder, driven by the EDL in output time:
voice bus (optional clean: highpass, FFT denoise, gentle compression) plus
voiceover files at mapped times; music bus with one track per section, gain
relative to the voice after measuring each file's LUFS, per-track fades,
pickup offset `OFF = pickup - (shift - S)`, fadeout and swell volume ramps,
hard dropouts; SFX bus with automatic pitch and speed variation for
back-to-back repeats; sidechain ducking; then measure, apply a static gain
to the profile's target, and a true-peak limiter. loudnorm's second pass is
never used. Stems are rendered by muting the other buses while keeping the
sidechain input, so the music stem carries the real ducking. Video is
stream-copied.

Music comes from the profile's library folder with a `library.yaml`
(file, moods, bpm, cached pickups). If the library is empty, `synth.py`
beds and SFX are used and the ledger records "placeholder audio".

### Verify
Per output (long-form and each Short), `qa_report.json` and `.md` with
annotated frame grabs (face box, safe zone, caption box drawn on):

| Check | Method | Target |
|---|---|---|
| Dead air | RMS pause detection on the final mix | no empty pause > 0.5 s outside planned beats |
| Loudness | ebur128 integrated | within ±1 LU of profile target |
| True peak | ebur128 | ≤ -1 dBTP |
| Music automation | RMS of the music stem in 0.5 s windows at every dropout, fadeout, swell, pickup | dropout < -50 dBFS, fadeout monotone down, swell monotone up, pickup energy step present |
| Captions and cards in safe zone | computed boxes from ASS plus pixel diff of the frame with and without subtitles inside the face box | no overlap, inside safe zone |
| Faces never cropped | face track vs. crop window on sampled frames | box fully inside |
| Hook | first speech word, first visual change, hook segment position | speech and a visual change inside 3 s |
| Pacing | scene changes per minute overall and first 60 s, average shot length | vs. the skill benchmarks for the profile experience |
| Font size | measured glyph height | within 10% of configured |
| NOT EXECUTED | the technique ledger | every skipped technique with its reason |

### Package
Final file named by title slug, `metadata.json` with title, description,
chapters (from cards, through the timing map), tags, Shorts metadata.
Thumbnail: the sharpest well-lit face frame from the face track (Laplacian
variance, face size), composed per the profile style, with text placed in
the largest empty region that does not touch the face box, then
`thumb_check` metrics and sheet. End screen: the last N seconds reserve a
zone that no caption may enter, recorded in `end_screen.json`, with an
optional rendered plate.

## 6. Formats

`Format` protocol:

```
class Format(Protocol):
    name: str
    def ingest(project) -> IngestResult            # media, or script -> scripted timeline
    def transcript(project) -> Transcript          # whisper, or derived from script
    def analyze(project) -> Analysis               # pauses, energy, faces (or layout boxes)
    def plan_context(project) -> dict              # format-specific hints for the LLM
    def build_edl(decisions, analysis, profile) -> EDL
    def render_picture(edl, project) -> TimelineResult
    def shorts_policy(profile) -> ShortsPolicy
    def verify_extras(edl, outputs) -> list[Check]
```

**talking-head:** the pipeline above.

**chat-skit:** a YAML script:

```yaml
title: "FrogBert vs the group chat"
characters:
  frog: {name: FrogBert, avatar: frog.png, color: "#57F287"}
  dan:  {name: Dan,      avatar: dan.png}
scenes:
  - card: "3 AM. The group chat wakes up."
  - msg: {from: dan, text: "who's awake", typing: 1.4}
  - msg: {from: frog, text: "I never sleep.", punch: true}
  - beat: 1.2
  - sfx: notification
```

The compositor draws Discord-style frames with Pillow: dark chat UI, avatar,
name, timestamp rows, message bubbles, typing indicator with animated dots,
highlight band on the newest message that fades over ~1.5 s, big grey text
cards, and camera punch-ins on punchlines (zoom anchored to the newest
message, the "face" of this format). Frames stream into ffmpeg as raw video
so no PNG sequence is written. Message pop SFX, keyboard ticks during
typing, music bed from the profile. The planner still runs the story pass
over the script: punchline detection drives dropouts and punch-ins, dense
exchanges get beats, cards signpost scenes. Open question 3 below covers
voices.

## 7. Profiles

YAML, validated by Pydantic, resolved against the format:

```yaml
name: personal
format: talking-head
experience: informative            # hangout | informative | entertainment
fonts:  {primary: fonts/Poppins-Bold.ttf, fallback: DejaVuSans-Bold}
colors: {bg: "#141414", text: "#FFFFFF", accent: "#FF4E2A"}   # warm orange-red
captions: {style: keyword, max_words: 3, size_px: 64, position: lower-middle, accent_words: true}
cards:    {style: dark-textured, glow: true, duration: 2.5}
audio:
  music_dir: ~/autoedit-assets/personal/music
  sfx_dir:   ~/autoedit-assets/personal/sfx
  music_rel_db: -10
  duck_ratio: 8
  lufs: -14
  true_peak: -1.5
  voice_clean: auto
end_screen: {seconds: 15, reserve_zone: right-third}
thumbnail: {style: face-plus-text, text_max_words: 3, mood_color: warm}
shorts: {count: 4, min_s: 15, max_s: 60, context_label: "@handle", caption_style: word-by-word}
```

`frogbertsaid` uses the chat-skit format, entertainment experience, a dark
Discord palette (chat `#313338`, panel `#2B2D31`, text `#DBDEE1`, blurple
accent `#5865F2`), the big grey card style, and its own music and SFX
folders.

## 8. Shorts engine (milestone 2)

- **Candidates:** windows of 15 to 60 s aligned to sentence boundaries,
  built from the long-form cut so dead air is already gone.
- **Scoring:** LLM scores each candidate for hook strength, self-contained
  idea, and payoff, in one cached call. Audio energy peaks add a bonus. The
  top 3 to 5 non-overlapping windows win. Each short is re-anchored so its
  strongest line (the LLM-identified hook sentence) is the first thing heard.
- **Picture:** 1080x1920 crop driven by the face track: the crop window
  follows the face center with a deadband and EMA smoothing, clamped to the
  source. Never a fixed center crop. Emphasis zooms anchored on the face.
  If no face is tracked, the blurred-background letterbox recipe is the
  fallback and the ledger says so.
- **Captions:** word-by-word ASS captions with karaoke highlight, one to
  three words per line, kept inside the safe zone (clear of the bottom 20%
  and the right 15%), and positioned above or below the face box per
  moment so they never overlap it.
- **Context label:** a persistent pill in the top safe area.
- **Ending:** cut on the last word plus a short pad, no audio fade, music
  continues to the final frame so the loop is seamless.
- Each short is its own EDL in `04_plan/shorts/<id>.edl.json`, rendered by
  the same renderer, verified with the same QA plus the vertical checks.

## 9. Batch mode (milestone 4)

`autoedit batch --watch DIR --profile personal [--yolo]` polls the folder,
treats a file as complete when its size has been stable for 30 s, creates
the project, and enqueues a job in a SQLite queue. `autoedit worker` runs
jobs one at a time (ffmpeg already uses the cores), launching each stage as
a child process whose stdout goes to the project's log files. The worker
starts detached (`setsid`, PID file) so it survives the launching shell.
`autoedit jobs` and `autoedit logs <project> -f` show progress.

## 10. Web UI (milestone 5)

FastAPI with Jinja templates and vanilla JavaScript, no build step, served
on localhost. Pages: project list with state; project page with run, plan,
approve, render, verify, package buttons that enqueue jobs; plan review
with the story pass table, an EDL editor that validates on save, and the
preview player with decision markers on the scrub bar; QA report with the
frame grabs; Shorts list with players.

## 11. Testing

- **Unit:** timing map (frame snapping, composing cuts, beats, cards and
  speed changes, round trips); pause detection on synthetic audio with known
  gaps under three noise floors; mixer math (relative gain from LUFS, swell,
  fadeout and dropout ramps rendered on a tone and measured back); face
  smoothing (jittery boxes become smooth, deadband holds); safe-zone
  placement (never intersects the face box, always inside 9:16 safe area);
  EDL validation rules.
- **Golden:** the whole pipeline on a short sample clip with recorded LLM
  responses (`--replay`), asserting the QA report passes and that the
  technique ledger is complete. It runs offline. With a real face in the
  clip, face checks are asserted as executed. Without one, the test asserts
  the ledger honestly reports them as not executed.
- **Script wrappers:** the nine original CLIs keep working against the
  package and have smoke tests.

## 12. Reuse map for the existing scripts

| Script | Where it goes | Kept behaviour and fixes |
|---|---|---|
| `cut_silence.py` | `media/audio.py`, `render/picture.py` | RMS-window pause detection against the file's own floor + 6 dB; style presets; per-segment render then concat; timing map. Punch anchors change from fixed x/y to the face track |
| `mix_audio.py` | `render/sound.py` | per-file LUFS and gain relative to voice; fades; fadeout, swell, dropout ramps; sidechain duck; SFX auto-variation; VO bus; voice clean; static gain + limiter instead of loudnorm's second pass |
| `montage.py` | `render/picture.py` | evenly spaced chunks so progression points survive; speed; printed source times stored in the EDL |
| `insert_beats.py` | `render/picture.py` | freeze and pad beats, now applied per segment so there is never one big filter graph |
| `focus_image.py` | `media/images.py` | the whole guided-attention chain unchanged |
| `music_points.py` | `media/audio.py` | pickup and dip detection; the offset formula |
| `synth_audio.py` | `media/synth.py` | placeholder kit and beds with the bar-3 pickup; flagged in QA |
| `thumb_check.py` | `media/images.py` | real-size sheet and metrics |
| `analyze.py` | `stages/analyze.py`, `stages/verify.py` | scene-cut pacing stats, contact sheet, ebur128 loudness. Its silencedetect is replaced by the RMS method |

## 13. Milestones

Each milestone ends with a demo on real footage: frame grabs, the QA report,
and the plan summary, before the next one starts.

**M1: talking-head long-form, end to end with QA.** Two checkpoints.
- M1a: package skeleton, profiles, ingest, transcribe, analyze (including
  the face track), EDL schema and validation, timing map, picture, graphics
  and sound renderers, verify, package. Driven by a hand-written EDL so the
  deterministic half is proven first. Unit tests. Golden test.
- M1b: the plan stage (story pass, decisions, EDL assembly), review
  artifacts and preview, `--yolo`, and the CLI commands `new`, `run`,
  `plan`, `approve`, `render`, `verify`, `package`.

**M2: Shorts engine.** Selection, face-tracked vertical render,
word-by-word captions, context label, loop ending, vertical QA checks.

**M3: chat-skit format and the `frogbertsaid` profile.** Script parser,
compositor, punch-ins, typing indicators, highlight band, story pass over a
script, QA.

**M4: batch mode.** Watch folder, SQLite queue, detached worker, job
listing and log tailing.

**M5: web UI.** Project list, plan review and EDL editor, preview player,
approve and re-render, QA viewer.

## 14. What I need from you before M1

1. **Location.** `autoedit/` inside this repo, on the designated branch.
2. **Sample footage.** One talking-head clip of 1 to 3 minutes for demos,
   and a 20 to 60 s clip you are happy to commit under `autoedit/tests/fixtures/`
   for the golden test. A URL or a path in the repo both work.
3. **Assets.** A font file or two (Poppins if you want the reference look),
   any licensed music and SFX folders, and for M3 the avatar images and one
   real FrogBertSaid script. Until then, synth placeholders are used and
   flagged.
4. **API key.** `ANTHROPIC_API_KEY` for the plan-stage demo, set as an
   environment secret for this cloud environment.
5. **Decisions to confirm.** Default model `claude-opus-5-5`. The dead-air
   cut list is decided by code from the profile preset, and the LLM only
   protects pauses and adds beats. Voiceover slots hold a gap and print the
   line for you to record, with no synthetic voice in the final render.
6. **Chat-skit voices.** Silent text with SFX and music, or spoken lines
   from a TTS voice per character.

## 15. Risks and mitigations

- **CPU-only transcription is slow on long footage.** Proxy audio at
  16 kHz, int8 models, and the stage runs as a background job with progress.
- **mediapipe wheel availability** on your machine. OpenCV YuNet is the
  fallback with the same track format.
- **LLM output drift.** Structured outputs plus validation plus anchor
  resolution means a bad decision fails loudly instead of rendering wrong.
- **Fonts.** libass sizing is verified by measurement, and profiles fail
  fast if the TTF path is missing rather than silently using DejaVu.
- **Long renders.** Every stage is resumable from its artifacts, and the
  worker survives the shell.

## Implementation notes (what differs from the plan above)

- **Stage order** is ingest, transcribe, analyze, plan, render, shorts, package, verify. Package runs before
  verify so the QA report covers the thumbnail and the packaging ledger.
- **Anchor pads** up to 1 s are cosmetic and applied in output time inside one piece (a padded caption end
  never lands in a segment that moved elsewhere after a hook reorder); longer pads are structural and resolve
  in source time. Fadeouts and swells anchor by source time, clamped to their music section.
- **Music sections** anchor to segments in output order, so a hook moved to the front stays covered and a
  chapter card belongs to the section that follows it.
- **Verify** measures music automation on a pre-duck stem (`stems/music_raw.wav`) and checks caption ink
  against the face box by rendering the subtitles alone; the limiter runs at 4x oversampling with a 1 dB
  margin under the true-peak target, and the mix makes up to three gain passes on peaky music-only mixes.
- **chat-skit** composes the episode into the source video; the newest message is the focus track, so the
  talking-head renderer's face-anchored punch-ins and QA apply unchanged. Shorts for chat-skit (a native
  vertical chat layout) are reported as not executed rather than produced as unreadable 9:16 slices.
- **Soundscape atmosphere** beds under stills and B-roll are not implemented and are reported as not executed.
- **No transcriber available** (no whisper model and no pocketsphinx) degrades to a dead-air-only edit with the
  reason in the QA report instead of failing the batch job.
- **Planner effort** is not passed to the API yet (the structured-output call uses the model default).
