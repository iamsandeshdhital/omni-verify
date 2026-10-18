"""CCR computation and denominator selection (§2.1, §2.2, §2.4)."""

from __future__ import annotations

import pytest

from omni_verify.ccr import (
    RatioError,
    compute_ccr,
    rolling_window_denominator,
    select_denominator,
)
from omni_verify.merge import Span
from omni_verify.types import MediaType


def test_exact_twenty_percent():
    d = select_denominator(
        media_type=MediaType.VIDEO,
        total_duration_seconds=600.0,
        total_payload_characters=None,
    )
    ratio, _, _, _ = compute_ccr([Span(0.0, 120.0, ("A",))], d)
    assert ratio == pytest.approx(20.0)


def test_just_over_threshold():
    d = select_denominator(
        media_type=MediaType.VIDEO,
        total_duration_seconds=600.0,
        total_payload_characters=None,
    )
    ratio, _, _, _ = compute_ccr([Span(0.0, 120.5, ("A",))], d)
    assert ratio > 20.0


def test_overlap_does_not_inflate_ratio():
    """The regression this whole module exists for."""
    d = select_denominator(
        media_type=MediaType.VIDEO,
        total_duration_seconds=100.0,
        total_payload_characters=None,
    )
    naive = 20.0 + 20.0  # two 20s summing to 40% if double-counted
    ratio, _, pre, post = compute_ccr(
        [Span(0.0, 20.0, ("A",)), Span(10.0, 30.0, ("B",))], d
    )
    assert naive == 40.0
    assert ratio == pytest.approx(30.0)  # union is 30s, not 40s
    assert pre == 2 and post == 1


def test_text_denominator_is_characters():
    d = select_denominator(
        media_type=MediaType.SOCIAL_POST,
        total_duration_seconds=None,
        total_payload_characters=1000,
    )
    assert d.kind == "characters"
    ratio, _, _, _ = compute_ccr([Span(0, 250, ("A",))], d, span_kind="char")
    assert ratio == pytest.approx(25.0)


def test_excluded_spans_removed_from_numerator_only():
    """Excluding ad reads must not shrink the denominator - that is the
    gaming vector: pad with exclusions until the ratio collapses."""
    d = select_denominator(
        media_type=MediaType.VIDEO,
        total_duration_seconds=100.0,
        total_payload_characters=None,
    )
    ratio, _, _, _ = compute_ccr(
        [Span(0.0, 25.0, ("A",)), Span(50.0, 75.0, ("B",))],
        d,
        excluded_spans=[Span(0.0, 50.0, ("X",))],
    )
    assert ratio == pytest.approx(25.0)  # only 50-75 survives


def test_exclusion_refragments_a_merged_span():
    d = select_denominator(
        media_type=MediaType.VIDEO,
        total_duration_seconds=100.0,
        total_payload_characters=None,
    )
    ratio, merged, _, _ = compute_ccr(
        [Span(0.0, 50.0, ("A",))],
        d,
        excluded_spans=[Span(20.0, 30.0, ("X",))],
    )
    assert ratio == pytest.approx(40.0)
    assert len(merged) == 2


def test_ratio_capped_at_100():
    d = rolling_window_denominator(100.0)
    ratio, _, _, _ = compute_ccr([Span(0.0, 250.0, ("A",))], d)
    assert ratio == 100.0


def test_zero_duration_rejected():
    with pytest.raises(RatioError):
        select_denominator(
            media_type=MediaType.VIDEO,
            total_duration_seconds=0,
            total_payload_characters=None,
        )


def test_text_requires_characters():
    with pytest.raises(RatioError):
        select_denominator(
            media_type=MediaType.ARTICLE,
            total_duration_seconds=60.0,
            total_payload_characters=None,
        )


def test_sponsor_reads_count_in_denominator():
    """§2.2: denominator is the payload the viewer actually consumed."""
    d = select_denominator(
        media_type=MediaType.VIDEO,
        total_duration_seconds=120.0,  # 100s content + 20s sponsor read
        total_payload_characters=None,
    )
    ratio, _, _, _ = compute_ccr([Span(0.0, 30.0, ("A",))], d)
    assert ratio == pytest.approx(25.0)