# Caches, persistence and optimization

Chrome local storage holds popup preferences and identity/license-related fields (`js/content/popup_script.js`, `background.js`). The database worker contains SQLite and OPFS persistence plus explicit create/remove/import/export actions. Neither is an incidental cache that a documentation task may clear.

The scanner exposes delays, timeout/retry/refresh controls. Their names and HTML inputs do not establish optimum values or observed throughput; no benchmark was run. Treat saved settings and effective runtime initialization separately from HTML defaults.

The requested retrieval store is derived and local. It records source hashes and complete chunk ranges, and a build can reuse identical-content embeddings without merging source identities. Freshness compares the complete scoped corpus rather than relying on a timestamp. No watcher or scheduled rebuild is installed.
