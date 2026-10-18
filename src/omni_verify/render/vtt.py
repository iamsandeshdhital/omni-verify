"""Media renders: WebVTT warning tracks and Tier 3 overlay spec (§L5)."""

from __future__ import annotations

from typing import Any

from ..types import TIER3_OVERLAY, Tier


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _clean(text: str) -> str:
    """WebVTT cue text cannot contain a bare '-->' sequence."""
    return str(text).replace("-->", "-&gt;").replace("\n", " ").strip()


def render_vtt(canonical: dict[str, Any]) -> str:
    """Emit a WebVTT track with one cue per flagged segment."""
    lines: list[str] = ["WEBVTT", ""]

    meta = canonical.get("stream_metadata") or {}
    stream_id = meta.get("stream_id", "stream")

    tier = (canonical.get("penalization_enforcement") or {}).get("tier")
    if tier == Tier.T3.value:
        lines += [f"NOTE {stream_id}: {TIER3_OVERLAY}", ""]

    for flag in canonical.get("precision_flags") or []:
        loc = flag.get("location") or {}
        start, end = loc.get("timestamp_start"), loc.get("timestamp_end")
        if not start or not end:
            continue  # character-offset findings have no place on a timeline

        analysis = flag.get("claim_analysis") or {}
        verdict = analysis.get("verdict", "UNVERIFIED")
        severity = flag.get("severity", "INFO")

        lines.append(f"{flag.get('flag_id', 'FLAG')}")
        lines.append(f"{start} --> {end}")

        cue = [
            f"[{severity} · {flag.get('category', 'UNCLASSIFIED')} · {verdict}] "
            f"{_clean(analysis.get('statement_made', loc.get('excerpt', '')))}"
        ]
        verified = analysis.get("verified_fact")
        if verified:
            cue.append(f"Verified fact: {_clean(verified)}")
        sources = analysis.get("counter_evidence") or []
        if sources:
            first = sources[0]
            cue.append(
                f"Source: {first.get('source_tier', '?')} — "
                f"{_clean(first.get('source_name', 'unnamed'))}"
            )
        if analysis.get("confidence") is not None:
            cue.append(f"Confidence: {analysis['confidence']}")
        lines += cue + [""]

    return "\n".join(lines)


def overlay_spec(canonical: dict[str, Any]) -> dict[str, Any]:
    """Burn-in specification for the §2.5 full-frame overlay.

    Renderers consume this; the engine does not invoke ffmpeg itself, because
    overlay placement is an editorial decision, not a scoring one.
    """
    enf = canonical.get("penalization_enforcement") or {}
    is_tier3 = enf.get("tier") == Tier.T3.value
    overlay_text = TIER3_OVERLAY if is_tier3 else ""

    return {
        "enabled": is_tier3,
        "text": overlay_text,
        "position": "top_center",
        "persistent": True,
        "burn_in_command": (
            "ffmpeg -i in.mp4 -vf "
            "\"drawtext=text='CRITICAL WARNING: OVER 20%% OF THIS CONTENT CONTAINS "
            "VERIFIED FALSEHOODS OR UNLABELED FABRICATIONS.':"
            "fontcolor=white:fontsize=h/18:box=1:boxcolor=red@0.85:boxborderw=24:"
            "x=(w-text_w)/2:y=h/12\" -c:a copy out.mp4"
            if is_tier3
            else ""
        ),
        "png_overlay_track": f"outputs/{canonical.get('stream_metadata', {}).get('stream_id')}_tier3.png",
    }


__all__ = ["render_vtt", "overlay_spec"]