"""Compromised Content Ratio (§2.1, §2.2, §2.4)."""

from __future__ import annotations

from dataclasses import dataclass

from .merge import Span, merge_spans, total_length
from .types import AnalysisMode, MediaType

ROLLING_WINDOW_SECONDS = 600.0


class RatioError(ValueError):
    """Raised when the denominator is unusable."""


@dataclass(frozen=True, slots=True)
class Denominator:
    value: float
    kind: Literal["duration_seconds", "characters"]
    is_estimate: bool

    @property
    def is_text_based(self) -> bool:
        return self.kind == "characters"


TEXT_MEDIA_TYPES = frozenset({MediaType.ARTICLE, MediaType.SOCIAL_POST, MediaType.CAPTION})


def select_denominator(
    *,
    media_type: MediaType,
    total_duration_seconds: float | None,
    total_payload_characters: int | None,
) -> Denominator:
    """Pick the denominator per §2.2.

    Video/audio denominators include sponsor reads and ad breaks: that is the
    payload the viewer actually consumed. Text denominators are raw code points
    as received - no normalization, no markdown stripping - so any ratio is
    independently auditable against the raw payload.
    """
    if media_type in TEXT_MEDIA_TYPES:
        if total_payload_characters is None or total_payload_characters <= 0:
            raise RatioError(f"{media_type} requires a positive total_payload_characters")
        return Denominator(float(total_payload_characters), "characters", False)

    if total_duration_seconds is None or total_duration_seconds <= 0:
        raise RatioError(f"{media_type} requires a positive total_duration_seconds")

    return Denominator(float(total_duration_seconds), "duration_seconds", False)


def compute_ccr(
    flagged_spans: list[Span],
    denominator: Denominator,
    *,
    excluded_spans: list[Span] | None = None,
    span_kind: Literal["time", "char"] = "time",
) -> tuple[float, list[Span], int, int]:
    """Return ``(ratio_percent, merged_spans, pre_merge_count, post_merge_count)``.

    ``excluded_spans`` (§2.4) are removed from the *numerator* only. The
    denominator stays the full payload: excluding bridge filler from the total
    would let a creator shrink the denominator by padding with ad reads, which
    is precisely the gaming vector the ratio exists to close.
    """
    excluded = excluded_spans or []
    # Merge first, then subtract exclusions. Dropping a partially-overlapping
    # span wholesale would silently discard a flag because an ad break sits in
    # the middle of it - the opposite of what §2.4 intends.
    merged_all, pre_merge = merge_spans(flagged_spans, kind=span_kind)
    merged = _subtract(merged_all, excluded) if excluded else merged_all

    flagged_total = total_length(merged)
    ratio = (flagged_total / denominator.value) * 100.0
    ratio = min(ratio, 100.0)  # span merges cannot legitimately exceed the payload

    return ratio, merged, pre_merge, len(merged)


def rolling_window_denominator(window_seconds: float = ROLLING_WINDOW_SECONDS) -> Denominator:
    """§2.2 live-stream case. Flagged as an estimate; never auto-strikes alone."""
    return Denominator(float(window_seconds), "duration_seconds", True)


def _overlaps_any(span: Span, others: list[Span]) -> bool:
    return any(span.start < o.end and o.start < span.end for o in others)


def _subtract(spans: list[Span], holes: list[Span]) -> list[Span]:
    """Remove ``holes`` from ``spans``, re-fragmenting where necessary."""
    result: list[Span] = []
    for span in spans:
        pieces = [span]
        for hole in holes:
            nxt: list[Span] = []
            for piece in pieces:
                if not (piece.start < hole.end and hole.start < piece.end):
                    nxt.append(piece)
                    continue
                if hole.start > piece.start:
                    nxt.append(Span(piece.start, min(hole.start, piece.end), piece.flag_ids))
                if hole.end < piece.end:
                    nxt.append(Span(max(hole.end, piece.start), piece.end, piece.flag_ids))
            pieces = nxt
        result.extend(p for p in pieces if p.length > 0)
    return result