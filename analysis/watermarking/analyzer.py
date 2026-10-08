from analysis.core import AnalysisResult, Analyzer, EvidenceInput, Finding, decode_rgb
from analysis.metrics import compare_images
from analysis.watermarking.robustness import SCHEMES

METHOD_LABEL = {"spatial_lsb": "spatial-domain (LSB)", "dct": "DCT-domain"}
LIMITATIONS = [
    "Verification shows that a mark made with this method and key is present. It does not show that the rest of the content is unmodified: the DCT mark survives JPEG and noise, and anyone with the method and key could embed it.",
    "A missing watermark does not show that the image was never marked: a wrong key or method, or processing (e.g. JPEG for the spatial mark), prevents recovery.",
]


class WatermarkAnalyzer(Analyzer):
    """Watermark extraction/verification for one method and key, optionally against a reference image."""

    name = "watermark"
    version = "0.2.0"

    def __init__(self, method: str = "dct", key: str = "", expected: str | None = None, reference: EvidenceInput | None = None):
        if method not in SCHEMES:
            raise ValueError(f"Unknown watermark method: {method}")
        self.method, self.key, self.expected, self.reference = method, key, expected, reference

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        module = SCHEMES[self.method]
        pixels = decode_rgb(evidence.data)
        result = module.verify(pixels, self.key, self.expected)
        fits = self.expected is not None and len(self.expected.encode("utf-8")) <= module.MAX_MESSAGE_BYTES
        measurements = {
            "method": self.method,
            "key_supplied": bool(self.key),
            "expected_supplied": self.expected is not None,
            "extraction_status": result.status,
            "extracted_message": result.message,
            "bit_agreement": result.bit_agreement,
            "bit_error_rate": module.bit_error_rate(pixels, self.expected, self.key) if fits else None,
            **{f"param_{k}": v for k, v in result.parameters.items()},
        }
        if self.reference is not None:
            ref = decode_rgb(self.reference.data)
            if ref.shape == pixels.shape:
                m = compare_images(ref, pixels)
                measurements |= {"reference_mse": m["mse"], "reference_psnr_db": m["psnr_db"], "reference_ssim": m["ssim"]}

        label = METHOD_LABEL[self.method]
        too_small = result.status == "not_found" and float(result.parameters.get("copies", 0)) < module.MIN_COPIES
        if too_small:
            status, finding = "not_applicable", Finding(
                f"Image too small for the {label} watermark",
                f"Capacity allows {result.parameters.get('copies')} payload copies; at least {module.MIN_COPIES} are required.",
                "Extraction was not attempted.",
                "Says nothing about whether the image was ever watermarked.",
            )
        elif result.status == "verified":
            status, finding = "verified", Finding(
                f"Watermark verified ({label})",
                f"Extracted message equals the expected message; CRC valid; {result.bit_agreement:.1%} of carriers agree with the decoded bits.",
                "The image carries the expected watermark for this method and key.",
                "Not proof that the content is otherwise unmodified or authentic.",
                "verification",
            )
        elif result.status == "mismatch":
            status, finding = "indicator_detected", Finding(
                f"Watermark present but message differs ({label})",
                f"Extracted {result.message!r} (CRC valid); expected {self.expected!r}.",
                "The image carries a different watermark than expected with this key.",
                "Does not show who embedded either message.",
                "indicator",
            )
        elif result.status == "extracted":
            status, finding = "indicator_detected", Finding(
                f"Watermark extracted ({label})",
                f"Recovered {result.message!r} with a valid CRC; no expected message was supplied.",
                "A watermark made with this method and key is present.",
                "Without an expected message, nothing is verified about its content or origin.",
                "indicator",
            )
        else:
            status, finding = "no_indicator", Finding(
                f"No watermark recovered ({label})",
                "No payload with a valid CRC was decoded with this key.",
                "No mark made with this method and key was found.",
                "The image may still be watermarked with another key or method, or the mark may have been destroyed by processing.",
            )
        return AnalysisResult("watermark", self.version, status, finding.interpretation, measurements, [finding], LIMITATIONS)
