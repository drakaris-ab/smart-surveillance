"""
sahi.py

Slicing Aided Hyper Inference -- and, more to the point, a correct merge.

**What slicing buys.**  A bag 20 pixels wide in a 1920x1080 frame is about 10
pixels once the frame is letterboxed to the inference size. That is below what
the detector can resolve. Crop a 640x640 tile around it and infer at 640, and
the same bag is 20 pixels at inference scale -- detectable. Recall on distant
objects rises sharply. Nothing else in the pipeline changes: this module hands
back full-frame boxes.

**Why the previous merge produced wrong boxes.**  Tiles overlap, so one object
is often detected several times, and the duplicates were collapsed with NMS on
IoU. That fails in the exact case tiling creates. When an object straddles a
tile boundary, the tile sees only the visible fragment and reports a box around
that fragment. A fragment covering a third of the true object has an IoU with
it of about 0.33 -- well under any sane NMS threshold -- so *both* survive, and
the UI shows a correct box plus a clipped one that jitters as the object moves
across the seam. Boxes that looked "inaccurate" were mostly this.

Two changes fix it:

1. *Reject truncated boxes.*  A box touching a tile edge which is not also a
   frame edge is by definition cut off. Discard it rather than trying to repair
   it -- with 25% overlap, any object narrower than a quarter of a tile is fully
   inside some other tile, and anything larger is caught by the full-frame pass
   that runs alongside the tiles.
2. *Merge on intersection-over-smaller, not IoU.*  IoS asks "is the smaller box
   essentially contained in the larger one", which is the actual question when
   comparing a partial detection against a whole one. Survivors of a merge take
   the union of the group, so a genuinely split object is reassembled instead
   of being reported twice.

**Why motion gating is safe here, with one caveat that matters.**  Tiling every
region every frame is most of the cost, and most tiles are static wall. So only
tiles whose pixels changed get inferred. The caveat: an unattended object is by
definition *not moving*. Gate on motion alone and an abandoned bag stops being
detected the moment it settles, the tracker drops it, and the dwell timer
resets -- the system would become structurally incapable of detecting the thing
it exists to detect. So tiles overlapping any currently tracked object are
always inferred, and a full sweep runs periodically to pick up whatever
appeared without triggering the change detector.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.ai.detector.yolo_detector import RawDetections, YOLODetector

log = get_logger("sahi")


@dataclass(frozen=True)
class Tile:
    """A crop window, plus which of its edges are interior to the frame.

    An "open" edge is one where the frame continues past the tile, so a
    detection touching it is a fragment of something larger. An edge that
    coincides with the frame border is closed: a box touching it is legitimately
    at the picture edge and must be kept.
    """

    x1: int
    y1: int
    x2: int
    y2: int
    open_left: bool
    open_top: bool
    open_right: bool
    open_bottom: bool

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    def crop(self, frame: np.ndarray) -> np.ndarray:
        return frame[self.y1:self.y2, self.x1:self.x2]


def plan_tiles(height: int, width: int, slice_size: int, overlap: float) -> List[Tile]:
    """Cover the frame with equally sized, overlapping tiles.

    At the right and bottom borders the window is shifted back inward rather
    than shrunk. Slivers are the worse option: a 640x40 strip stretched to a
    square inference input distorts aspect ratio badly enough to hurt accuracy,
    and the extra overlap a shifted window creates costs nothing because the
    merge step collapses the duplicates it produces.
    """
    slice_size = max(64, int(slice_size))
    overlap = min(0.8, max(0.0, float(overlap)))
    step = max(1, int(round(slice_size * (1.0 - overlap))))

    def positions(total: int) -> List[Tuple[int, int]]:
        if total <= slice_size:
            return [(0, total)]
        spans, start = [], 0
        while True:
            end = min(start + slice_size, total)
            begin = max(0, end - slice_size)
            spans.append((begin, end))
            if end >= total:
                return spans
            start += step

    tiles: List[Tile] = []
    for y1, y2 in positions(height):
        for x1, x2 in positions(width):
            tiles.append(Tile(
                x1=x1, y1=y1, x2=x2, y2=y2,
                open_left=x1 > 0,
                open_top=y1 > 0,
                open_right=x2 < width,
                open_bottom=y2 < height,
            ))
    return tiles


def _drop_truncated(det: RawDetections, tile: Tile, margin: int) -> RawDetections:
    """Remove boxes that run into an open tile edge."""
    if len(det) == 0:
        return det

    x1, y1, x2, y2 = det.xyxy[:, 0], det.xyxy[:, 1], det.xyxy[:, 2], det.xyxy[:, 3]
    keep = np.ones(len(det), dtype=bool)
    if tile.open_left:
        keep &= x1 > margin
    if tile.open_top:
        keep &= y1 > margin
    if tile.open_right:
        keep &= x2 < tile.width - margin
    if tile.open_bottom:
        keep &= y2 < tile.height - margin

    return RawDetections(det.xyxy[keep], det.confidence[keep], det.class_id[keep])


def merge_nmm(
    det: RawDetections,
    ios_threshold: float,
    class_aware: bool = True,
    union_size_ratio: float = 0.5,
) -> RawDetections:
    """Collapse duplicate detections of one object into one box.

    Greedy, highest confidence first. For each surviving box, any lower-scoring
    box of the same class whose *intersection over its own area* exceeds the
    threshold is absorbed.

    Absorbed boxes of comparable size contribute to a union, which reassembles
    an object that two tiles each saw part of. A much smaller absorbed box is
    simply suppressed instead: taking a union there would stretch the box over a
    genuinely separate nearby object, which is how "one giant box swallowing
    half the scene" happens.
    """
    n = len(det)
    if n <= 1:
        return det

    order = np.argsort(-det.confidence, kind="stable")
    boxes = det.xyxy[order].astype(np.float64)
    confs = det.confidence[order]
    classes = det.class_id[order]

    widths = np.clip(boxes[:, 2] - boxes[:, 0], 0, None)
    heights = np.clip(boxes[:, 3] - boxes[:, 1], 0, None)
    areas = widths * heights

    consumed = np.zeros(n, dtype=bool)
    keep_boxes, keep_confs, keep_classes = [], [], []

    for i in range(n):
        if consumed[i]:
            continue
        consumed[i] = True
        box = boxes[i].copy()

        rest = np.flatnonzero(~consumed)
        if rest.size:
            ix1 = np.maximum(box[0], boxes[rest, 0])
            iy1 = np.maximum(box[1], boxes[rest, 1])
            ix2 = np.minimum(box[2], boxes[rest, 2])
            iy2 = np.minimum(box[3], boxes[rest, 3])
            inter = np.clip(ix2 - ix1, 0, None) * np.clip(iy2 - iy1, 0, None)

            smaller = np.minimum(areas[i], areas[rest])
            ios = np.divide(inter, smaller, out=np.zeros_like(inter), where=smaller > 0)

            match = ios >= ios_threshold
            if class_aware:
                match &= classes[rest] == classes[i]

            absorbed = rest[match]
            if absorbed.size:
                consumed[absorbed] = True
                ratios = np.divide(
                    areas[absorbed], areas[i],
                    out=np.zeros_like(areas[absorbed]), where=areas[i] > 0,
                )
                comparable = absorbed[ratios >= union_size_ratio]
                if comparable.size:
                    group = np.vstack([box[None, :], boxes[comparable]])
                    box = np.array([
                        group[:, 0].min(), group[:, 1].min(),
                        group[:, 2].max(), group[:, 3].max(),
                    ])

        keep_boxes.append(box)
        keep_confs.append(confs[i])
        keep_classes.append(classes[i])

    return RawDetections(
        xyxy=np.asarray(keep_boxes, dtype=np.float32).reshape(-1, 4),
        confidence=np.asarray(keep_confs, dtype=np.float32),
        class_id=np.asarray(keep_classes, dtype=np.int32),
    )


class TileGate:
    """Chooses which tiles are worth inferring this cycle.

    Change detection runs on a heavily downscaled greyscale copy -- roughly
    1/64th of the pixels -- so the gate costs well under a millisecond, which is
    the only way it can pay for itself. Per-tile change counts come from an
    integral image, making each tile a constant-time lookup regardless of size.
    """

    def __init__(self, downscale: int = 8, diff_threshold: int = 18, min_changed_ratio: float = 0.0015):
        self.downscale = max(2, int(downscale))
        self.diff_threshold = int(diff_threshold)
        self.min_changed_ratio = float(min_changed_ratio)
        self._previous: Optional[np.ndarray] = None
        self._cycle = 0

    def _small(self, frame: np.ndarray) -> np.ndarray:
        height, width = frame.shape[:2]
        target = (max(16, width // self.downscale), max(16, height // self.downscale))
        grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        return cv2.resize(grey, target, interpolation=cv2.INTER_AREA)

    def select(
        self,
        frame: np.ndarray,
        tiles: Sequence[Tile],
        keepalive: Sequence[Sequence[float]] = (),
    ) -> Tuple[List[int], str]:
        """Return the indices of tiles to infer, and why they were chosen."""
        self._cycle += 1
        small = self._small(frame)
        previous, self._previous = self._previous, small

        every = max(1, settings.sahi_full_sweep_every)
        if previous is None or previous.shape != small.shape or self._cycle % every == 1:
            return list(range(len(tiles))), "full-sweep"

        diff = cv2.absdiff(previous, small)
        _, mask = cv2.threshold(diff, self.diff_threshold, 1, cv2.THRESH_BINARY)
        integral = cv2.integral(mask.astype(np.uint8))

        height, width = frame.shape[:2]
        scale_x = small.shape[1] / max(1, width)
        scale_y = small.shape[0] / max(1, height)

        selected: List[int] = []
        for index, tile in enumerate(tiles):
            sx1 = int(tile.x1 * scale_x)
            sy1 = int(tile.y1 * scale_y)
            sx2 = min(small.shape[1], max(sx1 + 1, int(tile.x2 * scale_x)))
            sy2 = min(small.shape[0], max(sy1 + 1, int(tile.y2 * scale_y)))
            changed = (
                integral[sy2, sx2] - integral[sy1, sx2]
                - integral[sy2, sx1] + integral[sy1, sx1]
            )
            area = max(1, (sx2 - sx1) * (sy2 - sy1))
            if changed / area >= self.min_changed_ratio:
                selected.append(index)

        # A stationary abandoned object generates no motion, so tiles holding
        # something already being tracked are inferred regardless. Without this
        # the system would lose sight of an object precisely when it becomes
        # interesting.
        if keepalive:
            active = set(selected)
            for box in keepalive:
                if len(box) < 4:
                    continue
                bx1, by1, bx2, by2 = box[:4]
                for index, tile in enumerate(tiles):
                    if index in active:
                        continue
                    if bx1 < tile.x2 and bx2 > tile.x1 and by1 < tile.y2 and by2 > tile.y1:
                        active.add(index)
            selected = sorted(active)

        return selected, "motion+tracked"


@dataclass
class SlicedResult:
    detections: RawDetections
    tiles_run: int
    infer_ms: float
    mode: str


class SlicedDetector:
    """Full-frame pass plus adaptive tiling, merged into one set of boxes.

    The full-frame pass always runs. It is what catches objects too large to fit
    inside a tile, and it is the fallback that keeps the system working if
    tiling is gated off entirely for a cycle. Tiles are additive: they exist
    only to recover small objects the full-frame pass cannot resolve.
    """

    def __init__(self, detector: YOLODetector, camera_id: int = 0) -> None:
        self.detector = detector
        self.camera_id = camera_id
        self.gate = TileGate() if settings.sahi_motion_gate else None
        self._tiles: List[Tile] = []
        self._tiles_key: Tuple[int, int, int, float] = (0, 0, 0, 0.0)
        self._logged_plan = False

    def apply_tuning(self) -> None:
        """Adopt changed slicing settings.

        Almost everything in this class reads ``settings`` at the moment it is
        used, and the tile plan is keyed on size and overlap so it rebuilds
        itself. The one captured decision is whether a motion gate exists at all,
        so that is what this reconciles. A gate created here begins with a full
        sweep, which is correct: it has no history to compare against.
        """
        self.detector.apply_tuning()
        if settings.sahi_motion_gate and self.gate is None:
            self.gate = TileGate()
        elif not settings.sahi_motion_gate and self.gate is not None:
            self.gate = None
        self._logged_plan = False

    def _tiles_for(self, height: int, width: int) -> List[Tile]:
        key = (height, width, settings.sahi_slice, settings.sahi_overlap)
        if key != self._tiles_key:
            self._tiles = plan_tiles(height, width, settings.sahi_slice, settings.sahi_overlap)
            self._tiles_key = key
            self._logged_plan = False
        if not self._logged_plan:
            log.info(
                "cam=%d tiling %dx%d into %d tile(s) of %dpx at %.0f%% overlap",
                self.camera_id, width, height, len(self._tiles),
                settings.sahi_slice, settings.sahi_overlap * 100,
            )
            self._logged_plan = True
        return self._tiles

    def _should_slice(self, height: int, width: int) -> bool:
        if not settings.sahi_enabled:
            return False
        # Slicing a frame barely larger than one tile just repeats the
        # full-frame pass at a slightly different crop, for double the cost.
        limit = settings.sahi_slice * settings.sahi_min_scale
        return max(height, width) >= limit

    def detect(self, frame: np.ndarray, keepalive: Sequence[Sequence[float]] = ()) -> SlicedResult:
        height, width = frame.shape[:2]
        total_ms = 0.0

        full = self.detector.predict([frame], imgsz=settings.inference_size, batch_size=1)
        total_ms += getattr(self.detector, "last_infer_ms", 0.0)
        collected = [full[0]] if full else [RawDetections.empty()]

        tiles_run = 0
        mode = "full-frame"

        if self._should_slice(height, width):
            tiles = self._tiles_for(height, width)
            if self.gate is not None:
                indices, mode = self.gate.select(frame, tiles, keepalive)
            else:
                indices, mode = list(range(len(tiles))), "all-tiles"

            chosen = [tiles[i] for i in indices]
            if chosen:
                crops = [tile.crop(frame) for tile in chosen]
                # Tiles are inferred at their own pixel size. Upscaling a 640px
                # tile to 1280 costs ~4x the compute and adds no information,
                # because the extra pixels are interpolated.
                tile_results = self.detector.predict(
                    crops, imgsz=settings.sahi_slice, batch_size=settings.sahi_batch,
                )
                total_ms += getattr(self.detector, "last_infer_ms", 0.0)
                tiles_run = len(chosen)

                margin = settings.sahi_edge_margin
                for tile, result in zip(chosen, tile_results):
                    result = _drop_truncated(result, tile, margin)
                    if len(result) == 0:
                        continue
                    shifted = result.xyxy.copy()
                    shifted[:, [0, 2]] += tile.x1
                    shifted[:, [1, 3]] += tile.y1
                    collected.append(RawDetections(shifted, result.confidence, result.class_id))

        merged = self._combine(collected, height, width)
        return SlicedResult(detections=merged, tiles_run=tiles_run, infer_ms=total_ms, mode=mode)

    @staticmethod
    def _combine(parts: Sequence[RawDetections], height: int, width: int) -> RawDetections:
        parts = [p for p in parts if len(p) > 0]
        if not parts:
            return RawDetections.empty()

        xyxy = np.vstack([p.xyxy for p in parts]).astype(np.float32)
        conf = np.concatenate([p.confidence for p in parts]).astype(np.float32)
        cls = np.concatenate([p.class_id for p in parts]).astype(np.int32)

        # Clamp before merging: a box a pixel past the border would otherwise
        # skew the union of any group it joins.
        np.clip(xyxy[:, [0, 2]], 0, width - 1, out=xyxy[:, [0, 2]])
        np.clip(xyxy[:, [1, 3]], 0, height - 1, out=xyxy[:, [1, 3]])

        return merge_nmm(
            RawDetections(xyxy, conf, cls),
            ios_threshold=settings.sahi_merge_ios,
            class_aware=True,
        )
