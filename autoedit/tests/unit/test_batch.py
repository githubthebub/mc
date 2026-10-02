import json
import time
from pathlib import Path

from autoedit.batch.queue import JobQueue
from autoedit.batch.watcher import scan_once


def test_queue_claim_finish_and_orphans(tmp_path: Path):
    q = JobQueue(tmp_path / "queue.db")
    a = q.add("/p/a", "run", {"yolo": True})
    b = q.add("/p/b", "render")
    assert q.has_pending("/p/a")
    j = q.claim(pid=999999)              # a pid that does not exist
    assert j is not None and j.id == a.id and j.status == "running"
    assert q.requeue_orphans() == 1      # the dead worker's job goes back to the queue
    j = q.claim(pid=1)                   # pid 1 is alive
    assert j.id == a.id
    q.finish(j.id, "done")
    assert q.get(a.id).status == "done" and not q.has_pending("/p/a")
    assert q.cancel(b.id) and q.get(b.id).status == "cancelled"
    assert [x["id"] for x in q.list()] == [b.id, a.id]


def test_watcher_registers_only_stable_unseen_files(tmp_path: Path, monkeypatch):
    watch = tmp_path / "inbox"
    watch.mkdir()
    projects = tmp_path / "projects"
    q = JobQueue(tmp_path / "queue.db")
    clip = watch / "my clip.mp4"
    clip.write_bytes(b"\0" * 1000)
    sizes: dict = {}
    # first sight: remember the size, do not register
    assert scan_once(watch, "personal", None, q, projects, yolo=True, sizes=sizes) == []
    # same size but not yet stable for 30 s
    assert scan_once(watch, "personal", None, q, projects, yolo=True, sizes=sizes) == []
    sizes["my clip.mp4"] = (1000, time.time() - 31)
    reg = scan_once(watch, "personal", None, q, projects, yolo=True, sizes=sizes)
    assert len(reg) == 1 and (projects / "my-clip" / "project.yaml").exists()
    assert q.list()[0]["command"] == "run" and q.list()[0]["args"]["yolo"] is True
    # seen files are never registered twice
    assert scan_once(watch, "personal", None, q, projects, yolo=True, sizes=sizes) == []
    seen = json.loads((watch / ".autoedit_seen.json").read_text())
    assert "my clip.mp4" in seen
