"""SQLite job queue shared by the watcher, the worker, the CLI and the web UI."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    command TEXT NOT NULL,
    args TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'queued',
    created REAL NOT NULL,
    started REAL,
    finished REAL,
    pid INTEGER,
    error TEXT,
    log TEXT
);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status);
"""


@dataclass
class Job:
    id: int
    project: str
    command: str
    args: dict[str, Any]
    status: str
    created: float
    started: float | None = None
    finished: float | None = None
    pid: int | None = None
    error: str | None = None
    log: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "project": self.project, "command": self.command, "args": self.args, "status": self.status,
                "created": self.created, "started": self.started, "finished": self.finished, "pid": self.pid,
                "error": self.error, "log": self.log}


def _pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class JobQueue:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        return c

    @staticmethod
    def _row(r: sqlite3.Row) -> Job:
        return Job(r["id"], r["project"], r["command"], json.loads(r["args"] or "{}"), r["status"], r["created"],
                   r["started"], r["finished"], r["pid"], r["error"], r["log"])

    def add(self, project: str, command: str, args: dict[str, Any] | None = None) -> Job:
        with self._conn() as c:
            cur = c.execute("INSERT INTO jobs(project, command, args, status, created) VALUES (?,?,?,?,?)",
                            (str(project), command, json.dumps(args or {}), "queued", time.time()))
            return self.get(int(cur.lastrowid))  # type: ignore[arg-type]

    def get(self, job_id: int) -> Job:
        with self._conn() as c:
            r = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if r is None:
                raise KeyError(job_id)
            return self._row(r)

    def has_pending(self, project: str) -> bool:
        with self._conn() as c:
            r = c.execute("SELECT 1 FROM jobs WHERE project=? AND status IN ('queued','running') LIMIT 1", (str(project),)).fetchone()
            return r is not None

    def claim(self, pid: int) -> Job | None:
        """Atomically take the oldest queued job."""
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            r = c.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
            if r is None:
                c.execute("COMMIT")
                return None
            c.execute("UPDATE jobs SET status='running', started=?, pid=? WHERE id=?", (time.time(), pid, r["id"]))
            c.execute("COMMIT")
            return self.get(int(r["id"]))

    def finish(self, job_id: int, status: str, error: str | None = None, log: str | None = None) -> None:
        with self._conn() as c:
            c.execute("UPDATE jobs SET status=?, finished=?, error=?, log=COALESCE(?, log) WHERE id=?",
                      (status, time.time(), error, log, job_id))

    def set_log(self, job_id: int, log: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE jobs SET log=? WHERE id=?", (log, job_id))

    def requeue_orphans(self) -> int:
        """Jobs marked running whose worker process is gone go back to the queue."""
        n = 0
        with self._conn() as c:
            for r in c.execute("SELECT id, pid FROM jobs WHERE status='running'").fetchall():
                if not _pid_alive(r["pid"]):
                    c.execute("UPDATE jobs SET status='queued', started=NULL, pid=NULL WHERE id=?", (r["id"],))
                    n += 1
        return n

    def list(self, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
        with self._conn() as c:
            q = "SELECT * FROM jobs" + (" WHERE status=?" if status else "") + " ORDER BY id DESC LIMIT ?"
            rows = c.execute(q, ((status, limit) if status else (limit,))).fetchall()
            return [self._row(r).as_dict() for r in rows]

    def cancel(self, job_id: int) -> bool:
        with self._conn() as c:
            cur = c.execute("UPDATE jobs SET status='cancelled', finished=? WHERE id=? AND status='queued'", (time.time(), job_id))
            return cur.rowcount > 0
