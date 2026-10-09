"""Hash-chained timeline: chain construction and tamper detection, in pure functions and against stored records."""

import hashlib
import json
import os

import pytest

from analysis.core import decode_rgb, encode_png
from analysis.provenance import GENESIS, canonical_json, digest, entry_hash, verify_links
from app.services.store import store
from tests.conftest import upload


# ---- pure chain functions -------------------------------------------------------------------------

def _chain(n: int) -> list[dict]:
    entries, previous = [], GENESIS
    for i in range(n):
        e = {"sequence": i, "event_id": f"e{i}", "description": f"event {i}", "previous_hash": previous}
        e["hash"] = entry_hash(e)
        entries.append(e)
        previous = e["hash"]
    return entries


def test_canonical_json_is_order_independent_and_strict():
    assert canonical_json({"b": 1, "a": [1, 2]}) == canonical_json({"a": [1, 2], "b": 1}) == b'{"a":[1,2],"b":1}'
    assert canonical_json({"s": "é"}) == '{"s":"é"}'.encode()
    assert digest({"x": 1}) == hashlib.sha256(b'{"x":1}').hexdigest()
    with pytest.raises(ValueError):
        canonical_json({"x": float("nan")})


def test_intact_chain_verifies():
    chain = _chain(5)
    assert chain[0]["previous_hash"] == GENESIS
    assert verify_links(chain) == []
    assert verify_links(chain, expected_head=chain[-1]["hash"]) == []
    assert verify_links(chain, expected_head=chain[2]["hash"]) == []  # extended since: still valid


def test_modified_entry_is_detected():
    chain = _chain(5)
    chain[2]["description"] = "something else"
    issues = verify_links(chain)
    assert [(i.kind, i.sequence) for i in issues] == [("hash_mismatch", 2)]


def test_rehashed_entry_breaks_the_next_link():
    chain = _chain(5)
    chain[2]["description"] = "something else"
    chain[2]["hash"] = entry_hash(chain[2])  # attacker recomputes this entry only
    assert [(i.kind, i.sequence) for i in verify_links(chain)] == [("broken_link", 3)]


def test_removed_and_reordered_entries_are_detected():
    chain = _chain(5)
    removed = chain[:2] + chain[3:]
    assert {i.kind for i in verify_links(removed)} >= {"sequence_error", "broken_link"}
    swapped = [chain[0], chain[2], chain[1], chain[3], chain[4]]
    assert any(i.kind == "broken_link" for i in verify_links(swapped))


def test_truncation_needs_an_external_head():
    chain = _chain(5)
    truncated = chain[:3]
    assert verify_links(truncated) == []  # undetectable from the chain alone
    issues = verify_links(truncated, expected_head=chain[-1]["hash"])
    assert [i.kind for i in issues] == ["head_not_found"]


# ---- stored evidence ------------------------------------------------------------------------------

def _build(client, natural_png):
    ev = upload(client, natural_png)
    eid = ev["evidence_id"]
    stego = client.post("/api/steganography/embed", json={"evidence_id": eid, "payload": "hidden"}).json()["artifact"]
    client.post(f"/api/investigation/{eid}/pipeline", json={"subject_id": stego["image_id"]})
    return eid, stego


