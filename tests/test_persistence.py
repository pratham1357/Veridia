"""JSON + image-file persistence under storage/: layout, permissions, reload, damaged records, memory mode."""

import hashlib
import json
import stat

import pytest

from app.services import provenance
from app.services.errors import ServiceError
from app.services.store import store
from tests.conftest import upload


def _mode(path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _populate(client, natural_png):
    ev = upload(client, natural_png)
    eid = ev["evidence_id"]
    wm = client.post("/api/watermark/embed", json={"evidence_id": eid, "method": "dct", "message": "owner", "key": "k"}).json()
    client.post(f"/api/investigation/{eid}/pipeline", json={"subject_id": wm["artifact"]["image_id"]})
    return ev, wm["artifact"]


def test_layout_and_permissions(client, natural_png, storage):
    ev, art = _populate(client, natural_png)
    root = storage / "evidence" / ev["evidence_id"]
    original = root / "images" / f"{ev['evidence_id']}.png"
    derived = root / "images" / f"{art['image_id']}.png"

    assert original.read_bytes() == natural_png  # stored unmodified
    assert hashlib.sha256(derived.read_bytes()).hexdigest() == art["sha256"]
    assert _mode(original) == 0o400 and _mode(derived) == 0o400  # write-once, read-only
    assert _mode(root / "evidence.json") == 0o600 and _mode(root) == 0o700
    assert not list(root.rglob("*.tmp"))  # atomic replace leaves no temp files

    record = json.loads((root / "evidence.json").read_text())
    assert record["evidence_id"] == ev["evidence_id"]
    assert len(record["derived_artifacts"]) == 1 and len(record["analyses"]) == 4  # metadata, integrity, steganalysis, comparison
    assert record["timeline"][-1]["hash"] == client.get(f"/api/evidence/{ev['evidence_id']}").json()["timeline"][-1]["hash"]


def test_reload_restores_everything(client, natural_png, storage):
    ev, art = _populate(client, natural_png)
    before = client.get(f"/api/evidence/{ev['evidence_id']}").json()

    store.open(storage)  # simulates a backend restart
    after = client.get(f"/api/evidence/{ev['evidence_id']}").json()
    assert after == before
    assert client.get(f"/api/images/{ev['evidence_id']}").content == natural_png
    assert hashlib.sha256(client.get(f"/api/images/{art['image_id']}").content).hexdigest() == art["sha256"]
    assert [e["evidence_id"] for e in client.get("/api/evidence").json()] == [ev["evidence_id"]]

    verification = client.get(f"/api/provenance/{ev['evidence_id']}/verify").json()
    assert verification["valid"], verification["issues"]  # hashes survive the JSON round trip

    # work continues on the reloaded record and the chain keeps extending
    r = client.post(f"/api/investigation/{ev['evidence_id']}/analyses", json={"type": "integrity"})
    assert r.status_code == 200 and r.json()["result"]["measurements"]["hash_match"] is True
    assert client.get(f"/api/provenance/{ev['evidence_id']}/verify").json()["valid"]


def test_damaged_record_is_skipped_and_reported(client, natural_png, png_bytes, storage):
    good = upload(client, natural_png)
    bad = upload(client, png_bytes, "other.png")
    (storage / "evidence" / bad["evidence_id"] / "evidence.json").chmod(0o600)
    (storage / "evidence" / bad["evidence_id"] / "evidence.json").write_text("{not json")
    (storage / "evidence" / "not-an-id").mkdir()  # foreign entries are ignored
    (storage / "evidence" / "ev_../").mkdir(exist_ok=True)

    store.open(storage)
    assert [e["evidence_id"] for e in client.get("/api/evidence").json()] == [good["evidence_id"]]
    assert len(store.load_errors) == 1 and bad["evidence_id"] in store.load_errors[0]
    assert client.get("/api/health").json()["storage_load_errors"] == 1


def test_missing_image_file_is_reported_not_hidden(client, natural_png, storage):
    ev, art = _populate(client, natural_png)
    path = storage / "evidence" / ev["evidence_id"] / "images" / f"{art['image_id']}.png"
    path.unlink()
    store.open(storage)
    assert client.get(f"/api/images/{art['image_id']}").status_code == 410
    checks = {f["file_id"]: f["status"] for f in client.get(f"/api/provenance/{ev['evidence_id']}/verify").json()["files"]}
    assert checks[art["image_id"]] == "missing" and checks[ev["evidence_id"]] == "match"


def test_identifiers_never_form_paths(storage):
    with pytest.raises(ServiceError):
        store.report("ev_../../etc", "rep_x", "json")
    with pytest.raises(ServiceError):
        store.report("ev_" + "0" * 32, "../evidence", "html")


def test_memory_mode_writes_nothing(client, natural_png, tmp_path):
    store.open(None)
    ev = upload(client, natural_png)
    assert client.get(f"/api/images/{ev['evidence_id']}").content == natural_png
    assert provenance.verify(store.evidence(ev["evidence_id"])).valid
    assert client.get("/api/health").json()["storage"] == "memory"
    assert not (tmp_path / "storage" / "evidence" / ev["evidence_id"]).exists()
