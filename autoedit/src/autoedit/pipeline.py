"""Run stages in order with skip-if-current logic, and the plan/approve gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import Settings
from .profile import Profile, load_profile
from .project import STAGES, Project


class NotApproved(RuntimeError):
    pass


def profile_for(project: Project, settings: Settings) -> Profile:
    return load_profile(project.profile_name, settings.profiles_dir)


def run_stage(project: Project, stage: str, settings: Settings, *, force: bool = False, yolo: bool = False,
              llm: str = "auto", quiet: bool = False) -> Any:
    """Run one stage (always re-runs when force)."""
    prof = profile_for(project, settings)
    log = project.log(stage, quiet=quiet)
    if stage == "ingest":
        from .stages import ingest
        return ingest.run(project, settings, log)
    if stage == "transcribe":
        from .stages import transcribe
        return transcribe.run(project, settings, log)
    if stage == "analyze":
        from .stages import analyze
        return analyze.run(project, settings, prof, log)
    if stage == "plan":
        from .stages import plan
        return plan.run(project, settings, prof, log, llm=llm)
    if stage == "render":
        if not (project.approved or yolo):
            raise NotApproved("EDL not approved: review 04_plan/plan_summary.md and preview.mp4, then "
                              "`autoedit approve <project>` (or use --yolo)")
        from .stages import render
        return render.run(project, settings, prof, log)
    if stage == "verify":
        from .stages import verify
        return verify.run(project, settings, prof, log)
    if stage == "package":
        from .stages import package
        return package.run(project, settings, prof, log)
    raise ValueError(stage)


def run_pipeline(project: Project, settings: Settings, *, upto: str = "package", force: bool = False,
                 yolo: bool = False, llm: str = "auto", quiet: bool = False) -> dict[str, Any]:
    """Run every stage up to `upto`, skipping stages already done unless force. Stops at the
    review gate after plan when not approved and not yolo."""
    results: dict[str, Any] = {}
    for stage in STAGES:
        if STAGES.index(stage) > STAGES.index(upto):
            break
        if project.is_done(stage) and not force and stage != "verify" and stage != "package":
            results[stage] = "skipped (done)"
            continue
        if stage == "render" and not (project.approved or yolo):
            results[stage] = "waiting for approval"
            break
        results[stage] = run_stage(project, stage, settings, force=force, yolo=yolo, llm=llm, quiet=quiet)
        if stage == "plan" and not yolo and not project.approved:
            results["review"] = "plan written; approve to continue"
            break
    return results
