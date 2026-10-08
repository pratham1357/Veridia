"""Orchestration of steganalysis: statistical report, known-cover comparison, LSB planes."""

from analysis.core import encode_png
from analysis.steganography import lsb_analysis, steganalysis
from app.schemas.steganalysis import CoverComparison, SteganalysisReport
from app.services.artifacts import load_pair, load_pixels
from app.services.store import store


def report(image_id: str) -> SteganalysisReport:
    return SteganalysisReport(image_id=image_id, **steganalysis.report(load_pixels(image_id)))


def compare_cover(cover_id: str, suspect_id: str) -> CoverComparison:
    cover_px, suspect_px = load_pair(cover_id, suspect_id)
    return CoverComparison(
        cover=store.image(cover_id).summary(),
        suspect=store.image(suspect_id).summary(),
        **lsb_analysis.compare_with_cover(cover_px, suspect_px),
    )


def lsb_plane_png(image_id: str, channel: str) -> bytes:
    return encode_png(lsb_analysis.lsb_plane_image(load_pixels(image_id), channel))
