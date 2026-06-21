from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)

OANDA_API = "https://fxds-public-exchange-rates-api.oanda.com/cc-api/currencies"

CURRENCIES: dict[str, str] = {
    "AED": "UAE Dirham",
    "USD": "US Dollar",
    "OMR": "Omani Rial",
    "INR": "Indian Rupee",
    "QAR": "Qatar Riyal",
    "BHD": "Bahraini Dinar",
    "KWD": "Kuwaiti Dinar",
    "SAR": "Saudi Riyal",
}

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.oanda.com/currency-converter/en/",
    "Origin": "https://www.oanda.com",
    "Accept": "application/json, text/plain, */*",
}


def _chart_date_range() -> tuple[str, str]:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=90)
    return start.isoformat(), end.isoformat()


def fetch_usd_rate(quote: str, session: requests.Session | None = None) -> dict[str, Any]:
    if quote == "USD":
        return {
            "code": "USD",
            "rate": 1.0,
            "bid": 1.0,
            "ask": 1.0,
            "close_time": None,
        }

    start_date, end_date = _chart_date_range()
    params = {
        "base": "USD",
        "quote": quote,
        "data_type": "chart",
        "start_date": start_date,
        "end_date": end_date,
    }

    client = session or requests
    response = client.get(
        OANDA_API,
        params=params,
        headers=REQUEST_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("response") or []
    if not rows:
        raise ValueError(f"No OANDA rate data returned for USD->{quote}")

    latest = rows[-1]
    bid = float(latest["average_bid"])
    ask = float(latest["average_ask"])
    return {
        "code": quote,
        "rate": bid,
        "bid": bid,
        "ask": ask,
        "close_time": latest.get("close_time"),
    }


def fetch_all_rates() -> dict[str, Any]:
    session = requests.Session()
    rates: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for code in CURRENCIES:
        try:
            rates[code] = fetch_usd_rate(code, session=session)
        except Exception as exc:
            logger.exception("Failed to fetch USD->%s", code)
            errors.append(f"{code}: {exc}")

    if len(rates) < 2:
        raise RuntimeError(
            "Unable to load enough OANDA rates. " + "; ".join(errors)
        )

    return {
        "base": "USD",
        "rates": rates,
        "errors": errors,
    }