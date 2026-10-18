"""Fail-closed validation rules R1-R10."""

from __future__ import annotations

import pytest

from omni_verify.validation import parse_timestamp, validate_verdict
from tests.factories import valid_doc


def test_valid_document_passes():
    assert validate_verdict(valid_doc()) == []


def test_r1_false_without_evidence_rejected():
    doc = valid_doc()
    flag = doc["precision_flags"][0]
    flag["claim_analysis"]["verdict"] = "FALSE"
    flag["claim_analysis"]["counter_evidence"] = []
    issues = validate_verdict(doc)
    assert any(i.rule == "R1" for i in issues)


def test_r2_false_with_only_t4_rejected():
    """Four T4 blogs citing each other are still four T4 blogs."""
    doc = valid_doc()
    flag = doc["precision_flags"][0]
    flag["claim_analysis"]["verdict"] = "FALSE"
    flag["claim_analysis"]["counter_evidence"] = [
        {"source_name": "some blog", "source_tier": "T4", "evidence_summary": "..."}
    ]
    issues = validate_verdict(doc)
    assert any(i.rule in {"R2", "R3"} for i in issues)


def test_r3_t3_alone_cannot_support_false():
    doc = valid_doc()
    flag = doc["precision_flags"][0]
    flag["claim_analysis"]["verdict"] = "FALSE"
    flag["claim_analysis"]["counter_evidence"] = [
        {"source_name": "a newspaper", "source_tier": "T3", "evidence_summary": "..."}
    ]
    assert any(i.rule == "R3" for i in validate_verdict(doc))


def test_t2_source_does_support_false():
    doc = valid_doc()
    flag = doc["precision_flags"][0]
    flag["claim_analysis"]["verdict"] = "FALSE"
    flag["claim_analysis"]["counter_evidence"] = [
        {"source_name": "wire service", "source_tier": "T2", "evidence_summary": "..."}
    ]
    assert validate_verdict(doc) == []


def test_r4_retrieval_failure_caps_verdict():
    doc = valid_doc()
    doc["analyzer"]["retrieval_available"] = False
    doc["precision_flags"][0]["claim_analysis"]["verdict"] = "FALSE"
    issues = validate_verdict(doc)
    assert any(i.rule == "R4" for i in issues)


def test_r4_allows_unverified_without_retrieval():
    doc = valid_doc()
    doc["analyzer"]["retrieval_available"] = False
    doc["precision_flags"][0]["claim_analysis"]["verdict"] = "UNVERIFIED"
    assert not any(i.rule == "R4" for i in validate_verdict(doc))


def test_r5_unknown_verdict_rejected():
    doc = valid_doc()
    doc["precision_flags"][0]["claim_analysis"]["verdict"] = "PROBABLY_FALSE"
    assert any(i.rule == "R5" for i in validate_verdict(doc))


def test_r5_supported_is_not_a_verdict():
    doc = valid_doc()
    doc["precision_flags"][0]["claim_analysis"]["verdict"] = "SUPPORTED"
    assert any(i.rule == "R5" for i in validate_verdict(doc))


def test_r6_tier_inconsistent_with_ccr():
    doc = valid_doc()
    doc["stream_metadata"]["compromised_content_ratio_percent"] = 5.0
    doc["penalization_enforcement"]["tier"] = "TIER_3_HEAVY_PENALTY"
    assert any(i.rule == "R6" for i in validate_verdict(doc))


def test_r6_threshold_flag_inconsistent():
    doc = valid_doc()
    doc["stream_metadata"]["compromised_content_ratio_percent"] = 50.0
    doc["penalization_enforcement"]["exceeds_heavy_penalty_threshold"] = False
    assert any(i.rule == "R6" for i in validate_verdict(doc))


def test_r6_status_inconsistent():
    doc = valid_doc()
    doc["stream_metadata"]["compromised_content_ratio_percent"] = 50.0
    doc["stream_metadata"]["status"] = "CLEAN"
    assert any(i.rule == "R6" for i in validate_verdict(doc))


def test_r7_end_before_start():
    doc = valid_doc()
    doc["precision_flags"][0]["location"]["timestamp_end"] = "00:00:01.000"
    doc["precision_flags"][0]["location"]["timestamp_start"] = "00:10:00.000"
    assert any(i.rule == "R7" for i in validate_verdict(doc))


def test_r7_precision_none_requires_null_timestamps():
    doc = valid_doc()
    doc["precision_flags"][0]["location"]["timing_precision"] = "NONE"
    assert any(i.rule == "R7" for i in validate_verdict(doc))


def test_r7_missing_precision_declaration():
    doc = valid_doc()
    del doc["precision_flags"][0]["location"]["timing_precision"]
    assert any(i.rule == "R7" for i in validate_verdict(doc))


def test_r8_bias_may_not_count_toward_ccr():
    doc = valid_doc()
    doc["bias_flags"] = [
        {
            "bias_code": "SELECTIVE_FRAMING",
            "original_claim": "x",
            "verified_fact": "y",
            "why_biased": "z",
            "counts_toward_ccr": True,
        }
    ]
    assert any(i.rule == "R8" for i in validate_verdict(doc))


def test_r8_bias_requires_original_and_verified():
    doc = valid_doc()
    doc["bias_flags"] = [{"bias_code": "OMITTED_CONTEXT", "why_biased": "z"}]
    issues = validate_verdict(doc)
    assert len([i for i in issues if i.rule == "R8"]) >= 2


def test_r9_undisclosed_satire_must_be_classified():
    doc = valid_doc()
    doc["satire_protocol"] = {
        "is_satire_or_entertainment": True,
        "deception_type": None,
        "disclosure_present": False,
        "requires_mandatory_disclaimer": True,
        "mandatory_disclaimer_text": "x",
    }
    assert any(i.rule == "R9" for i in validate_verdict(doc))


def test_disclosed_satire_is_fine():
    doc = valid_doc()
    doc["satire_protocol"] = {
        "is_satire_or_entertainment": True,
        "deception_type": None,
        "disclosure_present": True,
        "requires_mandatory_disclaimer": False,
        "mandatory_disclaimer_text": "x",
    }
    assert not any(i.rule == "R9" for i in validate_verdict(doc))


def test_r10_text_media_rejects_duration():
    doc = valid_doc()
    doc["stream_metadata"]["media_type"] = "social_post"
    doc["stream_metadata"]["total_duration_seconds"] = 60.0
    doc["stream_metadata"]["total_payload_characters"] = 500
    assert any(i.rule == "R10" for i in validate_verdict(doc))


def test_r10_rolling_window_requires_estimate_flag():
    doc = valid_doc()
    doc["stream_metadata"]["analysis_mode"] = "ROLLING_WINDOW"
    doc["stream_metadata"]["duration_is_estimate"] = False
    assert any(i.rule == "R10" for i in validate_verdict(doc))


@pytest.mark.parametrize(
    ("ts", "secs"),
    [("00:00:00.000", 0.0), ("00:01:00.000", 60.0), ("01:00:00.000", 3600.0),
     ("00:00:01.500", 1.5)],
)
def test_parse_timestamp(ts, secs):
    assert parse_timestamp(ts) == pytest.approx(secs)


def test_parse_timestamp_rejects_garbage():
    with pytest.raises(ValueError):
        parse_timestamp("not-a-timestamp")