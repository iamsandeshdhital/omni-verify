# Canonical Verdict Schema — 1.1.0

## Top-level keys

| Key | Purpose |
|---|---|
| `schema_version` | Schema version string. Semver. |
| `stream_metadata` | Payload identity, denominator, CCR, status |
| `analyzer` | Engine version, confidence, retrieval audit trail |
| `satire_protocol` | Satire classification and disclosure state |
| `penalization_enforcement` | Tier, threshold flag, canonical actions, review state |
| `precision_flags` | Integrity findings. **These drive CCR.** |
| `bias_flags` | Framing findings. **These never drive CCR.** |
| `audit` | Merge counts, exclusions, threshold margin |

## Enumerations are values, not strings of options

Schema 1.0.0 shipped `"media_type": "live_video | audio | article | social_post
| caption"` — a single string listing options, which no validator can constrain
and which silently matched nothing. All enumerations are now single literal
values drawn from a closed set.

```
MediaType      live_video video audio article social_post caption
Verdict        FALSE MISLEADING OUTDATED UNVERIFIED FABRICATED CONTESTED SATIRE_ELEMENT
Severity       INFO MINOR MODERATE HIGH CRITICAL
SourceTier     T1 T2 T3 T4
Tier           TIER_1_MINOR TIER_2_MODERATE TIER_3_HEAVY_PENALTY
Status         CLEAN PARTIALLY_COMPROMISED HEAVILY_PENALIZED
EnforcementState   EXECUTING QUEUED PROVISIONAL ADVISORY_ONLY
UIAction       PIN_CONTEXT_CARD OVERLAY_WARNING_FLAG MUTE_RANGE
Genre          POLITICS_GOVT MEDICAL_HEALTH ECONOMICS_FINANCE SCIENCE_TECH
               LEGAL_SAFETY HISTORY_CULTURE SPORTS_ATHLETICS GAMING_ESPORTS
               LIFESTYLE_DIY ENTERTAINMENT_MEDIA SATIRE_PARODY MULTI
BiasCode       SELECTIVE_FRAMING OMITTED_CONTEXT EMOTIONAL_LANGUAGE
               GENERALIZATION_OVERREACH FALSE_EQUIVALENCE SOURCE_BIAS
               CONFIRMATION_STRUCTURE
```

`SUPPORTED` is deliberately absent from `Verdict`. A correctness verdict is not
a flag; emitting one would put clean content in the same array as compromised
content and invite downstream code to count it.

## Media-type conditional fields

| media_type | Duration fields | Character fields |
|---|---|---|
| `live_video`, `video`, `audio` | required, non-null | must be `null` |
| `article`, `social_post`, `caption` | must be `null` | required, non-null |

Validator rule R10 enforces this. A document carrying both is a scoring bug
waiting to happen — two denominators means two possible ratios.

## Precision flag

```json
{
  "flag_id": "FLAG_001",
  "location": {
    "timestamp_start": "00:01:10.000",
    "timestamp_end": "00:03:40.000",
    "character_start": null,
    "character_end": null,
    "timing_precision": "EXACT",
    "excerpt": "Exact transcription of the segment"
  },
  "category": "MEDICAL_HEALTH",
  "severity": "CRITICAL",
  "claim_analysis": {
    "statement_made": "Restatement of the claim.",
    "original_claim": "The claim exactly as stated. Verbatim.",
    "verified_fact": "What is actually true, with the source basis.",
    "delta": "Precisely how the original differs from the verified fact.",
    "verdict": "FALSE",
    "explanation": "Concise, evidence-backed reason.",
    "confidence": 0.81,
    "retrieval_performed": true,
    "fact_valid_as_of": "2026-10-18",
    "counter_evidence": [
      {
        "source_name": "Authoritative institution or peer-reviewed record",
        "source_tier": "T1",
        "evidence_summary": "What the primary evidence confirms.",
        "reference_url_or_doi": "https://doi.org/10.xxxx/xxxxx",
        "published_date": "2025-06-01"
      }
    ]
  },
  "ui_action_trigger": "OVERLAY_WARNING_FLAG"
}
```

### Why both `original_claim` and `verified_fact`

A verdict that states only a verdict is unreviewable by the person it penalizes.
`original_claim` is what was said, verbatim. `verified_fact` is what the record
shows. `delta` states how they differ. Without all three, an appeal reduces to
disputing an opaque label.

### `fact_valid_as_of`

Real-time correction is not merely epistemic hygiene, it is a correctness
requirement. Facts decay, some get reversed, and a stored verdict with no date
becomes wrong. Every finding carries the date it was true as of.

### Timing

`timing_precision` is mandatory and takes one of:

- `EXACT` — from platform captions or a timestamped transcript
- `ESTIMATED` — inferred from sentence boundaries; must be labelled as such
- `NONE` — no timing available; requires `null` timestamps

Timestamps that look authoritative but were guessed are worse than absent ones.

## Bias flag

```json
{
  "bias_code": "SELECTIVE_FRAMING",
  "category": "POLITICS_GOVT",
  "original_claim": "The policy worked.",
  "verified_fact": "The policy reduced the measured metric by 3%.",
  "why_biased": "Cites one favourable indicator while omitting the two others.",
  "counts_toward_ccr": false
}
```

`counts_toward_ccr` is always `false`. Validator rule R8 rejects `true`. Keeping
bias out of the numerator prevents the metric from being gamed by relabeling
opinion or adversarial framing as "bias" and thereby inflating a verdict.

## Audit block

```json
"audit": {
  "segments_pre_merge": 4,
  "segments_post_merge": 3,
  "near_threshold": false,
  "threshold_margin_note": null,
  "excluded_from_ratio": [],
  "notes": []
}
```

`segments_pre_merge` vs `segments_post_merge` is the dedup transparency
mechanism. A large gap means detectors overlapped heavily; an unusually large
`pre_merge` count against a small `post_merge` count may indicate
deliberate fragmentation.

`near_threshold` is observational only. No action.

## Fixed strings

Emitted verbatim. Never paraphrased, truncated, or localized.

```
SATIRE_DISCLAIMER
NOTICE: THIS CONTENT IS SATIRICAL / PARODY / ENTERTAINMENT AND IS NOT A REAL EVENT
OR FACTUAL REPORT.

TIER3_OVERLAY
CRITICAL WARNING: OVER 20% OF THIS CONTENT CONTAINS VERIFIED FALSEHOODS OR UNLABELED
FABRICATIONS.
```

## Consistency invariants

Three fields encode the same decision and must agree, or the document is invalid
(rule R6):

- `stream_metadata.compromised_content_ratio_percent`
- `penalization_enforcement.tier`
- `penalization_enforcement.exceeds_heavy_penalty_threshold`
- `stream_metadata.status`

Single source of truth is the CCR. `tier` derives from it. `status` derives from
`tier`. Any disagreement means a component computed independently — a bug.

Boundary: CCR of exactly **20.0** is `TIER_2_MODERATE` with
`exceeds_heavy_penalty_threshold: false`. Tier 3 requires strictly greater.

## Validation

```bash
omni-verify validate out.json     # exit 0 valid, 1 invalid
```

Rules R1–R10 are documented in [`VERDICT_POLICY.md`](VERDICT_POLICY.md) and
implemented in `src/omni_verify/validation.py`. Validation runs automatically
before emission with `strict=True` (the default). An emitted-but-invalid verdict
is worse than no verdict — downstream code will trust the field.