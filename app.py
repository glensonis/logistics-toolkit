from __future__ import annotations

import logging
import os
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

from fuel_fetcher import fetch_all_fuel_prices
from logistics_calculators import calculate_truck_requirement, calculate_warehouse_space
from logistics_chargeable import calculate_chargeable_weight
from logistics_desk_tools import (
    calculate_fifo_fefo,
    calculate_free_time,
    calculate_inventory_doh,
    calculate_landed_cost,
    calculate_multi_stop,
    calculate_pallet_build,
    calculate_receiving_capacity,
    calculate_transit_eta,
    calculate_trip_cost,
    check_dg_segregation,
    generate_doc_checklist,
)
from logistics_fuel_surcharge import calculate_fuel_surcharge
from logistics_quote import calculate_freight_quote
from oanda_fetcher import CURRENCIES, fetch_all_rates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 5 * 60
FUEL_REFRESH_INTERVAL_SECONDS = 60 * 60
HOST = "127.0.0.1"
PORT = 5000


def _resource_path(*parts: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


app = Flask(__name__, template_folder=_resource_path("templates"))

_cache_lock = threading.Lock()
_cache: dict = {
    "rates": None,
    "updated_at": None,
    "next_refresh_at": None,
    "errors": [],
    "source": "OANDA",
}

_fuel_lock = threading.Lock()
_fuel_cache: dict = {
    "uae": None,
    "gcc": None,
    "updated_at": None,
    "next_refresh_at": None,
    "errors": [],
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _refresh_rates() -> None:
    logger.info("Refreshing currency rates from OANDA...")
    try:
        payload = fetch_all_rates()
        now = _utc_now()
        with _cache_lock:
            _cache["rates"] = payload["rates"]
            _cache["updated_at"] = now.isoformat()
            _cache["next_refresh_at"] = (
                now.timestamp() + REFRESH_INTERVAL_SECONDS
            )
            _cache["errors"] = payload.get("errors", [])
        logger.info("Rates updated successfully")
    except Exception as exc:
        logger.exception("Rate refresh failed")
        with _cache_lock:
            _cache["errors"] = [str(exc)]


def _refresh_fuel_prices() -> None:
    logger.info("Refreshing fuel prices from official sources...")
    try:
        payload = fetch_all_fuel_prices()
        now = _utc_now()
        with _fuel_lock:
            _fuel_cache["uae"] = payload.get("uae")
            _fuel_cache["gcc"] = payload.get("gcc")
            _fuel_cache["updated_at"] = payload.get("updated_at") or now.isoformat()
            _fuel_cache["next_refresh_at"] = (
                now.timestamp() + FUEL_REFRESH_INTERVAL_SECONDS
            )
            _fuel_cache["errors"] = payload.get("errors", [])
        logger.info("Fuel prices updated successfully")
    except Exception as exc:
        logger.exception("Fuel price refresh failed")
        with _fuel_lock:
            _fuel_cache["errors"] = [str(exc)]


def _background_worker() -> None:
    while True:
        _refresh_rates()
        time.sleep(REFRESH_INTERVAL_SECONDS)


def _fuel_background_worker() -> None:
    while True:
        _refresh_fuel_prices()
        time.sleep(FUEL_REFRESH_INTERVAL_SECONDS)


def _snapshot() -> dict:
    with _cache_lock:
        return {
            "currencies": CURRENCIES,
            "rates": _cache["rates"],
            "updated_at": _cache["updated_at"],
            "next_refresh_at": _cache["next_refresh_at"],
            "refresh_interval_seconds": REFRESH_INTERVAL_SECONDS,
            "errors": list(_cache["errors"]),
            "source": _cache["source"],
        }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/rates")
def api_rates():
    return jsonify(_snapshot())


def _fuel_snapshot() -> dict:
    with _fuel_lock:
        return {
            "uae": _fuel_cache["uae"],
            "gcc": _fuel_cache["gcc"],
            "updated_at": _fuel_cache["updated_at"],
            "next_refresh_at": _fuel_cache["next_refresh_at"],
            "refresh_interval_seconds": FUEL_REFRESH_INTERVAL_SECONDS,
            "errors": list(_fuel_cache["errors"]),
        }


@app.route("/api/fuel-prices")
def api_fuel_prices():
    return jsonify(_fuel_snapshot())


@app.route("/api/convert")
def api_convert():
    data = _snapshot()
    rates = data.get("rates") or {}

    try:
        amount = float(request.args.get("amount", "1"))
    except ValueError:
        return jsonify({"error": "Invalid amount"}), 400

    from_ccy = request.args.get("from", "USD").upper()
    to_ccy = request.args.get("to", "AED").upper()

    if from_ccy not in CURRENCIES or to_ccy not in CURRENCIES:
        return jsonify({"error": "Unsupported currency"}), 400

    if from_ccy not in rates or to_ccy not in rates:
        return jsonify({"error": "Rates not loaded yet"}), 503

    from_rate = rates[from_ccy]["rate"]
    to_rate = rates[to_ccy]["rate"]
    if from_rate <= 0:
        return jsonify({"error": "Invalid source rate"}), 500

    usd_amount = amount / from_rate
    converted = usd_amount * to_rate
    cross_rate = to_rate / from_rate

    return jsonify(
        {
            "from": from_ccy,
            "to": to_ccy,
            "amount": amount,
            "result": converted,
            "rate": cross_rate,
            "updated_at": data.get("updated_at"),
            "source": data.get("source"),
        }
    )


@app.route("/api/truck", methods=["POST"])
def api_truck():
    try:
        return jsonify(calculate_truck_requirement(request.get_json(silent=True) or {}))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Truck calculation failed")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/warehouse", methods=["POST"])
def api_warehouse():
    try:
        return jsonify(calculate_warehouse_space(request.get_json(silent=True) or {}))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Warehouse calculation failed")
        return jsonify({"error": str(exc)}), 500


def _desk_post(handler):
    try:
        return jsonify(handler(request.get_json(silent=True) or {}))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Desk tool failed")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/quote", methods=["POST"])
