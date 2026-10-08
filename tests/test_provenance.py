"""Evidence creation, derived artifacts, parent-child links, timeline and recorded investigation analyses."""

import hashlib


def _upload(client, data, name="scene.png"):
    return client.post("/api/evidence/upload", files={"file": (name, data, "image/png")}).json()


def _evidence(client, evidence_id):
    return client.get(f"/api/evidence/{evidence_id}").json()


def test_evidence_creation_records_acquisition(client, natural_png):
    ev = _upload(client, natural_png)
    assert ev["sha256"] == hashlib.sha256(natural_png).hexdigest()
    assert [e["event_type"] for e in ev["timeline"]] == ["evidence_acquired", "metadata_extracted", "hash_computed"]
    assert ev["timeline"][2]["description"].endswith(ev["sha256"])
    assert ev["derived_artifacts"] == [] and ev["analyses"] == []


def test_derived_artifact_chain_and_original_unchanged(client, natural_png):
    ev = _upload(client, natural_png)
    eid = ev["evidence_id"]
    wm = client.post("/api/watermark/embed", json={"evidence_id": eid, "method": "dct", "message": "owner", "key": "k"}).json()["artifact"]
    att = client.post("/api/watermark/attack", json={"image_id": wm["image_id"], "method": "dct", "attack": "jpeg",
                                                     "parameter": 75, "message": "owner", "key": "k"}).json()["artifact"]
    derived = {d["artifact_id"]: d for d in _evidence(client, eid)["derived_artifacts"]}
    assert derived[wm["image_id"]]["parent_image_id"] == eid and derived[wm["image_id"]]["parent_sha256"] == ev["sha256"]
    assert derived[att["image_id"]]["parent_image_id"] == wm["image_id"] and derived[att["image_id"]]["parent_sha256"] == wm["sha256"]
    assert derived[att["image_id"]]["operation"] == "attack"
    for artifact_id, d in derived.items():
        assert hashlib.sha256(client.get(f"/api/images/{artifact_id}").content).hexdigest() == d["sha256"]

    original = client.get(f"/api/images/{eid}").content
    assert original == natural_png  # never overwritten
    record = client.post(f"/api/investigation/{eid}/analyses", json={"type": "integrity"}).json()
    assert record["result"]["measurements"]["hash_match"] is True

    events = [e["event_type"] for e in _evidence(client, eid)["timeline"]]
    assert events.count("artifact_created") == 2 and events[-1] == "analysis_completed"


def test_pipeline_on_derived_image(client, natural_png):
    eid = _upload(client, natural_png)["evidence_id"]
    stego = client.post("/api/steganography/embed", json={"evidence_id": eid, "payload": "x" * 3000}).json()["artifact"]
    records = client.post(f"/api/investigation/{eid}/pipeline", json={
        "subject_id": stego["image_id"], "watermark": {"method": "dct", "key": "k", "expected_message": "owner"},
    }).json()
    by_type = {r["result"]["analysis_type"]: r for r in records}
    assert list(by_type) == ["metadata", "integrity", "steganalysis", "watermark", "comparison"]
    assert by_type["steganalysis"]["result"]["status"] == "indicator_detected"
    assert by_type["watermark"]["result"]["status"] == "no_indicator"
    assert by_type["comparison"]["reference_image_id"] == eid and by_type["comparison"]["result"]["measurements"]["lsb_only"]
    assert all(r["subject_image_id"] == stego["image_id"] and r["subject_sha256"] == stego["sha256"] for r in records)

    ev = _evidence(client, eid)
    assert len(ev["analyses"]) == 5
    analysis_events = [e for e in ev["timeline"] if e["event_type"] == "analysis_completed"]
    assert {e["reference_id"] for e in analysis_events} == {r["record_id"] for r in records}
    timestamps = [e["timestamp"] for e in ev["timeline"]]
    assert timestamps == sorted(timestamps)


def test_images_from_other_evidence_are_rejected(client, natural_png, png_bytes):
    first = _upload(client, natural_png)["evidence_id"]
    second = _upload(client, png_bytes, "other.png")["evidence_id"]
    r = client.post(f"/api/investigation/{first}/analyses", json={"type": "comparison", "subject_id": second})
    assert r.status_code == 422
    assert client.post(f"/api/investigation/{first}/analyses", json={"type": "bogus"}).status_code == 422
