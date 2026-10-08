"""Watermark robustness experiments: attack a watermarked image, then try to recover the mark.

Each result row records the attack, its parameter, the distortion the attack
introduced (measured against the watermarked input), whether the watermark was
still verified, and the raw bit error rate before redundancy/voting. The BER is
a continuous measure: decoding can still succeed at a non-zero BER because the
payload is repeated, and fails once errors overwhelm the voting.
"""

from types import ModuleType
from typing import Any

import numpy as np

from analysis.metrics import compare_images
from analysis.watermarking import dct_watermark, lsb_watermark
from analysis.watermarking.attacks import ATTACKS, apply_attack

SCHEMES: dict[str, ModuleType] = {"spatial_lsb": lsb_watermark, "dct": dct_watermark}


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
