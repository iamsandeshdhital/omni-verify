"""Twitch. Monetization exists but is subscription-based rather than per-video
ad revenue, so a content-specific revenue withdrawal is not a native concept.
Enforcement is heavily right-of-publicity and copyright oriented.
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
        SUPPRESSION: "channelVisibility=OFFLINE_SOON",
        STRIKE: "contentPolicyViolation",
        BANNER: "chatNotice",
    },
)

PROFILE = make_profile(
    platform_id="twitch",
    display_name="Twitch",
    media_types=("live_video", "video"),
    authority=ModerationAuthority(
        centralized=True,
        note="Centralized content policy enforcement with automated and human review.",
    ),
    strikes=StrikeSystem(
        name="Content policy violation",
        strikes_required=None,
        window_days=30,
        expires=False,
        api_writable=False,
        note="Escalates to channel suspension. Off-platform enforcement is explicitly "
             "part of Twitch's model, which matters for RADIUS-style networks.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=True,
        withdrawable=False,
        api_writable=False,
        mechanism="subscriptions, bits, ads revenue share",
        note="Revenue attaches to the channel and the broadcaster, not to a single "
             "VOD. There is no per-clip revenue withdrawal API.",
    ),
    native_labels=NativeLabelSystem(
        name=None,
        supports_machine_submission=False,
        note="No fact-check label surface. Chat notices are broadcaster-controlled.",
    ),
    disclosure_norms="Weak for in-stream claims; no synthetic-media requirement.",
    ingest_methods=("url", "upload"),
    rate_limit="Helix API app rate limits; VOD download requires broadcaster OAuth.",
    capabilities=CAPABILITIES,
    notes=("Live content has no fixed duration at ingest time - rolling-window CCR is the "
           "normal path here, which forces §2.2 provisional handling."),
)