"""Catalogue of image-producing operations recorded in provenance.

Operation names used to be a closed ``Literal``. They are now open identifiers:
a new operation (e.g. a DWT watermark or a new attack) is added by calling
``register_operation`` once, and ``artifacts.derive`` refuses names that were
never registered so typos cannot reach the record. Records that carry a
well-formed name this build does not know (e.g. written by a newer version)
still load; ``describe`` gives them a readable fallback label.
"""

import re
from dataclasses import asdict, dataclass

from app.schemas.evidence import OPERATION_NAME_PATTERN
from app.schemas.provenance import OperationInfo


@dataclass(frozen=True)
class OperationSpec:
    name: str
    label: str
    output_label: str
    category: str
    description: str


_REGISTRY: dict[str, OperationSpec] = {}


def register_operation(spec: OperationSpec) -> OperationSpec:
    """Add an operation. Re-registering an identical spec is a no-op; a conflicting one is an error."""
    if not re.fullmatch(OPERATION_NAME_PATTERN, spec.name):
        raise ValueError(f"Invalid operation name {spec.name!r}: use lowercase letters, digits and underscores.")
    existing = _REGISTRY.get(spec.name)
    if existing is not None and existing != spec:
        raise ValueError(f"Operation {spec.name!r} is already registered with a different definition.")
    _REGISTRY[spec.name] = spec
    return spec


def unregister_operation(name: str) -> None:
    _REGISTRY.pop(name, None)


def is_registered(name: str) -> bool:
    return name in _REGISTRY


def require_operation(name: str) -> OperationSpec:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise LookupError(f"Operation {name!r} is not registered; call register_operation first.") from None


def describe(name: str) -> OperationInfo:
    spec = _REGISTRY.get(name)
    if spec is None:
        readable = name.replace("_", " ")
        return OperationInfo(name=name, label=readable.capitalize(), output_label=f"Output of {readable}",
                             category="unregistered", description="Not registered in this version of VERIDIA.", registered=False)
    return OperationInfo(**asdict(spec))


def operations() -> list[OperationInfo]:
    return [describe(name) for name in _REGISTRY]


for _spec in (
    OperationSpec("lsb_steganography_embed", "LSB steganography embed", "Stego image", "steganography",
                  "Sequential RGB LSB embedding of a text payload (payload not recorded)."),
    OperationSpec("keyed_lsb_steganography_embed", "Keyed LSB steganography embed", "Keyed stego image", "steganography",
                  "Keyed pseudo-random RGB LSB embedding of a text payload (payload and key not recorded)."),
    OperationSpec("lsb_matching_steganography_embed", "LSB matching (±1) embed", "LSB-matching stego image", "steganography",
                  "LSB matching: samples are nudged by ±1 so pair-of-values statistics are not equalised (payload not recorded)."),
    OperationSpec("watermark_embed", "Spatial (LSB) watermark embed", "Spatial-watermarked image", "watermarking",
                  "Keyed, redundant LSB watermark (message and key not recorded)."),
    OperationSpec("dct_watermark_embed", "DCT watermark embed", "DCT-watermarked image", "watermarking",
                  "Block-DCT coefficient-pair watermark in the luminance channel (message and key not recorded)."),
    OperationSpec("dwt_watermark_embed", "DWT watermark embed", "DWT-watermarked image", "watermarking",
                  "One-level Haar wavelet watermark in the luminance detail sub-bands (message and key not recorded)."),
    OperationSpec("attack", "Attack (robustness experiment)", "Attacked image", "attack",
                  "Signal-processing attack applied to measure watermark robustness; attack name and parameter recorded."),
):
    register_operation(_spec)
