# Security Policy

## Reporting a vulnerability

Open a private GitHub security advisory. Do not open a public issue for an
unfixed vulnerability.

## Threat model

This project is a **scoring and projection** system. It reads content, computes
a ratio, and emits a verdict document. It has no privileged write access to any
platform.

### What this system can be trusted to do

- Produce a reproducible CCR from a declared denominator and a merged flag set.
- Reject verdicts that lack authoritative evidence (rules R1–R5).
- Refuse to claim an enforcement action a platform cannot perform.

### What it cannot do

- Guarantee that a `FALSE` verdict is correct. The evidence gate constrains
  *unsupported* verdicts; it does not make retrieval exhaustive.
- Guarantee coverage. Content that is not extracted as a claim is not scored.
  This is the single largest limitation (paper §9).
- Execute enforcement. It has no write path to any platform.

### Risks we specifically consider

**Verdict inflation.** An adversary who knows the scoring rule can pad flagged
segments to trigger Tier 3, or fragment claims so merges understate them.
Mitigations: the `audit` block reports pre-merge and post-merge counts, so
fragmentation is visible; the validator enforces evidence requirements
independently of ratio.

**Weaseling.** A creator can pad a post with neutral filler to depress CCR.
Mitigations: the denominator is the full payload including sponsor reads; §2.4
exclusions are enumerated in `audit.excluded_from_ratio` rather than applied
silently.

**Denial of review.** Mass-flagging could flood the review queue. Not yet
mitigated; see ROADMAP.

## Secrets

The scoring core requires no credentials. Retrieval (L3, unimplemented) is
designed to sit behind a separate key-bearing service boundary so that an
air-gapped scoring deployment stays air-gapped.

Never commit tokens. This repository's history has been kept free of
credentials; if you find one, report it privately and it will be rotated.