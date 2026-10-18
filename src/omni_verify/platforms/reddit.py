"""Reddit. The delegated-authority case. There is no platform-level strike for
misinformation - subreddit moderators act independently, so the projection is a
mod-advisory brief rather than an enforcement action.
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
    suppression=True,  # downrank only, via moderator action
    strike=False,  # moderation is delegated, not platform-issued
    overlay=False,
    banner=True,
    aliases={
        SUPPRESSION: "suggestedSort=DOWNRANK_ADVISORY",
        BANNER: "postFlair=CONTENT_DISPUTED",
    },
)

PROFILE = make_profile(
    platform_id="reddit",
    display_name="Reddit",
    media_types=("social_post", "caption"),
    authority=ModerationAuthority(
        centralized=False,
        delegated_to_moderators=True,
        note="Enforcement is per-subreddit. The platform issues sitewide actions only "
             "for spam and certain illegal content, not for misinformation.",
    ),
    strikes=StrikeSystem(
        name=None,
        strikes_required=None,
        window_days=None,
        expires=False,
        api_writable=False,
        note="A 'strike' is a subreddit ban, issued by that subreddit's moderators "
             "under their own rules. There is no cross-subreddit strike.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=False,
        withdrawable=False,
        api_writable=False,
        note="Ad revenue is Reddit's, not the poster's.",
    ),
    native_labels=NativeLabelSystem(
        name="Post flair (CONTENT_DISPUTED)",
        supports_machine_submission=True,
        note="Flair is applied by moderators, not by Reddit. The pipeline can suggest "
             "flair text and a moderator-facing summary.",
    ),
    disclosure_norms="Community-specific. Flair is the primary convention for disputed content.",
    ingest_methods=("url", "api", "paste_text"),
    rate_limit="OAuth API limits are per-app; anonymous access is effectively absent.",
    capabilities=CAPABILITIES,
    notes=("Emit a moderator briefing: the finding, the evidence, and a suggested "
           "action. Never claim a ban was issued."),
)