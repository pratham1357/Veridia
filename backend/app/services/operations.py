"""Orchestration of LSB steganography and image comparison.

Algorithms live in the ``analysis`` package; this module loads images, calls
them, and stores derived artifacts with provenance (via ``artifacts.derive``).
"""

from analysis.core import encode_png
from analysis.integrity.ela import ela_map
from analysis.metrics import compare_images, difference_map
from analysis.steganography import keyed_lsb, lsb, lsb_matching, spa
from analysis.steganography.evaluation import evaluate_detector
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


def ela_png(image_id: str, quality: int) -> tuple[bytes, int]:
    image, peak = ela_map(load_pixels(image_id), quality)
    return encode_png(image), peak

def embed_keyed_lsb(evidence_id: str, payload: str, key: str) -> OperationResult:
    store.evidence(evidence_id)
    payload_bytes = payload.encode("utf-8")

    artifact, record, original_px, _ = derive(
        evidence_id,
        "keyed_lsb_steganography_embed",
        "keyed-stego",
        lambda px: keyed_lsb.embed(px, payload_bytes, key),
        {
            "method": "keyed pseudo-random RGB LSB, 1 bit/sample",
            "payload_bytes": len(payload_bytes),
        },
    )

    return OperationResult(
        artifact=artifact.summary(),
        record=record,
        capacity=CapacityReport(
            capacity_bytes=keyed_lsb.capacity_bytes(original_px),
            payload_bytes=len(payload_bytes),
            utilization_percent=(
                100.0 * len(payload_bytes) / keyed_lsb.capacity_bytes(original_px)
                if keyed_lsb.capacity_bytes(original_px) > 0
                else 0.0
            ),
        ),
    )


def extract_keyed_lsb(source_id: str, key: str) -> StegoExtractResult:
    pixels = load_pixels(source_id)
    try:
        text = keyed_lsb.extract_text(pixels, key)
    except (keyed_lsb.NoPayloadError, keyed_lsb.KeyedLsbError) as exc:
        return StegoExtractResult(found=False, detail=str(exc))

    return StegoExtractResult(
        found=True,
        payload=text,
        payload_bytes=len(text.encode("utf-8")),
        detail="Keyed LSB payload extracted.",
    )


def embed_lsb_matching(
    evidence_id: str, payload: str, seed: int = 0
) -> OperationResult:
    store.evidence(evidence_id)
    payload_bytes = payload.encode("utf-8")

    artifact, record, original_px, _ = derive(
        evidence_id,
        "lsb_matching_steganography_embed",
        "matching-stego",
        lambda px: lsb_matching.embed(px, payload_bytes, seed),
        {
            "method": "LSB Matching +/-1, pseudo-random sample order",
            "payload_bytes": len(payload_bytes),
            "seed": seed,
        },
    )

    capacity = original_px.size // 8
    return OperationResult(
        artifact=artifact.summary(),
        record=record,
        capacity=CapacityReport(
            capacity_bytes=capacity,
            payload_bytes=len(payload_bytes),
            utilization_percent=(
                100.0 * len(payload_bytes) / capacity if capacity else 0.0
            ),
        ),
    )


def extract_lsb_matching(
    source_id: str, payload_bytes: int, seed: int = 0
) -> StegoExtractResult:
    pixels = load_pixels(source_id)
    try:
        raw = lsb_matching.extract(pixels, payload_bytes, seed)
        text = raw.decode("utf-8")
    except (lsb_matching.LsbMatchingError, UnicodeDecodeError) as exc:
        return StegoExtractResult(
            found=False,
            detail=f"Could not extract a valid UTF-8 payload: {exc}",
        )

    return StegoExtractResult(
        found=True,
        payload=text,
        payload_bytes=len(raw),
        detail="LSB Matching payload extracted.",
    )


def evaluate_spa(
    cover_ids: list[str],
    stego_ids_by_rate: dict[float, list[str]],
    threshold: float = 0.05,
) -> dict:
    covers = [load_pixels(image_id) for image_id in cover_ids]
    stego_images = {
        rate: [load_pixels(image_id) for image_id in image_ids]
        for rate, image_ids in stego_ids_by_rate.items()
    }
    return evaluate_detector(
        covers,
        stego_images,
        detector=lambda image: spa.analyze(image)["score"],
        threshold=threshold,
    )
