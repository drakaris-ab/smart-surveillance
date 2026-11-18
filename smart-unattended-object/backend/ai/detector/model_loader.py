"""
model_loader.py

Loads the YOLO weights exactly once and hands the same instance to every
camera thread.

Two changes matter beyond the original singleton.

**The device is pinned at load, and again at every predict call.**  Ultralytics
does not infer on the ``YOLO`` wrapper: ``predict()`` lazily builds a
``BasePredictor`` which builds an ``AutoBackend``, and *that* runs the forward
pass. ``AutoBackend`` calls ``select_device()`` itself, so a model moved with
``.to("cuda")`` can still end up executing somewhere else if the predict call
does not name a device. Device and precision lock in on the first predict and
are awkward to change afterwards, so both are passed explicitly every time.

**The model is warmed up before any camera sees a frame.**  The first inference
pays for CUDA context creation, kernel autotuning and cuDNN algorithm search --
seconds, not milliseconds. Paying that during startup instead of on the first
real frame stops the first camera from timing out and keeps the initial FPS
measurement from being wildly pessimistic.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from ultralytics import YOLO

from backend.core.config import settings
from backend.core.runtime import get_profile, sync
from backend.core.logging import get_logger

log = get_logger("model")

# backend/  <- app/ <- ai/ <- detector/model_loader.py
ROOT_DIR = Path(__file__).resolve().parents[3]
WEIGHTS_DIR = ROOT_DIR / "weights"

_model: Optional[YOLO] = None
_names: Dict[int, str] = {}
_lock = threading.Lock()


def _resolve_weights() -> Path:
    candidate = Path(settings.model_name)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    direct = WEIGHTS_DIR / settings.model_name
    if direct.exists():
        return direct

    # A missing model is a deployment mistake, not a runtime condition, so say
    # exactly what is on disk rather than letting ultralytics try to download.
    present = sorted(p.name for p in WEIGHTS_DIR.glob("*.pt")) if WEIGHTS_DIR.is_dir() else []
    raise FileNotFoundError(
        f"model '{settings.model_name}' not found in {WEIGHTS_DIR}. "
        f"Available: {present or 'none'}. Set UOD_MODEL to one of these."
    )


def _warmup(model: YOLO) -> None:
    profile = get_profile()
    size = settings.inference_size
    blank = np.zeros((size, size, 3), dtype=np.uint8)
    started = time.perf_counter()
    try:
        model.predict(
            source=blank,
            device=profile.device,
            half=profile.half,
            imgsz=size,
            conf=0.99,
            verbose=False,
        )
        sync()
    except Exception as exc:  # a failed warmup must not stop the worker booting
        log.warning("warmup pass failed (%s); first real frame will be slower", exc)
        return
    log.info("warmup complete in %.0fms at imgsz=%d", (time.perf_counter() - started) * 1000, size)


def load_model() -> YOLO:
    """Return the shared model, loading it on first call. Thread-safe."""
    global _model, _names

    if _model is not None:
        return _model

    with _lock:
        if _model is not None:
            return _model

        weights = _resolve_weights()
        profile = get_profile()
        log.info("loading %s", weights.name)

        model = YOLO(str(weights))
        model.to(profile.torch_device)

        raw_names = getattr(model, "names", {}) or {}
        _names = {int(k): str(v) for k, v in raw_names.items()}

        _warmup(model)
        _model = model
        log.info(
            "model ready: %s, %d classes, %s%s",
            weights.name, len(_names), profile.device,
            " (fp16)" if profile.half else "",
        )

    return _model


def loaded_count() -> int:
    """How many detector instances exist -- one, or nothing has run yet.

    Reported by the performance endpoint so "adding a camera loaded another copy
    of the model" is a question with an answer rather than a suspicion.
    """
    return 1 if _model is not None else 0


def get_names() -> Dict[int, str]:
    """``{class_id: class_name}`` for the loaded model."""
    if not _names:
        load_model()
    return dict(_names)


def class_ids_for(wanted: set[str]) -> list[int]:
    """Translate class names into the ids this checkpoint actually uses.

    Never hardcode ids. A custom-trained checkpoint can order classes any way
    it likes, and silently detecting the wrong class is far harder to spot than
    detecting nothing. Names absent from the model are reported once, since a
    typo in the wanted set otherwise looks like a detection failure.
    """
    names = get_names()
    lowered = {name.lower(): cid for cid, name in names.items()}
    ids, missing = [], []
    for name in sorted(wanted):
        cid = lowered.get(name.lower())
        if cid is None:
            missing.append(name)
        else:
            ids.append(cid)
    if missing:
        log.warning(
            "these classes are not in %s and will never be detected: %s",
            settings.model_name, ", ".join(missing),
        )
    return sorted(ids)
