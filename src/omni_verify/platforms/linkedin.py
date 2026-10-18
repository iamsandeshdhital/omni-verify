"""LinkedIn. Professional register. No per-post monetization to withdraw, but
real account-restriction machinery and a documented Professional Community
Policy. Claim density is high and domain skews finance and workplace claims.
"""

from __future__ import annotations

from ..platforms.projection import BANNER, STRIKE, SUPPRESSION, Capabilities, make_profile
from .base import (
    ModerationAuthority,
    MonetizationCapability,
    NativeLabelSystem,
    StrikeSystem,
)

CAPABILITIES = Capabilities(
    monetization_block=False,
    monetization_hold=False,
    suppression=True,
    strike=True,
    overlay=False,
    banner=True,
    aliases={
        SUPPRESSION: "feedEligibility=DEPRIORITIZE",
        STRIKE: "accountRestriction",
        BANNER: "contentAdvisory",
    },
)

PROFILE = make_profile(
    platform_id="linkedin",
    display_name="LinkedIn",
    media_types=("social_post", "article", "video", "caption"),
    authority=ModerationAuthority(
        centralized=True,
        note="Centralized enforcement under the Professional Community Policy.",
    ),
    strikes=StrikeSystem(
        name="Account restriction",
        strikes_required=None,
        window_days=None,
        expires=True,
        api_writable=False,
        note="Restrictions escalate from search and discovery exclusion to "
             "suspension. No programmatic issuance path.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=False,
        withdrawable=False,
        api_writable=False,
        note="No creator payout programme. The separate ads product has its own "
             "content policy but does not expose per-post withdrawal.",
    ),
    native_labels=NativeLabelSystem(
        name=None,
        supports_machine_submission=False,
        note="No public native label system. Distribution and restriction are the "
             "available levers.",
    ),
    disclosure_norms="Moderate for professional credentials; weak for health and finance claims.",
    ingest_methods=("url", "api", "paste_text"),
    rate_limit="REST API app-level rate limits; posting API access is restricted.",
    capabilities=CAPABILITIES,
    notes=("Financial advice and health claims are frequent here and high-stakes under "
           "§6 - expect most FALSE verdicts to route to human review."),
)