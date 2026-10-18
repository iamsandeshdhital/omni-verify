# omni-verify

Multi-platform content integrity engine. Scores a video, post, or article against
a **Compromised Content Ratio (CCR)** and emits an enforcement tier, then projects
that verdict onto each platform's *actual* enforcement capability.

> [!IMPORTANT]
> This system produces **verdicts and recommendations**. It does not demonetize,
> ban, or strike anyone. It cannot — no public API exists for most of those
> actions. Every projection states explicitly what the target platform can and
> cannot do.

---

## The problem this solves

A flat "monetization block + account strike" output is meaningless on X (no
organic ad revenue to withdraw), wrong on Reddit (mods, not the platform), and
absurd on Bluesky or Telegram (no advertising; E2EE means no authority at all).

`omni-verify` separates two concerns that are usually conflated:

1. **Integrity** — what is the ratio of compromised content, and what tier does
   that place it in? Platform-independent.
2. **Enforcement** — what can this specific platform actually do about it?

Integrity is computed once. Enforcement is projected 14 ways.

## Install

```bash
git clone https://github.com/iamsandeshdhital/omni-verify
cd omni-verify
pip install -e ".[api,dev]"
```

The scoring core is **pure standard library** — no runtime dependencies — so a
reviewer can reproduce any published ratio offline with nothing installed.

## Quick start

```bash
omni-verify matrix                      # print the platform capability matrix
omni-verify score examples/sample_post.txt examples/sample_flags.json \
    --stream-id STRM_887102 --platform X --timestamp "2026-10-18T00:00:00Z"
omni-verify project out.json --platforms youtube x bluesky telegram
omni-verify validate out.json
```

Real run against the bundled example:

```
chars        : 1279
flagged      : 361
CCR %        : 28.23
status       : HEAVILY_PENALIZED
tier         : TIER_3_HEAVY_PENALTY | exceeds: True
state        : QUEUED | review: True
verdicts     : ['FALSE', 'MISLEADING', 'UNVERIFIED']
```

Same verdict, four platforms:

| Platform | Projected actions | Declined |
|---|---|---|
| YouTube | monetization block, recommendation filter, strike, overlay | — (no write API; advisory) |
| X | reach suppression | demonetization, strike, overlay |
| Bluesky | — | all four |
| Telegram | — | all four, *and no authority exists* |

## API

```bash
uvicorn omni_verify.api:app --reload
curl -F "payload=@post.txt" -F "flags=$(cat flags.json)" localhost:8000/score
```

`GET /platforms` returns the live capability matrix.

## How it works

```
L0 Ingress      upload · URL · API connector · paste transcript
L1 Canonicalize ASR transcript + platform context -> CanonicalContent
L2 Analyze      claim extraction · satire detect · genre route · bias detect
L3 Verify       query plan -> search -> fetch -> source tiering (T1-T4)
L4 Score        merge spans -> CCR -> tier -> review gate
L5 Project      canonical verdict -> 14 platform projections + VTT + overlay
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and the full
[paper](docs/PAPER.md).

## Design commitments

**Bias is not misinformation.** Framed-but-true content is not compromised
content. Bias findings are reported with `counts_toward_ccr: false` so the ratio
cannot be inflated by calling ordinary opinion "biased."

**Fail closed.** A `FALSE` verdict requires counter-evidence *and* a T1/T2
source. If retrieval fails, verdicts cap at `UNVERIFIED`. A claim is never
upgraded to `FALSE` to push a ratio over threshold — rule R2 in the validator
enforces this and there is a test for it.

**Declining is honest.** On a platform that cannot perform an action, the
projection reports it as declined with a reason, rather than silently emitting a
field that means nothing.

**Boundaries are explicit.** CCR of exactly 20.0% is Tier 2. Tier 3 requires
strictly greater. Both the code and the docs say so, and the boundary is
duplicated deliberately so it cannot be changed in one place and missed in the
other.

## Tests

```bash
python -m pytest -q      # 152 passed
```

Coverage includes the overlap-double-count regression, the 20.0% boundary from
both sides, T4-source-only rejection, bias/CCR isolation, and all 14 platforms.

## Status

- [x] CCR engine, span merging, tier logic, boundary rules
- [x] Fail-closed validator (R1–R10)
- [x] 14 platform capability profiles + projection
- [x] VTT + overlay rendering
- [x] CLI + FastAPI
- [x] Review gate
- [ ] Claim extraction (L2) — pluggable, not implemented
- [ ] Retrieval + source tiering (L3) — pluggable, not implemented
- [ ] OCR for on-screen text — **known gap**, see paper §9
- [ ] Large-scale benchmark — not run, see paper §8

The last three matter. A scoring core with no claim extractor is a calculator,
not a fact-checker. See [`docs/ROADMAP.md`](docs/ROADMAP.md).

## License

MIT — see [LICENSE](LICENSE).

## Documentation

| Document | Contents |
|---|---|
| [PAPER.md](docs/PAPER.md) | Full technical paper: formal CCR, projection model, threat model, limitations |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layer-by-layer design |
| [PLATFORM_MATRIX.md](docs/PLATFORM_MATRIX.md) | Generated capability matrix |
| [SCHEMA.md](docs/SCHEMA.md) | Canonical verdict schema |
| [VERDICT_POLICY.md](docs/VERDICT_POLICY.md) | Evidence rules and review gate |
| [ROADMAP.md](docs/ROADMAP.md) | What is missing |