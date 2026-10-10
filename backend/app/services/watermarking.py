"""Orchestration of watermark embedding, verification, attack experiments and method comparison."""

from types import ModuleType

from analysis.core import encode_png
from analysis.metrics import compare_images
from analysis.watermarking import dct_watermark, dwt_watermark, robustness
from analysis.watermarking.attacks import ATTACKS, apply_attack
from analysis.watermarking.dct import dct_magnitude_map
from analysis.watermarking.haar import subband_preview
from app.schemas.evidence import QualityMetrics
from app.schemas.operations import OperationResult
from app.schemas.watermark import (
    AttackInfo,
    AttackResult,
    CompareMethodsResult,
    MethodComparison,
    RobustnessReport,
    RobustnessRow,
    SweepReport,
    SweepRequest,
    SweepSeries,
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


METHOD_NAME: dict[str, str] = {"spatial_lsb": "Spatial (LSB)", "dct": "DCT", "dwt": "DWT"}


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
    elif method == "dwt":
        s = strength if strength is not None else dwt_watermark.DEFAULT_STRENGTH
        params |= {"method": "one-level Haar DWT sub-band pair (Y channel)", "strength": s,
                   "coefficients": "HL vs LH detail sub-bands"}
        artifact, record, _, _ = derive(
            evidence_id, "dwt_watermark_embed", "dwt_watermarked", lambda px: dwt_watermark.embed(px, message, key, s), params
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


def _preflight_embeds(
    evidence_id: str, methods: list[WatermarkMethod], message: str, key: str, strength: float | None, pixels=None
) -> None:
    """Prove that every requested embed will succeed, *before* any artifact or timeline event exists.

    Embedding records a derived artifact, a provenance record and a timeline event as it goes, so a
    request that embeds several methods and then fails part-way would leave the earlier ones behind.
    This runs each embed in memory first (same message, key, strength and image as the real one), so the
    scheme's own validation (message length, strength range, minimum image size) decides, and nothing is
    stored. It costs one extra in-memory embed per method.
    """
    store.evidence(evidence_id)
    if pixels is None:
        pixels = load_pixels(evidence_id)
    for method in methods:
        module = _scheme(method)
        try:
            if method == "spatial_lsb":
                module.embed(pixels, message, key)
            else:
                module.embed(pixels, message, key, strength if strength is not None else module.DEFAULT_STRENGTH)
        except ValueError as exc:
            raise ServiceError(f"{METHOD_NAME[method]}: {exc}", 422) from exc


def sweep(req: SweepRequest) -> SweepReport:
    """Sweep one attack over a parameter range for one or several methods.

    Everything that can be rejected is rejected first: attack name, range, step and point count
    (``robustness.sweep_values``), message length per method, and, when embedding fresh watermarks,
    that each embed will succeed. Only then are artifacts created, so an invalid request has no effect.
    """
    attack = ATTACKS.get(req.attack)
    if attack is None:
        raise ServiceError(f"Unknown attack: {req.attack}", 422)
    start, stop, step = (d if v is None else v for d, v in zip(robustness.default_sweep(req.attack), (req.start, req.stop, req.step)))
    try:
        values = robustness.sweep_values(req.attack, start, stop, step)
    except ValueError as exc:
        raise ServiceError(str(exc), 422) from exc

    methods = list(dict.fromkeys(req.methods or [req.method]))  # drop duplicates, keep order
    size = len(req.message.encode("utf-8"))
    for method in methods:
        limit = _scheme(method).MAX_MESSAGE_BYTES
        if size > limit:
            raise ServiceError(f"{METHOD_NAME[method]}: message is {size} bytes but the limit is {limit}.", 422)
    if req.methods:
        store.evidence(req.image_id)  # multi-method sweeps embed from the original evidence
    source = load_pixels(req.image_id)  # an unknown image fails here, with nothing created
    for value in (values[0], values[-1]):  # an attack can reject a parameter for this image (e.g. a crop leaving too little)
        try:
            apply_attack(source, req.attack, value)
        except ValueError as exc:
            raise ServiceError(str(exc), 422) from exc
    if req.methods:
        _preflight_embeds(req.image_id, methods, req.message, req.key, None, source)

    series = []
    for method in methods:
        image_id = req.image_id
        if req.methods:  # embed each method fresh from the same evidence so the comparison is fair
            image_id = embed(req.image_id, method, req.message, req.key, None).artifact.image_id
        try:
            rows = robustness.sweep(load_pixels(image_id), method, req.message, req.key, req.attack, start, stop, step)
        except ValueError as exc:  # unreachable after validation above; kept as a safety net
            raise ServiceError(str(exc), 422) from exc
        series.append(SweepSeries(method=method, image_id=image_id, rows=[_row(r) for r in rows]))
    return SweepReport(attack=req.attack, attack_label=attack.label, parameter_label=attack.parameter_label, series=series)


def compare_methods(evidence_id: str, message: str, key: str, strength: float | None) -> CompareMethodsResult:
    limit = min(dct_watermark.MAX_MESSAGE_BYTES, dwt_watermark.MAX_MESSAGE_BYTES)
    if len(message.encode("utf-8")) > limit:
        raise ServiceError(f"Message must be at most {limit} bytes to fit every method.", 422)
    # `strength` is the DCT strength (the UI slider says so). DCT and DWT strengths are on different scales
    # (defaults 25 and 8), so applying one value to both made DWT 3x too strong and changed every number in
    # the comparison. Spatial and DWT always use their documented defaults.
    strengths: dict[str, float | None] = {"spatial_lsb": None, "dct": strength, "dwt": None}
    pixels = load_pixels(evidence_id)
    for method, value in strengths.items():  # all or nothing: prove every embed first
        _preflight_embeds(evidence_id, [method], message, key, value, pixels)  # type: ignore[list-item]
    methods = []
    for method in ("spatial_lsb", "dct", "dwt"):
        result = embed(evidence_id, method, message, key, strengths[method])  # type: ignore[arg-type]
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


def dwt_map_png(image_id: str) -> bytes:
    """The four Haar sub-bands tiled LL/LH over HL/HH."""
    return encode_png(subband_preview(load_pixels(image_id)))
