import hashlib

from analysis.metadata import extract_metadata


def test_upload_hashes_original_and_records_dimensions(client, png_bytes):
    r = client.post("/api/evidence/upload", files={"file": ("sample.png", png_bytes, "image/png")})
    assert r.status_code == 201
    body = r.json()
    assert body["sha256"] == hashlib.sha256(png_bytes).hexdigest()
    assert (body["width"], body["height"]) == (64, 64)
    assert body["file_size"] == len(png_bytes)
    # the stored original is byte-identical to the upload
    assert client.get(f"/api/images/{body['evidence_id']}").content == png_bytes


def test_rejects_non_image_and_mismatched_content(client, png_bytes):
    bad = client.post("/api/evidence/upload", files={"file": ("x.png", b"not an image", "image/png")})
    assert bad.status_code == 415
    mismatch = client.post("/api/evidence/upload", files={"file": ("x.jpg", png_bytes, "image/jpeg")})
    assert mismatch.status_code == 415
    script = client.post("/api/evidence/upload", files={"file": ("x.exe", b"MZ\x90\x00", "image/png")})
    assert script.status_code == 415


def test_rejects_corrupt_image(client, png_bytes):
    r = client.post("/api/evidence/upload", files={"file": ("t.png", png_bytes[:60], "image/png")})
    assert r.status_code == 400


def test_filename_is_sanitized(client, png_bytes):
    r = client.post("/api/evidence/upload", files={"file": ("..\\..\\evil name.png", png_bytes, "image/png")})
    assert r.json()["original_filename"] == "evil name.png"


def test_metadata_reports_absent_exif_explicitly(png_bytes):
    m = extract_metadata(png_bytes)
    assert m["format"] == {"status": "available", "value": "PNG"}
    assert (m["width"]["value"], m["height"]["value"]) == (64, 64)
    assert m["exif"] == {"status": "not_available", "entries": []}


def test_metadata_reads_exif(jpeg_with_exif):
    m = extract_metadata(jpeg_with_exif)
    assert m["exif"]["status"] == "available"
    assert {"ifd": "IFD0", "tag": "Make", "value": "VeridiaCam"} in m["exif"]["entries"]
