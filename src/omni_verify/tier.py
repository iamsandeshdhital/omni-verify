"""Tier assignment, the 20% boundary, and the §6 review gate."""

from __future__ import annotations

from dataclasses import dataclass, field

from .types import (
    MUTE_ELIGIBLE_CATEGORIES,
    MUTE_MIN_SEGMENT_SECONDS,
    AnalysisMode,
    EnforcementState,
    EVIDENCE_BACKED_VERDICTS,
    HIGH_STAKES_CATEGORIES,
    Severity,
    Status,
    Tier,
    Verdict,
)

#: Tier 3 requires strictly greater. CCR of exactly 20.0 is Tier 2.
#: Change this and the §2.5 table together - they are duplicated deliberately.
HEAVY_THRESHOLD_PERCENT = 20.0

#: Observational band. No action, but reviewers see how close a call was.
NEAR_THRESHOLD_MARGIN = 1.0

#: §6. Below this, findings route to review rather than executing.
MIN_EXECUTING_CONFIDENCE = 0.70

TIER1_MAX = 5.0


def assign_tier(ccr_percent: float) -> Tier:
    """Map CCR to tier using the strict ``> 20.0`` boundary."""
    if ccr_percent < 0:
        raise ValueError("CCR cannot be negative")
    if ccr_percent > HEAVY_THRESHOLD_PERCENT:
        return Tier.T3
    if ccr_percent > TIER1_MAX:
        return Tier.T2
    return Tier.T1


def exceeds_heavy_threshold(ccr_percent: float) -> bool:
    return ccr_percent > HEAVY_THRESHOLD_PERCENT


def is_near_threshold(ccr_percent: float) -> bool:
    """``19.0 <= CCR <= 20.0``. Observational only."""
    return (
        HEAVY_THRESHOLD_PERCENT - NEAR_THRESHOLD_MARGIN
        <= ccr_percent
        <= HEAVY_THRESHOLD_PERCENT
    )


def assign_status(ccr_percent: float, tier: Tier) -> Status:
    """Integrity status. Satire is orthogonal and never appears here (§3.4)."""
    if ccr_percent == 0:
        return Status.CLEAN
    if tier is Tier.T3:
        return Status.HEAVILY_PENALIZED
    return Status.PARTIALLY_COMPROMISED


def tier_actions(tier: Tier) -> list[str]:
    """Canonical action set before platform-capability filtering (§L5)."""
    if tier is Tier.T1:
        return ["INLINE_CONTEXT_CARD"]
    if tier is Tier.T2:
        return [
            "SEGMENT_WARNING_BANNER",
            "PARTIAL_MONETIZATION_HOLD",
        ]
    return [
        "FULL_DEMONETIZATION",
        "ALGORITHMIC_SUPPRESSION",
        "ACCOUNT_STRIKE_ISSUED",
        "FULL_FRAME_WARNING_OVERLAY",
    ]


def margin_note(ccr_percent: float) -> str | None:
    if not is_near_threshold(ccr_percent):
        return None
    return (
        f"CCR {ccr_percent:.1f}% is within {NEAR_THRESHOLD_MARGIN:.1f} percentage point(s) "
        f"of the {HEAVY_THRESHOLD_PERCENT:.1f}% threshold. Tier 2 applies at exactly "
        f"{HEAVY_THRESHOLD_PERCENT:.1f}%; Tier 3 requires strictly greater."
    )


def penalty_reason(ccr_percent: float, tier: Tier) -> str:
    if tier is not Tier.T3:
        note = margin_note(ccr_percent)
        return note or (
            f"Compromised content ratio {ccr_percent:.1f}% is within the "
            f"{HEAVY_THRESHOLD_PERCENT:.1f}% tolerance."
        )
    margin = ccr_percent - HEAVY_THRESHOLD_PERCENT
    return (
        f"Compromised and unverified content ratio ({ccr_percent:.1f}%) exceeded the maximum "
        f"{HEAVY_THRESHOLD_PERCENT:.1f}% safety threshold by {margin:.1f} percentage points."
    )


@dataclass(slots=True)
class FlagSummary:
    """Minimal projection of a precision flag, for gate evaluation."""

    category: str
    verdict: str
    severity: str
    segment_seconds: float


@dataclass(slots=True)
class ReviewGate:
    requires_human_review: bool
    state: EnforcementState
    reasons: list[str] = field(default_factory=list)


def evaluate_review_gate(
    *,
    flags: list[FlagSummary],
    tier: Tier,
    analysis_mode: AnalysisMode,
    confidence: float,
) -> ReviewGate:
    """§6. Queue rather than execute when harm is hard to reverse, evidence is
    thin, or the verdict is high-stakes."""
    reasons: list[str] = []

    high_stakes = [
        f for f in flags
        if f.category in HIGH_STAKES_CATEGORIES
        and f.verdict in {Verdict.FALSE.value, Verdict.FABRICATED.value}
    ]
    if high_stakes:
        reasons.append(
            f"{len(high_stakes)} high-stakes finding(s) in "
            f"{sorted({f.category for f in high_stakes})} with a definitive verdict."
        )

    if tier is Tier.T3:
        reasons.append("Tier 3 trigger; full demonetization and account strike are costly to unwind.")

    if analysis_mode is AnalysisMode.ROLLING_WINDOW:
        reasons.append("Rolling-window CCR on a live stream is provisional (§2.2).")

    if confidence < MIN_EXECUTING_CONFIDENCE:
        reasons.append(f"Analyzer confidence {confidence:.2f} below {MIN_EXECUTING_CONFIDENCE:.2f}.")

    if not reasons:
        return ReviewGate(False, EnforcementState.EXECUTING)

    return ReviewGate(True, EnforcementState.QUEUED, reasons)


def severity_ui_action(
    *,
    category: str,
    severity: str,
    verdict: str,
    segment_seconds: float,
    is_audio_claim: bool,
    mute_eligible_categories: frozenset[str] | None = None,
    mute_min_seconds: float | None = None,
) -> str:
    """§4.1 severity -> UI action. MUTE_RANGE requires every condition."""
    eligible = mute_eligible_categories or MUTE_ELIGIBLE_CATEGORIES
    min_seconds = mute_min_seconds if mute_min_seconds is not None else MUTE_MIN_SEGMENT_SECONDS

    if (
        severity == Severity.CRITICAL.value
        and is_audio_claim
        and category in eligible
        and segment_seconds >= min_seconds
    ):
        return "MUTE_RANGE"

    if severity in {Severity.MODERATE.value, Severity.HIGH.value, Severity.CRITICAL.value}:
        return "OVERLAY_WARNING_FLAG"

    return "PIN_CONTEXT_CARD"


__all__ = [
    "HEAVY_THRESHOLD_PERCENT",
    "NEAR_THRESHOLD_MARGIN",
    "MIN_EXECUTING_CONFIDENCE",
    "FlagSummary",
    "ReviewGate",
    "assign_status",
    "assign_tier",
    "evaluate_review_gate",
    "exceeds_heavy_threshold",
    "is_near_threshold",
    "margin_note",
    "penalty_reason",
    "severity_ui_action",
    "tier_actions",
    "EVIDENCE_BACKED_VERDICTS",
]