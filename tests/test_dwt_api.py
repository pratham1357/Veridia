"""API: DWT embedding/verification, the sweep endpoint, sub-band view and three-way comparison."""

from analysis.watermarking.attacks import ATTACKS
from tests.conftest import upload

MSG, KEY = "VERIDIA", "k"


def _embed(client, evidence_id, method="dwt", **extra):
    return client.post("/api/watermark/embed", json={"evidence_id": evidence_id, "method": method, "message": MSG, "key": KEY, **extra})


def test_dwt_embed_records_provenance_and_verifies(client, natural_png):
    ev = upload(client, natural_png)
    eid = ev["evidence_id"]

    r = _embed(client, eid)
    assert r.status_code == 200
    body = r.json()
    assert body["record"]["operation"] == "dwt_watermark_embed"
    assert body["record"]["parameters"]["method"].startswith("one-level Haar")
    assert body["record"]["parameters"]["strength"] == 8.0
    assert "key" not in body["record"]["parameters"] and body["record"]["parameters"]["key_used"] is True
    assert body["record"]["metrics"]["psnr_db"] > 35
    art = body["artifact"]

    v = client.post("/api/watermark/verify", json={
        "source_id": art["image_id"], "method": "dwt", "key": KEY, "expected_message": MSG, "reference_id": eid,
    }).json()
    assert v["status"] == "verified" and v["bit_error_rate"] == 0.0
    assert v["parameters"]["domain"].startswith("one-level 2-D Haar")
    assert v["reference_metrics"]["psnr_db"] > 35

    # the mark is method- and key-specific
    assert client.post("/api/watermark/verify", json={"source_id": art["image_id"], "method": "dct", "key": KEY}).json()["status"] == "not_found"
    assert client.post("/api/watermark/verify", json={"source_id": art["image_id"], "method": "dwt", "key": "no"}).json()["status"] == "not_found"
    assert client.post("/api/watermark/verify", json={"source_id": eid, "method": "dwt", "key": KEY}).json()["status"] == "not_found"

    # the artifact is linked to the evidence and the chain still verifies
    evidence = client.get(f"/api/evidence/{eid}").json()
    assert [a["operation"] for a in evidence["derived_artifacts"]] == ["dwt_watermark_embed"]
    assert client.get(f"/api/provenance/{eid}/verify").json()["valid"] is True


