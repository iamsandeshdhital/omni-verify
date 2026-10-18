"""End-to-end pipeline assembly and media rendering."""

from __future__ import annotations

import json

import pytest

from omni_verify.ingest.canonical import from_text, from_transcript, Segment, validate
from omni_verify.pipeline import RawBiasFlag, RawFlag, build_verdict
from omni_verify.platforms import project
from omni_verify.render.vtt import overlay_spec, render_vtt
from omni_verify.types import AnalysisMode, MediaType
from omni_verify.validation import validate_verdict

T1 = {
    "source_name": "Official statistical agency",
    "source_tier": "T1",
    "evidence_summary": "Contradicts the claim.",
    "reference_url_or_doi": "https://example.org/record",
    "published_date": "2026-01-15",
}


def make_flag(**kw) -> RawFlag:
    base = dict(
        start=0.0, end=100.0, category="ECONOMICS_FINANCE", severity="HIGH",
        verdict="FALSE", statement_made="Inflation is 40%.", original_claim="40%",
        verified_fact="It was 4%.", explanation="Decimal transposition.",
        confidence=0.9, retrieval_performed=True, counter_evidence=[dict(T1)],
    )
    base.update(kw)
    return RawFlag(**base)


def text_content(text: str = "x" * 1000):
    return from_text(stream_id="STRM_T", platform="X", text=text)


def video_content(duration: float = 100.0):
    return from_transcript(
        stream_id="STRM_V",
        platform="YouTube",
        segments=[Segment(0.0, duration, "claim", confidence=0.95)],
        total_duration_seconds=duration,
    )


# --- assembly ---------------------------------------------------------------


