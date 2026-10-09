"""Recorded investigation analyses: run an analyzer on an image of an evidence item and record the result.

Algorithms live in ``analysis``; this module selects the analyzer, records an
``AnalysisRecord`` on the evidence and adds a timeline event. Exploratory views
(e.g. the Steganalysis page) call the analysis endpoints directly and are not
recorded; analyses run here are, and each is anchored in the evidence's hash chain.
"""

import uuid
from dataclasses import asdict

from analysis.core import EvidenceInput, ImageDecodeError
from analysis.integrity import ELAAnalyzer, IntegrityAnalyzer, compare
from analysis.integrity.ela import DEFAULT_QUALITY as ELA_DEFAULT_QUALITY
from analysis.metadata import MetadataAnalyzer
from analysis.steganography import SteganographyAnalyzer
from analysis.watermarking import WatermarkAnalyzer
from app.schemas.evidence import AnalysisRecord, AnalysisResult, EvidenceArtifact
from app.schemas.investigation import WatermarkCheck
from app.services.errors import ServiceError
from app.services.provenance import image_label, record_event
from app.services.store import StoredImage, store

LABEL = {
    "metadata": "Metadata analysis",
    "integrity": "Integrity analysis",
    "ela": "Error level analysis (experimental)",
    "steganalysis": "Steganalysis",
    "watermark": "Watermark verification",
    "comparison": "Comparison",
}
PIPELINE = ("metadata", "integrity", "ela", "steganalysis")


def _member(evidence: EvidenceArtifact, image_id: str) -> StoredImage:
    image = store.image(image_id)
    if image.evidence_id != evidence.evidence_id:
        raise ServiceError("Image does not belong to this evidence item.", 422)
    return image


def _input(image: StoredImage) -> EvidenceInput:
    return EvidenceInput(image.image_id, image.data, image.sha256, image.filename)


def run_analysis(
    evidence_id: str,
    kind: str,
    subject_id: str | None = None,
    reference_id: str | None = None,
    watermark: WatermarkCheck | None = None,
    ela_quality: int = ELA_DEFAULT_QUALITY,
) -> AnalysisRecord:
    evidence = store.evidence(evidence_id)
    subject = _member(evidence, subject_id or evidence_id)
    reference = _member(evidence, reference_id) if reference_id else None
    try:
        if kind == "comparison":
            reference = reference or _member(evidence, evidence_id)
            result = compare(_input(reference), _input(subject))
        elif kind == "watermark":
            wm = watermark or WatermarkCheck()
            result = WatermarkAnalyzer(wm.method, wm.key, wm.expected_message, _input(reference) if reference else None).analyze(_input(subject))
        elif kind == "ela":
            result = ELAAnalyzer(ela_quality).analyze(_input(subject))
        else:
            analyzer = {"metadata": MetadataAnalyzer, "integrity": IntegrityAnalyzer, "steganalysis": SteganographyAnalyzer}[kind]()
            result = analyzer.analyze(_input(subject))
    except (ImageDecodeError, ValueError) as exc:
        raise ServiceError(str(exc), 422) from exc

    record = AnalysisRecord(
        record_id=f"ana_{uuid.uuid4().hex}",
        subject_image_id=subject.image_id,
        subject_sha256=subject.sha256,
        reference_image_id=reference.image_id if reference else None,
        result=AnalysisResult.model_validate(asdict(result)),
    )
    against = f" against {image_label(evidence, reference.image_id)}" if reference else ""
    with store.lock:
        evidence.analyses.append(record)
        record_event(
            evidence,
            "analysis_completed",
            subject.image_id,
            f"{LABEL[kind]} on {image_label(evidence, subject.image_id)}{against}: {result.status.replace('_', ' ')}",
            reference_id=record.record_id,
            timestamp=record.result.timestamp,
        )
        store.save(evidence)
    return record


def run_pipeline(
    evidence_id: str,
    subject_id: str | None,
    watermark: WatermarkCheck | None,
    include_ela: bool = False,
    ela_quality: int = ELA_DEFAULT_QUALITY,
) -> list[AnalysisRecord]:
    """Metadata → integrity → (ELA) → steganalysis → (watermark) → (comparison with the original, for derived images)."""
    original = store.evidence(evidence_id).evidence_id
    subject = subject_id or original
    kinds = [k for k in PIPELINE if k != "ela" or include_ela]
    records = [run_analysis(evidence_id, kind, subject, ela_quality=ela_quality) for kind in kinds]
    if watermark is not None:
        reference = original if subject != original else None
        records.append(run_analysis(evidence_id, "watermark", subject, reference, watermark))
    if subject != original:
        records.append(run_analysis(evidence_id, "comparison", subject, original))
    return records
