# Platform Capability Matrix

> **Generated** by `omni-verify matrix` from the profile registry. Not
> hand-maintained, so it cannot drift from code. Regenerate with
> `python -m omni_verify.cli matrix`.

## Summary

| Platform | Authority | Monetization block | Strike system | Strike API | Native label |
|---|---|---|---|---|---|
| YouTube | centralized | **yes** | Community Guidelines strike | no | — |
| TikTok | centralized | **yes** | Policy point | no | In-app fact-check label |
| Meta (Facebook) | centralized | **yes** | Account status action | no | Fact-check label |
| X | centralized | no | — | — | Community Notes |
| Instagram | centralized | no | Account status action | no | Fact-check label |
| Threads | centralized | no | Account status action | no | Fact-check label |
| LinkedIn | centralized | no | Account restriction | no | — |
| Twitch | centralized | no | Content policy violation | no | — |
| Snapchat | centralized | no | Account action | no | — |
| Spotify (Podcasts) | centralized | no | — | — | — |
| Reddit | **delegated** | no | — (mod/sub ban) | n/a | Post flair |
| Mastodon | **delegated** | no | — (instance silence) | n/a | `boef` plugin |
| Bluesky | **decentralized** | no | — | — | AT Protocol labels |
| Telegram / E2EE | **none** | no | — | n/a | — |

## What "authority" means here

**Centralized** — the platform enforces its own policy and can act on the
creator directly.

**Delegated** — enforcement belongs to individual moderators. Reddit's moderators
control a single subreddit; Mastodon's control a single instance. There is no
cross-subreddit or cross-instance action, and a platform-level "strike" does not
exist as a concept.

**Decentralized** — no central body holds enforcement power. Bluesky's moderation
is performed by independent labeler services; a label is data that any client may
render, ignore, or hide.

**None** — the platform cannot act, full stop. For end-to-end encrypted
messengers this is a cryptographic fact, not a policy choice: Telegram cannot
enforce a verdict against a private channel because it cannot read it.

## Three findings worth stating plainly

**1. Monetization exists on three of fourteen platforms.**
YouTube, TikTok, and Meta have withdrawable per-content revenue. The other
eleven do not. A `FULL_DEMONETIZATION` action on Threads is not a weak action —
it is a meaningless one, and the projection declines it rather than emitting a
field that implies enforcement.

**2. Strike semantics vary more than strike existence.**
YouTube: 3 strikes / 90 days / expire. Meta and Instagram: 3 strikes / 30 days /
do not expire, shared across surfaces on one account. Reddit: a "strike" is a
subreddit ban with no cross-subreddit effect. Telegram: the concept does not
exist. Treating "strike" as one atomic action across these platforms would be
wrong in every direction.

**3. Almost nothing is writable.**
Not one of the fourteen platforms exposes a public write API for the actions in
the canonical vocabulary. `api_writable: false` appears on every projection.
This is why `enforcement_state` defaults to `QUEUED` rather than `EXECUTING` —
the system produces verdicts and a human performs enforcement.

## Machine-readable

```python
from omni_verify.platforms import capability_matrix
for row in capability_matrix():
    ...
```

Or per-platform:

```python
from omni_verify.platforms import get_profile
prof = get_profile("bluesky")
prof.monetization.has_creator_revenue      # False
prof.action_alias("FULL_DEMONETIZATION")   # None
prof.action_alias("SEGMENT_WARNING_BANNER")# "com.atproto.label.defs#label"
```

## Volatility warning

Every field in this matrix reflects public platform behaviour as understood at
the time of writing, and platform policy changes without notice. Strike
thresholds, label programmes, and monetization surfaces in particular are not
stable APIs. Each profile carries a `notes` field and an `api_writable` flag
precisely so that a projection cannot imply more than is currently true.

Treat this as a research artifact, not an integration contract. Re-verify
before relying on any row operationally.