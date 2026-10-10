"""API workflows for DCT watermarking, attack experiments, method comparison and steganalysis."""

from analysis.watermarking.attacks import ATTACKS


def _upload(client, data, name="cover.png"):
    return client.post("/api/evidence/upload", files={"file": (name, data, "image/png")}).json()


def _dct_embed(client, evidence_id, message="VERIDIA-2026", key="k"):
    return client.post(
        "/api/watermark/embed", json={"evidence_id": evidence_id, "method": "dct", "message": message, "key": key}
    )


def test_dct_embed_verify_with_reference(client, natural_png):
    ev = _upload(client, natural_png)
    r = _dct_embed(client, ev["evidence_id"])
    assert r.status_code == 200
    art = r.json()["artifact"]
    assert r.json()["record"]["operation"] == "dct_watermark_embed"
    assert r.json()["record"]["parameters"]["strength"] == 25.0

    v = client.post("/api/watermark/verify", json={
        "source_id": art["image_id"], "method": "dct", "key": "k",
        "expected_message": "VERIDIA-2026", "reference_id": ev["evidence_id"],
    }).json()
    assert v["status"] == "verified" and v["bit_error_rate"] == 0.0
    assert v["reference_metrics"]["psnr_db"] > 38 and v["parameters"]["blocks"] == 1024

    wrong_method = client.post("/api/watermark/verify", json={"source_id": art["image_id"], "method": "spatial_lsb", "key": "k"})
    assert wrong_method.json()["status"] == "not_found"

    assert client.get(f"/api/watermark/dct-map/{art['image_id']}").headers["content-type"] == "image/png"
    diff = client.get(f"/api/analysis/difference/{ev['evidence_id']}/{art['image_id']}")
    assert diff.headers["content-type"] == "image/png" and int(diff.headers["x-max-difference"]) > 0


def test_dct_rejects_small_image(client, png_bytes):
    ev = _upload(client, png_bytes)  # 64x64: too few 8x8 blocks
    r = _dct_embed(client, ev["evidence_id"])
    assert r.status_code == 422 and "too small" in r.json()["detail"]
    v = client.post("/api/watermark/verify", json={"source_id": ev["evidence_id"], "method": "dct"}).json()
    assert v["status"] == "not_found" and "too small" in v["detail"]


def test_attack_experiment_and_provenance(client, natural_png):
    ev = _upload(client, natural_png)
    art = _dct_embed(client, ev["evidence_id"]).json()["artifact"]
    r = client.post("/api/watermark/attack", json={
        "image_id": art["image_id"], "method": "dct", "attack": "jpeg", "parameter": 75,
        "message": "VERIDIA-2026", "key": "k",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["row"]["status"] == "verified" and body["row"]["attack_label"] == "JPEG recompression"
    assert body["record"]["operation"] == "attack" and body["record"]["input_image_id"] == art["image_id"]
    chain = client.get(f"/api/evidence/{ev['evidence_id']}").json()["provenance"]
    assert [p["operation"] for p in chain] == ["dct_watermark_embed", "attack"]

    bad = client.post("/api/watermark/attack", json={"image_id": art["image_id"], "method": "dct",
                                                      "attack": "jpeg", "parameter": 0, "message": "x"})
    assert bad.status_code == 422


def test_robustness_suite_and_attack_catalogue(client, natural_png):
    ev = _upload(client, natural_png)
    art = _dct_embed(client, ev["evidence_id"]).json()["artifact"]
    rows = client.post("/api/watermark/robustness", json={
        "image_id": art["image_id"], "method": "dct", "message": "VERIDIA-2026", "key": "k",
    }).json()["rows"]
    assert len(rows) == 1 + sum(len(a.presets) for a in ATTACKS.values())
    assert {a["name"] for a in client.get("/api/watermark/attacks").json()} == set(ATTACKS)


def test_compare_methods(client, natural_png):
    ev = _upload(client, natural_png)
    r = client.post("/api/watermark/compare-methods", json={"evidence_id": ev["evidence_id"], "message": "VERIDIA", "key": "k"})
    assert r.status_code == 200
    methods = {m["method"]: m for m in r.json()["methods"]}
    assert set(methods) == {"spatial_lsb", "dct", "dwt"}
    assert all(m["verification"]["status"] == "verified" for m in methods.values())
    jpeg75 = {m: next(row for row in v["robustness"] if row["attack"] == "jpeg" and row["parameter"] == 75)["status"]
              for m, v in methods.items()}
    # measured on this fixture: the fragile spatial mark dies, both transform-domain marks survive
    assert jpeg75 == {"spatial_lsb": "not_found", "dct": "verified", "dwt": "verified"}
    too_long = client.post("/api/watermark/compare-methods", json={"evidence_id": ev["evidence_id"], "message": "x" * 17})
    assert too_long.status_code == 422


def test_steganalysis_endpoints(client, natural_png, png_bytes):
    ev = _upload(client, natural_png)
    stego = client.post("/api/steganography/embed", json={"evidence_id": ev["evidence_id"], "payload": "x" * 3000}).json()
    sid = stego["artifact"]["image_id"]

    clean = client.get(f"/api/steganalysis/report/{ev['evidence_id']}").json()
    suspect = client.get(f"/api/steganalysis/report/{sid}").json()
    assert clean["chi_square"]["consistent_prefix_fraction"] == 0.0
    assert suspect["chi_square"]["consistent_prefix_fraction"] > 0.0
    assert suspect["disclaimer"].startswith("These measurements may indicate")

    cmp = client.post("/api/steganalysis/cover-comparison", json={"cover_id": ev["evidence_id"], "suspect_id": sid}).json()
    assert cmp["lsb_only"] and cmp["changed_samples"] > 0

    other = _upload(client, png_bytes, "small.png")
    mismatch = client.post("/api/steganalysis/cover-comparison", json={"cover_id": other["evidence_id"], "suspect_id": sid})
    assert mismatch.status_code == 422
