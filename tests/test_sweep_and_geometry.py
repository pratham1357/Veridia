"""Geometric attacks (rotation, true crop) and the attack parameter sweep.

These record measured behaviour on the project's synthetic test image. A method
failing an attack is a valid outcome, so the assertions describe what was
measured rather than asserting that every mark must survive.
"""

import numpy as np
import pytest

from analysis.metrics import compare_images
from analysis.watermarking import dct_watermark as dc, dwt_watermark as dw, lsb_watermark as ls, robustness
from analysis.watermarking.attacks import ATTACKS, apply_attack, crop, crop_resync, rotate

MSG, KEY = "VERIDIA-2026", "k"


@pytest.fixture
def marked(natural):
    return {"spatial_lsb": ls.embed(natural, MSG, KEY), "dct": dc.embed(natural, MSG, KEY), "dwt": dw.embed(natural, MSG, KEY)}


# ---- geometric attacks -----------------------------------------------------------------------------

def test_new_attacks_are_registered_with_sane_ranges():
    for name in ("rotate", "crop_resync"):
        a = ATTACKS[name]
        assert a.presets and a.minimum < a.maximum
        assert all(a.minimum <= p <= a.maximum for p in a.presets)


def test_rotation_keeps_the_canvas_but_moves_content(natural):
    out = rotate(natural, 5)
    assert out.shape == natural.shape and out.dtype == np.uint8
    assert not np.array_equal(out, natural)
    assert np.array_equal(rotate(natural, 0), natural)  # identity at zero degrees


def test_crop_resync_differs_from_border_crop(natural):
    """crop() blanks a border in place; crop_resync() removes it and rescales, moving every pixel."""
    blanked, shifted = crop(natural, 0.1), crop_resync(natural, 0.1)
    assert blanked.shape == shifted.shape == natural.shape
    assert (blanked[:5] == 0).all()  # border blanked, content stays put
    assert not (shifted[:5] == 0).all()  # content pulled in from inside, nothing blanked
    assert not np.array_equal(blanked, shifted)
    with pytest.raises(ValueError, match="too little"):
        crop_resync(natural, 0.499)


def test_geometric_attacks_desynchronise_every_method(marked):
    """None of the three schemes resynchronises, so a true crop defeats all of them."""
    modules = {"spatial_lsb": ls, "dct": dc, "dwt": dw}
    for method, module in modules.items():
        attacked = apply_attack(marked[method], "crop_resync", 0.1)
        assert module.verify(attacked, KEY, MSG).status == "not_found", f"{method} unexpectedly survived a true crop"
    for method, module in modules.items():
        attacked = apply_attack(marked[method], "rotate", 5)
        assert module.verify(attacked, KEY, MSG).status == "not_found", f"{method} unexpectedly survived a 5 degree rotation"


# ---- sweep ------------------------------------------------------------------------------------------

def test_jpeg_sweep_covers_the_documented_range(marked):
    rows = robustness.sweep(marked["dct"], "dct", MSG, KEY)
    assert [r["parameter"] for r in rows] == [float(q) for q in range(10, 101, 10)]
    assert all(r["attack"] == "jpeg" for r in rows)
    assert all(0.0 <= r["bit_error_rate"] <= 1.0 for r in rows)
    assert all("psnr_db" in r and "ssim" in r for r in rows)  # quality metrics recorded per step


def test_sweep_degrades_as_the_attack_gets_harsher(marked):
    """Heavier JPEG must not produce a *lower* error rate than the mildest setting."""
    rows = robustness.sweep(marked["dwt"], "dwt", MSG, KEY)
    worst, best = rows[0], rows[-1]  # quality 10 vs quality 100
    assert best["bit_error_rate"] <= worst["bit_error_rate"]
    assert best["status"] == "verified"  # quality 100 is near lossless


def test_sweep_accepts_other_attacks_and_rejects_bad_input(marked):
    rows = robustness.sweep(marked["dct"], "dct", MSG, KEY, attack="noise", start=0, stop=10, step=5)
    assert [r["parameter"] for r in rows] == [0.0, 5.0, 10.0]
    assert rows[0]["status"] == "verified"  # sigma 0 is a no-op
    for kwargs in ({"attack": "nope"}, {"step": 0}, {"start": 50, "stop": 10}):
        with pytest.raises(ValueError):
            robustness.sweep(marked["dct"], "dct", MSG, KEY, **kwargs)


def test_sweep_quality_metrics_are_measured_against_the_marked_image(marked):
    rows = robustness.sweep(marked["dct"], "dct", MSG, KEY, attack="noise", start=0, stop=0, step=1)
    assert rows[0]["psnr_db"] is None and rows[0]["ssim"] == pytest.approx(1.0)  # identical to its input
    assert compare_images(marked["dct"], marked["dct"])["mse"] == 0.0


# ---- brightness presets ------------------------------------------------------------------------------

def test_brightness_presets_are_odd_so_they_test_the_mark_not_the_arithmetic():
    presets = ATTACKS["brightness"].presets
    assert presets and all(int(p) % 2 == 1 for p in presets)


def test_even_brightness_shifts_leave_every_lsb_alone(natural):
    """Documents why even presets would have flattered the spatial mark: the LSB plane is unchanged."""
    interior = natural[(natural > 2) & (natural < 253)]  # clipping aside
    assert interior.size
    for delta in (2, 20, -20):
        shifted = apply_attack(natural, "brightness", delta)
        unclipped = (natural.astype(int) + delta >= 0) & (natural.astype(int) + delta <= 255)
        assert np.array_equal((shifted & 1)[unclipped], (natural & 1)[unclipped])
    odd = apply_attack(natural, "brightness", 21)
    assert (odd & 1).tolist() != (natural & 1).tolist()


def test_spatial_mark_does_not_survive_the_brightness_presets_but_transform_marks_do(marked):
    modules = {"spatial_lsb": ls, "dct": dc, "dwt": dw}
    for delta in ATTACKS["brightness"].presets:
        status = {m: modules[m].verify(apply_attack(marked[m], "brightness", delta), KEY, MSG).status for m in modules}
        assert status == {"spatial_lsb": "not_found", "dct": "verified", "dwt": "verified"}, f"brightness {delta}: {status}"
    assert ls.bit_error_rate(apply_attack(marked["spatial_lsb"], "brightness", 25), MSG, KEY) > 0.9  # LSBs inverted, not just noisy
