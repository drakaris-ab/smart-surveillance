"""
severity.py

Grades a confirmed threat. Duration is the only signal available -- a bag that
has stood alone for four minutes deserves more attention than one that has stood
for forty seconds, and nothing else in the pipeline distinguishes them.

The class list is no longer duplicated here. It was a hand-copied second copy of
the set in ``config.py``, which is exactly the kind of duplication that silently
diverges: adding a class in one place and not the other produced an object that
could accumulate dwell time but could never be graded above "NONE".

Severity is reported as both a name and a rank. The name is what an operator
reads; the rank is what code should compare, because string ordering puts
"CRITICAL" below "LOW" alphabetically and any sort written against the names
would be quietly wrong.
"""

from __future__ import annotations

from typing import Tuple

from backend.core.config import UNATTENDED_OBJECT_CLASSES, settings

_CANDIDATES = frozenset(name.lower() for name in UNATTENDED_OBJECT_CLASSES)

# (multiple of the threat threshold, severity, rank). Expressed as multiples
# rather than absolute seconds: with a 30s threshold the old fixed 30/60/120
# boundaries put an object at CRITICAL after four times the threshold, but if an
# operator raises the threshold to 600s for a car park every threat would be
# born CRITICAL. The ladder starts above 1.0 because an object is only graded at
# all once it has already crossed the threshold.
_LADDER: Tuple[Tuple[float, str, int], ...] = (
    (2.0, "LOW", 1),
    (4.0, "MEDIUM", 2),
    (8.0, "HIGH", 3),
    (float("inf"), "CRITICAL", 4),
)

SEVERITY_RANKS = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


class SeverityAnalyzer:
    """Maps dwell duration onto a severity name and rank."""

    def grade(self, obj: dict) -> Tuple[str, int]:
        if not obj.get("is_threat"):
            return "NONE", 0
        if str(obj.get("class_name", "")).lower() not in _CANDIDATES:
            return "NONE", 0

        duration = float(obj.get("dwell_seconds", obj.get("duration", 0)) or 0.0)
        threshold = max(1.0, float(obj.get("threat_seconds") or settings.threat_seconds))
        multiple = duration / threshold

        for limit, name, rank in _LADDER:
            if multiple < limit:
                return name, rank
        return "CRITICAL", 4

    def get_severity(self, obj: dict) -> str:
        """Grade the object and record the rank alongside the name."""
        name, rank = self.grade(obj)
        obj["severity_rank"] = rank
        return name
