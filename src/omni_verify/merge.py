"""Span merging (§2.3).

Mandatory before ratio summation. Overlapping flagged segments that are summed
naively double-count, which inflates CCR and can push a borderline video across
the 20% threshold on nothing but an artifact of segmentation.

Policy: sort by start, then merge any spans that overlap *or* whose gap is
within tolerance. A gap-tolerant merge is safe here because content separated by
less than half a second of clean audio is not meaningfully a separate claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SpanKind = Literal["time", "char"]

DEFAULT_TIME_TOLERANCE = 0.5
DEFAULT_CHAR_TOLERANCE = 1


@dataclass(frozen=True, slots=True)
class Span:
    """A half-open interval [start, end) over the payload's coordinate space."""

    start: float
    end: float
    flag_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"span end {self.end} precedes start {self.start}")

    @property
    def length(self) -> float:
        return self.end - self.start


def merge_spans(
    spans: list[Span],
    kind: SpanKind = "time",
    tolerance: float | None = None,
) -> tuple[list[Span], int]:
    """Merge overlapping or near-adjacent spans.

    Returns ``(merged, pre_merge_count)`` so the audit block can report how much
    deduplication occurred (§5 ``audit.segments_pre_merge``).
    """
    if not spans:
        return [], 0

    tol = tolerance if tolerance is not None else (
        DEFAULT_TIME_TOLERANCE if kind == "time" else DEFAULT_CHAR_TOLERANCE
    )

    ordered = sorted(spans, key=lambda s: (s.start, s.end))
    merged: list[Span] = [ordered[0]]

    for current in ordered[1:]:
        last = merged[-1]
        # Touching or overlapping, or separated by no more than `tol`.
        if current.start - tol <= last.end:
            merged[-1] = Span(
                start=last.start,
                end=max(last.end, current.end),
                flag_ids=last.flag_ids + current.flag_ids,
            )
        else:
            merged.append(current)

    return merged, len(spans)


def total_length(spans: list[Span]) -> float:
    """Sum merged span lengths. Must only be called on already-merged input."""
    return sum(s.length for s in spans)