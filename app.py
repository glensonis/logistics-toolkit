from __future__ import annotations

import logging
import math
import os
import socket
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

from errors import UserInputError
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
LAN_HOST = "0.0.0.0"
PORT = 5000


def _resource_path(*parts: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


app = Flask(__name__, template_folder=_resource_path("templates"))
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1 MB request body limit


@app.errorhandler(413)
def _too_large(_exc):
    return jsonify({"error": "Request body too large (limit 1 MB)"}), 413

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
    except Exception:
        logger.exception("Rate refresh failed")
        with _cache_lock:
            _cache["errors"] = ["Currency rates unavailable"]


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
    except Exception:
        logger.exception("Fuel price refresh failed")
        with _fuel_lock:
            _fuel_cache["errors"] = ["Fuel prices unavailable"]


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


GENERIC_400 = "Invalid input: please check the values and try again"
GENERIC_500 = "Internal error while processing the request"
BAD_JSON_MSG = "Malformed JSON request body"


def _json_body():
    """Return (body, error_response). Malformed JSON gets its own 400."""
    raw = request.get_data(cache=True)
    if not raw or not raw.strip():
        return {}, None
    body = request.get_json(silent=True)
    if body is None:
        return None, (jsonify({"error": BAD_JSON_MSG}), 400)
    if not isinstance(body, dict):
        return None, (jsonify({"error": GENERIC_400}), 400)
    return body, None


class _Abort(Exception):
    """Carry a ready-made (safe) error response out of a handler."""

    def __init__(self, message, status):
        super().__init__(message)
        self.message = message
        self.status = status


def _safe_call(label, fn):
    """Run fn(); map errors to safe client responses, never echoing str(exc)."""
    try:
        return jsonify(fn())
    except _Abort as exc:
        return jsonify({"error": exc.message}), exc.status
    except UserInputError as exc:
        return jsonify({"error": str(exc)}), 400
    except (ValueError, TypeError, OverflowError) as exc:
        app.logger.info("%s rejected input (%s)", label, type(exc).__name__)
        return jsonify({"error": GENERIC_400}), 400
    except Exception:
        app.logger.exception("%s failed", label)
        return jsonify({"error": GENERIC_500}), 500


def _post_tool(label, handler):
    body, err = _json_body()
    if err:
        return err
    return _safe_call(label, lambda: _ensure_finite(handler(body)))


@app.route("/api/truck", methods=["POST"])
def api_truck():
    return _post_tool("Truck calculation", calculate_truck_requirement)


@app.route("/api/warehouse", methods=["POST"])
def api_warehouse():
    return _post_tool("Warehouse calculation", calculate_warehouse_space)


def _desk_post(handler):
    return _post_tool("Desk tool", handler)


@app.route("/api/quote", methods=["POST"])
def api_quote():
    return _desk_post(calculate_freight_quote)


@app.route("/api/chargeable-weight", methods=["POST"])
def api_chargeable():
    return _desk_post(calculate_chargeable_weight)


MAX_PERCENT = 1000.0


def _parse_num(value, field, *, default=None, minimum=0.0, exclusive_min=False, maximum=None):
    """Parse a finite float within bounds; raise UserInputError with a field-level message."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if default is None:
            raise UserInputError(f"{field} is required")
        return float(default)
    if isinstance(value, bool):
        raise UserInputError(f"{field} must be a number")
    try:
        num = float(value)
    except OverflowError:
        raise UserInputError(f"{field} is too large") from None
    except (TypeError, ValueError):
        raise UserInputError(f"{field} must be a number") from None
    if not math.isfinite(num):
        raise UserInputError(f"{field} must be a finite number")
    if exclusive_min and num <= minimum:
        raise UserInputError(f"{field} must be greater than {minimum:g}")
    if not exclusive_min and num < minimum:
        raise UserInputError(f"{field} must be {minimum:g} or more")
    if maximum is not None and num > maximum:
        raise UserInputError(f"{field} must be {maximum:g} or less")
    return num


def _all_finite(value) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_all_finite(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return all(_all_finite(v) for v in value)
    return True


def _ensure_finite(result):
    if not _all_finite(result):
        raise UserInputError("Inputs are too large to calculate a result")
    return result


@app.route("/api/fuel-surcharge")
def api_fuel_surcharge():
    def run():
        baseline = _parse_num(request.args.get("baseline"), "Baseline", default=3.5, exclusive_min=True)
        current_param = request.args.get("current")
        if current_param is not None:
            current = _parse_num(current_param, "Current price")
            currency = request.args.get("currency", "LOCAL")
        else:
            snap = _fuel_snapshot() or {}
            uae = snap.get("uae") or {}
            currency = uae.get("currency", "AED")
            grades = uae.get("grades") or []
            diesel = next((g for g in grades if "diesel" in str(g.get("name", "")).lower()), None)
            if not diesel:
                raise _Abort("Diesel price unavailable", 503)
            try:
                current = float(diesel["price"])
            except (KeyError, TypeError, ValueError, OverflowError):
                current = float("nan")
            if not math.isfinite(current) or current < 0:
                app.logger.warning("Fuel feed returned an unusable diesel price")
                raise _Abort("Diesel price unavailable", 503)
        return _ensure_finite(calculate_fuel_surcharge(baseline, current, currency=currency))

    return _safe_call("Fuel surcharge", run)


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
    body, err = _json_body()
    if err:
        return err

    def run():
        qty = _parse_num(body.get("quantity"), "Quantity", default=1, minimum=1)
        if qty != int(qty):
            raise UserInputError("Quantity must be a whole number")
        clean = {
            "goods_value": _parse_num(body.get("goods_value"), "Goods value", exclusive_min=True),
            "quantity": int(qty),
            "duty_percent": _parse_num(body.get("duty_percent"), "Duty %", default=0, maximum=MAX_PERCENT),
            "vat_percent": _parse_num(body.get("vat_percent"), "VAT %", default=0, maximum=MAX_PERCENT),
            "clearance_fees": _parse_num(body.get("clearance_fees"), "Clearance fees", default=0),
            "other_fees": _parse_num(body.get("other_fees"), "Other fees", default=0),
            "to_currency": str(body.get("to_currency") or "AED").upper(),
        }
        fx = _parse_num(body.get("fx_rate"), "FX rate", default=0)
        if fx <= 0:
            data = _snapshot() or {}
            rates = data.get("rates") or {}
            from_ccy = str(body.get("from_currency") or "USD").upper()
            to_ccy = clean["to_currency"]
            if from_ccy not in rates or to_ccy not in rates:
                raise _Abort("Rates not loaded", 503)
            try:
                fx = float(rates[to_ccy]["rate"]) / float(rates[from_ccy]["rate"])
            except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
                fx = float("nan")
            if not math.isfinite(fx) or fx <= 0:
                app.logger.warning("Rate feed returned unusable data")
                raise _Abort("Rates not loaded", 503)
        try:
            result = calculate_landed_cost(clean, fx)
        except OverflowError:
            raise UserInputError("Inputs are too large to calculate a result") from None
        return _ensure_finite(result)

    return _safe_call("Landed cost", run)


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


def _lan_mode() -> bool:
    return "--lan" in sys.argv[1:] or os.environ.get("LOGISTICS_LAN") == "1"


def _lan_ip() -> str | None:
    # UDP connect() only selects the outbound interface; no packet is sent.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def main() -> None:
    lan = _lan_mode()
    bind_host = LAN_HOST if lan else HOST
    if not _is_frozen():
        print("=" * 52)
        print("  Logistics Toolkit (FX, Fuel, Truck, Warehouse)")
        print("=" * 52)
        print(f"  Starting server at http://{HOST}:{PORT}")
        if lan:
            ip = _lan_ip()
            if ip:
                print(f"  LAN sharing ON - other devices open http://{ip}:{PORT}")
            else:
                print(f"  LAN sharing ON - open http://<this-PC-IP>:{PORT} on other devices")
            print("  Home network only: there is no login. Do not port-forward.")
        print("  Close the browser tab when finished, then stop this window.")
        print("=" * 52)

    _refresh_rates()
    _refresh_fuel_prices()
    threading.Thread(target=_background_worker, daemon=True).start()
    threading.Thread(target=_fuel_background_worker, daemon=True).start()
    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host=bind_host, port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()