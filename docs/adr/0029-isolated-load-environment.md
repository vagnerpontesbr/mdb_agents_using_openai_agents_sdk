# ADR-0029: Explicit isolated load environment

- Status: Implemented locally; approved resources applied and bounded Atlas role/domain checks passed
- Owner: Telecom demo maintainer
- Refines: [ADR-0017](0017-two-cluster-memory-boundary.md), [ADR-0027](0027-bounded-knowledge-evaluation-cache.md)

## Context

Phase 8 requires real ingestion/cache tests without writing to the demo corpus.
Existing repository constructors allow only demo database names. Changing a global
name or weakening the name check would risk accidental cross-environment writes.

## Decision

Keep demo defaults and add a keyword-only, strictly boolean `load_environment`
constructor option for MongoIngestion, MongoKnowledgeReader, MongoCandidateCache and MongoKnowledgeAuthority.
Only trusted test-process construction can select it; no HTTP payload, tenant value,
user role or model argument selects the environment. A load process accepts only
`telecom_load_ingestion` or `telecom_load_knowledge`, as applicable, and rejects demo
names. A default process rejects load names. Arbitrary database names remain rejected.

The [exact proposal](../../compatibility/phase8-resource-plan.json) creates eight
collections across those two databases on the existing OpenAI-SDK cluster, reusing
the authoritative schema/index generators. Four new collection-scoped identities
separate knowledge reading, knowledge publication, ingestion and cache writes.
No existing role is broadened. No document is inserted by provisioning.

The apply script defaults to a zero-call dry run. A live application requires the
reviewed plan SHA-256, checks source/plan equality and existing resource drift,
and stores credentials only in ignored mode-0600 `.env.phase8`. It does not change
ClusterDemoTelco, Engine policy/memory/deployment, Atlas tier or demo data.

## Alternatives considered

Using demo namespaces would invalidate the isolated-load requirement. A universal
arbitrary database parameter would weaken fail-closed configuration. A new cluster
would add cost and operations without evidence that physical separation is needed.

## Consequences and tradeoffs

Logical namespaces and database roles do not isolate shared Atlas CPU, storage or
search resources. Tests must remain bounded and monitor contention. Database roles
and tenant/ACL checks require separate positive and negative live controls.
The constructor controls are local changes; the existing hosted deployment retains
its published code. No load-enabled HTTP configuration or hosted deployment is added.

## Validation

Parameterized tests verify default/load acceptance, cross-environment rejection,
arbitrary-name rejection and nonboolean selection rejection for all four adapters.
The proposal and apply dry run make no external calls. Remote schema/index readiness and 208 role controls passed after requester approval.
Bounded worker and cache-revocation controls passed; bounded sustained acceptance passed. The requester excluded production-capacity and pricing proof from demo acceptance; see the final decision in OPS-001.
[OPS-001](../tasks/OPS-001-RESILIENCE.md) records measurements and remaining gates.

## Revisit trigger

Revisit if measured shared-cluster contention requires physical isolation, if more
application environments are needed, or if deployment configuration becomes dynamic.
