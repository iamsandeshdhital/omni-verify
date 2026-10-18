"""Platform capability profiles (Layer 5).

The central architectural claim of this project: enforcement actions are **not**
portable across platforms. Emitting ``FULL_DEMONETIZATION`` for a Bluesky post
produces a field that means nothing and a log that implies an action nobody
took. ``PlatformProfile`` declares what a platform can actually do, and
:mod:`omni_verify.project` filters the canonical action set through it.

Adding a platform is one new module plus a registry line. No core changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

# Canonical action vocabulary (tier.tier_actions) -> per-platform naming.
MONETIZATION_ACTIONS = frozenset({"FULL_DEMONETIZATION", "PARTIAL_MONETIZATION_HOLD"})
SUPPRESSION_ACTIONS = frozenset({"ALGORITHMIC_SUPPRESSION"})
STRIKE_ACTIONS = frozenset({"ACCOUNT_STRIKE_ISSUED"})
OVERLAY_ACTIONS = frozenset({"FULL_FRAME_WARNING_OVERLAY"})
BANNER_ACTIONS = frozenset({"SEGMENT_WARNING_BANNER", "INLINE_CONTEXT_CARD"})

ADVISORY = "ADVISORY_ONLY"


@dataclass(frozen=True, slots=True)
class ModerationAuthority:
    """Who actually holds enforcement power on this surface."""

    centralized: bool
    delegated_to_moderators: bool = False
    decentralized_labeling: bool = False
    has_any_authority: bool = True
    note: str = ""


@dataclass(frozen=True, slots=True)
class StrikeSystem:
    """Native strike semantics, or ``None`` where the platform has none."""

    name: str | None
    strikes_required: int | None
    window_days: int | None
    expires: bool
    api_writable: bool
    note: str = ""


@dataclass(frozen=True, slots=True)
class MonetizationCapability:
    """What revenue can actually be withdrawn, and by what mechanism."""

    has_creator_revenue: bool
    withdrawable: bool
    api_writable: bool
    mechanism: str | None = None
    note: str = ""


@dataclass(frozen=True, slots=True)
class NativeLabelSystem:
    name: str | None
    supports_machine_submission: bool
    note: str = ""


@dataclass(slots=True)
class PlatformProfile(Protocol):
    """Structural contract every platform module implements."""

    platform_id: str
    display_name: str
    media_types: tuple[str, ...]
    authority: ModerationAuthority
    strikes: StrikeSystem
    monetization: MonetizationCapability
    native_labels: NativeLabelSystem
    disclosure_norms: str = ""
    ingest_methods: tuple[str, ...] = ()
    rate_limit: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)

    # -- projection contract ------------------------------------------------

    def action_alias(self, action: str) -> str | None:
        """Map a canonical action to this platform's equivalent.

        Returns ``None`` when the platform cannot perform the action, which is
        what causes the caller to substitute an advisory.
        """
        raise NotImplementedError

    def project(self, canonical: dict[str, Any]) -> "ProjectionResult":
        """Project a canonical verdict into a platform-native payload."""
        raise NotImplementedError


@dataclass(slots=True)
class ProjectionResult:
    platform_id: str
    supported: bool
    actions_triggered: list[str]
    api_payload: dict[str, Any]
    unsupported_actions: list[str] = field(default_factory=list)
    unsupported_reason: str | None = None
    advisory_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform_id": self.platform_id,
            "supported": self.supported,
            "advisory_only": self.advisory_only,
            "actions_triggered": self.actions_triggered,
            "unsupported_actions": self.unsupported_actions,
            "unsupported_reason": self.unsupported_reason,
            "api_payload": self.api_payload,
        }