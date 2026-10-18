"""Instagram. Shares Meta enforcement machinery but has separate media surfaces:
Reels, Stories and Feed each behave differently for distribution control.
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
    monetization_block=False,  # creator payouts not withdrawable per-post via API
    monetization_hold=False,
    suppression=True,
    strike=True,
    overlay=False,
    banner=True,
    aliases={
        SUPPRESSION: "exploreExclude",
        STRIKE: "accountStatusAction",
        BANNER: "factCheckLabel",
    },
)

PROFILE = make_profile(
    platform_id="instagram",
    display_name="Instagram",
    media_types=("social_post", "video", "caption"),
    authority=ModerationAuthority(
        centralized=True,
        note="Centralized enforcement under Meta's Community Standards.",
    ),
    strikes=StrikeSystem(
        name="Account status action",
        strikes_required=3,
        window_days=30,
        expires=False,
        api_writable=False,
        note="Shared with Facebook enforcement state per account.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=True,
        withdrawable=False,
        api_writable=False,
        note="Creator payouts and brand content eligibility exist, but there is no "
             "per-post withdraw API. Monetization actions project to advisory.",
    ),
    native_labels=NativeLabelSystem(
        name="Fact-check label",
        supports_machine_submission=True,
        note="Same partner programme as Meta/Facebook.",
    ),
    disclosure_norms="Inconsistent. AI-content labels exist but are not universally applied.",
    ingest_methods=("url", "upload", "api", "paste_text"),
    rate_limit="Graph API; media access is restricted for most content.",
    capabilities=CAPABILITIES,
)