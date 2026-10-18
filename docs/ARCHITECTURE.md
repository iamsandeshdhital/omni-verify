# Architecture

## The separation

Two concerns are usually conflated in content-integrity systems. They are not
the same problem.

**Integrity** — what fraction of this payload is compromised, and what tier does
that place it in? Platform-independent. Pure arithmetic over declared inputs.

**Enforcement** — what can this specific platform actually do about it?
Platform-specific. A filter over a declared capability set.

Integrity is computed once and is identical for every platform. Enforcement is
projected N ways, and the projections are genuinely different from each other.

A single Tier 3 verdict (28.2% CCR on a 1,279-character post) produces:

| Platform | Applied | Declined |
|---|---|---|
| YouTube | monetization block, recommendation filter, strike, overlay | — |
| X | reach suppression | demonetization, strike, overlay |
| Bluesky | — | all four |
| Telegram | — | all four, no authority exists |
| Reddit | downrank advisory | demonetization, strike, overlay |

Same verdict. Four different realities. An implementation that emitted one flat
action list would be wrong on four of these five platforms.

---

## Layers

```
┌─ L0 INGRESS ─────────────────────────────────────────────────┐
│  Upload · URL · Platform API connector · Paste transcript      │
└───────────────────────────┬────────────────────────────────────┘
                            ▼
┌─ L1 CANONICALIZE ────────────────────────────────────────────┐
│  Media download → audio extract → ASR transcript → captions   │
│  Attach platform context: title, description, hashtags,       │
│  caption, comments, engagement, disclosure widgets            │
│  → CanonicalContent (platform-agnostic)                       │
└───────────────────────────┬────────────────────────────────────┘
                            ▼
┌─ L2 ANALYZE (parallel fan-out) ───────────────────────────────┐
│  ┌───────────┐ ┌─────────────┐ ┌────────┐ ┌───────────────┐  │
│  │ Claim     │ │ Satire /    │ │ Genre  │ │ Bias          │  │
│  │ extraction│ │ fiction det │ │ routing│ │ detection     │  │
│  └─────┬─────┘ └─────────────┘ └───┬────┘ └───────┬───────┘  │
│        └────────────┬──────────────┴───────────────┘          │
│                     ▼                                         │
│        Domain analyzers: MEDICAL · LEGAL · FINANCE ·          │
│        POLITICAL · SCIENCE · SPORTS · GAMING · DIY            │
└───────────────────────────┬───────────────────────────────────┘
                            ▼
┌─ L3 VERIFY (retrieval) ───────────────────────────────────────┐
│  Query planner → search → fetch → source tierer (T1–T4)       │
│  Verdict assignment with tier caps                            │
│  Fail-closed: no retrieval → cap at UNVERIFIED → human review │
└───────────────────────────┬───────────────────────────────────┘
                            ▼
┌─ L4 SCORE ────────────────────────────────────────────────────┐
│  Merge spans (§2.3) → CCR → tier → review gate (§6)           │
└───────────────────────────┬───────────────────────────────────┘
                            ▼
┌─ L5 PROJECT ──────────────────────────────────────────────────┐
│  Canonical JSON (schema 1.1.0)                                 │
│      ├─→ 14 platform projections (capability-filtered)        │
│      ├─→ WebVTT warning track                                 │
│      └─→ Tier 3 ffmpeg burn-in spec                            │
└───────────────────────────────────────────────────────────────┘
```

**Implemented:** L0, L1, L4, L5, plus the evidence gate that L3 depends on.
**Not implemented:** L2 claim extraction, L3 retrieval, OCR.

---

## Why capability filtering lives in its own layer

If it were folded into scoring, the scorer would need to know platform policy,
and the policy would leak into the CCR. That is how a threshold rule acquires a
platform-specific carve-out and becomes unpredictable.

Keeping projection at L5 means the canonical verdict is the single auditable
record. Anyone can recompute a CCR without knowing anything about any platform.

---

## Projection model

**Definition.** Let $V$ be a canonical verdict with action set $A(V)$, and $P$ a
target platform with capability set $K(P) \subseteq \mathcal{A}$. Then

