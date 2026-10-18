"""Pipeline assembly: analysis results -> validated canonical verdict (§5).

This module owns construction of the canonical document. It deliberately does
*not* perform claim extraction or retrieval - those are L2/L3 concerns and are
pluggable. What it guarantees is that any set of findings, however they were
produced, is merged, scored, tiered, review-gated, and emitted consistently.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .ccr import compute_ccr, rolling_window_denominator, select_denominator
from .ingest.canonical import CanonicalContent
from .merge import Span
from .render.vtt import overlay_spec, render_vtt
from .tier import (
    assign_status,
    assign_tier,
    evaluate_review_gate,
    exceeds_heavy_threshold,
    is_near_threshold,
    margin_note,
    penalty_reason,
    severity_ui_action,
    tier_actions,
)
from .types import (
    ANALYZER_VERSION,
    SATIRE_DISCLAIMER,
    SCHEMA_VERSION,
    AnalysisMode,
    EnforcementState,
    Genre,
    MediaType,
    SatireDeception,
    SourceTier,
    Tier,
    Verdict,
)
from .validation import validate_verdict


@dataclass(slots=True)
class RawFlag:
    """A finding as produced by L2/L3, before merging and scoring."""

    start: float
    end: float
    category: str
    severity: str
    verdict: str
    statement_made: str = ""
    original_claim: str = ""
    verified_fact: str = ""
    explanation: str = ""
    confidence: float = 0.5
    retrieval_performed: bool = False
    counter_evidence: list[dict[str, Any]] = field(default_factory=list)
    is_audio_claim: bool = False
    timing_precision: str = "EXACT"

    def span(self, flag_id: str) -> Span:
        return Span(self.start, self.end, (flag_id,))


@dataclass(slots=True)
class RawBiasFlag:
    code: str
    original_claim: str
    verified_fact: str
    why_biased: str
    category: str = "GENERAL"


def build_verdict(
    *,
    content: CanonicalContent,
    flags: list[RawFlag],
    bias_flags: list[RawBiasFlag] | None = None,
    genre: str = Genre.MULTI.value,
    analysis_mode: AnalysisMode = AnalysisMode.FULL,
    satire: bool = False,
    disclosure_present: bool | None = None,
    analyzer_confidence: float = 0.8,
    retrieval_available: bool = True,
    search_queries: list[str] | None = None,
    sources_retrieved: int = 0,
    excluded_spans: list[Span] | None = None,
    stream_timestamp: str | None = None,
    notes: list[str] | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Assemble and (by default) validate a canonical verdict document."""
    is_text = content.media_type in {
        MediaType.ARTICLE, MediaType.SOCIAL_POST, MediaType.CAPTION
    }

    denominator = (
        select_denominator(
            media_type=content.media_type,
            total_duration_seconds=content.total_duration_seconds,
            total_payload_characters=content.total_payload_characters or None,
        )
        if analysis_mode is AnalysisMode.FULL
        else rolling_window_denominator()
    )

    raw_spans = [f.span(f"FLAG_{i:03d}") for i, f in enumerate(flags, start=1)]
    span_kind = "char" if is_text else "time"

    ratio, merged, pre_merge, post_merge = compute_ccr(
        raw_spans,
        denominator,
        excluded_spans=excluded_spans,
        span_kind=span_kind,
    )

    tier = assign_tier(ratio)
    exceeds = exceeds_heavy_threshold(ratio)
    status = assign_status(ratio, tier)

    merged_flag_ids = {fid for span in merged for fid in span.flag_ids}
    severity_lookup = {
        f"FLAG_{i:03d}": f for i, f in enumerate(flags, start=1)
    }

    precision_flags: list[dict[str, Any]] = []
    for i, flag in enumerate(flags, start=1):
        flag_id = f"FLAG_{i:03d}"
        if flag_id not in merged_flag_ids:
            continue  # this segment was fully excluded per §2.4

        analysis: dict[str, Any] = {
            "statement_made": flag.statement_made,
            "original_claim": flag.original_claim or flag.statement_made,
            "verified_fact": flag.verified_fact,
            "delta": _delta(flag),
            "verdict": flag.verdict,
            "explanation": flag.explanation,
            "confidence": flag.confidence,
            "retrieval_performed": flag.retrieval_performed,
            "fact_valid_as_of": (stream_timestamp or "")[:10] or None,
            "counter_evidence": flag.counter_evidence,
        }

        precision_flags.append(
            {
                "flag_id": flag_id,
                "location": {
                    "timestamp_start": None if is_text else _ts(flag.start),
                    "timestamp_end": None if is_text else _ts(flag.end),
                    "character_start": int(flag.start) if is_text else None,
                    "character_end": int(flag.end) if is_text else None,
                    "timing_precision": "NONE" if is_text else flag.timing_precision,
                    "excerpt": flag.statement_made,
                },
                "category": flag.category,
                "severity": flag.severity,
                "claim_analysis": analysis,
                "ui_action_trigger": severity_ui_action(
                    category=flag.category,
                    severity=flag.severity,
                    verdict=flag.verdict,
                    segment_seconds=flag.end - flag.start,
                    is_audio_claim=flag.is_audio_claim,
                ),
            }
        )

    gate = evaluate_review_gate(
        flags=[
            _FlagSummary(f.category, f.verdict, f.severity, f.end - f.start)
            for i, f in enumerate(flags, start=1)
            if f"FLAG_{i:03d}" in merged_flag_ids
        ],
        tier=tier,
        analysis_mode=analysis_mode,
        confidence=analyzer_confidence,
    )

    deception = None
    if satire and not disclosure_present:
        deception = SatireDeception.UNDISCLOSED_FICTION.value

    doc: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "stream_metadata": {
            "stream_id": content.stream_id,
            "media_type": content.media_type.value,
            "platform": content.platform,
            "genre_category": genre,
            "analysis_mode": analysis_mode.value,
            "duration_is_estimate": analysis_mode is AnalysisMode.ROLLING_WINDOW,
            "total_duration_seconds": (
                None if is_text else content.total_duration_seconds
            ),
            "total_payload_characters": (
                content.total_payload_characters if is_text else None
            ),
            "word_count": content.word_count if is_text else None,
            "compromised_duration_seconds": (
                None if is_text else round(sum(s.length for s in merged), 3)
            ),
            "compromised_characters": (
                int(sum(s.length for s in merged)) if is_text else None
            ),
            "compromised_content_ratio_percent": round(ratio, 2),
            "overall_trust_score": round(100.0 - ratio, 2),
            "status": status.value,
        },
        "analyzer": {
            "analyzer_version": ANALYZER_VERSION,
            "analyzed_at": stream_timestamp or "",
            "confidence": analyzer_confidence,
            "retrieval_available": retrieval_available,
            "search_queries": search_queries or [],
            "sources_retrieved": sources_retrieved,
        },
        "satire_protocol": {
            "is_satire_or_entertainment": satire,
            "deception_type": deception,
            "disclosure_present": disclosure_present,
            "requires_mandatory_disclaimer": satire and not disclosure_present,
            "mandatory_disclaimer_text": SATIRE_DISCLAIMER,
        },
        "penalization_enforcement": {
            "tier": tier.value,
            "exceeds_heavy_penalty_threshold": exceeds,
            "enforcement_state": gate.state.value,
            "requires_human_review": gate.requires_human_review,
            "actions_triggered": tier_actions(tier),
            "penalty_reason": penalty_reason(ratio, tier),
            "review_reasons": gate.reasons,
            "appeal_path": f"/appeals/content-integrity/{content.stream_id}",
        },
        "precision_flags": precision_flags,
        "bias_flags": [
            {
                "bias_code": b.code,
                "category": b.category,
                "original_claim": b.original_claim,
                "verified_fact": b.verified_fact,
                "why_biased": b.why_biased,
                "counts_toward_ccr": False,
            }
            for b in (bias_flags or [])
        ],
        "audit": {
            "segments_pre_merge": pre_merge,
            "segments_post_merge": post_merge,
            "near_threshold": is_near_threshold(ratio),
            "threshold_margin_note": margin_note(ratio),
            "excluded_from_ratio": [
                {"start": s.start, "end": s.end} for s in (excluded_spans or [])
            ],
            "notes": list(notes or []) + list(content.notes),
        },
    }

    if strict:
        issues = validate_verdict(doc)
        if issues:
            raise ValueError(
                "canonical verdict failed validation:\n  "
                + "\n  ".join(str(i) for i in issues)
            )

    return doc


@dataclass(slots=True)
class _FlagSummary:
    category: str
    verdict: str
    severity: str
    segment_seconds: float


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _delta(flag: RawFlag) -> str:
    if not flag.original_claim or not flag.verified_fact:
        return ""
    return (
        f"Original asserts '{flag.original_claim[:160]}'; "
        f"verified record shows '{flag.verified_fact[:160]}'."
    )


__all__ = ["RawFlag", "RawBiasFlag", "build_verdict", "render_vtt", "overlay_spec"]