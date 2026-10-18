"""Spotify podcasts. Episode-level surface with no creator monetization to
withdraw. Relevant because spoken health and finance claims in long episodes
sit under the same CCR machinery as short-form video.
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
    monetization_block=False,
    monetization_hold=False,
    suppression=True,
    strike=False,
    overlay=False,
    banner=True,
    aliases={
        SUPPRESSION: "episodeDistribution=REMOVE",
        BANNER: "episodeAdvisory",
    },
)

PROFILE = make_profile(
    platform_id="spotify_podcasts",
    display_name="Spotify (Podcasts)",
    media_types=("audio", "video"),
    authority=ModerationAuthority(
        centralized=True,
        note="Centralized RSS and editorial enforcement, applied largely at the show "
             "or episode level rather than per claim.",
    ),
    strikes=StrikeSystem(
        name=None,
        strikes_required=None,
        window_days=None,
        expires=False,
        api_writable=False,
        note="Enforcement typically applies to the show or publisher account, not to "
             "an individual episode.",
    ),
    monetization=MonetizationCapability(
        has_creator_revenue=False,
        withdrawable=False,
        api_writable=False,
        note="Podcast ad revenue is sold through Spotify's ad platform. There is no "
             "per-episode withdrawal API.",
    ),
    native_labels=NativeLabelSystem(
        name=None,
        supports_machine_submission=False,
        note="No fact-check label surface.",
    ),
    disclosure_norms="IAB guidelines for health and finance advertising exist but are "
                     "self-regulated and poorly enforced in editorial audio.",
    ingest_methods=("url", "upload", "paste_transcript"),
    rate_limit="Web API app-level; RSS is public.",
    capabilities=CAPABILITIES,
    notes=("Long episodes make duration denominators large, which mechanically depresses "
           "CCR. Consider whether that is the intended policy signal for long-form audio."),
)