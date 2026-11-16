"""Pinned Jupiter CLI calls with bounded pipes and owned process teardown."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import os
import re
import selectors
import signal
import subprocess
import tempfile
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

APPROVED_BINARY = Path("/opt/homebrew/bin/jup")
APPROVED_ENTRYPOINT = Path("/opt/homebrew/lib/node_modules/@jup-ag/cli/dist/index.js")
CLI_VERSION = "0.10.1"
CLI_SHA256 = "226db8ce76ca60b44629676a9cea0c699b934240dba200fefcf6f8c931f0ea94"
SAFE_PATH = "/opt/homebrew/bin:/usr/bin:/bin"
MAX_INPUT = 64 * 1024
MAX_STDOUT = 1024 * 1024
MAX_STDERR = 64 * 1024
MAX_TRANSACTION_BYTES = 1232
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
SECRET_FIELDS = frozenset(
    {
        "privatekey",
        "secretkey",
        "seed",
        "seedphrase",
        "mnemonic",
        "apikey",
        "authorization",
        "bearertoken",
        "accesstoken",
        "refreshtoken",
    }
)


class AdapterError(RuntimeError):
    """A safe diagnostic; ambiguous means an effect requires reconciliation."""

    def __init__(self, code, *, ambiguous=False, returncode=None, stderr=b""):
        super().__init__(code)
        self.code = code
        self.ambiguous = ambiguous
        self.returncode = returncode
        self.stderr_bytes = len(stderr)
        self.stderr_sha256 = hashlib.sha256(stderr).hexdigest() if stderr else None


def _timeout(value):
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or not 0 < value <= 60
    ):
        raise AdapterError("invalid_process_timeout")
    return float(value)


def _environment():
    # In particular, do not inherit NODE_OPTIONS, preload settings or shell hooks.
    result = {"PATH": SAFE_PATH, "LC_ALL": "C", "NO_COLOR": "1", "TERM": "dumb"}
    for name in ("HOME", "TMPDIR", "SSL_CERT_FILE", "SSL_CERT_DIR"):
        if name in os.environ:
            result[name] = os.environ[name]
    return result


def _cleanup(process):
    """Kill only while the unreaped direct child still reserves this group ID."""
    try:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            # macOS can deny signalling a zombie-only group. Reap and probe,
            # but never send a signal after the group ID could be recycled.
            process.kill()
            process.wait(timeout=1)
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                pass
            else:
                raise AdapterError("process_group_cleanup_failed") from None
        process.wait(timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        raise AdapterError("process_group_cleanup_failed") from None
    finally:
        process.stdout.close()
        process.stderr.close()


def _bounded_process(
    argv,
    *,
    timeout,
    payload=b"",
    stdout_limit=MAX_STDOUT,
    stderr_limit=MAX_STDERR,
    ambiguous=False,
):
    """Drain both pipes incrementally; a closed pipe does not prove child exit."""
    timeout = _timeout(timeout)
    if not isinstance(payload, bytes) or len(payload) > MAX_INPUT:
        raise AdapterError("process_input_limit")
    if not hasattr(os, "waitid") or not hasattr(os, "WNOWAIT"):
        raise AdapterError("nonreaping_wait_unavailable")
    with tempfile.TemporaryFile() as source:
        source.write(payload)
        source.seek(0)
        try:
            process = subprocess.Popen(
                argv,
                stdin=source,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=_environment(),
                close_fds=True,
                start_new_session=True,
            )
        except OSError:
            raise AdapterError("process_start_failed") from None
        streams = {process.stdout: bytearray(), process.stderr: bytearray()}
        limits = {process.stdout: stdout_limit, process.stderr: stderr_limit}
        deadline = time.monotonic() + timeout
        error = None
        try:
            with selectors.DefaultSelector() as selector:
                for stream in streams:
                    selector.register(stream, selectors.EVENT_READ)
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise AdapterError("process_timeout", ambiguous=ambiguous)
                    for key, _ in selector.select(min(0.05, remaining)):
                        chunk = os.read(key.fileobj.fileno(), 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        streams[key.fileobj].extend(chunk)
                        if len(streams[key.fileobj]) > limits[key.fileobj]:
                            raise AdapterError(
                                "process_output_limit", ambiguous=ambiguous
                            )
            while (
                os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOWAIT | os.WNOHANG)
                is None
            ):
                if time.monotonic() >= deadline:
                    raise AdapterError("process_timeout", ambiguous=ambiguous)
                time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        except AdapterError as caught:
            error = caught
        except (OSError, ValueError):
            error = AdapterError("process_transport_failed", ambiguous=ambiguous)
        finally:
            try:
                _cleanup(process)
            except AdapterError as caught:
                error = AdapterError(caught.code, ambiguous=ambiguous)
        stderr = bytes(streams[process.stderr])
        if error is not None:
            raise AdapterError(
                error.code,
                ambiguous=error.ambiguous,
                returncode=process.returncode,
                stderr=stderr,
            ) from None
        return process.returncode, bytes(streams[process.stdout]), stderr


def _invalid_constant(value):
    raise ValueError("nonfinite_json")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _clean_json(value, *, refuse_secrets=False, depth=0):
    if depth > 30:
        raise ValueError("json_nesting_limit")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite_json")
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("json_object_key_requires_string")
            secret = re.sub("[^a-z]", "", key.lower()) in SECRET_FIELDS
            if secret and refuse_secrets:
                raise ValueError("secret_payload_refused")
            result[key] = (
                "[REDACTED]"
                if secret
                else _clean_json(item, refuse_secrets=refuse_secrets, depth=depth + 1)
            )
        return result
    if isinstance(value, list):
        return [
            _clean_json(item, refuse_secrets=refuse_secrets, depth=depth + 1)
            for item in value
        ]
    return value


def run_json(argv, *, timeout, payload=b"", ambiguous=False):
    status, stdout, stderr = _bounded_process(
        argv, timeout=timeout, payload=payload, ambiguous=ambiguous
    )
    if status != 0:
        code = "process_nonzero_exit"
        if argv and argv[0] == str(APPROVED_BINARY):
            try:
                error = json.loads(
                    stdout.decode("utf-8"),
                    parse_constant=_invalid_constant,
                    object_pairs_hook=_unique_object,
                )
                if error == {
                    "error": "Insufficient funds to execute the request. Please check your SOL or token balance."
                }:
                    code = "jupiter_insufficient_funds"
            except (UnicodeError, ValueError, TypeError, RecursionError):
                pass
        raise AdapterError(
            code,
            ambiguous=ambiguous,
            returncode=status,
            stderr=stderr,
        )
    try:
        result = json.loads(
            stdout.decode("utf-8"),
            parse_constant=_invalid_constant,
            object_pairs_hook=_unique_object,
        )
        if not isinstance(result, (dict, list)):
            raise TypeError("json_object_or_array_required")
        return _clean_json(result)
    except (UnicodeError, ValueError, TypeError, RecursionError):
        raise AdapterError(
            "invalid_process_json",
            ambiguous=ambiguous,
            returncode=status,
            stderr=stderr,
        ) from None


def collateral_amount(value):
    try:
        if isinstance(value, bool) or len(str(value)) > 128:
            raise ValueError("invalid_amount")
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < Decimal(10) or amount.adjusted() > 18:
            raise ValueError("invalid_amount")
        if amount != amount.quantize(Decimal("0.000001")):
            raise ValueError("amount_exceeds_usdc_precision")
    except (InvalidOperation, ValueError):
        raise AdapterError(
            "collateral_requires_finite_usdc_amount_at_least_10"
        ) from None
    return format(amount.normalize(), "f")


def _key_arguments(key_name):
    if key_name is None:
        return []
    if (
        not isinstance(key_name, str)
        or re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", key_name) is None
    ):
        raise AdapterError("invalid_named_cli_key")
    return ["--key", key_name]


def _public_key_bytes(value, code):
    if (
        not isinstance(value, str)
        or not 32 <= len(value) <= 44
        or any(char not in BASE58_ALPHABET for char in value)
    ):
        raise AdapterError(code)
    number = 0
    for char in value:
        number = number * 58 + BASE58_ALPHABET.index(char)
    raw = b"\0" * (len(value) - len(value.lstrip("1"))) + number.to_bytes(
        (number.bit_length() + 7) // 8, "big"
    )
    if len(raw) != 32:
        raise AdapterError(code)
    return raw


def _wallet_metadata(result, *, key_name=None):
    if not isinstance(result, list) or any(
        not isinstance(row, dict) or type(row.get("active")) is not bool
        for row in result
    ):
        raise AdapterError("invalid_cli_wallet_metadata")
    selected = [
        row
        for row in result
        if (row["active"] if key_name is None else row.get("name") == key_name)
    ]
    if len(selected) != 1:
        raise AdapterError(
            "cli_requires_exactly_one_active_wallet"
            if key_name is None
            else "cli_requires_exactly_one_named_wallet"
        )
    row = selected[0]
    address, name, kind = (row.get(key) for key in ("address", "name", "type"))
    _public_key_bytes(address, "invalid_cli_wallet_metadata")
    if (
        not isinstance(name, str)
        or not 1 <= len(name) <= 128
        or any(ord(char) < 32 for char in name)
        or not isinstance(kind, str)
        or not 1 <= len(kind) <= 64
    ):
        raise AdapterError("invalid_cli_wallet_metadata")
    return {"address": address, "name": name, "type": kind, "active": row["active"]}


def _transaction_layout(serialized):
    """Parse canonical legacy/v0 wire bytes without changing or signing them."""
    code = "invalid_serialized_solana_transaction"
    if (
        not isinstance(serialized, str)
        or not serialized
        or len(serialized) > 4 * ((MAX_TRANSACTION_BYTES + 2) // 3)
    ):
        raise AdapterError(code)
    try:
        raw = base64.b64decode(serialized, validate=True)
    except (ValueError, binascii.Error):
        raise AdapterError(code) from None
    if (
        not raw
        or len(raw) > MAX_TRANSACTION_BYTES
        or base64.b64encode(raw).decode("ascii") != serialized
    ):
        raise AdapterError(code)
    offset = 0

    def take(count):
        nonlocal offset
        if count < 0 or offset + count > len(raw):
            raise AdapterError(code)
        value = raw[offset : offset + count]
        offset += count
        return value

    def shortvec():
        value = 0
        for index in range(3):
            byte = take(1)[0]
            if (index == 2 and byte > 3) or (index and byte == 0):
                raise AdapterError(code)
            value |= (byte & 0x7F) << (7 * index)
            if byte < 0x80:
                return value
        raise AdapterError(code)

    signature_count = shortvec()
    if not 1 <= signature_count <= 127:
        raise AdapterError(code)
    signatures = tuple(take(64) for _ in range(signature_count))
    message_start = offset
    first = take(1)[0]
    versioned = first & 0x80
    if versioned and first != 0x80:
        raise AdapterError(code)
    header = take(3) if versioned else bytes([first]) + take(2)
    account_count = shortvec()
    required, readonly_signed, readonly_unsigned = header
    if (
        required != signature_count
        or not required <= account_count <= 256
        or readonly_signed >= required
        or readonly_unsigned > account_count - required
    ):
        raise AdapterError(code)
    accounts = tuple(take(32) for _ in range(account_count))
    if len(set(accounts)) != account_count:
        raise AdapterError(code)
    take(32)  # Recent blockhash; its value is verified by the service contract.
    instruction_indexes = []
    for _ in range(shortvec()):
        program_index = take(1)[0]
        if program_index >= account_count:
            raise AdapterError(code)
        instruction_indexes.extend(take(shortvec()))
        take(shortvec())
    loaded_count = 0
    if versioned:
        for _ in range(shortvec()):
            take(32)
            for _ in range(2):
                count = shortvec()
                take(count)
                loaded_count += count
    total_accounts = account_count + loaded_count
    if (
        offset != len(raw)
        or total_accounts > 256
        or any(index >= total_accounts for index in instruction_indexes)
    ):
        raise AdapterError(code)
    return raw[message_start:], signatures, accounts[:required]


class JupiterCLI:
    def __init__(self, binary=str(APPROVED_BINARY), timeout=20):
        if Path(binary) != APPROVED_BINARY:
            raise AdapterError("unapproved_jupiter_cli_binary")
        self.binary = str(APPROVED_BINARY)
        self.timeout = _timeout(timeout)

    def identity(self):
        try:
            entrypoint = APPROVED_BINARY.resolve(strict=True)
            if entrypoint != APPROVED_ENTRYPOINT:
                raise AdapterError("jupiter_cli_entrypoint_changed")
            with entrypoint.open("rb") as stream:
                body = stream.read(16 * 1024 * 1024 + 1)
            if (
                len(body) > 16 * 1024 * 1024
                or hashlib.sha256(body).hexdigest() != CLI_SHA256
            ):
                raise AdapterError("jupiter_cli_hash_mismatch")
        except OSError:
            raise AdapterError("jupiter_cli_missing") from None
        status, stdout, stderr = _bounded_process(
            [self.binary, "--version"], timeout=min(3, self.timeout), stdout_limit=128
        )
        if (
            status != 0
            or stdout.decode("utf-8", errors="replace").strip() != CLI_VERSION
        ):
            raise AdapterError(
                "jupiter_cli_version_mismatch", returncode=status, stderr=stderr
            )
        return {
            "version": CLI_VERSION,
            "entrypoint_sha256": CLI_SHA256,
            "binary": self.binary,
        }

    def _open(self, asset, side, collateral_usd, *, dry_run, key_name=None):
        if asset not in ("BTC", "SOL", "ETH"):
            raise AdapterError("unsupported_jupiter_cli_asset_BTC_SOL_ETH_only")
        if side not in ("long", "short"):
            raise AdapterError("invalid_position_side")
        amount = collateral_amount(collateral_usd)
        key_arguments = _key_arguments(key_name)
        started = time.monotonic()
        if not dry_run:
            self.identity()
        argv = [
            self.binary,
            "-f",
            "json",
            "perps",
            "open",
            "--asset",
            asset,
            "--side",
            side,
            "--amount",
            amount,
            "--input",
            "USDC",
            "--leverage",
            "10",
        ]
        argv.extend(key_arguments)
        if dry_run:
            argv.append("--dry-run")
        remaining = self.timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise AdapterError("identity_deadline_exceeded")
        result = run_json(argv, timeout=remaining, ambiguous=not dry_run)
        if not isinstance(result, dict):
            raise AdapterError("invalid_position_result", ambiguous=not dry_run)
        return result

    def preview(self, asset, side, collateral_usd, *, key_name=None):
        return self._open(asset, side, collateral_usd, dry_run=True, key_name=key_name)

    def execute(self, asset, side, collateral_usd, *, key_name=None):
        return self._open(asset, side, collateral_usd, dry_run=False, key_name=key_name)

    def positions(self, *, key_name=None):
        return run_json(
            [
                self.binary,
                "-f",
                "json",
                "perps",
                "positions",
                *_key_arguments(key_name),
            ],
            timeout=self.timeout,
        )

    def wallet(self, *, key_name=None):
        """Return public metadata for the active identity or one exact named key."""
        _key_arguments(key_name)
        result = run_json(
            [self.binary, "-f", "json", "keys", "list"], timeout=self.timeout
        )
        return _wallet_metadata(result, key_name=key_name)

    def sign_transaction(self, serialized_tx, *, key_name):
        """Sign only; the caller must verify the service intent before transmission."""
        if key_name is None:
            raise AdapterError("invalid_named_cli_key")
        key_arguments = _key_arguments(key_name)
        message, signatures, signers = _transaction_layout(serialized_tx)
        started = time.monotonic()
        self.identity()

        def remaining():
            budget = self.timeout - (time.monotonic() - started)
            if budget <= 0:
                raise AdapterError("signing_deadline_exceeded")
            return budget

        wallet = _wallet_metadata(
            run_json([self.binary, "-f", "json", "keys", "list"], timeout=remaining()),
            key_name=key_name,
        )
        public_key = _public_key_bytes(wallet["address"], "invalid_cli_wallet_metadata")
        if public_key not in signers:
            raise AdapterError("named_wallet_is_not_a_required_transaction_signer")
        signer_index = signers.index(public_key)
        result = run_json(
            [self.binary, "-f", "json", "sign", "--tx", serialized_tx, *key_arguments],
            timeout=remaining(),
            ambiguous=False,
        )
        if not isinstance(result, dict) or result.get("signer") != wallet["address"]:
            raise AdapterError("cli_signed_transaction_signer_mismatch")
        try:
            signed_message, signed_signatures, signed_signers = _transaction_layout(
                result.get("signedTransaction")
            )
        except AdapterError:
            raise AdapterError("invalid_cli_signed_transaction") from None
        if signed_message != message or signed_signers != signers:
            raise AdapterError("cli_signed_transaction_message_changed")
        if any(
            signature != signed_signatures[index]
            for index, signature in enumerate(signatures)
            if index != signer_index
        ):
            raise AdapterError("cli_signed_transaction_other_signature_changed")
        if signed_signatures[signer_index] == b"\0" * 64:
            raise AdapterError("cli_signed_transaction_owner_signature_missing")
        return {
            "signer": wallet["address"],
            "signedTransaction": result["signedTransaction"],
        }

    def close(self, position_id, *, key_name=None):
        key_arguments = _key_arguments(key_name)
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        if (
            not isinstance(position_id, str)
            or not 32 <= len(position_id) <= 44
            or any(c not in alphabet for c in position_id)
        ):
            raise AdapterError("invalid_position_public_key")
        number = 0
        for char in position_id:
            number = number * 58 + alphabet.index(char)
        if (
            len(position_id)
            - len(position_id.lstrip("1"))
            + (number.bit_length() + 7) // 8
            != 32
        ):
            raise AdapterError("invalid_position_public_key")
        started = time.monotonic()
        self.identity()
        remaining = self.timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise AdapterError("identity_deadline_exceeded")
        result = run_json(
            [
                self.binary,
                "-f",
                "json",
                "perps",
                "close",
                "--position",
                position_id,
                *key_arguments,
            ],
            timeout=remaining,
            ambiguous=True,
        )
        if not isinstance(result, dict):
            raise AdapterError("invalid_position_result", ambiguous=True)
        return result
