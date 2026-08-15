"""Pure event-classification logic for edge-to-cloud uploads."""

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class EventDecision:
    should_upload: bool
    event_type: str
    priority: bool = False


def split_faces(
    face_analysis: Mapping[str, Any] | None,
) -> tuple[list[dict], list[dict]]:
    """Return recognized and unknown face records from an analysis result."""
    faces: Sequence[Mapping[str, Any]] = (face_analysis or {}).get("faces", [])
    known = [dict(face) for face in faces if face.get("recognized") is True]
    unknown = [dict(face) for face in faces if face.get("recognized") is not True]
    return known, unknown


def classify_event(
    dwelling_analysis: Mapping[str, Any],
    face_analysis: Mapping[str, Any] | None,
) -> EventDecision:
    """Decide whether an edge event warrants cloud analysis."""
    known, unknown = split_faces(face_analysis)
    dwelling_detected = bool(dwelling_analysis.get("dwelling_detected", False))

    if dwelling_detected and unknown:
        return EventDecision(True, "dwelling_alert_unknown", priority=True)

    if dwelling_detected and known:
        duration = float(dwelling_analysis.get("longest_continuous_presence", 0) or 0)
        if duration > 60:
            return EventDecision(True, "dwelling_known_person")
        return EventDecision(False, "known_person_detected")

    if unknown:
        return EventDecision(True, "unknown_person_detected")

    if known:
        return EventDecision(False, "known_person_detected")

    return EventDecision(False, "motion_inconclusive")
