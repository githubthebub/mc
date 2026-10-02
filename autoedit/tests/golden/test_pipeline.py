"""Golden test: the whole pipeline on the synthetic sample with replayed planner responses, offline.
Asserts the QA report passes, every technique has a status, and the outputs are consistent."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from autoedit.config import Settings
from autoedit.edl.schema import EDL
from autoedit.edl.techniques import TECHNIQUES
from autoedit.media.probe import probe
from autoedit.pipeline import run_pipeline
from autoedit.project import Project
from tests.fixtures.make_sample import build

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture(scope="module")
def sample(tmp_path_factory) -> tuple[Path, Path]:
    d = tmp_path_factory.mktemp("sample")
    return build(d, 48.0, (640, 360))


@pytest.fixture(scope="module")
def project(sample, tmp_path_factory) -> tuple[Project, Settings]:
    mp4, tr = sample
    root = tmp_path_factory.mktemp("projects")
    models = Path("~/.cache/autoedit/models").expanduser()
    settings = Settings(projects_dir=root, models_dir=models)
    settings.render.workers = 2
    p = Project.create(root, "Golden Sample", mp4, "personal", "talking-head", options={"transcript": str(tr)})
    llm_dir = p.dir("plan") / "llm"
    llm_dir.mkdir(parents=True, exist_ok=True)
    for f in (FIXTURES / "sample" / "llm").glob("*.json"):
        shutil.copy(f, llm_dir / f.name)
    return p, settings


def test_pipeline_end_to_end(project):
    p, settings = project
    res = run_pipeline(p, settings, yolo=True, llm="replay", quiet=True)
    assert all(p.is_done(s) for s in ("ingest", "transcribe", "analyze", "plan", "render", "shorts", "package", "verify")), p.summary()

    # plan artifacts
    assert (p.dir("plan") / "plan_summary.md").exists()
    assert (p.dir("plan") / "preview.mp4").exists()
    edl = EDL.load(p.edl_json)
    assert edl.meta.created_by == "llm"
    assert edl.segments[0].src_in > 25.0, "the hook (S9) must have been moved to the front"
    assert any(c.text.startswith("Fix 1") for c in edl.cards)
    assert len(edl.voiceover_slots) == 1 and len(edl.music) == 3

    # render artifacts and timing map consistency
    final = p.final_mp4
    assert final.exists()
    tm = json.loads((p.dir("render") / "timing_map.json").read_text())
    info = probe(final)
    assert abs(info.duration - tm["out_duration"]) < 0.1
    kept_src = sum(sp["src_out"] - sp["src_in"] for sp in tm["spans"] if sp["src_in"] is not None)
    inserted = sum(sp["out_dur"] for sp in tm["spans"] if sp["src_in"] is None)
    assert kept_src < 48.0 - 8.0, "dead air and the cut sentence must remove source time"
    assert abs(tm["out_duration"] - (kept_src + inserted)) < 0.05, "output = kept source + cards and beats, exactly"
    assert inserted >= 2 * 2.5 + 1.2 + 2.0 - 0.1, "two cards and two beats are inserted"
    stems = p.dir("render") / "stems"
    assert all((stems / f"{n}.wav").exists() for n in ("voice", "music", "music_raw", "sfx"))

    # QA
    qa = json.loads(p.qa_json.read_text())
    long = qa["outputs"]["long"]
    statuses = {c["id"]: c["status"] for c in long["checks"]}
    for cid in ("dead_air", "loudness", "true_peak", "music_automation", "text_safe_zones", "faces_not_cropped", "hook"):
        assert statuses[cid] == "pass", (cid, next(c for c in long["checks"] if c["id"] == cid))
    assert qa["overall"] in ("pass", "warn")
    assert long["checks"] and all(c["frames"] for c in long["checks"] if c["id"] in ("hook", "text_safe_zones"))

    # the ledger covers every technique and is honest about placeholders and missing assets
    rendered = EDL.load(p.dir("render") / "edl.rendered.json")
    assert set(rendered.techniques) == set(TECHNIQUES)
    not_exec = {n["id"]: n for n in long["not_executed"]}
    assert "licensed_audio" in not_exec and "placeholder" in not_exec["licensed_audio"]["reason"]
    assert "broll_every_noun" in not_exec
    assert "voiceover_mixed" in not_exec            # the line was written but not recorded
    assert rendered.techniques["music_dropouts"].status == "executed"
    assert rendered.techniques["hook_proof_early"].status == "executed"

    # shorts: two vertical outputs, face-tracked, word captions, loop ending, all QA checks pass
    idx = json.loads((p.dir("render") / "shorts" / "index.json").read_text())
    assert idx["count"] == 2, idx
    for sh in idx["shorts"]:
        si = probe(Path(sh["file"]))
        assert (si.width, si.height) == (1080, 1920)
        assert 14.0 <= si.duration <= 61.0
        rep = qa["outputs"][sh["id"]]
        st = {c["id"]: c["status"] for c in rep["checks"]}
        for cid in ("dead_air", "loudness", "true_peak", "text_safe_zones", "faces_not_cropped", "hook", "loop_ending"):
            assert st[cid] == "pass", (sh["id"], cid, next(c for c in rep["checks"] if c["id"] == cid))
        sr = json.loads((p.dir("render") / "shorts" / sh["id"] / "resolved.json").read_text())
        assert any(r["mode"] == "face-tracked" for r in sr["crop_paths"])
        assert len(sr["word_captions"]) >= 5
    assert idx["shorts"][0]["hook_sentence"] == idx["shorts"][0]["from_sentence"], "a short starts on its strongest line"

    # package
    meta = json.loads((p.dir("package") / "metadata.json").read_text())
    assert len(meta["shorts"]) == 2 and all(Path(s["file"]).exists() for s in meta["shorts"])
    assert Path(meta["file"]).exists() and meta["title"] == "The one mistake killing your videos"
    assert Path(meta["thumbnail"]["file"]).exists() and not meta["thumbnail"]["overlaps_face"]
    assert len(meta["chapters"]) >= 3 and meta["chapters"][0]["out"] == 0.0


def test_hand_edited_edl_is_flagged(project):
    p, settings = project
    edl = EDL.load(p.edl_json)
    edl.notes.append("hand edit")
    edl.save(p.edl_json)
    assert p.edl_was_hand_edited()
