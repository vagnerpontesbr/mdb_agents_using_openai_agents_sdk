# Phase 0: compatibility evidence and explicit probes

Status: in progress, with remaining Engine/provider gates. Local split dependency locks, frozen installs/builds and synthetic CPU PDF/OCR now pass on macOS ARM64; see the latest checkpoint below. This phase is not complete. The application has not been scaffolded; these are diagnostic environment locks, not application or hosted-runtime acceptance.

## Implemented tooling

- `compatibility/package-metadata.json`: captured official PyPI package metadata, source URLs, version constraints, and download hashes. Metadata is not runtime evidence.
- `compatibility/requirements.in`: pinned candidate for resolver experiments. It is deliberately labeled unapproved; the incompatible Voyage SDK is excluded in favor of official HTTP calls.
- `scripts/check_compatibility.py`: offline metadata/import report; explicitly enabled Atlas ping/version, OpenAI synthetic function-calling, and Voyage contextual embedding/rerank probes. Reports only configuration presence, never secret values or raw exception messages.
- `tests/compatibility`: deterministic tests of evidence semantics, upper-bound detection, credential suppression, missing configuration, and live-call gating.
- `.env.example`: local configuration template. Neither example nor `.env` triggers network calls by itself.

## Run the offline checks

```bash
python3 scripts/check_repository.py
python3 -m unittest discover -s tests/compatibility -v
python3 scripts/check_compatibility.py --output artifacts/compatibility/local.json
```

The diagnostic exit codes are 0 for requested checks passing, 1 for a failure, and 2 for blocked prerequisites. A single successful probe is not phase acceptance. The full offline report intentionally leaves runtime/provider gates blocked until real evidence is recorded. The simple Python-bound evaluator handles only the captured numeric constraints; it refuses unknown syntax rather than replacing uv's full resolver.

## Current dependency finding

| Package | Captured release | Requires-Python | Meaning for 3.15.2 |
|---|---|---|---|
| openai-agents | 0.24.0 | >=3.10 | Direct bound permits it; transitive/install/runtime unverified |
| pymongo | 4.19.0 | >=3.11 | Direct bound permits it; wheels/runtime unverified |
| voyageai | 0.5.0 | >=3.9,<3.15 | Excluded; official HTTP selected |
| docling | 2.143.1 | >=3.10,<4.0 | Direct bound permits it; OCR/model dependencies unverified |
| agent-engine-sdk-memory | 0.11.11 | >=3.11 | Direct bound permits it; service/runtime unverified |

Python.org downloads was fetched again and identified 3.15.2. The installed system interpreter is 3.14.6. Installed uv 0.11.3 reported no 3.15.2 macOS ARM download. A `uv pip compile --python-version 3.15.2` attempt warned that 3.13.12 would be used to build dependencies and then failed on PyPI DNS. No target build, successful resolution, or lockfile resulted. This does not prove every package is incompatible; it establishes that this attempted environment did not validate them.

A current uv 0.13.6 wheel was downloaded from PyPI into temporary storage and verified against its published SHA-256 (`51361029b7cf91185d0092c4b356d110b4ad629e9cb11593f1e006ac72a72ca9`). Its executable recognizes the requested Python artifact, but `uv python install 3.15.2` failed on GitHub DNS in this execution environment. The user's global uv installation was not changed. Updating uv addresses the catalog issue but does not by itself resolve this session's networking or the Voyage package constraint.

The target Python artifact was subsequently downloaded through curl and extracted into temporary storage. `/tmp/telecom-python-manual/python/bin/python3.15` executes Python 3.15.2; all 16 diagnostic tests pass with it. A renewed uv resolution attempt using that interpreter still failed on PyPI DNS. The interpreter blocker is resolved locally; dependency installation remains unverified.

