from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

IPT_UAE_URL = "https://www.ipt-energy.com/uae/fuel-prices"
ARAMCO_KSA_URL = (
    "https://www.aramco.com/en/what-we-do/energy-products/retail-fuels"
)
GPP_BASE = "https://www.globalpetrolprices.com"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

MONTH_PATTERN = (
    r"(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(20\d{2})"
)

UAE_GRADE_LABELS = ("E-plus 91", "Special 95", "Super 98", "Diesel")

GCC_COUNTRIES: tuple[dict[str, str], ...] = (
    {
        "name": "Saudi Arabia",
        "slug": "Saudi-Arabia",
        "currency": "SAR",
        "authority": "Saudi Aramco",
    },
    {
        "name": "Oman",
        "slug": "Oman",
        "currency": "OMR",
        "authority": "National Subsidy System",
    },
    {
        "name": "Qatar",
        "slug": "Qatar",
        "currency": "QAR",
        "authority": "Woqod (Q.P.S.C.)",
    },
    {
        "name": "Bahrain",
        "slug": "Bahrain",
        "currency": "BHD",
        "authority": "Bahrain official regulators",
    },
    {
        "name": "Kuwait",
        "slug": "Kuwait",
        "currency": "KWD",
        "authority": "Kuwait National Petroleum Company",
    },
)


def _http_get(
    session: requests.Session,
    url: str,
    *,
    timeout: int = 45,
) -> str:
    try:
        response = session.get(url, timeout=timeout, verify=True)
        response.raise_for_status()
        return response.text
    except RequestException as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc


def _parse_month_label(html: str) -> str | None:
    match = re.search(MONTH_PATTERN, html, re.IGNORECASE)
    if not match:
        return None
    return f"{match.group(1)} {match.group(2)}"


def _parse_uae_prices(html: str) -> dict[str, Any]:
    month = _parse_month_label(html)
    grades: list[dict[str, Any]] = []
    for label in UAE_GRADE_LABELS:
        match = re.search(
            rf">{re.escape(label)}</td>[\s\S]{{0,220}}?([\d.]+)\s*AED",
            html,
            re.IGNORECASE,
        )
        if not match:
            raise ValueError(f"UAE price not found for {label}")
        grades.append({"name": label, "price": float(match.group(1))})

    return {
        "country": "United Arab Emirates",
        "month": month,
        "currency": "AED",
        "unit": "per litre",
        "grades": grades,
        "source": "UAE Fuel Price Committee (via IPT Energy)",
        "source_url": IPT_UAE_URL,
    }


def _parse_aramco_prices(html: str) -> dict[str, Any] | None:
    month_match = re.search(r"Prices for the month of ([^<(]+)", html, re.IGNORECASE)
    if not month_match:
        return None

    month = month_match.group(1).strip()
    section = html[month_match.start() : month_match.start() + 4000]
    pairs = re.findall(
        r"<h3[^>]*>\s*([\d.]+)\s*</h3>\s*<[^>]+>\s*([^<]+)",
        section,
        re.IGNORECASE,
    )
    if not pairs:
        return None

    label_map = {
        "gasoline 91": "Gasoline 91",
        "gasoline 95": "Gasoline 95",
        "gasoline 98": "Gasoline 98",
        "diesel": "Diesel",
        "kerosene": "Kerosene",
    }
    grades: list[dict[str, Any]] = []
    for price_text, raw_label in pairs:
        key = raw_label.strip().lower()
        name = label_map.get(key)
        if not name:
            continue
        grades.append({"name": name, "price": float(price_text)})

    if not grades:
        return None

    return {
        "country": "Saudi Arabia",
        "month": month,
        "currency": "SAR",
        "unit": "per litre",
        "grades": grades,
        "gasoline_95": next(
            (g["price"] for g in grades if g["name"] == "Gasoline 95"),
            None,
        ),
        "diesel": next(
            (g["price"] for g in grades if g["name"] == "Diesel"),
            None,
        ),
        "source": "Saudi Aramco",
        "source_url": ARAMCO_KSA_URL,
    }


def _parse_gpp_fuel_price(
    html: str,
    country_name: str,
    fuel: str,
) -> tuple[str, float] | None:
    if fuel == "gasoline":
        pattern = (
            rf"gasoline price in\s+{re.escape(country_name)}\s+is\s+"
            rf"([A-Z]{{3}})\s+([\d.]+)\s+per liter"
        )
    else:
        pattern = (
            rf"diesel fuel in\s+{re.escape(country_name)}\s+is\s+"
            rf"([A-Z]{{3}})\s+([\d.]+)\s+per liter"
        )
    match = re.search(pattern, html, re.IGNORECASE)
    if not match:
        return None
    return match.group(1), float(match.group(2))


def _parse_gpp_updated_on(html: str) -> str | None:
    match = re.search(r"updated on\s+(\d{2}-[A-Za-z]{3}-\d{4})", html, re.IGNORECASE)
    return match.group(1) if match else None


def _fetch_gpp_country(
    session: requests.Session,
    meta: dict[str, str],
) -> dict[str, Any]:
    gasoline_html = _http_get(
        session,
        f"{GPP_BASE}/{meta['slug']}/gasoline_prices/",
    )
    diesel_html = _http_get(
        session,
        f"{GPP_BASE}/{meta['slug']}/diesel_prices/",
    )

    gasoline = _parse_gpp_fuel_price(gasoline_html, meta["name"], "gasoline")
    diesel = _parse_gpp_fuel_price(diesel_html, meta["name"], "diesel")
    if not gasoline or not diesel:
        raise ValueError(f"Could not parse GlobalPetrolPrices data for {meta['name']}")

    currency = gasoline[0]
    updated_on = _parse_gpp_updated_on(gasoline_html) or _parse_gpp_updated_on(
        diesel_html
    )
    month = _parse_month_label(gasoline_html) or _parse_month_label(diesel_html)

    return {
        "country": meta["name"],
        "month": month,
        "currency": currency,
        "unit": "per litre",
        "gasoline_95": gasoline[1],
        "diesel": diesel[1],
        "updated_on": updated_on,
        "source": f"{meta['authority']} (via GlobalPetrolPrices)",
        "source_url": f"{GPP_BASE}/{meta['slug']}/gasoline_prices/",
    }


def fetch_all_fuel_prices() -> dict[str, Any]:
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)

    errors: list[str] = []
    uae: dict[str, Any] | None = None
    gcc: list[dict[str, Any]] = []

    try:
        uae_html = _http_get(session, IPT_UAE_URL)
        uae = _parse_uae_prices(uae_html)
    except Exception as exc:
        logger.exception("Failed to fetch UAE fuel prices")
        errors.append(f"UAE: {exc}")

    saudi: dict[str, Any] | None = None
    try:
        aramco_html = _http_get(session, ARAMCO_KSA_URL, timeout=25)
        saudi = _parse_aramco_prices(aramco_html)
    except Exception as exc:
        logger.warning("Aramco direct fetch unavailable: %s", exc)

    for meta in GCC_COUNTRIES:
        if meta["name"] == "Saudi Arabia" and saudi:
            gcc.append(saudi)
            continue
        try:
            gcc.append(_fetch_gpp_country(session, meta))
        except Exception as exc:
            logger.exception("Failed to fetch fuel prices for %s", meta["name"])
            errors.append(f"{meta['name']}: {exc}")

    if uae is None and not gcc:
        raise RuntimeError(
            "Unable to load fuel prices. " + "; ".join(errors)
        )

    now = datetime.now(timezone.utc)
    return {
        "updated_at": now.isoformat(),
        "uae": uae,
        "gcc": gcc,
        "errors": errors,
    }