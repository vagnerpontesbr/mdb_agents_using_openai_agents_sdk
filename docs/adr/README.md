# Architecture Decision Records

Status: ADRs 0001–0009 are proposed. ADRs 0010–0011 record explicit user-selected architecture; implementation verification remains pending. ADRs 0012–0014 define the authored Codex repository foundation; remote/runtime verification remains pending. None claims a verified provider integration.

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
| [ADR-0010](0010-mongodb-integrated-data-platform.md) | Use MongoDB for operational data, Search, and Vector Search | Selected; verification pending |
| [ADR-0011](0011-single-cluster-logical-isolation.md) | Use one Atlas cluster with service-owned databases and collections | Selected; verification pending |
| [ADR-0012](0012-codex-repository-instructions.md) | Use concise repository instructions as Codex working context | Foundation selected; verification scoped |
| [ADR-0013](0013-evidence-driven-delivery.md) | Deliver bounded tasks with explicit acceptance evidence | Foundation selected; verification scoped |
| [ADR-0014](0014-layered-repository-validation.md) | Automate repository checks and add validation layers with implementation | Foundation selected; verification scoped |
