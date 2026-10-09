"""The evidence timeline as a SHA-256 hash chain, and its verification.

Events are only created by real operations. Each event is a chain link (see
``analysis.provenance.chain``) and additionally carries ``content_hash``, the
hash of the record it refers to (the evidence identity, metadata, a provenance
record with its derived artifact, an analysis record or a report record). So
the chain covers what happened, not just the event descriptions.

``verify`` re-derives everything from the stored data:

- links / event hashes: every event recomputes to its stored hash and points at its predecessor
- record content: every referenced record still hashes to the event's ``content_hash``
- coverage: every provenance, analysis and report record is anchored by an event (nothing injected)
- lineage: parent links and parent/child hashes of derived artifacts are mutually consistent
- files: every stored image and report file still hashes to its recorded SHA-256
- head (optional): a head hash recorded elsewhere is still part of the chain
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from analysis.provenance import ALGORITHM, GENESIS, digest, entry_hash, verify_links
from app.schemas.evidence import EvidenceArtifact, TimelineEvent
from app.schemas.provenance import ChainCheck, ChainIssue, ChainVerification, FileCheck
from app.services.errors import ServiceError
from app.services.store import store

IDENTITY_FIELDS = {"evidence_id", "original_filename", "file_type", "file_size", "sha256", "width", "height", "created_at"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def image_label(evidence: EvidenceArtifact, image_id: str) -> str:
    """Human-readable name for an image within an evidence item."""
    if image_id == evidence.evidence_id:
        return f"original evidence ({evidence.original_filename})"
    return store.image(image_id).filename


def as_json(model: BaseModel, **kwargs: Any) -> Any:
    """The model exactly as persisted (JSON round trip), so hashes survive a save and reload."""
    return json.loads(model.model_dump_json(**kwargs))


def event_content(evidence: EvidenceArtifact, event_type: str, reference_id: str | None) -> Any | None:
    """The record an event refers to, as canonical-JSON-ready data; None if it cannot be found."""
    if event_type == "evidence_acquired":
        return as_json(evidence, include=IDENTITY_FIELDS)
    if event_type == "metadata_extracted":
        return as_json(evidence.metadata_results) if evidence.metadata_results else None
    if event_type == "hash_computed":
        return {"evidence_id": evidence.evidence_id, "sha256": evidence.sha256}
    if event_type == "artifact_created":
        record = next((r for r in evidence.provenance if r.record_id == reference_id), None)
        artifact = next((a for a in evidence.derived_artifacts if a.provenance_record_id == reference_id), None)
        return {"provenance_record": as_json(record), "derived_artifact": as_json(artifact)} if record and artifact else None
    if event_type == "analysis_completed":
        record = next((r for r in evidence.analyses if r.record_id == reference_id), None)
        return as_json(record) if record else None
    if event_type == "report_exported":
        record = next((r for r in evidence.reports if r.report_id == reference_id), None)
        return as_json(record) if record else None
    return None


def record_event(
    evidence: EvidenceArtifact,
    event_type: str,
    subject_image_id: str,
    description: str,
    reference_id: str | None = None,
    timestamp: datetime | None = None,
) -> TimelineEvent:
    """Append a chained event. The referenced record must already be on ``evidence``."""
    with store.lock:
        content = event_content(evidence, event_type, reference_id)
        previous = evidence.timeline[-1].hash if evidence.timeline else GENESIS
        body = {
            "sequence": len(evidence.timeline),
            "event_id": f"evt_{uuid.uuid4().hex}",
            "timestamp": timestamp or now(),
            "event_type": event_type,
            "subject_image_id": subject_image_id,
            "description": description,
            "reference_id": reference_id,
            "content_hash": digest(content) if content is not None else None,
            "previous_hash": previous,
        }
        draft = TimelineEvent(**body, hash=GENESIS)
        event = draft.model_copy(update={"hash": entry_hash(as_json(draft))})
        evidence.timeline.append(event)
        return event


def chain_head(evidence: EvidenceArtifact) -> str | None:
    return evidence.timeline[-1].hash if evidence.timeline else None


def _file_check(file_id: str, kind: str, expected: str, read) -> FileCheck:
    try:
        actual = hashlib.sha256(read()).hexdigest()
    except ServiceError:
        return FileCheck(file_id=file_id, kind=kind, expected_sha256=expected, status="missing")  # type: ignore[arg-type]
    return FileCheck(file_id=file_id, kind=kind, expected_sha256=expected, actual_sha256=actual,  # type: ignore[arg-type]
                     status="match" if actual == expected else "mismatch")


def file_checks(evidence: EvidenceArtifact) -> list[FileCheck]:
    """Re-hash every stored file of this evidence item against its recorded SHA-256."""
    eid = evidence.evidence_id

    def image_reader(image_id: str):
        def read() -> bytes:
            return store.image(image_id).data
        return read

    checks = [_file_check(eid, "original", evidence.sha256, image_reader(eid))]
    checks += [_file_check(a.artifact_id, "derived", a.sha256, image_reader(a.artifact_id)) for a in evidence.derived_artifacts]
    for r in evidence.reports:
        for fmt, expected in (("json", r.json_sha256), ("html", r.html_sha256)):
            checks.append(_file_check(f"{r.report_id}.{fmt}", "report", expected,
                                      lambda r=r, fmt=fmt: store.report(eid, r.report_id, fmt)))
    return checks


def verify(evidence: EvidenceArtifact, expected_head: str | None = None) -> ChainVerification:
    with store.lock:
        events = [as_json(e) for e in evidence.timeline]
        issues: list[ChainIssue] = []

        link_issues = verify_links(events, expected_head)
        for i in link_issues:
            check = {"hash_mismatch": "event_hashes", "head_not_found": "head"}.get(i.kind, "links")
            issues.append(ChainIssue(check=check, kind=i.kind, detail=i.detail, sequence=i.sequence, event_id=i.entry_id))

        for e in evidence.timeline:
            content = event_content(evidence, e.event_type, e.reference_id)
            if content is None:
                if e.content_hash is not None:
                    issues.append(ChainIssue(check="record_content", kind="missing_record", sequence=e.sequence, event_id=e.event_id,
                                             record_id=e.reference_id, detail=f"The {e.event_type.replace('_', ' ')} record this event covers is missing."))
            elif digest(content) != e.content_hash:
                issues.append(ChainIssue(check="record_content", kind="content_mismatch", sequence=e.sequence, event_id=e.event_id,
                                         record_id=e.reference_id,
                                         detail=f"The {e.event_type.replace('_', ' ')} record no longer matches the hash recorded in the chain: it was modified after the event."))

        anchored = {(e.event_type, e.reference_id) for e in evidence.timeline}
        expected_anchors = (
            [("artifact_created", r.record_id, "provenance record") for r in evidence.provenance]
            + [("analysis_completed", r.record_id, "analysis record") for r in evidence.analyses]
            + [("report_exported", r.report_id, "report record") for r in evidence.reports]
        )
        for event_type, record_id, label in expected_anchors:
            if (event_type, record_id) not in anchored:
                issues.append(ChainIssue(check="coverage", kind="unanchored_record", record_id=record_id,
                                         detail=f"A {label} exists that no timeline event covers: it was added outside the application."))
        artifact_records = {a.provenance_record_id for a in evidence.derived_artifacts}
        for r in evidence.provenance:
            if r.record_id not in artifact_records:
                issues.append(ChainIssue(check="coverage", kind="unanchored_record", record_id=r.record_id,
                                         detail="A provenance record has no matching derived artifact."))

        hashes = {evidence.evidence_id: evidence.sha256} | {a.artifact_id: a.sha256 for a in evidence.derived_artifacts}
        records = {r.record_id: r for r in evidence.provenance}
        for a in evidence.derived_artifacts:
            problems = []
            if a.parent_image_id not in hashes:
                problems.append("its parent is not part of this evidence item")
            elif hashes[a.parent_image_id] != a.parent_sha256:
                problems.append("its parent_sha256 differs from the parent's recorded SHA-256")
            record = records.get(a.provenance_record_id)
            if record and (record.output_sha256 != a.sha256 or record.input_sha256 != a.parent_sha256
                           or record.input_image_id != a.parent_image_id or record.output_image_id != a.artifact_id):
                problems.append("its provenance record names different input/output images or hashes")
            if problems:
                issues.append(ChainIssue(check="lineage", kind="lineage_mismatch", record_id=a.artifact_id,
                                         detail=f"Derived artifact {a.filename}: " + "; ".join(problems) + "."))

        files = file_checks(evidence)
        for f in files:
            if f.status != "match":
                issues.append(ChainIssue(check="files", kind=f"file_{f.status}", record_id=f.file_id,
                                         detail=f"{f.kind.capitalize()} file {f.file_id} is {'missing' if f.status == 'missing' else 'changed: its SHA-256 no longer matches the recorded value'}."))

    def check(name: str, label: str, ok_detail: str) -> ChainCheck:
        found = [i for i in issues if i.check == name]
        return ChainCheck(name=name, label=label, passed=not found,  # type: ignore[arg-type]
                          detail=ok_detail if not found else f"{len(found)} problem(s); see issues.")

    checks = [
        check("links", "Chain links and sequence", f"{len(events)} event(s), each linked to its predecessor from the genesis hash."),
        check("event_hashes", "Event hashes", "Every event recomputes to its stored SHA-256."),
        check("record_content", "Covered records", "Every referenced record matches the content hash in its event."),
        check("coverage", "Coverage", "Every provenance, analysis and report record is anchored by an event."),
        check("lineage", "Artifact lineage", "Parent links and parent/child hashes are consistent."),
        check("files", "Stored files", f"{len(files)} file(s) re-hashed; all match their recorded SHA-256."),
    ]
    if expected_head is not None:
        checks.append(check("head", "Expected head", "The supplied head hash is part of the chain (the chain has at most been extended since)."))
    sequences = [i.sequence for i in issues if i.sequence is not None]
    return ChainVerification(
        evidence_id=evidence.evidence_id,
        verified_at=now(),
        valid=not issues,
        algorithm=ALGORITHM,
        genesis_hash=GENESIS,
        head_hash=chain_head(evidence),
        event_count=len(events),
        expected_head=expected_head,
        first_invalid_sequence=min(sequences) if sequences else None,
        checks=checks,
        issues=issues,
        files=files,
    )
