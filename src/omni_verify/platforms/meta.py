"""Meta (Facebook). Third-Party Fact Checking historically ran through a
partner program with programmatic label submission. Payouts are narrow, so
monetization_block is false for most surfaces while strike machinery is real.
"""

from __future__ import annotations

from ..platforms.projection import (
    BANNER,
    MONETIZATION_BLOCK,
    MONETIZATION_HOLD,
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
    overlay=False,  # Meta labels in feed, no forced full-frame burn-in
    banner=True,
    aliases={
        MONETIZATION_BLOCK: "payoutDisable",
        MONETIZATION_HOLD: "payoutHold",
        SUPPRESSION: "distributionFilter=DOWNRANK",
        STRIKE: "accountStatusAction",
        BANNER: "factCheckLabel",
    },
)

PROFILE = make_profile(
    platform_id="meta",
    display_name="Meta (Facebook)",
    media_types=("social_post", "video", "live_video", "caption"),
    authority=ModerationAuthority(
        centralized=True,
        note="Centralized Community Standards enforcement with an external fact-check "
             "partner network.",
    ),
    strikes=StrikeSystem(
        name="Account status action (strike / feature restriction)",
        strikes_required=3,
        window_days=30,
        expires=False,
        api_writable=False,
        note="Strike thresholds escalate. There is no public API to issue an account "
             "status action programmatically.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=True,
        withdrawable=True,
        api_writable=False,
        mechanism="content payouts programme eligibility",
        note="Surface-level monetization is narrow. Suppression is the more "
             "consequential lever here.",
    ),
    native_labels=NativeLabelSystem(
        name="Fact-check label",
        supports_machine_submission=True,
        note="Historically programmatic via the fact-checking partner programme. "
             "Verify current partner requirements before integrating.",
    ),
    disclosure_norms="Political and social-issue ads carry a disclaimer library. "
                     "Synthetic media labelling is required but inconsistently surfaced.",
    ingest_methods=("url", "upload", "api", "paste_text"),
    rate_limit="Graph API app-level rate limits; page content access is heavily restricted.",
    capabilities=CAPABILITIES,
    notes=("Facebook and Instagram share enforcement machinery but are separate "
           "surfaces with separate capabilities - do not reuse one projection for both."),
)