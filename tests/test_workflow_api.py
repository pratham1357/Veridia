"""End-to-end: upload -> LSB embed -> extract -> watermark -> verify -> compare."""

import hashlib


def _upload(client, png_bytes):
    return client.post("/api/evidence/upload", files={"file": ("cover.png", png_bytes, "image/png")}).json()


def test_stego_workflow(client, png_bytes):
    ev = _upload(client, png_bytes)
    r = client.post("/api/steganography/embed", json={"evidence_id": ev["evidence_id"], "payload": "meet at noon"})
    assert r.status_code == 200
    out = r.json()
    art = out["artifact"]
    assert out["capacity"]["payload_bytes"] == 12
    assert art["sha256"] != ev["sha256"]  # a modified image necessarily has a different hash
    assert out["record"]["input_sha256"] == ev["sha256"] and out["record"]["output_sha256"] == art["sha256"]
    assert "payload" not in out["record"]["parameters"]

    data = client.get(f"/api/images/{art['image_id']}?download=true")
    assert hashlib.sha256(data.content).hexdigest() == art["sha256"]
    assert "attachment" in data.headers["content-disposition"]

    got = client.post("/api/steganography/extract", json={"source_id": art["image_id"]}).json()
    assert got["found"] and got["payload"] == "meet at noon"
    clean = client.post("/api/steganography/extract", json={"source_id": ev["evidence_id"]}).json()
    assert clean["found"] is False

    assert client.get(f"/api/steganalysis/report/{art['image_id']}").json()["veridia_lsb_header_found"] is True
    assert client.get(f"/api/steganalysis/lsb-plane/{art['image_id']}/red").headers["content-type"] == "image/png"

    cmp = client.post("/api/analysis/compare", json={"original_id": ev["evidence_id"], "processed_id": art["image_id"]}).json()
    assert cmp["hashes_differ"] and cmp["metrics"]["mse"] > 0
    assert len(client.get(f"/api/evidence/{ev['evidence_id']}").json()["provenance"]) == 1


def test_stego_over_capacity_is_rejected(client, png_bytes):
    ev = _upload(client, png_bytes)
    r = client.post("/api/steganography/embed", json={"evidence_id": ev["evidence_id"], "payload": "x" * 2000})
    assert r.status_code == 422


def test_watermark_workflow(client, png_bytes):
    ev = _upload(client, png_bytes)
    r = client.post("/api/watermark/embed", json={"evidence_id": ev["evidence_id"], "message": "(c) team", "key": "s3"})
    assert r.status_code == 200
    art = r.json()["artifact"]
    assert r.json()["record"]["parameters"]["key_used"] is True
    v = client.post("/api/watermark/verify", json={"source_id": art["image_id"], "key": "s3", "expected_message": "(c) team"})
    assert v.json()["status"] == "verified"
    v = client.post("/api/watermark/verify", json={"source_id": ev["evidence_id"], "key": "s3"})
    assert v.json()["status"] == "not_found"


def test_unknown_ids_404(client):
    assert client.get("/api/evidence/nope").status_code == 404
    assert client.post("/api/steganography/extract", json={"source_id": "nope"}).status_code == 404
