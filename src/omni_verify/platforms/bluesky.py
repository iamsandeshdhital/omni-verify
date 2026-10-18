"""Bluesky. Fully decentralized, no ads, no monetization whatsoever. The only
available action is publishing a label through an independent labeler service.
Every canonical penalty declines; that is the correct output, not a failure.
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
    suppression=False,  # no ranking authority held by anyone in the protocol
    strike=False,
    overlay=False,
    banner=True,
    aliases={BANNER: "com.atproto.label.defs#label"},
)

PROFILE = make_profile(
    platform_id="bluesky",
    display_name="Bluesky",
    media_types=("social_post", "caption"),
    authority=ModerationAuthority(
        centralized=False,
        decentralized_labeling=True,
        note="Moderation is performed by independent labeler services and the user's "
             "own client. The protocol holds no enforcement authority.",
    ),
    strikes=StrikeSystem(
        name=None,
        strikes_required=None,
        window_days=None,
        expires=False,
        api_writable=False,
        note="There is no strike concept. A label is data that any client may render, "
             "ignore, or hide.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=False,
        withdrawable=False,
        api_writable=False,
        note="No advertising in the protocol. All monetization actions always decline.",
    ),
    native_labels=NativeLabelSystem(
        name="AT Protocol labels",
        supports_machine_submission=True,
        note="Labels are signed atproto records. A label is a statement, not an "
             "enforcement act - it depends on client software to be visible.",
    ),
    disclosure_norms="Label-driven rather than self-declared.",
    ingest_methods=("url", "api", "paste_text"),
    rate_limit="Public AppView has no published quota; be polite.",
    capabilities=CAPABILITIES,
    notes=("A Tier 3 verdict here projects to advisory-only plus a label record. That is "
           "the honest output: the protocol cannot demonetize or ban."),
)