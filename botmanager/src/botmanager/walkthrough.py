"""One ordered, copyable workflow shared by terminal and structured help.

Examples are data. Importing this module never probes an owner or starts a process.
The parser tests bind every example to the real command registry.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Stage:
    title: str
    prerequisite: str
    commands: tuple[str, ...]
    shell: tuple[str, ...] = ()
    before: tuple[str, ...] = ()


SETUP = (
    'export PATH="$HOME/.local/bin:$PATH"',
    'export SOLBOT_HOME="${SOLBOT_HOME:-$HOME/.config/solbot}"',
    'export SOLBOT_ECOSYSTEM_HOME="${SOLBOT_ECOSYSTEM_HOME:-$HOME/.local/share/solmargintrader/ecosystem-paper-v2}"',
)

STAGES = (
    Stage(
        "1. Inspect the installation and existing owners (reads only)",
        "Use the shell setup below in each terminal. Existing names/descriptors are never overwritten; "
        "choose a new home or unused names for a new demonstration. help is JSON; --help is this walkthrough.",
        (
            "solbot help",
            "solbot schema",
            "solbot discover",
            "solbot list",
            "solbot status --why",
            "solbot stack status",
            "solbot service status",
            "solbot ui status",
            "solbot ui",
            'solbot --ecosystem-home "$SOLBOT_ECOSYSTEM_HOME" health-check',
        ),
    ),
    Stage(
        "2. Enable persistent availability, then find/open the UI",
        "Run after reviewing stage 1. stack install refuses a competing legacy supervisor; "
        "migrate only its verified service, as described in stage 12. On macOS the user LaunchAgent "
        "returns after login following reboot; Linux uses a user systemd service. The suite "
        "monitors existing input but does not create a recorder or start a new research job. "
        "ui status returns the actual verified URL, never a guessed port; ui open starts the suite if needed.",
        (
            "solbot stack install",
            "solbot stack start",
            "solbot stack status",
            "solbot ui start",
            "solbot ui status",
            "solbot ui open",
            "solbot health-check",
            "solbot metrics",
            "solbot component-alerts --after 0 --limit 100",
        ),
    ),
    Stage(
        "3. Create a draft with defaults and inspect its pinned settings",
        "Creating a draft starts no worker. my-grid must be an unused name. "
        "Only --set values override defaults; schema lists editable fields and bounds.",
        (
            "solbot schema grid",
            "solbot create grid --name my-grid",
            "solbot config my-grid --effective",
            "solbot history my-grid --revision 1",
            "solbot status my-grid --why",
        ),
    ),
    Stage(
        "4. Prepare prospective input, validate/register it, then request paper start",
        "Requires the existing shared-sol-usd archive and its independent producer. --reference "
        "explicitly consents to Coinbase SOL/USD reference evidence for the Jupiter SOL/USDC target. "
        "Do not continue past a failed data-check. Preparation records a new activation boundary; "
        "completed minutes, warmup and trades take actual time. start persists intent; stage 2 owns workers.",
        (
            'solbot prepare-input my-grid --archive shared-sol-usd --reference --mode prospective --output "$SOLBOT_HOME/my-grid-prospective.json"',
            'solbot data-check my-grid --descriptor "$SOLBOT_HOME/my-grid-prospective.json"',
            'solbot register-input my-grid --descriptor "$SOLBOT_HOME/my-grid-prospective.json"',
            "solbot start my-grid",
            "solbot status my-grid --why",
        ),
    ),
    Stage(
        "5. Observe progress, reports and entry controls",
        "health BOT explains account health; health-check/metrics are compact component telemetry. "
        "Read next_after in each page and pass that exact cursor on the next call; 0 is the first page. "
        "Pause/resume support Grid and DCA, retain existing exits and require a fresh UUID for each operation. "
        "A stopped account can retain positions; no command here liquidates it.",
        (
            "solbot health my-grid",
            "solbot alerts my-grid --after 0 --limit 100",
            "solbot events my-grid --after 0 --limit 100",
            "solbot report my-grid --after 0 --limit 100 --format json",
            "solbot report my-grid --after 0 --limit 100 --format human",
            "solbot report my-grid --after 0 --limit 100 --format csv",
            "solbot history-page my-grid --after 0 --limit 100",
            "solbot run-history my-grid --after 0 --limit 100",
            "solbot pause my-grid --request-id 70e04bf6-e449-43c9-969c-e4b66734072a",
            "solbot resume my-grid --request-id 16be2d54-3414-41ce-8660-66289cf6abc1",
        ),
    ),
    Stage(
        "5b. Select an actual paper run for an attributed report",
        "The paper runtime ID is independent of the research run ID. This captures the registered "
        "current paper runtime. For an archived report, use an actual runtime_id from run-history items.",
        ('solbot report my-grid --run-id "$PAPER_RUN_ID" --format json',),
        before=(
            'solbot run-history my-grid --after 0 --limit 100 > "$SOLBOT_HOME/paper-runs.json"',
            '''export PAPER_RUN_ID="$(python3 -c 'import json,sys; b=json.load(open(sys.argv[1])); assert b["ok"] and b["data"]["current_runtime_id"]; print(b["data"]["current_runtime_id"])' "$SOLBOT_HOME/paper-runs.json")"''',
        ),
    ),
    Stage(
        "6. Optional independent DCA, Trend and Momentum accounts",
        "Each name needs its own descriptor/account. Run each family's complete sequence only when wanted. "
        "All share the selected existing producer; the supervisor admits at most four active workers. "
        "Trend/Momentum do not support entry pause. These virtual accounts are not funded wallet allocations.",
        tuple(
            command
            for family in ("dca", "trend", "momentum")
            for command in (
                f"solbot schema {family}",
                f"solbot create {family} --name my-{family}",
                f'solbot prepare-input my-{family} --archive shared-sol-usd --reference --mode prospective --output "$SOLBOT_HOME/my-{family}-prospective.json"',
                f'solbot data-check my-{family} --descriptor "$SOLBOT_HOME/my-{family}-prospective.json"',
                f'solbot register-input my-{family} --descriptor "$SOLBOT_HOME/my-{family}-prospective.json"',
                f"solbot start my-{family}",
                f"solbot status my-{family} --why",
                f"solbot stop my-{family}",
            )
        ),
    ),
    Stage(
        "7. M4 research: reviewed owner, separate historical capture and frozen search",
        "Requires the regular installed research runtime and canonical authority; setup probes/writes "
        "a descriptor without initializing authority. Review the descriptor before research-register. "
        "Use the normal registration below for existing authority; only for a verified never-bound namespace "
        "use the explicitly labelled first-use alternative in stage 12. Never recreate a lost authority. "
        "Backtest is descriptive. Production blind judging currently requires macOS isolation. "
        "Reference USD data does not establish certified executable Jupiter costs or final eligibility. "
        "Save the successful research JSON using the redirect shown below; capture its actual run_id, "
        "then use stage 8. Existing output paths must match exactly or be replaced with new filenames.",
        (
            'solbot research-setup --output "$SOLBOT_HOME/research-owner.json"',
            'solbot research-register --owner "$SOLBOT_HOME/research-owner.json" --accept-registered-roots-only',
            'solbot prepare-input my-grid --archive shared-sol-usd --reference --mode historical --output "$SOLBOT_HOME/my-grid-historical.json"',
            'solbot data-check my-grid --descriptor "$SOLBOT_HOME/my-grid-historical.json"',
            'solbot backtest my-grid --owner "$SOLBOT_HOME/research-owner.json" --descriptor "$SOLBOT_HOME/my-grid-historical.json"',
            'solbot research-plan my-grid --output "$SOLBOT_HOME/my-grid-plan.json"',
            'solbot research-status --owner "$SOLBOT_HOME/research-owner.json"',
            'solbot research my-grid --owner "$SOLBOT_HOME/research-owner.json" --descriptor "$SOLBOT_HOME/my-grid-historical.json" --plan "$SOLBOT_HOME/my-grid-plan.json" > "$SOLBOT_HOME/research-result.json"',
        ),
        (
            "# After research returns ok:true, capture the owner-issued run ID:",
            '''export RUN_ID="$(python3 -c 'import json,sys; b=json.load(open(sys.argv[1])); assert b["ok"]; print(b["data"]["run"]["run_id"])' "$SOLBOT_HOME/research-result.json")"''',
        ),
    ),
    Stage(
        "8. Research receipts and protected learning (conditional, elapsed evidence required)",
        "RUN_ID must come from stage 7 or the actual research-status owner record. Labels require "
        "300 comparable resolved outcomes and 30 completed trades. learning-propose may retain the "
        "incumbent; capture a proposal ID only from ok:true. After that capture, inspect before shadow. "
        "Promotion requires certified accepted evidence, actual seven-day prospective worker/observation "
        "spans, 30 comparable closed shadow trades, 48-hour cooldown, unchanged pins/revision and a "
        "healthy reconciled flat boundary. Reference-only data remains uncertified. No client clock or "
        "test fixture bypasses these gates. Promotion and rollback commands are separate conditional actions.",
        (
            'solbot research-status --owner "$SOLBOT_HOME/research-owner.json" --run-id "$RUN_ID"',
            'solbot research-proposal --owner "$SOLBOT_HOME/research-owner.json" --run-id "$RUN_ID"',
            'solbot learning-labels my-grid --owner "$SOLBOT_HOME/research-owner.json"',
            'solbot learning-propose my-grid --run-id "$RUN_ID" --owner "$SOLBOT_HOME/research-owner.json" > "$SOLBOT_HOME/learning-result.json"',
        ),
        (
            "# Only after learning-propose returns ok:true:",
            '''export PROPOSAL_ID="$(python3 -c 'import json,sys; b=json.load(open(sys.argv[1])); assert b["ok"]; print(b["data"]["id"])' "$SOLBOT_HOME/learning-result.json")"''',
        ),
    ),
    Stage(
        "8b. Inspect/shadow an actual proposal; adopt or roll back only when its gates pass",
        "PROPOSAL_ID is the owner-issued ID captured in stage 8. inspect is read-only. A refused "
        "promotion keeps the incumbent; rollback changes future configuration and cannot undo trades. "
        "Use fresh request UUIDs for a new operation; reuse an exact UUID only to reconcile its receipt.",
        (
            'solbot learning-proposal "$PROPOSAL_ID" --owner "$SOLBOT_HOME/research-owner.json"',
            'solbot learning-shadow "$PROPOSAL_ID" --owner "$SOLBOT_HOME/research-owner.json"',
            'solbot learning-proposal "$PROPOSAL_ID" --owner "$SOLBOT_HOME/research-owner.json"',
            'solbot learning-promote "$PROPOSAL_ID" --request-id f9038263-a2b8-4070-8612-37a554b459be --owner "$SOLBOT_HOME/research-owner.json"',
            'solbot learning-rollback "$PROPOSAL_ID" --request-id df1967a4-337d-4d88-bdc7-802558473455 --owner "$SOLBOT_HOME/research-owner.json"',
        ),
    ),
    Stage(
        "9. Browser owner: discover, inspect, compare and reconcile",
        "Load the matching extension and its reviewed native helper first. Extension stays dry-run/disarmed. "
        "discover reports browser:INSTALLATION_UUID:grid. Select the actual profile identity in the shell "
        "below; never guess a UUID or choose the first of several profiles. Save browser-status with the "
        "redirect below, then capture its observed generation/hash before each new control. "
        "A later stop needs a fresh observation after start acknowledgment. Offline/armed owners refuse.",
        ("solbot discover",),
        (
            'printf "Browser identity from discover: "; IFS= read -r BROWSER_ID',
            "export BROWSER_ID",
            'solbot browser-status "$BROWSER_ID" > "$SOLBOT_HOME/browser-observation.json"',
            '''export BROWSER_GENERATION="$(python3 -c 'import json,sys; b=json.load(open(sys.argv[1])); assert b["ok"]; print(b["data"]["snapshot"]["generation"])' "$SOLBOT_HOME/browser-observation.json")"''',
            '''export BROWSER_HASH="$(python3 -c 'import json,sys; b=json.load(open(sys.argv[1])); assert b["ok"]; print(b["data"]["snapshot"]["config_hash"])' "$SOLBOT_HOME/browser-observation.json")"''',
        ),
    ),
    Stage(
        "9b. Guarded browser controls using the observation from stage 9",
        "After start/receipt, repeat the stage 9 observation/captures before the optional stop. "
        "A stale generation/hash refuses without an unguarded retry. A receipt can stay pending until "
        "the extension polls and acknowledges it. These request UUIDs are examples for one operation each.",
        (
            'solbot browser-status "$BROWSER_ID"',
            'solbot browser-control "$BROWSER_ID" start --request-id 23da071c-2a83-4152-b3ac-f04f1caa3e15 --expected-generation "$BROWSER_GENERATION" --expected-config-hash "$BROWSER_HASH"',
            "solbot browser-receipt 23da071c-2a83-4152-b3ac-f04f1caa3e15",
        ),
    ),
    Stage(
        "9c. Re-observe before a new browser stop",
        "Wait for the start receipt to resolve, then capture the current owner's generation and hash. "
        "These are the actual observation values compared atomically by the browser owner.",
        (
            'solbot browser-control "$BROWSER_ID" stop --request-id 34262d0b-3aef-46de-8a80-382db7257232 --expected-generation "$BROWSER_GENERATION" --expected-config-hash "$BROWSER_HASH"',
            "solbot browser-receipt 34262d0b-3aef-46de-8a80-382db7257232",
        ),
        before=(
            'solbot browser-status "$BROWSER_ID" > "$SOLBOT_HOME/browser-observation.json"',
            '''export BROWSER_GENERATION="$(python3 -c 'import json,sys; b=json.load(open(sys.argv[1])); assert b["ok"]; print(b["data"]["snapshot"]["generation"])' "$SOLBOT_HOME/browser-observation.json")"''',
            '''export BROWSER_HASH="$(python3 -c 'import json,sys; b=json.load(open(sys.argv[1])); assert b["ok"]; print(b["data"]["snapshot"]["config_hash"])' "$SOLBOT_HOME/browser-observation.json")"''',
        ),
    ),
    Stage(
        "10. Optional executor preview and directed quote evidence",
        "Separate executor installation required; setup probes public identity and loads no keys. "
        "Set its installed absolute interpreter path in the shell below. Before admit/intent, a reviewed "
        "owner must provide the exact compatible request artifact at executor-request.json, including "
        "its real request UUID; capture that UUID below. There is no safe generic order template. "
        "Current paper/disarmed manager refuses live forwarding and uncertified admission. "
        "cycle-check separately requires genuine aligned directed quotes and explicit failure/unwind/cost "
        "assumptions in cycle-evidence.json; it diagnoses conditional economics and never books profit.",
        (),
        (
            'printf "Installed executor Python (absolute path): "; IFS= read -r EXECUTOR_PYTHON',
            "export EXECUTOR_PYTHON",
        ),
    ),
    Stage(
        "10b. Run only after the reviewed optional artifacts exist",
        "Review executor-owner.json after setup. The two request commands below show separate APIs; "
        "use only the API matching the owner's reviewed request schema. An unavailable capability is a "
        "reported refusal, never a reason to supply fake source/certification evidence or arm a wallet.",
        (
            'solbot executor-setup --interpreter "$EXECUTOR_PYTHON" --home "$HOME/.config/solmargintrader-executor" --output "$SOLBOT_HOME/executor-owner.json"',
            'solbot executor-capabilities --executor "$SOLBOT_HOME/executor-owner.json"',
        ),
    ),
    Stage(
        "10c. Exact owner artifacts and optional conditional quote diagnosis",
        "The reviewed request and genuine cycle evidence must already exist. Capturing request_id "
        "does not validate the request; the owner compares its complete binding. Use each API only "
        "for a compatible reviewed request and reconcile uncertainty instead of submitting again.",
        (
            'solbot executor-admit my-grid --executor "$SOLBOT_HOME/executor-owner.json" --request "$SOLBOT_HOME/executor-request.json"',
            'solbot executor-intent my-grid --executor "$SOLBOT_HOME/executor-owner.json" --request "$SOLBOT_HOME/executor-request.json"',
            'solbot executor-status --executor "$SOLBOT_HOME/executor-owner.json" --request-id "$EXECUTOR_REQUEST_ID"',
            'solbot executor-reconcile --executor "$SOLBOT_HOME/executor-owner.json"',
            'solbot cycle-check --descriptor "$SOLBOT_HOME/cycle-evidence.json"',
        ),
        before=(
            '''export EXECUTOR_REQUEST_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["request_id"])' "$SOLBOT_HOME/executor-request.json")"''',
        ),
    ),
    Stage(
        "11. Stop, edit with compare-and-swap, inspect history, back up and restore",
        "After stop, verify owner release and zero exposure before apply; stop never sells positions. "
        "The example expects fresh my-grid revision 1; inspect config first and use its actual revision "
        "if it differs. Apply revision 2 only after the edit succeeds. A new compatible prospective "
        "descriptor may be required; select a new path rather than overwriting frozen input. "
        "Before backup stop every other bot you started, quiesce external controls, stop the suite and "
        "verify stopped owners. Restore requires a never-existing destination and retains the live "
        "canonical research authority. stack stop/uninstall may retain an adopted independent UI; "
        "read ui_retained. Restart explicitly resumes monitoring of retained desired intents.",
        (
            "solbot stop my-grid",
            "solbot status my-grid --why",
            "solbot config my-grid --effective",
            "solbot edit my-grid --set range_pct=20 --expected-revision 1 --request-id dbe47b81-b873-437c-a149-d6c6c11af6eb",
            "solbot history my-grid",
            "solbot apply my-grid --expected-revision 2 --request-id 707d5687-0261-4915-b721-51cec31bc23e",
            "solbot history my-grid --revision 2",
            "solbot stack restart",
            "solbot health-check",
            "solbot stack stop",
            "solbot stack status",
            'solbot backup "$SOLBOT_HOME-backup-01"',
            'solbot restore "$SOLBOT_HOME-backup-01" "$SOLBOT_HOME-restored-01"',
            "solbot stack uninstall",
        ),
    ),
    Stage(
        "12. Alternatives and recovery branches (choose, do not run all)",
        "Foreground alternatives: with no installed/running suite, stack run holds this terminal and "
        "monitors manager+UI; daemon is the older manager-only foreground owner. service install is "
        "the older macOS manager-only service. Never run either alongside the suite for the same home. "
        "To migrate an identified old service, capture its status/versions/backup first, use its matching "
        "installed executable to uninstall that exact service, verify ownership release, then stage 2. "
        "research-cancel targets an actual active run obtained from research-status in another terminal; "
        "research-recover requires a proved-released interrupted owner lease. Both retain spent finals. "
        "The first-authority command is ONLY for a verified never-bound namespace; missing registered "
        "authority must refuse. Do not use it to clear a database error or reset prior evidence.",
        (
            "solbot stack run",
            "solbot daemon",
            "solbot service install",
            "solbot service uninstall",
            'solbot research-register --owner "$SOLBOT_HOME/research-owner.json" --accept-registered-roots-only --initialize-first-authority',
            'solbot research-cancel --owner "$SOLBOT_HOME/research-owner.json" --run-id "$RUN_ID"',
            'solbot research-recover --owner "$SOLBOT_HOME/research-owner.json" --run-id "$RUN_ID"',
        ),
    ),
)


def workflow():
    """JSON-safe help metadata, from the same examples as terminal help."""
    return {"shell_setup": list(SETUP), "stages": [asdict(stage) for stage in STAGES]}


def render():
    lines = [
        "Recommended order: the complete paper/disarmed workflow",
        "These are staged examples, not one unattended script. Continue only when a prerequisite passes.",
        "Shell setup (macOS/Linux/WSL2; solbot is the installed executable):",
        *("  " + command for command in SETUP),
        "",
    ]
    for stage in STAGES:
        lines.extend((stage.title, "  " + stage.prerequisite))
        lines.extend("  " + command for command in stage.before)
        lines.extend("  " + command for command in stage.commands)
        lines.extend("  " + command for command in stage.shell)
        lines.append("")
    lines.extend(
        (
            "Fresh operation UUIDs: python3 -c 'import uuid; print(uuid.uuid4())'",
            "Executor request UUID: read request_id from the reviewed owner artifact; do not invent it.",
            "Local UI: solbot ui status; solbot ui open. Component collectors: solbot health-check; solbot metrics.",
            "Native Windows is not supported by the full stack; use WSL2 with the Linux prerequisites.",
            "macOS LaunchAgent returns at user login, not before login. Linux boot persistence needs user linger.",
            "Details: https://github.com/mithudso/solmargintrader/blob/master/docs/bot-manager-managed-suite.md",
            "Reference input: https://github.com/mithudso/solmargintrader/blob/master/docs/bot-manager-quickstart.md",
        )
    )
    return "\n".join(lines)
