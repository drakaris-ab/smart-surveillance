"""
ownership.py

Decides whether an object still has its owner nearby -- the judgement the whole
feature rests on, since "unattended" means nothing more than "the owner left".

**Why the old distance test could not work.**  It compared bounding-box centres
and called anything within 250 pixels "near". Two independent problems:

*Resolution.*  250px is roughly a third of the width of a 720p frame and an
eighth of a 4K one. The same scene, recorded at two resolutions, produced
different ownership.

*Perspective.*  A person and their bag ten metres from the camera are perhaps 40
pixels apart. The same pair at the far end of a concourse are 8 pixels apart,
while two strangers standing near the camera are 300 pixels apart and read as
unrelated. One pixel threshold cannot describe both.

**The fix: measure in units the scene supplies itself.**  A person is about 1.7m
tall everywhere in the frame, so their pixel height is a free depth-corrected
ruler. Distance is expressed as a multiple of the nearest person's height, which
makes 1.1 mean "within arm's reach" at any depth and any resolution.

Distance is also measured between *foot points* -- the bottom centre of each box
-- not centres. A standing person's centre sits at chest height, so a bag on the
floor beside them is a full half-height away by centre distance while being
touching in reality. Foot points both sit on the ground plane, where the
distance that matters actually lives.

Two further behaviours the old version got wrong:

*Binding survived nothing.*  Owner assignments were deleted for any object not
present in the current frame, so a single missed detection unbound the object,
and the next frame rebound it to whoever happened to be closest -- often a
passer-by, which reset the timer. Bindings now expire on a timeout, not on a
missed frame.

*A carried bag kept its old owner.*  Binding was permanent once made. If someone
picks the bag up and carries it away, the object is moving, so the binding is
transferred to whoever is actually carrying it -- transferred, not torn down and
rebuilt, because an object with no binding reads as unowned, and rebuilding takes
several frames during which that is what the UI would show.

**Proxy attendance.**  A binding deliberately survives its owner leaving, so the
object cannot be re-bound to a passer-by. That leaves one case unhandled: a
different person comes and *stays* with the object -- a colleague taking over a
bag, a family member sitting down beside it. Left alone, the original binding
would keep reporting "owner absent" and the object would alert while somebody is
plainly standing over it.

So a second person can be recognised as attending the object without taking the
binding, on strict evidence: the bound owner must be gone past the grace window,
and the newcomer must be within assigning distance, *stationary*, and persist for
several frames. Stationarity is the discriminator that a distance test alone
lacks -- a passer-by is moving, someone keeping watch is not.

The binding itself is never transferred, which is what stops this from becoming
a way to launder the dwell timer. Proxy attendance pauses the clock; it does not
reset it. If the newcomer walks off, the accumulated time is still there and the
alert fires immediately rather than starting again from zero.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from backend.core.config import settings
from backend.core.logging import get_logger

log = get_logger("ownership")


def foot_point(bbox) -> Tuple[float, float]:
    """Bottom-centre of a box: where the object meets the ground plane."""
    x1, y1, x2, y2 = bbox
    return ((float(x1) + float(x2)) / 2.0, float(y2))


@dataclass
class _Person:
    """A visible person, as ownership needs to see them."""

    foot: Tuple[float, float]
    height: float
    # Standing still rather than walking through. Only a stationary person can
    # be credited with attending an object they do not own.
    stationary: bool


@dataclass
class _Binding:
    owner_id: int
    bound_at: float
    # When the owner was last confirmed near. Drives the grace window.
    last_seen: float
    # When the *object* was last seen at all. Drives expiry, so an object whose
    # owner walked off an hour ago keeps its binding and does not become
    # available for rebinding to a stranger.
    object_seen: float
    last_distance: float = 0.0


@dataclass
class _Scale:
    """Running estimate of "how many pixels is a person" in this scene."""

    ema: float = 0.0
    alpha: float = 0.15
    samples: int = 0

    def observe(self, height: float) -> None:
        if height <= 1:
            return
        self.ema = height if self.samples == 0 else (1 - self.alpha) * self.ema + self.alpha * height
        self.samples += 1

    def estimate(self, frame_height: Optional[int]) -> float:
        if self.samples:
            return self.ema
        # Before any person has been seen there is no measured ruler. A standing
        # adult occupies roughly a third of the frame at typical surveillance
        # framing -- crude, but it keeps the units sane rather than dividing by
        # zero, and it is replaced by a real measurement as soon as one appears.
        return max(40.0, 0.33 * float(frame_height or 720))


class OwnershipAnalyzer:
    """Binds objects to owners and reports whether that owner is still present."""

    def __init__(
        self,
        assign_factor: Optional[float] = None,
        release_factor: Optional[float] = None,
        grace_seconds: Optional[float] = None,
        bind_frames: Optional[int] = None,
    ) -> None:
        self.assign_factor = float(assign_factor if assign_factor is not None else settings.owner_assign_factor)
        self.release_factor = float(release_factor if release_factor is not None else settings.owner_release_factor)
        self.grace_seconds = float(grace_seconds if grace_seconds is not None else settings.owner_grace_seconds)
        self.bind_frames = int(bind_frames if bind_frames is not None else settings.owner_bind_frames)

        self._bindings: Dict[int, _Binding] = {}
        # {object_track_id: (candidate_person_id, consecutive_frames)}
        self._pending: Dict[int, Tuple[int, int]] = {}
        # Same shape, but for a stationary non-owner accumulating evidence that
        # it is attending an object whose own owner has gone.
        self._proxy: Dict[int, Tuple[int, int]] = {}
        self._scale = _Scale()

    def apply_tuning(self) -> None:
        """Adopt changed ownership distances, keeping every existing binding.

        Bindings survive on purpose. Widening the release distance should stop a
        bag being called abandoned, not forget who owns it -- and the scale ruler
        is kept too, since it takes many frames of observed people to converge
        and is what makes these factors resolution-independent.
        """
        self.assign_factor = float(settings.owner_assign_factor)
        self.release_factor = float(settings.owner_release_factor)
        self.grace_seconds = float(settings.owner_grace_seconds)
        self.bind_frames = int(settings.owner_bind_frames)

    # -- helpers ------------------------------------------------------------

    def _people(self, detections: List[dict]) -> Dict[int, _Person]:
        """Every visible, tracked person, keyed by track id."""
        people: Dict[int, _Person] = {}
        for obj in detections:
            if not obj.get("is_person"):
                continue
            track_id = obj.get("track_id")
            if track_id is None:
                continue
            x1, y1, x2, y2 = obj["bbox"]
            height = max(1.0, float(y2) - float(y1))
            people[int(track_id)] = _Person(
                foot=foot_point(obj["bbox"]),
                height=height,
                stationary=bool(not obj.get("is_moving") and obj.get("motion_ready")),
            )
            self._scale.observe(height)
        return people

    def _normalised(
        self,
        anchor: Tuple[float, float],
        person: _Person,
        frame_height: Optional[int],
    ) -> Tuple[float, float]:
        """Return (pixel distance, distance in person-heights)."""
        pixels = math.hypot(anchor[0] - person.foot[0], anchor[1] - person.foot[1])
        # Use this person's own height when it looks plausible, otherwise the
        # scene-wide estimate. A person partly out of frame, or a truncated box,
        # reports a height far smaller than reality and would otherwise inflate
        # every normalised distance around them.
        scene = self._scale.estimate(frame_height)
        reference = person.height if person.height >= 0.5 * scene else scene
        return pixels, pixels / max(1.0, reference)

    # -- main ---------------------------------------------------------------

    def analyze(self, detections: List[dict]) -> List[dict]:
        now = time.monotonic()
        people = self._people(detections)

        for obj in detections:
            if obj.get("is_person"):
                obj.update(
                    owner_present=True, ownerless=False, owner_id=obj.get("track_id"),
                    owner_distance=0.0, owner_distance_norm=0.0, owner_state="self",
                    owner_missing_seconds=0.0, attendance="self",
                    attended_by=obj.get("track_id"),
                )
                continue

            track_id = obj.get("track_id")
            if track_id is None:
                # Untracked object: no identity to hold a binding against. Say
                # so explicitly rather than guessing, and let the dwell stage
                # ignore it -- it cannot be timed anyway.
                obj.update(
                    owner_present=False, ownerless=False, owner_id=None,
                    owner_distance=-1.0, owner_distance_norm=-1.0, owner_state="untracked",
                    owner_missing_seconds=0.0, attendance="unknown", attended_by=None,
                )
                continue

            track_id = int(track_id)
            frame_height = obj.get("frame_height")
            anchor = foot_point(obj["bbox"])

            nearest_id, nearest_px, nearest_norm = None, -1.0, float("inf")
            for person_id, person in people.items():
                pixels, norm = self._normalised(anchor, person, frame_height)
                if norm < nearest_norm:
                    nearest_id, nearest_px, nearest_norm = person_id, pixels, norm

            binding = self._bindings.get(track_id)

            # A moving object is being carried, so the closest person is the
            # carrier and the binding follows them.
            if binding is not None and obj.get("is_moving"):
                binding = self._maybe_transfer(track_id, binding, nearest_id, nearest_norm, now)

            if binding is None:
                binding = self._try_bind(track_id, nearest_id, nearest_norm, now)
            else:
                binding.object_seen = now

            self._report(obj, binding, people, anchor, frame_height, nearest_id, nearest_px, nearest_norm, now)

        self._expire(now)
        return detections

    def _maybe_transfer(
        self, track_id: int, binding: _Binding,
        nearest_id: Optional[int], nearest_norm: float, now: float,
    ) -> Optional[_Binding]:
        """Move a binding to the person now carrying the object.

        The transfer needs the same persistence as an initial bind, for the same
        reason: whoever is momentarily closest to a bag in motion is often just
        someone it was carried past.
        """
        if nearest_id is None or nearest_norm > self.assign_factor:
            # Moving with nobody near enough to be carrying it. The old binding
            # is certainly stale and there is no candidate to inherit it.
            self._bindings.pop(track_id, None)
            self._pending.pop(track_id, None)
            return None

        if nearest_id == binding.owner_id:
            # The owner is the one carrying it, which is the ordinary case.
            self._pending.pop(track_id, None)
            binding.last_seen = now
            binding.last_distance = nearest_norm
            return binding

        pending_id, frames = self._pending.get(track_id, (nearest_id, 0))
        frames = frames + 1 if pending_id == nearest_id else 1
        self._pending[track_id] = (nearest_id, frames)
        if frames < self.bind_frames:
            return binding

        self._pending.pop(track_id, None)
        previous = binding.owner_id
        binding.owner_id = nearest_id
        binding.bound_at = now
        binding.last_seen = now
        binding.last_distance = nearest_norm
        log.debug("object #%d handed from person #%d to #%d", track_id, previous, nearest_id)
        return binding

    def _try_bind(
        self, track_id: int, nearest_id: Optional[int], nearest_norm: float, now: float,
    ) -> Optional[_Binding]:
        """Bind only after a candidate has stayed close for several frames.

        A single frame of proximity is not evidence of ownership -- people walk
        past luggage constantly. Requiring persistence is what stops a passer-by
        from being recorded as the owner and, worse, from resetting the timer
        when they leave.
        """
        if nearest_id is None or nearest_norm > self.assign_factor:
            self._pending.pop(track_id, None)
            return None

        pending_id, frames = self._pending.get(track_id, (nearest_id, 0))
        frames = frames + 1 if pending_id == nearest_id else 1
        self._pending[track_id] = (nearest_id, frames)

        if frames < self.bind_frames:
            return None

        self._pending.pop(track_id, None)
        binding = _Binding(
            owner_id=nearest_id, bound_at=now, last_seen=now,
            object_seen=now, last_distance=nearest_norm,
        )
        self._bindings[track_id] = binding
        log.debug("object #%d bound to person #%d at %.2f person-heights", track_id, nearest_id, nearest_norm)
        return binding

    def _report(
        self, obj: dict, binding: Optional[_Binding],
        people: Dict[int, _Person],
        anchor: Tuple[float, float], frame_height: Optional[int],
        nearest_id: Optional[int], nearest_px: float, nearest_norm: float, now: float,
    ) -> None:
        track_id = int(obj["track_id"])

        if binding is None:
            # Never had an owner. Not the same thing as abandoned: an object that
            # was already in the scene when monitoring began has no history, so
            # it is reported unowned and the dwell stage decides what that means.
            self._proxy.pop(track_id, None)
            obj.update(
                owner_present=False, ownerless=True, owner_id=None,
                owner_distance=round(nearest_px, 1),
                owner_distance_norm=round(nearest_norm, 2) if nearest_norm != float("inf") else -1.0,
                owner_state="never-owned", owner_missing_seconds=0.0,
                attendance="none", attended_by=None,
            )
            return

        owner = people.get(binding.owner_id)

        if owner is None:
            # Owner not visible at all. Distinguish briefly-occluded from gone:
            # within the grace window the object is still treated as attended,
            # so a person stepping behind a pillar does not start the clock.
            gone_for = now - binding.last_seen
            pixels, norm = -1.0, -1.0
            state = "owner-occluded"
        else:
            pixels, norm = self._normalised(anchor, owner, frame_height)
            binding.last_distance = norm
            # Hysteresis: once bound, the owner may drift out to the wider
            # release radius before counting as gone. A single threshold makes
            # ownership flicker for anyone standing right at the boundary, and
            # every flicker restarts the dwell timer.
            if norm <= self.release_factor:
                binding.last_seen = now
                self._proxy.pop(track_id, None)
                obj.update(
                    owner_present=True, ownerless=False, owner_id=binding.owner_id,
                    owner_distance=round(pixels, 1), owner_distance_norm=round(norm, 2),
                    owner_state="owner-near", owner_missing_seconds=0.0,
                    attendance="owner", attended_by=binding.owner_id,
                )
                return
            gone_for = now - binding.last_seen
            state = "owner-leaving"

        if gone_for <= self.grace_seconds:
            # Still inside the grace window: treat as attended without crediting
            # the owner with being near, so the grace clock keeps running.
            self._proxy.pop(track_id, None)
            obj.update(
                owner_present=True, ownerless=False, owner_id=binding.owner_id,
                owner_distance=round(pixels, 1) if pixels >= 0 else -1.0,
                owner_distance_norm=round(norm, 2) if norm >= 0 else -1.0,
                owner_state=state, owner_missing_seconds=round(gone_for, 1),
                attendance="grace", attended_by=binding.owner_id,
            )
            return

        # The owner is gone for real. Before declaring the object unattended,
        # check whether somebody else is standing with it.
        proxy_id = self._proxy_attendance(track_id, people, anchor, frame_height)
        if proxy_id is not None:
            obj.update(
                owner_present=True, ownerless=False, owner_id=binding.owner_id,
                owner_distance=round(pixels, 1) if pixels >= 0 else -1.0,
                owner_distance_norm=round(norm, 2) if norm >= 0 else -1.0,
                owner_state="attended-by-other", owner_missing_seconds=round(gone_for, 1),
                attendance="proxy", attended_by=proxy_id,
            )
            return

        obj.update(
            owner_present=False, ownerless=True, owner_id=binding.owner_id,
            owner_distance=round(pixels, 1) if pixels >= 0 else -1.0,
            owner_distance_norm=round(norm, 2) if norm >= 0 else -1.0,
            owner_state="owner-absent" if owner is None else "owner-left",
            owner_missing_seconds=round(gone_for, 1),
            attendance="none", attended_by=None,
        )

    def _proxy_attendance(
        self,
        track_id: int,
        people: Dict[int, _Person],
        anchor: Tuple[float, float],
        frame_height: Optional[int],
    ) -> Optional[int]:
        """Return a person who has stayed with this object, if any.

        Only stationary people count, and only after several consecutive frames.
        Both conditions exist to keep foot traffic out: someone walking past is
        moving, and someone who merely happens to pass close is gone by the next
        frame.
        """
        candidate_id, candidate_norm = None, float("inf")
        for person_id, person in people.items():
            if not person.stationary:
                continue
            _, norm = self._normalised(anchor, person, frame_height)
            if norm <= self.assign_factor and norm < candidate_norm:
                candidate_id, candidate_norm = person_id, norm

        if candidate_id is None:
            self._proxy.pop(track_id, None)
            return None

        pending_id, frames = self._proxy.get(track_id, (candidate_id, 0))
        frames = frames + 1 if pending_id == candidate_id else 1
        self._proxy[track_id] = (candidate_id, frames)
        return candidate_id if frames >= self.bind_frames else None

    def _expire(self, now: float) -> None:
        """Drop bindings for objects not seen for a while.

        Keyed on how long the *object* has been gone, not on whether it appeared
        in this particular frame -- that distinction is what made the original
        lose bindings to a single dropped detection.
        """
        ttl = max(settings.track_ttl_seconds, self.grace_seconds * 2)
        stale = [tid for tid, b in self._bindings.items() if now - b.object_seen > ttl]
        for track_id in stale:
            self._bindings.pop(track_id, None)
            self._pending.pop(track_id, None)
            self._proxy.pop(track_id, None)

    def forget(self, track_id: int) -> None:
        track_id = int(track_id)
        self._bindings.pop(track_id, None)
        self._pending.pop(track_id, None)
        self._proxy.pop(track_id, None)
