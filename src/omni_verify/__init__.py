"""omni-verify: multi-platform content integrity engine.

Public surface is deliberately small. Import :func:`analyze` for the full
pipeline, or the lower-level :mod:`omni_verify.ccr` / :mod:`omni_verify.tier`
modules for the scoring primitives.
"""

from __future__ import annotations

from .ccr import Denominator, compute_ccr, select_denominator
from .merge import Span, merge_spans
from .tier import (
    HEAVY_THRESHOLD_PERCENT,
    assign_status,
    assign_tier,
    evaluate_review_gate,
    exceeds_heavy_threshold,
    is_near_threshold,
    penalty_reason,
    tier_actions,
)
from .types import (
    ANALYZER_VERSION,
    SATIRE_DISCLAIMER,
    SCHEMA_VERSION,
    TIER3_OVERLAY,
    AnalysisMode,
    EnforcementState,
    MediaType,
    Severity,
    SourceTier,
    Status,
    Tier,
    Verdict,
)
from .validation import Issue, assert_valid, validate_verdict

__version__ = "0.1.0"

__all__ = [
    "ANALYZER_VERSION",
    "AnalysisMode",
    "Denominator",
    "EnforcementState",
    "HEAVY_THRESHOLD_PERCENT",
    "Issue",
    "MediaType",
    "SATIRE_DISCLAIMER",
    "SCHEMA_VERSION",
    "Severity",
    "SourceTier",
    "Span",
    "Status",
    "TIER3_OVERLAY",
    "Tier",
    "Verdict",
    "__version__",
    "assert_valid",
    "assign_status",
    "assign_tier",
    "compute_ccr",
    "evaluate_review_gate",
    "exceeds_heavy_threshold",
    "is_near_threshold",
    "merge_spans",
    "penalty_reason",
    "select_denominator",
    "tier_actions",
    "validate_verdict",
]