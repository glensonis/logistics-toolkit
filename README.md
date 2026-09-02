# Logistics Toolkit

Freight quoting, chargeable weight, fuel surcharge, truck/warehouse sizing, and eleven logistics desk tools, with live FX and fuel-price feeds.

This is a **dual-target** project: the same source runs as a Flask webpage and as a standalone Windows desktop app (`LogisticsToolkit.exe`).

## Run the webpage

```bash
python -m pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). Dependencies are `flask` and `requests` (`requirements.txt`).

## Smoke tests

`scripts/smoke_api.py` is the test suite. There is no pytest.

```bash
python scripts/smoke_api.py
```

Run it from the repo root. It exercises every JSON route through Flask's test client, primes the FX/fuel caches with a live network fetch first, and prints per-endpoint runtime output with a PASS/FAIL tally.

## Build the Windows desktop app

On Windows:

```bat
build_app.bat
```

The script builds `--onedir --noupx --noconsole` (not `--onefile`, and not UPX) so Microsoft Defender is less likely to false-positive, then scans the result with Defender and aborts if flagged.

## Notes

- Port is **5000** on **127.0.0.1**.
- Keep the webpage and desktop app in parity when changing shared logic.
- Do not reformat `templates/index.html`: `patch_desktop_ui.py` matches exact source text to patch the desktop UI.
- Contributor / agent notes (architecture, desktop AV caveats, CLI policy) live in `CLAUDE.md`.
