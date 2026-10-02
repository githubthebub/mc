"""autoedit command line: new | run | plan | approve | render | verify | package | shorts | batch | worker | serve."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import load_settings
from .project import STAGES, Project


def _project(path: str) -> Project:
    p = Path(path).expanduser()
    if not (p / "project.yaml").exists():
        cands = [load_settings().projects_dir / path]
        for c in cands:
            if (c / "project.yaml").exists():
                return Project.open(c)
        print(f"not a project: {path}", file=sys.stderr)
        sys.exit(2)
    return Project.open(p)


def cmd_new(a: argparse.Namespace) -> int:
    s = load_settings()
    opts = {}
    if a.transcript:
        opts["transcript"] = str(Path(a.transcript).expanduser().resolve())
    if a.script:
        opts["script"] = str(Path(a.script).expanduser().resolve())
    p = Project.create(s.projects_dir, a.name, Path(a.source) if a.source else None, a.profile, a.format,
                       copy_source=a.copy, options=opts)
    print(json.dumps(p.summary(), indent=1))
    return 0


def cmd_run(a: argparse.Namespace) -> int:
    from .pipeline import run_pipeline
    s = load_settings()
    p = _project(a.project)
    res = run_pipeline(p, s, upto=a.upto, force=a.force, yolo=a.yolo, llm=a.llm)
    print(json.dumps({k: (v if isinstance(v, str) else "ok") for k, v in res.items()}, indent=1))
    if res.get("review"):
        print(f"\nReview: {p.dir('plan') / 'plan_summary.md'}\nPreview: {p.dir('plan') / 'preview.mp4'}\n"
              f"Then: autoedit approve {p.root}   (or autoedit run --yolo)")
    return 0


def _stage_cmd(stage: str):
    def f(a: argparse.Namespace) -> int:
        from .pipeline import NotApproved, run_pipeline, run_stage
        s = load_settings()
        p = _project(a.project)
        if getattr(a, "deps", False):
            run_pipeline(p, s, upto=STAGES[STAGES.index(stage) - 1], yolo=True, llm=getattr(a, "llm", "auto"))
        try:
            r = run_stage(p, stage, s, force=True, yolo=getattr(a, "yolo", False), llm=getattr(a, "llm", "auto"))
        except NotApproved as e:
            print(str(e), file=sys.stderr)
            return 3
        if stage == "verify":
            print(json.dumps({"overall": r["overall"], "checks": {c["id"]: c["status"] for c in r["outputs"]["long"]["checks"]},
                              "not_executed": [n["id"] for n in r["outputs"]["long"]["not_executed"]]}, indent=1))
            print(f"report: {p.dir('verify') / 'qa_report.md'}")
        elif stage == "plan":
            print(f"plan: {p.dir('plan') / 'plan_summary.md'}\npreview: {p.dir('plan') / 'preview.mp4'}")
        elif stage == "package":
            print(json.dumps({"file": r["file"], "title": r["title"], "thumbnail": r["thumbnail"]["file"]}, indent=1))
        else:
            print("ok")
        return 0
    return f


def cmd_approve(a: argparse.Namespace) -> int:
    p = _project(a.project)
    if not p.edl_json.exists():
        print("no EDL to approve; run `autoedit plan` first", file=sys.stderr)
        return 2
    from .edl.schema import EDL
    from .edl.validate import validate
    edl = EDL.load(p.edl_json)
    problems = validate(edl, p)
    errors = [x for x in problems if x.level == "error"]
    for x in problems:
        print(f"{x.level}: {x.msg}")
    if errors:
        print("EDL has errors; fix them before approving", file=sys.stderr)
        return 2
    p.approve()
    print(f"approved {p.root}")
    return 0


def cmd_status(a: argparse.Namespace) -> int:
    s = load_settings()
    roots = [Path(a.project)] if a.project else sorted(d for d in s.projects_dir.glob("*") if (d / "project.yaml").exists())
    for r in roots:
        print(json.dumps(Project.open(r).summary()))
    return 0


def cmd_shorts(a: argparse.Namespace) -> int:
    from .pipeline import profile_for
    from .stages import shorts
    s = load_settings()
    p = _project(a.project)
    r = shorts.run(p, s, profile_for(p, s), p.log("shorts"), count=a.count, llm=a.llm)
    print(json.dumps(r, indent=1, default=str))
    return 0


def cmd_batch(a: argparse.Namespace) -> int:
    from .batch.watcher import watch
    return watch(Path(a.watch), a.profile, a.format, yolo=a.yolo, once=a.once)


def cmd_worker(a: argparse.Namespace) -> int:
    from .batch.worker import worker_main
    return worker_main(daemon=a.daemon, once=a.once)


def cmd_jobs(a: argparse.Namespace) -> int:
    from .batch.queue import JobQueue
    s = load_settings()
    for j in JobQueue(s.projects_dir / "queue.db").list():
        print(json.dumps(j))
    return 0


def cmd_serve(a: argparse.Namespace) -> int:
    from .web.app import serve
    return serve(a.host, a.port)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="autoedit", description="Raw footage or a script in; YouTube video and Shorts out.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new", help="create a project folder")
    n.add_argument("name")
    n.add_argument("--source", help="video file (talking-head)")
    n.add_argument("--script", help="script YAML (chat-skit)")
    n.add_argument("--profile", default="personal")
    n.add_argument("--format", default=None, help="talking-head | chat-skit (default: the profile's)")
    n.add_argument("--transcript", help="use this word-level transcript JSON instead of transcribing")
    n.add_argument("--copy", action="store_true", help="copy the source into the project")
    n.set_defaults(fn=cmd_new)

    r = sub.add_parser("run", help="run the pipeline (stops at review unless --yolo)")
    r.add_argument("project")
    r.add_argument("--upto", default="verify", choices=STAGES)
    r.add_argument("--force", action="store_true", help="re-run stages that are already done")
    r.add_argument("--yolo", action="store_true", help="skip the human review gate")
    r.add_argument("--llm", default="auto", choices=["auto", "off", "replay"], help="plan with Claude, code only, or replay saved responses")
    r.set_defaults(fn=cmd_run)

    for st in ("ingest", "transcribe", "analyze", "plan", "render", "package", "verify"):  # shorts has its own command
        sp = sub.add_parser(st, help=f"run the {st} stage")
        sp.add_argument("project")
        sp.add_argument("--deps", action="store_true", help="run earlier stages first if needed")
        if st in ("plan",):
            sp.add_argument("--llm", default="auto", choices=["auto", "off", "replay"])
        if st == "render":
            sp.add_argument("--yolo", action="store_true")
        sp.set_defaults(fn=_stage_cmd(st))

    ap_ = sub.add_parser("approve", help="approve the EDL for rendering (validates it first)")
    ap_.add_argument("project")
    ap_.set_defaults(fn=cmd_approve)

    st_ = sub.add_parser("status", help="list projects and stage states")
    st_.add_argument("project", nargs="?")
    st_.set_defaults(fn=cmd_status)

    sh = sub.add_parser("shorts", help="select and render Shorts from a rendered project")
    sh.add_argument("project")
    sh.add_argument("--count", type=int, default=None)
    sh.add_argument("--llm", default="auto", choices=["auto", "off", "replay"])
    sh.set_defaults(fn=cmd_shorts)

    b = sub.add_parser("batch", help="watch a folder and queue new files as projects")
    b.add_argument("--watch", required=True)
    b.add_argument("--profile", default="personal")
    b.add_argument("--format", default=None)
    b.add_argument("--yolo", action="store_true")
    b.add_argument("--once", action="store_true", help="scan once and exit")
    b.set_defaults(fn=cmd_batch)

    w = sub.add_parser("worker", help="process the job queue")
    w.add_argument("--daemon", action="store_true", help="detach and keep running after this shell exits")
    w.add_argument("--once", action="store_true", help="process one job and exit")
    w.set_defaults(fn=cmd_worker)

    j = sub.add_parser("jobs", help="list queued jobs")
    j.set_defaults(fn=cmd_jobs)

    sv = sub.add_parser("serve", help="local web UI")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8765)
    sv.set_defaults(fn=cmd_serve)

    a = ap.parse_args(argv)
    if a.cmd == "new" and a.format is None:
        from .profile import load_profile
        a.format = load_profile(a.profile, load_settings().profiles_dir).format
    return int(a.fn(a) or 0)


if __name__ == "__main__":
    sys.exit(main())
