import numpy as np
import pytest

from analysis.steganography import lsb, lsb_analysis


def test_round_trip_unicode(pixels):
    stego = lsb.embed_text(pixels, "Hello, VERIDIA — héllo ✓")
    assert lsb.extract_text(stego) == "Hello, VERIDIA — héllo ✓"


def test_only_lsbs_change_and_input_untouched(pixels):
    original = pixels.copy()
    stego = lsb.embed_text(pixels, "secret")
    assert np.array_equal(pixels, original)
    assert np.max(np.abs(stego.astype(int) - original.astype(int))) <= 1


def test_capacity_exceeded(pixels):
    cap = lsb.capacity_bytes(pixels)
    assert cap == 64 * 64 * 3 // 8 - 8
    lsb.embed(pixels, b"x" * cap)  # exactly full is allowed
    with pytest.raises(lsb.CapacityError):
        lsb.embed(pixels, b"x" * (cap + 1))


def test_empty_payload_rejected(pixels):
    with pytest.raises(lsb.LsbError):
        lsb.embed(pixels, b"")


def test_no_payload_in_clean_image(pixels):
    with pytest.raises(lsb.NoPayloadError):
        lsb.extract(pixels)


def test_capacity_report(pixels):
    report = lsb.capacity_report(pixels, 153)
    assert report["capacity_bytes"] == 1528
    assert report["utilization_percent"] == pytest.approx(10.0131, abs=1e-3)


def test_header_detection_and_plane(pixels):
    assert not lsb_analysis.has_veridia_header(pixels)
    stego = lsb.embed_text(pixels, "hi")
    assert lsb_analysis.has_veridia_header(stego)
    assert set(np.unique(lsb_analysis.lsb_plane_image(stego, "red"))) <= {0, 255}