def api_quote():
    return _desk_post(calculate_freight_quote)


@app.route("/api/chargeable-weight", methods=["POST"])
def api_chargeable():
    return _desk_post(calculate_chargeable_weight)


@app.route("/api/fuel-surcharge")
def api_fuel_surcharge():
    baseline = float(request.args.get("baseline", 3.5))
    current_param = request.args.get("current")
    currency = "AED"
    if current_param is not None:
        current = float(current_param)
        currency = request.args.get("currency", "LOCAL")
    else:
        snap = _fuel_snapshot()
        uae = snap.get("uae") or {}
        currency = uae.get("currency", "AED")
        grades = uae.get("grades") or []
        diesel = next((g for g in grades if "diesel" in str(g.get("name", "")).lower()), None)
        if not diesel:
            return jsonify({"error": "Diesel price unavailable"}), 503
        current = float(diesel["price"])
    try:
        return jsonify(calculate_fuel_surcharge(baseline, current, currency=currency))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/receiving", methods=["POST"])
def api_receiving():
    return _desk_post(calculate_receiving_capacity)


@app.route("/api/inventory-doh", methods=["POST"])
def api_inventory_doh():
    return _desk_post(calculate_inventory_doh)


@app.route("/api/pallet-build", methods=["POST"])
def api_pallet_build():
    return _desk_post(calculate_pallet_build)


@app.route("/api/fifo-fefo", methods=["POST"])
def api_fifo_fefo():
    return _desk_post(calculate_fifo_fefo)


@app.route("/api/landed-cost", methods=["POST"])
def api_landed_cost():
    body = request.get_json(silent=True) or {}
    fx = float(body.get("fx_rate") or 0)
    if fx <= 0:
        data = _snapshot()
        rates = data.get("rates") or {}
        from_ccy = str(body.get("from_currency") or "USD").upper()
        to_ccy = str(body.get("to_currency") or "AED").upper()
        if from_ccy not in rates or to_ccy not in rates:
            return jsonify({"error": "Rates not loaded"}), 503
        fx = rates[to_ccy]["rate"] / rates[from_ccy]["rate"]
    try:
        return jsonify(calculate_landed_cost(body, fx))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/doc-checklist", methods=["POST"])
def api_doc_checklist():
    return _desk_post(generate_doc_checklist)


@app.route("/api/dg-segregation", methods=["POST"])
def api_dg_segregation():
    return _desk_post(check_dg_segregation)


@app.route("/api/trip-cost", methods=["POST"])
def api_trip_cost():
    return _desk_post(calculate_trip_cost)


@app.route("/api/transit-eta", methods=["POST"])
def api_transit_eta():
    return _desk_post(calculate_transit_eta)


@app.route("/api/free-time", methods=["POST"])
def api_free_time():
    return _desk_post(calculate_free_time)


@app.route("/api/multi-stop", methods=["POST"])
def api_multi_stop():
    return _desk_post(calculate_multi_stop)


def _open_browser() -> None:
    time.sleep(1.5)
    webbrowser.open(f"http://{HOST}:{PORT}")


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def main() -> None:
    if not _is_frozen():
        print("=" * 52)
        print("  Logistics Toolkit (FX, Fuel, Truck, Warehouse)")
        print("=" * 52)
        print(f"  Starting server at http://{HOST}:{PORT}")
        print("  Close the browser tab when finished, then stop this window.")
        print("=" * 52)

    _refresh_rates()
    _refresh_fuel_prices()
    threading.Thread(target=_background_worker, daemon=True).start()
    threading.Thread(target=_fuel_background_worker, daemon=True).start()
    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()