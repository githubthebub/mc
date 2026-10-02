# autoedit

Raw footage or a script in; a publish-ready YouTube long-form video and Shorts out, applying the
`video-editor` skill's editing, story, sound-design and packaging philosophy. See `docs/PLAN.md`.

```
pip install -e ".[dev]"
autoedit new "My video" --source footage.mp4 --profile personal
autoedit run projects/my-video            # stops at the review gate after planning
autoedit approve projects/my-video        # or: autoedit run projects/my-video --yolo
```
