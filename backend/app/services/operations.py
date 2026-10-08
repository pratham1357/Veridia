"""Orchestration of LSB steganography and image comparison.

Algorithms live in the ``analysis`` package; this module loads images, calls
them, and stores derived artifacts with provenance (via ``artifacts.derive``).
"""

from analysis.core import encode_png
from analysis.metrics import compare_images, difference_map
from analysis.steganography import lsb
from app.schemas.evidence import QualityMetrics
from app.schemas.operations import CapacityReport, CompareResult, OperationResult, StegoExtractResult
from app.services.artifacts import derive, load_pair, load_pixels
from app.services.store import store


def stego_capacity(evidence_id: str, payload_bytes: int = 0) -> CapacityReport:
    store.evidence(evidence_id)
    return CapacityReport(**lsb.capacity_report(load_pixels(evidence_id), payload_bytes))


def embed_stego(evidence_id: str, payload: str) -> OperationResult:
    store.evidence(evidence_id)
    payload_bytes = len(payload.encode("utf-8"))
    artifact, record, original_px, _ = derive(
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
    pixels = load_pixels(source_id)
    try:
        raw = lsb.extract(pixels)
        text = raw.decode("utf-8")
    except lsb.NoPayloadError as exc:
        return StegoExtractResult(found=False, detail=str(exc))
    except UnicodeDecodeError:
        return StegoExtractResult(found=False, detail="A payload header was found but the payload is not valid UTF-8 text.")
    return StegoExtractResult(found=True, payload=text, payload_bytes=len(raw), detail="Payload extracted.")


def compare(original_id: str, processed_id: str) -> CompareResult:
    original, processed = store.image(original_id), store.image(processed_id)
    a, b = load_pair(original_id, processed_id)
    return CompareResult(
        original=original.summary(),
        processed=processed.summary(),
        metrics=QualityMetrics(**compare_images(a, b)),
        hashes_differ=original.sha256 != processed.sha256,
    )


def difference_png(original_id: str, processed_id: str) -> tuple[bytes, int]:
    image, peak = difference_map(*load_pair(original_id, processed_id))
    return encode_png(image), peak
