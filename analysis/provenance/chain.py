"""SHA-256 hash chain over an ordered list of records (used for the evidence timeline).

Each entry is a JSON object with at least ``sequence``, ``previous_hash`` and
``hash``. The hash of an entry is

    SHA-256( canonical_json( entry without its "hash" field ) )

and ``previous_hash`` must equal the hash of the entry before it (``GENESIS``
for the first). Because the previous hash is inside the hashed body, changing,
removing, inserting or reordering any entry breaks every link after it.

Canonical JSON: keys sorted, no insignificant whitespace, UTF-8, and no NaN or
infinity (they have no JSON representation). Two systems that agree on these
rules compute the same hashes from the same data.

What a hash chain does *not* do: anyone who can rewrite the stored chain can
also recompute every hash. Truncation (dropping the newest entries) and a
complete rewrite are only detectable against a head hash recorded somewhere
else, which is why ``verify_links`` accepts an ``expected_head``.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

GENESIS = "0" * 64
ALGORITHM = "SHA-256 over canonical JSON (sorted keys, compact separators, UTF-8)"


def canonical_json(value: Any) -> bytes:
    """Deterministic JSON encoding used for every hash in the chain."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    """SHA-256 (hex) of the canonical JSON encoding of ``value``."""
    return hashlib.sha256(canonical_json(value)).hexdigest()


def entry_hash(entry: Mapping[str, Any]) -> str:
    """Hash of one chain entry: everything except its own ``hash`` field."""
    return digest({k: v for k, v in entry.items() if k != "hash"})


@dataclass(frozen=True)
class ChainIssue:
    kind: str  # broken_link | hash_mismatch | sequence_error | head_not_found
    detail: str
    sequence: int | None = None
    entry_id: str | None = None


def verify_links(
    entries: Sequence[Mapping[str, Any]], expected_head: str | None = None, id_field: str = "event_id"
) -> list[ChainIssue]:
    """Check sequence numbers, links and entry hashes; optionally that ``expected_head`` is in the chain.

    An ``expected_head`` that matches an *earlier* entry is accepted: the chain
    has only been extended since that head was recorded. One that matches no
    entry means the chain was truncated or rewritten after it was recorded.
    """
    issues: list[ChainIssue] = []
    previous = GENESIS
    for index, entry in enumerate(entries):
        seq, eid = entry.get("sequence"), entry.get(id_field)
        if seq != index:
            issues.append(ChainIssue("sequence_error", f"Entry at position {index} carries sequence {seq}.", index, eid))
        if entry.get("previous_hash") != previous:
            issues.append(ChainIssue(
                "broken_link",
                f"previous_hash {str(entry.get('previous_hash'))[:16]}… does not equal the hash of the preceding entry ({previous[:16]}…).",
                index, eid,
            ))
        recomputed = entry_hash(entry)
        if entry.get("hash") != recomputed:
            issues.append(ChainIssue(
                "hash_mismatch",
                f"Stored hash {str(entry.get('hash'))[:16]}… does not match the recomputed {recomputed[:16]}…: the entry was modified.",
                index, eid,
            ))
        previous = str(entry.get("hash"))
    if expected_head is not None and expected_head.lower() not in {str(e.get("hash")) for e in entries}:
        issues.append(ChainIssue(
            "head_not_found",
            f"The expected head {expected_head[:16]}… is not in the chain: entries were removed or the chain was rewritten after that head was recorded.",
        ))
    return issues