def test_dwt_rejects_oversized_message(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    assert client.post("/api/watermark/embed", json={
        "evidence_id": eid, "method": "dwt", "message": "x" * 17, "key": KEY}).status_code == 422


def test_dwt_fits_smaller_images_than_dct(client, png_bytes):
    """One carrier per 2x2 pixels beats one bit per 8x8 block, so DWT needs a far smaller image."""
    eid = upload(client, png_bytes, "small.png")["evidence_id"]  # 64x64 = 1024 carriers but only 64 DCT blocks
    assert _embed(client, eid).status_code == 200
    dct = client.post("/api/watermark/embed", json={
        "evidence_id": eid, "method": "dct", "message": MSG, "key": KEY})
    assert dct.status_code == 422 and "too small" in dct.json()["detail"]


def test_dwt_rejects_images_below_its_own_minimum(client):
    from analysis.core import encode_png
    from tests.conftest import natural_image

    eid = upload(client, encode_png(natural_image(32, 32)), "tiny.png")["evidence_id"]  # 256 carriers < 504
    r = _embed(client, eid)
    assert r.status_code == 422 and "too small" in r.json()["detail"]


def test_sweep_endpoint_single_and_multi_method(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    art = _embed(client, eid).json()["artifact"]

    single = client.post("/api/watermark/sweep", json={
        "image_id": art["image_id"], "method": "dwt", "message": MSG, "key": KEY}).json()
    assert single["attack"] == "jpeg" and single["parameter_label"] == "quality"
    assert len(single["series"]) == 1 and single["series"][0]["method"] == "dwt"
    assert [row["parameter"] for row in single["series"][0]["rows"]] == [float(q) for q in range(10, 101, 10)]
    assert single["series"][0]["rows"][-1]["status"] == "verified"  # quality 100

    multi = client.post("/api/watermark/sweep", json={
        "image_id": eid, "method": "dwt", "message": MSG, "key": KEY,
        "methods": ["spatial_lsb", "dct", "dwt"]}).json()
    assert [s["method"] for s in multi["series"]] == ["spatial_lsb", "dct", "dwt"]
    # each method is embedded fresh, so every series has its own artifact
    assert len({s["image_id"] for s in multi["series"]}) == 3
    # the fragile spatial mark should not survive any JPEG quality in the range
    spatial = next(s for s in multi["series"] if s["method"] == "spatial_lsb")
    assert all(row["status"] != "verified" for row in spatial["rows"])

    evidence = client.get(f"/api/evidence/{eid}").json()
    assert len(evidence["derived_artifacts"]) == 4  # the first embed plus one per swept method
    assert client.get(f"/api/provenance/{eid}/verify").json()["valid"] is True


def test_sweep_rejects_unknown_attack_and_bad_range(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    art = _embed(client, eid).json()["artifact"]
    base = {"image_id": art["image_id"], "method": "dwt", "message": MSG, "key": KEY}
    assert client.post("/api/watermark/sweep", json={**base, "attack": "nope"}).status_code == 422
    assert client.post("/api/watermark/sweep", json={**base, "start": 90, "stop": 10}).status_code == 422
    assert client.post("/api/watermark/sweep", json={**base, "step": 0}).status_code == 422


def test_geometric_attacks_exposed_and_recorded(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    art = _embed(client, eid).json()["artifact"]
    catalogue = {a["name"]: a for a in client.get("/api/watermark/attacks").json()}
    assert {"rotate", "crop_resync"} <= set(catalogue)
    assert catalogue["rotate"]["parameter_label"] == "degrees"

    r = client.post("/api/watermark/attack", json={
        "image_id": art["image_id"], "method": "dwt", "attack": "rotate", "parameter": 5, "message": MSG, "key": KEY})
    assert r.status_code == 200
    assert r.json()["row"]["status"] == "not_found"  # no geometric resynchronisation
    assert r.json()["record"]["input_image_id"] == art["image_id"]
    assert client.post("/api/watermark/attack", json={
        "image_id": art["image_id"], "method": "dwt", "attack": "rotate", "parameter": 99,
        "message": MSG, "key": KEY}).status_code == 422


def test_subband_view_and_three_way_comparison(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    art = _embed(client, eid).json()["artifact"]
    for endpoint in (f"/api/watermark/dwt-map/{art['image_id']}", f"/api/watermark/dct-map/{art['image_id']}"):
        resp = client.get(endpoint)
        assert resp.status_code == 200 and resp.headers["content-type"] == "image/png"

    r = client.post("/api/watermark/compare-methods", json={"evidence_id": eid, "message": MSG, "key": KEY})
    assert r.status_code == 200
    methods = {m["method"]: m for m in r.json()["methods"]}
    assert set(methods) == {"spatial_lsb", "dct", "dwt"}
    assert all(m["verification"]["status"] == "verified" for m in methods.values())
    # every method is attacked with the same suite, so the rows line up for a side-by-side table
    counts = {m["method"]: len(m["robustness"]) for m in methods.values()}
    assert len(set(counts.values())) == 1
    assert counts["dwt"] == 1 + sum(len(a.presets) for a in ATTACKS.values())
    # the fragile spatial mark survives fewer attacks than the transform-domain ones
    survived = {k: sum(1 for row in m["robustness"] if row["attack"] != "none" and row["status"] == "verified")
                for k, m in methods.items()}
    assert survived["spatial_lsb"] < survived["dct"] and survived["spatial_lsb"] < survived["dwt"]


# ---- Investigation integration (regression: DWT used to raise KeyError -> HTTP 500) ------------------

def _dwt_artifact(client, eid):
    return _embed(client, eid).json()["artifact"]["image_id"]


def test_investigation_analysis_supports_dwt(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    art = _dwt_artifact(client, eid)
    r = client.post(f"/api/investigation/{eid}/analyses", json={
        "type": "watermark", "subject_id": art, "reference_id": eid,
        "watermark": {"method": "dwt", "key": KEY, "expected_message": MSG}})
    assert r.status_code == 200
    result = r.json()["result"]
    assert result["status"] == "verified" and result["measurements"]["method"] == "dwt"
    assert result["measurements"]["bit_error_rate"] == 0.0 and result["measurements"]["reference_psnr_db"] > 35
    assert "key" not in result["measurements"]  # the key is used for extraction only, never recorded

    wrong = client.post(f"/api/investigation/{eid}/analyses", json={
        "type": "watermark", "subject_id": art, "watermark": {"method": "dwt", "key": "nope", "expected_message": MSG}})
    assert wrong.status_code == 200 and wrong.json()["result"]["status"] == "no_indicator"


def test_investigation_pipeline_supports_dwt_and_keeps_provenance_valid(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    art = _dwt_artifact(client, eid)
    r = client.post(f"/api/investigation/{eid}/pipeline", json={
        "subject_id": art, "watermark": {"method": "dwt", "key": KEY, "expected_message": MSG}})
    assert r.status_code == 200
    by_type = {rec["result"]["analysis_type"]: rec for rec in r.json()}
    assert by_type["watermark"]["result"]["status"] == "verified"
    assert {"metadata", "integrity", "steganalysis", "watermark", "comparison"} <= set(by_type)

    evidence = client.get(f"/api/evidence/{eid}").json()
    anchored = {e["reference_id"] for e in evidence["timeline"] if e["event_type"] == "analysis_completed"}
    assert anchored == {a["record_id"] for a in evidence["analyses"]}  # every analysis has its timeline event
    stamps = [e["timestamp"] for e in evidence["timeline"]]
    assert stamps == sorted(stamps)
    verification = client.get(f"/api/provenance/{eid}/verify").json()
    assert verification["valid"] is True and verification["issues"] == []


def test_investigation_still_rejects_unsupported_methods_and_records_nothing(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    art = _dwt_artifact(client, eid)
    before = client.get(f"/api/evidence/{eid}").json()
    for method in ("dwt2", "DWT", "wavelet"):
        wm = {"method": method, "key": KEY, "expected_message": MSG}
        assert client.post(f"/api/investigation/{eid}/analyses", json={"type": "watermark", "subject_id": art, "watermark": wm}).status_code == 422
        assert client.post(f"/api/investigation/{eid}/pipeline", json={"subject_id": art, "watermark": wm}).status_code == 422
    after = client.get(f"/api/evidence/{eid}").json()
    assert (len(after["analyses"]), len(after["timeline"])) == (len(before["analyses"]), len(before["timeline"]))
    assert client.get(f"/api/provenance/{eid}/verify").json()["valid"] is True


def test_compare_methods_strength_applies_to_dct_only(client, natural_png):
    """Regression (found in a real browser): the UI's 'DCT strength' slider value was also applied to DWT.

    DCT and DWT strengths are on different scales (defaults 25 and 8), so DWT was embedded ~3x too strongly and the
    comparison showed ~29 dB / SSIM 0.48 instead of its documented ~38 dB / ~0.9.
    """
    eid = upload(client, natural_png)["evidence_id"]
    r = client.post("/api/watermark/compare-methods", json={"evidence_id": eid, "message": MSG, "key": KEY, "strength": 50})
    assert r.status_code == 200
    by = {m["method"]: m for m in r.json()["methods"]}
    assert by["dct"]["record"]["parameters"]["strength"] == 50
    assert by["dwt"]["record"]["parameters"]["strength"] == 8.0  # its own default, not the DCT value
    assert "strength" not in by["spatial_lsb"]["record"]["parameters"]
    assert by["dwt"]["record"]["metrics"]["psnr_db"] > 35 and by["dwt"]["record"]["metrics"]["ssim"] > 0.85
    default = client.post("/api/watermark/compare-methods", json={"evidence_id": eid, "message": MSG, "key": KEY}).json()["methods"]
    assert {m["method"]: m["record"]["parameters"].get("strength") for m in default} == {"spatial_lsb": None, "dct": 25.0, "dwt": 8.0}
