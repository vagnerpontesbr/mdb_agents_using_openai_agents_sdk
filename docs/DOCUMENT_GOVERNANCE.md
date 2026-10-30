# Document governance and risk

Status: authoritative governance contract. Phase 4 implements native owner review,
transactional publication and hosted retrieval; [RAG-001](tasks/RAG-001-KNOWLEDGE.md)
records actual acceptance and remaining checks. [ADR-0026](adr/0026-governed-knowledge-publication.md)
defines the owner and publication boundary. The synthetic quality demonstration
below is not a measured retrieval evaluation. Scheduled reassessment, cached answers
and the full diagnostic UI below remain planned; request-time eligibility is enforced.

## Ownership and metadata

Store governance on an immutable document version, with inherited eligibility metadata on chunks. Preserve the authoritative record and recheck it before answering because search indexes and caches can lag. Dates are UTC instants; source creation is never inferred from upload time.

| Field | Meaning and validation |
|---|---|
| `tenant_id`, `document_id`, `version_id` | Authenticated tenant scope and immutable identities |
| `information_owner` | Accountable business owner ID/team, resolvable to an active owner; distinct from uploader |
| `created_at` | Original document creation date, with provenance; unknown values trigger review |
| `ingested_at` | Server-recorded ingestion time; never used as proof of freshness |
| `effective_from`, `expires_at` | Business validity interval; eligibility is `effective_from <= now < expires_at` |
| `last_reviewed_at`, `review_due_at` | Completed owner review and next required review; overdue at `now >= review_due_at` |
| `reviewed_by`, `approved_by`, `approved_at` | Verified accountable review and publication audit |
| `source_uri`, `source_system`, `checksum` | Origin and integrity, with access-controlled original |
| `classification`, `acl`, `language` | Confidentiality, authorized readers, language |
| `product`, `region`, `firmware_range` | Applicability; unknown compatibility must not be assumed |
| `supersedes`, `superseded_by` | Version lineage; replacement activation retires the old version |
| `status` | `draft`, `in_review`, `approved`, `published`, `quarantined`, `expired`, `superseded`, `revoked` |
| `business_impact`, `change_rate` | Owner-assigned enums with documented rationale |
| `parser_version`, `embedding_profile`, `chunker_version` | Reproducible transformation lineage |
| `risk_score`, `risk_factors`, `risk_policy_version`, `risk_assessed_at` | Reproducible risk result and reasons |

Validate date ordering, required ownership, active approval, ACL completeness, source integrity, and applicable scope before publication. Reviews are append-only events; changing content creates a new version. A metadata-only review cannot silently extend validity without an authorized approval. Curator upload and owner approval are separate permissions.

## Proposed risk score

This deterministic 0–100 score is an explainable prioritization heuristic, **not a probability of error**. Initial weights require calibration with owners and incidents. Each factor is binary; add its weight when true, cap at 100, and store the evidence.

| Factor | Weight |
|---|---:|
| Document expired | 30 |
| Review overdue or review date missing | 15 |
| Active replacement exists or authoritative conflict confirmed | 25 |
| Owner missing, inactive, or unresolved | 10 |
| Provenance, approval, or mandatory metadata unverified | 10 |
| High-impact operational instructions | 5 |
| Rapidly changing subject/product | 5 |

Bands: 0–19 low; 20–39 moderate; 40–69 high; 70–100 critical. Moderate requires an owner review before publication; high/critical are quarantined pending resolution. Low risk still requires all eligibility rules. **Expired, superseded, revoked, unapproved, unauthorized, or out-of-scope content is excluded regardless of score.** Missing validity or applicability fields fail closed for operational procedures. A score never grants access.

Reassess at ingestion, review, publication, replacement, policy change, and scheduled time boundaries. Evaluate current validity at request time even if background reassessment is late. Record `as_of` and policy version to reproduce past decisions.

## Enforcement and lineage

1. Ingest into staging, extract metadata, verify against the source/owner, and calculate risk; LLM-extracted metadata remains unverified until checked.
2. Apply approval and risk policy before publication; quarantine failures with actionable reasons.
3. Apply tenant, ACL, applicability, and validity filters in both hybrid retrieval branches.
4. Batch-revalidate candidate document versions against the authoritative governance store after retrieval and immediately before response release. Refill candidates within a bounded budget or abstain.
5. Cache entries carry source version IDs, governance revision, and earliest source expiry/review boundary. Cache reads recheck eligibility; a cache hit cannot outlive a source's validity. Revoke/replace events invalidate affected results.
6. Trace the answer to source chunks, document versions, risk snapshot, prompt/model, and policy versions. Citation presence alone does not establish authority.
7. Keep historical versions for authorized audit under retention policy; retrieval exclusion is separate from physical deletion. Never expose quarantined content through ordinary customer search.

The curatorial UI shows owner, dates, risk factors, blockers, and replacement links. Builder diagnostics explain excluded sources; customer responses use approved evidence or escalation.

## Evaluation: source quality is a separate axis

Measure retrieval relevance (Precision/Recall@k, MRR, nDCG), context relevance, faithfulness, citation correctness, and answer correctness against a **time-valid independent reference**. Also measure stale-source exposure, applicable-source coverage, policy exclusion recall, false exclusion, risk calibration, and current business outcome correctness. Distinguish these denominators and report sample counts.

LLM judges and reference answers can share the same stale source. A perfect score against that source does not prove real-world accuracy. Independent SME-approved truth includes effective dates and product/firmware scope. Version datasets, annotation provenance, clocks, models, and graders; report confidence/uncertainty and disagreements. Never label a stale-reference score simply “accuracy.”

See the [synthetic demonstration](../examples/telecom/governance/README.md). Its perfect scores are illustrative fixtures, not measured performance or a guarantee that every RAG metric will equal 1.0.
