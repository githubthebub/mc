"""Face detection and tracking.

A face track is computed once per project (on the proxy) and used by punch-ins,
emphasis zooms, Shorts crops, caption placement, thumbnails and QA. Boxes are in
source pixel coordinates. mediapipe's BlazeFace is the detector; the track is
smoothed with an EMA and a deadband so crops do not jitter.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MODEL_NAME = "blaze_face_short_range.tflite"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_detector/"
             "blaze_face_short_range/float16/latest/blaze_face_short_range.tflite")


class FaceModelUnavailable(RuntimeError):
    pass


def ensure_model(models_dir: Path) -> Path:
    """Return the detector model path, downloading it on first use."""
    models_dir = Path(models_dir).expanduser()
    models_dir.mkdir(parents=True, exist_ok=True)
    p = models_dir / MODEL_NAME
    if p.exists() and p.stat().st_size > 100_000:
        return p
    tmp = p.with_suffix(".part")
    try:
        if shutil.which("curl"):
            subprocess.run(["curl", "-sS", "-L", "-o", str(tmp), MODEL_URL], check=True, timeout=120)
        else:
            urllib.request.urlretrieve(MODEL_URL, tmp)
        if tmp.stat().st_size < 100_000:
            raise RuntimeError("downloaded file too small")
        tmp.replace(p)
    except Exception as e:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        raise FaceModelUnavailable(f"could not fetch {MODEL_URL}: {e}. Place the file at {p} manually.") from e
    return p


@dataclass
class FaceBox:
    t: float
    x: float
    y: float
    w: float
    h: float
    score: float = 1.0

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def as_int(self) -> tuple[int, int, int, int]:
        return int(round(self.x)), int(round(self.y)), int(round(self.w)), int(round(self.h))


@dataclass
class FaceTrack:
    width: int
    height: int
    sample_dt: float
    samples: list[FaceBox]
    detector: str = "mediapipe-blazeface"

    # ---- queries ----
    def box_at(self, t: float, max_gap: float = 1.0) -> FaceBox | None:
        """Interpolated box at t, bridging detection gaps up to max_gap seconds."""
        s = self.samples
        if not s:
            return None
        if t <= s[0].t:
            return s[0] if s[0].t - t <= max_gap else None
        if t >= s[-1].t:
            return s[-1] if t - s[-1].t <= max_gap else None
        lo, hi = 0, len(s) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if s[mid].t <= t:
                lo = mid
            else:
                hi = mid
        a, b = s[lo], s[hi]
        if b.t - a.t > max_gap:
            near = a if t - a.t <= b.t - t else b
            return near if abs(near.t - t) <= max_gap / 2 else None
        f = (t - a.t) / (b.t - a.t) if b.t > a.t else 0.0
        return FaceBox(t, a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f,
                       a.w + (b.w - a.w) * f, a.h + (b.h - a.h) * f, min(a.score, b.score))

    def mean_box(self, t0: float, t1: float) -> FaceBox | None:
        """Average box over a source range (what a static punch-in anchors to)."""
        inside = [b for b in self.samples if t0 <= b.t <= t1]
        if not inside:
            return self.box_at((t0 + t1) / 2)
        n = len(inside)
        return FaceBox((t0 + t1) / 2, sum(b.x for b in inside) / n, sum(b.y for b in inside) / n,
                       sum(b.w for b in inside) / n, sum(b.h for b in inside) / n,
                       sum(b.score for b in inside) / n)

    def present_fraction(self, duration: float) -> float:
        if duration <= 0 or not self.samples:
            return 0.0
        expected = max(1, int(duration / self.sample_dt))
        return min(1.0, len(self.samples) / expected)

    def median_box(self) -> FaceBox | None:
        if not self.samples:
            return None
        xs = sorted(b.x for b in self.samples)
        ys = sorted(b.y for b in self.samples)
        ws = sorted(b.w for b in self.samples)
        hs = sorted(b.h for b in self.samples)
        m = len(xs) // 2
        return FaceBox(0.0, xs[m], ys[m], ws[m], hs[m])

    # ---- io ----
    def to_json(self) -> dict[str, Any]:
        return {"width": self.width, "height": self.height, "sample_dt": self.sample_dt,
                "detector": self.detector, "count": len(self.samples),
                "samples": [asdict(b) for b in self.samples]}

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "FaceTrack":
        return cls(d["width"], d["height"], d["sample_dt"], [FaceBox(**b) for b in d["samples"]],
                   d.get("detector", "mediapipe-blazeface"))

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_json()))

    @classmethod
    def load(cls, path: Path) -> "FaceTrack":
        return cls.from_json(json.loads(path.read_text()))


def smooth_track(samples: list[FaceBox], alpha: float = 0.2, deadband: float = 0.04,
                 max_gap: float = 1.0) -> list[FaceBox]:
    """EMA on center and size with a deadband (fraction of the box size).

    The EMA is reset after a gap longer than max_gap so the track can jump to a
    new position after the face was lost rather than sliding across the frame.
    """
    out: list[FaceBox] = []
    cx = cy = w = h = None
    last_t = None
    for b in samples:
        if cx is None or (last_t is not None and b.t - last_t > max_gap):
            cx, cy, w, h = b.cx, b.cy, b.w, b.h
        else:
            tol = deadband * max(w, h)
            if abs(b.cx - cx) > tol:
                cx += alpha * (b.cx - cx)
            if abs(b.cy - cy) > tol:
                cy += alpha * (b.cy - cy)
            w += alpha * (b.w - w)
            h += alpha * (b.h - h)
        last_t = b.t
        out.append(FaceBox(b.t, cx - w / 2, cy - h / 2, w, h, b.score))
    return out


def detect_faces(video: Path, model_path: Path, *, src_width: int, src_height: int,
                 sample_fps: float = 10.0, min_confidence: float = 0.5,
                 on_progress=None) -> tuple[list[FaceBox], float]:
    """Run BlazeFace on sampled frames of a (proxy) video. Returns (boxes in source pixels, sample_dt)."""
    import cv2
    import mediapipe as mp
    import numpy as np
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python import vision

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    pw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or src_width)
    ph = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or src_height)
    step = max(1, int(round(fps / sample_fps)))
    sx, sy = src_width / pw, src_height / ph
    opts = vision.FaceDetectorOptions(base_options=BaseOptions(model_asset_path=str(model_path)),
                                      min_detection_confidence=min_confidence)
    det = vision.FaceDetector.create_from_options(opts)
    boxes: list[FaceBox] = []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % step == 0:
            rgb = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            res = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
            if res.detections:
                d = max(res.detections, key=lambda d: d.bounding_box.width * d.bounding_box.height)
                bb = d.bounding_box
                boxes.append(FaceBox(round(i / fps, 3), bb.origin_x * sx, bb.origin_y * sy,
                                     bb.width * sx, bb.height * sy, float(d.categories[0].score)))
            if on_progress and n_frames:
                on_progress(i / n_frames)
        i += 1
    cap.release()
    det.close()
    return boxes, step / fps


def build_track(video: Path, model_path: Path, *, src_width: int, src_height: int,
                sample_fps: float = 10.0, min_confidence: float = 0.5, on_progress=None) -> FaceTrack:
    raw, dt = detect_faces(video, model_path, src_width=src_width, src_height=src_height,
                           sample_fps=sample_fps, min_confidence=min_confidence, on_progress=on_progress)
    return FaceTrack(src_width, src_height, dt, smooth_track(raw))


def crop_for_zoom(face: FaceBox | None, width: int, height: int, scale: float,
                  fallback: str = "top") -> tuple[int, int, int, int]:
    """Crop window (x, y, w, h) in source pixels for a punch-in of `scale`.

    The face center keeps the same screen position after the zoom (so the eye does
    not jump across the cut), clamped to the frame. Without a face: `fallback`
    'top' anchors at 30% height, 'center' at the middle.
    """
    cw, ch = int(width / scale) // 2 * 2, int(height / scale) // 2 * 2
    if face is not None:
        # screen position of the face center as a fraction of the frame
        fx, fy = face.cx / width, face.cy / height
        x = face.cx - fx * cw
        y = face.cy - fy * ch
        # the face must stay fully inside the crop with a margin; eye-trace yields to that
        mx, my = face.w * 0.15, face.h * 0.15
        x = min(x, face.x - mx)
        x = max(x, face.x + face.w + mx - cw)
        y = min(y, face.y - my)
        y = max(y, face.y + face.h + my - ch)
    else:
        x = (width - cw) / 2
        y = (height - ch) * (0.3 if fallback == "top" else 0.5)
    x = int(min(max(0, x), width - cw)) // 2 * 2
    y = int(min(max(0, y), height - ch)) // 2 * 2
    return x, y, cw, ch
