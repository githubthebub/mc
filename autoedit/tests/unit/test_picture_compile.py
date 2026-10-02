from fractions import Fraction

from autoedit.edl.schema import EDL, Anchor, Beat, Card, Meta, MontageSpec, Segment, Zoom
from autoedit.edl.transcript import Transcript, Word
from autoedit.media.probe import MediaInfo
from autoedit.profile import load_profile
from autoedit.render.picture import compile_pieces, montage_chunks


def _info():
    from pathlib import Path
    return MediaInfo(Path("x.mp4"), 60.0, 1920, 1080, Fraction(30, 1), True, 48000, None, "h264", "yuv420p")


def _tr():
    ws = [Word(id=i, text=f"w{i}", t0=1 + i * 0.5, t1=1.4 + i * 0.5) for i in range(40)]
    tr = Transcript(words=ws)
    tr.sentences = Transcript.group_sentences(ws)
    return tr


def test_montage_chunks_cover_the_range_evenly():
    seg = Segment(id="m", kind="montage", src_in=100.0, src_out=400.0, montage=MontageSpec(target_s=10, chunk_s=1.0, speed=2.0))
    chunks = montage_chunks(seg)
    assert len(chunks) == 10
    assert chunks[0][0] == 100.0 and abs(chunks[-1][1] - 400.0) < 0.01
    assert all(abs((b - a) - 2.0) < 0.01 for a, b in chunks)       # 2 s of source per 1 s chunk at 2x
    gaps = [chunks[i + 1][0] - chunks[i][0] for i in range(len(chunks) - 1)]
    assert max(gaps) - min(gaps) < 0.05                              # evenly spaced: every stage of progress shows


def test_compile_splits_at_zooms_beats_and_cards_and_keeps_frame_counts():
    meta = Meta(project="p", profile="personal", format="talking-head", source="x", duration=60, fps="30/1", width=1920, height=1080)
    edl = EDL(meta=meta, segments=[Segment(id="s1", src_in=0.0, src_out=10.0), Segment(id="s2", src_in=12.0, src_out=20.0),
                                   Segment(id="m1", kind="montage", src_in=20.0, src_out=50.0, montage=MontageSpec(target_s=6, speed=1.5))],
              zooms=[Zoom(id="z", at=Anchor(word=4), end=Anchor(word=6, edge="end"), scale=1.3)],
              beats=[Beat(id="b", after=Anchor(word=10, edge="end"), dur=1.5)],
              cards=[Card(id="k", before_segment="s2", text="Part 2", dur=2.0)])
    tr = _tr()
    c = compile_pieces(edl, tr, _info(), None, load_profile("personal"))
    ids = [p.id for p in c.pieces]
    assert ids[:3] == ["s1#0", "s1#1", "s1#2"]        # split before the zoom, the zoom, after the zoom
    zoom_piece = next(p for p in c.pieces if p.zoom == "z")
    assert zoom_piece.crop is not None and zoom_piece.src_in == 3.0 and abs(zoom_piece.src_out - 4.4) < 1e-6
    held = next(p for p in c.pieces if p.hold > 0)
    assert held.hold_frames == 45 and abs(held.src_out - 6.4) < 1e-6
    assert "card:k" in ids and ids.index("card:k") < ids.index("s2#0")
    montage = [p for p in c.pieces if p.kind == "montage"]
    assert len(montage) == 6 and all(p.rate == 1.5 for p in montage)
    # the timing map is exact: output frames = sum of piece frames, and the hold has its own span
    assert c.timing.total_frames == sum(p.frames + p.hold_frames for p in c.pieces)
    assert any(s.kind == "hold" and s.id == f"{held.id}:hold" for s in c.timing.spans)
    assert any(e["type"] == "hold" and e["ref"] == "b" for e in c.events)
    assert any(e["type"] == "sfx" and e["ref"] == "k" for e in c.events)   # the card's shutter
