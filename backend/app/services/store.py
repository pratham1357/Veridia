"""Evidence store: JSON records and image files under ``storage/``, or memory only.

Layout (one directory per evidence item, all names server-generated)::

    storage/evidence/<evidence_id>/
        evidence.json                 EvidenceArtifact (metadata, provenance, analyses, reports, timeline)
        images/<image_id>.<ext>       original bytes (unmodified) and derived artifacts (PNG)
        reports/<report_id>.json|html exported investigation reports

Image and report files are write-once and made read-only (0400); ``evidence.json``
is replaced atomically (temp file + fsync + rename) on every change. Directories
are created 0700. User input never forms a path: IDs are validated against
``ID_PATTERN`` before use, and anything else found under ``storage/`` is ignored.

Image bytes are read from disk on every access rather than cached, so integrity
analysis and chain verification see the file as it is now.

Without a root (``open(None)``) the store keeps everything in memory, as before.
"""

import logging
import os
import re
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.schemas.evidence import EvidenceArtifact, ImageSummary
from app.services.errors import ServiceError

log = logging.getLogger(__name__)

ID_PATTERN = re.compile(r"^(ev|art|rep)_[0-9a-f]{32}$")
EXTENSION = {"image/png": "png", "image/jpeg": "jpg", "image/bmp": "bmp"}
REPORT_FORMATS = {"json": "application/json", "html": "text/html"}


@dataclass(frozen=True)
class StoredImage:
    image_id: str
    filename: str
    mime_type: str
    sha256: str
    width: int
    height: int
    evidence_id: str  # root evidence; equals image_id for an original
    size: int
    path: Path | None = None  # persistent mode
    blob: bytes | None = field(default=None, repr=False)  # memory mode

    @property
    def data(self) -> bytes:
        if self.path is None:
            assert self.blob is not None
            return self.blob
        try:
            return self.path.read_bytes()
        except FileNotFoundError:
            raise ServiceError("The stored file for this image is missing from storage.", 410) from None

    def summary(self) -> ImageSummary:
        return ImageSummary(
            image_id=self.image_id,
            filename=self.filename,
            mime_type=self.mime_type,
            size=self.size,
            sha256=self.sha256,
            width=self.width,
            height=self.height,
        )


def _checked_id(value: str) -> str:
    if not ID_PATTERN.fullmatch(value):
        raise ServiceError("Invalid identifier.", 400)
    return value


def _ensure_dir(path: Path) -> None:
    """Create ``path`` and any missing parents as 0700 (``mkdir(parents=True)`` would apply the mode to the leaf only)."""
    for directory in [*reversed(path.parents), path]:
        if not directory.exists():
            directory.mkdir(mode=0o700)


