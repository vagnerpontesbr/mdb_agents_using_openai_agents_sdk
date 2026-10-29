# Custom OpenAI Agents SDK / Engine adapter

This experimental adapter runs the real OpenAI `Runner` inside MongoDB Agent
Engine. It is a custom integration with bounded hosted evidence, not a native
vendor-supported OpenAI adapter or the full telecom application. Phase 0 is
complete for the [accepted demo scope](../../docs/compatibility/PHASE_0.md).

## Runtime ownership and implemented contract

| Component | Responsibility |
| --- | --- |
| OpenAI Agents SDK | Agent/Runner orchestration, tool schemas and bounded result translation |
| Agent Engine | Hosted execution, model/tool mediation, native review/resume, replay, managed memory and primary traces |
| Application backend | Email/password identity, requester-only admission, exact-action checks and domain validation |
| MongoDB application cluster | App-owned identity records; no duplicate Engine conversation/review store |

The current request contract is one text request, one model call and at most one
remote read tool. Tool output ends the run without another model synthesis step.
Strict Pydantic argument/result validation rejects malformed or out-of-scope
requests. Engine tool/model failures propagate; the adapter does not convert them
into successful financial answers or perform an independent retry.

[adapter.py](src/openai_engine_adapter/adapter.py) implements `BaseAgent.execute`
with a single-use awaitable/async-iterable result. [app.py](src/openai_engine_adapter/app.py)
registers the BaseApp/TenantRuntime loader and translates AER input/output.
Engine proxies share the request's operation-step allocator and trusted runtime
context. The [provider](src/openai_engine_adapter/openai_provider.py) calls the
Responses API only in the Engine Tool Pod, using injected credentials.

[Native review](src/openai_engine_adapter/review_execution.py) binds the exact
result to Engine interruption/finalization. [Managed memory](src/openai_engine_adapter/managed_memory.py)
projects turns through Engine ownership, and [memory context](src/openai_engine_adapter/memory_context.py)
retrieves scoped semantic/episodic data for the model. No SDK Session persistence,
independent approval database or second memory writer is introduced.

## Tested entrypoints

The repository `agent.yaml` defaults to the basic `invoice:app` fixture. Staged
manifests select other entrypoints explicitly; staging/building is not deployment.

| Module (`openai_engine_adapter.<module>:app`) | Bounded purpose |
| --- | --- |
| `invoice` | Basic synthetic invoice and backend scope rejection |
| `review_invoice` | Native approve/reject, resume and replay |
| `expiry_invoice` | Synthetic 60-second review deadline |
| `memory_invoice` | Engine-owned conversation projection |
| `recall_invoice` | Semantic/episodic retrieval plus native review; restored hosted demo |
| `expiry_memory_invoice` | Combined memory/review-expiry and recovery proof |
| `contract_probe` | Isolated Engine action/fence diagnostic; see task evidence |
| `dependency_failure_invoice` | Isolated unavailable loopback dependency in Tool Pod; never returns an invoice |

The active checkpoint is `recall_invoice:app`, restored with deployment
`deploy-9c637560`, build `bld_01M63Y9G5090B560AYEFWA7D4K`. A positive memory/native
review call passed afterward. [Hosted evidence](../../docs/tasks/COMP-003-HOSTED.md)
and [fault/restoration evidence](../../docs/tasks/COMP-003-FAULTS.md) record exact
scope, historical failures and restoration. Workflow versions are fixture-specific;
switching entrypoints is not an in-flight workflow migration contract.

## Validation and packaging

Tested pins: Python 3.15.2, OpenAI Agents SDK 0.24.0, OpenAI 3.40.0, and Engine
SDK/runner 0.11.11. The 61 hosted-contract tests passed on macOS and in the existing
Linux/amd64 image with current source mounted. Those local tests use doubled
remote boundaries where documented; actual hosted results are recorded separately.

From the project root, with the frozen hosted environment installed:

```sh
uv run --project compatibility/hosted-runtime --frozen --no-sync python -m unittest discover -s tests/hosted_contract -v
uv build --project compatibility/openai_engine_adapter --python compatibility/hosted-runtime/.venv/bin/python --out-dir artifacts/compatibility/adapter-dist
```

The hosted build uses an allowlisted source stage and a verified compact Linux
Python bundle. Follow [the Python hosting runbook](../../docs/compatibility/PYTHON315_HOSTED.md)
and `scripts/prepare_hosted_invoice.py`; never upload the root `.env`, `.venv` or
private diagnostic outputs. Builds/deployments incur external work and are not
needed for documentation checks. [Demo startup](../../docs/runbooks/DEMO.md) is separate.

## Explicit limitations

- Complete chronological transcript restoration is excluded by [ADR-0021](../../docs/adr/0021-demo-semantic-episodic-continuity.md).
- General multi-turn tool loops, supervisor/specialist composition, handoffs,
  provider continuation IDs, structured model outputs and token streaming are not
  validated by this single-tool adapter. Native review continuation is distinct
  from arbitrary OpenAI conversation continuation.
- The local app uses the private operator CLI identity under [ADR-0022](../../docs/adr/0022-demo-private-engine-cli-identity.md);
  this is not an unattended least-privilege Engine credential solution.
- Cancellation stops awaiting work locally; it does not prove cancellation of
  already-running remote work or billing. Injected dependency failure is not a
  guarantee for every real backing-service outage.
- Tests do not establish production capacity, perfect memory extraction, identical
  LLM prose or factual correctness beyond the exact validated synthetic result.

The [publication runbook](../../docs/runbooks/REPOSITORY_SETUP.md) distinguishes
published code, remote CI and current local documentation changes.
