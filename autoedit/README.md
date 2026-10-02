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
