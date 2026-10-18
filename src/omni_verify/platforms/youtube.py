"""YouTube. The reference case: ad revenue and a real strike system exist,
but neither has a public write API. Projections are advisory - a human executes.
"""

from __future__ import annotations

from ..platforms.projection import (
    BANNER,
    MONETIZATION_BLOCK,
    MONETIZATION_HOLD,
    OVERLAY,
    STRIKE,
    SUPPRESSION,
    Capabilities,
    make_profile,
)
from .base import (
    ModerationAuthority,
    MonetizationCapability,
    NativeLabelSystem,
    StrikeSystem,
)

CAPABILITIES = Capabilities(
    monetization_block=True,
    monetization_hold=True,
    suppression=True,
    strike=True,
    overlay=True,
    banner=True,
    aliases={
        MONETIZATION_BLOCK: "monetizationPolicy=MONETIZATION_POLICY_BLOCK",
        MONETIZATION_HOLD: "monetizationPolicy=MONETIZATION_POLICY_PARTIAL_HOLD",
        SUPPRESSION: "recommendationFilter=REMOVE_FROM_UP_NEXT",
        STRIKE: "communityGuidelineStrike",
        OVERLAY: "fullFrameOverlay",
        BANNER: "segmentWarningBanner",
    },
)

PROFILE = make_profile(
    platform_id="youtube",
    display_name="YouTube",
    media_types=("video", "live_video", "caption"),
    authority=ModerationAuthority(
        centralized=True,
        note="Centralized policy enforcement under Community Guidelines.",
    ),
    strikes=StrikeSystem(
        name="Community Guidelines strike",
        strikes_required=3,
        window_days=90,
        expires=True,
        api_writable=False,
        note="Strikes are issued by the Trust & Safety team. The Data API v3 has no "
             "write path for issuing strikes; overshoot counts accumulate on the "
             "channel, not on individual videos.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=True,
        withdrawable=True,
        api_writable=False,
        mechanism="monetizationPolicy on the content owner",
        note="Demonetization is performed by a human reviewer. Shorts and long-form "
             "are separate surfaces with separate policy handling.",
    ),
    native_labels=NativeLabelSystem(
        name=None,
        supports_machine_submission=False,
        note="YouTube does not expose a machine-submittable fact-check label. "
             "Information panels are editorially assigned.",
    ),
    disclosure_norms="Synthetic/synthetic-media disclosure is required in the "
                     "upload description and, for realistic content, in the player.",
    ingest_methods=("url", "upload", "api", "paste_transcript"),
    rate_limit="YouTube Data API v3 default quota 10,000 units/day; "
               "captions.list costs 200 units per call.",
    capabilities=CAPABILITIES,
    notes=(
        "Platform changes policy surfaces frequently. Re-verify monetization and "
        "strike semantics before relying on them operationally.",
    ),
)