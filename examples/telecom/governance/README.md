# Demonstration: excellent RAG scores, obsolete business advice

Status: authored synthetic source fixtures and evaluation specification. PDFs, ingestion, grader execution, and measured results are future implementation work. These Markdown documents will be rendered into PDF with matching metadata sidecars, then ingested through the actual Docling/Voyage pipeline. Generate original-file checksums and server ingestion times at execution; the frontmatter dates are fixed-clock demonstration data, not production timestamps.

## Scenario

Use `as_of=2026-10-28T12:00:00Z` and a synthetic customer with Fictional FiberBox X1 firmware 2.x. Question: **“How should I resolve E17 on my FiberBox X1?”** Firmware is supplied by the authenticated service record.

- [Obsolete source](legacy-ont-procedure.md): recently uploaded, expired and overdue for review, with an active replacement. Risk = 30 expiry + 15 overdue review + 25 replacement + 5 impact + 5 change rate = **80/100, critical**. Ownership and provenance are assumed verified in this synthetic fixture.
- [Current source](current-ont-procedure.md): applicable replacement, valid and reviewed at the fixed clock. Risk = 5 impact + 5 change rate = **10/100, low**; still subject to normal approval and applicability checks.

Maintain an independent SME-approved expected outcome: **check provisioning incidents; do not reset the legacy profile; link/open a provisioning ticket.** In this fixture the simulated reset fails the business acceptance test for firmware 2.x. This is a fictional rule, not advice about real equipment.

## Three runs

1. **Isolated negative control:** ingest only v1 in an explicitly separate evaluation database. Disable governance only inside that negative-control harness. Evaluate against a stale gold answer: “perform the legacy profile reset.” The generated answer can be relevant, faithfully sourced, correctly cited, and operationally wrong.
2. **Governed, no replacement available:** ingest v1 normally. Quarantine/exclude it; the assistant must abstain and escalate. Coverage decreases honestly rather than hiding missing valid knowledge.
3. **Governed, replacement available:** ingest both versions with registered lineage. Retrieve v2 for firmware 2.x, exclude v1, and produce the current expected outcome. Seed an old cached answer too; demonstrate its rejection despite a high semantic match.

The negative-control switch must not exist in ordinary customer request parameters. Test tenant isolation independently; this experiment is about stale content, not bypassing authorization.

## Illustrative scorecard — not measured results

For a controlled one-question/top-1 negative control with v1 marked relevant, Precision@1, Recall@1, MRR, and nDCG@1 can all equal 1.0. Faithfulness, citation correctness, answer relevance, and correctness **against the stale gold** can also appear perfect. Those are expected educational values contingent on the answer and grader, not guaranteed outputs. A one-item set provides no statistical quality claim.

| Axis | Negative-control illustration | Governed acceptance target |
|---|---|---|
| Retrieval against stale labels | All listed retrieval metrics 1.0 | Use time-valid, applicability-aware labels instead |
| Faithfulness/citation | 1.0 to obsolete v1 | Faithful citations to eligible v2, or no answer |
| Correctness against stale reference | 1.0 | Do not use as current-business truth |
| Current business correctness | 0.0 for legacy reset | Correct provisioning outcome, or appropriate escalation |
| Stale-source exposure | 1/1 answer | 0 answers using expired/superseded sources |
| Document risk | 80, critical | v1 excluded regardless of retrieval rank |

Report grader failures separately from task failures. Show actual values after execution, source dates/owner, score breakdown, policy decision, retrieved versions, and simulated business outcome side by side. Add paraphrases, firmware changes, missing metadata, expiry boundaries, owner changes, and cache races before drawing broader conclusions.
