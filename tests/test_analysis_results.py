"""Every analyzer returns the common result structure with consistent, interpretable fields."""

import io
from dataclasses import fields

import pytest
from PIL import Image

from analysis.core import AnalysisResult, EvidenceInput, Finding, encode_png, sha256_hex
from analysis.integrity import IntegrityAnalyzer, compare
from analysis.metadata import MetadataAnalyzer
from analysis.steganography import SteganographyAnalyzer, lsb
from analysis.watermarking import WatermarkAnalyzer, dct_watermark

STATUSES = {"verified", "indicator_detected", "no_indicator", "inconclusive", "not_applicable"}


def _input(data: bytes, name: str = "img") -> EvidenceInput:
    return EvidenceInput(name, data, sha256_hex(data), name)


def _check(result: AnalysisResult) -> AnalysisResult:
    assert result.status in STATUSES
    assert result.interpretation and result.limitations and result.findings
    assert {f.name for f in fields(AnalysisResult)} >= {"analysis_type", "status", "measurements", "findings", "interpretation", "limitations", "timestamp"}
    for f in result.findings:
        assert isinstance(f, Finding) and all([f.finding, f.evidence, f.interpretation, f.limitation])
        assert f.kind in {"observation", "indicator", "verification"}
    for value in result.measurements.values():
        assert value is None or isinstance(value, (str, int, float, bool))
    if result.status == "indicator_detected":
        assert any(f.kind == "indicator" for f in result.findings)
    return result


@pytest.fixture
def clean(natural):
    return _input(encode_png(natural), "clean.png")


def test_clean_image_baseline(clean):
    assert _check(MetadataAnalyzer().analyze(clean)).status == "no_indicator"
    integrity = _check(IntegrityAnalyzer().analyze(clean))
    assert integrity.status == "no_indicator" and integrity.measurements["hash_match"] is True
    assert any(f.kind == "verification" for f in integrity.findings)
    assert _check(SteganographyAnalyzer().analyze(clean)).status == "no_indicator"


def test_integrity_detects_changed_bytes(clean):
    tampered = EvidenceInput("x", clean.data + b"\x00", clean.sha256)
    result = _check(IntegrityAnalyzer().analyze(tampered))
    assert result.status == "indicator_detected" and result.measurements["hash_match"] is False


def test_metadata_indicators(natural):
    exif = Image.Exif()
    exif[0x010F], exif[0x0110], exif[0x0131], exif[0x0132] = "Canon", "EOS", "Editor 1.0", "2026:01:02 10:00:00"
    
    exif_ifd = {0x9003: "2026:01:01 09:00:00"}
    exif[0x8769] = exif_ifd

    buf = io.BytesIO()
    Image.fromarray(natural).save(buf, format="JPEG", quality=85, exif=exif)
    result = _check(MetadataAnalyzer().analyze(_input(buf.getvalue())))
    assert result.status == "indicator_detected"
    titles = {f.finding for f in result.findings}
    assert {"Processing software recorded", "File modification time differs from capture time", "Capture device recorded"} <= titles
    jpeg = _check(IntegrityAnalyzer().analyze(_input(buf.getvalue())))
    assert jpeg.measurements["jpeg_quality_estimate"] == 85
    assert "does not establish manipulation" in next(f.limitation for f in jpeg.findings if f.finding == "Image is JPEG compressed")


def test_steganalysis_and_comparison_on_stego(natural, clean):
    stego = _input(encode_png(lsb.embed_text(natural, "x" * 2000)), "stego.png")
    assert _check(SteganographyAnalyzer().analyze(stego)).status == "indicator_detected"
    cmp = _check(compare(clean, stego))
    assert cmp.status == "indicator_detected" and cmp.measurements["lsb_only"] is True
    assert set(cmp.data) == {"difference", "reference", "subject"}
    assert _check(compare(clean, clean)).status == "verified"
    small = _input(encode_png(natural[:64, :64]))
    assert _check(compare(clean, small)).status == "not_applicable"


def test_watermark_statuses(natural, clean):
    marked = _input(encode_png(dct_watermark.embed(natural, "owner", "k")), "wm.png")
    verified = _check(WatermarkAnalyzer("dct", "k", "owner", reference=clean).analyze(marked))
    assert verified.status == "verified" and verified.measurements["reference_psnr_db"] > 38
    assert "key" not in verified.measurements and verified.measurements["key_supplied"] is True
    assert _check(WatermarkAnalyzer("dct", "k", "other").analyze(marked)).status == "indicator_detected"
    assert _check(WatermarkAnalyzer("dct", "wrong").analyze(marked)).status == "no_indicator"
    tiny = _input(encode_png(natural[:64, :64]))
    assert _check(WatermarkAnalyzer("dct").analyze(tiny)).status == "not_applicable"
    with pytest.raises(ValueError):
        WatermarkAnalyzer("wavelet_packet")  # not a registered method


def test_every_registered_watermark_scheme_has_an_analyzer_label():
    """Adding a scheme to robustness.SCHEMES without a label made WatermarkAnalyzer raise KeyError (HTTP 500)."""
    from analysis.watermarking.analyzer import METHOD_LABEL
    from analysis.watermarking.robustness import SCHEMES

    assert set(SCHEMES) <= set(METHOD_LABEL)


def test_dwt_watermark_analysis_statuses(natural, clean):
    from analysis.watermarking import dwt_watermark

    marked = _input(encode_png(dwt_watermark.embed(natural, "owner", "k")), "dwt.png")
    verified = _check(WatermarkAnalyzer("dwt", "k", "owner", reference=clean).analyze(marked))
    assert verified.status == "verified" and verified.measurements["method"] == "dwt"
    assert "DWT-domain" in verified.findings[0].finding and verified.measurements["reference_psnr_db"] > 35
    assert _check(WatermarkAnalyzer("dwt", "k", "other").analyze(marked)).status == "indicator_detected"
    assert _check(WatermarkAnalyzer("dwt", "wrong").analyze(marked)).status == "no_indicator"
    assert _check(WatermarkAnalyzer("dct", "k").analyze(marked)).status == "no_indicator"  # wrong method for this mark
    tiny = _input(encode_png(natural[:32, :32]))  # 256 carriers < the 504 DWT needs
    assert _check(WatermarkAnalyzer("dwt").analyze(tiny)).status == "not_applicable"


@pytest.mark.parametrize("method", ["", "DWT", "dwt2", "wavelet_packet", "lsb"])
def test_unsupported_watermark_methods_are_still_rejected(method):
    with pytest.raises(ValueError, match="Unknown watermark method"):
        WatermarkAnalyzer(method)
