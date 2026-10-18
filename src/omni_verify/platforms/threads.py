"""Threads. Meta surface with no creator revenue at all, so every monetization
action declines and suppression plus labeling carry the entire signal.
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
        SUPPRESSION: "replyRankingFilter",
        STRIKE: "accountStatusAction",
        BANNER: "factCheckLabel",
    },
)

PROFILE = make_profile(
    platform_id="threads",
    display_name="Threads",
    media_types=("social_post", "caption"),
    authority=ModerationAuthority(
        centralized=True,
        note="Centralized enforcement sharing Meta's account status machinery.",
    ),
    strikes=StrikeSystem(
        name="Account status action",
        strikes_required=3,
        window_days=30,
        expires=False,
        api_writable=False,
        note="Cross-surface with Instagram and Facebook on the same Meta account.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=False,
        withdrawable=False,
        api_writable=False,
        note="No creator monetization programme. Monetization actions always decline.",
    ),
    native_labels=NativeLabelSystem(
        name="Fact-check label",
        supports_machine_submission=True,
        note="Shared Meta programme.",
    ),
    disclosure_norms="Minimal.",
    ingest_methods=("url", "upload", "paste_text"),
    rate_limit="Threads API is comparatively permissive; verify current availability.",
    capabilities=CAPABILITIES,
)