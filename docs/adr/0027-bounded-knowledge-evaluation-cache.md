# ADR-0027: Bounded knowledge evaluation and candidate cache

- Status: Implemented within approved Phase 5 scope; bounded Phase 5 acceptance and final hosted verification passed
- Owner: Telecom demo maintainer

## Context

Phase 5 evaluates current truth separately from stale-source relevance and wording
repeatability. Engine remains the memory, approval and primary trace owner.

## Decision

Cache only candidate references, query hashes and contextual embeddings in the
knowledge domain. Reuse the existing context-4 query embedding at 1024 dimensions;
this supersedes the initial proposed autoEmbed/512 cache profile for this bounded
candidate cache. No cross-model embedding compatibility is assumed. Current source
checks, ACL/applicability and reranking remain mandatory on a hit. At most 128 hash
slots survive concurrently; logical expiry is at most 15 minutes and cannot exceed
source validity. Use the calibrated 0.91 threshold for the bounded demo; source
revalidation and current-query reranking remain mandatory. TTL cleanup is not an
authorization control.

The evaluator writes only its isolated synthetic corpus. Both new identities have
collection-scoped CRUD roles on OpenAI-SDK. No new Engine memory writer, approval
owner or trace store is introduced. Offline Responses judging uses no tools and
cannot authorize actions. Human reference review is demo owner approval, not an
external SME study. Failures remain in denominators; unavailable metrics are null.

## Alternatives considered

Caching generated answers would require additional response-level correctness and
invalidation evidence. Changing production dimensions after six synthetic queries
would be unjustified. Both are deferred; production knowledge stays at 1024.

## Consequences and tradeoffs

Slot collisions evict entries and may reduce hit rate. Source rereads and reranking
retain costs on a hit. Query-equivalence scores alone cannot establish whether a
candidate set can serve another question. After unsuccessful 0.99/0.98 experiments,
0.91 passed the frozen v3 source-recall and per-group paraphrase criteria: five of
six new paraphrases reused candidates, and all fourteen new queries retained the
correct top-one source. This is synthetic demo evidence, not a universal threshold.
Native session-only trace correlation cannot establish execution-level attribution.
Redacted tool arguments prevent parameter-accuracy grading.

## Validation

[EVAL-001](../tasks/EVAL-001-QUALITY.md) records actual checks, deployed resources,
provider experiments and hosted baseline. Mock tests do not establish
provider quality or capacity. The original failed reports are preserved.

## Revisit trigger

Revisit before answer caching, changing embedding profiles, production use, broader
capacity claims or replacing the synthetic demo reference with real business labels.
