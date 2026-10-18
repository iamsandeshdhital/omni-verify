"""Platform capability filtering (Layer 5) and the registry."""

from __future__ import annotations

import pytest

from omni_verify.platforms import all_profiles, capability_matrix, get_profile, project
from omni_verify.types import PLATFORMS
from tests.factories import valid_doc


def test_all_fourteen_platforms_registered():
    assert len(PLATFORMS) == 14
    assert set(p.platform_id for p in all_profiles()) == set(PLATFORMS)


@pytest.mark.parametrize("platform_id", PLATFORMS)
def test_registry_roundtrip(platform_id):
    prof = get_profile(platform_id)
    assert prof.platform_id == platform_id
    assert prof.media_types


def test_unknown_platform_raises():
    with pytest.raises(KeyError):
        get_profile("myspace")


def test_capability_matrix_row_per_platform():
    rows = capability_matrix()
    assert len(rows) == 14
    assert {r["platform_id"] for r in rows} == set(PLATFORMS)


# --- the interesting cases --------------------------------------------------


def test_youtube_supports_monetization_block():
    """Projected under YouTube's native name, not the canonical one."""
    doc = valid_doc()
    result = project("youtube", doc)
    assert "monetizationPolicy=MONETIZATION_POLICY_BLOCK" in result.actions_triggered
    assert result.unsupported_actions == []


def test_youtube_projection_is_advisory_no_write_api():
    """Money and strikes exist but there is no public write path."""
    doc = valid_doc()
    result = project("youtube", doc)
    assert result.api_payload["api_writable"] is False
    assert "human must execute" in (result.unsupported_reason or "")


def test_x_declines_monetization_block():
    """X has no organic ad revenue. Declining is correct, not a failure."""
    doc = valid_doc()
    result = project("x", doc)
    assert "FULL_DEMONETIZATION" in result.unsupported_actions
    assert "no creator revenue" in (result.unsupported_reason or "")
    assert result.advisory_only is False  # it still has suppression + notes


def test_x_declines_account_strike():
    doc = valid_doc()
    result = project("x", doc)
    assert "ACCOUNT_STRIKE_ISSUED" in result.unsupported_actions


def test_bluesky_has_no_enforcement_authority():
    doc = valid_doc()
    result = project("bluesky", doc)
    assert result.advisory_only is True
    assert result.supported is False
    assert result.unsupported_reason


def test_bluesky_still_offers_a_label_at_lower_tiers():
    """At Tier 3 the only actions are penalties, and Bluesky has no penalties.
    The label surface is what Tier 2 projection uses."""
    from omni_verify.platforms import get_profile

    prof = get_profile("bluesky")
    assert prof.action_alias("SEGMENT_WARNING_BANNER") == "com.atproto.label.defs#label"
    assert prof.action_alias("FULL_DEMONETIZATION") is None


def test_reddit_strike_is_delegated_not_platform():
    doc = valid_doc()
    result = project("reddit", doc)
    assert "ACCOUNT_STRIKE_ISSUED" in result.unsupported_actions
    # Reddit *can* downrank, so the projection is not fully advisory-only.
    assert any("DOWNRANK" in a for a in result.actions_triggered)
    assert result.api_payload["advisory_only"] is False


def test_telegram_has_no_authority_at_all():
    """E2EE: enforcement is impossible, not merely unavailable."""
    doc = valid_doc()
    result = project("telegram", doc)
    assert result.supported is False
    assert result.advisory_only is True
    assert "encryption" in (result.unsupported_reason or "").lower()


def test_telegram_advisory_declares_every_tier3_action():
    doc = valid_doc()
    result = project("telegram", doc)
    assert result.unsupported_actions
    # Every Tier 3 penalty must be declined, none silently applied.
    assert set(result.unsupported_actions) >= {
        "FULL_DEMONETIZATION",
        "ACCOUNT_STRIKE_ISSUED",
        "ALGORITHMIC_SUPPRESSION",
        "FULL_FRAME_WARNING_OVERLAY",
    }
    assert result.actions_triggered == []


def test_threads_always_declines_monetization():
    doc = valid_doc()
    result = project("threads", doc)
    assert "FULL_DEMONETIZATION" in result.unsupported_actions


def test_meta_overlay_declines():
    """Meta labels in feed; no forced full-frame burn-in."""
    doc = valid_doc()
    result = project("meta", doc)
    assert "FULL_FRAME_WARNING_OVERLAY" in result.unsupported_actions


@pytest.mark.parametrize("platform_id", PLATFORMS)
def test_projection_never_claims_more_than_canonical(platform_id):
    """No projection may invent an action the canonical tier did not grant."""
    doc = valid_doc()
    result = project(platform_id, doc)
    assert len(result.actions_triggered) + len(result.unsupported_actions) == len(
        doc["penalization_enforcement"]["actions_triggered"]
    )


@pytest.mark.parametrize("platform_id", PLATFORMS)
def test_projection_payload_is_serialisable(platform_id):
    import json

    doc = valid_doc()
    json.dumps(project(platform_id, doc).to_dict())


def test_tier1_projects_lightly_everywhere():
    from tests.factories import video_doc

    doc = video_doc(3.0)
    doc["penalization_enforcement"]["actions_triggered"] = ["INLINE_CONTEXT_CARD"]
    for platform_id in PLATFORMS:
        result = project(platform_id, doc)
        # A context card is either supported or explicitly declared unsupported.
        assert isinstance(result.to_dict(), dict)


def test_clean_doc_projects_everywhere():
    from tests.factories import clean_doc

    doc = clean_doc()
    doc["penalization_enforcement"]["actions_triggered"] = ["INLINE_CONTEXT_CARD"]
    for platform_id in PLATFORMS:
        assert project(platform_id, doc).to_dict()["platform_id"] == platform_id