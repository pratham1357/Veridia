"""Recording helpers for the evidence timeline. Events are only created by real operations."""

import uuid
from datetime import datetime, timezone

from app.schemas.evidence import EvidenceArtifact, TimelineEvent
from app.services.store import store


def now() -> datetime:
    return datetime.now(timezone.utc)


def image_label(evidence: EvidenceArtifact, image_id: str) -> str:
    """Human-readable name for an image within an evidence item."""
    if image_id == evidence.evidence_id:
        return f"original evidence ({evidence.original_filename})"
    return store.image(image_id).filename


def record_event(
    evidence: EvidenceArtifact,
    event_type: str,
    subject_image_id: str,
    description: str,
    reference_id: str | None = None,
    timestamp: datetime | None = None,
) -> TimelineEvent:
    event = TimelineEvent(
        event_id=f"evt_{uuid.uuid4().hex}",
        timestamp=timestamp or now(),
        event_type=event_type,  # type: ignore[arg-type]
        subject_image_id=subject_image_id,
        description=description,
        reference_id=reference_id,
    )
    evidence.timeline.append(event)
    return event
