# Verdict Policy and Evidence Rules

## The failure mode this policy exists to prevent

The dangerous output from a content-integrity system is not a crash. It is a
confident, unsupported `FALSE` verdict that inflates CCR past 20% and triggers a
wrongful demonetization.

That specific output is designed to be **unrepresentable**. The rules below are
enforced in `validation.py` and rejection raises before emission.

## Verdict lattice

| Verdict | Meaning | Requires counter-evidence | Requires T1/T2 |
|---|---|---|---|
| `FALSE` | Contradicted by authoritative record | yes | yes |
| `FABRICATED` | Evidence the claim was invented | yes | yes |
| `MISLEADING` | Accurate parts arranged to mislead | no | no |
| `OUTDATED` | Was true, no longer | no | no |
| `CONTESTED` | Credible sources disagree | no | no |
| `UNVERIFIED` | Could not be settled | no | no |
| `SATIRE_ELEMENT` | Recognised fiction, disclosure assessed separately | no | no |

## Source tiers

| Tier | Definition | Max verdict alone |
|---|---|---|
| **T1** | Primary records, court filings, official statistics, regulatory filings, peer-reviewed literature, standards bodies, official datasets | `FALSE` |
| **T2** | Established wire services, national professional bodies, major reference works, university press | `FALSE` |
| **T3** | Reputable secondary journalism, specialist trade press | `MISLEADING` |
| **T4** | Blogs, forums, social posts, AI summaries, aggregator rewrites | `UNVERIFIED` |

**Citation density is not authority.** Four T4 sources agreeing with each other
are still four T4 sources. A retracted blog citing three others is four.

**Tier captures authority, not independence.** Two T1 outlets may share an
upstream dataset. Tiering does not detect that, and the system does not claim to.

## Enforced rules

| Rule | Statement |
|---|---|
| R1 | `FALSE`/`FABRICATED` requires ≥1 `counter_evidence` entry |
| R2 | `FALSE`/`FABRICATED` requires ≥1 T1 or T2 source |
| R3 | T3 alone → `MISLEADING` at most. T4 alone → `UNVERIFIED` at most |
| R4 | If `analyzer.retrieval_available` is false, verdict caps at `UNVERIFIED` |
| R5 | Verdict must be in the enum. No correctness verdict is representable |
| R6 | `tier`, `exceeds_heavy_penalty_threshold`, `status` must agree with CCR |
| R7 | `timestamp_end ≥ timestamp_start`; `timing_precision` required; `NONE` requires nulls |
| R8 | Bias findings require `original_claim`, `verified_fact`, `why_biased`, and `counts_toward_ccr: false` |
| R9 | Undisclosed satire must be classified `UNDISCLOSED_FICTION` |
| R10 | Media-type conditional fields; rolling-window requires `duration_is_estimate` |

### R2 is load-bearing

R1 alone is insufficient. A finding can carry counter-evidence that is entirely
composed of low-tier sources — which is the common case for a confident-looking
wrong answer. R2 is what requires the evidence to actually be authoritative.

There is a test for this specifically:

```python
def test_r2_false_with_only_t4_rejected():
    """Four T4 blogs citing each other are still four T4 blogs."""
```

### R4 is the fail-closed rule

Retrieval can fail: rate limits, network, index changes, or a language the
retriever does not cover. On failure the verdict caps at `UNVERIFIED` and the
finding routes to review.

The absence of a source is not evidence of falsity. A jurisdiction with different
record-keeping will have T1 sources that simply do not exist for a given claim,
and a system that treats that absence as disproof will systematically penalise
speakers from under-documented regions.

## Review gate

Enforcement is **queued, not executed**, when any of:

- A flag in `MEDICAL_HEALTH`, `LEGAL_SAFETY`, or `POLITICS_GOVT` with verdict
  `FALSE` or `FABRICATED`.
- Any Tier 3 trigger.
- `analysis_mode: ROLLING_WINDOW`.
- `analyzer.confidence < 0.70`.

Otherwise `enforcement_state: EXECUTING`.

The rationale is asymmetry of cost. A false positive is a wrongful
demonetization with reputational and possibly legal consequences, and it is
expensive to unwind. A false negative is one video that was not suppressed. When
the costs are not symmetric, default toward the reversible option.

`enforcement_state` values: `EXECUTING`, `QUEUED`, `PROVISIONAL`,
`ADVISORY_ONLY`.

## What the policy does not do

**It does not make verdicts correct.** The evidence gate constrains *unsupported*
verdicts. It does not make retrieval exhaustive, and a `FALSE` backed by a
genuine T1 source is still capable of being wrong about a fast-moving fact.

**It does not detect error in a correct-seeming finding.** Every rule here is a
necessary condition on a verdict, not a sufficient one.

**It does not address selective non-retrieval.** If the analyzer never forms a
claim from content, no rule fires. Coverage is upstream of every rule here, which
is why unimplemented claim extraction is the project's largest limitation.