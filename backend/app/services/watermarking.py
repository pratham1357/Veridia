"""Orchestration of watermark embedding, verification, attack experiments and method comparison."""

from types import ModuleType

from analysis.core import encode_png
from analysis.metrics import compare_images
from analysis.watermarking import dct_watermark, robustness
from analysis.watermarking.attacks import ATTACKS, apply_attack
from analysis.watermarking.dct import dct_magnitude_map
from app.schemas.evidence import QualityMetrics
from app.schemas.operations import OperationResult
from app.schemas.watermark import (
    AttackInfo,
    AttackResult,
    CompareMethodsResult,
    MethodComparison,
    RobustnessReport,
    RobustnessRow,
    WatermarkMethod,
    WatermarkVerifyResult,
)
from app.services.artifacts import derive, load_pair, load_pixels
from app.services.errors import ServiceError
from app.services.store import store

_DETAIL = {
    "verified": "A watermark was extracted and matches the expected message.",
    "mismatch": "A watermark was extracted but differs from the expected message.",
    "extracted": "A watermark was extracted. No expected message was supplied to compare against.",
    "not_found": "No valid watermark was found with this method and key. The key or method may be wrong, the image "
    "may not be watermarked, or processing may have destroyed the watermark.",
}


def _scheme(method: WatermarkMethod) -> ModuleType:
    return robustness.SCHEMES[method]


def _ber(module: ModuleType, pixels, message: str | None, key: str) -> float | None:
    if message is None or len(message.encode("utf-8")) > module.MAX_MESSAGE_BYTES:
        return None
    return module.bit_error_rate(pixels, message, key)


def embed(evidence_id: str, method: WatermarkMethod, message: str, key: str, strength: float | None) -> OperationResult:
    store.evidence(evidence_id)
    params: dict[str, str | int | float | bool] = {
        "message_bytes": len(message.encode("utf-8")),
        "key_used": bool(key),  # the key itself is never recorded
    }
    if method == "dct":
        s = strength if strength is not None else dct_watermark.DEFAULT_STRENGTH
        params |= {"method": "block DCT coefficient-pair (Y channel)", "strength": s,
                   "coefficients": f"C{dct_watermark.COEFF_A} vs C{dct_watermark.COEFF_B}"}
        artifact, record, _, _ = derive(
            evidence_id, "dct_watermark_embed", "dct_watermarked", lambda px: dct_watermark.embed(px, message, key, s), params
        )
    else:
        params |= {"method": "keyed redundant LSB watermark"}
        artifact, record, _, _ = derive(
            evidence_id, "watermark_embed", "watermarked", lambda px: _scheme("spatial_lsb").embed(px, message, key), params
        )
    return OperationResult(artifact=artifact.summary(), record=record)


def verify(
    source_id: str, method: WatermarkMethod, key: str, expected: str | None, reference_id: str | None = None
) -> WatermarkVerifyResult:
    module = _scheme(method)
    pixels = load_pixels(source_id)
    result = module.verify(pixels, key, expected)
    reference_metrics = None
    if reference_id is not None:
        reference, _ = load_pair(reference_id, source_id)
        reference_metrics = QualityMetrics(**compare_images(reference, pixels))
    detail = _DETAIL[result.status]
    if result.status == "not_found" and float(result.parameters.get("copies", 0)) < module.MIN_COPIES:
        detail = "This image is too small to carry this watermark, so no extraction was attempted."
    return WatermarkVerifyResult(
        method=method,
        status=result.status,  # type: ignore[arg-type]
        message=result.message,
        bit_agreement=result.bit_agreement,
        bit_error_rate=_ber(module, pixels, expected, key),
        parameters=result.parameters,
        reference_metrics=reference_metrics,
        detail=detail,
    )


def attacks() -> list[AttackInfo]:
    return [
        AttackInfo(name=a.name, label=a.label, parameter_label=a.parameter_label, presets=list(a.presets),
                   minimum=a.minimum, maximum=a.maximum)
        for a in ATTACKS.values()
    ]


def _row(raw: dict) -> RobustnessRow:
    attack = ATTACKS.get(raw["attack"])
    return RobustnessRow(
        **raw,
        attack_label=attack.label if attack else "No attack (baseline)",
        parameter_label=attack.parameter_label if attack else "",
    )


def run_attack(image_id: str, method: WatermarkMethod, attack: str, parameter: float, message: str, key: str) -> AttackResult:
    if attack not in ATTACKS:
        raise ServiceError(f"Unknown attack: {attack}", 422)
    artifact, record, _, attacked = derive(
        image_id,
        "attack",
        f"{attack}_{parameter:g}",
        lambda px: apply_attack(px, attack, parameter),
        {"attack": attack, "parameter": parameter},
    )
    recovery = robustness.recovery(attacked, method, message, key)
    row = _row({"attack": attack, "parameter": parameter, **record.metrics.model_dump(), **recovery})
    return AttackResult(artifact=artifact.summary(), record=record, row=row)


def run_suite(image_id: str, method: WatermarkMethod, message: str, key: str) -> RobustnessReport:
    rows = robustness.run_suite(load_pixels(image_id), method, message, key)
    return RobustnessReport(image_id=image_id, method=method, rows=[_row(r) for r in rows])


def compare_methods(evidence_id: str, message: str, key: str, strength: float | None) -> CompareMethodsResult:
    if len(message.encode("utf-8")) > dct_watermark.MAX_MESSAGE_BYTES:
        raise ServiceError(f"Message must be at most {dct_watermark.MAX_MESSAGE_BYTES} bytes to fit both methods.", 422)
    methods = []
    for method in ("spatial_lsb", "dct"):
        result = embed(evidence_id, method, message, key, strength)  # type: ignore[arg-type]
        image_id = result.artifact.image_id
        methods.append(
            MethodComparison(
                method=method,  # type: ignore[arg-type]
                artifact=result.artifact,
                record=result.record,
                verification=verify(image_id, method, key, message),  # type: ignore[arg-type]
                robustness=run_suite(image_id, method, message, key).rows,  # type: ignore[arg-type]
            )
        )
    return CompareMethodsResult(original=store.image(evidence_id).summary(), methods=methods)


def dct_map_png(image_id: str) -> bytes:
    return encode_png(dct_magnitude_map(load_pixels(image_id)))
