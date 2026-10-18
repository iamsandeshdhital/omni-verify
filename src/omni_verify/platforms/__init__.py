"""Platform capability profiles (Layer 5)."""

from __future__ import annotations

from .base import (
    ModerationAuthority,
    MonetizationCapability,
    NativeLabelSystem,
    PlatformProfile,
    ProjectionResult,
    StrikeSystem,
)
from .registry import all_profiles, capability_matrix, get_profile, project

__all__ = [
    "ModerationAuthority",
    "MonetizationCapability",
    "NativeLabelSystem",
    "PlatformProfile",
    "ProjectionResult",
    "StrikeSystem",
    "all_profiles",
    "capability_matrix",
    "get_profile",
    "project",
]