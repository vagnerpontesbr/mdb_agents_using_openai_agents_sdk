# COMP-001-PDF: CPU extraction with page provenance

- Status: Done for the bounded synthetic conversion proof; parent COMP-001 remains in progress
- Owner: Repository maintainer
- Dependencies: Authorized Python 3.14 CPU experiment, Docling, Poppler and Tesseract
- Relevant ADRs: [ADR-0002](../adr/0002-service-boundaries.md), [ADR-0015](../adr/0015-voyage-http-python315.md)

## Scope

Prove actual Docling CPU conversion of a two-page textual PDF and a two-page image-only PDF, with expected text attached to the correct source pages. Preserve Python 3.15 for the agent runtime. Do not scaffold the application or claim complete ingestion.

## Acceptance criteria

- The scanned PDF has no embedded text before OCR.
- Both conversions report success and recover the known instruction on each page with matching, unambiguous page provenance.
- Execution explicitly selects CPU and bounds pages, file size and process duration.
- Negative controls reject missing text, swapped/missing/ambiguous page provenance and incomplete page sets.

## Validation plan

Generate synthetic fixtures, render and inspect them, run the real pinned Docling conversion and the deterministic evidence tests. No customer documents or cloud inference are needed. Docling may download model weights.

## Evidence and handoff

All bounded acceptance criteria passed on 2026-10-28. See the authoritative [Phase 0 checkpoint](../compatibility/PHASE_0.md#synthetic-textualscanned-pdf-checkpoint) for exact versions, commands and limitations. Files are locally authored, not committed or published. Parent compatibility still requires locks/builds and the other provider gates; this is not a completed phase checkpoint.