def _write_new(path: Path, data: bytes, mode: int = 0o400) -> None:
    """Write a file that must not already exist (write-once), then restrict its permissions."""
    _ensure_dir(path.parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(path, mode)


def _replace(path: Path, data: bytes) -> None:
    """Atomically replace ``path`` (readers see the old or the new content, never a partial file)."""
    _ensure_dir(path.parent)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


class EvidenceStore:
    def __init__(self) -> None:
        self.lock = threading.RLock()  # serialises mutations of evidence records and their files
        self.root: Path | None = None
        self.load_errors: list[str] = []
        self._evidence: dict[str, EvidenceArtifact] = {}
        self._images: dict[str, StoredImage] = {}  # originals and derived artifacts, by image ID
        self._reports: dict[tuple[str, str, str], bytes] = {}  # memory mode only

    # ---- lifecycle -------------------------------------------------------------------------------

    @property
    def persistent(self) -> bool:
        return self.root is not None

    def open(self, root: Path | None) -> None:
        """Reset the store and, with a root, load every evidence item found under it."""
        with self.lock:
            self.root = Path(root).resolve() if root is not None else None
            self.load_errors = []
            self._evidence.clear()
            self._images.clear()
            self._reports.clear()
            if self.root is None:
                return
            _ensure_dir(self._evidence_root())
            for directory in sorted(self._evidence_root().iterdir()):
                if directory.is_dir() and ID_PATTERN.fullmatch(directory.name) and directory.name.startswith("ev_"):
                    self._load(directory)

    def _evidence_root(self) -> Path:
        assert self.root is not None
        return self.root / "evidence"

    def _dir(self, evidence_id: str) -> Path:
        return self._evidence_root() / _checked_id(evidence_id)

    def _image_path(self, evidence_id: str, image_id: str, mime_type: str) -> Path:
        return self._dir(evidence_id) / "images" / f"{_checked_id(image_id)}.{EXTENSION.get(mime_type, 'bin')}"

    def _load(self, directory: Path) -> None:
        try:
            evidence = EvidenceArtifact.model_validate_json((directory / "evidence.json").read_bytes())
            if evidence.evidence_id != directory.name:
                raise ValueError("evidence_id does not match its directory")
        except Exception as exc:  # a damaged record must not stop the others from loading
            message = f"{directory.name}: could not load evidence.json ({type(exc).__name__})"
            log.warning(message)
            self.load_errors.append(message)
            return
        eid = evidence.evidence_id
        self._evidence[eid] = evidence
        self._register(StoredImage(eid, evidence.original_filename, evidence.file_type.mime_type, evidence.sha256,
                                   evidence.width, evidence.height, eid, evidence.file_size,
                                   path=self._image_path(eid, eid, evidence.file_type.mime_type)))
        for a in evidence.derived_artifacts:
            if ID_PATTERN.fullmatch(a.artifact_id):
                self._register(StoredImage(a.artifact_id, a.filename, a.mime_type, a.sha256, a.width, a.height, eid, a.size,
                                           path=self._image_path(eid, a.artifact_id, a.mime_type)))

    def _register(self, image: StoredImage) -> None:
        self._images[image.image_id] = image

    # ---- writes ----------------------------------------------------------------------------------

    def _put_image(self, evidence_id: str, image_id: str, filename: str, mime_type: str, data: bytes,
                   sha256: str, width: int, height: int) -> StoredImage:
        if self.root is None:
            image = StoredImage(image_id, filename, mime_type, sha256, width, height, evidence_id, len(data), blob=data)
        else:
            path = self._image_path(evidence_id, image_id, mime_type)
            _write_new(path, data)
            image = StoredImage(image_id, filename, mime_type, sha256, width, height, evidence_id, len(data), path=path)
        self._register(image)
        return image

    def add_evidence(self, evidence: EvidenceArtifact, data: bytes) -> StoredImage:
        """Store the original bytes unmodified and persist the new evidence record."""
        with self.lock:
            original = self._put_image(evidence.evidence_id, evidence.evidence_id, evidence.original_filename,
                                       evidence.file_type.mime_type, data, evidence.sha256, evidence.width, evidence.height)
            self._evidence[evidence.evidence_id] = evidence
            self.save(evidence)
            return original

    def add_artifact(self, evidence_id: str, image_id: str, filename: str, mime_type: str, data: bytes,
                     sha256: str, width: int, height: int) -> StoredImage:
        with self.lock:
            return self._put_image(evidence_id, image_id, filename, mime_type, data, sha256, width, height)

    def save(self, evidence: EvidenceArtifact) -> None:
        """Persist the evidence record (no-op in memory mode)."""
        if self.root is None:
            return
        with self.lock:
            _replace(self._dir(evidence.evidence_id) / "evidence.json", evidence.model_dump_json(indent=2).encode("utf-8"))

    def put_report(self, evidence_id: str, report_id: str, fmt: str, data: bytes) -> None:
        if fmt not in REPORT_FORMATS:
            raise ServiceError("Unknown report format.", 400)
        with self.lock:
            if self.root is None:
                self._reports[(evidence_id, report_id, fmt)] = data
            else:
                _write_new(self._dir(evidence_id) / "reports" / f"{_checked_id(report_id)}.{fmt}", data)

    # ---- reads -----------------------------------------------------------------------------------

    def evidence(self, evidence_id: str) -> EvidenceArtifact:
        try:
            return self._evidence[evidence_id]
        except KeyError:
            raise ServiceError("Evidence not found.", 404) from None

    def image(self, image_id: str) -> StoredImage:
        try:
            return self._images[image_id]
        except KeyError:
            raise ServiceError("Image not found.", 404) from None

    def images_of(self, evidence_id: str) -> list[StoredImage]:
        return [img for img in self._images.values() if img.evidence_id == evidence_id]

    def report(self, evidence_id: str, report_id: str, fmt: str) -> bytes:
        if fmt not in REPORT_FORMATS:
            raise ServiceError("Unknown report format.", 400)
        if self.root is None:
            try:
                return self._reports[(evidence_id, report_id, fmt)]
            except KeyError:
                raise ServiceError("Report not found.", 404) from None
        try:
            return (self._dir(evidence_id) / "reports" / f"{_checked_id(report_id)}.{fmt}").read_bytes()
        except FileNotFoundError:
            raise ServiceError("Report file not found in storage.", 404) from None

    def list_evidence(self) -> list[EvidenceArtifact]:
        return sorted(self._evidence.values(), key=lambda e: e.created_at, reverse=True)


store = EvidenceStore()
