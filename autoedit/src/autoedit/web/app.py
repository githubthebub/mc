"""FastAPI app for the local UI. Start with `autoedit serve`."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import base64
import secrets
import shutil
import threading

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
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

UPLOAD_CHUNK = 1 << 20
ASSET_KINDS = {"music": "music_dir", "sfx": "sfx_dir"}


@app.middleware("http")
async def basic_auth(request: Request, call_next):
    """HTTP basic auth when AUTOEDIT_PASSWORD is set (any user name). /healthz stays open for the platform."""
    pw = os.environ.get("AUTOEDIT_PASSWORD")
    if not pw or request.url.path == "/healthz":
        return await call_next(request)
    header = request.headers.get("authorization", "")
    if header.lower().startswith("basic "):
        try:
            _, _, given = base64.b64decode(header[6:]).decode("utf-8", "replace").partition(":")
            if secrets.compare_digest(given.encode(), pw.encode()):
                return await call_next(request)
        except (ValueError, UnicodeError):
            pass
    return Response("authentication required", status_code=401, headers={"WWW-Authenticate": 'Basic realm="autoedit"'})


@app.get("/healthz")
def healthz():
    return {"ok": True}


def _safe_name(name: str) -> str:
    base = Path(name or "upload").name
    keep = "".join(c if c.isalnum() or c in "._- " else "_" for c in base).strip() or "upload"
    return keep[:120]


async def save_upload(up: UploadFile, dest_dir: Path) -> Path:
    """Stream an upload to disk in chunks (videos can be several GB)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / _safe_name(up.filename or "upload")
    with dest.open("wb") as f:
        while True:
            chunk = await up.read(UPLOAD_CHUNK)
            if not chunk:
                break
            f.write(chunk)
    await up.close()
    return dest


def _has_file(up: UploadFile | None) -> bool:
    return up is not None and bool(up.filename)
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


_worker_thread: threading.Thread | None = None


def start_worker_thread() -> None:
    """Run the job worker inside this process (hosted mode: one machine runs the UI and the jobs)."""
    global _worker_thread
    if _worker_thread is not None and _worker_thread.is_alive():
        return
    from ..batch.worker import worker_loop
    _worker_thread = threading.Thread(target=worker_loop, args=(queue(),), name="autoedit-worker", daemon=True)
    _worker_thread.start()


def worker_alive() -> dict[str, Any]:
    if _worker_thread is not None and _worker_thread.is_alive():
        return {"pid": os.getpid(), "alive": True, "in_process": True}
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
async def new_project(name: str = Form(...), source: str = Form(""), script: str = Form(""), profile: str = Form("personal"),
                      transcript: str = Form(""), source_file: UploadFile | None = File(None),
                      script_file: UploadFile | None = File(None), transcript_file: UploadFile | None = File(None),
                      avatar_files: list[UploadFile] | None = File(None)):
    """Create a project from uploaded files (hosted use) or from paths on this machine (local use)."""
    from ..profile import load_profile
    from ..project import slugify
    fmt = load_profile(profile, settings().profiles_dir).format
    staging = settings().projects_dir / ".uploads" / f"{slugify(name)}-{int(time.time())}"
    opts: dict[str, str] = {}
    src_path: Path | None = None
    try:
        if _has_file(source_file):
            src_path = await save_upload(source_file, staging)  # type: ignore[arg-type]
        elif source.strip():
            src_path = Path(source.strip()).expanduser()
        if _has_file(script_file):
            opts["script"] = str(await save_upload(script_file, staging))  # type: ignore[arg-type]
        elif script.strip():
            opts["script"] = str(Path(script.strip()).expanduser().resolve())
        if _has_file(transcript_file):
            opts["transcript"] = str(await save_upload(transcript_file, staging))  # type: ignore[arg-type]
        elif transcript.strip():
            opts["transcript"] = str(Path(transcript.strip()).expanduser().resolve())
        for av in avatar_files or []:
            if _has_file(av):
                await save_upload(av, staging)   # avatars sit next to the script, where it looks first
        if src_path is None and "script" not in opts:
            raise HTTPException(400, "upload a video (talking-head) or a script (chat-skit)")
        p = Project.create(settings().projects_dir, name, src_path, profile, fmt, copy_source=src_path is not None and _has_file(source_file), options=opts)
    except (FileExistsError, FileNotFoundError) as e:
        raise HTTPException(400, str(e)) from e
    if src_path is not None and _has_file(source_file):
        src_path.unlink(missing_ok=True)   # copied into the project's assets/
    if opts.get("script"):
        # keep script, avatars and transcript with the project
        dst = p.root / "assets" / "upload"
        if staging.exists():
            shutil.copytree(staging, dst, dirs_exist_ok=True)
            for k in ("script", "transcript"):
                if k in opts and Path(opts[k]).parent == staging:
                    opts[k] = str(dst / Path(opts[k]).name)
            p.cfg["options"] = {**p.options, **opts}
            import yaml
            (p.root / "project.yaml").write_text(yaml.safe_dump(p.cfg, sort_keys=False))
    elif opts.get("transcript") and Path(opts["transcript"]).parent == staging:
        dst = p.root / "assets" / Path(opts["transcript"]).name
        shutil.move(opts["transcript"], dst)
        p.cfg["options"] = {**p.options, "transcript": str(dst)}
        import yaml
        (p.root / "project.yaml").write_text(yaml.safe_dump(p.cfg, sort_keys=False))
    shutil.rmtree(staging, ignore_errors=True)
    return RedirectResponse(f"/p/{p.root.name}", status_code=303)


