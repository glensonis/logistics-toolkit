#!/usr/bin/env bash
set -euo pipefail

# Idempotent dependency bootstrap for the Logistics Toolkit Flask app.
# Dependencies are just flask + requests (see requirements.txt).
python3 -m pip install --user --break-system-packages -r requirements.txt

# Best-effort convenience so the README's `python ...` commands work verbatim.
# python3 is always present on the base image; this only adds the bare `python`
# alias when it is missing, and never fails the install if it cannot be created.
if ! command -v python >/dev/null 2>&1; then
  sudo ln -sf "$(command -v python3)" /usr/local/bin/python || true
fi
