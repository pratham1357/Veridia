import math

import numpy as np
import pytest

from analysis.metrics import compare_images, mse, psnr, ssim


def test_known_mse_and_psnr():
    a = np.zeros((8, 8, 3), dtype=np.uint8)
    b = a + 2  # every sample differs by 2 -> MSE 4
    assert mse(a, b) == 4.0
    assert psnr(a, b) == pytest.approx(10 * math.log10(255**2 / 4))


def test_identical_images():
    a = np.random.default_rng(0).integers(0, 256, (16, 16, 3), dtype=np.uint8)
    assert compare_images(a, a) == {"mse": 0.0, "psnr_db": None, "ssim": 1.0}


def test_ssim_decreases_with_distortion():
    a = np.random.default_rng(0).integers(0, 256, (32, 32, 3), dtype=np.uint8)
    noisy = np.clip(a.astype(int) + np.random.default_rng(1).integers(-40, 40, a.shape), 0, 255).astype(np.uint8)
    assert 0 < ssim(a, noisy) < 0.99


def test_shape_mismatch():
    with pytest.raises(ValueError):
        mse(np.zeros((4, 4, 3), np.uint8), np.zeros((5, 4, 3), np.uint8))
