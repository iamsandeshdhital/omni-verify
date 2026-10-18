# Enforcement-Capability Projection for Multi-Platform Content Integrity Scoring

*A working technical paper for `omni-verify`. Contains no fabricated results: §8
specifies the evaluation protocol and states plainly that no large-scale
benchmark has been run.*

---

## Abstract

Automated content-integrity systems produce a single verdict — "this content is
misleading" — and hand it to a platform, which then does something with it. In
practice that handoff is broken. The action vocabulary these systems assume
(monetization removal, algorithmic suppression, account strikes, forced overlays)
does not exist uniformly across the platforms such content actually appears on.
X has no organic ad revenue to withdraw. Reddit issues strikes per-subreddit
through individual moderators. Bluesky's protocol holds no enforcement authority
at all, and end-to-end encrypted messengers cannot read the content they would
be asked to act on.

We formalize this gap as the **enforcement-capability projection problem**: given
a platform-independent integrity verdict, determine the maximal legal action set
for a specific target platform, and declare explicitly which requested actions
are unperformable. We introduce the **Compromised Content Ratio (CCR)** — the
fraction of a payload occupied by merged spans of verified-false, misleading,
outdated, or unverified claims — with an explicit span-merging precondition, an
inclusive/exclusive threshold boundary, and a fail-closed evidence gate that
forbids a definitive verdict without tier-1 or tier-2 sourcing.

We describe a reference implementation covering fourteen platforms, a canonical
verdict schema, a validator enforcing ten consistency rules, and a projection
layer with 152 passing tests. We contribute four observations we argue matter
more than the arithmetic: (1) declining an action is a substantive output that
must be reported, not omitted; (2) bias and misinformation must occupy separate
channels or the ratio becomes gameable by relabeling opinion; (3) overlapping
detections must be merged before summation or the ratio is inflated by a
segmentation artifact; and (4) the ratio denominator must include filler a
creator could otherwise inflate to escape the threshold.

---

## 1. Introduction

Content integrity automation has converged on a familiar interface: ingest a
stream, classify segments as compromised or not, compute an aggregate score,
trigger penalties above a threshold. The threshold formulation is attractive
because it is proportional — a single false claim in a ten-hour stream should not
carry the same consequence as a stream that is false throughout.

The formulation breaks in two places.

**The aggregate is not portable.** Enforcement vocabularies are platform-specific
and non-overlapping. A verdict requesting `FULL_DEMONETIZATION` is actionable on
YouTube and meaningless on Bluesky. Systems that emit a single action list
without capability filtering produce logs implying enforcement that never
occurred — a governance failure as much as a technical one.

**The aggregate is easy to game.** Any ratio over a payload admits three
manipulations: (a) inflate the numerator by double-counting overlapping
detections; (b) exclude self-serving spans from the numerator while also
shrinking the denominator; (c) pad the payload with neutral filler. Each is
cheap and none is detectable from the score alone.

We address the first with an explicit projection model and the second with
conservative construction rules. We do not solve adversarial gaming; §7 states
what remains.

### 1.1 Contributions

1. A formal projection model mapping platform-independent verdicts to maximal
   platform-legal action sets, with first-class declaration of declined actions.
2. The CCR with span merging as a mandatory precondition, an explicit boundary
   convention, and a fail-closed evidence gate.
3. Separation of bias analysis from integrity scoring via a non-counting
   channel.
4. A fourteen-platform reference implementation with a machine-checked
   capability matrix and 152 tests.
5. An explicit account of what the system cannot do — coverage, correctness,
   and enforcement execution (§9).

---

## 2. Scope and Assumptions

Payloads are one of: linear video, live video, audio, article, social post, or
caption. Analysis is single-pass; there is no cross-post correlation and no
user-history model. Each stream fragment carries one primary genre code from a
fixed taxonomy (§A.2).

The system computes and reports. It does not enforce. No component holds write
credentials for any platform, and no public write API exists for most of the
actions in the canonical vocabulary (§4.3).

---

## 3. Integrity Model

### 3.1 Compromised Content Ratio

