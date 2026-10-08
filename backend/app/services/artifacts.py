"""Shared helpers: load stored images as pixels and create derived artifacts with provenance."""

import uuid
from datetime import datetime, timezone
from typing import Callable

import numpy as np

from analysis.core import ImageDecodeError, decode_rgb, encode_png, sha256_hex
from analysis.metrics import compare_images
from app.schemas.evidence import ProvenanceRecord, QualityMetrics
from app.services.errors import ServiceError
from app.services.store import StoredImage, store

Parameters = dict[str, str | int | float | bool]


def load_pixels(image_id: str) -> np.ndarray:
    try:
        return decode_rgb(store.image(image_id).data)
    except ImageDecodeError as exc:
        raise ServiceError(str(exc), 422) from exc


def load_pair(first_id: str, second_id: str) -> tuple[np.ndarray, np.ndarray]:
    a, b = load_pixels(first_id), load_pixels(second_id)
    if a.shape != b.shape:
        raise ServiceError("Images must have identical dimensions to be compared.", 422)
    return a, b


def derive(
    source_id: str,
    operation: str,
    suffix: str,
    transform: Callable[[np.ndarray], np.ndarray],
    parameters: Parameters,
) -> tuple[StoredImage, ProvenanceRecord, np.ndarray, np.ndarray]:
    """Apply ``transform`` to a stored image, store the PNG result and append a provenance record.

    Analysis-layer ``ValueError``s (capacity, invalid message, bad attack parameter)
    become 422 responses. Returns (artifact, record, input pixels, output pixels).
    """
    source = store.image(source_id)
    evidence = store.evidence(source.evidence_id)
    input_px = load_pixels(source_id)
    try:
        output_px = transform(input_px)
    except ValueError as exc:
        raise ServiceError(str(exc), 422) from exc

    png = encode_png(output_px)
    stem = source.filename.rsplit(".", 1)[0]
    artifact = StoredImage(
        image_id=f"art_{uuid.uuid4().hex}",
        filename=f"{stem}_{suffix}.png",  # always PNG: lossy formats would destroy embedded data
        mime_type="image/png",
        data=png,
        sha256=sha256_hex(png),
        width=source.width,
        height=source.height,
        evidence_id=evidence.evidence_id,
    )
    record = ProvenanceRecord(
        record_id=f"rec_{uuid.uuid4().hex}",
        operation=operation,  # type: ignore[arg-type]
        timestamp=datetime.now(timezone.utc),
        input_evidence_id=evidence.evidence_id,
        input_image_id=source.image_id,
        input_sha256=source.sha256,
        output_image_id=artifact.image_id,
        output_sha256=artifact.sha256,
        parameters=parameters,
        metrics=QualityMetrics(**compare_images(input_px, output_px)),
    )
    store.add_artifact(artifact)
    evidence.provenance.append(record)
    return artifact, record, input_px, output_px