def test_clean_text_document():
    doc = build_verdict(
        content=text_content(), flags=[], analyzer_confidence=0.9,
        stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert validate_verdict(doc) == []
    assert doc["stream_metadata"]["status"] == "CLEAN"
    assert doc["stream_metadata"]["compromised_content_ratio_percent"] == 0.0
    assert doc["satire_protocol"]["mandatory_disclaimer_text"]


def test_tier3_video_document():
    doc = build_verdict(
        content=video_content(100.0),
        flags=[make_flag(start=0.0, end=25.0)],
        genre="ECONOMICS_FINANCE",
        analyzer_confidence=0.9,
        stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert validate_verdict(doc) == []
    assert doc["stream_metadata"]["compromised_content_ratio_percent"] == 25.0
    assert doc["penalization_enforcement"]["tier"] == "TIER_3_HEAVY_PENALTY"
    assert doc["penalization_enforcement"]["exceeds_heavy_penalty_threshold"] is True
    assert doc["stream_metadata"]["status"] == "HEAVILY_PENALIZED"


def test_exactly_twenty_is_tier2():
    doc = build_verdict(
        content=video_content(100.0), flags=[make_flag(start=0.0, end=20.0)],
        analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert doc["stream_metadata"]["compromised_content_ratio_percent"] == 20.0
    assert doc["penalization_enforcement"]["tier"] == "TIER_2_MODERATE"
    assert doc["penalization_enforcement"]["exceeds_heavy_penalty_threshold"] is False
    assert doc["audit"]["near_threshold"] is True
    assert doc["audit"]["threshold_margin_note"]


def test_overlapping_flags_merge_and_report_audit():
    doc = build_verdict(
        content=video_content(100.0),
        flags=[make_flag(start=0.0, end=15.0), make_flag(start=10.0, end=25.0)],
        analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert doc["audit"]["segments_pre_merge"] == 2
    assert doc["audit"]["segments_post_merge"] == 1
    assert doc["stream_metadata"]["compromised_content_ratio_percent"] == 25.0


def test_unverified_without_evidence_is_allowed():
    doc = build_verdict(
        content=text_content(),
        flags=[make_flag(
            start=0, end=200, verdict="UNVERIFIED", counter_evidence=[],
            retrieval_performed=False, category="HISTORY_CULTURE",
        )],
        analyzer_confidence=0.5, stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert validate_verdict(doc) == []


def test_false_without_evidence_is_rejected():
    with pytest.raises(ValueError, match="validation"):
        build_verdict(
            content=text_content(),
            flags=[make_flag(start=0, end=200, counter_evidence=[])],
            analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
        )


def test_unsupported_evidence_fails_closed():
    with pytest.raises(ValueError):
        build_verdict(
            content=text_content(),
            flags=[make_flag(start=0, end=200, counter_evidence=[
                {"source_name": "blog", "source_tier": "T4", "evidence_summary": "no"}
            ])],
            analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
        )


def test_text_document_uses_character_offsets():
    doc = build_verdict(
        content=text_content("x" * 1000), flags=[make_flag(start=100, end=350)],
        analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
    )
    loc = doc["precision_flags"][0]["location"]
    assert loc["timestamp_start"] is None
    assert loc["character_start"] == 100
    assert doc["stream_metadata"]["total_duration_seconds"] is None
    assert doc["stream_metadata"]["total_payload_characters"] == 1000


def test_bias_flags_do_not_change_ccr():
    without = build_verdict(
        content=text_content(), flags=[], analyzer_confidence=0.9,
        stream_timestamp="2026-10-18T00:00:00Z",
    )
    with_bias = build_verdict(
        content=text_content(), flags=[],
        bias_flags=[RawBiasFlag(
            code="SELECTIVE_FRAMING", original_claim="a", verified_fact="b",
            why_biased="c",
        )],
        analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert (
        without["stream_metadata"]["compromised_content_ratio_percent"]
        == with_bias["stream_metadata"]["compromised_content_ratio_percent"]
    )
    assert len(with_bias["bias_flags"]) == 1
    assert with_bias["bias_flags"][0]["counts_toward_ccr"] is False


def test_satire_disclosed_excluded_from_ratio():
    doc = build_verdict(
        content=video_content(100.0), flags=[make_flag(start=0.0, end=30.0)],
        satire=True, disclosure_present=True, genre="SATIRE_PARODY",
        analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert doc["satire_protocol"]["is_satire_or_entertainment"] is True
    assert doc["satire_protocol"]["requires_mandatory_disclaimer"] is False


def test_undisclosed_satire_is_deception():
    doc = build_verdict(
        content=video_content(100.0), flags=[make_flag(start=0.0, end=30.0)],
        satire=True, disclosure_present=False, genre="SATIRE_PARODY",
        analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert doc["satire_protocol"]["deception_type"] == "UNDISCLOSED_FICTION"
    assert doc["satire_protocol"]["requires_mandatory_disclaimer"] is True


def test_rolling_window_is_provisional():
    doc = build_verdict(
        content=video_content(100.0), flags=[make_flag(start=0.0, end=30.0)],
        analysis_mode=AnalysisMode.ROLLING_WINDOW,
        analyzer_confidence=0.95, stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert doc["stream_metadata"]["analysis_mode"] == "ROLLING_WINDOW"
    assert doc["stream_metadata"]["duration_is_estimate"] is True
    assert doc["penalization_enforcement"]["enforcement_state"] == "QUEUED"


def test_high_stakes_flags_route_to_review():
    doc = build_verdict(
        content=video_content(100.0),
        flags=[make_flag(start=0.0, end=25.0, category="MEDICAL_HEALTH")],
        genre="MEDICAL_HEALTH", analyzer_confidence=0.95,
        stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert doc["penalization_enforcement"]["requires_human_review"] is True
    assert doc["penalization_enforcement"]["review_reasons"]


def test_low_confidence_routes_to_review():
    doc = build_verdict(
        content=video_content(100.0),
        flags=[make_flag(start=0.0, end=3.0, category="SPORTS_ATHLETICS",
                         verdict="MISLEADING")],
        genre="SPORTS_ATHLETICS", analyzer_confidence=0.4,
        stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert doc["penalization_enforcement"]["requires_human_review"] is True


def test_mute_range_requires_all_conditions():
    doc = build_verdict(
        content=video_content(100.0),
        flags=[make_flag(
            start=0.0, end=60.0, category="MEDICAL_HEALTH", severity="CRITICAL",
            is_audio_claim=True,
        )],
        genre="MEDICAL_HEALTH", analyzer_confidence=0.95,
        stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert doc["precision_flags"][0]["ui_action_trigger"] == "MUTE_RANGE"


def test_short_segment_does_not_mute():
    doc = build_verdict(
        content=video_content(100.0),
        flags=[make_flag(start=0.0, end=10.0, category="MEDICAL_HEALTH",
                         severity="CRITICAL", is_audio_claim=True)],
        genre="MEDICAL_HEALTH", analyzer_confidence=0.95,
        stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert doc["precision_flags"][0]["ui_action_trigger"] == "OVERLAY_WARNING_FLAG"


def test_document_is_json_serialisable():
    doc = build_verdict(
        content=video_content(100.0), flags=[make_flag(start=0.0, end=25.0)],
        analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
    )
    json.dumps(doc)


# --- projection of a pipeline output ----------------------------------------


def test_pipeline_output_projects_to_every_platform():
    doc = build_verdict(
        content=video_content(100.0), flags=[make_flag(start=0.0, end=25.0)],
        analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
    )
    for platform_id in ("youtube", "x", "bluesky", "reddit", "telegram"):
        assert project(platform_id, doc).to_dict()["platform_id"] == platform_id


# --- rendering ---------------------------------------------------------------


def test_vtt_has_cue_per_flag():
    doc = build_verdict(
        content=video_content(100.0), flags=[make_flag(start=1.0, end=25.0)],
        analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
    )
    vtt = render_vtt(doc)
    assert vtt.startswith("WEBVTT")
    assert "00:00:01.000 --> 00:00:25.000" in vtt
    assert "Verified fact:" in vtt


def test_vtt_tier3_carries_global_note():
    doc = build_verdict(
        content=video_content(100.0), flags=[make_flag(start=0.0, end=25.0)],
        analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert "CRITICAL WARNING: OVER 20%" in render_vtt(doc)


def test_overlay_spec_only_at_tier3():
    tier3 = build_verdict(
        content=video_content(100.0), flags=[make_flag(start=0.0, end=25.0)],
        analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
    )
    tier2 = build_verdict(
        content=video_content(100.0), flags=[make_flag(start=0.0, end=10.0)],
        analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert overlay_spec(tier3)["enabled"] is True
    assert overlay_spec(tier3)["burn_in_command"].startswith("ffmpeg")
    assert overlay_spec(tier2)["enabled"] is False


def test_vtt_skips_character_offset_findings():
    doc = build_verdict(
        content=text_content(), flags=[make_flag(start=10, end=90)],
        analyzer_confidence=0.9, stream_timestamp="2026-10-18T00:00:00Z",
    )
    assert "-->" not in render_vtt(doc)


# --- ingest ------------------------------------------------------------------


def test_ingest_validation_catches_empty():
    from omni_verify.ingest.canonical import CanonicalContent

    problems = validate(CanonicalContent(
        stream_id="X", media_type=MediaType.SOCIAL_POST, platform="X"
    ))
    assert problems


def test_character_count_is_raw_code_points():
    c = text_content("hello world")
    assert c.total_payload_characters == 11
    assert c.word_count == 2