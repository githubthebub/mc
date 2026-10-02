# autoedit

Raw footage or a script in; a publish-ready YouTube long-form video and Shorts out, applying the
`video-editor` skill's editing, story, sound-design and packaging philosophy. See `docs/PLAN.md`.

```
pip install -e ".[dev]"
autoedit new "My video" --source footage.mp4 --profile personal
autoedit run projects/my-video            # stops at the review gate after planning
autoedit approve projects/my-video        # or: autoedit run projects/my-video --yolo
```

## Commands

| Command | What it does |
|---|---|
| `autoedit new NAME --source clip.mp4 --profile personal [--transcript words.json]` | create a project folder |
| `autoedit run PROJECT [--yolo] [--llm auto\|off\|replay] [--force]` | ingest, transcribe, analyze, plan, then stop at the review gate (or go all the way with `--yolo`) |
| `autoedit approve PROJECT` | validate and approve the EDL after you reviewed `04_plan/plan_summary.md` and `preview.mp4` |
| `autoedit render\|shorts\|package\|verify PROJECT` | run one stage (`shorts` picks and renders the vertical cuts) |
| `autoedit status [PROJECT]` | stage states |

Outputs land in `07_package/` (named final, `shorts/`, `thumbnail.png`, `metadata.json`) and the QA report in
`06_verify/qa_report.md` with frame grabs under `06_verify/frames/`.

Set `ANTHROPIC_API_KEY` for the planner; without it the plan stage falls back to dead-air removal only and says so.
Configuration: an optional `autoedit.yaml` (projects_dir, models_dir, skill_dir, llm.model, whisper.model, render.workers).

## Batch mode

```
autoedit batch --watch ~/inbox --profile personal --yolo     # registers each new file once its size is stable for 30 s
autoedit worker --daemon                                     # detached worker; survives closing the terminal
autoedit jobs                                                # queue state; autoedit retry ID re-queues a failed job
autoedit enqueue PROJECT render --yolo                        # queue any stage for a project
```

Jobs run one at a time (ffmpeg already uses every core). Each job's output goes to `PROJECT/logs/job_<id>_<cmd>.log`;
stage progress is in `PROJECT/logs/<stage>.progress.json`. Without `--yolo` a batch job stops at the review gate
with status `waiting_approval`; approve and `autoedit enqueue PROJECT run`.

## Web UI

```
pip install -e ".[web]"
autoedit serve            # http://127.0.0.1:8765
```

Project list with stage states and QA verdicts; a project page with live progress, job queueing (run, plan,
render, shorts, package, verify, with yolo/force/planner options) and the package downloads; the plan review page
with the labelled preview player, a timeline of every decision (click to seek), the plan summary, an EDL editor
that validates on save, and approve / re-plan / render buttons; the QA page with every check, its frame grabs,
and the NOT EXECUTED list. Jobs run through the same worker as batch mode (start it from the UI).
