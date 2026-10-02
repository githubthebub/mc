"""The job worker: one job at a time, each stage as a child process with its own log, detached from the
launching shell when started with --daemon so long renders survive the terminal closing."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from ..config import load_settings
from .queue import Job, JobQueue

POLL_S = 5.0


def _command(job: Job) -> list[str]:
    a = job.args or {}
    cmd = [sys.executable, "-m", "autoedit.cli", job.command, job.project]
    if job.command == "run":
        if a.get("yolo"):
            cmd.append("--yolo")
        if a.get("force"):
            cmd.append("--force")
        if a.get("llm"):
            cmd += ["--llm", str(a["llm"])]
        if a.get("upto"):
            cmd += ["--upto", str(a["upto"])]
    elif job.command in ("plan", "shorts") and a.get("llm"):
        cmd += ["--llm", str(a["llm"])]
    elif job.command == "render" and a.get("yolo"):
        cmd.append("--yolo")
    return cmd


def run_job(queue: JobQueue, job: Job) -> None:
    proj = Path(job.project)
    logs = proj / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / f"job_{job.id}_{job.command}.log"
    queue.set_log(job.id, str(log_path))
    with log_path.open("a") as lf:
        lf.write(f"# job {job.id}: {' '.join(_command(job))}\n")
        lf.flush()
        proc = subprocess.Popen(_command(job), stdout=lf, stderr=subprocess.STDOUT, cwd=str(proj.parent))
        rc = proc.wait()
    if rc == 0:
        queue.finish(job.id, "done")
    elif rc == 3:
        queue.finish(job.id, "waiting_approval", error="EDL needs approval: autoedit approve <project>")
    else:
        tail = "".join(log_path.read_text().splitlines(keepends=True)[-20:])
        queue.finish(job.id, "failed", error=f"exit {rc}\n{tail}")


def worker_loop(queue: JobQueue, once: bool = False) -> int:
    stop = {"flag": False}

    def _sig(*_: object) -> None:
        stop["flag"] = True

    import threading
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, _sig)
        signal.signal(signal.SIGINT, _sig)
    pid = os.getpid()
    n = queue.requeue_orphans()
    if n:
        print(f"requeued {n} orphaned job(s)")
    while not stop["flag"]:
        job = queue.claim(pid)
        if job is None:
            if once:
                return 0
            time.sleep(POLL_S)
            continue
        print(f"job {job.id}: {job.command} {job.project}")
        run_job(queue, job)
        print(f"job {job.id}: {queue.get(job.id).status}")
        if once:
            return 0
    return 0


def worker_main(daemon: bool = False, once: bool = False) -> int:
    settings = load_settings()
    qpath = settings.projects_dir / "queue.db"
    queue = JobQueue(qpath)
    if daemon:
        settings.projects_dir.mkdir(parents=True, exist_ok=True)
        log = settings.projects_dir / "worker.log"
        pidfile = settings.projects_dir / "worker.pid"
        if pidfile.exists():
            try:
                old = int(pidfile.read_text().strip())
                os.kill(old, 0)
                print(f"worker already running (pid {old})")
                return 0
            except (OSError, ValueError):
                pass
        with log.open("a") as lf:
            proc = subprocess.Popen([sys.executable, "-m", "autoedit.cli", "worker"], stdout=lf, stderr=subprocess.STDOUT,
                                    start_new_session=True, close_fds=True, cwd=str(settings.projects_dir.parent))
        pidfile.write_text(str(proc.pid))
        print(f"worker started (pid {proc.pid}); log {log}")
        return 0
    return worker_loop(queue, once=once)
