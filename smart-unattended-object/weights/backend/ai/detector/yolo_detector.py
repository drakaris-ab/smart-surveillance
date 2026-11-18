"""
yolo_detector.py

The only place in the system that calls the model. Everything else asks this
class for boxes.

**Why a lock.**  There is one shared ``YOLO`` instance, and Ultralytics caches a
single ``BasePredictor`` on it. That predictor holds per-call state -- batch
buffers, the source iterator, the results list. Two camera threads calling
``predict()`` on the same model therefore interleave writes into the same
buffers: the visible symptom is boxes from one camera appearing on another, or
an ``IndexError`` deep inside ultralytics. The lock serialises entry. This costs
nothing in throughput, because the GPU executes one kernel stream here anyway --
the work was always serial, it was just previously unsynchronised.

**Why class filtering happens here.**  The original pipeline detected all 80
COCO classes, tracked them, smoothed their labels, and only then discarded
everything that was not a person or a bag. Passing ``classes=`` into predict
moves that filter ahead of the model's own NMS, so cars and chairs are dropped
before they cost anything -- and, more importantly, they never enter the
tracker's ID namespace where they compete for associations with the objects we
actually care about.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

import numpy as np

from backend.core.config import ALLOWED_CLASSES, settings
from backend.core.logging import get_logger, throttled
from backend.core.runtime import get_profile
from backend.ai.detector.model_loader import class_ids_for, get_names, load_model

log = get_logger("detector")


@dataclass
class RawDetections:
    """Boxes for one image, in that image's own pixel space."""

    xyxy: np.ndarray      # (N, 4) float32
    confidence: np.ndarray  # (N,)  float32
    class_id: np.ndarray    # (N,)  int32

    @staticmethod
    def empty() -> "RawDetections":
        return RawDetections(
            np.zeros((0, 4), dtype=np.float32),
            np.zeros((0,), dtype=np.float32),
            np.zeros((0,), dtype=np.int32),
        )

    def __len__(self) -> int:
        return int(self.xyxy.shape[0])


class YOLODetector:
    """Shared-model inference with an explicit device, precision and class set."""

    _model_lock = threading.Lock()  # class-level: guards the shared predictor
    _infer_lock = threading.Lock()

    def __init__(
        self,
        conf_threshold: Optional[float] = None,
        inference_size: Optional[int] = None,
        allowed_classes: Iterable[str] = ALLOWED_CLASSES,
    ) -> None:
        self.model = load_model()
        self.profile = get_profile()

        self.MIN_CONF = float(conf_threshold if conf_threshold is not None else settings.track_confidence)
        self.INFERENCE_SIZE = int(inference_size if inference_size is not None else settings.inference_size)

        self.names = get_names()
        self.allowed_class_ids = class_ids_for(set(allowed_classes))
        self.person_class_ids = set(class_ids_for({"person"}))

        # Cumulative, for the /system/performance endpoint.
        self.total_calls = 0
        self.total_images = 0
        self.total_infer_ms = 0.0

    # -- properties ---------------------------------------------------------

    @property
    def device(self) -> str:
        return self.profile.device

    def is_person(self, class_id: int) -> bool:
        return int(class_id) in self.person_class_ids

    def apply_tuning(self) -> None:
        """Adopt a changed confidence floor or inference size.

        Both were captured in ``__init__`` because they are passed on every
        ``predict`` call and re-reading them per call is measurable at this rate.
        Neither touches the loaded weights, so there is nothing to reload: the
        next call simply runs at the new size. The model file itself cannot be
        changed this way and is reported as restart-required instead.
        """
        self.MIN_CONF = float(settings.track_confidence)
        self.INFERENCE_SIZE = int(settings.inference_size)

    def class_name(self, class_id: int) -> str:
        return self.names.get(int(class_id), str(class_id))

    # -- inference ----------------------------------------------------------

    def predict(
        self,
        images: Sequence[np.ndarray],
        imgsz: Optional[int] = None,
        batch_size: Optional[int] = None,
    ) -> List[RawDetections]:
        """Run the model over ``images``, returning one result per image.

        ``imgsz`` defaults to the configured inference size. SAHI overrides it
        with the tile's own size so a 640px tile is inferred at 640 rather than
        being upscaled -- upscaling a tile costs roughly 2.25x the compute for
        no extra information, since the pixels are interpolated.
        """
        if not images:
            return []

        size = int(imgsz or self.INFERENCE_SIZE)
        batch = max(1, int(batch_size or settings.sahi_batch))
        results: List[RawDetections] = []

        started = time.perf_counter()
        with self._infer_lock:
            for start in range(0, len(images), batch):
                chunk = list(images[start:start + batch])
                try:
                    raw = self.model.predict(
                        source=chunk,
                        device=self.profile.device,
                        half=self.profile.half,
                        imgsz=size,
                        conf=self.MIN_CONF,
                        iou=settings.nms_iou,
                        classes=self.allowed_class_ids or None,
                        max_det=settings.max_detections,
                        verbose=False,
                    )
                except Exception as exc:
                    # One bad batch must not kill the camera thread. Report at
                    # most once per interval and return empties for the chunk,
                    # which the tracker handles as "nothing seen this frame".
                    throttled(
                        log, "predict-failed", 40,
                        "inference failed on a batch of %d: %s", len(chunk), exc,
                        interval=15.0,
                    )
                    results.extend(RawDetections.empty() for _ in chunk)
                    continue
                results.extend(self._to_raw(r) for r in raw)
            # No explicit device synchronise here. ``_to_raw`` copies every result
            # tensor to host memory, which already blocks until the kernels that
            # produced it have finished, so the timing below is honest without
            # one. A full ``torch.cuda.synchronize`` would additionally wait for
            # unrelated work -- and it would do so while still holding the lock,
            # so with several cameras each one would drain the whole device before
            # the next was allowed to queue anything, leaving the GPU idle in
            # between.

        elapsed_ms = (time.perf_counter() - started) * 1000
        self.total_calls += 1
        self.total_images += len(images)
        self.total_infer_ms += elapsed_ms
        self.last_infer_ms = elapsed_ms
        return results

    @staticmethod
    def _to_raw(result) -> RawDetections:
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return RawDetections.empty()
        return RawDetections(
            xyxy=boxes.xyxy.detach().cpu().numpy().astype(np.float32),
            confidence=boxes.conf.detach().cpu().numpy().astype(np.float32),
            class_id=boxes.cls.detach().cpu().numpy().astype(np.int32),
        )

    def stats(self) -> dict:
        calls = max(1, self.total_calls)
        images = max(1, self.total_images)
        return {
            "device": self.profile.device,
            "half_precision": self.profile.half,
            "inference_size": self.INFERENCE_SIZE,
            "calls": self.total_calls,
            "images": self.total_images,
            "avg_ms_per_call": round(self.total_infer_ms / calls, 2),
            "avg_ms_per_image": round(self.total_infer_ms / images, 2),
        }
