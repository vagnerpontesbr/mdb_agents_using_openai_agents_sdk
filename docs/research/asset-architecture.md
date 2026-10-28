# Research 3 — asset architecture, Voyage, ingestion and user experience

Research date: October 28, 2026. Planning only: no packages installed, paid inference called, compatibility tests run or deployment performed. The official pages below were opened and read through Chrome after shell DNS failed. Proposed architecture is distinguished from vendor capabilities.

## Verified capabilities

| Topic | Official evidence and consequence |
|---|---|
| Current Python | [Python Downloads](https://www.python.org/downloads/) displays **3.15.2**, released October 25, 2026, as the latest version. Pin this patch at implementation, subject to dependency compatibility verification. |
| Contextual Voyage | [Contextualized Chunk Embeddings](https://docs.voyageai.com/docs/contextualized-chunk-embeddings) documents **voyage-context-4** with backend auto-chunking. |
| Auto-chunking | `Client.contextualized_embed(inputs=List[str], model="voyage-context-4", input_type="document", enable_auto_chunking=True)`. Server default `chunk_size=512`; default `chunk_overlap=0`. Do not combine with `chunk_fn`. Python returns `results[].chunk_texts` in embedding order; REST returns per-item `text`, and its example includes `chunker_version`. |
| Contextual limits | Model table gives 32K per-chunk window and 120K total with auto-chunking; its specific note limits total to 32K without auto-chunking. Up to 1,000 inputs and 16K chunks per request. A general section repeats 120K without separating modes: use the specific conservative limit and verify contracts. |
| Contextual queries | Same method/model with `input_type="query"`, without auto-chunking. Flat `List[str]` is valid for queries. |
| General Voyage | [Text Embeddings](https://docs.voyageai.com/docs/embeddings) lists **voyage-4** and **voyage-4-lite**, 32K context, dimensions 256/512/1024 (default)/2048. It explicitly declares compatibility across the general 4 series. API: `Client.embed()`, `input_type=query/document`. |
| Matryoshka | [Flexible Dimensions](https://docs.voyageai.com/docs/flexible-dimensions-and-quantization) documents 2048-vector prefixes of 1024/512/256. Its truncation example **renormalizes L2**. Flexible dimensions do not imply arbitrary cross-model compatibility. |
| Reranking | [Rerankers](https://docs.voyageai.com/docs/reranker) recommends **rerank-3** for quality and **rerank-3-lite** for latency, both 32K context. `Client.rerank(query, documents, model, top_k)` returns indices and relevance scores. Limits: 1,000 documents, query up to 8K, weighted total up to 600K tokens. Scores are not universal probabilities. |
| Docling | [Official overview](https://docling-project.github.io/docling/) confirms PDF layout, reading order, tables, OCR, Markdown export and lossless JSON. Started at IBM Research; now an LF AI & Data project. [Installation](https://docling-project.github.io/docling/getting_started/installation/) shows v2.143.1 and `uv add docling`. |
| Python + Docling | Installation page does not prove Python 3.15.2 compatibility for all transitive dependencies. OCR/PyTorch vary by platform; Nemotron extra specifically requires Linux x86_64/Python 3.12/CUDA 13. Exclude that extra from the default. Lock resolution, installation and PDF conversion on target platforms remain mandatory gates. |

## Model allocation and MongoDB automatic embedding

The user's latest requirement prefers **MongoDB Auto Embedding whenever supported**. Validate the official MongoDB capability matrix before implementing any manual embedding path: supported models, contextual/document modes, server-side auto-chunking, dimensions, query-time embedding, indexing, updates, tenancy and regional availability. MongoDB research owns this verification. Do not assume automatic embedding is incompatible with contextual models or Matryoshka merely because those features need investigation.

Logical model allocation remains independent of execution provider:

- Technical KB documents **and queries**: `voyage-context-4`, initially 1024 dimensions, native Voyage auto-chunking. No second Docling/LangChain chunker. The documented 512-token/zero-overlap defaults are a measurable starting point, not adaptive optimization of chunk size.
- Durable memory and offers/catalog: `voyage-4`, subject to Agent Engine memory integration. `voyage-4-lite` query embeddings can target the general 4 space because compatibility is documented, with retrieval evaluation required.
- Semantic cache: `voyage-4-lite` on both sides and a separate collection/measurement profile.
- Technical reranking: `rerank-3`; optional `rerank-3-lite` latency profile after evaluation.
- The general 4-series compatibility statement must not automatically be extended to `voyage-context-4`; separate contextual/general spaces until specific evidence and tests establish compatibility.

For each workflow, record `embedding_execution=auto|direct`, model, dimensions, supported contract and rationale. Prefer native automatic embedding where it preserves requirements. Use direct Voyage only for documented capability gaps; if a gap is unresolved, keep it an implementation gate. Avoid duplicate embedding or duplicate billing by clearly assigning ownership of each vector field.

## Concrete Matryoshka design

Embedding registry records model, dimension, dtype, normalization, pipeline version and semantic space. MongoDB vector indexes have fixed dimensions matched by queries. Deliver 1024-dimensional baseline first, then a reproducible comparison against normalized 256-prefix vectors, reporting Recall@k, nDCG, latency and index size. An optional profile uses 256-dimensional ANN candidates, exact 1024 cosine rescoring of those candidates, native lexical fusion under a validated MongoDB contract, and final Voyage cross-encoder reranking. Rescoring cannot recover candidates lost at the first stage. Storing two vectors may increase storage; measure total cost before claiming savings. Keep quantization separate from dimensionality reduction in the first implementation.

## Proposed ingestion pipeline

1. An authorized operator supplies PDF and metadata. The technical specialist's ingestion tool schedules a job and returns `job_id`; a normal customer's upload cannot publish trusted knowledge. Backend authorization is mandatory.
2. Validate MIME/size, tenant, source, checksum and idempotency key. Store the original by reference and its document record. The model cannot supply arbitrary filesystem paths or unrestricted URLs.
3. A worker runs Docling, enabling OCR when required, and saves structured JSON plus canonical Markdown/text with tables, headings and page provenance. Specify OCR languages and machine requirements.
4. Construct canonical-text interval mappings to Docling items/pages. Feed complete documents to the supported contextual auto-chunking path. Over-limit documents require explicit section-level partition manifests; record reduced context across partitions rather than pretending unlimited support.
5. Persist **Voyage-returned chunk text** and its corresponding embedding/order, or equivalent documented automatic-embedding output. The consulted Voyage docs do not promise source offsets: align `chunk_texts` to canonical text, handling repeated occurrences, normalization and overlap, and validate using fixtures. Ambiguous alignment must cite document/section and mark the page unknown, never invent page numbers.
6. Minimum metadata: tenant, document_id, version_id, checksum, source_uri, title, procedure, product/network/device, language, effective_from/to, ACL, chunk_index, verified page_refs, parser/version, model/dimension and exposed chunker version. Use immutable versions and an active-version publication pointer.
7. Job lifecycle: queued/processing/ready/failed; bounded retries, leases and idempotent resume. Publish only after complete chunks and ready indexes. New KB publication increments the cache namespace.

Docling parses; Voyage auto-chunking defines retrieval chunks. OCR must not block the API event loop or keep a chat request open indefinitely. The OpenAI research did not establish Hosted File Search as an exporter for this Voyage/MongoDB pipeline.

## Retrieval and semantic cache

Proposed technical retrieval: authorization plus tenant/ACL/effective-date filters in **both** branches → MongoDB Search lexical branch and contextual vector branch → native `$rankFusion` → distinct candidates and metadata → Voyage reranker → evidence with citations. Candidate counts and top-k are experimental configuration calibrated against telecom questions. Unsupported MongoDB stages must produce a capability diagnostic rather than silently replace native fusion with Python.

Cache eligibility follows authentication and a safe request-type decision. Prefer cached evidence or stable informational answers. Key/filter scope includes tenant, access scope, language, domain, KB/policy/prompt/model versions and relevant context. Include TTL, publication invalidation, hit telemetry and evidence provenance. Exclude personalized balances/invoices, plan changes, action execution, dynamic offer eligibility, live incidents and anything requiring current state. Hits never bypass authorization, confirmation or business tools. Evaluate false hits using hard pairs differing in negation, device, product, region or version.

## Application and deliverable structure

React + TypeScript; propose MongoDB LeafyGreen components and official design tokens, with package/license/React compatibility checked before locking. **Everything is English**, following the final user correction: navigation, user-facing interface, code, architecture/research, implementation plan, demo text/voice conversations and telecom sample procedures.

Agent runtime is shared by text and required voice channels. Browser UI includes microphone permission, recording/stop controls, audio playback, editable/visible transcript, interruption/cancellation and text fallback. Reuse authenticated customer/session identity across channels; never identify a customer solely by voice or caller ID. Browser voice is the initial runnable channel; a telecom voice adapter contract isolates telephony transports and provider-specific webhooks/media. Parent research validates OpenAI `agents.voice` with `VoicePipeline` and `SingleAgentVoiceWorkflow` for STT → same supervisor → TTS. Include latency, timeout, turn-taking and failed-transcription behavior in tests. Voice is a first-release requirement, not a future-only item.

Operator views cover document ingestion status and memory review. A separate builder view shows agent events, retrieval results, cache decisions and metrics without exposing hidden model reasoning. Customer-facing flows should not be cluttered with implementation detail.

Target Python 3.15.2 with uv for interpreter/dependencies/build; typed ASGI API; independent frontend. Build a thin reusable framework of contracts/adapters rather than replacing the Agents SDK loop or adding LangGraph/mem0 as a second runtime. Suggested layout: `packages/agent_framework`, `apps/api`, `apps/worker`, `apps/web`, `examples/telecom`, `infra`, `tests`, `evals`, `docs/adr`, `scripts`. Include `pyproject.toml`, `.python-version`, `uv.lock`, `.env.example`, JS lockfile, diagnostics/setup/seed/dev/build/test commands and reproducible containers. If Docling cannot run on 3.15, explicitly propose an isolated worker on a verified version; no silent downgrade.

Synthetic customers, accounts, plans, coverage and incidents. Example procedures: ONT LOS, Wi-Fi versus access-network slowness, regional outage, APN/mobile data, eSIM and N2 escalation. Finance explains invoices; sales checks eligibility and recommends offers; mutations are simulated with idempotency and explicit application confirmation. Document replacement boundaries for real CRM/BSS/OSS connectors.

## Tests and acceptance criteria

- Installation/build smoke on target Python; SDK/Voyage/MongoDB imports; digital and scanned PDF conversion; frontend build; browser voice round-trip using the shared supervisor.
- Live contracts for automatic embedding where selected, contextual auto-chunking text/vector counts and dimensions, page mapping, idempotency/retries and version publication. Mocks alone do not establish provider compatibility.
- Target MongoDB integration verifies indexes, filtering of both branches and `$rankFusion`; zero tenant/ACL leakage in adversarial tests.
- Evals cover supervisor/specialist routing, grounding/citations, abstention/escalation, accurate memory versus inference, false cache hits, and actions never served by cache.
- Matryoshka and rerank comparisons report quality, p50/p95, token use and cost. Numeric targets require the evaluation dataset and budget, not invented guarantees.
- Guided demo: returning customer recalls consented preference; voice technical issue retrieves cited procedure; equivalent safe question shows cache hit; personalized offer checks eligibility; new document invalidates old results.

## Remaining implementation gates

Python 3.15.2 dependency/platform compatibility; exact Voyage SDK version supporting auto-chunking; chunk-to-page alignment; account/regional model availability; MongoDB Auto Embedding capability matrix; LeafyGreen/React compatibility; MongoDB 9/Agent Engine details from research 2; telephony provider and deployment target; production traffic/SLO/cost targets. A browser voice demo can proceed with a transport abstraction while telephony provider selection remains open.
