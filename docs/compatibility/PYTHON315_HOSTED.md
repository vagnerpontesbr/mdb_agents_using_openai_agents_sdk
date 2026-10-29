# Python 3.15.2 hosted-build experiment

This is a COMP-003 compatibility experiment, not a supported Engine image override. The original hosted build could not discover Python 3.15.2. Keep the exact target and the dependency lock; do not treat the following generic lockfile error as proof that the lock is stale.

## Interpreter and provenance

Astral's [20261026 python-build-standalone release](https://github.com/astral-sh/python-build-standalone/releases/tag/20261026) publishes `cpython-3.15.2+20261026-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz`, SHA-256 `7b03163a980c607ba8194709d4a4086735a7a9c488cc475b098157306927b36b`. The checksum was verified before extraction. Python 3.15.2, x86_64 and OpenSSL imports were verified inside Linux. The locally tested uv catalog lacked this final release, despite the downloadable artifact being available.

The experiment includes the interpreter under `.runtime-python/python` in the source archive and supplies `.python-version` with `/app/.runtime-python/python/bin/python3.15`. That is an explicit interpreter path accepted by uv, matching Engine's observed `/app` build directory. It does not modify global uv settings or change the Python version. It remains specific to that platform layout and Linux architecture.

## Source staging and size limit

[prepare_hosted_invoice.py](../../scripts/prepare_hosted_invoice.py) creates a fresh stage from an allowlist: package manifests, the lock, agent.yaml and Python source. It rejects reused output directories and unverified interpreter archives. It does not upload or deploy. Environment files, credentials and caches are not copied.

The full interpreter bundle installed successfully in local Linux but its remote archive was rejected before CodeBuild because it exceeded the platform's 52,428,800-byte decompressed limit. The compact profile contains 49,166,913 bytes of regular files at the tested revision and fits that limit. It omits Tk/IDLE, terminfo, pip/ensurepip, C development headers and the embedding libpython shared library. `ldd` confirmed the Python executable does not link to that shared library. No binary is patched, hidden in a nested archive or recompressed to evade the limit. The regular runtime files remain available to source validation.

This is a noninteractive runtime for the bounded HTTP invoice probe. It is not a general Python development distribution: embedding, Tk, bootstrapping pip and compiling native extensions against its headers are unsupported. uv installed the actual locked dependencies, including a PyYAML build, with this profile. Any added dependency/workload requires revalidation. Runtime licenses and retained files remain in the staging artifact; large binaries are ignored artifacts, not repository source.

## Reproduce local Linux proof

Download the exact release artifact above to a private temporary path, then run from the repository root with a new output directory:

```bash
python3 scripts/prepare_hosted_invoice.py \
  --output artifacts/compatibility/hosted-invoice-python315-compact \
  --python-archive /tmp/telecom-python315-linux-amd64.tar.gz \
  --compact-runtime
docker build --platform linux/amd64 \
  -f compatibility/openai_engine_adapter/Dockerfile.python315-proof \
  -t telecom-python315-compact:local \
  artifacts/compatibility/hosted-invoice-python315-compact
```

The [diagnostic Dockerfile](../../compatibility/openai_engine_adapter/Dockerfile.python315-proof) pins Debian and uv image digests. uv 0.11.21 runs `uv sync --frozen --no-dev` with automatic Python downloads disabled. Both full and compact profiles passed all 22 adapter/loader/provider tests under Docker Desktop x86_64 emulation on macOS ARM64. Tests use Engine/HTTP transport doubles; this is Linux compatibility evidence, not live Engine policy or provider execution.

## Remote outcomes

- Original build `bld_01M621HKZWQ2Q13QCGQM15M7ST`: failed to find the interpreter.
- Full bundle `bld_01M6227MJW46XNDZC99EPK41F8`: archive uploaded, then rejected by the decompressed size limit; CodeBuild did not start.
- Compact bundle `bld_01M622CNYJW9R30TVZQ0Q36DQF`: archive accepted; BUILD log explicitly selected CPython 3.15.2 from the bundled path and resolved 56 packages. Final image/deployment status is tracked in [COMP-003](../tasks/COMP-003-HOSTED.md).

[Portable Linux evidence](../../compatibility/python315-linux-evidence.json) records artifact provenance, source hashes and validation scope. This experiment does not change shared Anthropic memory, credentials, clusters, policies or existing geo-intelligence-network deployments.
