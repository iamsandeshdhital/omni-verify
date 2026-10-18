"""Canonical enumerations for schema 1.1.0.

Every value here is a single literal string. The 1.0.0 defect was pipe-delimited
pseudo-enums (e.g. ``"FALSE | MISLEADING"``) shipped as one string value, which
no validator can constrain. Sets are the single source of truth.
"""

from __future__ import annotations

from enum import StrEnum

SCHEMA_VERSION = "1.1.0"
ANALYZER_VERSION = "OMNI-VERIFY-1.1.0"


class Verdict(StrEnum):
    FALSE = "FALSE"
    MISLEADING = "MISLEADING"
    OUTDATED = "OUTDATED"
    UNVERIFIED = "UNVERIFIED"
    FABRICATED = "FABRICATED"
    CONTESTED = "CONTESTED"
    SATIRE_ELEMENT = "SATIRE_ELEMENT"


class Severity(StrEnum):
    INFO = "INFO"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SourceTier(StrEnum):
    T1 = "T1"  # primary records, filings, official statistics, peer-reviewed
    T2 = "T2"  # wire services, national professional bodies, reference works
    T3 = "T3"  # reputable secondary journalism, trade press
    T4 = "T4"  # blogs, forums, social posts, AI summaries, aggregators


class Tier(StrEnum):
    T1 = "TIER_1_MINOR"
    T2 = "TIER_2_MODERATE"
    T3 = "TIER_3_HEAVY_PENALTY"


class Status(StrEnum):
    CLEAN = "CLEAN"
    PARTIALLY_COMPROMISED = "PARTIALLY_COMPROMISED"
    HEAVILY_PENALIZED = "HEAVILY_PENALIZED"


class MediaType(StrEnum):
    LIVE_VIDEO = "live_video"
    VIDEO = "video"
    AUDIO = "audio"
    ARTICLE = "article"
    SOCIAL_POST = "social_post"
    CAPTION = "caption"


class AnalysisMode(StrEnum):
    FULL = "FULL"
    ROLLING_WINDOW = "ROLLING_WINDOW"


class EnforcementState(StrEnum):
    EXECUTING = "EXECUTING"
    QUEUED = "QUEUED"
    PROVISIONAL = "PROVISIONAL"
    ADVISORY_ONLY = "ADVISORY_ONLY"


class SatireDeception(StrEnum):
    """§3.3. Disclosed satire is excluded from CCR; undisclosed fiction is not."""

    UNDISCLOSED_FICTION = "UNDISCLOSED_FICTION"


class UIAction(StrEnum):
    PIN_CONTEXT_CARD = "PIN_CONTEXT_CARD"
    OVERLAY_WARNING_FLAG = "OVERLAY_WARNING_FLAG"
    MUTE_RANGE = "MUTE_RANGE"


class BiasCode(StrEnum):
    SELECTIVE_FRAMING = "SELECTIVE_FRAMING"
    OMITTED_CONTEXT = "OMITTED_CONTEXT"
    EMOTIONAL_LANGUAGE = "EMOTIONAL_LANGUAGE"
    GENERALIZATION_OVERREACH = "GENERALIZATION_OVERREACH"
    FALSE_EQUIVALENCE = "FALSE_EQUIVALENCE"
    SOURCE_BIAS = "SOURCE_BIAS"
    CONFIRMATION_STRUCTURE = "CONFIRMATION_STRUCTURE"


class Genre(StrEnum):
    POLITICS_GOVT = "POLITICS_GOVT"
    MEDICAL_HEALTH = "MEDICAL_HEALTH"
    ECONOMICS_FINANCE = "ECONOMICS_FINANCE"
    SCIENCE_TECH = "SCIENCE_TECH"
    LEGAL_SAFETY = "LEGAL_SAFETY"
    HISTORY_CULTURE = "HISTORY_CULTURE"
    SPORTS_ATHLETICS = "SPORTS_ATHLETICS"
    GAMING_ESPORTS = "GAMING_ESPORTS"
    LIFESTYLE_DIY = "LIFESTYLE_DIY"
    ENTERTAINMENT_MEDIA = "ENTERTAINMENT_MEDIA"
    SATIRE_PARODY = "SATIRE_PARODY"
    MULTI = "MULTI"


# --- Fixed strings (§5.1). Never paraphrase, never truncate. ---

SATIRE_DISCLAIMER = (
    "NOTICE: THIS CONTENT IS SATIRICAL / PARODY / ENTERTAINMENT AND IS NOT A REAL EVENT "
    "OR FACTUAL REPORT."
)

TIER3_OVERLAY = (
    "CRITICAL WARNING: OVER 20% OF THIS CONTENT CONTAINS VERIFIED FALSEHOODS OR "
    "UNLABELED FABRICATIONS."
)

# --- Source tier -> maximum verdict that tier alone can support (§1.4) ---

MAX_VERDICT_BY_TIER: dict[SourceTier, Verdict] = {
    SourceTier.T1: Verdict.FALSE,
    SourceTier.T2: Verdict.FALSE,
    SourceTier.T3: Verdict.MISLEADING,
    SourceTier.T4: Verdict.UNVERIFIED,
}

#: Verdicts that require at least one T1 or T2 counter-evidence source.
EVIDENCE_BACKED_VERDICTS = frozenset({Verdict.FALSE, Verdict.FABRICATED})

#: Verdict values that may be emitted with zero counter-evidence sources.
UNCORROBORATED_VERDICTS = frozenset(
    {
        Verdict.UNVERIFIED,
        Verdict.CONTESTED,
        Verdict.OUTDATED,
        Verdict.SATIRE_ELEMENT,
        Verdict.MISLEADING,
    }
)

#: Categories where a wrong verdict can cause physical, legal, or civic harm.
#: These force the §6 human review gate regardless of confidence.
HIGH_STAKES_CATEGORIES = frozenset(
    {Genre.MEDICAL_HEALTH, Genre.LEGAL_SAFETY, Genre.POLITICS_GOVT}
)

#: Categories eligible for MUTE_RANGE (§4.1) - all conditions required.
MUTE_ELIGIBLE_CATEGORIES = frozenset(
    {Genre.MEDICAL_HEALTH, Genre.LEGAL_SAFETY, Genre.ECONOMICS_FINANCE}
)

MUTE_MIN_SEGMENT_SECONDS = 30.0

PLATFORMS = (
    "youtube",
    "tiktok",
    "x",
    "meta",
    "instagram",
    "threads",
    "reddit",
    "bluesky",
    "mastodon",
    "linkedin",
    "twitch",
    "snapchat",
    "spotify_podcasts",
    "telegram",
)