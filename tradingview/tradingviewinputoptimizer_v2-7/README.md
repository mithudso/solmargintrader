# TradingView Input Optimizer bundle

This Chrome Manifest V3 extension automates strategy and indicator input searches on TradingView and stores result tables locally. The directory is named `tradingviewinputoptimizer_v2-7`, but `manifest.json` and the popup identify version **2.3.11**. The English locale describes it as “Optimize tradingview strategies & indicators.”

This is an upstream, largely obfuscated browser bundle inside an ignored directory of solmargintrader. Its code and third-party dependencies remain unchanged. Only the documentation is tracked in the parent repository; cloning the parent alone does not supply the extension. No extension execution, license validation or chart interaction was performed for this documentation pass.

## Start here

Read [installation](docs/INSTALLATION.md) for manual browser loading and limits, [architecture](docs/ARCHITECTURE.md) for the browser contexts, [development](docs/DEVELOPMENT.md) for safe changes, and [testing](docs/TESTING.md) for what has actually been checked. The [known issues](docs/known-issues.md) distinguish observed gaps from unverified behavior.

## Documentation

- [Components](docs/COMPONENTS.md), [file overview](docs/codebase-overview.md), [onboarding](docs/onboarding.md), [requirements](docs/requirements.md).
- [Security](docs/SECURITY.md), [integrations](docs/integrations-and-assumptions.md), [external calls](docs/external-calls.md), [logging](docs/logging.md), [caches and storage](docs/caching-and-optimization.md).
- [Retrieval indexes](docs/RETRIEVAL.md), [MCP boundary](docs/MCP.md), [retrieval runbook](docs/runbooks/retrieval.md), [documentation audit](docs/repo-bootstrap-audit-2026-11-08.md).
- [Agent guidance](CLAUDE.md), [contributing](CONTRIBUTING.md), [prompt history](prompts.md), [continuation record](memory.md).

## Source of truth

The manifest defines browser wiring and permissions. The supplied JavaScript defines behavior; these docs describe static inspection and do not certify runtime correctness, performance or security. Vendored package scripts are not an extension build/install workflow. Preserve each vendor license; this documentation pass grants no new redistribution rights.
