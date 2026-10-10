"""Watermark robustness experiments: attack a watermarked image, then try to recover the mark.

Each result row records the attack, its parameter, the distortion the attack
introduced (measured against the watermarked input), whether the watermark was
still verified, and the raw bit error rate before redundancy/voting. The BER is
a continuous measure: decoding can still succeed at a non-zero BER because the
payload is repeated, and fails once errors overwhelm the voting.
"""

import math
from types import ModuleType
from typing import Any

import numpy as np

from analysis.metrics import compare_images
from analysis.watermarking import dct_watermark, dwt_watermark, lsb_watermark
from analysis.watermarking.attacks import ATTACKS, apply_attack

SCHEMES: dict[str, ModuleType] = {"spatial_lsb": lsb_watermark, "dct": dct_watermark, "dwt": dwt_watermark}

SWEEP_MIN, SWEEP_MAX, SWEEP_STEP = 10, 100, 10
# Upper bound on the points of one sweep series. Each point is a full attack plus a watermark decode
# (about 60 ms on a 256x256 image, far more on large ones), and a request may sweep three methods, so an
# unbounded step would let one request run for hours. 100 admits JPEG quality 5..100 at step 1 (96 points)
# and every default sweep, while rejecting anything finer.
MAX_SWEEP_POINTS = 100


def recovery(attacked: np.ndarray, scheme: str, message: str, key: str) -> dict[str, Any]:
    """Attempt to verify ``message`` in ``attacked`` and measure the raw bit error rate."""
    module = SCHEMES[scheme]
    result = module.verify(attacked, key, message)
    ber = module.bit_error_rate(attacked, message, key) if len(message.encode("utf-8")) <= module.MAX_MESSAGE_BYTES else None
    return {"status": result.status, "extracted_message": result.message, "bit_error_rate": ber}


def evaluate(attacked: np.ndarray, reference: np.ndarray, scheme: str, message: str, key: str) -> dict[str, Any]:
    """Distortion of ``attacked`` relative to ``reference`` plus watermark recovery."""
    return {**compare_images(reference, attacked), **recovery(attacked, scheme, message, key)}


def run_attack(marked: np.ndarray, attack: str, parameter: float, scheme: str, message: str, key: str = "") -> tuple[np.ndarray, dict[str, Any]]:
    attacked = apply_attack(marked, attack, parameter)
    return attacked, {"attack": attack, "parameter": parameter, **evaluate(attacked, marked, scheme, message, key)}


def run_suite(marked: np.ndarray, scheme: str, message: str, key: str = "") -> list[dict[str, Any]]:
    """Run every preset of every attack. The first row is the unattacked baseline."""
    rows = [{"attack": "none", "parameter": 0.0, **evaluate(marked, marked, scheme, message, key)}]
    for attack in ATTACKS.values():
        for parameter in attack.presets:
            rows.append(run_attack(marked, attack.name, parameter, scheme, message, key)[1])
    return rows


def default_sweep(attack: str) -> tuple[float, float, float]:
    """Default ``(start, stop, step)`` for sweeping ``attack``.

    JPEG sweeps quality 10..100 in steps of 10. Every other attack sweeps its whole documented range
    in ten equal steps (eleven points), since JPEG's range means nothing for, say, rotation in degrees.
    """
    if attack == "jpeg":
        return float(SWEEP_MIN), float(SWEEP_MAX), float(SWEEP_STEP)
    spec = ATTACKS.get(attack)
    if spec is None:
        raise ValueError(f"Unknown attack: {attack}")
    return spec.minimum, spec.maximum, (spec.maximum - spec.minimum) / 10


def sweep_values(attack: str, start: float, stop: float, step: float) -> list[float]:
    """The parameter values of a sweep, validated *before* any work is done.

    Raises ``ValueError`` for an unknown attack, non-finite numbers, a non-positive step,
    ``start > stop``, a range outside the attack's documented limits, or more than
    ``MAX_SWEEP_POINTS`` points. Values are computed as ``start + i * step`` and rounded, so
    they do not accumulate floating-point error (0.30000000000000004).
    """
    spec = ATTACKS.get(attack)
    if spec is None:
        raise ValueError(f"Unknown attack: {attack}")
    for name, value in (("start", start), ("stop", stop), ("step", step)):
        if not math.isfinite(value):
            raise ValueError(f"Sweep {name} must be a finite number.")
    if step <= 0:
        raise ValueError("Sweep step must be positive.")
    if start > stop:
        raise ValueError("Sweep start must not exceed stop.")
    if start < spec.minimum or stop > spec.maximum:
        raise ValueError(
            f"{spec.label} {spec.parameter_label} must stay between {spec.minimum:g} and {spec.maximum:g} "
            f"(requested {start:g} to {stop:g})."
        )
    count = math.floor(min((stop - start) / step, 1e15) + 1e-9) + 1
    if count > MAX_SWEEP_POINTS:
        raise ValueError(
            f"Sweep would run {count:,} points; the maximum is {MAX_SWEEP_POINTS}. Increase the step or narrow the range."
        )
    return [round(start + i * step, 9) for i in range(count)]


def sweep(marked: np.ndarray, scheme: str, message: str, key: str = "", attack: str = "jpeg",
          start: float | None = None, stop: float | None = None, step: float | None = None) -> list[dict[str, Any]]:
    """Run one attack across a parameter range, so the point where recovery fails is visible.

    Omitted bounds come from :func:`default_sweep` (JPEG quality 10..100 in steps of 10). Returns
    one row per parameter value, each with the attack's distortion and the watermark recovery result.
    """
    defaults = default_sweep(attack)
    values = sweep_values(attack, *(d if v is None else v for d, v in zip(defaults, (start, stop, step))))
    return [run_attack(marked, attack, v, scheme, message, key)[1] for v in values]
