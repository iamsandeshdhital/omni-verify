"""Snapchat / Spotlight. No monetization to withdraw, no public strike semantics
and no native label surface. Public Spotlight content is the only meaningful
discovery surface.
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
        SUPPRESSION: "spotlightEligibility=HIDDEN",
        STRIKE: "accountAction",
        BANNER: "contentAdvisory",
    },
)

PROFILE = make_profile(
    platform_id="snapchat",
    display_name="Snapchat (Spotlight)",
    media_types=("video", "social_post"),
    authority=ModerationAuthority(
        centralized=True,
        note="Centralized enforcement, largely opacity-driven.",
    ),
    strikes=StrikeSystem(
        name="Account action",
        strikes_required=None,
        window_days=None,
        expires=False,
        api_writable=False,
        note="Thresholds and expiry are unpublished. Treat as opaque.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=False,
        withdrawable=False,
        api_writable=False,
        note="Snap does not offer a creator revenue programme at present.",
    ),
    native_labels=NativeLabelSystem(
        name=None,
        supports_machine_submission=False,
        note="No native label surface.",
    ),
    disclosure_norms="Minimal.",
    ingest_methods=("url", "upload"),
    rate_limit="Unofficial APIs only. Use the upload path.",
    capabilities=CAPABILITIES,
    notes=("Opaque enforcement means the projection is largely advisory. It should never "
           "claim an action was taken."),
)