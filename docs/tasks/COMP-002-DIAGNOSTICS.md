# COMP-002: Identify memory failure boundaries and inspect Atlas access

- Status: Diagnostic increment done locally; provider compatibility blocked
- Owner: Repository implementation
- Dependencies: COMP-001, existing Atlas/Engine configuration
- Relevant ADRs: [Memory boundaries](../adr/0003-memory-state.md), [approved cluster boundary](../adr/0017-two-cluster-memory-boundary.md)

## Scope

Inspect existing Atlas network/user/cluster metadata without mutation and improve the existing synthetic memory diagnostic. This increment does not implement application memory or complete COMP-002.

## Acceptance criteria

- Distinguish client initialization, write, same-session read, other-session read and client close failures.
- A write exception must retain an unknown persistence outcome; no automatic probe-level retry.
- Suppress raw exception text and retain only sanitized status plus synthetic correlation metadata.
- Failed separation must fail the diagnostic even after an acknowledged write.
- Record actual Atlas inspection and functional memory evidence independently.

## Validation and evidence

On 2026-10-28, authenticated read-only Atlas CLI inspection succeeded outside the sandbox. The sandbox's unauthenticated result did not describe the user's Terminal login. Findings and limitations are recorded in the authoritative [Phase 0 checkpoint](../compatibility/PHASE_0.md#authenticated-atlas-inspection-and-failure-stage-evidence).

`python3 -m unittest discover -s tests/compatibility -v` passed 29 tests, including failure injection at all five memory stages and a negative separation control. These use SDK doubles and do not establish provider compatibility. The same 29 tests passed in the locked Python 3.15.2 environment. `python3 scripts/check_repository.py` passed with 45 Markdown files and 16 ADRs; `git diff --check` passed. The existing SDK method signatures and pinned dependency versions are unchanged.

A single real read-only context preflight in the frozen Python 3.15.2 environment still returned `MemoryServerError`, HTTP 500, at report time `2026-10-28T15:01:52.323135+00:00`. The command exited 1. Safe local evidence is `artifacts/compatibility/engine-context.json` (ignored). No new memory write was attempted.

## Remaining diagnostic handoff

The next provider investigation should correlate the context failure above with server-side memory-runtime logs. The user-confirmed database identity has scope on the intended cluster, and Atlas lists platform-labeled network entries; neither establishes the exact stored URI/password, current runtime egress IP or a successful runtime-to-Atlas connection. Obtain those checks from the Engine configuration owner/provider without posting secrets. Verify the embedding endpoint/key pairing if the runtime logs identify provider authentication or embedding failures. Do not broaden roles, overwrite secrets, change models, or restart the service based only on an unexplained HTTP 500.

Application identities still require service/database least privilege and independent allowed/denied tests. Designated-cluster attachment, memory continuity/isolation and hosted execution remain open. Local edits are not committed, pushed or deployed. Phase 0 is not complete.

## Latest continuation

[Hosted dependency isolation](../compatibility/PHASE_0.md#hosted-semantic-memory-dependency-isolation) now proves that basic reads and text-mode context work, while semantic context fails. Local Atlas embeddings and filtered vector queries passed independently. Hosted secret readiness remains pending after the documented endpoint experiment. The project Voyage key has not been compared with the working local key or replaced. This supersedes the earlier broad description of memory as wholly unverified: write/read continuity and semantic retrieval acceptance still remain open.


## Shared provider correction retest

The [latest retest](../compatibility/PHASE_0.md#retest-after-user-managed-shared-provider-correction) supersedes the earlier semantic HTTP 500 observation: basic context and explicit text/semantic requests now succeed. A single synthetic STM write was acknowledged, but immediate and subsequent context retrieval did not return its marker. Continuity acceptance therefore still fails; no repeated write or provider configuration change was made.


## Persisted STM marker investigation

The [latest investigation](../compatibility/PHASE_0.md#persisted-marker-and-stm-retrieval-investigation) confirms the marker is stored with the intended synthetic session on the designated memory cluster. Secrets and runtime now report ready. STM retrieval still returns zero results; the record has no embedding and its collection has no Search indexes. The harness now verifies the acknowledgement field and uses a context budget above the server's formatting reserve. Managed index lifecycle and end-to-end continuity remain unresolved.


## STM continuity gate passed after authorized configuration application

The [applied STM checkpoint](../compatibility/PHASE_0.md#applied-stm-configuration-and-successful-continuity-proof) records generation 10, memory-server upgrade v0.11.10 to v0.11.11, and successful synthetic write/read plus distinct-user/session negative control. Text, semantic and hybrid retrieval also passed without source degradation. Anthropic and credentials were preserved. Earlier missing-STM results are superseded for new turns; tenant authorization, durable extraction and the remaining COMP-002 acceptance criteria are still open.
