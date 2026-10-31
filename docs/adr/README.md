# Architecture Decision Records

Status: ADRs 0001–0009 describe proposed full-application architecture. Later
records capture explicit user decisions and bounded Phase 0 acceptance; ADR-0017
supersedes ADR-0011. [Phase 0](../compatibility/PHASE_0.md) owns the detailed runtime
evidence, and [publication status](../runbooks/REPOSITORY_SETUP.md) owns Git/PR/CI
verification. ADR acceptance is not a claim of full application implementation.

Each ADR records context, decision, alternatives, consequences, and validation. Assign an accountable owner when implementation starts. Change status to accepted only after review; preserve history and use a superseding ADR for a material reversal.

| ADR | Decision | Status |
|---|---|---|
| [ADR-0001](0001-framework-platform.md) | Separate agent framework from agent platform | Proposed |
| [ADR-0002](0002-service-boundaries.md) | Separate workloads at justified service boundaries | Proposed |
| [ADR-0003](0003-memory-state.md) | Separate conversation, durable memory, and execution state | Proposed |
| [ADR-0004](0004-embedding-retrieval.md) | Prefer native Auto Embedding while preserving contextual retrieval | Proposed |
| [ADR-0005](0005-document-governance.md) | Govern document validity independently of retrieval relevance | Proposed |
| [ADR-0006](0006-evaluation-truth.md) | Separate RAG faithfulness from time-valid business correctness | Proposed |
| [ADR-0007](0007-budgets-guardrails.md) | Enforce budgets and authorization outside model prompts | Proposed |
| [ADR-0008](0008-voice-channel.md) | Reuse the agent workflow across chat and browser voice | Proposed |
| [ADR-0009](0009-deterministic-responses.md) | Constrain generation and render critical responses deterministically | Proposed |
| [ADR-0010](0010-mongodb-integrated-data-platform.md) | Use MongoDB for operational data, Search, and Vector Search | Selected; bounded Phase 0 evidence recorded |
| [ADR-0011](0011-single-cluster-logical-isolation.md) | Use one Atlas cluster with service-owned databases and collections | Superseded by ADR-0017 |
| [ADR-0012](0012-codex-repository-instructions.md) | Use concise repository instructions as Codex working context | Foundation selected; verification scoped |
| [ADR-0013](0013-evidence-driven-delivery.md) | Deliver bounded tasks with explicit acceptance evidence | Foundation selected; verification scoped |
| [ADR-0014](0014-layered-repository-validation.md) | Automate repository checks and add validation layers with implementation | Foundation selected; verification scoped |
| [ADR-0015](0015-voyage-http-python315.md) | Preserve Python 3.15 and use the official Voyage HTTP API | Selected; bounded Phase 0 evidence recorded |
| [ADR-0016](0016-split-compatibility-environments.md) | Separate locked agent and CPU ingestion compatibility environments | Selected; local verification scoped |
| [ADR-0017](0017-two-cluster-memory-boundary.md) | Separate application and shared Engine memory clusters | Approved; bounded cluster/isolation controls passed |

| [ADR-0018](0018-engine-feature-precedence.md) | Prefer Engine for overlapping platform features; retain SDK orchestration | Selected; bounded custom hosted integration passed |
| [ADR-0019](0019-requester-approval-memory-retention.md) | Requester self-approval and thirty-day memory retention | Requester admission passed; native expurgo accepted without further proof |

| [ADR-0020](0020-demo-email-password-auth.md) | Demo email/password login, admin-only registration and initial administrator | Selected by user; local contract implemented |
| [ADR-0021](0021-demo-semantic-episodic-continuity.md) | Limit demo continuity to validated Engine semantic/episodic memory | Selected by user; chronological restoration outside demo scope |
| [ADR-0022](0022-demo-private-engine-cli-identity.md) | Retain private operator Engine CLI identity in the loopback demo backend | Selected by user; demo-only privilege exception |
| [ADR-0023](0023-quiet-environment-demo-voice.md) | Limit demo voice to quiet environments with bounded manual retries | Selected by user; microphone/listening proof passed |

| [ADR-0024](0024-phase-one-application-boundaries.md) | Phase 1 identity application, process ownership and typed response boundary | Implemented; validation in FND-003 |

| [ADR-0025](0025-phase-two-journey.md) | Bounded SDK supervisor/specialists, native review and chained browser voice | Bounded hosted and browser acceptance passed |

| [ADR-0026](0026-governed-knowledge-publication.md) | Owner-authorized native review and domain publication of governed PDFs | Selected; bounded Phase 4 evidence recorded |

| [ADR-0027](0027-bounded-knowledge-evaluation-cache.md) | Bounded contextual candidate cache and isolated quality evaluation | Bounded Phase 5 acceptance passed |

| [ADR-0028](0028-mit-automated-demo-handoff.md) | MIT license and accepted automated demo handoff | Accepted by requester; Phase 6 and correction CI passed |
