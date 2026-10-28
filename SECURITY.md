# Security and trust boundaries

This is a non-production reference under development. Security controls described in the plan require implementation evidence.

Treat customer input, PDFs, retrieved text, memory content, and tool outputs as untrusted data. Backend identity, service credentials, and reviewed business/governance policy define authority. No model output may choose arbitrary tenants, database names, credentials, filesystem paths, or action permissions.

Protect tenant/ACL boundaries across CRUD, Search, Vector Search, cache, exports, and evaluation databases. Restrict each service to its owned collections. Keep provider keys and database URIs with credentials out of source, browser bundles, logs, fixtures, and issue reports. Use synthetic customer data and disable raw-audio retention by default.

Critical review areas: prompt injection into tools, stale-source acceptance, SSRF/file-path handling during ingestion, replayed approvals, duplicate financial effects, cross-tenant cache hits, unbounded retries, and inappropriate public traces. See [best practices](docs/BEST_PRACTICES.md) for detailed controls.

Do not report credentials or customer data in public issues. Use GitHub private vulnerability reporting if the repository owner has enabled it; otherwise request a private reporting channel from the owner without publishing exploit details or secrets. No private reporting endpoint or GitHub security setting has been verified in this session.
