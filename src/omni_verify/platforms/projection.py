"""Shared capability-filtering projection.

Every platform module supplies a :class:`Capabilities` block; the logic that
turns a canonical verdict into a platform-legal action list is identical
everywhere, so it lives here rather than being copied 14 times.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import (
    ADVISORY,
    BANNER_ACTIONS,
    MONETIZATION_ACTIONS,
    OVERLAY_ACTIONS,
    STRIKE_ACTIONS,
    SUPPRESSION_ACTIONS,
    ModerationAuthority,
    MonetizationCapability,
    NativeLabelSystem,
    PlatformProfile,
    ProjectionResult,
    StrikeSystem,
)

MONETIZATION_BLOCK = "FULL_DEMONETIZATION"
MONETIZATION_HOLD = "PARTIAL_MONETIZATION_HOLD"
SUPPRESSION = "ALGORITHMIC_SUPPRESSION"
STRIKE = "ACCOUNT_STRIKE_ISSUED"
OVERLAY = "FULL_FRAME_WARNING_OVERLAY"
BANNER = "SEGMENT_WARNING_BANNER"
CARD = "INLINE_CONTEXT_CARD"


@dataclass(frozen=True, slots=True)
class Capabilities:
    """Which canonical action families this platform can actually perform."""

    monetization_block: bool = False
    monetization_hold: bool = False
    suppression: bool = False
    strike: bool = False
    overlay: bool = False
    banner: bool = False

    #: canonical action -> platform-native action name
    aliases: dict[str, str] = field(default_factory=dict)

    def allows(self, action: str) -> bool:
        if action == MONETIZATION_BLOCK:
            return self.monetization_block
        if action == MONETIZATION_HOLD:
            return self.monetization_hold
        if action in SUPPRESSION_ACTIONS:
            return self.suppression
        if action in STRIKE_ACTIONS:
            return self.strike
        if action in OVERLAY_ACTIONS:
            return self.overlay
        if action in BANNER_ACTIONS:
            return self.banner
        return False


def classify(action: str) -> str:
    if action in MONETIZATION_ACTIONS:
        return "monetization"
    if action in SUPPRESSION_ACTIONS:
        return "suppression"
    if action in STRIKE_ACTIONS:
        return "strike"
    if action in OVERLAY_ACTIONS:
        return "overlay"
    return "banner"


def filter_actions(
    actions: list[str], caps: Capabilities
) -> tuple[list[str], list[str]]:
    """Split canonical actions into (platform-native, unsupported)."""
    supported: list[str] = []
    unsupported: list[str] = []
    for action in actions:
        if caps.allows(action):
            supported.append(caps.aliases.get(action, action))
        else:
            unsupported.append(action)
    return supported, unsupported


def project_canonical(
    profile: PlatformProfile,
    canonical: dict[str, Any],
    caps: Capabilities,
) -> ProjectionResult:
    """Project canonical -> platform-native, filtering by capability."""
    enf = (canonical.get("penalization_enforcement") or {})
    actions = list(enf.get("actions_triggered") or [])
    supported, unsupported = filter_actions(actions, caps)

    tier = enf.get("tier")
    state = enf.get("enforcement_state", "QUEUED")
    enforced = [a for a in supported if a != ADVISORY]

    advisory_only = not enforced
    no_authority = not profile.authority.has_any_authority
    api_writable = (
        profile.monetization.api_writable
        or profile.strikes.api_writable
    ) and bool(enforced) and state != "PROVISIONAL"

    reasons: list[str] = []
    if no_authority:
        reasons.append(
            profile.authority.note
            or "Platform holds no moderation authority over this surface."
        )
    if unsupported:
        reasons.append(_unsupported_reason(profile, unsupported))
    if enforced and not api_writable:
        reasons.append(
            "No public write API exists for these actions. Projection is advisory; "
            "a human must execute them."
        )

    reason = " ".join(reasons) if reasons else None

    payload = {
        "stream_id": (canonical.get("stream_metadata") or {}).get("stream_id"),
        "tier": tier,
        "enforcement_state": "PROVISIONAL" if no_authority else state,
        "actions_applied": supported,
        "actions_declined": unsupported,
        "api_writable": api_writable,
        "advisory_only": advisory_only,
    }
    if unsupported:
        payload["unsupported_reason"] = reason

    return ProjectionResult(
        platform_id=profile.platform_id,
        supported=bool(enforced) and not no_authority,
        actions_triggered=supported,
        api_payload=payload,
        unsupported_actions=unsupported,
        unsupported_reason=reason,
        advisory_only=advisory_only,
    )


def _unsupported_reason(profile: PlatformProfile, unsupported: list[str]) -> str:
    families = sorted({classify(a) for a in unsupported})
    if "monetization" in families and not profile.monetization.has_creator_revenue:
        money = "This platform has no creator revenue stream, so no monetization action exists."
    elif "strike" in families and profile.strikes.name is None:
        money = "This platform has no platform-level strike system."
    elif "strike" in families:
        money = "Strikes are issued by individual moderators, not the platform."
    else:
        money = "This platform cannot perform the requested action."
    declined = ", ".join(sorted(set(unsupported)))
    return f"{money} Declined: {declined}."


class ConcreteProfile:
    """Default :class:`PlatformProfile` implementation.

    A real class rather than a closure factory: a ``class`` body does not
    resolve free names from an enclosing function scope, so the closure form
    silently raised ``NameError`` at import time.
    """

    __slots__ = (
        "platform_id", "display_name", "media_types", "authority", "strikes",
        "monetization", "native_labels", "disclosure_norms", "ingest_methods",
        "rate_limit", "notes", "capabilities",
    )

    def __init__(
        self,
        *,
        platform_id: str,
        display_name: str,
        media_types: tuple[str, ...],
        authority: ModerationAuthority,
        strikes: StrikeSystem,
        monetization: MonetizationCapability,
        native_labels: NativeLabelSystem,
        disclosure_norms: str,
        ingest_methods: tuple[str, ...],
        rate_limit: str,
        capabilities: Capabilities,
        notes: tuple[str, ...] = (),
    ) -> None:
        self.platform_id = platform_id
        self.display_name = display_name
        self.media_types = media_types
        self.authority = authority
        self.strikes = strikes
        self.monetization = monetization
        self.native_labels = native_labels
        self.disclosure_norms = disclosure_norms
        self.ingest_methods = ingest_methods
        self.rate_limit = rate_limit
        self.capabilities = capabilities
        self.notes = notes

    def action_alias(self, action: str) -> str | None:
        if not self.capabilities.allows(action):
            return None
        return self.capabilities.aliases.get(action, action)

    def project(self, canonical: dict[str, Any]) -> ProjectionResult:
        return project_canonical(self, canonical, self.capabilities)

    def __repr__(self) -> str:  # pragma: no cover - display only
        return f"<ConcreteProfile {self.platform_id}>"


def make_profile(**kwargs: Any) -> ConcreteProfile:
    """Build a platform profile. ``capabilities`` is required."""
    if "capabilities" not in kwargs:
        raise TypeError(
            f"{kwargs.get('platform_id', '<unknown>')}: make_profile requires "
            "capabilities=CAPABILITIES"
        )
    return ConcreteProfile(**kwargs)