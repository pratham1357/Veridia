"""Steganalysis on a known clean image and known generated stego images (fixed fixture, not a general accuracy claim)."""

import numpy as np
import pytest

from analysis.steganography import histogram, lsb, lsb_analysis, steganalysis
from analysis.steganography.rs_analysis import rs_estimate


def _random_payload(pixels, rate):
    n = int(lsb.capacity_bytes(pixels) * rate)
    if n == 0:
        return pixels
    return lsb.embed(pixels, np.random.default_rng(5).integers(0, 256, n, dtype=np.uint8).tobytes())


def test_chi2_survival_function():
    assert histogram._chi2_sf(3.841, 1) == pytest.approx(0.05, abs=1e-3)
    assert histogram._chi2_sf(18.307, 10) == pytest.approx(0.05, abs=1e-3)
    assert histogram._chi2_sf(124.342, 100) == pytest.approx(0.05, abs=1e-3)
    assert histogram._chi2_sf(0, 5) == 1.0


def test_chi_square_on_equalised_and_skewed_histograms():
    equal = np.full(256, 100)
    assert histogram.chi_square_attack(equal)["p_value"] == pytest.approx(1.0)
    skewed = np.tile([150, 50], 128)
    assert histogram.chi_square_attack(skewed)["p_value"] < 1e-6
    assert histogram.chi_square_attack(np.zeros(256, int))["p_value"] is None


def test_clean_image(natural):
    r = steganalysis.report(natural)
    assert r["chi_square"]["p_value"] < 0.05
    assert r["chi_square"]["consistent_prefix_fraction"] == 0.0
    assert abs(r["rs_mean_estimate"]) < steganalysis.RS_THRESHOLD
    assert not r["veridia_lsb_header_found"]
    assert r["indicators"][0].startswith("No measurement exceeded")
    assert sum(r["histograms"]["red"]) == natural.shape[0] * natural.shape[1]


def test_partial_sequential_stego(natural):
    r = steganalysis.report(_random_payload(natural, 0.3))
    assert r["chi_square"]["consistent_prefix_fraction"] >= 0.3
    assert 0.15 < r["rs_mean_estimate"] < 0.45
    assert r["veridia_lsb_header_found"]
    text = " ".join(r["indicators"])
    assert "sequential" in text and "RS analysis" in text
    assert "detected" not in text.lower()


def test_full_capacity_stego(natural):
    r = steganalysis.report(_random_payload(natural, 1.0))
    assert r["chi_square"]["p_value"] > 0.95


def test_rs_tracks_embedding_rate(natural):
    estimates = [np.mean([rs_estimate(_random_payload(natural, rate)[..., c])["estimate"] for c in range(3)]) for rate in (0.0, 0.3, 0.6)]
    assert estimates[0] < estimates[1] < estimates[2]


def test_known_cover_comparison(natural):
    stego = lsb.embed_text(natural, "hello")
    c = lsb_analysis.compare_with_cover(natural, stego)
    assert c["lsb_only"] and c["max_abs_difference"] == 1
    assert c["last_changed_index"] < (8 + 5) * 8  # header + payload bits, sequential from sample 0
    assert lsb_analysis.compare_with_cover(natural, natural)["changed_samples"] == 0
    with pytest.raises(ValueError):
        lsb_analysis.compare_with_cover(natural, natural[:10])


def test_edge_cases():
    tiny = np.zeros((2, 2, 3), np.uint8)
    r = steganalysis.report(tiny)
    assert r["chi_square"]["p_value"] is None and r["rs_mean_estimate"] is None
    flat = np.full((32, 32, 3), 128, np.uint8)
    assert steganalysis.report(flat)["channels"][0]["entropy_bits"] == 0.0
