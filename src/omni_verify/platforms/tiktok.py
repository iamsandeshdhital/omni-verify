"""TikTok. Real monetization exists and is withdrawable. Political content
carries mandatory in-app fact-check labels under the EU DSA, which is the
closest thing in this matrix to a machine-submittable native label.
"""

from __future__ import annotations

from ..platforms.projection import (
    BANNER,
    MONETIZATION_BLOCK,
    MONETIZATION_HOLD,
    OVERLAY,
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
    overlay=True,
    banner=True,
    aliases={
        MONETIZATION_BLOCK: "creatorFundWithdrawal=HOLD",
        MONETIZATION_HOLD: "eligibleForPromotion=false",
        SUPPRESSION: "fyp_suppress",
        STRIKE: "policyPoint",
        OVERLAY: "fullFrameOverlay",
        BANNER: "factCheckLabel",
    },
)

PROFILE = make_profile(
    platform_id="tiktok",
    display_name="TikTok",
    media_types=("video", "live_video", "social_post"),
    authority=ModerationAuthority(
        centralized=True,
        note="Centralized integrity enforcement with an elected regulator interface.",
    ),
    strikes=StrikeSystem(
        name="Policy point",
        strikes_required=None,  # thresholds vary by violation class
        window_days=None,
        expires=True,
        api_writable=False,
        note="Policy points accumulate and drive feature restrictions. Thresholds "
             "differ per violation type and are not uniformly published.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=True,
        withdrawable=True,
        api_writable=False,
        mechanism="creator fund / shop eligibility",
        note="TikTok Shop and affiliate revenue are the larger surfaces. Removing a "
             "video removes its attributable revenue.",
    ),
    native_labels=NativeLabelSystem(
        name="In-app fact-check label",
        supports_machine_submission=True,
        note="Political-content fact-check labels are regulator-driven. Machine "
             "submission is possible in some jurisdictions but requires a signed "
             "fact-checking partnership.",
    ),
    disclosure_norms="Mandatory AI-generated content labelling since 2024.",
    ingest_methods=("url", "upload", "api"),
    rate_limit="Research API is restricted to approved researchers with a signed agreement.",
    capabilities=CAPABILITIES,
    notes=("Content originality policy catches reposts; a CCR verdict on unoriginal "
           "content is a different finding from a false-claim verdict."),
)