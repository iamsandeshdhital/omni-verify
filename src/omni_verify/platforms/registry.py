"""Platform registry: capability lookup and projection dispatch."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from ..types import PLATFORMS
from .base import PlatformProfile, ProjectionResult

_MODULES = {
    "youtube": ("youtube", "YOUTUBE"),
    "tiktok": ("tiktok", "TIKTOK"),
    "x": ("x", "X"),
    "meta": ("meta", "META"),
    "instagram": ("instagram", "INSTAGRAM"),
    "threads": ("threads", "THREADS"),
    "reddit": ("reddit", "REDDIT"),
    "bluesky": ("bluesky", "BLUESKY"),
    "mastodon": ("mastodon", "MASTONOD"),
    "linkedin": ("linkedin", "LINKEDIN"),
    "twitch": ("twitch", "TWITCH"),
    "snapchat": ("snapchat", "SNAPCHAT"),
    "spotify_podcasts": ("spotify_podcasts", "SPOTIFY"),
    "telegram": ("telegram", "TELEGRAM"),
}

assert set(_MODULES) == set(PLATFORMS), (
    f"registry/PLATFORMS drift: {set(_MODULES) ^ set(PLATFORMS)}"
)


def _load(platform_id: str) -> PlatformProfile:
    mod_name, attr = _MODULES[platform_id]
    module = __import__(f"omni_verify.platforms.{mod_name}", fromlist=[attr])
    return getattr(module, "PROFILE")


@lru_cache(maxsize=None)
def get_profile(platform_id: str) -> PlatformProfile:
    key = platform_id.strip().lower()
    if key not in _MODULES:
        raise KeyError(
            f"unknown platform {platform_id!r}; known: {sorted(_MODULES)}"
        )
    return _load(key)


def project(platform_id: str, canonical: dict[str, Any]) -> ProjectionResult:
    return get_profile(platform_id).project(canonical)


def all_profiles() -> list[PlatformProfile]:
    return [get_profile(p) for p in sorted(_MODULES)]


def capability_matrix() -> list[dict[str, Any]]:
    """Rows for docs/PLATFORM_MATRIX.md, generated not hand-maintained."""
    rows = []
    for prof in all_profiles():
        rows.append(
            {
                "platform_id": prof.platform_id,
                "display_name": prof.display_name,
                "media_types": list(prof.media_types),
                "monetization_block": prof.monetization.withdrawable,
                "monetization_api_writable": prof.monetization.api_writable,
                "strike_system": prof.strikes.name,
                "strike_api_writable": prof.strikes.api_writable,
                "native_labels": prof.native_labels.name,
                "authority": (
                    "decentralized"
                    if prof.authority.decentralized_labeling
                    else "delegated"
                    if prof.authority.delegated_to_moderators
                    else "centralized"
                    if prof.authority.centralized
                    else "none"
                ),
                "rate_limit": prof.rate_limit,
            }
        )
    return rows


__all__ = ["get_profile", "project", "all_profiles", "capability_matrix"]