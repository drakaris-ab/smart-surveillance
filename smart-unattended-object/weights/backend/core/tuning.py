"""
tuning.py

Runtime-adjustable detection parameters.

**Why this exists.**  Every threshold in ``config.py`` is read once at import, so
tuning detection meant editing a file, restarting the worker, waiting for the
model to load, restarting the cameras, and losing every track and dwell timer in
the process. Finding a workable confidence floor that way takes an afternoon.
The parameters that decide whether a bag is seen at all are exactly the ones that
need to be tried against a live scene, so they are exposed here and changeable
while the cameras run.

**How a change lands.**  Two mechanisms, because the code reads settings in two
ways. Most values -- everything in the slicing path, the pipeline pacing, the
decision confidence -- are read from ``settings`` at the moment they are used, so
writing the new value is enough. The rest were captured into an object when it
was constructed: the detector's inference size, the tracker's thresholds, the
analyzers' factors. For those, :data:`revision` is bumped and each camera
re-applies the captured values on its next frame, which is why every parameter
here takes effect within a frame or two and none of them require a restart.

Nothing here rebuilds the model or the tracker. Rebuilding the tracker would
discard every track id, which resets every dwell timer -- so a tweak intended to
improve detection would itself destroy the evidence being accumulated. The two
parameters that genuinely cannot be changed in place (the model file and the ReID
encoder) are marked ``restart_required`` and reported as such rather than being
quietly ignored.

**Not a settings store.**  Changes live in memory only. A restart returns to the
environment-and-default values, deliberately: an operator experimenting with
thresholds at 3am should not permanently reconfigure the deployment, and the
values that are meant to persist belong in the ``UOD_*`` environment where they
are visible to whoever deploys the thing.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from backend.core.config import Settings, settings
from backend.core.logging import get_logger

log = get_logger("tuning")

# Bumped on every accepted change. Cameras compare it against the revision they
# last applied; an int comparison per frame is free, which matters because this
# is on the hot path.
revision = 0

_lock = threading.Lock()
_defaults = Settings()
_dirty: Dict[str, Any] = {}


@dataclass(frozen=True)
class Param:
    """One adjustable value, with everything a UI needs to render a control.

    The bounds are not cosmetic. ``minimum``/``maximum`` are the range within
    which the value is meaningful rather than the range the type allows, so a
    slider cannot be dragged somewhere that silently breaks detection -- setting
    a confidence floor to 0.99, say, which produces exactly the "nothing is
    detected" symptom this panel exists to diagnose.
    """

    name: str
    group: str
    label: str
    help: str
    kind: str = "float"          # float | int | bool | str
    minimum: float = 0.0
    maximum: float = 1.0
    step: float = 0.01
    restart_required: bool = False

    def as_dict(self) -> Dict[str, Any]:
        current = getattr(settings, self.name)
        return {
            "name": self.name,
            "env": f"UOD_{_ENV_NAMES.get(self.name, self.name.upper())}",
            "group": self.group,
            "label": self.label,
            "help": self.help,
            "kind": self.kind,
            "value": current,
            "default": getattr(_defaults, self.name),
            "min": self.minimum,
            "max": self.maximum,
            "step": self.step,
            "restart_required": self.restart_required,
            "modified": current != getattr(_defaults, self.name),
        }

    def coerce(self, raw: Any) -> Any:
        """Validate and clamp, raising ValueError on anything unusable."""
        if self.kind == "str":
            text = str(raw).strip()
            if not text:
                raise ValueError(f"{self.name} cannot be empty")
            return text
        if self.kind == "bool":
            if isinstance(raw, bool):
                return raw
            if isinstance(raw, str):
                return raw.strip().lower() in {"1", "true", "yes", "on", "y"}
            return bool(raw)
        try:
            number = float(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{self.name} must be a number, got {raw!r}")
        if number != number:  # NaN
            raise ValueError(f"{self.name} must be a number, got NaN")
        # Clamp rather than reject: a slider that reports 0.9000000000000001 is
        # not an error, and refusing the whole request over it would make the
        # panel feel broken.
        number = max(self.minimum, min(self.maximum, number))
        return int(round(number)) if self.kind == "int" else round(number, 4)


# Field name -> the UOD_* suffix it is actually read from. They differ often
# enough that guessing is wrong, and the panel shows the env name so a value
# found by experiment can be made permanent in the deployment.
_ENV_NAMES: Dict[str, str] = {
    "model_name": "MODEL",
    "inference_size": "IMGSZ",
    "track_confidence": "TRACK_CONF",
    "decision_confidence": "DECISION_CONF",
    "max_detections": "MAX_DET",
    "sahi_enabled": "SAHI",
    "sahi_full_sweep_every": "SAHI_FULL_SWEEP",
    "track_with_reid": "REID",
    "reid_proximity_thresh": "REID_PROXIMITY",
    "reid_appearance_thresh": "REID_APPEARANCE",
    "track_buffer_seconds": "TRACK_BUFFER_S",
    "track_high_thresh": "TRACK_HIGH",
    "track_low_thresh": "TRACK_LOW",
    "new_track_thresh": "NEW_TRACK",
    "owner_assign_factor": "OWNER_ASSIGN",
    "owner_release_factor": "OWNER_RELEASE",
    "owner_grace_seconds": "OWNER_GRACE",
    "motion_threshold_factor": "MOTION_FACTOR",
    "motion_window_seconds": "MOTION_WINDOW_S",
    "motion_release_factor": "MOTION_RELEASE",
    "dwell_grace_seconds": "DWELL_GRACE",
    "track_ttl_seconds": "TRACK_TTL",
    "stabilizer_window": "STAB_WINDOW",
}

_DETECTION = "Detection"
_SLICING = "Slicing (small objects)"
_TRACKING = "Tracking"
_DECISION = "Threat decision"
_OWNERSHIP = "Ownership"
_MOTION = "Motion"
_STABILITY = "Stability"
_PIPELINE = "Pipeline"

# Ordered: the panel renders groups in the order they first appear, and this
# order is the order to try things in when a bag is not being detected --
# inference size and the tracking floor first, cosmetics last.
PARAMS: Tuple[Param, ...] = (
    # ---- detection --------------------------------------------------------
    Param(
        "inference_size", _DETECTION, "Inference size",
        "Longest edge the frame is resized to before the model sees it. The "
        "single most effective control for small objects: a bag 30px wide in a "
        "1080p frame is 17px at 640 and 27px at 1024. Must be a multiple of 32. "
        "Cost grows with the square, so 1280 is ~1.8x the work of 960.",
        kind="int", minimum=320, maximum=1536, step=32,
    ),
    Param(
        "track_confidence", _DETECTION, "Detector floor",
        "Confidence below which the model's output is discarded outright. Keep "
        "it below the tracking low threshold, or the association pass that "
        "recovers a track from a weak frame has nothing to work with.",
        minimum=0.01, maximum=0.60, step=0.01,
    ),
    Param(
        "nms_iou", _DETECTION, "NMS IoU",
        "Overlap at which two boxes of the same class are treated as one "
        "detection. Lower is more aggressive suppression; raise it if a bag "
        "held against a person is being merged away.",
        minimum=0.10, maximum=0.95, step=0.05,
    ),
    Param(
        "max_detections", _DETECTION, "Max detections",
        "Ceiling on boxes kept per image. Only bites in a crowd; raising it "
        "costs almost nothing.",
        kind="int", minimum=10, maximum=300, step=10,
    ),
    Param(
        "model_name", _DETECTION, "Model file",
        "Checkpoint in weights/. Changing it needs a restart: swapping weights "
        "in place would leave half the cameras running the old model.",
        kind="str", restart_required=True,
    ),

    # ---- slicing ----------------------------------------------------------
    Param(
        "sahi_enabled", _SLICING, "Slice large frames",
        "Run the model again on overlapping tiles at their native resolution, "
        "so a distant bag is inferred at full size instead of being shrunk with "
        "the whole frame. This is what makes small objects detectable at all on "
        "a wide shot. Turn it off to measure what it is costing you.",
        kind="bool",
    ),
    Param(
        "sahi_slice", _SLICING, "Tile size",
        "Edge length of each tile in source pixels. Smaller tiles magnify more "
        "but produce more of them, and an object larger than one tile gets cut "
        "across two and has to be merged back.",
        kind="int", minimum=256, maximum=1280, step=64,
    ),
    Param(
        "sahi_overlap", _SLICING, "Tile overlap",
        "Fraction each tile overlaps its neighbour. Overlap is what stops an "
        "object landing exactly on a seam from being missed by both tiles.",
        minimum=0.0, maximum=0.60, step=0.05,
    ),
    Param(
        "sahi_min_scale", _SLICING, "Minimum frame/tile ratio",
        "Skip slicing when the frame is less than this many times the tile "
        "size -- at that point the full-frame pass already sees the object at "
        "roughly native scale and tiling is pure cost.",
        minimum=1.0, maximum=4.0, step=0.1,
    ),
    Param(
        "sahi_merge_ios", _SLICING, "Merge threshold",
        "Two boxes from different tiles are the same object when the smaller is "
        "this far inside the larger (intersection-over-smaller, not IoU -- a "
        "half-object from one tile and the whole object from another have low "
        "IoU and would both survive, which is what produced doubled boxes).",
        minimum=0.20, maximum=0.95, step=0.05,
    ),
    Param(
        "sahi_edge_margin", _SLICING, "Edge margin (px)",
        "A box within this many pixels of a tile edge that is not a frame edge "
        "is a cut-off object and is dropped, because the same object is seen "
        "whole by the overlapping tile.",
        kind="int", minimum=0, maximum=16, step=1,
    ),
    Param(
        "sahi_motion_gate", _SLICING, "Only slice where something changed",
        "Infer a tile only when its pixels changed, plus any tile holding a "
        "tracked object. This is the difference between slicing costing a few "
        "tiles per frame and costing all of them.",
        kind="bool",
    ),
    Param(
        "sahi_full_sweep_every", _SLICING, "Full sweep every N cycles",
        "How often every tile is inferred regardless of motion, so an object "
        "that appeared during a gap in the gate is picked up. Lower is safer "
        "and more expensive.",
        kind="int", minimum=1, maximum=120, step=1,
    ),
    Param(
        "sahi_batch", _SLICING, "Tiles per batch",
        "Tiles sent to the GPU in one call. Higher keeps the device busier at "
        "the cost of VRAM; on CPU it makes little difference.",
        kind="int", minimum=1, maximum=16, step=1,
    ),

    # ---- tracking ---------------------------------------------------------
    Param(
        "new_track_thresh", _TRACKING, "New track threshold",
        "Confidence a detection must reach to become a tracked object. This is "
        "the gate that makes an object invisible everywhere at once: below it "
        "the tracker starts no track, so there is no id, no ownership, no dwell "
        "timer and no box on screen -- indistinguishable from the model not "
        "seeing it. Lower this first when something is detected but never "
        "appears.",
        minimum=0.05, maximum=0.90, step=0.01,
    ),
    Param(
        "track_high_thresh", _TRACKING, "High association threshold",
        "Detections at or above this join the first association pass. Below it "
        "they can only re-attach to a track that already exists.",
        minimum=0.05, maximum=0.90, step=0.01,
    ),
    Param(
        "track_low_thresh", _TRACKING, "Low association threshold",
        "Floor for the recovery pass. Weak detections between this and the high "
        "threshold keep an existing track alive through a hard frame instead of "
        "letting it lapse.",
        minimum=0.01, maximum=0.60, step=0.01,
    ),
    Param(
        "match_thresh", _TRACKING, "Match distance",
        "How far a box may be from a track's prediction and still be considered "
        "the same object. Raise it for fast movement, lower it when two nearby "
        "objects swap ids.",
        minimum=0.30, maximum=0.99, step=0.01,
    ),
    Param(
        "track_buffer_seconds", _TRACKING, "Keep lost tracks (s)",
        "How long a track survives without being seen before its id is retired. "
        "Longer means a bag behind a passing crowd keeps its identity -- and its "
        "accumulated dwell time -- instead of restarting as a new object.",
        minimum=0.5, maximum=15.0, step=0.5,
    ),
    Param(
        "reid_proximity_thresh", _TRACKING, "ReID proximity gate",
        "Appearance matching is only attempted for candidates within this "
        "spatial distance, which stops a similar-looking object across the room "
        "from stealing an id.",
        minimum=0.1, maximum=0.95, step=0.05,
    ),
    Param(
        "reid_appearance_thresh", _TRACKING, "ReID appearance gate",
        "How similar two crops must look to be judged the same object. Higher "
        "is stricter.",
        minimum=0.1, maximum=0.99, step=0.05,
    ),
    Param(
        "track_with_reid", _TRACKING, "Appearance re-identification",
        "Match objects by appearance as well as position. Needs a restart: the "
        "encoder is loaded when the tracker is built, and rebuilding the tracker "
        "would discard every track id and reset every dwell timer.",
        kind="bool", restart_required=True,
    ),

    # ---- threat decision --------------------------------------------------
    Param(
        "decision_confidence", _DECISION, "Decision confidence",
        "Confidence an object must hold to be confirmed as a threat, separate "
        "from and above the tracking floor. Set too high it becomes a second "
        "silent gate: the object tracks, draws, fills its dwell bar and then "
        "never turns red. Raise it if bystander luggage starts alerting.",
        minimum=0.05, maximum=0.95, step=0.01,
    ),
    Param(
        "threat_seconds", _DECISION, "Unattended for (s)",
        "How long an ownerless, stationary object must sit before it is a "
        "threat. Applies to cameras started after the change.",
        minimum=3.0, maximum=600.0, step=1.0,
    ),
    Param(
        "dwell_grace_seconds", _DECISION, "Dwell grace (s)",
        "A gap shorter than this -- a missed frame, someone walking past, the "
        "owner briefly returning -- is credited to the timer instead of resetting "
        "it. Without it a busy scene never accumulates a full interval.",
        minimum=0.0, maximum=30.0, step=0.5,
    ),
    Param(
        "track_ttl_seconds", _DECISION, "Forget object after (s)",
        "How long an object's accumulated state is kept after it stops being "
        "seen at all. Longer survives a genuine occlusion; shorter frees ids.",
        minimum=2.0, maximum=120.0, step=1.0,
    ),

    # ---- ownership --------------------------------------------------------
    Param(
        "owner_assign_factor", _OWNERSHIP, "Bind within (person heights)",
        "How close a person must be to an object to be considered its owner, "
        "measured in multiples of that person's own pixel height so the number "
        "holds at any distance from the camera and any resolution.",
        minimum=0.2, maximum=4.0, step=0.05,
    ),
    Param(
        "owner_release_factor", _OWNERSHIP, "Release beyond (person heights)",
        "How far the owner must get before the object counts as abandoned. Kept "
        "well above the bind distance on purpose: a single gap between the two "
        "would make ownership flicker on and off while someone stands beside "
        "their bag.",
        minimum=0.3, maximum=6.0, step=0.05,
    ),
    Param(
        "owner_grace_seconds", _OWNERSHIP, "Owner grace (s)",
        "How long a departed or occluded owner still counts as present. This is "
        "what separates stepping out of frame for a moment from leaving.",
        minimum=0.0, maximum=60.0, step=0.5,
    ),
    Param(
        "owner_bind_frames", _OWNERSHIP, "Frames to confirm owner",
        "Consecutive frames a person must be nearest before the binding is "
        "made, so a passer-by does not adopt someone else's bag.",
        kind="int", minimum=1, maximum=30, step=1,
    ),

    # ---- motion -----------------------------------------------------------
    Param(
        "motion_threshold_factor", _MOTION, "Movement threshold",
        "Fraction of the object's own diagonal it must travel to count as "
        "moving. Relative to the object, so a small bag and a large suitcase "
        "are judged by the same standard. Too low and box jitter reads as "
        "movement, which pauses the dwell timer forever.",
        minimum=0.05, maximum=2.0, step=0.05,
    ),
    Param(
        "motion_release_factor", _MOTION, "Settle threshold",
        "The lower bar an object must fall under to be called stationary again. "
        "Below the movement threshold deliberately, so a bag sitting still with "
        "a wobbling box does not oscillate between moving and settled.",
        minimum=0.01, maximum=1.0, step=0.01,
    ),
    Param(
        "motion_window_seconds", _MOTION, "Motion window (s)",
        "Span of history the movement measurement looks over. Longer is steadier "
        "but slower to notice that something has been picked up.",
        minimum=0.2, maximum=10.0, step=0.1,
    ),

    # ---- stability --------------------------------------------------------
    Param(
        "stabilizer_window", _STABILITY, "Label vote window",
        "Frames voted over to settle an object's class. A bag flickering between "
        "handbag and suitcase is one object, and without this it alternates "
        "labels every frame.",
        kind="int", minimum=1, maximum=60, step=1,
    ),
    Param(
        "smooth_boxes", _STABILITY, "Smooth boxes",
        "Average each box towards its previous position so a stationary object "
        "stops shimmering. Off shows the raw detector output.",
        kind="bool",
    ),
    Param(
        "smooth_alpha", _STABILITY, "Smoothing strength",
        "How much of the new box is taken each frame. Lower is smoother and lags "
        "more behind real movement.",
        minimum=0.05, maximum=1.0, step=0.05,
    ),
    Param(
        "smooth_snap_iou", _STABILITY, "Snap threshold",
        "When a new box overlaps the smoothed one by less than this, smoothing "
        "is abandoned and the box jumps. Without it a genuine fast move is "
        "dragged behind the object for several frames.",
        minimum=0.0, maximum=0.9, step=0.05,
    ),

    # ---- pipeline ---------------------------------------------------------
    Param(
        "target_fps", _PIPELINE, "Target FPS",
        "Frames per second each camera aims to analyse. The real limit is how "
        "fast inference returns; lowering this frees GPU for other cameras. "
        "Cameras already running keep their measured rate.",
        minimum=1.0, maximum=60.0, step=1.0,
    ),
    Param(
        "jpeg_quality", _PIPELINE, "Preview quality",
        "JPEG quality of the streamed preview. Affects bandwidth and encode "
        "cost only -- detection always runs on the original frame.",
        kind="int", minimum=30, maximum=95, step=5,
    ),
    Param(
        "stream_max_width", _PIPELINE, "Preview width (px)",
        "Longest edge of the preview sent to the browser; 0 keeps the source "
        "resolution. Boxes are scaled to match, so this does not move them.",
        kind="int", minimum=0, maximum=2560, step=64,
    ),
)

_BY_NAME: Dict[str, Param] = {param.name: param for param in PARAMS}
GROUPS: Tuple[str, ...] = (
    _DETECTION, _SLICING, _TRACKING, _DECISION,
    _OWNERSHIP, _MOTION, _STABILITY, _PIPELINE,
)


def warnings() -> List[str]:
    """Combinations that are individually legal and jointly broken.

    Each of these silently produces "nothing is detected" or "the box is there
    but never turns red", which is the failure mode this panel exists to make
    visible. They are reported rather than enforced: clamping a value the
    operator explicitly set would be worse than telling them what it implies.
    """
    notes: List[str] = []
    if settings.track_confidence >= settings.track_low_thresh:
        notes.append(
            f"Detector floor ({settings.track_confidence:.2f}) is not below the "
            f"low association threshold ({settings.track_low_thresh:.2f}), so "
            "the recovery pass has no weak detections to work with and objects "
            "will drop out on hard frames."
        )
    if settings.track_low_thresh > settings.track_high_thresh:
        notes.append(
            f"Low association threshold ({settings.track_low_thresh:.2f}) is "
            f"above the high one ({settings.track_high_thresh:.2f}); the "
            "recovery pass is empty."
        )
    if settings.new_track_thresh > settings.decision_confidence:
        notes.append(
            f"New track threshold ({settings.new_track_thresh:.2f}) is above the "
            f"decision confidence ({settings.decision_confidence:.2f}), so the "
            "tracking gate is stricter than the alert gate -- an object that "
            "would qualify as a threat is being discarded before it gets an id."
        )
    if settings.motion_release_factor >= settings.motion_threshold_factor:
        notes.append(
            "Settle threshold is not below the movement threshold, so objects "
            "will oscillate between moving and stationary and the dwell timer "
            "will keep pausing."
        )
    if settings.owner_release_factor <= settings.owner_assign_factor:
        notes.append(
            "Owner release distance is not above the bind distance, so ownership "
            "will flicker while a person stands beside their bag."
        )
    if settings.inference_size % 32:
        notes.append(
            f"Inference size {settings.inference_size} is not a multiple of 32; "
            "it will be rounded internally and may not be what you set."
        )

    # Not a combination of settings but a setting against the environment, and it
    # belongs in the same list because it has the same symptom: everything looks
    # configured correctly and bags are still missed. Imported lazily -- the
    # tracker package pulls in ultralytics, and this module is imported during
    # startup before any of that is needed.
    if settings.track_with_reid:
        try:
            from backend.ai.tracker.tracker_manager import reid_status

            status = reid_status()
        except Exception:
            status = None
        if status and not status["usable"]:
            notes.append(
                f"Appearance ReID is switched on but cannot run: {status['reason']}. "
                "Association falls back to motion only, which gives an abandoned "
                "object a new id once somebody walks in front of it -- and a new "
                "id restarts its dwell timer, so it may never be reported."
            )
    return notes


def snapshot() -> Dict[str, Any]:
    """The whole schema plus current values -- one GET populates the panel."""
    grouped: List[Dict[str, Any]] = []
    for group in GROUPS:
        items = [param.as_dict() for param in PARAMS if param.group == group]
        if items:
            grouped.append({"group": group, "params": items})
    return {
        "revision": revision,
        "groups": grouped,
        "modified": sorted(_dirty),
        "warnings": warnings(),
    }


def apply(changes: Dict[str, Any]) -> Dict[str, Any]:
    """Set values by field name, returning what landed and what did not.

    Partial success is the useful behaviour: a panel that sends six sliders and
    gets the whole request rejected because one is unknown teaches the operator
    nothing about which one.
    """
    global revision
    applied: Dict[str, Any] = {}
    rejected: Dict[str, str] = {}
    restart: List[str] = []

    with _lock:
        for name, raw in (changes or {}).items():
            param = _BY_NAME.get(str(name))
            if param is None:
                rejected[str(name)] = "unknown parameter"
                continue
            if param.restart_required:
                rejected[param.name] = (
                    "cannot be changed while running -- set "
                    f"UOD_{_ENV_NAMES.get(param.name, param.name.upper())} and restart"
                )
                restart.append(param.name)
                continue
            try:
                value = param.coerce(raw)
            except ValueError as exc:
                rejected[param.name] = str(exc)
                continue
            if value == getattr(settings, param.name):
                continue
            # settings is frozen so that nothing mutates it by accident; this is
            # the one deliberate exception, which is why it lives here alone.
            object.__setattr__(settings, param.name, value)
            applied[param.name] = value
            if value == getattr(_defaults, param.name):
                _dirty.pop(param.name, None)
            else:
                _dirty[param.name] = value

        if applied:
            revision += 1
            log.info(
                "tuning r%d: %s",
                revision,
                ", ".join(f"{key}={value!r}" for key, value in sorted(applied.items())),
            )

    if rejected:
        log.warning("tuning rejected: %s", rejected)
    return {
        "revision": revision,
        "applied": applied,
        "rejected": rejected,
        "restart_required": restart,
        "warnings": warnings(),
    }


def reset() -> Dict[str, Any]:
    """Put every adjustable value back to its environment-and-default state."""
    global revision
    with _lock:
        restored: Dict[str, Any] = {}
        for param in PARAMS:
            if param.restart_required:
                continue
            default = getattr(_defaults, param.name)
            if getattr(settings, param.name) != default:
                object.__setattr__(settings, param.name, default)
                restored[param.name] = default
        _dirty.clear()
        if restored:
            revision += 1
            log.info("tuning r%d: reset %d parameter(s)", revision, len(restored))
    return {"revision": revision, "restored": restored, "warnings": warnings()}


