#!/usr/bin/env python3
"""API smoke tests for Logistics Toolkit.

Exercises every JSON route through Flask's test client.
Primes the FX/fuel caches with a live network fetch first.
Prints per-endpoint runtime output and a PASS/FAIL tally.

Run from the repo root:

    python scripts/smoke_api.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import (  # noqa: E402
    _cache,
    _fuel_cache,
    _refresh_fuel_prices,
    _refresh_rates,
    app,
)

# Catalog keys bloat the preview without proving the route ran.
_OMIT_PREVIEW = frozenset({"dg_classes", "packing_groups", "pallet_types"})
_PREVIEW_MAX = 1200


def _out(msg: str = "") -> None:
    """Write ASCII-only stdout (Windows piped logs default to cp1252)."""
    text = msg if isinstance(msg, str) else str(msg)
    sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
    sys.stdout.flush()


def _for_print(obj):
    if isinstance(obj, dict):
        return {k: _for_print(v) for k, v in obj.items() if k not in _OMIT_PREVIEW}
    if isinstance(obj, list):
        return [_for_print(x) for x in obj]
    return obj


def _preview(data) -> str:
    dumped = json.dumps(_for_print(data), ensure_ascii=True, default=str, sort_keys=True)
    if len(dumped) > _PREVIEW_MAX:
        return dumped[:_PREVIEW_MAX] + "...[truncated]"
    return dumped


def _json_api_routes() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for rule in app.url_map.iter_rules():
        if not str(rule.rule).startswith("/api/"):
            continue
        methods = sorted(m for m in (rule.methods or set()) if m not in {"HEAD", "OPTIONS"})
        for method in methods:
            found.append((method, str(rule.rule)))
    found.sort()
    return found


def _diesel_available() -> bool:
    uae = _fuel_cache.get("uae") or {}
    grades = uae.get("grades") or []
    return any("diesel" in str(g.get("name", "")).lower() for g in grades if isinstance(g, dict))


def _ok_json(status: int, data) -> bool:
    return status == 200 and isinstance(data, dict) and "error" not in data


def _cases() -> list[dict]:
    today = date.today().isoformat()
    later = (date.today() + timedelta(days=45)).isoformat()
    later2 = (date.today() + timedelta(days=90)).isoformat()

    fsc_query = {"baseline": "3.5"}
    if not _diesel_available():
        fsc_query["current"] = "4.0"
        fsc_query["currency"] = "AED"

    return [
        {"method": "GET", "path": "/api/rates", "ok": _ok_json},
        {"method": "GET", "path": "/api/fuel-prices", "ok": _ok_json},
        {
            "method": "GET",
            "path": "/api/convert",
            "query": {"amount": "100", "from": "USD", "to": "AED"},
            "ok": lambda s, d: _ok_json(s, d) and "result" in d,
        },
        {
            "method": "GET",
            "path": "/api/fuel-surcharge",
            "query": fsc_query,
            "ok": lambda s, d: _ok_json(s, d) and "fsc_percent" in d,
        },
        {
            "method": "POST",
            "path": "/api/truck",
            "json": {
                "transport_region": "uae",
                "total_weight_kg": 8500,
                "total_volume_cbm": 28,
                "pallet_count": 12,
                "pallet_type": "standard",
                "stack_levels": 1,
                "safety_margin_pct": 10,
            },
            "ok": lambda s, d: _ok_json(s, d) and "primary" in d,
        },
        {
            "method": "POST",
            "path": "/api/warehouse",
            "json": {
                "length_m": 40,
                "width_m": 30,
                "height_m": 8,
                "aisle_width_m": 3,
                "staging_pct": 15,
                "clearance_pct": 10,
                "pallet_type": "standard",
                "stack_levels": 3,
                "pallet_height_m": 1.45,
            },
            "ok": lambda s, d: _ok_json(s, d) and "capacity" in d,
        },
        {
            "method": "POST",
            "path": "/api/quote",
            "json": {
                "rate_basis": "per_kg",
                "base_rate": 0.45,
                "weight_kg": 5000,
                "volume_cbm": 12,
                "volumetric_factor": 167,
                "distance_km": 250,
                "fsc_percent": 8,
                "margin_percent": 15,
                "tolls_fees": 0,
                "accessorials": [{"label": "Documentation fee", "amount": 75}],
                "currency": "AED",
            },
            "ok": lambda s, d: _ok_json(s, d) and "sell_total" in d,
        },
        {
            "method": "POST",
            "path": "/api/chargeable-weight",
            "json": {
                "actual_weight_kg": 500,
                "volume_cbm": 2.5,
                "volumetric_preset": "road_167",
            },
            "ok": lambda s, d: _ok_json(s, d) and "chargeable_weight_kg" in d,
        },
        {
            "method": "POST",
            "path": "/api/receiving",
            "json": {
                "dock_count": 2,
                "hours_per_day": 8,
                "avg_unload_minutes": 45,
                "trucks_scheduled": 6,
            },
            "ok": lambda s, d: _ok_json(s, d) and "total_slots" in d,
        },
        {
            "method": "POST",
            "path": "/api/inventory-doh",
            "json": {
                "on_hand_qty": 1200,
                "daily_outbound": 80,
                "lead_time_days": 14,
                "safety_stock_days": 7,
            },
            "ok": lambda s, d: _ok_json(s, d) and "days_on_hand" in d,
        },
        {
            "method": "POST",
            "path": "/api/pallet-build",
            "json": {
                "cartons_per_layer": 8,
                "layers": 3,
                "carton_weight_kg": 12,
                "max_stack_weight_kg": 1000,
            },
            "ok": lambda s, d: _ok_json(s, d) and "cartons_total" in d,
        },
        {
            "method": "POST",
            "path": "/api/fifo-fefo",
            "json": {
                "delivery_date": today,
                "batches": [
                    {"batch_id": "Lot A", "expiry_date": later, "quantity": 100},
                    {"batch_id": "Lot B", "expiry_date": later2, "quantity": 150},
                ],
            },
            "ok": lambda s, d: _ok_json(s, d) and "ship_order" in d,
        },
        {
            "method": "POST",
            "path": "/api/landed-cost",
            "json": {
                "goods_value": 10000,
                "quantity": 100,
                "duty_percent": 5,
                "vat_percent": 5,
                "clearance_fees": 500,
                "from_currency": "USD",
                "to_currency": "AED",
            },
            "ok": lambda s, d: _ok_json(s, d) and "landed_total" in d,
        },
        {
            "method": "POST",
            "path": "/api/doc-checklist",
            "json": {
                "dangerous_goods": False,
                "temperature_controlled": False,
                "cross_border": True,
                "high_value": False,
            },
            "ok": lambda s, d: _ok_json(s, d) and "items" in d,
        },
        {
            "method": "POST",
            "path": "/api/dg-segregation",
            "json": {"class_a": "3", "class_b": "8"},
            "ok": lambda s, d: _ok_json(s, d) and "segregate" in d,
        },
        {
            "method": "POST",
            "path": "/api/trip-cost",
            "json": {
                "distance_km": 250,
                "fuel_l_per_100km": 28,
                "fuel_price": 4.33,
                "driver_cost": 350,
                "tolls_fees": 25,
                "weight_kg": 5000,
            },
            "ok": lambda s, d: _ok_json(s, d) and "total_cost" in d,
        },
        {
            "method": "POST",
            "path": "/api/transit-eta",
            "json": {
                "pickup_date": today,
                "transit_days": 3,
                "buffer_days": 1,
                "skip_weekends": True,
            },
            "ok": lambda s, d: _ok_json(s, d) and "delivery_date" in d,
        },
        {
            "method": "POST",
            "path": "/api/free-time",
            "json": {"arrival_date": today, "free_days": 7},
            "ok": lambda s, d: _ok_json(s, d) and "last_free_day" in d,
        },
        {
            "method": "POST",
            "path": "/api/multi-stop",
            "json": {
                "stops": [
                    {"weight_kg": 2000, "volume_cbm": 5, "pallets": 4},
                    {"weight_kg": 3000, "volume_cbm": 7, "pallets": 6},
                ],
                "transport_region": "uae",
                "safety_margin_pct": 10,
            },
            "ok": lambda s, d: _ok_json(s, d) and "truck" in d,
        },
    ]


def _prime_caches() -> None:
    _out("Priming FX cache (live OANDA fetch)...")
    try:
        _refresh_rates()
    except Exception as exc:
        _out("  FX refresh raised: %s" % exc)

    rates = _cache.get("rates") or {}
    errors = list(_cache.get("errors") or [])
    _out("  FX currencies loaded: %s" % (len(rates),))
    if errors:
        _out("  FX errors: %s" % "; ".join(str(e) for e in errors))

    _out("Priming fuel cache (live fetch)...")
    try:
        _refresh_fuel_prices()
    except Exception as exc:
        _out("  Fuel refresh raised: %s" % exc)
    fuel_errors = list(_fuel_cache.get("errors") or [])
    uae = _fuel_cache.get("uae")
    gcc = _fuel_cache.get("gcc")
    _out("  Fuel UAE loaded: %s  GCC loaded: %s" % (bool(uae), bool(gcc)))
    if fuel_errors:
        _out("  Fuel errors: %s" % "; ".join(str(e) for e in fuel_errors))
    _out("")


def _run_one(client, case: dict) -> tuple[str, bool]:
    method = case["method"]
    path = case["path"]
    label = "%s %s" % (method, path)
    try:
        if method == "GET":
            response = client.get(path, query_string=case.get("query"))
        else:
            response = client.post(path, json=case.get("json") or {})
        status = response.status_code
        try:
            data = response.get_json(silent=True)
        except Exception:
            data = None
        if data is None:
            data = {"_raw": response.get_data(as_text=True)[:400]}
        passed = bool(case["ok"](status, data))
        _out("--- %s ---" % label)
        _out("HTTP %s  %s" % (status, "PASS" if passed else "FAIL"))
        _out(_preview(data))
        _out("")
        return label, passed
    except Exception as exc:
        _out("--- %s ---" % label)
        _out("FAIL  exception: %s" % exc)
        _out("")
        return label, False


def main() -> int:
    _out("=" * 60)
    _out("Logistics Toolkit API smoke tests")
    _out("Flask test client (no bind). Prefer 127.0.0.1 for live HTTP.")
    _out("=" * 60)
    _out("")

    _prime_caches()
    cases = _cases()
    covered = {(c["method"], c["path"]) for c in cases}
    live = _json_api_routes()
    missing = [item for item in live if item not in covered]
    extra = [item for item in sorted(covered) if item not in set(live)]

    results: list[tuple[str, bool]] = []
    with app.test_client() as client:
        for case in cases:
            results.append(_run_one(client, case))

    if missing:
        _out("--- coverage ---")
        _out("FAIL  JSON routes in app.py not exercised:")
        for method, path in missing:
            _out("  %s %s" % (method, path))
            results.append(("%s %s" % (method, path), False))
        _out("")
    if extra:
        _out("--- coverage ---")
        _out("Note: harness has cases not in live url_map:")
        for method, path in extra:
            _out("  %s %s" % (method, path))
        _out("")

    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    _out("=" * 60)
    _out("TALLY  PASS=%s  FAIL=%s  TOTAL=%s" % (passed, failed, len(results)))
    for label, ok in results:
        _out("  %s  %s" % ("PASS" if ok else "FAIL", label))
    _out("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
