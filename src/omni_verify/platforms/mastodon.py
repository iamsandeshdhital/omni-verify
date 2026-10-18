"""Mastodon. Instance-governed with no central authority and no monetization.
Notably, the `boef` plugin exists specifically to fetch an external fact-check
source and display a warning - the closest analogue to a machine-submittable
native label in the fediverse.
"""

from __future__ import annotations

from ..platforms.projection import BANNER, Capabilities, make_profile
from .base import (
    ModerationAuthority,
    MonetizationCapability,
    NativeLabelSystem,
    StrikeSystem,
)

SUPPRESSION_LABEL = "federationModeration"

CAPABILITIES = Capabilities(
    monetization_block=False,
    monetization_hold=False,
    suppression=True,  # instance-level federation/silencing by the moderator
    strike=False,
    overlay=False,
    banner=True,
    aliases={
        SUPPRESSION_LABEL: "account[report_type]=silence",
        BANNER: "boef#warning",
    },
)

PROFILE = make_profile(
    platform_id="mastodon",
    display_name="Mastodon",
    media_types=("social_post", "caption"),
    authority=ModerationAuthority(
        centralized=False,
        delegated_to_moderators=True,
        note="Each instance moderates its own users. Silence and suspend are instance "
             "actions, not protocol actions.",
    ),
    strikes=StrikeSystem(
        name=None,
        strikes_required=None,
        window_days=None,
        expires=False,
        api_writable=False,
        note="Instance moderators may silence or suspend. There is no strike ledger.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=False,
        withdrawable=False,
        api_writable=False,
        note="Most instances carry no advertising at all.",
    ),
    native_labels=NativeLabelSystem(
        name="boef anti-misinformation plugin",
        supports_machine_submission=True,
        note="boef polls an external fact-check URL and renders a warning. The fact-check "
             "source is typically a curated list rather than a live submission API.",
    ),
    disclosure_norms="Content warnings are instance-configuration dependent.",
    ingest_methods=("url", "api", "paste_text"),
    rate_limit="Per-instance. Large instances rate limit aggressively.",
    capabilities=CAPABILITIES,
)