# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Logistics Toolkit — a **dual-target build**: a Flask webpage and a standalone Windows desktop app (`LogisticsToolkit.exe`) built **from the same source**. Freight quoting, chargeable weight, fuel surcharge, truck/warehouse sizing, and eleven logistics desk tools, with live FX and fuel-price feeds.

## Commands

```bash
python app.py                    # run the webpage at http://127.0.0.1:5000
python scripts/smoke_api.py      # API smoke tests - the actual test harness
build_app.bat                    # build the desktop exe (see caveats below)
```

Dependencies are just `flask` and `requests` (`requirements.txt`).

**`scripts/smoke_api.py` is the test suite.** There is no pytest. It exercises every JSON route through Flask's test client, primes the FX/fuel caches with a live network fetch first, and prints real runtime output per endpoint with a PASS/FAIL tally. Run it after touching any calculator or route — the owner rejects "all PASS" claims that lack per-item runtime output, and this script exists to produce exactly that.

## The desktop build is AV-sensitive

`build_app.bat` is not a plain PyInstaller wrapper. It builds `--onedir --noupx --noconsole` specifically to avoid Microsoft Defender false positives, then **scans the result with Defender and aborts the build if flagged** — once on the raw build output and again on the delivered copy.

Do not "simplify" it to `--onefile` or re-enable UPX; both are what trip AV heuristics. The script also regenerates `Run Logistics Toolkit.bat` and cleans up `build/`, `dist/`, and the `.spec` file afterwards.

## Architecture

**One Flask app, two delivery modes.** `app.py` detects packaging via `sys.frozen` (`_is_frozen()`): when frozen it goes straight to serving, and when run from source it prints the startup banner and opens a browser. Port is hard-coded to **5000**.

Business logic is split into focused modules that `app.py` imports and exposes as JSON routes:

| Module | Owns |
|---|---|
| `logistics_quote.py` | freight quote calculation |
| `logistics_chargeable.py` | chargeable/volumetric weight |
| `logistics_fuel_surcharge.py` | fuel surcharge |
| `logistics_calculators.py` | truck requirement, warehouse space |
| `logistics_desk_tools.py` | the 11 desk tools (FIFO/FEFO, landed cost, DG segregation, transit ETA, ...) |
| `oanda_fetcher.py` | FX rates, 5-minute refresh |
| `fuel_fetcher.py` | UAE/GCC fuel prices, hourly refresh |

The frontend is a single vanilla `templates/index.html` — no framework, no build step.

**`patch_desktop_ui.py` rewrites `templates/index.html` in place** via literal string replacement to bring the desktop UI to feature parity. Because it matches exact source text, reformatting `index.html` will silently break it. Check it before reflowing that file.

**Keep desktop and webpage in parity** when changing shared logic — that is the point of the dual-target design.

## Agent Bus

Grok is the orchestrator and dispatches work items; Claude is Backend + UI support. Wait for Grok to assign scope rather than guessing it. Session start: `python scripts/agent_bus_cli.py ping --agent claude --status online --detail ready` then `inbox --agent claude --status pending`. Protocol is documented in `Agent_Bus_Protocol.txt`; standing CLI policy in `Grok_Build_Claude_CLI_Policy.txt`.

The bus here was adapted from the GlenSonis pattern but made self-contained (it derives `APP_DIR` from `__file__` rather than importing a config module). Task meta carries an extra `target` field — `desktop`, `webpage`, or `both` — for the dual-target split.

For any reply or post body containing quotes, parens, `=`, or unicode, use `--body-file <path>` — inline `--body` breaks PowerShell arg parsing and silently fails to post.

## Windows Python gotchas

- ASCII-only in anything printed to stdout when output may be redirected to a log — piped stdout defaults to cp1252 and a stray non-ASCII character can crash the process. Set `PYTHONUTF8=1` on spawned children.
- Never interpolate file paths into subprocess command strings; apostrophes break them. Pass argv lists.
- Prefer `127.0.0.1` over `localhost` for local HTTP — on this machine `localhost` resolves to IPv6 `::1` first and costs ~2s per request.
