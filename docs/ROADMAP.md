# Roadmap

Honest ordering: by how much each gap degrades the system, not by how easy it
is to build.

## 1. Claim extraction (L2) — blocking

**Status:** interface only. The scoring core is a calculator, not a
fact-checker.

Content that is not extracted as a claim is invisible to CCR. Everything else on
this list is a refinement; this one determines whether the system works at all.

Needs:
- Atomic propositional claim segmentation with span offsets
- Check-worthiness classification (is this claim verifiable at all?)
- Domain routing to specialized analyzers
- Handling for hedged, hypothetical, and reported speech

Open problem: a detector that cannot isolate propositional content should emit
nothing. A false flag on unfalsifiable speech is indistinguishable, to the
subject, from censorship of opinion.

## 2. OCR / visual claim extraction — blocking, highest risk

**Status:** not started.

Audio-only ASR cannot see misinformation carried by on-screen text, chart
labels, or memes. This is a large and common carrier, and its absence means
substantially reduced coverage on short-form video — the highest-volume surface
in the platform matrix.

This is the most likely source of a *confidently wrong* output: a video with a
perfectly clean audio track and a fabricated chart on screen will score clean.

Needs: frame sampling, text detection, chart/figure region extraction, and a
path from rendered text back to timestamps.

## 3. Retrieval and source tiering (L3) — blocking

**Status:** interface only. The evidence gate is implemented and tested; nothing
upstream of it exists.

Needs:
- Query planning from atomic claims
- Source classification against the T1–T4 tiers
- Evidence synthesis and contradiction detection
- Cache keyed on claim hash (cost control)
- Fail-closed behaviour already specified by rule R4

Cost is the real constraint: 2–6 searches plus fetches per flag.

## 4. Live-stream stream-level adjudication

**Status:** rolling-window CCR implemented; stream-level verdict not.

A live stream never has a final CCR at ingest time. Needs an end-of-stream
adjudication pass that recomputes over the full duration and resolves the
provisional tier.

## 5. Review console

**Status:** routing exists, destination does not.

`requires_human_review: true` currently routes nowhere. Needs a queue,
evidence display, and reviewer override that records the disagreement for
calibration.

## 6. Abuse resistance

**Status:** unaddressed.

Known attacks from the threat model (§7):
- Adversarial claim fragmentation to defeat span merging
- Padding payloads to depress CCR
- Flag floods against honest creators
- Authority laundering (false claims hidden inside real citations)

Mitigations in place: `audit` exposes pre/post merge counts and the full
exclusion list, so manipulation is visible rather than hidden in the score.
Rate limiting and reviewer-burden accounting are not built.

## 7. Multilingual coverage

**Status:** unstated, which is its own problem.

Genre taxonomy and source tiers are English-and-Western-institution shaped.
Applying T1/T2 priors to jurisdictions with different record-keeping
misclassifies absence of evidence as evidence of falsity. Rule R5's instinct is
right; the tier definitions need to be locale-aware before multi-jurisdiction
deployment is defensible.

## 8. Benchmark

**Status:** not run. See paper §8.1 for the proposed protocol.

No performance claims should be made about this system until at minimum:
- Claim extraction recall/precision are measured on an annotated corpus
- The fraction of adjudicated false claims where retrieval surfaces T1/T2
- Adversarial robustness under the §7 strategies
- Human-panel agreement on the same verdict set — the ceiling on any automated
  system

## Dependency order

```
1 claim extraction ──┐
                     ├──→ 8 benchmark (nothing is measurable before this)
2 OCR ───────────────┤
                     │
3 retrieval ─────────┴──→ 5 review console ──→ 6 abuse resistance

4 live adjudication can proceed in parallel
7 multilingual is a prerequisite for multi-jurisdiction use, not for launch
```