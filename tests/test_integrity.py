import io

import numpy as np
import pytest
from PIL import Image

from analysis.core import encode_png
from analysis.integrity.compression import blockiness, estimate_quality, jpeg_info, scaled_table, STD_LUMINANCE
from analysis.metrics import channel_histograms, channel_statistics, difference_statistics, luminance


def _jpeg(pixels, quality):
    buf = io.BytesIO()
    Image.fromarray(pixels).save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _decode(data):
    with Image.open(io.BytesIO(data)) as img:
        return np.array(img.convert("RGB"))


def test_channel_statistics_known_values():
    px = np.zeros((2, 2, 3), np.uint8)
    px[..., 0] = [[0, 10], [20, 30]]
    px[..., 1] = 100
    px[..., 2] = [[255, 255], [0, 0]]
    stats = {s["channel"]: s for s in channel_statistics(px)}
    assert stats["red"] == {"channel": "red", "mean": 15.0, "std": pytest.approx(np.std([0, 10, 20, 30])), "min": 0, "max": 30}
    assert stats["green"]["std"] == 0.0 and stats["blue"]["max"] == 255
    assert stats["gray"]["min"] == luminance(px).min()
    hist = channel_histograms(px)
    assert set(hist) == {"red", "green", "blue", "gray"} and all(sum(h) == 4 for h in hist.values())
    assert hist["green"][100] == 4


def test_difference_statistics():
    a = np.zeros((4, 4, 3), np.uint8)
    b = a.copy()
    b[0, 0, 0] = 1
    b[1, 1] = [3, 0, 0]
    d = difference_statistics(a, b)
    assert d["changed_pixels"] == 2 and d["total_pixels"] == 16 and d["changed_fraction"] == 2 / 16
    assert d["max_abs_difference"] == 3 and not d["lsb_only"]
    assert d["changed_samples_per_channel"] == {"red": 2, "green": 0, "blue": 0}
    assert difference_statistics(a, a)["changed_pixels"] == 0


def test_jpeg_quality_estimate(natural):
    for quality in (95, 80, 50, 30):
        info = jpeg_info(_jpeg(natural, quality))
        assert info["quality_estimate_luminance"] == quality and info["standard_tables"]
        assert len(info["tables"][0]) == 64
    assert estimate_quality(scaled_table(STD_LUMINANCE, 63), STD_LUMINANCE) == (63, 0.0)


def test_jpeg_info_not_applicable_to_png(natural):
    assert jpeg_info(encode_png(natural)) is None


def test_blockiness_separates_block_structure(natural):
    clean = blockiness(natural)
    recompressed = blockiness(_decode(_jpeg(natural, 90)))
    assert clean == pytest.approx(1.0, abs=0.05)
    assert recompressed > 1.1 > clean
    assert blockiness(natural[:8, :8]) is None
