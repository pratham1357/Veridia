"""Extensible provenance operation names: registry, validation, derive() integration and API."""

import numpy as np
import pytest
from pydantic import ValidationError

from app.schemas.evidence import ProvenanceRecord
from app.services import operation_registry as registry
from app.services.artifacts import derive
from app.services.operation_registry import OperationSpec
from tests.conftest import upload

INVERT = OperationSpec("invert_colours", "Colour inversion", "Inverted image", "test", "Inverts every sample (test operation).")


@pytest.fixture
def invert():
    registry.register_operation(INVERT)
    yield INVERT
    registry.unregister_operation(INVERT.name)


def _record(operation: str) -> dict:
    h = "a" * 64
    return {"record_id": "rec_1", "operation": operation, "timestamp": "2026-10-09T00:00:00Z", "input_evidence_id": "ev_1",
            "input_image_id": "ev_1", "input_sha256": h, "output_image_id": "art_1", "output_sha256": h,
            "parameters": {}, "metrics": {"mse": 0, "psnr_db": None, "ssim": 1}}


def test_builtin_operations_are_listed(client):
    ops = {o["name"]: o for o in client.get("/api/provenance/operations").json()}
    assert set(ops) >= {"lsb_steganography_embed", "watermark_embed", "dct_watermark_embed", "attack"}
    assert ops["dct_watermark_embed"]["label"] == "DCT watermark embed" and ops["attack"]["category"] == "attack"
    assert all(o["registered"] for o in ops.values())


def test_names_are_open_but_well_formed():
    assert ProvenanceRecord.model_validate(_record("dwt_watermark_embed")).operation == "dwt_watermark_embed"  # future name loads
    for bad in ("DCT", "dct watermark", "1abc", "x", "a" * 65, "../etc"):
        with pytest.raises(ValidationError):
            ProvenanceRecord.model_validate(_record(bad))


def test_register_validation():
    with pytest.raises(ValueError):
        registry.register_operation(OperationSpec("Bad Name", "x", "x", "x", "x"))
    with pytest.raises(ValueError):  # conflicting redefinition
        registry.register_operation(OperationSpec("attack", "Something else", "x", "x", "x"))
    registry.register_operation(registry.require_operation("attack"))  # identical re-registration is fine


def test_unknown_operation_falls_back_to_readable_label():
    info = registry.describe("dwt_watermark_embed")
    assert not info.registered and info.label == "Dwt watermark embed" and info.category == "unregistered"


def test_derive_requires_registration(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    with pytest.raises(LookupError):
        derive(eid, "invert_colours", "inverted", lambda px: 255 - px, {})


def test_new_operation_flows_through_provenance_and_chain(client, natural_png, invert):
    eid = upload(client, natural_png)["evidence_id"]
    artifact, record, _, out = derive(eid, invert.name, "inverted", lambda px: (255 - px).astype(np.uint8), {"channels": "rgb"})
    assert record.operation == "invert_colours" and record.metrics.mse > 0

    ev = client.get(f"/api/evidence/{eid}").json()
    assert ev["derived_artifacts"][0]["operation"] == "invert_colours"
    assert ev["timeline"][-1]["description"].startswith("Derived artifact created by colour inversion")
    assert "invert_colours" in {o["name"] for o in client.get("/api/provenance/operations").json()}
    assert client.get(f"/api/provenance/{eid}/verify").json()["valid"]

    report = client.get(f"/api/reports/{eid}/{client.post(f'/api/reports/{eid}').json()['report_id']}/json").json()
    assert report["images"][1]["operation_label"] == "Colour inversion"
