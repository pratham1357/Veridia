"""Investigation reports: a machine-readable JSON document and a self-contained HTML rendering of it.

A report is a snapshot of one evidence item as recorded: identity and metadata,
every image with its hash (re-checked at export), the provenance chain, every
recorded analysis with its findings and limitations, the hash-chained timeline
and a chain verification. It adds no conclusions of its own.

Both files are written once under ``storage/evidence/<id>/reports/`` and a
``report_exported`` event, whose content hash covers both file hashes, is
appended to the timeline. The report therefore covers events ``0 .. N-1`` and
names the head hash of event ``N-1``; the export event itself is ``N``.

The HTML is generated with ``string.Template`` and ``html.escape``. It loads no
external resources (thumbnails are inline PNG data URIs, charts are inline SVG)
and is served with a Content-Security-Policy that blocks scripts.
"""

import base64
import hashlib
import io
import json
import uuid
from collections import Counter
from html import escape
from string import Template
from typing import Any

from PIL import Image

from analysis.provenance import ALGORITHM, GENESIS
from app.core.config import settings
from app.schemas.evidence import EvidenceArtifact, ReportRecord
from app.services.operation_registry import describe
from app.services.errors import ServiceError
from app.services.provenance import as_json, now, record_event, verify
from app.services.store import store

SCHEMA = "veridia.investigation-report"
SCHEMA_VERSION = 1
THUMBNAIL_PX = 192
ANALYSIS_LABEL = {
    "metadata": "Metadata",
    "integrity": "Integrity",
    "ela": "Error level analysis (experimental)",
    "steganalysis": "Steganalysis",
    "watermark": "Watermark verification",
    "comparison": "Comparison",
}
STATUS_LABEL = {
    "verified": "Verified",
    "indicator_detected": "Indicator detected",
    "no_indicator": "No indicator detected",
    "inconclusive": "Inconclusive",
    "not_applicable": "Not applicable",
}
STATEMENT = (
    "This report lists measurements, findings and their limitations as recorded by VERIDIA. It contains no authenticity "
    "verdict and no score: each finding is a potential indicator to be interpreted in context and corroborated."
)
REPORT_LIMITATIONS = [
    "The record covers what VERIDIA did after the file was acquired; it says nothing about the image's history before acquisition.",
    "The hash chain detects changes to the stored record; anyone able to rewrite the whole chain can also recompute it. "
    "Record the chain head hash elsewhere (e.g. in a case file) to detect later truncation or rewriting.",
    "Thumbnails in the HTML rendering are downscaled PNG previews for orientation only, not evidence.",
    "Payloads, watermark messages and keys are never recorded and do not appear in this report.",
]


# ---- JSON report -------------------------------------------------------------------------------------

