"""Document factories.

A plain factory rather than a fixture, because tests need to import and mutate
copies directly (``test_validation`` calls ``valid_doc()`` at module scope).
"""

from __future__ import annotations

import copy
from typing import Any

from omni_verify.types import SATIRE_DISCLAIMER, SCHEMA_VERSION

T1_SOURCE = {
    "source_name": "Cochrane Database of Systematic Reviews",
    "source_tier": "T1",
    "evidence_summary": "No association between the vaccine and autism.",
    "reference_url_or_doi": "10.1002/14651858.CD005125",
    "published_date": "2014-02-28",
}


def video_doc(ccr: float = 25.0) -> dict[str, Any]:
    """A internally-consistent Tier 3 video verdict at a given CCR."""
    seconds = 600.0
    return {
        "schema_version": SCHEMA_VERSION,
        "stream_metadata": {
            "stream_id": "STRM_TEST",
            "media_type": "video",
            "platform": "YouTube",
            "genre_category": "MEDICAL_HEALTH",
            "analysis_mode": "FULL",
            "duration_is_estimate": False,
            "total_duration_seconds": seconds,
            "total_payload_characters": None,
            "word_count": None,
            "compromised_duration_seconds": round(seconds * ccr / 100.0, 3),
            "compromised_characters": None,
            "compromised_content_ratio_percent": ccr,
            "overall_trust_score": round(100.0 - ccr, 2),
            "status": (
                "HEAVILY_PENALIZED" if ccr > 20.0
                else "PARTIALLY_COMPROMISED" if ccr > 0
                else "CLEAN"
            ),
        },
        "analyzer": {
            "analyzer_version": "OMNI-VERIFY-1.1.0",
            "analyzed_at": "2026-10-18T00:00:00Z",
            "confidence": 0.85,
            "retrieval_available": True,
            "search_queries": [],
            "sources_retrieved": 1,
        },
        "satire_protocol": {
            "is_satire_or_entertainment": False,
            "deception_type": None,
            "disclosure_present": None,
            "requires_mandatory_disclaimer": False,
            "mandatory_disclaimer_text": SATIRE_DISCLAIMER,
        },
        "penalization_enforcement": {
            "tier": (
                "TIER_3_HEAVY_PENALTY" if ccr > 20.0
                else "TIER_2_MODERATE" if ccr > 5.0
                else "TIER_1_MINOR"
            ),
            "exceeds_heavy_penalty_threshold": ccr > 20.0,
            "enforcement_state": "QUEUED",
            "requires_human_review": True,
            "actions_triggered": (
                [
                    "FULL_DEMONETIZATION",
                    "ALGORITHMIC_SUPPRESSION",
                    "ACCOUNT_STRIKE_ISSUED",
                    "FULL_FRAME_WARNING_OVERLAY",
                ]
                if ccr > 20.0
                else ["SEGMENT_WARNING_BANNER", "PARTIAL_MONETIZATION_HOLD"]
                if ccr > 5.0
                else ["INLINE_CONTEXT_CARD"]
            ),
            "penalty_reason": "test fixture",
            "appeal_path": "/appeals/content-integrity/STRM_TEST",
        },
        "precision_flags": [
            {
                "flag_id": "FLAG_001",
                "location": {
                    "timestamp_start": "00:01:10.000",
                    "timestamp_end": "00:03:40.000",
                    "character_start": None,
                    "character_end": None,
                    "timing_precision": "EXACT",
                    "excerpt": "The vaccine causes autism.",
                },
                "category": "MEDICAL_HEALTH",
                "severity": "CRITICAL",
                "claim_analysis": {
                    "statement_made": "The vaccine causes autism.",
                    "original_claim": "The vaccine causes autism.",
                    "verified_fact": "Large cohort studies find no association.",
                    "delta": "Original asserts causation; record shows no association.",
                    "verdict": "FALSE",
                    "explanation": "Extensively refuted in peer-reviewed literature.",
                    "confidence": 0.95,
                    "retrieval_performed": True,
                    "fact_valid_as_of": "2026-10-18",
                    "counter_evidence": [dict(T1_SOURCE)],
                },
                "ui_action_trigger": "OVERLAY_WARNING_FLAG",
            }
        ],
        "bias_flags": [],
    }


def valid_doc() -> dict[str, Any]:
    """A deep copy, safe to mutate inside a test."""
    return copy.deepcopy(video_doc(25.0))


def clean_doc() -> dict[str, Any]:
    """CCR 0: no flags, CLEAN status, Tier 1."""
    doc = video_doc(0.0)
    doc["precision_flags"] = []
    doc["penalization_enforcement"]["requires_human_review"] = False
    doc["penalization_enforcement"]["enforcement_state"] = "EXECUTING"
    doc["stream_metadata"]["compromised_duration_seconds"] = 0.0
    return doc