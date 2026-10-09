"""Operation catalogue and hash-chain verification results."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class OperationInfo(BaseModel):
    name: str
    label: str = Field(description="Human-readable name of the operation.")
    output_label: str = Field(description="What the operation's output image is called.")
    category: str
    description: str
    registered: bool = Field(default=True, description="False for names found in records but not registered in this build.")


class ChainCheck(BaseModel):
    name: Literal["links", "event_hashes", "record_content", "coverage", "lineage", "files", "head"]
    label: str
    passed: bool
    detail: str


class ChainIssue(BaseModel):
    check: str
    kind: str
    detail: str
    sequence: int | None = None
    event_id: str | None = None
    record_id: str | None = None


class FileCheck(BaseModel):
    file_id: str = Field(description="Image ID, or report ID plus format.")
    kind: Literal["original", "derived", "report"]
    expected_sha256: str
    actual_sha256: str | None = None
    status: Literal["match", "mismatch", "missing"]


class ChainVerification(BaseModel):
    evidence_id: str
    verified_at: datetime
    valid: bool = Field(description="True when every check passed.")
    algorithm: str
    genesis_hash: str
    head_hash: str | None = Field(description="Hash of the last timeline event; record it elsewhere to detect later truncation or rewriting.")
    event_count: int
    expected_head: str | None = None
    first_invalid_sequence: int | None = None
    checks: list[ChainCheck]
    issues: list[ChainIssue]
    files: list[FileCheck]