def build_report(evidence: EvidenceArtifact, report_id: str) -> dict[str, Any]:
    """The JSON report document (a plain dict, ready for ``json.dumps``)."""
    verification = verify(evidence)
    files = {f.file_id: f.status for f in verification.files}
    images = [{
        "image_id": evidence.evidence_id, "role": "original", "filename": evidence.original_filename,
        "mime_type": evidence.file_type.mime_type, "size": evidence.file_size, "width": evidence.width,
        "height": evidence.height, "sha256": evidence.sha256, "parent_image_id": None, "operation": None,
        "operation_label": None, "created_at": as_json(evidence, include={"created_at"})["created_at"],
        "file_check": files.get(evidence.evidence_id),
    }]
    for a in evidence.derived_artifacts:
        images.append({
            "image_id": a.artifact_id, "role": "derived", "filename": a.filename, "mime_type": a.mime_type,
            "size": a.size, "width": a.width, "height": a.height, "sha256": a.sha256,
            "parent_image_id": a.parent_image_id, "parent_sha256": a.parent_sha256, "operation": a.operation,
            "operation_label": describe(a.operation).label, "created_at": as_json(a, include={"created_at"})["created_at"],
            "provenance_record_id": a.provenance_record_id, "file_check": files.get(a.artifact_id),
        })
    statuses = Counter(r.result.status for r in evidence.analyses)
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "report_id": report_id,
        "generated_at": now().isoformat().replace("+00:00", "Z"),
        "generator": {"name": settings.app_name, "version": settings.version},
        "statement": STATEMENT,
        "evidence": as_json(evidence, include={"evidence_id", "original_filename", "file_type", "file_size", "sha256",
                                             "width", "height", "created_at", "metadata_results"}),
        "images": images,
        "provenance_records": [as_json(r) for r in evidence.provenance],
        "analyses": [as_json(r) for r in evidence.analyses],
        "summary": {
            "images": len(images),
            "derived_artifacts": len(evidence.derived_artifacts),
            "analyses": len(evidence.analyses),
            "analyses_by_status": {s: statuses.get(s, 0) for s in STATUS_LABEL},
            "analyzers": sorted({f"{r.result.analysis_type} v{r.result.analyzer_version}" for r in evidence.analyses}),
            "timeline_events": len(evidence.timeline),
        },
        "timeline": [as_json(e) for e in evidence.timeline],
        "chain": {
            "algorithm": ALGORITHM,
            "genesis_hash": GENESIS,
            "head_hash": verification.head_hash,
            "events_covered": verification.event_count,
            "verification": as_json(verification),
        },
        "limitations": REPORT_LIMITATIONS,
    }


# ---- HTML rendering ----------------------------------------------------------------------------------

