"""FastAPI app for the local UI. Start with `autoedit serve`."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..batch.queue import JobQueue
from ..config import Settings, load_settings
from ..edl.schema import EDL
from ..edl.validate import validate
from ..paths import BUILTIN_PROFILES_DIR
from ..project import STAGES, Project

HERE = Path(__file__).parent
app = FastAPI(title="autoedit")
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
templates = Jinja2Templates(directory=str(HERE / "templates"))
_settings: Settings | None = None


def settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def queue() -> JobQueue:
    return JobQueue(settings().projects_dir / "queue.db")


def all_projects() -> list[Project]:
    d = settings().projects_dir
    if not d.exists():
        return []
    return [Project.open(p) for p in sorted(d.iterdir()) if (p / "project.yaml").exists()]


def project_or_404(slug: str) -> Project:
    p = settings().projects_dir / slug
    if not (p / "project.yaml").exists():
        raise HTTPException(404, f"no project {slug}")
    return Project.open(p)


def progress_of(p: Project) -> dict[str, Any]:
    out = {}
    for f in (p.root / "logs").glob("*.progress.json"):
        try:
            d = json.loads(f.read_text())
            if time.time() - d.get("ts", 0) < 600:
                out[d["stage"]] = d
        except (ValueError, OSError):
            pass
    return out


def qa_of(p: Project) -> dict[str, Any] | None:
    if not p.qa_json.exists():
        return None
    try:
        q = json.loads(p.qa_json.read_text())
    except ValueError:
        return None
    return {"overall": q.get("overall"), "outputs": {k: {"overall": v["overall"], "checks": {c["id"]: c["status"] for c in v["checks"]}}
                                                     for k, v in q.get("outputs", {}).items()}}


def worker_alive() -> dict[str, Any]:
    pidfile = settings().projects_dir / "worker.pid"
    pid = None
    alive = False
    if pidfile.exists():
        try:
            pid = int(pidfile.read_text().strip())
            os.kill(pid, 0)
            alive = True
        except (OSError, ValueError):
            alive = False
    return {"pid": pid, "alive": alive}


def profiles() -> list[str]:
    names = set()
    for d in [settings().profiles_dir, BUILTIN_PROFILES_DIR]:
        if d and Path(d).exists():
            names.update(f.stem for f in Path(d).glob("*.yaml"))
    return sorted(names)


def project_view(p: Project) -> dict[str, Any]:
    s = p.summary()
    s["qa"] = qa_of(p)
    s["slug"] = p.root.name
    s["progress"] = progress_of(p)
    s["jobs"] = [j for j in queue().list(200) if j["project"] == str(p.root)][:10]
    s["has_plan"] = p.edl_json.exists()
    s["has_preview"] = (p.dir("plan") / "preview.mp4").exists()
    s["has_final"] = p.final_mp4.exists()
    meta = p.dir("package") / "metadata.json"
    s["package"] = json.loads(meta.read_text()) if meta.exists() else None
    return s


# ---- pages -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "projects": [project_view(p) for p in all_projects()], "worker": worker_alive(), "profiles": profiles(),
        "projects_dir": str(settings().projects_dir)})


@app.post("/new")
def new_project(name: str = Form(...), source: str = Form(""), script: str = Form(""), profile: str = Form("personal"),
                transcript: str = Form("")):
    from ..profile import load_profile
    fmt = load_profile(profile, settings().profiles_dir).format
    opts = {}
    if script.strip():
        opts["script"] = str(Path(script.strip()).expanduser().resolve())
    if transcript.strip():
        opts["transcript"] = str(Path(transcript.strip()).expanduser().resolve())
    try:
        p = Project.create(settings().projects_dir, name, Path(source.strip()) if source.strip() else None, profile, fmt, options=opts)
    except (FileExistsError, FileNotFoundError) as e:
        raise HTTPException(400, str(e)) from e
    return RedirectResponse(f"/p/{p.root.name}", status_code=303)


@app.get("/p/{slug}", response_class=HTMLResponse)
def project_page(request: Request, slug: str):
    p = project_or_404(slug)
    return templates.TemplateResponse(request, "project.html", {"p": project_view(p), "stages": STAGES, "worker": worker_alive()})


@app.get("/p/{slug}/status.json")
def project_status(slug: str):
    return JSONResponse(project_view(project_or_404(slug)))


@app.post("/p/{slug}/enqueue")
def enqueue(slug: str, command: str = Form("run"), yolo: str = Form(""), force: str = Form(""), llm: str = Form("auto")):
    p = project_or_404(slug)
    if command not in ("run", "plan", "render", "shorts", "package", "verify"):
        raise HTTPException(400, "bad command")
    args = {"llm": llm}
    if yolo:
        args["yolo"] = True
    if force:
        args["force"] = True
    queue().add(str(p.root), command, args)
    return RedirectResponse(f"/p/{slug}", status_code=303)


@app.post("/p/{slug}/approve")
def approve(slug: str):
    p = project_or_404(slug)
    if not p.edl_json.exists():
        raise HTTPException(400, "no EDL yet")
    edl = EDL.load(p.edl_json)
    problems = validate(edl, p)
    if any(x.level == "error" for x in problems):
        return RedirectResponse(f"/p/{slug}/plan?msg=errors", status_code=303)
    p.approve()
    return RedirectResponse(f"/p/{slug}/plan?msg=approved", status_code=303)


@app.get("/p/{slug}/plan", response_class=HTMLResponse)
def plan_page(request: Request, slug: str, msg: str = ""):
    import markdown
    p = project_or_404(slug)
    d = p.dir("plan")
    summary_md = (d / "plan_summary.md").read_text() if (d / "plan_summary.md").exists() else "_No plan yet. Queue `plan`._"
    edl_text = p.edl_json.read_text() if p.edl_json.exists() else ""
    problems = []
    if p.edl_json.exists():
        try:
            problems = [{"level": x.level, "msg": x.msg} for x in validate(EDL.load(p.edl_json), p)]
        except Exception as e:  # noqa: BLE001
            problems = [{"level": "error", "msg": f"EDL does not parse: {e}"}]
    markers: list[dict[str, Any]] = []
    out_dur = 0.0
    res_path = p.dir("render") / "preview" / "resolved.json"
    if res_path.exists():
        res = json.loads(res_path.read_text())
        out_dur = float(res.get("out_duration") or 0.0)
        for kind, color in (("captions", "#FFD400"), ("zooms", "#3CC8FF"), ("beats", "#57F287"), ("cards", "#FFFFFF"),
                            ("dropouts", "#FF4E2A"), ("fadeouts", "#B57BFF"), ("swells", "#FF9F1C"), ("music", "#8899AA")):
            for it in res.get(kind, []):
                t0 = it.get("out_in", it.get("out"))
                t1 = it.get("out_out", it.get("out_end", (t0 or 0) + 0.5))
                if t0 is None:
                    continue
                markers.append({"kind": kind, "id": it.get("id") or it.get("ref") or kind, "t0": t0, "t1": t1, "color": color,
                                "label": it.get("text") or it.get("reason") or it.get("mood") or ""})
    return templates.TemplateResponse(request, "plan.html", {
        "p": project_view(p), "summary_html": markdown.markdown(summary_md, extensions=["tables"]),
        "edl_text": edl_text, "problems": problems, "markers": markers, "out_dur": out_dur, "msg": msg,
        "hand_edited": p.edl_was_hand_edited()})


@app.post("/p/{slug}/edl")
def save_edl(slug: str, edl_text: str = Form(...)):
    p = project_or_404(slug)
    try:
        edl = EDL.model_validate(json.loads(edl_text))
    except Exception as e:  # noqa: BLE001
        return HTMLResponse(f"<pre>EDL rejected:\n{e}</pre><p><a href='/p/{slug}/plan'>back</a></p>", status_code=400)
    edl.meta.created_by = "human"
    edl.save(p.edl_json)
    p.state["approved"] = False
    p.save_state()
    return RedirectResponse(f"/p/{slug}/plan?msg=saved", status_code=303)


@app.get("/p/{slug}/qa", response_class=HTMLResponse)
def qa_page(request: Request, slug: str):
    p = project_or_404(slug)
    report = json.loads(p.qa_json.read_text()) if p.qa_json.exists() else None
    return templates.TemplateResponse(request, "qa.html", {"p": project_view(p), "report": report})


@app.get("/p/{slug}/file/{path:path}")
def project_file(slug: str, path: str):
    p = project_or_404(slug)
    root = p.root.resolve()
    target = (root / path).resolve()
    if root not in target.parents or not target.is_file():
        raise HTTPException(404, "no such file")
    return FileResponse(str(target))


@app.get("/jobs", response_class=HTMLResponse)
def jobs_page(request: Request):
    return templates.TemplateResponse(request, "jobs.html", {"jobs": queue().list(100), "worker": worker_alive()})


@app.get("/jobs.json")
def jobs_json():
    return JSONResponse({"jobs": queue().list(100), "worker": worker_alive()})


@app.post("/jobs/{job_id}/retry")
def job_retry(job_id: int):
    q = queue()
    old = q.get(job_id)
    q.add(old.project, old.command, old.args)
    return RedirectResponse("/jobs", status_code=303)


@app.post("/jobs/{job_id}/cancel")
def job_cancel(job_id: int):
    queue().cancel(job_id)
    return RedirectResponse("/jobs", status_code=303)


@app.get("/jobs/{job_id}/log", response_class=HTMLResponse)
def job_log(job_id: int):
    j = queue().get(job_id)
    text = Path(j.log).read_text()[-20000:] if j.log and Path(j.log).exists() else "(no log yet)"
    return HTMLResponse(f"<pre style='white-space:pre-wrap;font:13px monospace;background:#111;color:#ddd;padding:12px'>{text}</pre>")


@app.post("/worker/start")
def worker_start():
    from ..batch.worker import worker_main
    worker_main(daemon=True)
    return RedirectResponse("/jobs", status_code=303)


def serve(host: str = "127.0.0.1", port: int = 8765) -> int:
    import uvicorn
    print(f"autoedit UI: http://{host}:{port}  (projects in {settings().projects_dir})")
    uvicorn.run(app, host=host, port=port, log_level="warning")
    return 0
