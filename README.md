# Telecom Agent Reference Asset

A planned, adaptable customer-service reference built around OpenAI Agents SDK, MongoDB, Voyage AI, Python managed by uv, and React.

**Current status: planning and local repository foundation.** Codex instructions, task/review templates, and an offline repository checker are present. No application, dependency lock, provider integration, or deployment has been completed.

The design includes a supervisor and financial, technical, and sales specialists; chat and browser voice; MongoDB Agent Engine memory; contextual PDF retrieval; native hybrid rank fusion; semantic caching; and MongoDB Auto Embedding wherever supported. Everything is in English.

## Planning documents

- [Implementation plan and acceptance criteria](initial_plan.md)
- [Requirements and latest user decisions](docs/REQUIREMENTS.md)
- [Architecture Decision Records](docs/adr/README.md)
- [Data architecture, memory boundary and Twelve-Factor mapping](docs/DATA_ARCHITECTURE.md)
- [Best Practices](docs/BEST_PRACTICES.md)
- [Document governance and risk scoring](docs/DOCUMENT_GOVERNANCE.md)
- [Outdated-document RAG demonstration](examples/telecom/governance/README.md)
- [Service boundaries and stress tests](docs/SCALABILITY_AND_STRESS_TESTS.md)
- [OpenAI Agents SDK assessment](docs/research/openai-sdk.md)
- [MongoDB Agent Engine, memory, and Auto Embedding assessment](docs/research/mongodb-engine.md)
- [Voyage, ingestion, and application architecture](docs/research/asset-architecture.md)
- [Voice architecture](docs/research/voice-agents.md)
- [Codex repository workflow](docs/research/codex-workflow.md)

The implementation starts with compatibility proofs. In particular, the documented Agent Engine memory integration path does not establish native hosted execution compatibility with the OpenAI Agents SDK. The plan preserves both requirements and makes that integration a validation gate.

## Contributor entry points

- [Codex repository instructions](AGENTS.md)
- [Contribution workflow and current checks](CONTRIBUTING.md)
- [Implementation backlog](docs/tasks/README.md)
- [Security boundaries](SECURITY.md)
- [Phase 0 compatibility work and current blockers](docs/compatibility/PHASE_0.md)
- [GitHub setup status and runbook](docs/runbooks/REPOSITORY_SETUP.md)

Run `python3 scripts/check_repository.py` from the project root. This validates repository structure and local documentation links, not application behavior.

Phase 0 is in progress: Python 3.15.2 runs locally and 16 diagnostic tests pass. The user selected the official Voyage HTTP API instead of the incompatible Python SDK, preserving the chosen models ([ADR-0015](docs/adr/0015-voyage-http-python315.md)). Full dependency and live provider compatibility remain unverified; no application lock is approved yet.
