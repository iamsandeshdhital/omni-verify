"""Tier boundaries and the review gate (§2.5, §3.4, §6)."""

from __future__ import annotations

import pytest

from omni_verify.tier import (
    HEAVY_THRESHOLD_PERCENT,
    FlagSummary,
    assign_status,
    assign_tier,
    evaluate_review_gate,
    exceeds_heavy_threshold,
    is_near_threshold,
    margin_note,
    penalty_reason,
    tier_actions,
)
from omni_verify.types import AnalysisMode, EnforcementState, Status, Tier


@pytest.mark.parametrize(
    ("ccr", "expected"),
    [
        (0.0, Tier.T1),
        (5.0, Tier.T1),       # boundary: <=5 is Tier 1
        (5.01, Tier.T2),
        (19.99, Tier.T2),
        (20.0, Tier.T2),      # THE boundary: exactly 20.0 is NOT Tier 3
        (20.01, Tier.T3),
        (25.0, Tier.T3),
        (100.0, Tier.T3),
    ],
)
def test_tier_boundaries(ccr, expected):
    assert assign_tier(ccr) is expected


def test_threshold_is_strictly_greater():
    assert exceeds_heavy_threshold(20.0) is False
    assert exceeds_heavy_threshold(20.0001) is True
    assert HEAVY_THRESHOLD_PERCENT == 20.0


def test_negative_ccr_rejected():
    with pytest.raises(ValueError):
        assign_tier(-1.0)


def test_near_threshold_band():
    assert is_near_threshold(19.0) is True
    assert is_near_threshold(20.0) is True
    assert is_near_threshold(18.9) is False
    assert is_near_threshold(20.1) is False


def test_margin_note_only_in_band():
    assert margin_note(19.5) is not None
    assert margin_note(10.0) is None
    assert "20.0%" in margin_note(19.5)


def test_status_derivation():
    assert assign_status(0.0, Tier.T1) is Status.CLEAN
    assert assign_status(10.0, Tier.T2) is Status.PARTIALLY_COMPROMISED
    assert assign_status(25.0, Tier.T3) is Status.HEAVILY_PENALIZED


def test_tier3_actions_include_all_four():
    actions = tier_actions(Tier.T3)
    assert set(actions) == {
        "FULL_DEMONETIZATION",
        "ALGORITHMIC_SUPPRESSION",
        "ACCOUNT_STRIKE_ISSUED",
        "FULL_FRAME_WARNING_OVERLAY",
    }


def test_tier1_has_no_reach_or_money_penalty():
    actions = tier_actions(Tier.T1)
    assert "FULL_DEMONETIZATION" not in actions
    assert actions == ["INLINE_CONTEXT_CARD"]


def test_clean_low_stakes_executes():
    gate = evaluate_review_gate(
        flags=[FlagSummary("SPORTS_ATHLETICS", "MISLEADING", "MINOR", 5.0)],
        tier=Tier.T2,
        analysis_mode=AnalysisMode.FULL,
        confidence=0.9,
    )
    assert gate.requires_human_review is False
    assert gate.state is EnforcementState.EXECUTING


def test_high_stakes_false_verdict_queues():
    gate = evaluate_review_gate(
        flags=[FlagSummary("MEDICAL_HEALTH", "FALSE", "CRITICAL", 40.0)],
        tier=Tier.T2,
        analysis_mode=AnalysisMode.FULL,
        confidence=0.95,
    )
    assert gate.requires_human_review is True
    assert gate.state is EnforcementState.QUEUED
    assert any("high-stakes" in r for r in gate.reasons)


def test_legal_and_political_also_high_stakes():
    for cat in ("LEGAL_SAFETY", "POLITICS_GOVT"):
        gate = evaluate_review_gate(
            flags=[FlagSummary(cat, "FABRICATED", "CRITICAL", 10.0)],
            tier=Tier.T1,
            analysis_mode=AnalysisMode.FULL,
            confidence=0.99,
        )
        assert gate.requires_human_review is True


def test_low_confidence_queues_even_when_tier1():
    gate = evaluate_review_gate(
        flags=[FlagSummary("SCIENCE_TECH", "UNVERIFIED", "MINOR", 3.0)],
        tier=Tier.T1,
        analysis_mode=AnalysisMode.FULL,
        confidence=0.5,
    )
    assert gate.requires_human_review is True


def test_rolling_window_always_provisional():
    gate = evaluate_review_gate(
        flags=[FlagSummary("SPORTS_ATHLETICS", "MISLEADING", "MINOR", 5.0)],
        tier=Tier.T1,
        analysis_mode=AnalysisMode.ROLLING_WINDOW,
        confidence=0.95,
    )
    assert gate.requires_human_review is True
    assert gate.state is EnforcementState.QUEUED
    assert any("provisional" in r for r in gate.reasons)


def test_tier3_always_queues():
    gate = evaluate_review_gate(
        flags=[FlagSummary("ECONOMICS_FINANCE", "MISLEADING", "MODERATE", 30.0)],
        tier=Tier.T3,
        analysis_mode=AnalysisMode.FULL,
        confidence=0.99,
    )
    assert gate.requires_human_review is True


def test_penalty_reason_states_margin():
    reason = penalty_reason(25.0, Tier.T3)
    assert "25.0%" in reason and "20.0%" in reason and "5.0 percentage" in reason