from analysis.core import AnalysisResult, Analyzer, EvidenceInput, Finding, status_from_findings
from analysis.metadata.extract import extract_metadata

LIMITATIONS = [
    "Metadata is written by whatever software last saved the file and can be edited or removed without trace.",
    "Only EXIF (IFD0, Exif and GPS sub-IFDs) is read; XMP and IPTC are not parsed.",
]


def _tags(metadata: dict) -> dict[str, object]:
    tags: dict[str, object] = {}
    for entry in metadata["exif"]["entries"]:
        tags.setdefault(entry["tag"], entry["value"])
    return tags


class MetadataAnalyzer(Analyzer):
    """Header metadata and EXIF, with findings on device, software, timestamps and location fields."""

    name = "metadata"
    version = "0.2.0"

    def analyze(self, evidence: EvidenceInput) -> AnalysisResult:
        md = extract_metadata(evidence.data)
        tags = _tags(md)
        gps_present = any(e["ifd"] == "GPS" for e in md["exif"]["entries"])
        text = lambda key: str(tags[key]) if key in tags else None  # noqa: E731
        measurements = {
            "format": md["format"]["value"],
            "width": md["width"]["value"],
            "height": md["height"]["value"],
            "color_mode": md["mode"]["value"],
            "bit_depth": md["bit_depth"]["value"],
            "icc_profile": md["icc_profile"]["status"] == "available",
            "exif_status": md["exif"]["status"],
            "exif_entries": len(md["exif"]["entries"]),
            "make": text("Make"),
            "model": text("Model"),
            "software": text("Software"),
            "datetime": text("DateTime"),
            "datetime_original": text("DateTimeOriginal"),
            "gps_present": gps_present,
        }

        if md["exif"]["status"] == "unknown":
            finding = Finding(
                "EXIF could not be read",
                "An EXIF block may be present but could not be parsed.",
                "The metadata may be damaged or use an unsupported structure.",
                "Unreadable metadata does not show that the file was tampered with.",
            )
            return AnalysisResult("metadata", self.version, "inconclusive", "EXIF could not be interpreted.", measurements, [finding], LIMITATIONS, {"metadata": md})

        findings = self._findings(measurements, md["exif"]["status"] == "not_available")
        status = status_from_findings(findings)
        interpretation = {
            "indicator_detected": "Metadata contains fields that may indicate processing after capture; see findings.",
            "no_indicator": "No metadata field indicating processing was observed.",
        }[status]
        return AnalysisResult("metadata", self.version, status, interpretation, measurements, findings, LIMITATIONS, {"metadata": md})

    @staticmethod
    def _findings(m: dict, exif_absent: bool) -> list[Finding]:
        if exif_absent:
            return [Finding(
                "No EXIF metadata present",
                "The file contains no EXIF block.",
                "Metadata was never written or was removed (many platforms, editors and lossless exports, including VERIDIA's PNG outputs, do not write EXIF).",
                "Absence of metadata does not establish that the image was edited or that metadata was deliberately stripped.",
            )]
        findings = []
        if m["make"] or m["model"]:
            findings.append(Finding(
                "Capture device recorded",
                f"EXIF Make = {m['make']!r}, Model = {m['model']!r}.",
                "The file claims to originate from this device.",
                "EXIF fields are easily edited; this is a claim, not proof of origin.",
            ))
        if m["software"]:
            findings.append(Finding(
                "Processing software recorded",
                f"EXIF Software = {m['software']!r}.",
                "Software wrote or processed this file.",
                "Cameras and phones also write this field; it does not show that the content was altered.",
                "indicator",
            ))
        if m["datetime"] and m["datetime_original"] and m["datetime"] != m["datetime_original"]:
            findings.append(Finding(
                "File modification time differs from capture time",
                f"DateTimeOriginal = {m['datetime_original']!r}, DateTime = {m['datetime']!r}.",
                "The file was probably written again after capture (e.g. edited, rotated or re-saved).",
                "Timestamps are editable and depend on device clocks; re-saving without content changes also updates DateTime.",
                "indicator",
            ))
        if m["gps_present"]:
            findings.append(Finding(
                "Location (GPS) data present",
                "The EXIF GPS sub-IFD contains entries.",
                "The file records where it was captured, as claimed by the device.",
                "GPS fields can be edited or wrong; treat them as sensitive personal data.",
            ))
        if not findings:
            findings.append(Finding(
                "EXIF present without device, software or timestamp fields",
                f"{m['exif_entries']} EXIF entries, none of Make, Model, Software, DateTime.",
                "Only technical fields were written.",
                "Does not establish how or where the image was produced.",
            ))
        return findings