Let a payload $P$ have a coordinate space $X_P$: time in seconds for
time-based media, raw Unicode code points for text. A detector $d$ yields spans
$S_d = \{\langle a, b \rangle\}$ over $X_P$. The compromised set is

$$C = \bigcup_{d \in D} S_d$$

and

$$\mathrm{CCR}(P) = \frac{\lambda(C)}{\lambda(X_P)} \times 100$$

where $\lambda$ is Lebesgue measure. **Overlaps are counted once**, which makes
the union in the numerator load-bearing rather than incidental: if two detectors
both flag $[0, 20]$ and $[10, 30]$, naive summation yields 40 units where the
true compromised extent is 30.

`merge.py` implements this. The merged and pre-merge counts are both reported in
`audit`, so fragmentation or duplication is visible to a reviewer rather than
invisible in the score.

### 3.2 Denominator

$\lambda(X_P)$ is the full payload extent the consumer received.

- Time-based: total runtime, **including** sponsor reads and ad breaks.
- Text: raw code points as received — no normalization, no whitespace trimming,
  no markdown stripping. `word_count` is also emitted so any ratio is
  independently auditable against the raw payload.

Including sponsor reads is deliberate. A creator must not be able to escape the
threshold by inserting ad inventory, which would otherwise inflate the
denominator without reducing the numerator's absolute extent.

### 3.3 Exclusions

Excluded from the numerator, and enumerated in `audit.excluded_from_ratio`:

- Neutral bridge material with no factual assertion (intro, outro, sponsor
  reads, calls to action).
- Satire flagged `SATIRE_ELEMENT` where disclosure is present.

Exclusions reduce the numerator only. They never reduce the denominator.

Satire presents an ambiguity worth naming. Disclosed satire is excluded;
*undisclosed* fiction presented as genuine reporting is classified
`UNDISCLOSED_FICTION` (§3.5) and counted normally. Without this distinction a
properly-labelled comedy special scores as 100% compromised.

### 3.4 Threshold and Boundary

| Tier | CCR | Canonical actions |
|---|---|---|
| Tier 1 | $0 < \mathrm{CCR} \leq 5.0$ | inline context card |
| Tier 2 | $5.0 < \mathrm{CCR} \leq 20.0$ | segment banner, partial monetization hold |
| Tier 3 | $\mathrm{CCR} > 20.0$ | full demonetization, suppression, strike, overlay |

The boundary is **inclusive**: CCR of exactly 20.0 is Tier 2. Tier 3 requires
strictly greater. This is stated in the code, in the docs, and asserted in
`test_tier.py::test_tier_boundaries` from both sides.

An observational band $19.0 \leq \mathrm{CCR} \leq 20.0$ sets
`audit.near_threshold` with an explicit margin note. It triggers no action. It
exists because the difference between a warning and a demonetization should
never come down to a single second of audio that nobody audited.

### 3.5 Satire and synthetic media

Content identified as satire, parody, or fiction sets
`is_satire_or_entertainment`. Disclosed satire is excluded from CCR (§3.3).
Undisclosed fiction presented as breaking news, medical guidance, or an official
statement is `UNDISCLOSED_FICTION` and is scored normally; above 20% it is
treated as deception and receives Tier 3.

The two conditions are independent. `stream_metadata.status` reports integrity
only. In schema 1.0.0 these were conflated — `status` could be both
`HEAVILY_PENALIZED` and `SATIRE_ENTERTAINMENT`, which is not a decidable state.
The validator now rejects it (rule R9).

---

## 4. System Architecture

```
L0  Ingress       upload · URL · API connector · pasted transcript
L1  Canonicalize  ASR transcript + platform context -> CanonicalContent
L2  Analyze       claim extraction · satire detect · genre route · bias detect
L3  Verify        query plan -> search -> fetch -> source tiering
L4  Score         merge spans -> CCR -> tier -> review gate
L5  Project       canonical verdict -> N platform projections + VTT + overlay
```

L1–L5 are implemented. L2 claim extraction and L3 retrieval are pluggable
interfaces and are **not implemented** (§9).

### 4.1 CanonicalContent

