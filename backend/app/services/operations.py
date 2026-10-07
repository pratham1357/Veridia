"""Orchestration of steganography, watermarking and comparison.

Algorithms live in the ``analysis`` package; this module loads evidence, calls
them, stores derived artifacts and records provenance.
"""

import uuid
from datetime import datetime, timezone
from typing import Callable

import numpy as np

from analysis.core import ImageDecodeError, decode_rgb, encode_png, sha256_hex
from analysis.metrics import compare_images
from analysis.steganography import lsb, lsb_analysis
from analysis.watermarking import lsb_watermark as wm
from app.schemas.evidence import ImageSummary, ProvenanceRecord, QualityMetrics
from app.schemas.operations import (
    CapacityReport,
    ChannelLsbStats,
    CompareResult,
    LsbAnalysis,
    OperationResult,
    StegoExtractResult,
    WatermarkVerifyResult,
)
from app.services.errors import ServiceError
from app.services.store import StoredImage, store


def _pixels(image_id: str) -> np.ndarray:
    try:
        return decode_rgb(store.image(image_id).data)
    except ImageDecodeError as exc:
        raise ServiceError(str(exc), 422) from exc


def _derive(
    evidence_id: str,
    operation: str,
    suffix: str,
    transform: Callable[[np.ndarray], np.ndarray],
    parameters: dict[str, str | int | float | bool],
) -> tuple[StoredImage, ProvenanceRecord, np.ndarray, np.ndarray]:
    evidence = store.evidence(evidence_id)
    original_px = _pixels(evidence_id)
    try:
        output_px = transform(original_px)
    except (lsb.LsbError, wm.WatermarkError) as exc:
        raise ServiceError(str(exc), 422) from exc

    png = encode_png(output_px)
    stem = evidence.original_filename.rsplit(".", 1)[0]
    artifact = StoredImage(
        image_id=f"art_{uuid.uuid4().hex}",
        filename=f"{stem}_{suffix}.png",  # always PNG: lossy formats would destroy LSB data
        mime_type="image/png",
        data=png,
        sha256=sha256_hex(png),
        width=evidence.width,
        height=evidence.height,
    )
    record = ProvenanceRecord(
        record_id=f"rec_{uuid.uuid4().hex}",
        operation=operation,  # type: ignore[arg-type]
        timestamp=datetime.now(timezone.utc),
        input_evidence_id=evidence_id,
        input_sha256=evidence.sha256,
        output_image_id=artifact.image_id,
        output_sha256=artifact.sha256,
        parameters=parameters,
        metrics=QualityMetrics(**compare_images(original_px, output_px)),
    )
    store.add_artifact(artifact)
    evidence.provenance.append(record)
    return artifact, record, original_px, output_px


# --- steganography -----------------------------------------------------------


def stego_capacity(evidence_id: str, payload_bytes: int = 0) -> CapacityReport:
    store.evidence(evidence_id)
    return CapacityReport(**lsb.capacity_report(_pixels(evidence_id), payload_bytes))


def embed_stego(evidence_id: str, payload: str) -> OperationResult:
    payload_bytes = len(payload.encode("utf-8"))
    artifact, record, original_px, _ = _derive(
        evidence_id,
        "lsb_steganography_embed",
        "stego",
        lambda px: lsb.embed_text(px, payload),
        {"method": "sequential RGB LSB, 1 bit/sample", "payload_bytes": payload_bytes},
    )
    return OperationResult(
        artifact=artifact.summary(),
        record=record,
        capacity=CapacityReport(**lsb.capacity_report(original_px, payload_bytes)),
    )


def extract_stego(source_id: str) -> StegoExtractResult:
    pixels = _pixels(source_id)
    try:
        raw = lsb.extract(pixels)
        text = raw.decode("utf-8")
    except lsb.NoPayloadError as exc:
        return StegoExtractResult(found=False, detail=str(exc))
    except UnicodeDecodeError:
        return StegoExtractResult(found=False, detail="A payload header was found but the payload is not valid UTF-8 text.")
    return StegoExtractResult(found=True, payload=text, payload_bytes=len(raw), detail="Payload extracted.")


def analyze_lsb(image_id: str) -> LsbAnalysis:
    pixels = _pixels(image_id)
    return LsbAnalysis(
        image_id=image_id,
        channels=[ChannelLsbStats(**s) for s in lsb_analysis.channel_statistics(pixels)],
        veridia_lsb_header_found=lsb_analysis.has_veridia_header(pixels),
        note="These are descriptive LSB characteristics, not proof that data is hidden. Natural images and prior "
        "processing can produce similar values, and a small payload may not change them noticeably.",
    )


def lsb_plane_png(image_id: str, channel: str) -> bytes:
    return encode_png(lsb_analysis.lsb_plane_image(_pixels(image_id), channel))


# --- watermarking ------------------------------------------------------------


def embed_watermark(evidence_id: str, message: str, key: str) -> OperationResult:
    artifact, record, _, _ = _derive(
        evidence_id,
        "watermark_embed",
        "watermarked",
        lambda px: wm.embed(px, message, key),
        {
            "method": "keyed redundant LSB watermark",
            "message_bytes": len(message.encode("utf-8")),
            "key_used": bool(key),  # the key itself is never recorded
        },
    )
    return OperationResult(artifact=artifact.summary(), record=record)


def verify_watermark(source_id: str, key: str, expected: str | None) -> WatermarkVerifyResult:
    result = wm.verify(_pixels(source_id), key, expected)
    detail = {
        "verified": "A watermark was extracted and matches the expected message.",
        "mismatch": "A watermark was extracted but differs from the expected message.",
        "extracted": "A watermark was extracted. No expected message was supplied to compare against.",
        "not_found": "No valid watermark was found for this key. The key may be wrong, the image may not be "
        "watermarked, or the watermark may have been destroyed by processing.",
    }[result.status]
    return WatermarkVerifyResult(
        status=result.status, message=result.message, bit_agreement=result.bit_agreement, detail=detail
    )


# --- comparison --------------------------------------------------------------


def compare(original_id: str, processed_id: str) -> CompareResult:
    original, processed = store.image(original_id), store.image(processed_id)
    a, b = _pixels(original_id), _pixels(processed_id)
    if a.shape != b.shape:
        raise ServiceError("Images must have identical dimensions to be compared.", 422)
    summaries: tuple[ImageSummary, ImageSummary] = original.summary(), processed.summary()
    return CompareResult(
        original=summaries[0],
        processed=summaries[1],
        metrics=QualityMetrics(**compare_images(a, b)),
        hashes_differ=original.sha256 != processed.sha256,
    )
