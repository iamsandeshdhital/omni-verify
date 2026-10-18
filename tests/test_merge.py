"""Span merging (§2.3) - the double-count guard."""

from __future__ import annotations

from omni_verify.merge import Span, merge_spans, total_length


def test_no_spans():
    assert merge_spans([]) == ([], 0)


def test_single_span_unchanged():
    merged, pre = merge_spans([Span(10.0, 20.0, ("FLAG_001",))])
    assert pre == 1
    assert merged == [Span(10.0, 20.0, ("FLAG_001",))]


def test_overlapping_spans_merge_once():
    spans = [Span(0.0, 10.0, ("A",)), Span(5.0, 15.0, ("B",))]
    merged, pre = merge_spans(spans)
    assert pre == 2
    assert len(merged) == 1
    # The whole point: 25 raw units collapse to 15, not 25.
    assert total_length(merged) == 15.0
    assert set(merged[0].flag_ids) == {"A", "B"}


def test_triple_overlap_does_not_triple_count():
    spans = [Span(0.0, 10.0, ("A",)), Span(2.0, 12.0, ("B",)), Span(4.0, 14.0, ("C",))]
    merged, _ = merge_spans(spans)
    assert total_length(merged) == 14.0


def test_disjoint_spans_remain_separate():
    merged, pre = merge_spans([Span(0.0, 10.0, ("A",)), Span(60.0, 70.0, ("B",))])
    assert len(merged) == 2 and pre == 2


def test_gap_within_tolerance_merges():
    # 0.4s apart -> treated as one contiguous claim
    merged, _ = merge_spans([Span(0.0, 10.0, ("A",)), Span(10.4, 20.0, ("B",))])
    assert len(merged) == 1


def test_gap_beyond_tolerance_stays_split():
    merged, _ = merge_spans([Span(0.0, 10.0, ("A",)), Span(11.0, 20.0, ("B",))])
    assert len(merged) == 2


def test_unsorted_input_is_sorted():
    merged, _ = merge_spans([Span(60.0, 70.0, ("B",)), Span(0.0, 10.0, ("A",))])
    assert [s.start for s in merged] == [0.0, 60.0]


def test_contained_span_absorbed():
    merged, _ = merge_spans([Span(0.0, 100.0, ("A",)), Span(10.0, 20.0, ("B",))])
    assert len(merged) == 1
    assert total_length(merged) == 100.0


def test_zero_length_span_is_retained():
    merged, _ = merge_spans([Span(5.0, 5.0, ("A",))])
    assert len(merged) == 1 and merged[0].length == 0.0


def test_end_before_start_raises():
    import pytest

    with pytest.raises(ValueError):
        Span(10.0, 5.0, ("A",))


def test_char_tolerance_merges_adjacent_offsets():
    merged, _ = merge_spans(
        [Span(0, 10, ("A",)), Span(11, 20, ("B",))], kind="char"
    )
    assert len(merged) == 1