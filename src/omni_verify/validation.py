"""Fail-closed validation (§1.2, §1.4, §5.2).

This module is the reason the system can be trusted. The dangerous failure mode
is not a crash - it is a confident, unsupported ``FALSE`` verdict that inflates
CCR and triggers a wrongful demonetization. Everything below exists to reject
that specific output.

Rules enforced:

R1  ``FALSE`` / ``FABRICATED`` requires >= 1 counter-evidence entry.
R2  ``FALSE`` / ``FABRICATED`` requires >= 1 T1 or T2 source. R1 alone is not
     enough: four T4 blogs citing each other are still four T4 blogs.
R3  T4 alone tops out at ``UNVERIFIED``; T3 alone tops out at ``MISLEADING``.
R4  Retrieval failure caps the verdict at ``UNVERIFIED``.
R5  No flag may carry a correctness verdict - ``SUPPORTED`` is not in the enum.
R6  ``tier``, ``exceeds_heavy_penalty_threshold`` and ``status`` must agree.
R7  Timing: ``timestamp_end`` >= ``timestamp_start``; ``timing_precision``
     must be declared; precision NONE requires null timestamps.
R8  Bias findings never count toward CCR.
R9  Undisclosed satire must be classified ``UNDISCLOSED_FICTION``.
R10 Text media carry no duration fields; time-based media require one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .tier import HEAVY_THRESHOLD_PERCENT, assign_tier, exceeds_heavy_threshold
from .types import AnalysisMode, SourceTier, Status, Verdict

TEXT_MEDIA = frozenset({"article", "social_post", "caption"})
DEFINITIVE_VERDICTS = frozenset({Verdict.FALSE, Verdict.FABRICATED})
AUTHORITATIVE_TIERS = frozenset({SourceTier.T1.value, SourceTier.T2.value})


@dataclass(frozen=True, slots=True)
class Issue:
    rule: str
    path: str
    message: str
    severity: str = "ERROR"

    def __str__(self) -> str:
        return f"[{self.rule}] {self.path}: {self.message}"


def parse_timestamp(ts: str) -> float:
    """Parse ``HH:MM:SS.mmm`` (or ``HH:MM:SS``) into seconds."""
    parts = str(ts).split(":")
    if len(parts) != 3:
        raise ValueError(f"malformed timestamp {ts!r}")
    h, m, s = parts
    return int(h) * 3600 + int(m) * 60 + float(s)


def _get(doc: dict[str, Any], *path: str) -> Any:
    cur: Any = doc
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def validate_verdict(doc: dict[str, Any]) -> list[Issue]:
    """Validate a canonical verdict document. An empty list means valid."""
    issues: list[Issue] = []
    issues += _validate_metadata(doc)
    issues += _validate_flags(doc)
    issues += _validate_bias_flags(doc)
    issues += _validate_satire(doc)
    issues += _validate_media_fields(doc)
    return issues


def assert_valid(doc: dict[str, Any]) -> None:
    issues = validate_verdict(doc)
    if issues:
        joined = "\n  ".join(str(i) for i in issues)
        raise ValueError(f"invalid canonical verdict:\n  {joined}")


# --- R6: internal consistency ------------------------------------------------


def _validate_metadata(doc: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    meta = doc.get("stream_metadata") or {}
    ratio = meta.get("compromised_content_ratio_percent")

    if not isinstance(ratio, (int, float)):
        issues.append(
            Issue("R6", "stream_metadata.compromised_content_ratio_percent",
                  f"must be numeric, got {ratio!r}")
        )
        return issues

    ratio = float(ratio)
    if not 0 <= ratio <= 100:
        issues.append(Issue("R6", "stream_metadata.compromised_content_ratio_percent",
                            f"{ratio} outside [0, 100]"))

    try:
        expected_tier = assign_tier(ratio)
    except ValueError as exc:
        issues.append(Issue("R6", "stream_metadata.compromised_content_ratio_percent", str(exc)))
        return issues

    expected_flag = exceeds_heavy_threshold(ratio)

    tier = _get(doc, "penalization_enforcement", "tier")
    if isinstance(tier, str) and tier != expected_tier.value:
        issues.append(Issue("R6", "penalization_enforcement.tier",
                            f"{tier} inconsistent with CCR {ratio} "
                            f"(expected {expected_tier.value})"))

    threshold_flag = _get(doc, "penalization_enforcement", "exceeds_heavy_penalty_threshold")
    if isinstance(threshold_flag, bool) and threshold_flag != expected_flag:
        issues.append(Issue("R6", "penalization_enforcement.exceeds_heavy_penalty_threshold",
                            f"{threshold_flag} inconsistent with CCR {ratio} "
                            f"(expected {expected_flag})"))

    status = meta.get("status")
    if isinstance(status, str):
        if expected_flag and status != Status.HEAVILY_PENALIZED.value:
            issues.append(Issue("R6", "stream_metadata.status",
                                f"{status} inconsistent with CCR above "
                                f"{HEAVY_THRESHOLD_PERCENT}%"))
        elif ratio == 0 and status != Status.CLEAN.value:
            issues.append(Issue("R6", "stream_metadata.status",
                                f"CCR is 0 so status must be CLEAN, got {status}"))
    return issues


# --- R1-R5: flag-level evidence integrity -----------------------------------


def _validate_flags(doc: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    available = _get(doc, "analyzer", "retrieval_available")
    retrieval_available = True if available is None else bool(available)

    for idx, flag in enumerate(doc.get("precision_flags") or []):
        base = f"precision_flags[{idx}]"
        analysis = flag.get("claim_analysis") or {}
        raw = analysis.get("verdict")

        try:
            verdict = Verdict(raw)
        except ValueError:
            issues.append(
                Issue("R5", f"{base}.claim_analysis.verdict",
                      f"{raw!r} is not a member of the verdict enum; "
                      f"allowed: {[v.value for v in Verdict]}")
            )
            continue

        sources = analysis.get("counter_evidence") or flag.get("counter_evidence") or []
        tiers_present = {
            str(s.get("source_tier")) for s in sources if isinstance(s, dict)
        }
        authoritative = AUTHORITATIVE_TIERS & tiers_present

        if verdict in DEFINITIVE_VERDICTS and not sources:
            issues.append(Issue("R1", f"{base}.claim_analysis.counter_evidence",
                                f"{verdict.value} requires at least 1 counter-evidence entry"))

        if verdict in DEFINITIVE_VERDICTS and sources and not authoritative:
            issues.append(
                Issue("R3", f"{base}.claim_analysis.counter_evidence",
                      f"{verdict.value} requires at least 1 T1 or T2 source; found "
                      f"{sorted(tiers_present)}. T3 alone tops out at MISLEADING, "
                      f"T4 alone at UNVERIFIED.")
            )

        if not retrieval_available and verdict not in {
            Verdict.UNVERIFIED, Verdict.CONTESTED, Verdict.OUTDATED
        }:
            issues.append(Issue("R4", f"{base}.claim_analysis.verdict",
                                f"retrieval unavailable; {verdict.value} must be capped "
                                f"at UNVERIFIED"))

        issues += _validate_timing(base, flag)

    return issues


def _validate_timing(base: str, flag: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    loc = flag.get("location") or {}
    start, end = loc.get("timestamp_start"), loc.get("timestamp_end")
    precision = loc.get("timing_precision")

    if precision not in {"EXACT", "ESTIMATED", "NONE"}:
        issues.append(Issue("R7", f"{base}.location.timing_precision",
                            f"must be EXACT, ESTIMATED or NONE; got {precision!r}"))
        return issues

    if precision == "NONE":
        if start is not None or end is not None:
            issues.append(Issue("R7", f"{base}.location",
                                "timing_precision NONE requires null timestamps"))
        return issues

    if start is None or end is None:
        issues.append(Issue("R7", f"{base}.location",
                            f"timing_precision {precision} requires both timestamps"))
        return issues

    try:
        if parse_timestamp(end) < parse_timestamp(start):
            issues.append(Issue("R7", f"{base}.location",
                                f"timestamp_end {end} precedes timestamp_start {start}"))
    except ValueError as exc:
        issues.append(Issue("R7", f"{base}.location", str(exc)))

    return issues


# --- R8: bias isolation ------------------------------------------------------


def _validate_bias_flags(doc: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for idx, flag in enumerate(doc.get("bias_flags") or []):
        base = f"bias_flags[{idx}]"
        for required in ("original_claim", "verified_fact", "why_biased"):
            if not flag.get(required):
                issues.append(Issue("R8", f"{base}.{required}", "required and non-empty"))
        if flag.get("counts_toward_ccr") is True:
            issues.append(Issue("R8", f"{base}.counts_toward_ccr",
                                "bias findings must never count toward CCR"))
    return issues


# --- R9: satire / deception --------------------------------------------------


def _validate_satire(doc: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    satire = doc.get("satire_protocol") or {}
    if satire.get("is_satire_or_entertainment") and not satire.get("disclosure_present"):
        if satire.get("deception_type") != "UNDISCLOSED_FICTION":
            issues.append(Issue("R9", "satire_protocol.deception_type",
                                "satire without disclosure must be classified "
                                "UNDISCLOSED_FICTION (§3.3)"))
    return issues


# --- R10: media-type conditional fields --------------------------------------


def _validate_media_fields(doc: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    meta = doc.get("stream_metadata") or {}
    media_type = meta.get("media_type")

    if media_type in TEXT_MEDIA:
        if meta.get("total_duration_seconds") is not None:
            issues.append(Issue("R10", "stream_metadata.total_duration_seconds",
                                f"must be null for {media_type}"))
        if not meta.get("total_payload_characters"):
            issues.append(Issue("R10", "stream_metadata.total_payload_characters",
                                f"required and non-null for {media_type}"))
    elif media_type is not None:
        if not meta.get("total_duration_seconds"):
            issues.append(Issue("R10", "stream_metadata.total_duration_seconds",
                                f"required and non-null for {media_type}"))

    mode = meta.get("analysis_mode")
    if mode == AnalysisMode.ROLLING_WINDOW.value and not meta.get("duration_is_estimate"):
        issues.append(Issue("R10", "stream_metadata.duration_is_estimate",
                            "ROLLING_WINDOW mode requires duration_is_estimate true"))

    return issues


__all__ = ["Issue", "validate_verdict", "assert_valid", "parse_timestamp"]