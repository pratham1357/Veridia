"""Error Level Analysis: error computation, block statistics, clusters, analyzer statuses and API."""

import io

import numpy as np
import pytest
from PIL import Image

from analysis.core import EvidenceInput, encode_png, sha256_hex
from analysis.integrity.ela import (
    ELAAnalyzer,
    Z_THRESHOLD,
    block_means,
    block_size_for,
    clusters,
    ela_map,
    error_level_analysis,
    recompression_error,
)
from tests.conftest import natural_image, upload

REGION = (slice(16, 80), slice(160, 224))  # 64x64 px = blocks rows 1-4, cols 10-13


def _jpeg(pixels, quality):
    buf = io.BytesIO()
    Image.fromarray(pixels).save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _decode(data):
    with Image.open(io.BytesIO(data)) as img:
        return np.array(img.convert("RGB"))


def _spliced() -> np.ndarray:
    """A JPEG q75 image with a 64x64 region pasted in from a never-compressed source."""
    base = _decode(_jpeg(natural_image(256, 256, 7), 75))
    rng = np.random.default_rng(1)
    donor = np.clip(natural_image(256, 256, 99)[::-1, ::-1].astype(int) + rng.normal(0, 6, (256, 256, 3)), 0, 255).astype(np.uint8)
    base[REGION] = donor[REGION]
    return base


def _input(pixels: np.ndarray) -> EvidenceInput:
    data = encode_png(pixels)
    return EvidenceInput("img", data, sha256_hex(data))


def test_recompression_error_basics(natural):
    error = recompression_error(natural, 90)
    assert error.shape == natural.shape[:2] and error.min() >= 0
    assert np.array_equal(error, recompression_error(natural, 90))  # deterministic
    with pytest.raises(ValueError):
        recompression_error(natural, 30)
    image, peak = ela_map(natural, 90)
    assert image.dtype == np.uint8 and image.max() == 255 and peak == int(error.max())


def test_block_geometry():
    assert block_size_for(256, 256) == 16
    assert block_size_for(4000, 3000) % 8 == 0 and 4000 // block_size_for(4000, 3000) <= 64
    means = block_means(np.arange(64, dtype=float).reshape(8, 8), 4)
    assert means.shape == (2, 2) and means[0, 0] == np.arange(64).reshape(8, 8)[:4, :4].mean()


def test_clusters_are_four_connected():
    mask = np.zeros((6, 6), bool)
    mask[0:2, 0:2] = True  # 4 blocks
    mask[4, 4] = True
    mask[3, 3] = True  # diagonal to (4,4): separate cluster
    found = clusters(mask)
    assert [c["blocks"] for c in found] == [4, 1, 1]
    assert found[0] == {"blocks": 4, "row": 0, "col": 0, "rows": 2, "cols": 2}


@pytest.mark.parametrize("resave", [None, 95])
def test_spliced_region_is_flagged(resave):
    pixels = _spliced()
    if resave:
        pixels = _decode(_jpeg(pixels, resave))
    ela = error_level_analysis(pixels, 90)
    z = np.array(ela["block_z"])
    assert (z[1:5, 10:14] > Z_THRESHOLD).all()  # every block of the pasted region
    assert any(c["row"] <= 1 and c["col"] <= 10 and c["row"] + c["rows"] >= 5 and c["col"] + c["cols"] >= 14 for c in ela["clusters"])


def test_unspliced_image_does_not_flag_that_region():
    z = np.array(error_level_analysis(_decode(_jpeg(natural_image(256, 256, 7), 75)), 90)["block_z"])
    assert not (z[1:5, 10:14] > Z_THRESHOLD).any()


def test_analyzer_result_structure():
    result = ELAAnalyzer(90).analyze(_input(_spliced()))
    assert result.analysis_type == "ela" and result.status == "indicator_detected"
    assert result.measurements["outlier_blocks"] >= 16 and result.measurements["quality"] == 90
    assert [f.kind for f in result.findings] == ["observation", "indicator"]
    assert any("Experimental" in limitation for limitation in result.limitations)
    assert len(result.data["block_z"]) == 16 and len(result.data["block_z"][0]) == 16


def test_analyzer_not_applicable_and_inconclusive():
    tiny = ELAAnalyzer().analyze(_input(np.full((40, 40, 3), 128, np.uint8)))
    assert tiny.status == "not_applicable"
    flat = ELAAnalyzer().analyze(_input(np.full((128, 128, 3), 128, np.uint8)))  # recompression changes nothing
    assert flat.status == "inconclusive"
    with pytest.raises(ValueError):
        ELAAnalyzer(100)


def test_ela_api(client):
    eid = upload(client, encode_png(_spliced()), "spliced.png")["evidence_id"]
    r = client.get(f"/api/analysis/ela/{eid}?quality=90")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and int(r.headers["x-ela-peak"]) > 0
    assert client.get(f"/api/analysis/ela/{eid}?quality=20").status_code == 422

    record = client.post(f"/api/investigation/{eid}/analyses", json={"type": "ela", "ela_quality": 85}).json()
    assert record["result"]["analysis_type"] == "ela" and record["result"]["measurements"]["quality"] == 85
    assert record["result"]["status"] == "indicator_detected"

    records = client.post(f"/api/investigation/{eid}/pipeline", json={"include_ela": True}).json()
    assert [r["result"]["analysis_type"] for r in records] == ["metadata", "integrity", "ela", "steganalysis"]
    assert client.get(f"/api/provenance/{eid}/verify").json()["valid"]
