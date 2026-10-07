"""In-memory evidence store. Contents are lost on restart; there is deliberately no persistence yet."""

from dataclasses import dataclass

from app.schemas.evidence import EvidenceArtifact, ImageSummary
from app.services.errors import ServiceError


@dataclass(frozen=True)
class StoredImage:
    image_id: str
    filename: str
    mime_type: str
    data: bytes
    sha256: str
    width: int
    height: int

    def summary(self) -> ImageSummary:
        return ImageSummary(
            image_id=self.image_id,
            filename=self.filename,
            mime_type=self.mime_type,
            size=len(self.data),
            sha256=self.sha256,
            width=self.width,
            height=self.height,
        )


class EvidenceStore:
    def __init__(self) -> None:
        self._evidence: dict[str, EvidenceArtifact] = {}
        self._images: dict[str, StoredImage] = {}  # originals and derived artifacts, by image ID

    def add_evidence(self, evidence: EvidenceArtifact, original: StoredImage) -> None:
        self._evidence[evidence.evidence_id] = evidence
        self._images[original.image_id] = original

    def add_artifact(self, image: StoredImage) -> None:
        self._images[image.image_id] = image

    def evidence(self, evidence_id: str) -> EvidenceArtifact:
        try:
            return self._evidence[evidence_id]
        except KeyError:
            raise ServiceError("Evidence not found.", 404) from None

    def image(self, image_id: str) -> StoredImage:
        try:
            return self._images[image_id]
        except KeyError:
            raise ServiceError("Image not found.", 404) from None

    def list_evidence(self) -> list[EvidenceArtifact]:
        return sorted(self._evidence.values(), key=lambda e: e.created_at, reverse=True)


store = EvidenceStore()
