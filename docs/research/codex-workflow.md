# Repository practices for Codex

Consulted source: [official AGENTS.md documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

The documentation confirms hierarchical discovery of AGENTS.md instructions and directory-specific guidance. These are asset recommendations, not mandatory product requirements:

- Create concise root AGENTS.md guidance covering architecture, setup, execution, validation, and boundaries.
- Add local backend/frontend instructions only when useful.
- Document real commands for uv, Python builds, linting, types, tests, and frontend builds. Do not present planned commands as implemented.
- Record architecture decisions and compatibility gates with sources and verification dates.
- Commit uv.lock, the Python version, and the frontend lockfile. CI must not implicitly update locks.
- Work in small vertical deliveries with clear contracts, demonstrable behavior, and acceptance criteria.
- Test routing, authorization, tenant isolation, memory, caching, and retrieval. Separate deterministic CI from credentialed integration suites.
- Keep secrets and personal data out of traces and fixtures; use synthetic examples.
- Never invent service APIs. Label unverified integrations explicitly.
- Focus reviews on contracts, security, retrieval quality, and observable behavior; automate formatting.

This planning stage does not modify global Codex settings or add approval requirements to already authorized work.
