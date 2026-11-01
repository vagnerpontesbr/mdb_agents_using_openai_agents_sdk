# ADR-0033: Governed language source lineage

- Status: Implemented locally; Atlas validator application and multilingual acceptance pending
- Date: 2026-11-01
- Owner: Telecom demo maintainer
- Refines: [ADR-0026](0026-governed-knowledge-publication.md), [ADR-0032](0032-multilingual-profile.md)

## Context

Knowledge versions/chunks currently permit only English. Expanding the interface
cannot authorize a translated procedure. A translation can become unsafe if its
original is revoked, replaced or no longer available to the reader. Existing native
approval digests must survive an additive schema change.

## Decision

Allow en, pt and es in the existing language field; retain exact language filters,
source checks, tenant/ACLs, native approval, current-version pointers and immutable
source bytes. An independently authored source in any supported language still
requires its own owner review and approval. The uploader declares whether a source
is a translation; the information owner reviews that declaration with the content.
There is no LLM authority to approve a translation or classify away its lineage.

A declared translation supplies one optional translation_of field containing the
original immutable version key. That reference is part of the translated version's
approval digest. Resolve it only in the same tenant, verify its key, require a
separate document and a different language, and reject references to translations.
This bounds lineage to one original and prevents chains/cycles.

Both sources must satisfy current approval, owner, checksum, dates, applicability
and reader ACL checks. Revalidate the original before releasing a cached translation
as well as during publication assessment. A translation becomes unavailable when
its original becomes ineligible; no mass rewrite or secondary cache writer is needed.
This does not prove translation fidelity: reviewed sources and semantic acceptance
remain mandatory.

Omit an absent translation_of during all serialization, including native review
requests and metadata hashes. Preserve the exact existing English digest. Do not
bulk rewrite existing versions or invalidate old approvals merely to add a default.

## Storage rollout and rollback

The exact proposal is [LANG-2c validators](../../compatibility/lang2c-validator-proposal.json).
It changes only document_versions and chunks validators in telecom_demo_knowledge on
OpenAI-SDK, retaining strict/error mode and every unrelated constraint. Read-only
Atlas inspection found no drift and zero existing documents requiring a rewrite.
No role, index, Engine policy or memory configuration change is included.

Apply only after explicit approval and a fresh drift/data preflight. Two collMod
operations are not atomic together; the script verifies each and supports resuming
an already partially applied proposal. Do not silently downgrade validators after
new-language documents exist. Before any such writes, exact old validators can be
restored after checking compatibility. Afterward, disable new uploads and retain
compatible readers/validators until an explicitly reviewed rollback is available.

## Validation and remaining gate

Local tests cover the old approval hash, both language enums, exact tenant/key lookup,
expired/revoked/replaced originals, wrong ACL/tenant, bounded lineage, cached-source
revocation before release, and migration preflight/scope enforcement. They do not
claim Atlas enforcement, published translations, hosted semantic quality or speech
acceptance. I18N-001 remains the authoritative phase record.


## Alternatives considered

Unreviewed runtime translation can alter operational instructions. Copying the
original approval to a translated source fails to bind its different bytes. A
separate collection per language adds unnecessary ownership and migration surfaces.
Unbounded translation chains complicate revocation; a single original reference
keeps every release check bounded.

## Consequences and tradeoffs

Translated versions require their own review and additional original-source reads.
Revoking an original can make otherwise current translations unavailable, favoring
safe refusal over stale instructions. Existing English approval hashes remain
stable. Owners must review whether an upload is original or translated; schema
validation cannot establish linguistic equivalence.

## Revisit trigger

Translation chains, multiple originals, additional languages, changed approval-hash
rules, or a requirement to keep translations valid after their original is withdrawn.