Platform-agnostic normalized payload: media type, duration or character count,
transcript segments with speaker and ASR confidence, title, description,
hashtags, caption, engagement, and whether a disclosure widget was present. The
scoring core consumes only `CanonicalContent`; no platform-specific field
reaches the scorer.

### 4.2 The Projection Problem

**Definition.** Let $V$ be a canonical verdict with action set $A(V)$, and let
$P$ be a target platform with capability set $K(P) \subseteq \mathcal{A}$ over the
canonical action vocabulary $\mathcal{A}$. The maximal legal action set is

$$A_P(V) = \{\, a \in A(V) \mid a \in K(P) \,\}$$

and the **declined set** is

$$D_P(V) = A(V) \setminus A_P(V)$$

The projection is $(A_P(V), D_P(V))$ — it must emit **both**. An implementation
returning only $A_P(V)$ loses the operator's ability to distinguish "nothing was
wrong" from "the platform cannot act."

$K(P)$ is declared per platform as a `Capabilities` block over six families:
`monetization_block`, `monetization_hold`, `suppression`, `strike`, `overlay`,
`banner`, plus a canonical-to-native alias map.

### 4.3 Capability Profiles

Fourteen platforms are profiled. The substantive findings:

| Platform | $K(P)$ | Authority | Notes |
|---|---|---|---|
| YouTube | money, suppression, strike, overlay, banner | centralized | No write API. Projections advisory. |
| TikTok | money, suppression, strike, overlay, banner | centralized | Political fact-check labels are regulator-driven |
| X | suppression, banner | centralized | No organic ad revenue; no strike system |
| Meta | money, suppression, strike, banner | centralized | Overlay declined — labels in feed, no burn-in |
| Instagram | suppression, strike, banner | centralized | No per-post monetization withdrawal |
| Threads | suppression, strike, banner | centralized | No creator revenue at all |
| Reddit | suppression, banner | **delegated** | "Strike" is a per-subreddit mod action |
| Bluesky | banner only | **decentralized** | Protocol holds no authority; labels are data |
| Mastodon | suppression, banner | delegated | `boef` fetches an external check URL |
| LinkedIn | suppression, strike, banner | centralized | Heavy finance/health claim density |
| Twitch | suppression, strike, banner | centralized | Revenue attaches to channel, not VOD |
| Snapchat | suppression, strike, banner | centralized | Opaque enforcement |
| Spotify | suppression, banner | centralized | Show-level, not episode-level |
| Telegram | none | **none** | E2EE: enforcement is *impossible*, not unavailable |

Two rows deserve emphasis because they are qualitatively different rather than
merely narrower.

**Reddit** has no platform-level misinformation strike. A "strike" is a
subreddit ban issued by that subreddit's moderators under their own rules, with
no cross-subreddit effect. The correct projection is a moderator briefing — the
finding, the evidence, a suggested flair — not an action claim.

**Telegram** holds no moderation authority over private channels, because
end-to-end encryption means it cannot read them. `has_any_authority=False` is
declared, and every projection is `advisory_only` with `enforcement_state:
PROVISIONAL`. The refusal reason is reported prominently, because an operator
seeing a Tier 3 verdict could otherwise believe a channel was acted against.

### 4.4 Projected Output

```json
{
  "platform_id": "x",
  "supported": true,
  "advisory_only": false,
  "actions_triggered": ["reachSuppression"],
  "unsupported_actions": ["FULL_DEMONETIZATION", "ACCOUNT_STRIKE_ISSUED",
                          "FULL_FRAME_WARNING_OVERLAY"],
  "unsupported_reason": "This platform has no creator revenue stream, so no
                         monetization action exists. Declined: ...",
  "api_payload": { "api_writable": false, "actions_applied": [...],
                   "actions_declined": [...] }
}
```

`api_writable: false` is distinct from `advisory_only: false`. The first means
the actions are legitimate but no public API performs them; the second means
nothing was applied at all.

---

## 5. Evidence Model

### 5.1 Source Tiers

