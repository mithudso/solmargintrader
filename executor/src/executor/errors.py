"""Error types. Every refusal carries a code that maps to the envelope `error.code`."""

from __future__ import annotations

# Envelope error codes. The first five are the same set soltui's registry uses; `refused` and `ambiguous` are
# executor-specific, because a caller driving real money must tell "a rail said no" from "the venue broke" from
# "a send may or may not have landed".
CODES = ("bad_params", "unknown_command", "forbidden", "refused", "failed", "timeout", "ambiguous")


class ExecutorError(Exception):
    """A failure that maps to an envelope error."""

    code = "failed"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        if code is not None:
            if code not in CODES:
                raise ValueError(f"unknown error code {code!r}")
            self.code = code
        self.message = message


class BadParams(ExecutorError):
    code = "bad_params"


class Refused(ExecutorError):
    """A rail, gate or verifier said no. Nothing was signed or sent."""

    code = "refused"

    def __init__(self, problems: list[str] | str):
        self.problems = [problems] if isinstance(problems, str) else list(problems)
        super().__init__("refused: " + "; ".join(self.problems))


class Forbidden(ExecutorError):
    code = "forbidden"


class Ambiguous(ExecutorError):
    """A transaction may or may not have landed. It is journalled as `unknown` and never retried."""

    code = "ambiguous"


class RpcError(ExecutorError):
    code = "failed"


class WalletError(ExecutorError):
    code = "failed"


class SendRejected(RpcError):
    """The node answered a send with a JSON-RPC error (for example a failed preflight). The transaction was not
    accepted, so this outcome is definite, unlike a transport error or timeout, which is ambiguous."""


class HttpError(ExecutorError):
    """An HTTP error status from a service. `status` lets callers retry rate limits (429) only."""

    code = "failed"

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status