def _verify(client, eid, **params):
    r = client.get(f"/api/provenance/{eid}/verify", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _edit_record(storage, eid, change):
    path = storage / "evidence" / eid / "evidence.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    change(record)
    path.write_text(json.dumps(record), encoding="utf-8")
    store.open(storage)


def test_timeline_events_form_a_chain(client, natural_png):
    eid, _ = _build(client, natural_png)
    timeline = client.get(f"/api/evidence/{eid}").json()["timeline"]
    assert [e["sequence"] for e in timeline] == list(range(len(timeline)))
    assert timeline[0]["previous_hash"] == GENESIS
    assert all(b["previous_hash"] == a["hash"] for a, b in zip(timeline, timeline[1:]))
    assert all(e["content_hash"] for e in timeline)

    v = _verify(client, eid)
    assert v["valid"] and v["issues"] == [] and v["head_hash"] == timeline[-1]["hash"]
    assert v["event_count"] == len(timeline) and all(c["passed"] for c in v["checks"])
    assert {f["kind"] for f in v["files"]} == {"original", "derived"}


def test_verification_is_read_only(client, natural_png):
    eid, _ = _build(client, natural_png)
    before = client.get(f"/api/evidence/{eid}").json()["timeline"]
    _verify(client, eid)
    assert client.get(f"/api/evidence/{eid}").json()["timeline"] == before


def test_edited_analysis_result_is_detected(client, natural_png, storage):
    eid, _ = _build(client, natural_png)

    def soften(record):
        stego = next(a for a in record["analyses"] if a["result"]["analysis_type"] == "steganalysis")
        stego["result"]["status"] = "no_indicator"

    _edit_record(storage, eid, soften)
    v = _verify(client, eid)
    assert not v["valid"]
    assert [(i["check"], i["kind"]) for i in v["issues"]] == [("record_content", "content_mismatch")]
    assert v["first_invalid_sequence"] is not None


def test_edited_event_description_is_detected(client, natural_png, storage):
    eid, _ = _build(client, natural_png)
    _edit_record(storage, eid, lambda r: r["timeline"][1].update(description="Metadata extracted: nothing to see"))
    v = _verify(client, eid)
    assert [(i["kind"], i["sequence"]) for i in v["issues"]] == [("hash_mismatch", 1)]


def test_deleted_event_and_injected_record_are_detected(client, natural_png, storage):
    eid, _ = _build(client, natural_png)

    def delete_last_analysis_event(record):
        record["timeline"].pop(4)  # an analysis_completed event in the middle

    _edit_record(storage, eid, delete_last_analysis_event)
    kinds = {(i["check"], i["kind"]) for i in _verify(client, eid)["issues"]}
    assert ("links", "broken_link") in kinds and ("coverage", "unanchored_record") in kinds


def test_lineage_tampering_is_detected(client, natural_png, storage):
    eid, _ = _build(client, natural_png)
    _edit_record(storage, eid, lambda r: r["derived_artifacts"][0].update(parent_sha256="0" * 64))
    kinds = {(i["check"], i["kind"]) for i in _verify(client, eid)["issues"]}
    assert ("lineage", "lineage_mismatch") in kinds and ("record_content", "content_mismatch") in kinds


def test_modified_image_file_is_detected(client, natural_png, storage):
    eid, stego = _build(client, natural_png)
    path = storage / "evidence" / eid / "images" / f"{stego['image_id']}.png"
    pixels = decode_rgb(path.read_bytes())
    pixels[0, 0] ^= 1  # one imperceptible change, saved as a perfectly valid PNG
    os.chmod(path, 0o600)
    path.write_bytes(encode_png(pixels))

    v = _verify(client, eid)
    assert [(i["check"], i["kind"], i["record_id"]) for i in v["issues"]] == [("files", "file_mismatch", stego["image_id"])]
    # the integrity analyzer sees the same change on the bytes as they are now
    r = client.post(f"/api/investigation/{eid}/analyses", json={"type": "integrity", "subject_id": stego["image_id"]})
    assert r.json()["result"]["measurements"]["hash_match"] is False
    assert r.json()["result"]["status"] == "indicator_detected"


def test_truncation_detected_with_expected_head(client, natural_png, storage):
    eid, _ = _build(client, natural_png)
    head = _verify(client, eid)["head_hash"]

    def truncate(record):
        dropped = record["timeline"].pop()
        record["analyses"] = [a for a in record["analyses"] if a["record_id"] != dropped["reference_id"]]

    _edit_record(storage, eid, truncate)
    assert _verify(client, eid)["valid"]  # consistent on its own
    v = _verify(client, eid, expected_head=head)
    assert not v["valid"] and [i["kind"] for i in v["issues"]] == ["head_not_found"]
    assert client.get(f"/api/provenance/{eid}/verify", params={"expected_head": "xyz"}).status_code == 422