PAGE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="$generator">
<title>VERIDIA report $report_id</title>
<style>
:root { --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; --soft:#f8fafc; --accent:#0e7490; --amber:#b45309; --green:#047857; --red:#b91c1c; }
* { box-sizing: border-box; }
body { margin: 0; background: #fff; color: var(--ink); font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1040px; margin: 0 auto; padding: 32px 20px 64px; }
h1 { font-size: 26px; letter-spacing: .2em; margin: 0; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .12em; color: var(--muted); border-bottom: 1px solid var(--line); padding-bottom: 6px; margin: 36px 0 14px; }
h3 { font-size: 15px; margin: 0; }
table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
th, td { text-align: left; vertical-align: top; padding: 6px 8px; border-bottom: 1px solid var(--line); }
th { color: var(--muted); font-weight: 600; }
code, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11.5px; word-break: break-all; }
.nowrap { white-space: nowrap; word-break: normal; }
.muted { color: var(--muted); }
.statement { background: var(--soft); border-left: 3px solid var(--accent); padding: 10px 14px; margin: 18px 0; }
.badge { display: inline-block; white-space: nowrap; border-radius: 3px; padding: 1px 8px; font-size: 11.5px; font-weight: 600; }
.verified { background: #d1fae5; color: var(--green); } .indicator_detected { background: #fef3c7; color: var(--amber); }
.no_indicator { background: #e2e8f0; color: #334155; } .inconclusive { background: #ede9fe; color: #6d28d9; }
.not_applicable { background: #f1f5f9; color: var(--muted); }
.ok { background: #d1fae5; color: var(--green); } .bad { background: #fee2e2; color: var(--red); }
.card { border: 1px solid var(--line); border-radius: 4px; padding: 14px 16px; margin: 14px 0; break-inside: avoid; }
.card header { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 8px; }
.card header .meta { margin-left: auto; color: var(--muted); font-size: 12px; }
.finding { border-top: 1px solid var(--line); padding: 8px 0; }
.finding dl { display: grid; grid-template-columns: 7.5rem 1fr; gap: 2px 10px; margin: 4px 0 0; font-size: 12.5px; }
.finding dt { color: var(--muted); } .finding dd { margin: 0; } .limit { color: var(--amber); }
.kind { font-size: 10.5px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-left: 8px; }
.tree, .tree ul { list-style: none; margin: 0; padding-left: 18px; } .tree { padding-left: 0; }
.tree li { margin: 4px 0; } .tree ul { border-left: 1px solid var(--line); }
.thumb { width: 72px; height: 72px; object-fit: contain; background: var(--soft); border: 1px solid var(--line); }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
dl.kv { display: grid; grid-template-columns: 11rem 1fr; gap: 4px 12px; margin: 0; } dl.kv dt { color: var(--muted); } dl.kv dd { margin: 0; }
svg { max-width: 100%; height: auto; }
footer { margin-top: 48px; font-size: 12px; color: var(--muted); }
@media (max-width: 720px) { .grid2 { grid-template-columns: 1fr; } dl.kv { grid-template-columns: 1fr; } }
@media print { main { padding: 0; } h2 { break-after: avoid; } }
</style>
</head>
<body>
<main>
$body
</main>
</body>
</html>
""")


def _badge(status: str) -> str:
    return f'<span class="badge {escape(status)}">{escape(STATUS_LABEL.get(status, status))}</span>'


def _ok(passed: bool, yes: str = "pass", no: str = "fail") -> str:
    return f'<span class="badge {"ok" if passed else "bad"}">{yes if passed else no}</span>'


def _value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".") if abs(value) < 1e6 else f"{value:.4g}"
    if isinstance(value, int):
        return f"{value:,}"
    return escape(str(value))


def _thumbnail(image_id: str) -> str:
    try:
        with Image.open(io.BytesIO(store.image(image_id).data)) as img:
            img = img.convert("RGB")
            img.thumbnail((THUMBNAIL_PX, THUMBNAIL_PX))
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
    except Exception:  # missing or undecodable file: the inventory table reports it
        return '<span class="muted">—</span>'
    return f'<img class="thumb" alt="" src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">'


def _ela_svg(data: dict[str, Any]) -> str:
    """Block z-score heatmap of an ELA record, outlier clusters outlined."""
    grid = data.get("block_z") or []
    if not grid or not grid[0]:
        return ""
    rows, cols, cell = len(grid), len(grid[0]), 8
    threshold = 6.0
    rects = []
    for r, row in enumerate(grid):
        for c, z in enumerate(row):
            t = max(0.0, min(1.0, (z or 0) / (2 * threshold)))  # 0 at the median, 1 at twice the threshold
            light = round(96 - 58 * t)
            color = f"hsl({round(200 - 170 * t)} 80% {light}%)"
            rects.append(f'<rect x="{c * cell}" y="{r * cell}" width="{cell}" height="{cell}" fill="{color}"/>')
    for cl in data.get("clusters", []):
        rects.append(f'<rect x="{cl["col"] * cell}" y="{cl["row"] * cell}" width="{cl["cols"] * cell}" height="{cl["rows"] * cell}" '
                     'fill="none" stroke="#b91c1c" stroke-width="1.5"/>')
    return (f'<figure><svg viewBox="0 0 {cols * cell} {rows * cell}" width="{min(480, cols * cell * 2)}" role="img" '
            f'aria-label="ELA block z-score map">{"".join(rects)}</svg>'
            f'<figcaption class="muted">Block error level relative to the image median ({data.get("block_size")} px blocks, '
            f'quality {data.get("quality")}); outlined: outlier clusters.</figcaption></figure>')


def _analysis_card(r: dict[str, Any], names: dict[str, str]) -> str:
    res = r["result"]
    against = f' vs {escape(names.get(r["reference_image_id"], r["reference_image_id"]))}' if r.get("reference_image_id") else ""
    findings = "".join(
        f'<div class="finding"><strong>{escape(f["finding"])}</strong><span class="kind">{escape(f["kind"])}</span>'
        f'<dl><dt>Evidence</dt><dd>{escape(f["evidence"])}</dd><dt>Interpretation</dt><dd>{escape(f["interpretation"])}</dd>'
        f'<dt>Limitation</dt><dd class="limit">{escape(f["limitation"])}</dd></dl></div>'
        for f in res["findings"]
    ) or '<p class="muted">No findings.</p>'
    measurements = "".join(f"<tr><th>{escape(k.replace('_', ' '))}</th><td class=\"mono\">{_value(v)}</td></tr>"
                           for k, v in res["measurements"].items())
    limitations = "".join(f"<li>{escape(x)}</li>" for x in res["limitations"])
    extra = _ela_svg(res.get("data") or {}) if res["analysis_type"] == "ela" else ""
    return f"""<section class="card" id="{escape(r['record_id'])}">
<header><h3>{escape(ANALYSIS_LABEL.get(res['analysis_type'], res['analysis_type']))}</h3>{_badge(res['status'])}
<span class="meta">{escape(names.get(r['subject_image_id'], r['subject_image_id']))}{against} · {escape(res['timestamp'])} · v{escape(res['analyzer_version'])}</span></header>
<p>{escape(res['interpretation'])}</p>{extra}{findings}
<details><summary class="muted">Measurements</summary><table>{measurements}</table></details>
<details><summary class="muted">Limitations</summary><ul>{limitations}</ul></details>
<p class="muted mono">record {escape(r['record_id'])} · subject SHA-256 {escape(r['subject_sha256'])}</p>
</section>"""


def _tree(parent: str, images: list[dict[str, Any]]) -> str:
    children = [i for i in images if i.get("parent_image_id") == parent]
    if not children:
        return ""
    items = "".join(
        f'<li>↳ <span class="muted">{escape(i["operation_label"] or "")}</span> {escape(i["filename"])} '
        f'<code>{escape(i["sha256"][:16])}…</code>{_tree(i["image_id"], images)}</li>'
        for i in children
    )
    return f"<ul>{items}</ul>"


def render_html(report: dict[str, Any]) -> str:
    ev, chain, summary = report["evidence"], report["chain"], report["summary"]
    verification = chain["verification"]
    images = report["images"]
    names = {i["image_id"]: (f"original ({i['filename']})" if i["role"] == "original" else i["filename"]) for i in images}
    md = ev.get("metadata_results") or {}

    header = f"""<header>
<h1>VERIDIA</h1>
<p class="muted">Investigation report · {escape(report['report_id'])} · generated {escape(report['generated_at'])} by {escape(report['generator']['name'])} {escape(report['generator']['version'])}</p>
</header>
<p class="statement">{escape(report['statement'])}</p>"""

    integrity = f"""<h2>Record integrity</h2>
<dl class="kv">
<dt>Hash chain</dt><dd>{_ok(verification['valid'], 'all checks passed', 'inconsistencies detected')}</dd>
<dt>Events covered</dt><dd>{chain['events_covered']} (sequence 0–{max(chain['events_covered'] - 1, 0)})</dd>
<dt>Chain head</dt><dd><code>{escape(chain['head_hash'] or '—')}</code></dd>
<dt>Algorithm</dt><dd>{escape(chain['algorithm'])}</dd>
</dl>
<table><thead><tr><th>Check</th><th>Result</th><th>Detail</th></tr></thead><tbody>
{''.join(f"<tr><td>{escape(c['label'])}</td><td>{_ok(c['passed'])}</td><td>{escape(c['detail'])}</td></tr>" for c in verification['checks'])}
</tbody></table>
{('<h3 style="margin-top:14px">Issues</h3><ul>' + ''.join(f"<li><strong>{escape(i['kind'])}</strong> {escape(i['detail'])}</li>" for i in verification['issues']) + '</ul>') if verification['issues'] else ''}"""

    exif = (md.get("exif") or {}).get("entries") or []
    meta_rows = "".join(
        f"<tr><th>{escape(label)}</th><td>{_value((md.get(key) or {}).get('value')) if (md.get(key) or {}).get('status') == 'available' else '—'}</td>"
        f"<td class=\"muted\">{escape(str((md.get(key) or {}).get('status', '')).replace('_', ' '))}</td></tr>"
        for key, label in (("format", "Format"), ("mode", "Colour mode"), ("bit_depth", "Bit depth"), ("icc_profile", "ICC profile"))
    )
    exif_rows = "".join(f"<tr><td class=\"muted\">{escape(str(x['ifd']))}</td><td>{escape(str(x['tag']))}</td>"
                        f"<td class=\"mono\">{escape(x['value'] if isinstance(x['value'], str) else json.dumps(x['value']))}</td></tr>"
                        for x in exif)
    identity = f"""<h2>Evidence</h2>
<div class="grid2"><dl class="kv">
<dt>Evidence ID</dt><dd><code>{escape(ev['evidence_id'])}</code></dd>
<dt>File</dt><dd>{escape(ev['original_filename'])}</dd>
<dt>Detected type</dt><dd>{escape(ev['file_type']['mime_type'])}</dd>
<dt>Size · dimensions</dt><dd>{ev['file_size']:,} bytes · {ev['width']}×{ev['height']}</dd>
<dt>Acquired</dt><dd>{escape(ev['created_at'])}</dd>
<dt>SHA-256</dt><dd><code>{escape(ev['sha256'])}</code></dd>
</dl><table><tbody>{meta_rows}</tbody></table></div>
<details><summary class="muted">EXIF ({len(exif)} entries)</summary><table><tbody>{exif_rows or '<tr><td class="muted">No EXIF metadata.</td></tr>'}</tbody></table></details>"""

    inventory_rows = "".join(
        f"<tr><td>{_thumbnail(i['image_id'])}</td><td>{escape(i['filename'])}<div class=\"muted\">"
        f"{'Original evidence' if i['role'] == 'original' else escape(i['operation_label'] or '')}</div></td>"
        f"<td class=\"mono\">{escape(i['image_id'])}<br>{escape(i['sha256'])}</td>"
        f"<td>{i['width']}×{i['height']}<br>{i['size']:,} B</td>"
        f"<td>{_ok(i['file_check'] == 'match', 'hash matches', escape(str(i['file_check'])))}</td></tr>"
        for i in images
    )
    inventory = f"""<h2>Images ({summary['images']})</h2>
<table><thead><tr><th></th><th>Image</th><th>ID · SHA-256</th><th>Size</th><th>Stored file</th></tr></thead><tbody>{inventory_rows}</tbody></table>"""

    ops = "".join(
        f"<tr><td>{escape(describe(r['operation']).label)}<div class=\"muted\">{escape(r['timestamp'])}</div></td>"
        f"<td>{escape(names.get(r['input_image_id'], r['input_image_id']))}<br><code>{escape(r['input_sha256'][:16])}…</code></td>"
        f"<td>{escape(names.get(r['output_image_id'], r['output_image_id']))}<br><code>{escape(r['output_sha256'][:16])}…</code></td>"
        f"<td class=\"mono\">{escape(json.dumps(r['parameters'], ensure_ascii=False))}</td>"
        f"<td class=\"mono nowrap\">MSE {_value(r['metrics']['mse'])}<br>PSNR {_value(r['metrics']['psnr_db']) if r['metrics']['psnr_db'] is not None else '∞'}<br>SSIM {_value(r['metrics']['ssim'])}</td></tr>"
        for r in report["provenance_records"]
    )
    provenance = f"""<h2>Provenance</h2>
<ul class="tree"><li><strong>Original evidence</strong> {escape(ev['original_filename'])} <code>{escape(ev['sha256'][:16])}…</code>{_tree(ev['evidence_id'], images)}</li></ul>
{f'<table style="margin-top:12px"><thead><tr><th>Operation</th><th>Input</th><th>Output</th><th>Parameters</th><th>Metrics (output vs input)</th></tr></thead><tbody>{ops}</tbody></table>' if ops else '<p class="muted">No image-producing operations.</p>'}"""

    by_status = ", ".join(f"{escape(STATUS_LABEL[s])}: {n}" for s, n in summary["analyses_by_status"].items() if n)
    findings_rows = "".join(
        f"<tr><td><a href=\"#{escape(r['record_id'])}\">{escape(ANALYSIS_LABEL.get(r['result']['analysis_type'], r['result']['analysis_type']))}</a></td>"
        f"<td>{escape(names.get(r['subject_image_id'], r['subject_image_id']))}</td><td>{_badge(r['result']['status'])}</td>"
        f"<td>{escape(r['result']['interpretation'])}</td></tr>"
        for r in report["analyses"]
    )
    findings = f"""<h2>Findings summary</h2>
<p class="muted">{summary['analyses']} recorded analysis result(s){': ' + by_status if by_status else ''}. Results are not combined into a verdict.</p>
{f'<table><thead><tr><th>Analysis</th><th>Image</th><th>Status</th><th>Interpretation</th></tr></thead><tbody>{findings_rows}</tbody></table>' if findings_rows else '<p class="muted">No analyses recorded.</p>'}
<h2>Analysis details</h2>
{''.join(_analysis_card(r, names) for r in report['analyses']) or '<p class="muted">None.</p>'}"""

    timeline_rows = "".join(
        f"<tr><td class=\"mono\">{e['sequence']}</td><td class=\"mono\">{escape(e['timestamp'])}</td>"
        f"<td>{escape(e['event_type'].replace('_', ' '))}</td><td>{escape(e['description'])}</td>"
        f"<td class=\"mono\">{escape(e['previous_hash'][:12])}…<br>→ {escape(e['hash'][:12])}…</td></tr>"
        for e in report["timeline"]
    )
    timeline = f"""<h2>Timeline (hash-chained)</h2>
<table><thead><tr><th>#</th><th>Time (UTC)</th><th>Event</th><th>Description</th><th>Previous → hash</th></tr></thead><tbody>{timeline_rows}</tbody></table>"""

    methods = f"""<h2>Methods and limitations</h2>
<p>Analyzers used: {escape(', '.join(summary['analyzers']) or 'none')}.</p>
<ul>{''.join(f'<li>{escape(x)}</li>' for x in report['limitations'])}</ul>
<footer>The JSON version of this report ({escape(report['report_id'])}.json) contains every value shown here plus the structured
analysis data. Re-verify the record at any time with <code>GET /api/provenance/{escape(ev['evidence_id'])}/verify?expected_head={escape(chain['head_hash'] or '')}</code>.</footer>"""

    body = "\n".join([header, integrity, identity, inventory, provenance, findings, timeline, methods])
    return PAGE.substitute(generator=escape(f"{report['generator']['name']} {report['generator']['version']}"),
                           report_id=escape(report["report_id"]), body=body)


# ---- export ------------------------------------------------------------------------------------------

def create_report(evidence_id: str) -> ReportRecord:
    """Generate, store and record a report (JSON + HTML) of the evidence as recorded now."""
    with store.lock:
        evidence = store.evidence(evidence_id)
        report_id = f"rep_{uuid.uuid4().hex}"
        report = build_report(evidence, report_id)
        json_bytes = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8")
        html_bytes = render_html(report).encode("utf-8")
        store.put_report(evidence_id, report_id, "json", json_bytes)
        store.put_report(evidence_id, report_id, "html", html_bytes)
        record = ReportRecord(
            report_id=report_id,
            created_at=now(),
            events_covered=report["chain"]["events_covered"],
            chain_head=report["chain"]["head_hash"] or GENESIS,
            chain_valid=report["chain"]["verification"]["valid"],
            json_sha256=hashlib.sha256(json_bytes).hexdigest(),
            json_size=len(json_bytes),
            html_sha256=hashlib.sha256(html_bytes).hexdigest(),
            html_size=len(html_bytes),
        )
        evidence.reports.append(record)
        record_event(
            evidence,
            "report_exported",
            evidence.evidence_id,
            f"Investigation report exported ({report_id}): covers events 0–{record.events_covered - 1}, "
            f"chain {'verified' if record.chain_valid else 'with inconsistencies'}, JSON SHA-256 {record.json_sha256[:16]}…",
            reference_id=report_id,
            timestamp=record.created_at,
        )
        store.save(evidence)
        return record


def report_file(evidence_id: str, report_id: str, fmt: str) -> tuple[bytes, ReportRecord]:
    evidence = store.evidence(evidence_id)
    record = next((r for r in evidence.reports if r.report_id == report_id), None)
    if record is None:
        raise ServiceError("Report not found.", 404)
    return store.report(evidence_id, report_id, fmt), record

