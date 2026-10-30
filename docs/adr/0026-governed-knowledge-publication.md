# ADR-0026: Governed knowledge publication

- Status: Selected by the user; bounded implementation and evidence in [RAG-001](../tasks/RAG-001-KNOWLEDGE.md)
- Owner: Telecom demo maintainer

## Context

Phase 4 needs PDF curation and retrieval without introducing another approval or
memory owner. Application roles alone do not establish document ownership.

## Decision

Users read eligible sources. Administrators upload metadata/PDFs and run the
isolated ingestion worker. The initial administrator is the operator-registered
information owner. Ownership is an entitlement, not a third application role.
The owner initiates and approves their own exact native Engine publication request.

Engine owns suspension, deadline, decision and completed approval outcome. The
backend verifies requester, workspace, generation and exact metadata digest before
the scoped publisher performs its MongoDB domain transaction. A tool receipt alone
cannot authorize publication. Domain review events bind publications to Engine
executions; they are not a second approval workflow.

The ingestion identity writes only jobs and staged artifacts. The publisher writes
knowledge versions, chunks, current pointers and domain receipts. Reader credentials
have no publication authority. Only scoped reader/ingestion credentials enter the
hosted tools; the private CLI identity stays in the loopback backend.

Versions bind source dates, original PDF checksum and exact replacement key.
UTC dates are canonicalized to BSON millisecond precision before hashing. Source
review dates are curator assertions reviewed by the owner; the native decision time
is recorded separately in its Engine execution and domain publication receipt.
Retrieval rechecks authoritative eligibility before and after reranking and returns
exact excerpts with citations. Oversize responses abstain rather than truncate
operational instructions. No response cache is introduced.

## Alternatives considered

A separate application approval queue or SDK memory writer would duplicate Engine
ownership and is rejected. OCR is isolated from interactive execution. The agent
ingestion tool accepts an already uploaded job ID and requires registered ownership;
all admins can use the curation UI. This narrower tool permission avoids inferring
application admin rights from a hosted caller ID.

## Consequences and tradeoffs

The fixed demo scope and bounded PDF profile are documented in the
[runbook](../runbooks/PHASE_4.md). Document history cleanup is distinct from Engine's
accepted native memory retention. Corpus quality and capacity evaluation remain
Phase 5 work. Publication approval expires; after expiry a new native review is
required even when retrying a previously completed publication.

## Validation

See the [task evidence](../tasks/RAG-001-KNOWLEDGE.md) for live Atlas role/schema,
provider, native review, publication, stale-source exclusion and hosted checks.
Local doubles establish contracts only. No production readiness is asserted.

## Revisit trigger

Revisit before multi-tenant deployment, broader document formats, automated source
cleanup, or replacing the private loopback identity with a production identity.