| Tier | Sources | Max verdict supported |
|---|---|---|
| T1 | primary records, court filings, official statistics, regulatory filings, peer-reviewed literature, standards bodies | `FALSE` |
| T2 | wire services, national professional bodies, major reference works | `FALSE` |
| T3 | reputable secondary journalism, specialist trade press | `MISLEADING` |
| T4 | blogs, forums, social posts, generated summaries, aggregators | `UNVERIFIED` |

The tier caps the verdict, not the confidence. Four T4 sources agreeing with
each other are still four T4 sources; citation density is not authority.

### 5.2 Verdict Lattice

`FALSE` · `MISLEADING` · `OUTDATED` · `UNVERIFIED` · `FABRICATED` · `CONTESTED`
· `SATIRE_ELEMENT`

`SUPPORTED` is deliberately not a member. A correctness verdict is not a flag;
emitting one would place clean content in the same array as compromised content
and invite downstream code to count it.

### 5.3 Fail-Closed Validation

Ten rules are enforced in `validation.py`:

- **R1** `FALSE`/`FABRICATED` requires ≥1 counter-evidence entry.
- **R2/R3** `FALSE`/`FABRICATED` requires ≥1 T1 or T2 source. T3 alone tops out
  at `MISLEADING`; T4 alone at `UNVERIFIED`.
- **R4** Retrieval failure caps the verdict at `UNVERIFIED`.
- **R5** Verdict must be a member of the enum. No correctness verdict.
- **R6** `tier`, `exceeds_heavy_penalty_threshold`, and `status` must agree
  with the computed CCR.
- **R7** Timing consistency; `timing_precision` must be declared; `NONE`
  requires null timestamps.
- **R8** Bias findings require `original_claim`, `verified_fact`, `why_biased`,
  and must set `counts_toward_ccr: false`.
- **R9** Undisclosed satire must be classified `UNDISCLOSED_FICTION`.
- **R10** Text media carry no duration fields; rolling-window mode requires
  `duration_is_estimate`.

R2 is the load-bearing rule. The dangerous failure of an automated integrity
system is not a crash — it is a confident unsupported `FALSE` that inflates CCR
and triggers a wrongful demonetization. R2 makes that output unrepresentable.

### 5.4 Bias as a Separate Channel

Framed-but-true content is not compromised content. Bias findings are emitted in
a parallel `bias_flags` array with `counts_toward_ccr: false`, each carrying
`original_claim`, `verified_fact`, and `why_biased`.

Seven codes: `SELECTIVE_FRAMING`, `OMITTED_CONTEXT`, `EMOTIONAL_LANGUAGE`,
`GENERALIZATION_OVERREACH`, `FALSE_EQUIVALENCE`, `SOURCE_BIAS`,
`CONFIRMATION_STRUCTURE`.

Keeping bias out of the numerator is a policy decision with a direct
consequence: it prevents the metric from being gamed by relabeling ordinary
opinion or adversarial framing as "bias" and thereby inflating a verdict against
a speaker. A separate channel forces the distinction to be argued rather than
scored.

---

## 6. Review Gate

Tier assignment is a routing decision, not an execution decision. Enforcement
is queued, not executed, when any of:

- Any flag in `MEDICAL_HEALTH`, `LEGAL_SAFETY`, or `POLITICS_GOVT` with verdict
  `FALSE` or `FABRICATED`.
- Any Tier 3 trigger.
- `analysis_mode: ROLLING_WINDOW`.
- Analyzer confidence below 0.70.

The rationale is asymmetry of cost. A false positive here is a wrongful
demonetization with reputational and possibly legal consequences, and it is
expensive to unwind; a false negative is one video not suppressed. The gate
defaults toward review.

Rolling-window mode warrants specific mention. Live streams have no fixed
duration at ingest time, so CCR is computed over a trailing 600-second window.
Such a CCR is an estimate about a fragment, never about the stream, and never
triggers an account strike on its own.

---

## 7. Threat Model

### 7.1 Metric gaming

| Attack | Mitigation | Residual |
|---|---|---|
| Double-count overlapping detections | Mandatory merge; pre/post counts in `audit` | Adversarial fragmenting to defeat merge |
| Pad payload with filler | Denominator is full payload; exclusions enumerated | Padding still lowers absolute rate |
| Exclude self-serving spans | Exclusions reduce numerator only, never denominator | Exclusion-classification disputes |
| Manufacture flags to force Tier 3 | Evidence gate independent of ratio | Flag floods against honest creators |

