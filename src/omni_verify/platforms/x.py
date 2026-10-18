"""X (Twitter). The important property: no organic ad revenue on posts, so
``FULL_DEMONETIZATION`` is meaningless here. The real enforcement surface is
Community Notes eligibility plus reach suppression.
"""

from __future__ import annotations

from ..platforms.projection import BANNER, SUPPRESSION, Capabilities, make_profile
from .base import (
    ModerationAuthority,
    MonetizationCapability,
    NativeLabelSystem,
    StrikeSystem,
)

CAPABILITIES = Capabilities(
    monetization_block=False,  # nothing to withdraw
    monetization_hold=False,
    suppression=True,
    strike=False,  # no platform strike system
    overlay=False,
    banner=True,
    aliases={
        SUPPRESSION: "reachSuppression",
        BANNER: "communityNoteCandidate",
    },
)

PROFILE = make_profile(
    platform_id="x",
    display_name="X (Twitter)",
    media_types=("social_post", "video", "caption"),
    authority=ModerationAuthority(
        centralized=True,
        note="Centralized enforcement, plus a crowdsourced Community Notes layer.",
    ),
    strikes=StrikeSystem(
        name=None,
        strikes_required=None,
        window_days=None,
        expires=False,
        api_writable=False,
        note="X has no strike system. Content may be labeled, demonetized via the Ads "
             "product (a separate, opt-in product with its own content policy), or "
             "deprioritized.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=False,
        withdrawable=False,
        api_writable=False,
        note="Organic posts carry no ad revenue. Creator subscription payouts exist "
             "but are not withdrawable per-post through any public API.",
    ),
    native_labels=NativeLabelSystem(
        name="Community Notes",
        supports_machine_submission=False,
        note="Community Notes are crowd-written and bridged, not machine-submitted. "
             "The pipeline's useful contribution is candidate identification and a "
             "draft note body, not a direct submission.",
    ),
    disclosure_norms="Weak. Synthetic media labelling is largely opt-in.",
    ingest_methods=("url", "upload", "paste_text"),
    rate_limit="API v2 tiered; recent posts are heavily rate limited on the basic tier.",
    capabilities=CAPABILITIES,
    notes=(
        "Declining FULL_DEMONETIZATION here is correct behaviour, not a bug. The "
        "projection will report unsupported_actions rather than fabricate a penalty.",
    ),
)