@app.get("/assets", response_class=HTMLResponse)
def assets_page(request: Request, msg: str = ""):
    from ..profile import load_profile
    libs = []
    for name in profiles():
        prof = load_profile(name, settings().profiles_dir)
        for kind, attr in ASSET_KINDS.items():
            d = prof.resolve_path(getattr(prof.audio, attr))
            files = sorted(f.name for f in d.iterdir() if f.is_file() and not f.name.startswith(".")) if d and d.exists() else []
            libs.append({"profile": name, "kind": kind, "dir": str(d) if d else "(not set)", "files": files})
        d = prof.resolve_path(prof.chat.assets_dir) if prof.format == "chat-skit" else None
        if d:
            files = sorted(f.name for f in d.iterdir() if f.is_file()) if d.exists() else []
            libs.append({"profile": name, "kind": "avatars", "dir": str(d), "files": files})
    return templates.TemplateResponse(request, "assets.html", {"libs": libs, "msg": msg, "worker": worker_alive(), "profiles": profiles()})


@app.post("/assets")
async def assets_upload(profile: str = Form(...), kind: str = Form(...), files: list[UploadFile] = File(...)):
    from ..profile import load_profile
    prof = load_profile(profile, settings().profiles_dir)
    if kind in ASSET_KINDS:
        d = prof.resolve_path(getattr(prof.audio, ASSET_KINDS[kind]))
    elif kind == "avatars":
        d = prof.resolve_path(prof.chat.assets_dir)
    else:
        raise HTTPException(400, "kind must be music, sfx or avatars")
    if d is None:
        raise HTTPException(400, f"profile {profile} has no {kind} folder configured")
    n = 0
    for up in files:
        if _has_file(up):
            await save_upload(up, d)
            n += 1
    return RedirectResponse(f"/assets?msg=uploaded+{n}+file(s)", status_code=303)


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
    if os.environ.get("AUTOEDIT_INPROCESS_WORKER"):
        start_worker_thread()
    else:
        from ..batch.worker import worker_main
        worker_main(daemon=True)
    return RedirectResponse("/jobs", status_code=303)


def serve(host: str = "127.0.0.1", port: int = 8765, with_worker: bool = False) -> int:
    import sys

    import uvicorn
    local = host in ("127.0.0.1", "localhost", "::1")
    if not local and not os.environ.get("AUTOEDIT_PASSWORD"):
        print("refusing to listen on a public address without AUTOEDIT_PASSWORD set "
              "(anyone could spend your API key and fill your disk)", file=sys.stderr)
        return 2
    settings().projects_dir.mkdir(parents=True, exist_ok=True)
    if with_worker:
        os.environ["AUTOEDIT_INPROCESS_WORKER"] = "1"
        start_worker_thread()
    print(f"autoedit UI: http://{host}:{port}  (projects in {settings().projects_dir}; "
          f"worker {'in-process' if with_worker else 'separate'}; auth {'on' if os.environ.get('AUTOEDIT_PASSWORD') else 'off'})")
    uvicorn.run(app, host=host, port=port, log_level="warning", proxy_headers=True, forwarded_allow_ips="*")
    return 0