### 7.2 Goodhart

Once CCR is a published threshold, content optimized *for* the metric diverges
from content optimized for truth: padding, slowing, and omitting verifiable
claims all lower it. We regard this as inherent to any threshold metric and not
solvable within this design. The mitigation is that the metric is auditable —
denominator, spans, evidence, and verdict are all emitted, so a reader can
dispute the inputs rather than argue about the score.

### 7.3 Authority laundering

A creator who launders a false claim through a "the study says" framing presents
a *citation*, and citations are T4 by default. The system must judge the cited
work, not the citation. This is a retrieval task (L3) and is unimplemented;
claims resting on unresolved citations should resolve to `UNVERIFIED`.

### 7.4 Weaseling

"Some people say X" is unfalsifiable as phrased. A detector that cannot isolate
the propositional content should not emit a flag — a false flag on unfalsifiable
speech is indistinguishable, to the subject, from censorship of opinion.

---

## 8. Evaluation Protocol

**No large-scale benchmark has been run.** This is stated plainly because
impressive-sounding metrics on a system with no implemented claim extractor would
be fiction. What exists is 152 unit and integration tests covering:

- Span merge: overlap, containment, triple overlap, tolerance, unsorted input.
- CCR: exact 20.0, just-over boundary, overlap non-inflation, exclusion
  semantics, sponsor-read denominators, 100% cap.
- Tier: boundary from both sides, status derivation, action sets, near-threshold
  band.
- Evidence: T4-only rejection, T3-only rejection, retrieval-failure capping,
  unknown verdict rejection.
- Bias/CCR isolation.
- All 14 platforms: registry round-trip, capability filtering, no-projection-
  invents-actions invariant, serializability.
- Pipeline: end-to-end assembly, boundary behaviour, disclosure and deception,
  rolling window, review gate routing, mute-range conditions.
- Rendering: VTT cue generation, overlay spec gating.

### 8.1 Proposed benchmarks

Not yet built. Stated so the gap is legible:

1. **Claim extraction recall.** Sample annotated corpora across genres;
   measure detector recall/precision at span level.
2. **Evidence sufficiency.** For adjudicated false claims, measure the fraction
   where retrieval surfaces a T1/T2 source — the binding constraint on `FALSE`.
3. **Adversarial robustness.** Apply known evasion strategies (§7) and measure
   CCR shift.
4. **Cross-platform projection consistency.** Verify that projections never
   claim more than the canonical tier granted (already tested as an invariant).
5. **Reviewer agreement.** Human-panel agreement on the same verdict set —
   the ceiling on any automated system.

---

## 9. Limitations

Stated without hedging, because each one bounds what the system is.

**1. No claim extraction.** The scoring core is a calculator, not a
fact-checker. Content not extracted as a claim is invisible to CCR. This is the
largest limitation by a wide margin.

**2. No retrieval.** L3 is an interface. Evidence in the bundled example is
illustrative. The evidence gate is implemented and tested; nothing upstream of
it is.

**3. No OCR.** Audio-only ASR cannot see misinformation carried by on-screen
text, chart labels, or memes. This is a large and common carrier, and its
absence means the system is substantially blind on short-form video — the
highest-volume surface in the matrix. **This is the most consequential gap after
claim extraction.**

**4. Coverage is unmeasurable without extraction.** CCR describes the payload's
*detected* compromise. A low CCR means little without a recall estimate, and
none exists yet.

**5. Platform data is volatile.** Strike structures, label programs, and
monetization surfaces change without notice. Profiles carry `rate_limit` and
`notes` fields for this reason, but there is no live verification.

**6. Corroboration is not independent.** T1 sources may share upstream data.
Tiering captures authority, not independence.

**7. Facts decay.** Every finding carries `fact_valid_as_of`. A stored verdict
becomes wrong as records update, and nothing re-checks it.

**8. Live streams are only ever fragments.** Rolling-window CCR describes a
600-second window of a stream that may not exist yet.

