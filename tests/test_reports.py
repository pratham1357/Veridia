"""Investigation report export: JSON structure, HTML rendering and escaping, storage, hashes and chain anchoring."""

import hashlib
import io
import json

from PIL import Image

from app.services.store import store
from tests.conftest import natural_image, upload

KEY = "s3cr3t-key-7Q"


def _jpeg_with_make(pixels, make: str) -> bytes:
    exif = Image.Exif()
    exif[0x010F] = make
    buf = io.BytesIO()
    Image.fromarray(pixels).save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def _investigate(client, data, name="scene.png", mime="image/png"):
    ev = upload(client, data, name, mime)
    eid = ev["evidence_id"]
    art = client.post("/api/watermark/embed", json={"evidence_id": eid, "method": "dct", "message": "owner", "key": KEY}).json()["artifact"]
    client.post(f"/api/investigation/{eid}/pipeline", json={"subject_id": art["image_id"], "include_ela": True,
                                                            "watermark": {"method": "dct", "key": KEY, "expected_message": "owner"}})
    return eid, art


def test_report_json_contents(client, natural_png):
    eid, art = _investigate(client, natural_png)
    events_before = len(client.get(f"/api/evidence/{eid}").json()["timeline"])

    r = client.post(f"/api/reports/{eid}")
    assert r.status_code == 201
    rec = r.json()
    assert rec["events_covered"] == events_before and rec["chain_valid"] is True

    body = client.get(f"/api/reports/{eid}/{rec['report_id']}/json")
    assert hashlib.sha256(body.content).hexdigest() == rec["json_sha256"] == body.headers["x-report-sha256"]
    report = body.json()
    assert report["schema"] == "veridia.investigation-report" and report["schema_version"] == 1
    assert report["report_id"] == rec["report_id"] and report["evidence"]["evidence_id"] == eid
    assert [i["role"] for i in report["images"]] == ["original", "derived"]
    assert all(i["file_check"] == "match" for i in report["images"])
    assert report["images"][1]["operation"] == "dct_watermark_embed" and report["images"][1]["operation_label"] == "DCT watermark embed"
    types = [a["result"]["analysis_type"] for a in report["analyses"]]
    assert types == ["metadata", "integrity", "ela", "steganalysis", "watermark", "comparison"]
    assert report["summary"]["analyses"] == 6 and sum(report["summary"]["analyses_by_status"].values()) == 6
    assert report["chain"]["head_hash"] == report["timeline"][-1]["hash"] == rec["chain_head"]
    assert report["chain"]["verification"]["valid"] is True
    assert KEY not in body.text  # keys are never recorded
    assert "owner" not in json.dumps(report["provenance_records"])  # nor the embedded message (the extraction result is a finding)


def test_report_export_is_recorded_in_the_chain(client, natural_png):
    eid, _ = _investigate(client, natural_png)
    rec = client.post(f"/api/reports/{eid}").json()
    ev = client.get(f"/api/evidence/{eid}").json()
    last = ev["timeline"][-1]
    assert last["event_type"] == "report_exported" and last["reference_id"] == rec["report_id"]
    assert last["sequence"] == rec["events_covered"]
    assert ev["reports"] == [rec] and client.get(f"/api/reports/{eid}").json() == [rec]

    v = client.get(f"/api/provenance/{eid}/verify", params={"expected_head": rec["chain_head"]}).json()
    assert v["valid"]  # the report's head is still in the chain, which has since been extended
    assert {f["file_id"] for f in v["files"] if f["kind"] == "report"} == {f"{rec['report_id']}.json", f"{rec['report_id']}.html"}


def test_report_html_is_self_contained_and_escaped(client):
    eid, _ = _investigate(client, _jpeg_with_make(natural_image(), "<script>alert(1)</script>"), "photo.jpg", "image/jpeg")
    rec = client.post(f"/api/reports/{eid}").json()
    r = client.get(f"/api/reports/{eid}/{rec['report_id']}/html")
    html = r.text
    assert r.headers["content-type"].startswith("text/html")
    assert "default-src 'none'" in r.headers["content-security-policy"] and r.headers["x-content-type-options"] == "nosniff"
    assert hashlib.sha256(r.content).hexdigest() == rec["html_sha256"]

    assert KEY not in html and "<script" not in html.lower() and "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "http://" not in html and "https://" not in html and "src=\"/" not in html  # no external or server resources
    assert html.count("data:image/png;base64,") == 2  # original + derived thumbnails
    assert "<svg" in html  # ELA block map
    for text in ("Record integrity", "Findings summary", "Timeline (hash-chained)", "Methods and limitations", rec["chain_head"]):
        assert text in html
    assert "attachment" in client.get(f"/api/reports/{eid}/{rec['report_id']}/html?download=true").headers["content-disposition"]


def test_report_files_are_stored_and_survive_reload(client, natural_png, storage):
    eid, _ = _investigate(client, natural_png)
    rec = client.post(f"/api/reports/{eid}").json()
    folder = storage / "evidence" / eid / "reports"
    assert sorted(p.name for p in folder.iterdir()) == sorted([f"{rec['report_id']}.html", f"{rec['report_id']}.json"])
    assert hashlib.sha256((folder / f"{rec['report_id']}.json").read_bytes()).hexdigest() == rec["json_sha256"]

    store.open(storage)
    assert client.get(f"/api/reports/{eid}/{rec['report_id']}/json").json()["report_id"] == rec["report_id"]
    assert client.get(f"/api/provenance/{eid}/verify").json()["valid"]


def test_tampered_report_file_is_detected(client, natural_png, storage):
    eid, _ = _investigate(client, natural_png)
    rec = client.post(f"/api/reports/{eid}").json()
    path = storage / "evidence" / eid / "reports" / f"{rec['report_id']}.json"
    path.chmod(0o600)
    report = json.loads(path.read_text(encoding="utf-8"))
    report["analyses"][0]["result"]["status"] = "verified"
    path.write_text(json.dumps(report), encoding="utf-8")
    issues = client.get(f"/api/provenance/{eid}/verify").json()["issues"]
    assert [(i["kind"], i["record_id"]) for i in issues] == [("file_mismatch", f"{rec['report_id']}.json")]


def test_report_on_tampered_record_says_so(client, natural_png, storage):
    eid, _ = _investigate(client, natural_png)
    path = storage / "evidence" / eid / "evidence.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["analyses"][0]["result"]["interpretation"] = "rewritten"
    path.write_text(json.dumps(record), encoding="utf-8")
    store.open(storage)

    rec = client.post(f"/api/reports/{eid}").json()
    assert rec["chain_valid"] is False
    html = client.get(f"/api/reports/{eid}/{rec['report_id']}/html").text
    assert "inconsistencies detected" in html and "content_mismatch" in html


def test_report_errors(client, natural_png):
    eid = upload(client, natural_png)["evidence_id"]
    assert client.post("/api/reports/ev_missing").status_code == 404
    assert client.get(f"/api/reports/{eid}/rep_{'0' * 32}/json").status_code == 404
    rec = client.post(f"/api/reports/{eid}").json()  # a report with no analyses is still valid
    assert client.get(f"/api/reports/{eid}/{rec['report_id']}/pdf").status_code == 422
    assert client.get(f"/api/reports/{eid}/{rec['report_id']}/json").json()["analyses"] == []