The user selected official Voyage HTTP calls while retaining Python 3.15 and the chosen models ([ADR-0015](../adr/0015-voyage-http-python315.md)). `compatibility/voyage_http.py` implements a diagnostic adapter for contextual document/query embeddings and reranking with response validation, bounded inputs/responses, no redirects or retries, and sanitized errors. Its I/O timeout is not a total wall-clock deadline. General voyage-4/voyage-4-lite calls and the production asynchronous transport remain future implementation work. Official sources: [contextual embeddings](https://docs.voyageai.com/docs/contextualized-chunk-embeddings), [rerank API](https://docs.voyageai.com/reference/reranker-api), and [current reranker models](https://docs.voyageai.com/docs/reranker).

## Configure existing services

The user confirms an Atlas cluster and Agent Engine project already exist. Use those resources; do not create another cluster. If `.env` does not exist:

```bash
cp .env.example .env
```

Fill it in an editor. `ATLAS_CLUSTER_HOST` is the intended SRV hostname without scheme, credentials, or path. `OPENAI_MODEL` must be a model available to the account. Engine fields belong to the existing hosted project. Configure `AGENT_ENGINE_URL=https://agentengine.mongodb.com`; the future SDK adapter maps this application setting to its documented `base_url` argument. Do not paste values into chat or issue reports. Copying the template does not install dependencies or validate permissions.

After a compatible SDK environment has actually been installed, use uv's environment loading:

```bash
uv run --no-project --env-file .env python scripts/check_compatibility.py --probe mongodb --allow-live --output artifacts/compatibility/mongodb.json
uv run --no-project --env-file .env python scripts/check_compatibility.py --probe openai --allow-live --output artifacts/compatibility/openai.json
uv run --no-project --env-file .env python scripts/check_compatibility.py --probe voyage --allow-live --output artifacts/compatibility/voyage.json
```

These commands require the selected interpreter to have the relevant packages. They do not automatically install them. The Atlas probe is sequential/read-only, compares the configured SRV hostname, and runs ping/buildInfo with a short diagnostic deadline. Its one-operation pool is not a production sizing recommendation. It does not prove Search support, roles, or Engine same-cluster attachment.

The OpenAI probe makes a bounded real-model request, disables tracing/retries, and requires actual execution of a synthetic read-only invoice tool. It incurs provider usage. It tests the SDK/model tool contract, not real billing or authorization. No live probe runs without `--allow-live`; no database/index creation or mutation is implemented here.

The Voyage probe makes three billable HTTP calls with synthetic text: contextual document auto-chunking, query embedding, and reranking. It needs only the standard library and a configured Voyage key; it does not install the Python SDK. Contract tests use a fake transport and do not prove live API availability.

## Remaining acceptance gates

1. Local macOS ARM64 split dependency acceptance passed; validate any future application/platform changes independently rather than treating these diagnostic locks as a hosted-runtime proof.
2. HTTP resolves the direct SDK selection conflict; verify the chosen API contract with actual contextual chunks, query vectors, dimensions, and reranking.
3. Verify existing Atlas version, Search/Auto Embedding/native fusion, index readiness, and allowed/denied tenant/service access in designated test namespaces.
4. Verify Engine memory record/context/tenant isolation and attachment to its designated cluster under [ADR-0017](../adr/0017-two-cluster-memory-boundary.md).
5. Prove hosted Engine execution, audit/replay and interrupted-run behavior with OpenAI orchestration, or record an explicit incompatible contract requiring a decision.
6. Parse textual/scanned PDFs and validate source alignment; perform an actual voice round trip with session continuity.

The harness does not pretend to implement the unverified Engine or search APIs. Add probes as their exact pinned contracts and resources become available. Never mark an unexecuted gate passed because configuration fields or SDK classes exist.

## Phase boundary

Stop after the phase acceptance evidence is complete and provide manual commit commands. Wait for the user's commit confirmation before Phase 1. If compatibility remains blocked, report it as blocked and continue only independent Phase 0 work; do not claim a completed phase or generate a fake lockfile.

## Local evidence so far

Sixteen deterministic harness tests passed on Python 3.15.2, including nine Voyage HTTP contract tests. The repository checker passed with 40 Markdown documents and 15 ADRs. The offline report excludes the incompatible Voyage SDK and leaves unexecuted dependency/provider gates blocked. At the initial offline checkpoint, no paid model call, database write, or index creation had occurred. See the subsequent live checkpoint below. These results validate the diagnostic harness, not the target application stack.

## Live checkpoint: 2026-10-28

The user completed local configuration. All required variables are present; secret values are excluded from evidence and logs.

| Check | Observed evidence | Status / limit |
|---|---|---|
| Core Python 3.15.2 environment | uv run installed 44 packages; imports of openai-agents 0.24.0 with voice extra, pymongo 4.19.0, and agent-engine-sdk-memory 0.11.11 passed | Core subset passed; not the full application graph or build |
| Full candidate | uv resolver rejected Docling 2.143.1 → docling-slim[standard] → torch>=2.2.2 because available torch wheels lacked cp315 | Failed on this macOS ARM target; Python 3.14 ingestion-worker exception awaiting user decision |
| OpenAI SDK | Real model selected and executed the synthetic invoice function, returning the expected tool output | Passed; no financial action or real customer data involved |
| Atlas connection | Configured SRV host matched; ping and buildInfo succeeded; server reported 8.0.34 | Connectivity passed; requested MongoDB 9 gate failed; no cluster changes made |
| Voyage HTTP | Document auto-chunk, contextual query, and rerank requests each returned HTTP 403 | Endpoint rejected configured key; provider message distinguishes Voyage keys from MongoDB Atlas keys; origin of key awaiting user clarification |
| Engine SDK | Synthetic STM probe failed with MemoryServerError; a separate read-only context request failed with MemoryConnectionError | Project metadata GET via direct curl returned HTTP 200 with the configured token; memory round trip remains unverified; write persistence is unknown, not asserted absent |

The OpenAI check incurred real provider usage. An Engine synthetic write was attempted with a unique user/session and idempotency key. No index creation or Atlas version change was performed. Raw provider responses and credentials are not committed.

Direct `uv pip compile` still failed DNS in this execution surface, but `uv run --with` reached PyPI and established a concrete resolver result. Direct curl also reached providers. Do not attribute these surface-specific failures to the user's Mac DNS, which resolved the domain successfully.

Reproduce the installed core subset and bounded SDK probes (requires the target interpreter to be available):

```bash
uv run --no-project --python 3.15.2 --env-file .env \
  --with 'openai-agents[voice]==0.24.0' --with pymongo==4.19.0 \
  --with agent-engine-sdk-memory==0.11.11 \
  python scripts/check_compatibility.py --probe openai --allow-live \
  --output artifacts/compatibility/openai.json
```

Change `--probe` and output filename to `mongodb` for read-only version validation or `engine` for the synthetic memory write/read and distinct-user/session check. The Engine probe is not a tenant authorization test and does not prove same-cluster attachment. A process-level deadline should supervise this diagnostic because the SDK owns transport timeouts. Do not run it repeatedly to hide an unresolved server error. The `voyage` probe requires the key to match its official Voyage endpoint.

Do not commit this phase as complete: resolve the user decisions and remaining live gates first. No application lock or full-stack compatibility claim is approved.

## Atlas key correction and CPU ingestion investigation

The user confirmed the model API key was created in Atlas. The appropriate base URL is `https://ai.mongodb.com/v1`, configured as `VOYAGE_BASE_URL` in `.env.example` and locally. The direct HTTP adapter now permits explicit official Voyage, Atlas, and documented US/EU Atlas endpoints; it rejects arbitrary hosts and does not follow redirects. Geography-scoped keys require their matching endpoint. This changes transport routing, not model choices or Auto Embedding preference.

Three direct curl calls to the Atlas endpoint returned HTTP 200. The actual responses were validated using the adapter's contract checks with exact request-body matching: voyage-context-4 produced three auto-chunks at dimension 256, one query embedding, and chunker version 1.0.0; rerank-3 returned two valid ranked results. Safe local evidence is in `artifacts/compatibility/voyage-atlas-http.json`. These checks establish provider HTTP contracts, not RAG quality. The separate Python urllib attempt failed at the transport layer in this execution surface.

CPU-only operation does not imply absence of PyTorch. The official Docling installation guide explicitly describes CPU-only PyTorch distributions. Captured docling-slim 2.143.1 metadata declares torch in both `standard` and `models-local` extras. An actual `uv run` experiment installed `docling-slim[format-pdf]==2.143.1` on Python 3.15.2 without torch, but importing `docling.document_converter.DocumentConverter` failed because its ASR import path imports torch. Therefore the tested slim profile does not provide a working DocumentConverter without torch. No GPU functionality was requested or enabled. A different supported parsing pipeline must demonstrate PDF/OCR/provenance parity before replacing the planned one; no downgrade or reduced ingestion feature set is approved.

Sources:

- [Atlas model API endpoints and clients](https://www.mongodb.com/docs/voyageai/api-and-clients/)
- [Atlas contextual embedding models](https://www.mongodb.com/docs/voyageai/models/contextualized-chunk-embeddings/)
- [Atlas OpenAPI specification](https://www.mongodb.com/docs/api/doc/atlas-embedding-and-reranking-api/)
- [Docling installation and CPU-only PyTorch](https://docling-project.github.io/docling/getting_started/installation/)
- [Pinned docling-slim metadata](https://pypi.org/pypi/docling-slim/2.143.1/json)

After the endpoint change, 18 local deterministic tests pass. Provider integration remains a separate gate from those tests.

## Atlas 9 and authorized CPU experiment

After the user's Atlas upgrade, a new PyMongo ping/buildInfo probe returned **9.0.4** on 2026-10-28. The version gate now passes; previous 8.0.34 observations above are historical. No MongoDB/Atlas MCP tools were exposed in this session, so this evidence is explicitly a direct-driver check, not an MCP check. Search/index/isolation capabilities still need their own tests.

The user authorized testing Docling/PyTorch on Python 3.14 in CPU mode, while preserving Python 3.15 for the agent runtime. This authorizes the compatibility experiment; final worker packaging and full PDF/OCR acceptance remain separate gates.

The authorized Python 3.14 CPU experiment **passed**: uv installed 103 packages; Python 3.14.6 imported Docling 2.143.1's DocumentConverter and PyTorch 2.14.1. A tensor operation explicitly on CPU returned the expected result. PdfPipelineOptions accepted AcceleratorDevice.CPU with two threads. No GPU operation or PDF conversion was executed, and no model download was initiated by this smoke check. The result validates the dependency boundary only; full textual/scanned PDF conversion and provenance remain unverified.

Reproduce the CPU experiment independently of the Python 3.15 agent environment:

```bash
uv run --no-project --python 3.14.6 \
  --with-requirements compatibility/ingestion-cpu-requirements.in \
  python scripts/check_docling_cpu.py \
  --output artifacts/compatibility/docling-cpu.json
```

The candidate file is not a lock. Keep the failed combined Python 3.15 candidate as historical compatibility evidence until final manifests separate the ingestion worker. Do not interpret the successful CPU import as a full ingestion acceptance test.

## MongoDB MCP checkpoint

On 2026-10-28, the MongoDB MCP `connect` tool successfully established a connection using the project's configured URI. A read-only MCP `find` on `local.startup_log`, sorted by `startTime` descending with a one-document limit, returned `buildinfo.version = 9.0.4` and startup time `2026-10-28T13:38:03.000Z`. This is separate MCP evidence, in addition to the earlier direct PyMongo check. No application data or index was changed. It does not establish Search/Auto Embedding capability, tenant authorization, or Engine attachment.

## Synthetic textual/scanned PDF checkpoint

On 2026-10-28, actual CPU conversions passed on Python 3.14.6 with Docling 2.143.1, PyTorch 2.14.1 and Tesseract 5.5.2. Both a two-page textual PDF and an image-only version returned successful conversion status. The expected instruction on each page was recovered with an unambiguous matching Docling `page_no`. The scanned fixture was independently checked with pypdf to contain no embedded text. Rendered scanned pages were visually inspected and were legible, with no clipping or overlap.

This supersedes the earlier import-only PDF status for this small synthetic case. It does not prove table accuracy, noisy/rotated scans, arbitrary PDFs, Voyage chunk-to-page alignment, publication governance, or production worker packaging. Table extraction was enabled, but these fixtures do not contain tables. CPU selection was explicit; cloud inference was not enabled. Model weights may be downloaded by Docling.

Reproduce from the project root (Poppler `pdftoppm` and Tesseract with English data must be installed):

```bash
uv run --no-project --python 3.14.6 \
  --with reportlab==5.1.0 --with pypdf==6.21.3 --with pillow==12.2.0 \
  python scripts/create_pdf_probe_fixtures.py
uv run --no-project --python 3.14.6 \
  --with-requirements compatibility/ingestion-cpu-requirements.in \
  python scripts/check_docling_pdf.py --allow-model-downloads
```

The conversion child process has a 240-second deadline per fixture, a two-page limit and a 5 MB input limit. This is a diagnostic boundary, not a production resource sandbox. Generated fixtures, PNGs and `docling-pdf.json` remain under ignored `artifacts/compatibility/`. The candidate dependencies are not a frozen lock. APIs were checked against the installed pinned package and the [official pinned OCR example](https://github.com/docling-project/docling/blob/v2.143.1/docs/examples/full_page_ocr.py).

Four new deterministic tests reject missing text, wrong pages, missing/ambiguous provenance and incomplete page sets. Together with the existing harness, 22 tests pass on both Python 3.14.6 and Python 3.15.2. These tests validate evidence logic separately from the real conversion result. The repository checker passed with 41 Markdown files and 15 ADRs, and `git diff --check` passed. See [COMP-001 PDF task](../tasks/COMP-001-PDF.md).

## Prepared search checkpoint

Before execution, MCP discovery found only `admin`, `config`, and `local` databases, and no collections in the proposed `telecom_eval_knowledge` namespace. The [search probe plan](../../compatibility/search-probe-plan.json) defines four synthetic records, two indexes and six queries at most. The user confirmed M10 with tier and storage auto-scaling enabled; this prerequisite is user-confirmed, not MCP-inspected. The user subsequently approved index creation. See the live checkpoint below for completed execution. The available MCP tools cannot inspect Atlas tier settings.

Official [index documentation](https://www.mongodb.com/docs/vector-search/indexes/vector-search-type/) confirms an optional 512-dimensional Auto Embedding configuration. The MCP index tool's exposed schema omits that optional field, so it must not be silently replaced with a model default. The preparation also identified different query representations: MCP exposes a `query.text` object, while the skill example uses a plain `query` string. The live checkpoint records the tested form.

## Live search checkpoint

On 2026-10-28, after explicit approval, four synthetic documents were inserted through MCP into `telecom_eval_knowledge.phase0_search_probe` on the existing Atlas cluster. MCP created `phase0_lexical`; PyMongo 4.19.0 on Python 3.15.2 created `phase0_autoembed` with `voyage-4-lite` and exactly 512 dimensions using `SearchIndexModel`. The driver contract was verified against the installed version and [official versioned source](https://github.com/mongodb/mongo-python-driver/blob/4.19.0/pymongo/operations.py). A single sequential diagnostic connection was used, with one application connection and a 30-second operation deadline; monitoring connections are additional. This is not production pool sizing.

Both index definitions were then verified through MCP as `READY` and `queryable: true`. Five live MCP aggregation calls ran successfully:

| Query | Expected and observed result |
|---|---|
| Lexical control without filters | All four synthetic IDs |
| Lexical with tenant/ACL/published prefilters | Only `phase0_allowed` |
| Auto Embedding control without filters | All four synthetic IDs |
| Auto Embedding with tenant/ACL/published prefilters | Only `phase0_allowed` |
| Native `$rankFusion` combining the filtered branches | Only `phase0_allowed` |

Auto Embedding accepted `query: {"text": "optical cable"}` through MCP. Plain-string query syntax was not tested. The controls establish that excluded documents were actually indexed, avoiding an empty-index false pass. Tenant, ACL and publication filters were inside each search branch, before fusion. The test uses static synthetic policy fields; it does not implement expiry/review/replacement checks or authoritative revalidation during concurrent changes.

The [exact pipelines](../../compatibility/search-probe-pipelines.json), [safe evidence](../../compatibility/search-probe-evidence.json) and [task record](../tasks/COMP-004-SEARCH.md) are locally authored. The four records and two indexes remain on Atlas for inspection. Indexing and query embedding used the real provider; no cost or quality metric was measured. This proves the bounded model/index/filter/fusion contract, not database-role isolation, production authorization, RAG quality, contextual-vector indexes, voyage-4 catalog configuration, or Engine compatibility. Phase 0 remains incomplete.

## Locked dependency checkpoint

On 2026-10-28, the user-requested dependency validation passed for two isolated projects on macOS ARM64 using uv 0.11.3:

| Environment | Interpreter | Direct runtime dependencies | Locked package count |
|---|---|---|---|
| Agent diagnostic | Python 3.15.2 | openai-agents[voice] 0.24.0, pymongo 4.19.0, agent-engine-sdk-memory 0.11.11 | 46 |
| CPU ingestion diagnostic | Python 3.14.6 | docling 2.143.1, torch 2.14.1 | 105 |

Counts include each local diagnostic package and uv_build 0.11.3, the pinned build backend. Both projects have a `pyproject.toml` and generated `uv.lock`. Fresh `.venv` installations using `uv sync --frozen --group build` passed. Offline `uv lock --check` and `uv pip check` passed; every installed distribution/version exactly matched its lock. SDK/voice/memory imports and a CPU tensor check passed. Wheel and sdist builds used `uv build --no-build-isolation` against the frozen backend, and both built wheels passed direct import checks. No application build is claimed.

Synthetic textual/scanned PDF conversion with expected page provenance passed again in the locked ingestion environment. The 22 deterministic harness tests passed in the locked agent environment. Ruff 0.14.0 passed on the two new diagnostic packages. The [dependency evidence](../../compatibility/dependency-evidence.json) records lock/build hashes and observations; the [dependency task](../tasks/COMP-001-DEPENDENCIES.md) provides exact reproduction commands. [ADR-0016](../adr/0016-split-compatibility-environments.md) records the scope and tradeoffs.

The historical combined Python 3.15 candidate remains incompatible with the tested Docling/PyTorch wheels. The split resolves this local dependency gate without downgrading the agent runtime. These exact-patch locks intentionally target only macOS ARM64. Linux/hosted Engine, application manifests, browser/system audio libraries, Poppler/Tesseract and model-weight reproducibility need separate validation. No provider request or database write was made for this dependency task. Changes remain local and uncommitted; Phase 0 is not complete.

## Engine authentication checkpoint

On 2026-10-28, `agentengine memory status` returned `state: ready` for the CLI context whose project ID was confirmed to match local configuration. A read-only `Memory.build_context` request using the frozen SDK environment returned `MemoryAuthError`, HTTP 401, code `INVALID_TOKEN`. No new memory turn was submitted. Runtime readiness does not prove application authentication, memory isolation or same-cluster attachment.

The [official standalone memory guide](https://www.mongodb.com/docs/agentengine/add-features/memory-only/) documents one-hour service-account tokens. Expiration is a possible cause; this response alone does not establish why the token is invalid. The local env contains a token but no client credentials for autonomous renewal. At the user's request, [refresh_engine_token.py](../../scripts/refresh_engine_token.py) prompts for client ID and secret in an interactive Terminal, exchanges them only at the official OAuth endpoint, and atomically updates only `AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN` in `.env` with private file permissions. It rejects redirects, does not print secrets, and does not persist client credentials. Its OAuth exchange has not yet been run; local update safety tests and lint passed.

Run from the repository root:

```bash
python3 scripts/refresh_engine_token.py
```

After successful renewal, the read-only preflight is available without submitting another turn:

```bash
uv run --project compatibility/agent-runtime --frozen --no-sync --env-file .env \
  python scripts/check_compatibility.py --probe engine-context --allow-live \
  --output artifacts/compatibility/engine-context.json
```

Then run the existing synthetic memory round trip only if authentication succeeds. The SDK owns timeout/retry behavior; supervise live diagnostics with a process deadline. The harness now has 27 passing deterministic tests. Token renewal and the subsequent memory proof remain pending; Phase 0 is incomplete.

## Engine checkpoint after token renewal

After the user ran the hidden-prompt token refresh on 2026-10-28, the frozen SDK's read-only context probe returned HTTP 500 (`MemoryServerError`) instead of 401. A direct request using the same documented context body also returned 500 with `Failed to build context`. No new turn was written and no repeat write was attempted to mask the failure.

Read-only authenticated metadata requests returned HTTP 200 for the project, memory runtime, secret runtime readiness and memory configuration. Both the CLI and API reported memory `state: ready`; secret runtime readiness was true. Configuration generation and received generation were both 9. This establishes that the renewed token is accepted for these metadata endpoints; functional memory remains unverified.

The existing memory configuration uses `voyage-4-large` at 1024 dimensions, `short_term.embed_on_write: false`, and an Anthropic extraction provider. The requested memory-model target remains `voyage-4`; the existing server configuration was not changed. The runtime reports a configured image tag v0.11.10 and resolved image tag v0.11.11; this observation alone does not prove a version mismatch caused the failure.

Secret metadata lists `MONGODB_URI`, `VOYAGE_API_KEY`, `LLM_API_KEY`, and the configured Anthropic secret name. Presence/readiness does not verify their values, endpoints, database grants or target cluster. MCP database discovery on the intended Atlas cluster did not show an identifiable Engine memory database, but this is not sufficient to prove that the Engine uses a different cluster or cannot access this one. Same-cluster attachment remains open.

Next diagnostic: verify the Engine's stored `MONGODB_URI` targets the intended Atlas cluster, Engine egress access and required database grants, then obtain server-side diagnostics for the context failure if those are correct. Do not overwrite existing project secrets, switch models/re-embed, restart/upgrade the runtime, or create competing memory collections merely to bypass the unexplained 500. The official standalone guide notes that internal memory-runtime logs are not exposed through the CLI. No further token rotation is indicated by the current evidence.

## Engine-to-Atlas diagnostic continuation

The user confirmed the target hostname on 2026-10-28. A read-only cluster listing through the Engine's delegated Atlas API identified `OpenAI-SDK` (M10) with an SRV host matching both that target and local configuration. The Atlas project contains four existing clusters; no additional cluster was created, selected for application storage, or modified.

`GET /api/v1/projects/{id}/atlas-link` returned a successful stored egress synchronization at `2026-10-28T14:45:14Z`, with `cluster_count: 2` and `clusters_differ: false`. The separate current cluster listing returned four clusters. This discrepancy merits investigation but does not prove that the target cluster is blocked. The public status response omits the actual topology snapshot, and the stored Engine `MONGODB_URI` secret cannot be read through the available metadata API.

The Atlas CLI `accessLists list` attempt returned `unauthorized`. The Engine CLI's Atlas status command required a workspace despite memory being project-scoped, so no workspace was created merely to work around that diagnostic limitation. The user was asked to run `atlas auth login` locally to enable read-only network/database-user inspection; no credential needs to be pasted into chat.

To distinguish an empty-session context failure from a failure of the complete flow, one bounded synthetic STM round-trip attempt was executed with the renewed token and a 120-second process deadline. It returned HTTP 500 (`MemoryServerError`) at `2026-10-28T14:56:28Z`. The existing report does not identify which call failed, so persistence is **unknown**, not asserted absent or successful. No additional write retry was made. This attempted diagnostic does not establish memory continuity or isolation.

The remaining next step is authenticated Atlas inspection, followed by verification of the Engine's stored connection target if network/roles do not explain the failure. No secret overwrite, runtime restart/upgrade, model change, or managed-memory database mutation was performed during this continuation.

## Authenticated Atlas inspection and failure-stage evidence

The user confirmed Atlas CLI login was already complete. On this continuation, `atlas auth whoami` returned unauthenticated inside the execution sandbox but succeeded outside it using the existing login. This supersedes the earlier request to log in again; the authentication difference is execution-context dependent.

Read-only `atlas accessLists list --output json`, `atlas dbusers list --output json`, and `atlas clusters list --output json` succeeded in the authenticated context. The selected project contains the intended OpenAI-SDK cluster, running MongoDB 9.0.4 on M10 with compute and disk auto-scaling enabled. Five network entries include two /32 entries labeled MongoDB Agent Platform. Labels do not prove the runtime's current source IPs or actual connectivity.

The user confirmed that the Engine's stored connection uses database user `agentsdk`. Atlas lists that identity with cluster scope OpenAI-SDK and roles `readWriteAnyDatabase`, `dbAdminAnyDatabase`, and `clusterMonitor`. These broad diagnostic roles do not meet the application's eventual service/database least-privilege requirement. A separate workspace-prefixed Engine identity is restricted to another cluster, but it is not the user-confirmed identity for this memory configuration and therefore does not explain this failure. No roles, secrets, network rules or cluster settings were changed. Password correctness, the exact stored connection string, runtime egress reachability and functional memory remain unverified.

The STM probe now reports the failed stage and whether its write was not attempted, has an unknown outcome, or was acknowledged by the SDK. A failed write remains unknown because the server may have persisted it before returning an error. Acknowledgement does not prove later retrieval or durable extraction. The report retains a synthetic run ID without exposing exception messages or credentials. This evidence applies to future executions; it cannot identify the stage of historical HTTP 500 failures. No write retry was made during this change. See [COMP-002 diagnostics](../tasks/COMP-002-DIAGNOSTICS.md).

## Dedicated workspace registration

On 2026-10-28, the user selected a dedicated workspace only, retaining the existing Engine project and its shared memory configuration. CLI 0.1.120 created `agentsdk` with workspace ID `ws-6ae20f53f3b040aa65fa961a` in the existing project. An independent `workspace get` returned the expected name, project, ID and `framework: openai-agents`. The framework value is registration metadata, not a verified execution adapter. The existing geo-intelligence-network workspace was not modified.

The CLI requires an `agent.yaml` even for registration. An ignored administrative manifest under `artifacts/compatibility/workspace-registration/` supplied the name and proposed `agentsdk.app:app` entrypoint. That entrypoint is **not implemented**; the manifest is not deployable. The remote archive manifest path currently points to this registration directory and must be replaced with the actual validated application manifest during COMP-003. No build, deployment, runtime initialization, secret copy, Atlas selection change, or memory reconfiguration was performed.

The ignored local `.env` now records `AGENT_ENGINE_WORKSPACE_ID`; `.env.example` documents the setting. This is an administrative target value, not an Engine memory request parameter or automatic CLI directory binding. CLI commands should explicitly pass the existing context and the workspace ID where supported until a validated application directory is initialized. Existing project credentials and memory settings remain in place. Registration does not resolve the previously observed HTTP 500 or complete Phase 0.

Inspect the registration with:

```bash
agentengine workspace get ws-6ae20f53f3b040aa65fa961a \
  --context 67b385a7976edf15ecc62e06 --json --no-log
```

## Memory cluster permission correction

The user clarified that project-shared memory resides on a different existing cluster from the application target and corrected the `agentsdk` database user's cluster access. Read-only Atlas inspection now lists both OpenAI-SDK and ClusterDemoTelco in that user's scopes, retaining `readWriteAnyDatabase`, `dbAdminAnyDatabase`, and `clusterMonitor`. This supersedes the earlier target-only scope observation. The exact stored Engine URI remains unreadable; the memory location is user-reported.

A read-only context preflight after that correction still returned `MemoryServerError`, HTTP 500, at `2026-10-28T15:11:12.036367+00:00` on the frozen Python 3.15.2 environment. No synthetic turn was submitted because the read preflight failed. Access-list metadata alone does not establish propagation to existing server connections or identify the remaining failure.

The user's shared-memory topology also differs from the original single-cluster acceptance target. Do not mark same-cluster attachment passed; a future explicit architecture decision must reconcile this deployment with ADR-0011 before COMP-002 can be completed.

After an additional 30-second wait, one final read-only preflight returned the same HTTP 500 at `2026-10-28T15:12:31.242728+00:00`. Safe local evidence is `artifacts/compatibility/engine-context-after-access.json`. Both commands exited 1; no write, restart, secret update or further grant change was performed. Repository validation and whitespace checks passed for this evidence update.

## Separate application and project-memory connection settings

The user explicitly requested the existing OpenAI-SDK and ClusterDemoTelco connections for `agentsdk`. On 2026-10-28, the workspace secret `APP_MONGODB_URI` was created from the existing local application URI after checking its SRV hostname against OpenAI-SDK. The value was passed through stdin and was not printed. A separate metadata listing confirmed workspace scope, version 1 and update time `2026-10-28T15:20:02Z`.

| Purpose | Existing cluster | Configuration scope | Secret |
|---|---|---|---|
| Application data | OpenAI-SDK | agentsdk workspace | `APP_MONGODB_URI` |
| Managed memory | ClusterDemoTelco (user-confirmed) | Existing shared project | `MONGODB_URI` |

The project secret metadata was inspected; `MONGODB_URI` remains the existing version 1 secret. Its value was not retrieved or overwritten. The second row is the existing managed-memory connection, not a second newly registered workspace secret. The future application must explicitly read `APP_MONGODB_URI` for its own database operations; that variable is not an automatic Engine SDK setting. Managed memory continues through the project-level Memory API, not a second direct memory client or writer.

The CLI Atlas setup flow stores a selected cluster and requires an initialized application directory. The administrative registration directory was pinned to the existing context, but `agentengine init --workspace-id ...` failed validation because no application `pyproject.toml` exists there. No placeholder package was added to bypass that gate. Therefore no completed Atlas setup selection, application integration, deployment or successful memory operation is claimed. The secret registration is complete; application consumption and hosted execution remain pending.

The user-selected two-cluster connection layout is recorded as an explicit deployment deviation from the original single-cluster requirement, whose formal architecture reconciliation remains open. No new cluster, database user, network rule or runtime restart was created by this task. Repository and whitespace checks passed; documentation changes remain local and uncommitted.

## Synthetic voice and chat continuation checkpoint

The [COMP-004 voice task](../tasks/COMP-004-VOICE.md) passed a bounded real-provider VoicePipeline round trip and following chat turn on the locked Python 3.15.2 environment. Input speech and generated output speech both preserved the synthetic support code; the chat turn recovered it from SDK input-item history. Python rendered the approved response from structured output. The audio was generated, not microphone-recorded, and no audio was retained.

This establishes the synthetic chained-voice and ephemeral history contract only. Browser playback/capture, cancellation, human intelligibility review and Engine-managed sessions remain separate gates. The initial failed live attempt and all tested versions/limits are recorded in the task. The final deterministic harness has 34 passing tests. Phase 0 remains incomplete.

## Two-cluster architecture approval

The user explicitly approved the existing application/memory split. [ADR-0017](../adr/0017-two-cluster-memory-boundary.md) supersedes ADR-0011 and closes the architecture-decision gap noted in earlier historical checkpoints. Runtime memory acceptance remains blocked by HTTP 500; no infrastructure or credentials changed as part of this documentation decision.

## Memory investigation after topology approval

Read-only memory configuration and runtime requests returned HTTP 200. Stored and received configuration generations both remain 9, with voyage-4-large at 1024 dimensions, embed_on_write disabled, and the configured Anthropic extraction provider unchanged. Runtime status remains ready. Subsequently, two scoped synthetic data reads (episodic and semantic) and two context requests returned HTTP 401. This is a new authentication blocker; those responses cannot establish whether the earlier HTTP 500 has been resolved. The local configuration does not retain OAuth client credentials, so the user was asked to run the existing hidden-prompt token refresh script.

Bounded Atlas log inspection was also attempted for the existing memory cluster. A preliminary broad keyword classifier counted `Connection not authenticating` informational messages as failures; inspection showed that classification was not valid evidence of rejected credentials. No authentication-failure count or causal claim is accepted from that preliminary summary. Raw downloaded logs were temporary and removed automatically. Memory-runtime internal logs remain unavailable through the exposed CLI. No restart, secret overwrite, model change or database mutation was performed during this investigation.

Next: after token renewal, compare scoped direct memory reads and context retrieval, preserving their distinct outcomes before selecting a corrective action. The four HTTP 401 observations are in the ignored local `artifacts/compatibility/engine-route-diagnostic.json`.

## Hosted semantic-memory dependency isolation

After token renewal, scoped episodic and semantic GET requests returned HTTP 200. Hosted `build_context_from_sources` requests with explicit text mode also returned 200 for STM and semantic sources. The same source contract with semantic mode returned HTTP 500; adding an explicit OpenAI format did not fix the simplified context route. This narrows the failure to the hosted semantic retrieval path, not all memory operations. These empty synthetic reads do not prove write/read continuity.

Read-only inspection of ClusterDemoTelco identified `mdb_memory_67b385a7976edf15ecc62e06` and five managed collection pairs of text/vector indexes. Inspected indexes were READY/queryable, and vector definitions used 1024 dimensions. No managed collections or indexes were changed.

A bounded isolation experiment then produced a valid 1024-dimensional voyage-4-large query embedding from `https://ai.mongodb.com/v1/embeddings` using the locally injected Voyage key. Direct `$vectorSearch` queries on memory_semantic and memory_snapshot passed with organization/project/synthetic-user prefilters, 20 candidates, limit 1 and count-only output. Both returned zero matches, as expected for the diagnostic identity. This proves the tested embedding and query contracts from the local diagnostic process only; it does not establish the hosted runtime's key, network access, or retrieval quality. See [safe dependency evidence](../../compatibility/engine-dependency-evidence.json).

### Endpoint experiment and current remote state

An existing local Docker memory-server image 0.11.9 was inspected only for its shipped provider configuration contract; it was not used as a substitute for hosted memory. Its Voyage implementation accepts VOYAGE_URL. This older local image does not establish the hosted 0.11.11 implementation. Based on the Atlas-issued-key hypothesis, project secret VOYAGE_URL was added as `https://ai.mongodb.com/v1` (version 1, 2026-10-28T16:19:50Z). Existing keys, model, dimensions and database URI were preserved.

`secret set --sync` stored the endpoint but timed out after five minutes awaiting readiness. The memory process subsequently reported ready, while `GET /secrets/runtime` still returned `ready: false`, `source: broker`, `reason: pending`. A dry run followed by `memory apply --wait` restarted only the project memory server, kept the configured image and returned ready. A subsequent context request at 2026-10-28T16:27:08.550925+00:00 still returned HTTP 500. No agent was built or deployed; agentsdk remains undeployed, and the geo agent deployment was not replaced.

The latest isolation check again reports pending secret readiness, successful hosted text retrieval, and failed semantic retrieval. Therefore the endpoint experiment is **not a confirmed fix**, and the currently loaded hosted provider configuration is unresolved. VOYAGE_URL remains registered. The original project VOYAGE_API_KEY has not been overwritten; its equality with the locally tested key is unknown. The next decision depends on confirming that key pairing or obtaining the provider exception through Engine diagnostics/support. Do not treat a ready process as proof that secrets have converged.

## Retest after user-managed shared provider correction

On 2026-10-28, the user reported completing the shared memory provider configuration while retaining Anthropic and the geo-intelligence-network configuration. No provider model, key, endpoint, dependency, deployment or runtime configuration was changed by this retest. The exact hosted secret values and causal effect of individual changes were not inspected.

On the frozen Python 3.15.2 / agent-engine-sdk-memory 0.11.11 macOS ARM64 environment, the existing read-only context preflight passed at 16:52:16 UTC. Explicit semantic-source requests in both text and semantic retrieval modes also succeeded using Claude output formatting. These observations supersede the earlier HTTP 500 for the tested requests; they do not establish retrieval quality or Anthropic extraction correctness.

One synthetic STM turn was then submitted through the managed Memory SDK. The SDK acknowledged it, but immediate context retrieval did not contain the exact marker, so the continuity probe exited 1. A subsequent read-only check of the same synthetic identity, in both text and semantic STM modes, also succeeded at the request level but did not contain the marker. The distinct user/session reads did not contain it either; this negative result alone is not isolation proof when the positive control failed. The write was not repeated and its synthetic record was not deleted.

Ignored local evidence: `artifacts/compatibility/engine-context-after-user-provider-fix.json`, `engine-sources-after-user-provider-fix.json`, `engine-after-user-provider-fix.json`, and `engine-marker-readback-after-user-provider-fix.json` in the same directory. No secrets or returned memory content are recorded. Next, investigate acknowledged-turn visibility and the context-selection contract before claiming memory continuity. Secret convergence, durable extraction, tenant authorization and hosted agent execution remain unverified. Phase 0 remains incomplete.

## Persisted marker and STM retrieval investigation

On 2026-10-28, further read-only investigation confirmed that the existing synthetic marker is persisted in ClusterDemoTelco, in `memory_short_term` within the project-managed database. A query constrained by organization, project and the synthetic user returned one record with the expected marker and session. The record is private, unpromoted and has no embedding. No other user's content was read or logged. No new write, index creation or provider configuration change was performed.

Hosted configuration reports Anthropic `claude-opus-5-5`, Voyage `voyage-4-large` at 1024 dimensions, and `short_term.embed_on_write=false`; generation and received generation are both 9. Runtime state and secret readiness now both report ready. This supersedes the earlier pending-secret observation, but does not establish successful Anthropic extraction.

The installed SDK 0.11.11 documents a 500-token formatting reserve. The previous diagnostic budget of 512 left too little room for a whole memory chunk. The probe now uses 2048 and checks the returned `WriteTurnResult.acknowledged` field instead of assuming acknowledgement from a non-throwing return. The historical report did not retain that field; persistence is now independently confirmed by the scoped database read.

The existing marker remained absent with 2048 tokens in both semantic retrieval and exact-marker text retrieval. Per-source outcomes reported zero results, no error and no retryable flag. `list_search_indexes()` returned no Search indexes for `memory_short_term`, unlike the previously inspected indexed memory types. Missing embeddings and absent STM Search indexes are concrete retrieval prerequisites to investigate with the Engine owner; no working STM retrieval contract or single causal fix is claimed. The API returning success with zero results must not be interpreted as memory continuity.

Safe ignored evidence: `artifacts/compatibility/engine-budget-readback.json`, `engine-retrieval-contract.json`, `engine-runtime-after-provider-fix.json`, and `engine-synthetic-storage.json` in the same directory. Index absence and record flags were observed through a separate scoped read. Next: validate the hosted Engine's supported STM retrieval/index lifecycle and whether raw turns must be promoted before context retrieval. Preserve shared Anthropic/provider configuration; do not manually create competing managed indexes or enable shared embedding writes without a validated service contract.

Validation: 36 deterministic compatibility tests passed on both the bootstrap interpreter and the frozen Python 3.15.2 environment. Repository validation (47 Markdown files, 17 ADRs) and `git diff --check` passed. These tests cover rejected acknowledgements and sufficient diagnostic context budget; they are not provider acceptance. Phase 0 remains incomplete.

## Applied STM configuration and successful continuity proof

On 2026-10-28, the user explicitly authorized applying the shared development-project change and restarting/upgrading its memory server. After renewing the expired SDK token, the current generation-9 configuration was retrieved and copied to a private, ignored backup. Only `metadata_partition_index.short_term: [both]` and `short_term.embed_on_write: true` were changed. Existing index declarations, Anthropic extraction configuration, Voyage model/dimensions and other options were preserved; no secrets were changed. These are project-wide settings and also affect geo-intelligence-network. Embedding new STM writes adds provider usage and write latency.

`agentengine memory configure` stored generation 10. The upgrade dry run identified the actual hosted image as v0.11.10 (the installed client was already 0.11.11), and resolved v0.11.11. `memory apply --upgrade --wait` successfully moved the memory server to v0.11.11 and returned ready. No agent was built or deployed. Independent API reads confirmed generation and received generation 10, exact equality with the prepared configuration, runtime ready and secrets ready.

On the frozen Python 3.15.2 macOS ARM64 / agent-engine-sdk-memory 0.11.11 environment, a single new synthetic turn passed the existing live continuity probe at 18:34:55 UTC: acknowledgement true, exact marker recovered in its own session, marker absent for a distinct user/session. A later read-only probe at 18:44:22 UTC recovered the same marker through explicit text, semantic and hybrid STM modes. Every source outcome reported the requested effective mode, one result, no error and no retryable flag. No manual managed-index creation or direct database writes were used. Successful search behavior is verified; index status was not separately listed in this continuation.

This supersedes the earlier zero-result STM blocker for newly written synthetic turns under generation 10. It does not establish backfill of old unembedded turns, cross-tenant authorization, deletion, concurrent-session isolation, durable Anthropic extraction, retrieval quality, hosted execution or phase completion. The distinct-user/session check changes both identifiers together. Historical reports remain historical and must not be relabeled as successes.

Evidence is in ignored `artifacts/compatibility/stm-configuration/`: `applied.json`, `engine-validation.json`, and `retrieval-modes.json`. `before.json` and `project-config.yaml` are private configuration copies, not commit artifacts. Official contract: [Memory SDK configuration and per-source retrieval](https://www.mongodb.com/docs/agentengine/sdk/python/packages/agent-engine-sdk-memory/). Repository documentation remains locally authored and uncommitted; the project memory configuration and image changes were actually applied and verified remotely. Phase 0 remains incomplete.

## Separate user/session filters and durable extraction check

After verifying published checkpoint commit `065c37d`, the next bounded increment reused its synthetic STM marker without any new writes or configuration changes. A live configuration read confirmed snapshot `max_messages=20`, `stale_minutes=1`, extraction enabled for semantic/episodic/taxonomic, and STM embedding on write enabled. A stale threshold is not a completion SLA or proof that a one-turn session was promoted. Official [memory SDK documentation](https://www.mongodb.com/docs/agentengine/sdk/python/packages/agent-engine-sdk-memory/) describes asynchronous turn-to-snapshot-to-extraction processing.

At 18:49:47 UTC and again through the reusable diagnostic at 18:51:01 UTC on 2026-10-28, the original marker was present in STM for the original user/session, absent for the same user in a different session, and absent for a different user using the original session ID. Every STM source reported hybrid mode without errors or degradation. This improves the earlier negative control that changed both identifiers at once, but remains filter evidence under one service credential rather than tenant authorization.

For the original user in a new session, explicit semantic and episodic sources returned zero results with no source errors. The exact durable-marker assertion failed; the other-user durable control is therefore blocked, not accepted as proof of isolation. No claim of successful Anthropic extraction or its root-cause failure follows from these observations. No additional turns, direct memory writes, promotion requests or shared-runtime changes were made.

Safe local evidence: `artifacts/compatibility/engine-isolation-validated.json`. The initial exploratory report `engine-durable-isolation.json` labeled the empty durable negative control as passing independently; the reusable diagnostic supersedes that acceptance classification by requiring its positive control. See [the diagnostic task](../tasks/COMP-002-DIAGNOSTICS.md#read-only-isolation-and-durable-memory-diagnostic) for reproduction and interpretation. Next: inspect the synthetic session's snapshot/promotion and extraction-task lifecycle before selecting a further provider/configuration change. A representative multi-turn extraction fixture and separate tenant credentials remain necessary for broader acceptance.

Validation: 40 deterministic tests passed on both the bootstrap interpreter and frozen Python 3.15.2 environment. Repository validation and `git diff --check` passed. The new tests reject leaks, absent positive controls, missing observations and unhealthy responses. An actual invocation without `--allow-live` exited 2 without network calls; the real provider diagnostic exited 1 because durable retrieval remains unproven. Phase 0 is still in progress; changes are local and uncommitted.

## Completed conversation pair and durable semantic-memory proof

The subsequent read-only lifecycle investigation found the original synthetic user turn embedded but unpromoted, with no snapshot. A scoped task-payload query found a snapshot task marked succeeded without a stored error. Task success alone therefore did not prove snapshot creation. The initial top-level user filter did not match task documents because task identity is nested under `payload`; the corrected query retained organization/project/session constraints.

Inspection of a stopped local memory-server v0.11.9 image revealed pair preservation: a trailing user message is retained for its assistant response, and a one-message buffer can yield no snapshot. This older image was used only to formulate a hypothesis, not as proof of the hosted v0.11.11 implementation. Official [memory extraction documentation](https://www.mongodb.com/docs/agentengine/add-features/memory-extraction/) confirms the asynchronous turn, snapshot and extraction stages, but does not specify pair preservation.

At 18:57:22 UTC on 2026-10-28, one authored synthetic assistant acknowledgement was appended to the existing diagnostic session through `Memory.record_turn`, using a unique explicit idempotency key. The SDK acknowledged turn sequence 2 with an embedding. No user turn was repeated, no long-term memory was written directly, and no configuration, credentials or runtime were changed. The acknowledgement restated only the synthetic marker; it was a test fixture, not a model-generated answer.

At 18:58:59 UTC, after the configured inactivity interval, all five read-only assertions passed: STM positive control, separate changed-session and changed-user negative controls, exact marker retrieved from durable sources for the same user in a new session, and absence for another user. The durable response selected one semantic record and zero episodic records, with no source errors or degraded retrieval modes.

A final scoped database inspection at 19:11:44 UTC confirmed both turns promoted, one embedded snapshot with no pending extractions, and one embedded semantic record. Snapshot, semantic, episodic and taxonomic tasks were marked succeeded without stored errors. There was no episodic document for this minimal fixture; a successful task does not require that every memory type produce content. These observations support the incomplete user-only fixture as the cause of the earlier missing durable result. The configured Anthropic extraction path produced a durable semantic record after the pair was completed; exact upstream request details were not logged.

Safe portable evidence is [engine-durable-evidence.json](../../compatibility/engine-durable-evidence.json). Ignored detailed evidence includes `engine-extraction-storage.json`, `engine-extraction-tasks.json`, `engine-complete-synthetic-pair.json`, `engine-pair-promotion.json`, `engine-isolation-after-pair.json` and `engine-completed-promotion.json` under `artifacts/compatibility/`. No raw customer content or secret values are included.

This closes the bounded durable-semantic-marker and separate user/session filter proof. It does not prove tenant authorization, deletion, concurrency, retention/recovery, general extraction quality or Engine-hosted application execution. The existing read-only isolation script now passes against this completed fixture. Future durable tests must submit a complete synthetic conversation pair through the managed API and wait for consolidation; a user-only STM fixture is insufficient. Phase 0 remains in progress.

## Credential boundary proof and application-tenancy distinction

On 2026-10-28, read-only CLI inventory found three existing service accounts, all project-scoped to the shared project and assigned PROJECT_OWNER. Only one service token is injected locally and only one project context is configured. No account was created, rotated, deactivated or granted permissions. Owner metadata and masked secret metadata were not copied into repository evidence. A decoded token's claim names alone did not establish its project scope; the server-side behavior was tested separately.

The new `engine-auth` probe in `scripts/check_compatibility.py` makes four sequential read-only context requests with no application retries or redirects. At 19:16:22 UTC, the valid credential returned HTTP 200, missing and invalid credentials returned HTTP 401, and the valid credential against a random synthetic project ID returned HTTP 403. The probe requires all four expected results; a failed positive control, 404 or server error cannot masquerade as a successful denial. No returned context or error body is retained. The 20-second timeout applies per transport I/O, not to total runtime.

[Portable authentication evidence](../../compatibility/engine-auth-evidence.json) records this bounded proof. The divergent project ID was synthetic, not a second existing project with its own known records and credentials, so this is project-mismatch rejection evidence, not full cross-project isolation. The SDK's [official hosted-connection contract](https://www.mongodb.com/docs/agentengine/sdk/python/packages/agent-engine-sdk-memory/) documents credential-to-project binding.

Clarification: project service accounts are not application tenants. Under the [approved data architecture](../DATA_ARCHITECTURE.md), the backend must derive tenant/customer/user scope from authenticated identity and enforce it before using its service credential; user_id/session_id filters supplied by a privileged caller are not authentication. Creating two accounts in the same shared Engine project would not establish tenant isolation. Keep the existing shared memory topology and test these concerns independently. No application ingress/authentication adapter exists yet, so no end-to-end tenant authorization claim is made.

Remaining authorization work: validate a dedicated runtime credential with the documented AGENT_DEVELOPER role against required allowed operations and forbidden administrative operations, without downgrading the existing administrative account or changing geo-intelligence-network credentials. An independent real-project credential/fixture is needed for a complete cross-project negative control. Application-tenant tests require an authenticated boundary that rejects caller-supplied identity substitution. These are unexecuted follow-ups, not implied approvals or successful tests.

Validation: 44 deterministic compatibility tests passed on both the bootstrap interpreter and frozen Python 3.15.2 environment. The live probe exited 0. No memory writes, provider changes, role changes or runtime restarts occurred in this increment. Phase 0 remains incomplete; local changes are uncommitted.

## Supported service roles, read-only access and token revocation

On 2026-10-28, CLI 0.1.120 and the current [service-account credential documentation](https://www.mongodb.com/docs/agentengine/api-keys-service-accounts/) list PROJECT_OWNER and PROJECT_READ_ONLY for project-scoped service accounts. This conflicts with the earlier SDK example and cached OpenAPI text mentioning AGENT_DEVELOPER. The previous recommendation to validate AGENT_DEVELOPER as an available limited execution role is therefore unverified and superseded by this finding. Do not substitute an alias and claim narrower grants without checking its effective role. The current documentation requires PROJECT_OWNER for project-scoped agent invocation.

A task-specific account named `agentsdk-phase0-readonly` was created with PROJECT_READ_ONLY and a 24-hour secret. Creation also returned a paired Atlas service-account ID; no existing identity or organization setting was modified. The secret was captured directly to a mode-0600 file under the ignored `artifacts/compatibility/readonly-account/` directory and was never printed or inserted into `.env`. OAuth token exchange succeeded.

At 19:19:13 UTC, the limited credential returned 200 for project metadata and memory context. A valid, idempotency-keyed synthetic turn-write request returned 403; no successful memory write is claimed. A malformed request to the service-account creation endpoint returned 401. The current documentation says that endpoint requires a signed-in user session, so this is a credential-type rejection, not a role-specific administration-denial proof. The existing owner credential independently returned 200 for memory context.

The temporary account was then deactivated. At 19:20:45 UTC, the previously working token returned 401 and a new token exchange using the same client credentials also returned 401. An independent CLI metadata read reported `is_active=false`. Existing agentsdk, geo and CI identities were unchanged. The paired Atlas account's separate lifecycle was not independently inspected; do not claim it was deleted.

[Portable read-only/revocation evidence](../../compatibility/engine-readonly-evidence.json) contains only sanitized results. Private creation output remains ignored and contains the now-deactivated credential. No secret rotation, provider change, memory restart or account-role broadening was performed.

This establishes the tested read-only/read-write distinction and immediate rejection of the deactivated service credential. It does not establish a narrowly permissioned write-capable runtime role, application-tenant authorization, or cross-project isolation with two real projects. The currently documented role set offers no separate project-level invoke-only role. Hosted execution must account for that platform limitation rather than silently treating PROJECT_OWNER as least privilege. Database/service ownership and application tenant enforcement remain separate requirements. Phase 0 remains incomplete.

## Paired Atlas test-account cleanup

On 2026-10-28, an authenticated Atlas project-level read found the temporary paired account still present with GROUP_READ_ONLY and one secret after Engine deactivation. Engine name `agentsdk-phase0-readonly` maps to Atlas name `sa-ap-6ae24a796ef1e72bb8f70bcd` and client ID `mdb_sa_id_6ae24a7ab5ba6da6774a4f71`; this is a service account, not the MongoDB database user `agentsdk`. An organization-level membership query returned 401 USER_UNAUTHORIZED. No organization permissions were changed.

The exact paired account was verified against the private creation response. Its one observed secret was revoked through the Atlas project API, and an independent read confirmed zero secrets. Its project membership was then removed; a subsequent project-level get returned 404 RESOURCE_NOT_FOUND. The organization-level account object was not deleted because organization access was unavailable; do not describe this as complete organization deletion. Existing accounts were untouched. Portable evidence is appended to [engine-readonly-evidence.json](../../compatibility/engine-readonly-evidence.json).

## Hosted execution framework preflight

COMP-003 has begun with the [hosted contract task](../tasks/COMP-003-HOSTED.md). The currently fetched official SDK overview lists LangGraph and Google ADK; it does not list an OpenAI Agents SDK adapter. The generic BaseApp/BaseAgent interfaces document extension points, not a tested OpenAI adapter. No build, deployment, new workspace or framework substitution was performed.

## Installed hosted-runner contract inspection

The [COMP-003 experiment](../tasks/COMP-003-HOSTED.md#pinned-runner-contract-experiment) installed OpenAI Agents SDK 0.24.0 with Engine base SDK/runner 0.11.11 in a separate frozen Python 3.15.2 macOS ARM64 environment. Dependency resolution, installation and imports passed. The actual runner dispatch guard rejected a native OpenAI Agent, and no model, workflow or suspension adapter hooks were registered. Inspection assertions passed; the diagnostic correctly exited 2 for blocked native integration.

This distinguishes a working memory API from an unimplemented hosted execution adapter. A custom adapter remains possible but untested and is not claimed as supported. No runtime was started, no model/tool request was made, and no remote build, deployment, workspace mutation or provider configuration change occurred. See [portable contract evidence](../../compatibility/hosted-contract-evidence.json) and the task's mapping table for remaining work. Phase 0 remains incomplete.

## Custom adapter local contract update

Following explicit user authorization and [ADR-0018](../adr/0018-engine-feature-precedence.md), the [custom adapter](../../compatibility/openai_engine_adapter/README.md) implements a bounded BaseAgent/Runner bridge using Engine model/tool proxies. Eleven offline adapter tests pass on the pinned hosted-runtime environment. Model/tool transport is doubled; actual proxy construction and shared step allocation are inspected without network. No hosted execution, live policy enforcement or approval/replay acceptance is claimed. [COMP-003](../tasks/COMP-003-HOSTED.md) retains those gates.

## Custom loader and package update

The [custom adapter package](../../compatibility/openai_engine_adapter/README.md) now exposes a BaseApp loader and reuses authenticated AER context bindings. Sixteen tests pass, including actual TenantRuntime dispatch and AER terminal-result parsing with model/tool transport doubles. Input `message` and output `response` translation gaps were corrected. The package lock and sdist/wheel build pass on the existing Python 3.15.2 interpreter; Linux and hosted execution remain untested. The dedicated workspace was remotely verified as `not_deployed`; no build/deployment or policy/secret changes were made. Invoice provider selection and the concrete Tool Pod provider implementation remain prerequisites for live trace/denial evidence. Memory provider configuration is unchanged.

## Remote invoice build attempt

The user selected gpt-6-luna for the invoice workflow; shared Anthropic memory remains unchanged. Twenty-two offline adapter/loader/provider tests, strict manifest validation, dependency checks and local sdist/wheel build pass. The source-only remote build was accepted with framework openai-agents after custom was rejected. Build `bld_01M621HKZWQ2Q13QCGQM15M7ST` failed because its VM image/uv could not find Python 3.15.2, before the adapter ran. A generic lock error followed; no target downgrade or lock removal was made. The workspace remains not_deployed; no live invoice/Engine denial evidence exists. OPENAI_API_KEY was created at workspace scope only, without logging its value. [Build evidence and source hashes](../../compatibility/hosted-invoice-evidence.json) distinguish uploaded local source from the older commit label. [COMP-003](../tasks/COMP-003-HOSTED.md) tracks the interpreter blocker and remaining live gates.

## Python 3.15.2 bundle and remote image success

The [bundled interpreter experiment](PYTHON315_HOSTED.md) preserves the selected Python target. Both full and compact profiles passed frozen installation and 22 offline adapter tests in Linux/amd64. The full source archive exceeded Engine's decompressed-size limit; the compact profile omitted unused development/GUI/embedding components and passed archive validation. Build `bld_01M622CNYJW9R30TVZQ0Q36DQF` selected the bundled CPython 3.15.2 and succeeded through Firecracker image publication. The missing-interpreter blocker is resolved for this tested packaging path.

Deployment `deploy-f45c6a70` was started for the exact successful build. Initial checks reported OENotReady, followed by pending internal certificates. These readiness blockers resolved: deployment succeeded at 2026-10-28T20:28:52.331Z, with OE, agent and tool available. A bounded invoice invocation was rejected as not deployed and did not establish model/tool execution. The existing geo-intelligence-network workspace independently reports ready/healthy. These platform observations do not identify an adapter failure or prove live invoice/policy acceptance. Forty-six bootstrap compatibility tests, including staging/checksum tests, pass. [Portable follow-up evidence](../../compatibility/python315-linux-evidence.json) records the build and deployment outcomes.


## Hosted deployment succeeds; model policy blocks invocation

The runtime registered `lookup_invoice`, populated the named LLM registry and completed AER warm-up. A blocking synthetic invoice call returned HTTP 500; a separate streaming call produced a correlated Engine `invoke_llm` trace marked BLOCKED: `AUTHORIZED_MODELS policy denied model "gpt-6-luna" at generation 8`. This is live model-policy denial evidence, not a successful invoice or complete positive/negative control. See [COMP-003](../tasks/COMP-003-HOSTED.md) and [portable evidence](../../compatibility/python315-linux-evidence.json). Project policy permits only `claude-opus-5-5`; its 26-tool allowlist omits `lookup_invoice`. Expanding these shared project permissions requires explicit user approval. No policy, memory provider or credential was changed in this diagnostic.


The subsequent GPT-5.6 Luna deployment `deploy-fbbf9a94` succeeded. A hosted call confirmed `gpt-5.6-luna` in the Engine denial trace; the shared model allowlist still blocks it. [Current model evidence](../../compatibility/gpt56-luna-evidence.json) distinguishes the passed direct provider test from the blocked hosted call. See [COMP-003](../tasks/COMP-003-HOSTED.md) for the pending policy authorization and positive control.


## Bounded hosted invoice accepted

After the authorized project allowlist additions propagated, the deployed `gpt-5.6-luna` custom adapter completed the synthetic invoice read through Engine model/tool proxies. A separate out-of-fixture invoice was rejected by backend code, with the failure propagated and traced. [COMP-003](../tasks/COMP-003-HOSTED.md) and [portable evidence](../../compatibility/gpt56-luna-evidence.json) contain exact outputs, call correlation and scope. The earlier Engine model-policy denial remains distinct from this backend negative control. This closes the basic hosted execution gate, not the entire phase: approval/resume, replay and hosted memory continuity remain open.

## Review native-interrupt contract correction

The first opt-in hosted review deployment built successfully but OE rejected direct suspension. The bridge now uses native interrupt finalization; 39 contract tests pass on macOS and Linux with doubled OE transport. [COMP-003](../tasks/COMP-003-HOSTED.md#native-interrupt-correction-after-hosted-rejection) records the failure and corrected contract; [review evidence](../../compatibility/hosted-review-evidence.json) tracks current remote results. This does not complete Phase 0 or establish hosted memory continuity.

Corrected deployment `deploy-8e0ea235` subsequently passed hosted suspension, approval/rejection and wrong/stale review-ID controls. Resumed traces show one model and one tool step per execution. See [hosted native review evidence](../tasks/COMP-003-HOSTED.md#hosted-native-review-and-resume-pass); forced-process recovery, changed actions/fences, reviewer authorization/expiry and hosted memory continuity remain unvalidated.

[Recovery after explicit sandbox termination](../tasks/COMP-003-HOSTED.md#recovery-after-explicit-session-sandbox-termination) now passes in the same execution with one visible model/tool sequence. A resume answer containing altered arguments is rejected before a valid approval succeeds. The 41 local tests additionally cover propagation of doubled Engine conflict/stale-fence errors; live fencing and semantic-action conflict enforcement remain separate open gates.

[Hosted action identity and stale-attempt controls](../tasks/COMP-003-HOSTED.md#hosted-action-identity-and-stale-attempt-controls-pass) now pass: changed arguments/call ID/tool name receive `NONDETERMINISTIC`, and the previous attempt/fence receives `STALE_FENCE` after resume. Both attempts have correlated hosted logs. The normal review build is restored at `deploy-72088429`; authorization/expiry, broader fault cases and hosted memory continuity remain open.

[Hosted expiry controls](../tasks/COMP-003-HOSTED.md#hosted-review-expiry-and-restart-preservation-pass) pass on `deploy-b0491bde`: timely approval succeeds, and late approval after sandbox termination returns `expired` in the same execution. The current fixture uses a synthetic 60-second TTL. Independent reviewer authorization remains open: the current credential accepted a delegated synthetic `user_id`, which is not a separately authenticated reviewer. The suite now has 48 passing macOS/Linux tests; hosted memory continuity remains separate.

[Memory-enabled hosted execution](../tasks/COMP-003-HOSTED.md#hosted-memory-enabled-execution-passes-retrieval-gate-remains-open) now completes model/tool/review and resumed settlement with Engine-owned memory projection. Independent stored-marker/deduplication/retrieval acceptance remains open: the local read token returns 401 INVALID_TOKEN and the trace reports zero memory counters. The current synthetic run ID is `98751e7966484cf3a7703be3086aa820`; reuse it for read-only validation after restoring a valid same-project credential. No duplicate writer or Anthropic configuration change was introduced.

[Independent hosted-memory retrieval](../tasks/COMP-003-HOSTED.md#independent-hosted-memory-retrieval-passes-after-token-refresh) passed after the user refreshed the local token: all five STM/durable positive and user/session negative controls passed for the existing hosted marker, with zero new writes. This resolves the stored-marker and new-session retrieval gate for the bounded probe. It does not establish independent user authorization, stored-turn deduplication or model context injection.