**9. Language coverage is unstated.** Genre taxonomy and source tiers are
English-and-Western-institution shaped. Applying T1/T2 priors to jurisdictions
with different record-keeping will misclassify *absence of evidence* as
*evidence of falsity* — R5 is the right instinct, but only English-language
retrieval is contemplated.

---

## 10. Ethics and Governance

A system that assigns monetary penalties to creators makes errors that cost
people money. Four commitments follow:

1. **Auditable inputs.** CCR is reproducible from the emitted document. A
   reviewer can recompute the ratio without the engine.
2. **Reversibility.** Queued-by-default enforcement and an `appeal_path` on
   every document.
3. **Declined actions are reported.** An operator must never infer enforcement
   occurred when it did not.
4. **No automation of high-stakes categories.** `MEDICAL_HEALTH`,
   `LEGAL_SAFETY`, and `POLITICS_GOVT` findings with definitive verdicts always
   reach a human.

The system should not be deployed to score political speech at scale without
the governance in §6 in place. Political content is where the false-positive
cost is least bounded and where a Tier 3 finding most plausibly reflects the
analyzer's priors rather than the speaker's claims.

---

## 11. Related Work

Community Notes (X) demonstrates crowdsourced bridging but yields notes, not
enforceable findings. Third-party fact-checking partnerships (Meta) demonstrate
programmatic label submission. `boef` (Mastodon) demonstrates a client fetching
external verification and rendering a warning. The EU DSA transparency and
election-integrity provisions establish a regulatory frame for political-content
labelling. Automated credibility research establishes check-worthiness
detection but not proportional penalty.

The projection problem — mapping one verdict onto heterogeneous enforcement
surfaces — does not appear to have been formalized in this literature. That is
the contribution claimed here, and it is a modest one: the model is a filter
over a capability set. Its value is in making declined actions a first-class,
tested output rather than an implicit failure.

---

## 12. Conclusion

Automated content integrity needs to separate what it *believes* from what a
platform can *do*. CCR with mandatory span merging, an explicit boundary, a
fail-closed evidence gate, and a non-counting bias channel is a defensible
aggregate. Projection with declared capability sets and first-class declined
actions makes that aggregate honest about its consequences.

What exists is the scoring, validation, and projection core — 152 tests, fourteen
platforms, no dependencies. What does not exist is claim extraction, retrieval,
OCR, and any benchmark. A scoring core is a necessary component of a fact-checking
system and is not a fact-checking system. The gap between those two sentences is
where the remaining work is.

---

## Appendix A — Canonical Verdict Schema

Full field documentation in [`SCHEMA.md`](SCHEMA.md). Enumerations are single
literal values; schema 1.0.0 shipped pipe-delimited pseudo-enums as strings,
which no validator can constrain.

Top-level keys: `schema_version`, `stream_metadata`, `analyzer`,
`satire_protocol`, `penalization_enforcement`, `precision_flags`, `bias_flags`,
`audit`.

Every finding carries both `original_claim` (verbatim) and `verified_fact`,
plus `delta` describing how they differ. A verdict that states only a verdict is
unreviewable by the person it penalizes.

## Appendix B — Platform Matrix

Generated by `omni-verify matrix` from the profile registry — not hand-maintained,
so it cannot drift from code. Full table in
[`PLATFORM_MATRIX.md`](PLATFORM_MATRIX.md).

## References

1. X Corp. Community Notes — bridging-based crowdsourced context.
2. Meta. Third-Party Fact Checking Program — programmatic label submission.
3. Mastodon. `boef` anti-misinformation plugin — client-side external verification.
4. Regulation (EU) 2022/2065 (DSA) — Arts. 35, 40; election integrity provisions.
5. Weth, C. et al. *On the Frustrations of Profiteering: A Content Integrity
   Framework for Social Media.* (framing bias taxonomy.)
6. "Cochrane Database of Systematic Reviews" — exemplar T1 source class used in
   `examples/sample_flags.json`.

> Reference 6's record is a genuine example of a T1 medical-evidence source
> class. The specific DOI in the example file is illustrative placeholder data,
> not a citation the engine produced.