$$A_P(V) = \{\, a \in A(V) \mid a \in K(P) \,\}, \qquad D_P(V) = A(V) \setminus A_P(V)$$

The projection emits **both**. Emitting only $A_P(V)$ destroys the operator's
ability to distinguish "nothing was wrong with this content" from "the platform
cannot do anything about it" — which are very different situations requiring
very different responses.

`Capabilities` declares six families per platform plus an alias map:

```python
Capabilities(
    monetization_block=False,   # can revenue actually be withdrawn?
    monetization_hold=False,
    suppression=True,            # can ranking be changed?
    strike=False,                # is there a platform-level strike?
    overlay=False,               # can a frame burn-in be forced?
    banner=True,                 # can a label/notice be attached?
    aliases={SUPPRESSION: "reachSuppression"},
)
```

---

## Module map

```
src/omni_verify/
├─ types.py        enums, fixed strings, tier caps      (no logic)
├─ merge.py        span merging + union length
├─ ccr.py          denominator selection, CCR, exclusions
├─ tier.py         boundaries, action sets, review gate
├─ validation.py   rules R1–R10
├─ pipeline.py     assembly: findings → validated verdict
├─ cli.py          score / validate / project / render / matrix
├─ api.py          FastAPI upload endpoint
├─ ingest/
│  └─ canonical.py CanonicalContent, from_text, from_transcript
├─ render/
│  └─ vtt.py       WebVTT cues, overlay burn-in spec
└─ platforms/
   ├─ base.py      PlatformProfile protocol, capability dataclasses
   ├─ projection.py Capabilities, filter_actions, ConcreteProfile
   ├─ registry.py  lookup + generated capability matrix
   └─ <14 modules> one file per platform
```

Adding a platform: write one module, add one line to `_MODULES` in `registry.py`.
The assertion at the top of that file fails loudly if the registry and
`types.PLATFORMS` drift apart.

---

## Data flow

```
CanonicalContent
    + list[RawFlag]
    + list[RawBiasFlag]
    + genre, satire, disclosure, confidence
        │
        ▼
   compute_ccr()      merge → subtract exclusions → union length / denominator
        │
        ▼
   assign_tier()      strict > 20.0 boundary
        │
        ▼
   evaluate_review_gate()   high-stakes? tier 3? rolling? low confidence?
        │
        ▼
   validate_verdict()  R1–R10, raises on failure
        │
        ├──→ canonical verdict (JSON)
        ├──→ project(p) for each of 14 platforms
        ├──→ render_vtt()  warning track
        └──→ overlay_spec()  burn-in spec
```

Validation runs **before** emission by default (`strict=True`). A verdict that
fails R1–R10 is not emitted, because an emitted-but-invalid verdict is worse
than no verdict — downstream code will trust the field.

---

## Dependency policy

The scoring core is **pure standard library**. Zero runtime dependencies.

This is a deliberate constraint, not an accident. A reviewer's first question
about a content-integrity tool should not be `pip install` something. The core
must run on an air-gapped regulator's machine, in a CI sandbox, and on a laptop
in a courtroom, all with nothing installed.

Optional extras:

| Extra | Adds | Needed by |
|---|---|---|
| `api` | FastAPI, uvicorn | `omni_verify.api` |
| `verify` | httpx, tiktoken | L3 retrieval (unimplemented) |
| `asr` | faster-whisper | L1 transcription |
| `dev` | pytest, ruff, mypy | development |

---

## Known gaps

| Gap | Consequence |
|---|---|
| No claim extraction (L2) | Scoring core is a calculator, not a fact-checker |
| No retrieval (L3) | Evidence gate tested, nothing upstream of it |
| **No OCR** | Blind to misinformation in on-screen text, charts, memes — the most common carrier on short-form video |
| No live-stream reassignment | Rolling-window CCR never resolves to a stream-level verdict |
| No cross-post correlation | Same false claim repeated across accounts scored independently |
| No reviewer UI | `requires_human_review` routes to a queue that does not exist yet |

The OCR gap is the one most likely to produce a confidently wrong answer: a
video can have a perfectly clean audio track and a fabricated chart on screen.