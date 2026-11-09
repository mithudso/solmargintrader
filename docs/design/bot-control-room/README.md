# Bot control room design

Version: 1.0.1
Delta: v1.0.0 to v1.0.1; document the durable self-contained preview export.

Open /Users/mitch/dev/solmargintrader/docs/design/bot-control-room/index.html in a browser. The HTML, CSS and JavaScript are local and require no build, package install, account or network service. This is a design prototype; all displayed results and actions are illustrative and reset on reload.

Explore the fleet, select different bots, inspect held Council signals, filter the roster, pause paper entries, open evidence, and create a paper draft through the five-stage studio. The action search supports Cmd+K or Ctrl+K, and Escape closes dialogs. Saving a draft starts nothing.

For local HTTP preview, the optional command is:

```bash
python3 -m http.server 18796 --bind 127.0.0.1 --directory /Users/mitch/dev/solmargintrader/docs/design/bot-control-room
```

Then open http://127.0.0.1:18796/

The design is /Users/mitch/dev/solmargintrader/docs/design/bot-control-room/DESIGN.md. Skill coverage is /Users/mitch/dev/solmargintrader/docs/design/bot-control-room/SKILLS.md. Browser evidence is /Users/mitch/dev/solmargintrader/docs/design/bot-control-room/REVIEW.md. The proposed implementation plan is /Users/mitch/dev/solmargintrader/docs/superpowers/plans/2026-11-09-bot-control-room.md. Nothing in that plan is marked implemented by this design task.

This session also exported /Users/mitch/Downloads/sol-bot-control-room-2026-11-09.html with the same CSS and JavaScript inlined. That local preview remains usable after the isolated task worktree is removed. It is a generated convenience copy, not a second source of truth.

Syntax verification:

```bash
node --check /Users/mitch/dev/solmargintrader/docs/design/bot-control-room/mockup.js
```

Repository documentation and retrieval checks:

```bash
cd /Users/mitch/dev/solmargintrader
python3 scripts/check_docs.py
python3 index/build.py --check
```
