# Logging

Visible application code uses browser `console.log`, `warn` and `error` across the background, popup, scanner, report and database worker. Several files contain obfuscation wrappers that also replace/bind console methods. No centralized structured error store, stable event schema, retention policy or automated log assertion suite is established here.

License/popup/worker code contains diagnostic logging and message payload logging. Treat console output, exports and browser profiles as potentially sensitive: registration identity and results pass through those contexts. This pass does not certify redaction or add logging. Useful future acceptance evidence includes the exact context, command, browser state, failure and outcome without real credentials or private results.

Retrieval generation writes an external build log/checkpoint and manifest with file hashes, chunk counts, model and verification results. Those are local artifacts; they do not alter application logging.
