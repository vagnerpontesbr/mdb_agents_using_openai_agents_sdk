# Multilingual source review packet

These three one-page synthetic procedures were prepared as drafts for owner review.
The requester authorized this exact publication packet and its bounded provider calls
with "sim aprovo" on 2026-11-01. Consult the
[execution evidence](../../../../compatibility/lang2c-publication-evidence.json)
for actual publication status: all three published and their direct retrieval checks
passed in 124.81 seconds with nine provider calls. The immutable proposal retains its
original status.
The source text and semantic acceptance phrases are in [optical-v1.json](optical-v1.json).
Portuguese and Spanish are declared translations of the English original. The
information owner must review content and exact metadata in native Engine approval.

- [English PDF](../../../../output/pdf/lang2c-optical-en.pdf)
- [Portuguese PDF](../../../../output/pdf/lang2c-optical-pt.pdf)
- [Spanish PDF](../../../../output/pdf/lang2c-optical-es.pdf)
- [Immutable byte checksums](../../../../output/pdf/lang2c-manifest.json)
- [Publication proposal](../../../../compatibility/lang2c-publication-proposal.json)
- [Local extraction evidence](../../../../compatibility/lang2c-source-evidence.json)

Reproduce the files without accessing Atlas or any model provider:

```sh
uv run --frozen --script scripts/prepare_multilingual_pdfs.py
```

The script has an isolated uv lock; it does not add ReportLab to the application.
Use Docling from the existing frozen ingestion project to extract each file:

```sh
uv run --project compatibility/ingestion-runtime --frozen python \
  scripts/extract_knowledge_pdf.py output/pdf/lang2c-optical-pt.pdf \
  --output /tmp/lang2c-reviewed-pt.json --allow-model-downloads
```

The output path must not exist. Repeat for en/es. The flag permits local parser
model downloads, not remote embedding requests. Scanned PDF/OCR is not part of this
packet. All three files passed Docling 2.143.1 with one page, unchanged steps and
negations, matching source hashes and enough headroom for hosted citations. Poppler
renders were visually inspected for legibility, accent glyphs and clipping.

## Proposed bounded publication

The proposed IDs are SOP-LANG-OPTICAL-EN, SOP-LANG-OPTICAL-PT and
SOP-LANG-OPTICAL-ES, version 20261101-1. They do not replace existing documents.
Tenant, equipment and reader ACL remain the existing synthetic demo scope. Stop if
any ID already exists; do not silently choose replacements. Source expiry is
2026-12-01 and review is due 2026-11-08. If those dates are stale at execution, prepare
a fresh review packet. Capture the actual owner-review time, not a fabricated past
approval timestamp. Do not update the dates after native approval.

After explicit authorization, use the existing domain upload/worker/review/publish
path: English first, then each translation linked to its exact published original
key. Validate each pending native action against its PDF hash and proposal before
the owner approves it. Runtime-generated job IDs, source-review timestamp and native
action digests are bound by that review; this packet is not an approval receipt.

Maximum: three source embedding requests, three query embeddings and three reranks,
three native publication reviews, one source at a time and 20 elapsed minutes.
No automatic provider retries. Index-visibility polling must be read-only and reuse
the query vector; it must not repeatedly call rerank. One query in each language
must cite the corresponding new document and preserve all four steps, negations and
page identity. Fail on incomplete procedure extraction, missing citations, stale
source or any attempt to answer from a different language. Check wrong tenant/ACL
using the same vector without adding provider calls.

Native review execution is permitted only in agentsdk. No hosted deployment, shared
policy, role, index, validator or memory change is part of this proposal. Publication
adds searchable demo data that existing readers may see. Retain native review and
source history; physical deletion and reversal require a separately reviewed action.
On partial failure, stop and report the exact published/staged IDs rather than rerun
the whole batch or silently remove evidence.

The USD 30 ceiling has not been increased; remaining billed spend is unknown in the
historical evidence. The requester confirmed the proposed budget envelope before execution.
Hosted multilingual chat, replay, cross-language memory and voice remain separate
acceptance gates. This narrow publication exercise cannot close LANG-2c by itself.
