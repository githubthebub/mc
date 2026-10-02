"""Golden test for the chat-skit format: a scripted episode composes into a Discord-style source, the
focus track stands in for the face, punch-ins land on the punchlines, and QA passes (code-only plan)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from autoedit.config import Settings
from autoedit.edl.schema import EDL
from autoedit.media.probe import probe
from autoedit.pipeline import run_pipeline
from autoedit.project import Project
from tests.fixtures.chat.make_avatars import draw

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "chat"


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> tuple[Project, Settings]:
    d = tmp_path_factory.mktemp("chat")
    shutil.copy(FIXTURES / "episode.yaml", d / "episode.yaml")
    draw(d)
    root = tmp_path_factory.mktemp("projects")
    settings = Settings(projects_dir=root, models_dir=Path("~/.cache/autoedit/models").expanduser())
    settings.render.workers = 2
    p = Project.create(root, "FrogBert Golden", None, "frogbertsaid", "chat-skit", options={"script": str(d / "episode.yaml")})
    return p, settings


def test_chat_skit_end_to_end(project):
    p, settings = project
    run_pipeline(p, settings, yolo=True, llm="off", quiet=True)
    assert all(p.is_done(s) for s in ("ingest", "transcribe", "analyze", "plan", "render", "shorts", "package", "verify")), p.summary()

    src = probe(p.ingest_source)
    assert (src.width, src.height) == (1920, 1080) and 30 < src.duration < 60
    tr = json.loads(p.transcript_json.read_text())
    assert len(tr["sentences"]) == 8 and tr["sentences"][1]["text"].startswith("FrogBert:")
    track = json.loads(p.face_track_json.read_text())
    assert track["detector"].startswith("chat-skit") and track["count"] > 300

    edl = EDL.load(p.edl_json)
    assert len(edl.segments) == 1, "scripted: every pause is deliberate, nothing is cut"
    assert len(edl.zooms) == 3 and all(z.scale > 1.1 for z in edl.zooms), "a punch-in per punchline"
    assert len(edl.sfx) >= 12 and len(edl.captions) == 0 and len(edl.music) == 1

    qa = json.loads(p.qa_json.read_text())
    long = qa["outputs"]["long"]
    st = {c["id"]: c["status"] for c in long["checks"]}
    for cid in ("dead_air", "loudness", "true_peak", "faces_not_cropped", "hook"):
        assert st[cid] == "pass", (cid, next(c for c in long["checks"] if c["id"] == cid))
    assert st["music_automation"] == "not_executed", "code-only plan: no music moves to measure"
    assert long["overall"] in ("pass", "warn")
    assert st["text_safe_zones"] == "not_executed"
    rendered = EDL.load(p.dir("render") / "edl.rendered.json")
    assert rendered.techniques["dead_air_removal"].status == "not_executed"
    assert rendered.techniques["emphasis_zooms"].status == "executed"
    assert rendered.techniques["shorts_face_tracked"].status == "not_executed"
    assert "chat-skit" in (rendered.techniques["shorts_face_tracked"].reason or "")
    meta = json.loads((p.dir("package") / "metadata.json").read_text())
    assert Path(meta["file"]).exists() and meta["shorts"] == []
