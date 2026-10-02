import json
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from autoedit.config import Settings  # noqa: E402
from autoedit.project import Project  # noqa: E402
from autoedit.web import app as webapp  # noqa: E402


@pytest.fixture
def client(tmp_path: Path):
    projects = tmp_path / "projects"
    projects.mkdir()
    src = tmp_path / "clip.mp4"
    src.write_bytes(b"\0" * 10)
    p = Project.create(projects, "Demo Video", src, "personal", "talking-head")
    (p.dir("plan") / "plan_summary.md").write_text("# Plan: Demo\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
    p.edl_json.write_text(json.dumps({"version": 1, "meta": {"project": "Demo Video", "profile": "personal", "format": "talking-head",
                                      "source": str(src), "duration": 10, "fps": "30/1", "width": 1920, "height": 1080},
                                      "segments": [{"id": "s1", "src_in": 0, "src_out": 10}]}))
    (p.dir("verify") / "frames").mkdir(parents=True, exist_ok=True)
    (p.dir("verify") / "frames" / "x.png").write_bytes(b"png")
    p.qa_json.write_text(json.dumps({"overall": "pass", "hand_edited_edl": False, "outputs": {"long": {
        "label": "long", "file": "f", "duration": 9.5, "size": [1920, 1080], "overall": "pass",
        "checks": [{"id": "hook", "status": "pass", "summary": "ok", "target": "3 s", "frames": ["frames/x.png"], "details": None}],
        "executed": [], "not_executed": [{"id": "broll_every_noun", "status": "not_executed", "description": "d", "reason": "no assets"}]}}}))
    webapp._settings = Settings(projects_dir=projects, models_dir=tmp_path / "models")
    return TestClient(webapp.app), p


def test_pages_render(client):
    c, p = client
    assert "Demo Video" in c.get("/").text
    assert c.get("/p/demo-video").status_code == 200
    plan = c.get("/p/demo-video/plan").text
    assert "<table>" in plan and "Approve for render" in plan
    qa = c.get("/p/demo-video/qa").text
    assert "broll_every_noun" in qa and "frames/x.png" in qa
    assert c.get("/jobs").status_code == 200
    assert c.get("/p/nope").status_code == 404


def test_enqueue_approve_and_edl_roundtrip(client):
    c, p = client
    r = c.post("/p/demo-video/enqueue", data={"command": "render", "yolo": "1", "llm": "replay"}, follow_redirects=False)
    assert r.status_code == 303
    jobs = c.get("/jobs.json").json()["jobs"]
    assert jobs[0]["command"] == "render" and jobs[0]["args"]["yolo"] is True
    r = c.post("/p/demo-video/approve", follow_redirects=False)
    assert r.status_code == 303 and "approved" in r.headers["location"]
    assert Project.open(p.root).approved
    bad = c.post("/p/demo-video/edl", data={"edl_text": "{not json"})
    assert bad.status_code == 400
    good = json.loads(p.edl_json.read_text())
    good["notes"] = ["edited in the UI"]
    r = c.post("/p/demo-video/edl", data={"edl_text": json.dumps(good)}, follow_redirects=False)
    assert r.status_code == 303
    assert not Project.open(p.root).approved, "an edit resets approval"


def test_file_serving_stays_inside_the_project(client):
    c, p = client
    assert c.get("/p/demo-video/file/06_verify/frames/x.png").status_code == 200
    assert c.get("/p/demo-video/file/../../etc/passwd").status_code == 404
    assert c.get("/p/demo-video/file/06_verify/missing.png").status_code == 404
