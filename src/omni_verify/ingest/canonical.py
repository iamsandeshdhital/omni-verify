"""Ingest: raw payload -> CanonicalContent.

The upload path is the reliable one. Platform API connectors are best-effort
because of quotas and terms-of-service restrictions on bulk content access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..types import MediaType


@dataclass(slots=True)
class Segment:
    start: float
    end: float
    text: str
    speaker: str | None = None
    confidence: float | None = None  # ASR confidence, not factual confidence


@dataclass(slots=True)
class CanonicalContent:
    """Platform-agnostic normalized payload."""

    stream_id: str
    media_type: MediaType
    platform: str
    total_duration_seconds: float | None = None
    text: str | None = None
    segments: list[Segment] = field(default_factory=list)
    title: str | None = None
    description: str | None = None
    hashtags: list[str] = field(default_factory=list)
    caption: str | None = None
    source_url: str | None = None
    engagement: dict[str, Any] = field(default_factory=dict)
    disclosure_widget_present: bool | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def total_payload_characters(self) -> int:
        """Raw code points, no normalization (§2.2)."""
        return len(self.text or "")

    @property
    def word_count(self) -> int:
        return len((self.text or "").split())


def from_text(
    *,
    stream_id: str,
    platform: str,
    text: str,
    media_type: MediaType = MediaType.SOCIAL_POST,
    **kwargs: Any,
) -> CanonicalContent:
    return CanonicalContent(
        stream_id=stream_id,
        media_type=media_type,
        platform=platform,
        text=text,
        **kwargs,
    )


def from_transcript(
    *,
    stream_id: str,
    platform: str,
    segments: list[Segment],
    total_duration_seconds: float,
    media_type: MediaType = MediaType.VIDEO,
    **kwargs: Any,
) -> CanonicalContent:
    return CanonicalContent(
        stream_id=stream_id,
        media_type=media_type,
        platform=platform,
        segments=segments,
        total_duration_seconds=total_duration_seconds,
        text=" ".join(s.text for s in segments).strip(),
        **kwargs,
    )


def validate(content: CanonicalContent) -> list[str]:
    """Cheap structural checks before the expensive analysis stages run."""
    problems: list[str] = []
    if not content.segments and not content.text:
        problems.append("content has neither transcript segments nor text")
    if content.media_type in {MediaType.ARTICLE, MediaType.SOCIAL_POST, MediaType.CAPTION}:
        if not content.text:
            problems.append(f"{content.media_type} requires text")
    else:
        if not content.total_duration_seconds or content.total_duration_seconds <= 0:
            problems.append(f"{content.media_type} requires a positive total_duration_seconds")
    for seg in content.segments:
        if seg.end < seg.start:
            problems.append(f"segment {seg.start}-{seg.end} ends before it starts")
    return problems


__all__ = ["CanonicalContent", "Segment", "from_text", "from_transcript", "validate"]