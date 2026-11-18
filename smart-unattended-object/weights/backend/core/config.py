"""
config.py

Every tunable in one place, overridable from the environment so a camera or a
whole deployment can be re-tuned without editing code.

Naming: every variable is ``UOD_<NAME>`` (Unattended Object Detection).
Read once at import; call :func:`settings.describe` to log what was resolved.

Nothing here reads the GPU or loads a model -- see ``app/core/runtime.py``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import Tuple


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(f"UOD_{name}")
    return default if value is None or value == "" else value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(f"UOD_{name}")
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "y"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env_str(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env_str(name, str(default)))
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Which classes matter
# ---------------------------------------------------------------------------
# People are context for ownership. Only the object classes below can ever
# become an unattended-object threat, so a stationary person or a parked
# vehicle can never raise an abandoned-object alert.
#
# Every name here must exist in the checkpoint's own class list or it is dead
# weight -- `class_ids_for` warns at startup about any that do not. These are the
# COCO names a left-behind item realistically lands on. There is no generic "bag"
# or "box" class in COCO: a tote, a carrier bag or a cardboard box is reported as
# whichever of these it most resembles, usually "handbag" or "suitcase", and
# often at low confidence. That is a limit of the checkpoint, not of the
# pipeline; a custom-trained model is the only real fix for those.

UNATTENDED_OBJECT_CLASSES: frozenset[str] = frozenset({
    "backpack",
    "handbag",
    "suitcase",
    "umbrella",
    "bottle",
    "vase",
})

PERSON_CLASSES: frozenset[str] = frozenset({"person"})

ALLOWED_CLASSES: frozenset[str] = UNATTENDED_OBJECT_CLASSES | PERSON_CLASSES


@dataclass(frozen=True)
class Settings:
    # ---- model / inference -------------------------------------------------
    model_name: str = field(default_factory=lambda: _env_str("MODEL", "yolo26m.pt"))
    inference_size: int = field(default_factory=lambda: _env_int("IMGSZ", 960))
    # Low bar so weak detections can still feed tracking continuity. It must sit
    # *below* `track_low_thresh`, or ByteTrack's second association pass -- the
    # one that recovers an existing track from a weak frame -- has an empty pool
    # to work with and the object flickers out on every hard frame.
    track_confidence: float = field(default_factory=lambda: _env_float("TRACK_CONF", 0.08))
    # Separate, stricter bar a detection must clear to confirm a real threat.
    # Kept well above the tracking floor but below what a COCO checkpoint scores
    # on a small bag on the floor (0.30-0.50). Set too high it becomes a second
    # invisible gate: the object tracks, draws, accumulates dwell, and then never
    # turns red, with nothing to indicate why. Raise it if bystander luggage
    # starts alerting.
    decision_confidence: float = field(default_factory=lambda: _env_float("DECISION_CONF", 0.40))
    nms_iou: float = field(default_factory=lambda: _env_float("NMS_IOU", 0.60))
    max_detections: int = field(default_factory=lambda: _env_int("MAX_DET", 100))

    # ---- device ------------------------------------------------------------
    # "auto" | "cuda" | "cuda:1" | "cpu"
    device: str = field(default_factory=lambda: _env_str("DEVICE", "auto"))
    allow_fp16: bool = field(default_factory=lambda: _env_bool("FP16", True))
    cpu_threads: int = field(default_factory=lambda: _env_int("CPU_THREADS", 0))  # 0 = leave alone

    # ---- SAHI (adaptive slicing) ------------------------------------------
    sahi_enabled: bool = field(default_factory=lambda: _env_bool("SAHI", True))
    sahi_slice: int = field(default_factory=lambda: _env_int("SAHI_SLICE", 640))
    sahi_overlap: float = field(default_factory=lambda: _env_float("SAHI_OVERLAP", 0.25))
    sahi_batch: int = field(default_factory=lambda: _env_int("SAHI_BATCH", 4))
    # Skip slicing entirely when the frame is not much bigger than one tile.
    sahi_min_scale: float = field(default_factory=lambda: _env_float("SAHI_MIN_SCALE", 1.6))
    # Merge duplicates across tiles on intersection-over-smaller, not IoU.
    sahi_merge_ios: float = field(default_factory=lambda: _env_float("SAHI_MERGE_IOS", 0.55))
    # A box hugging a tile edge that is not a frame edge is a cut-off object.
    sahi_edge_margin: int = field(default_factory=lambda: _env_int("SAHI_EDGE_MARGIN", 2))
    # Only tile regions that changed recently; full sweep every N cycles.
    sahi_motion_gate: bool = field(default_factory=lambda: _env_bool("SAHI_MOTION_GATE", True))
    sahi_full_sweep_every: int = field(default_factory=lambda: _env_int("SAHI_FULL_SWEEP", 30))

    # ---- pipeline pacing ---------------------------------------------------
    target_fps: float = field(default_factory=lambda: _env_float("TARGET_FPS", 12.0))
    # Run heavy detection every Nth processed frame; tracking coasts between.
    detect_every: int = field(default_factory=lambda: _env_int("DETECT_EVERY", 2))
    reconnect_delay: float = field(default_factory=lambda: _env_float("RECONNECT_DELAY", 2.0))
    jpeg_quality: int = field(default_factory=lambda: _env_int("JPEG_QUALITY", 80))
    # Longest edge of the streamed preview; 0 keeps the source resolution.
    stream_max_width: int = field(default_factory=lambda: _env_int("STREAM_MAX_WIDTH", 1280))

    # ---- tracking ----------------------------------------------------------
    # These four gates decide what is allowed to *become* an object at all, so
    # they are the most consequential numbers in the file. They sit at or below
    # the ultralytics defaults (0.25/0.1/0.25) on purpose: BoT-SORT silently
    # discards any detection below `new_track_thresh` instead of tracking it, and
    # a detection that never becomes a track never reaches the analyzer chain,
    # the API, or the screen. A bag set on the floor -- small, partly occluded,
    # seen from above -- routinely scores 0.30-0.50, so a high bar here does not
    # produce cautious tracking, it produces an invisible bag. Track liberally
    # and decide strictly: `decision_confidence` above is what gates the alert.
    track_with_reid: bool = field(default_factory=lambda: _env_bool("REID", True))
    # A .pt or .onnx encoder. Bare asset names such as "yolo26n-reid.onnx" are
    # fetched by ultralytics on first use; names matching a file in weights/ are
    # used directly, which keeps an offline machine working.
    reid_model: str = field(default_factory=lambda: _env_str("REID_MODEL", "yolo26n-reid.onnx"))
    # ReID costs a second forward pass per detection per frame, so it is skipped
    # on CPU unless explicitly forced.
    reid_force_cpu: bool = field(default_factory=lambda: _env_bool("REID_FORCE_CPU", False))
    reid_proximity_thresh: float = field(default_factory=lambda: _env_float("REID_PROXIMITY", 0.5))
    reid_appearance_thresh: float = field(default_factory=lambda: _env_float("REID_APPEARANCE", 0.8))
    # sparseOptFlow | orb | sift | ecc | none -- camera motion compensation.
    gmc_method: str = field(default_factory=lambda: _env_str("GMC", "sparseOptFlow"))
    track_buffer_seconds: float = field(default_factory=lambda: _env_float("TRACK_BUFFER_S", 3.0))
    track_high_thresh: float = field(default_factory=lambda: _env_float("TRACK_HIGH", 0.25))
    track_low_thresh: float = field(default_factory=lambda: _env_float("TRACK_LOW", 0.10))
    new_track_thresh: float = field(default_factory=lambda: _env_float("NEW_TRACK", 0.25))
    match_thresh: float = field(default_factory=lambda: _env_float("MATCH_THRESH", 0.80))

    # ---- box smoothing -----------------------------------------------------
    smooth_boxes: bool = field(default_factory=lambda: _env_bool("SMOOTH_BOXES", True))
    smooth_alpha: float = field(default_factory=lambda: _env_float("SMOOTH_ALPHA", 0.45))
    smooth_snap_iou: float = field(default_factory=lambda: _env_float("SMOOTH_SNAP_IOU", 0.20))

    # ---- ownership (scale-normalised) -------------------------------------
    # Distances are multiples of the person's own pixel height, so the same
    # numbers hold at any resolution and any depth in the scene.
    owner_assign_factor: float = field(default_factory=lambda: _env_float("OWNER_ASSIGN", 1.10))
    owner_release_factor: float = field(default_factory=lambda: _env_float("OWNER_RELEASE", 1.80))
    owner_grace_seconds: float = field(default_factory=lambda: _env_float("OWNER_GRACE", 3.0))
    owner_bind_frames: int = field(default_factory=lambda: _env_int("OWNER_BIND_FRAMES", 3))

    # ---- motion ------------------------------------------------------------
    # Fraction of the object's own diagonal that counts as real movement.
    motion_threshold_factor: float = field(default_factory=lambda: _env_float("MOTION_FACTOR", 0.35))
    motion_window_seconds: float = field(default_factory=lambda: _env_float("MOTION_WINDOW_S", 1.5))
    motion_release_factor: float = field(default_factory=lambda: _env_float("MOTION_RELEASE", 0.20))

    # ---- dwell / threat ----------------------------------------------------
    threat_seconds: float = field(default_factory=lambda: _env_float("THREAT_SECONDS", 30.0))
    # Brief re-attendance or jitter must not reset a long timer instantly.
    dwell_grace_seconds: float = field(default_factory=lambda: _env_float("DWELL_GRACE", 4.0))
    track_ttl_seconds: float = field(default_factory=lambda: _env_float("TRACK_TTL", 20.0))
    stabilizer_window: int = field(default_factory=lambda: _env_int("STAB_WINDOW", 15))

    # ---- logging -----------------------------------------------------------
    log_level: str = field(default_factory=lambda: _env_str("LOG_LEVEL", "INFO"))
    log_file: str = field(default_factory=lambda: _env_str("LOG_FILE", ""))
    log_summary_seconds: float = field(default_factory=lambda: _env_float("LOG_SUMMARY_S", 15.0))
    metrics_enabled: bool = field(default_factory=lambda: _env_bool("METRICS", True))

    @property
    def slice_wh(self) -> Tuple[int, int]:
        return (self.sahi_slice, self.sahi_slice)

    def describe(self) -> str:
        parts = [f"{f.name}={getattr(self, f.name)!r}" for f in fields(self)]
        return "settings: " + ", ".join(parts)


settings = Settings()
