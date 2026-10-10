"""Sweep requests are validated before any work or any artifact exists.

A multi-method sweep embeds one watermarked artifact per method. Every embed records a derived artifact,
a provenance record and a timeline event, so an invalid request that failed part-way used to leave the
earlier embeds behind. These tests check that an invalid request changes nothing, and that the point
count of a sweep is bounded.
"""

import json

import pytest

from analysis.core import encode_png
from analysis.watermarking import robustness
from analysis.watermarking.attacks import ATTACKS
from analysis.watermarking.robustness import MAX_SWEEP_POINTS, default_sweep, sweep_values
from tests.conftest import natural_image, upload

MSG, KEY = "VERIDIA", "k"
ALL = ["spatial_lsb", "dct", "dwt"]


def _state(client, eid):
    e = client.get(f"/api/evidence/{eid}").json()
    return {k: len(e[k]) for k in ("derived_artifacts", "provenance", "timeline", "analyses")}


def _sweep(client, image_id, **body):
    payload = {"image_id": image_id, "method": "dct", "message": MSG, "key": KEY, **body}
    return client.post("/api/watermark/sweep", json=payload)


# ---- the point-count bound -----------------------------------------------------------------------------

@pytest.mark.parametrize("args, count", [
    (("jpeg", 10, 100, 10), 10),
    (("jpeg", 5, 100, 1), 96),
    (("jpeg", 50, 50, 1), 1),            # a single point
    (("noise", 0, 1, 0.1), 11),          # no accumulated float error in the values
    (("brightness", 0, 99, 1), MAX_SWEEP_POINTS),  # exactly at the limit
])
def test_sweep_values_accepts_reasonable_requests(args, count):
    assert len(sweep_values(*args)) == count


