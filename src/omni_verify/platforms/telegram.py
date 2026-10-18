"""Telegram and equivalent end-to-end encrypted messengers.

The terminal case for capability filtering: the platform holds **no moderation
authority over private channels** and has no mechanism to enforce anything on
content it cannot read. Projection here is always advisory and must say so
loudly, because an operator seeing a Tier 3 verdict could otherwise believe a
channel was acted against.
"""

from __future__ import annotations

from ..platforms.projection import BANNER, Capabilities, make_profile
from .base import (
    ModerationAuthority,
    MonetizationCapability,
    NativeLabelSystem,
    StrikeSystem,
)

CAPABILITIES = Capabilities(
    monetization_block=False,
    monetization_hold=False,
    suppression=False,
    strike=False,
    overlay=False,
    banner=True,  # informational notice delivered to the operator only
    aliases={BANNER: "advisoryNotice"},
)

PROFILE = make_profile(
    platform_id="telegram",
    display_name="Telegram / E2EE messengers",
    media_types=("social_post", "video", "audio", "caption"),
    authority=ModerationAuthority(
        centralized=False,
        has_any_authority=False,
        note="End-to-end encryption means the platform cannot read private channel "
             "content and therefore cannot enforce any verdict against it. Public "
             "channel previews are the only visible surface, and even those are not "
             "actionable.",
    ),
    strikes=StrikeSystem(
        name=None,
        strikes_required=None,
        window_days=None,
        expires=False,
        api_writable=False,
        note="No strike concept. Enforcement against private groups is technically "
             "impossible, not merely unavailable.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=False,
        withdrawable=False,
        api_writable=False,
        note="No creator revenue programme.",
    ),
    native_labels=NativeLabelSystem(
        name=None,
        supports_machine_submission=False,
        note="No label surface. E2EE content is inaccessible to the platform.",
    ),
    disclosure_norms="None enforced.",
    ingest_methods=("paste_text", "upload"),
    rate_limit="Bot API rate limits apply to the operator's own bot only.",
    capabilities=CAPABILITIES,
    notes=("Always project as advisory_only with has_any_authority=False. If an operator "
           "needs enforcement here, the action is off-platform: report to a national "
           "regulator or law enforcement, not to Telegram."),
)