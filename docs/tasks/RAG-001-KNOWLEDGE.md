# RAG-001: Governed PDF knowledge

- Status: Complete for the bounded demo; published as `1a52afc`, CI passed
- Scope: Phase 4 acceptance; subsequent Phase 5 work is tracked in [EVAL-001](EVAL-001-QUALITY.md)
- Decision: [ADR-0026](../adr/0026-governed-knowledge-publication.md)
- Contracts: [governance](../DOCUMENT_GOVERNANCE.md), [runbook](../runbooks/PHASE_4.md)

## Implemented behavior

Authenticated users search and download currently eligible sources. Administrators
upload PDFs and source metadata, inspect jobs and start the isolated worker. The
registered owner initiates and approves their exact native Engine publication
request. Publication atomically writes immutable content, chunks, current pointer
and a native-bound domain receipt; replacements retire the exact previous version.
Engine remains the approval and memory owner. OpenAI Agents SDK orchestrates the
specialists, including hosted search and idempotent ingestion-request tools.

Seven Atlas collections have strict/error validators. Three scoped identities
separate ingestion, publication and reads on OpenAI-SDK. ClusterDemoTelco remains
Engine-managed memory. Both contextual and lexical search indexes are READY.
The user approved the exact shared tool policy expansion from 31 to 34 names and
the initial owner/role mapping. No authorization decision remains pending.

## Live evidence

| Acceptance | Portable evidence |
| --- | --- |
| 96 scoped CRUD checks and READY indexes | [resources](../../compatibility/phase4-resource-evidence.json) |
| Core schema and native fusion wire contract | [storage](../../compatibility/phase4-storage-evidence.json) |
| Remaining five collection validators | [curation schemas](../../compatibility/phase4-curation-schema-evidence.json) |
| Owner entitlement | [owner](../../compatibility/phase4-owner-evidence.json) |
| Exact shared policy change | [policy](../../compatibility/phase4-engine-policy-evidence.json) |
| Text/scanned Docling and actual context-4/rerank provider calls | [provider](../../compatibility/phase4-provider-evidence.json) |
| Transactional admission, leases, real extraction/embedding/staging | [ingestion](../../compatibility/phase4-ingestion-evidence.json) |
| Native reject/approve, idempotent publication, citations, tenant/ACL denial and original download | [publication](../../compatibility/phase4-publication-evidence.json) |
| Native rejection/approval, atomic replacement and old-source denial | [replacement](../../compatibility/phase4-replacement-evidence.json) |
| Hosted technical search/ingestion, invoice/sales and mixed regression | [hosted](../../compatibility/phase4-hosted-evidence.json) |
| Revoked, expired, overdue, changed-checksum and ACL sources excluded despite stale chunks | [invalidation](../../compatibility/phase4-invalidation-evidence.json) |

Full hosted deployment `deploy-1e78b4dd` succeeded on 2026-10-30 at 12:02:30 UTC,
workflow version 6. Actual technical search returned the retained synthetic
SOP-OPTICAL-DEMO with pages 1–2. Hosted ingestion recognized the existing staged job;
financial invoice and sales comparison regressions completed successfully.
Chrome login as the initial administrator and cited search also passed. The scripted
publication probe uses an operator-admitted identity and is not a browser login test.

Current local verification: 93 backend tests, 86 hosted contract tests, ten
Playwright UI tests, three frontend unit tests, Ruff, mypy (24 source files),
frontend ESLint and production build passed. The repository checker passed with
72 Markdown files and 26 ADRs; `git diff --check` passed.

Replacement acceptance passed against workflow version 6: native rejection denied
publication, native approval activated the exact new version, old chunks became
ineligible and old-source download was denied. The hosted specialist subsequently
cited the new version. Identical PDF/profile staging was reused and revalidated;
no additional OCR or document embedding call was needed. Several native invoke
attempts returned HTTP 503 before a successful attempt; this is not an availability
or resilience guarantee. No bypass of Engine approval was used.

The local application was restarted on port 53185 with both knowledge and journey
flags enabled. A real HTTP administrator login confirmed all three capabilities
(journey, voice and knowledge) and listed the replacement version. Audio listening
was not repeated in this phase. The Phase 4 source was subsequently committed and pushed by the user as `1a52afc`; the specifically recorded Atlas
resources and Engine deployment are remote. The assistant performed no Git writes. See [publication status](../runbooks/REPOSITORY_SETUP.md) for verification.

## Limits

This proves a bounded synthetic workflow, not corpus ranking quality, production
capacity or OCR fidelity for arbitrary documents. See the runbook for PDF, scope,
queue, retention and retry limits. Later quality work is tracked separately in EVAL-001.