def test_sweep_values_are_free_of_float_accumulation():
    assert sweep_values("noise", 0, 1, 0.1) == [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    assert sweep_values("jpeg", 10, 100, 10)[-1] == 100.0


@pytest.mark.parametrize("args, fragment", [
    (("jpeg", 10, 100, 0), "positive"),
    (("jpeg", 10, 100, -5), "positive"),
    (("jpeg", 10, 100, 0.0001), "maximum is"),                      # 900,001 points
    (("jpeg", 5, 100, 0.5), "maximum is"),                          # 191 points
    (("brightness", 0, 100, 1), "maximum is"),                      # 101 points: one over the limit
    (("jpeg", 10, 100, float("nan")), "finite"),
    (("jpeg", float("-inf"), 100, 1), "finite"),
    (("jpeg", 10, float("inf"), 1), "finite"),
    (("jpeg", 50, 10, 1), "must not exceed"),
    (("jpeg", 0, 100, 10), "between 5 and 100"),                    # JPEG quality below the attack minimum
    (("jpeg", 10, 500, 10), "between 5 and 100"),                   # and above its maximum
    (("rotate", 0, 90, 10), "between -45 and 45"),
    (("shear", 1, 2, 1), "Unknown attack"),
])
def test_sweep_values_rejects_unreasonable_requests(args, fragment):
    with pytest.raises(ValueError, match=fragment):
        sweep_values(*args)


def test_the_point_limit_is_documented_in_one_place():
    assert MAX_SWEEP_POINTS == 100
    assert "MAX_SWEEP_POINTS" in open(robustness.__file__, encoding="utf-8").read()


@pytest.mark.parametrize("attack", sorted(ATTACKS))
def test_every_attacks_default_sweep_is_valid_and_bounded(attack):
    start, stop, step = default_sweep(attack)
    values = sweep_values(attack, start, stop, step)
    assert 2 <= len(values) <= MAX_SWEEP_POINTS
    assert values[0] == pytest.approx(ATTACKS[attack].minimum if attack != "jpeg" else 10)
    assert default_sweep("jpeg") == (10.0, 100.0, 10.0)


# ---- API: accepted ---------------------------------------------------------------------------------------

def test_api_accepts_default_and_explicit_ranges(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    default = _sweep(client, eid).json()
    assert [r["parameter"] for r in default["series"][0]["rows"]] == [float(q) for q in range(10, 101, 10)]
    fine = _sweep(client, eid, start=70, stop=100, step=1).json()
    assert len(fine["series"][0]["rows"]) == 31


@pytest.mark.parametrize("attack", ["noise", "rotate", "contrast", "crop", "brightness", "rescale"])
def test_api_sweeps_attacks_other_than_jpeg_over_their_own_range(client, natural_png, attack):
    """Regression: the default range used to be JPEG's (10..100), which every other attack rejected."""
    eid = upload(client, natural_png)["evidence_id"]
    r = _sweep(client, eid, attack=attack)
    assert r.status_code == 200, r.text
    rows = r.json()["series"][0]["rows"]
    spec = ATTACKS[attack]
    assert rows[0]["parameter"] == pytest.approx(spec.minimum) and rows[-1]["parameter"] == pytest.approx(spec.maximum)


# ---- API: rejected, with nothing created -----------------------------------------------------------------

BAD_REQUESTS = [
    ("message too long for DCT and DWT", {"message": "x" * 20}, 422),
    ("JPEG quality below the minimum", {"start": 0}, 422),
    ("JPEG quality above the maximum", {"stop": 500}, 422),
    ("negative step", {"step": -1}, 422),
    ("zero step", {"step": 0}, 422),
    ("excessively small step", {"step": 0.0001}, 422),
    ("one point over the limit", {"attack": "brightness", "start": 0, "stop": 100, "step": 1}, 422),
    ("start greater than stop", {"start": 90, "stop": 10}, 422),
    ("unknown attack", {"attack": "shear"}, 422),
    ("rotation outside its range", {"attack": "rotate", "start": 0, "stop": 90, "step": 10}, 422),
]


@pytest.mark.parametrize("label, body, status", BAD_REQUESTS, ids=[b[0] for b in BAD_REQUESTS])
def test_invalid_multi_method_sweep_creates_no_artifacts(client, natural_png, label, body, status):
    eid = upload(client, natural_png)["evidence_id"]
    before = _state(client, eid)
    r = _sweep(client, eid, methods=ALL, **body)
    assert r.status_code == status, (label, r.text)
    assert _state(client, eid) == before, f"{label}: a rejected request left records behind"
    assert client.get(f"/api/provenance/{eid}/verify").json()["valid"] is True


@pytest.mark.parametrize("label, body, status", BAD_REQUESTS, ids=[b[0] for b in BAD_REQUESTS])
def test_invalid_single_image_sweep_is_rejected_and_records_nothing(client, natural_png, label, body, status):
    eid = upload(client, natural_png)["evidence_id"]
    art = client.post("/api/watermark/embed", json={"evidence_id": eid, "method": "dct", "message": MSG, "key": KEY}).json()["artifact"]["image_id"]
    before = _state(client, eid)
    assert _sweep(client, art, **body).status_code == status
    assert _state(client, eid) == before


def test_non_finite_numbers_are_rejected_at_the_schema(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    before = _state(client, eid)
    for field in ("start", "stop", "step"):
        raw = json.dumps({"image_id": eid, "method": "dct", "message": MSG, "methods": ALL}).rstrip("}") + f', "{field}": NaN}}'
        r = client.post("/api/watermark/sweep", content=raw, headers={"Content-Type": "application/json"})
        assert r.status_code == 422, field
    assert _state(client, eid) == before


def test_sweep_fails_before_embedding_when_one_method_cannot_carry_the_image(client, png_bytes):
    """64x64 has room for the spatial and DWT marks but too few 8x8 blocks for DCT; the spatial embed must not be kept."""
    eid = upload(client, png_bytes, "small.png")["evidence_id"]
    before = _state(client, eid)
    r = _sweep(client, eid, methods=ALL)
    assert r.status_code == 422 and "DCT" in r.json()["detail"] and "too small" in r.json()["detail"]
    assert _state(client, eid) == before


def test_sweep_rejects_an_attack_this_image_cannot_take_before_embedding(client):
    """A true crop leaves too little of a tiny image; that is discovered from the pixels, still before any embed."""
    eid = upload(client, encode_png(natural_image(30, 30)), "tiny.png")["evidence_id"]  # big enough for the spatial mark only
    before = _state(client, eid)
    r = _sweep(client, eid, methods=["spatial_lsb"], attack="crop_resync")
    assert r.status_code == 422 and "too little" in r.json()["detail"]
    assert _state(client, eid) == before


def test_unknown_image_is_404_and_creates_nothing(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    before = _state(client, eid)
    assert _sweep(client, "ev_" + "0" * 32, methods=ALL).status_code == 404
    assert _sweep(client, "art_" + "0" * 32).status_code == 404
    assert _state(client, eid) == before


def test_compare_methods_is_all_or_nothing(client, png_bytes):
    eid = upload(client, png_bytes, "small.png")["evidence_id"]
    before = _state(client, eid)
    r = client.post("/api/watermark/compare-methods", json={"evidence_id": eid, "message": MSG, "key": KEY})
    assert r.status_code == 422
    assert _state(client, eid) == before


# ---- successful operations keep their provenance behaviour -------------------------------------------------

def test_valid_multi_method_sweep_still_records_one_artifact_per_method(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    r = _sweep(client, eid, methods=ALL)
    assert r.status_code == 200 and [s["method"] for s in r.json()["series"]] == ALL
    after = _state(client, eid)
    assert after["derived_artifacts"] == 3 and after["provenance"] == 3 and after["timeline"] == 3 + 3  # acquisition events + 3 embeds
    evidence = client.get(f"/api/evidence/{eid}").json()
    assert sorted(a["operation"] for a in evidence["derived_artifacts"]) == ["dct_watermark_embed", "dwt_watermark_embed", "watermark_embed"]
    assert all(a["parent_image_id"] == eid for a in evidence["derived_artifacts"])
    assert client.get(f"/api/provenance/{eid}/verify").json()["valid"] is True


def test_duplicate_methods_are_collapsed(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    r = _sweep(client, eid, methods=["dct", "dct", "dwt"])
    assert [s["method"] for s in r.json()["series"]] == ["dct", "dwt"]
    assert _state(client, eid)["derived_artifacts"] == 2


def test_non_finite_numbers_anywhere_are_a_422_not_a_server_error(client, natural_png):
    """The default validation response echoed the rejected value, and NaN/Infinity cannot be JSON-encoded."""
    eid = upload(client, natural_png)["evidence_id"]
    raw = json.dumps({"evidence_id": eid, "method": "dct", "message": MSG}).rstrip("}") + ', "strength": Infinity}'
    r = client.post("/api/watermark/embed", content=raw, headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    errors = r.json()["detail"]
    assert errors and all(set(e) == {"loc", "msg", "type"} for e in errors)
    assert "strength" in errors[0]["loc"]
