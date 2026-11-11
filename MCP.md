# MCP and repository tooling

This repository does not ship an MCP server, register MCP tools, or require a repository
`.mcp.json`. The Chrome extension, its CLI, and local HTTP API call the same command
registry in `extension/src/core/commands.js`. They are not MCP transports.

Development agents may have machine-wide MCP connections such as Stele and the global
AI hub. Those connections are configured outside this repository. Do not copy machine
credentials or host-specific server settings into tracked editor files.

## Retrieval without a connector

```bash
python3 index/build.py --check
python3 index/search.py --text "fee_bps"
python3 index/search.py --file extension/src/core/risk.js
```

The existing keyword index is local/offline. Semantic search is optional and needs its
separate vectors/backend; see `index/README.md`. A missing connector does not authorize
starting inference, indexing or a daemon during ordinary repository startup.

The active environment may provide Stele task/knowledge tools. Follow the project workflow
when they are configured; never create or bind a different Stele project automatically.
