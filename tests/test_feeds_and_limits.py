import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module  # noqa: E402
import fuel_fetcher  # noqa: E402
import oanda_fetcher  # noqa: E402

SECRET = "SECRET_TOKEN_abc123 https://internal.example/x?key=zzz"


@pytest.fixture()
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


# ---- cache error leak ----
def test_rates_refresh_failure_cached_safely(client):
    with mock.patch.object(app_module, "fetch_all_rates", side_effect=RuntimeError(SECRET)):
        app_module._refresh_rates()
    body = client.get("/api/rates").get_data(as_text=True)
    assert SECRET not in body
    assert client.get("/api/rates").get_json()["errors"] == ["Currency rates unavailable"]


def test_fuel_refresh_failure_cached_safely(client):
    with mock.patch.object(app_module, "fetch_all_fuel_prices", side_effect=RuntimeError(SECRET)):
        app_module._refresh_fuel_prices()
    body = client.get("/api/fuel-prices").get_data(as_text=True)
    assert SECRET not in body
    assert client.get("/api/fuel-prices").get_json()["errors"] == ["Fuel prices unavailable"]


def test_fuel_fetcher_error_list_is_safe():
    def fail(*_a, **_k):
        raise RuntimeError(SECRET)

    with mock.patch.object(fuel_fetcher, "_http_get", side_effect=fail), \
         mock.patch.object(fuel_fetcher, "_fetch_gpp_country",
                           side_effect=lambda s, m: {"name": m["name"], "grades": []}):
        payload = fuel_fetcher.fetch_all_fuel_prices()
    errs = payload["errors"]
    assert "UAE prices unavailable" in errs
    assert all(SECRET not in e for e in errs)


def test_fuel_fetcher_total_failure_message_is_safe():
    with mock.patch.object(fuel_fetcher, "_http_get", side_effect=RuntimeError(SECRET)), \
         mock.patch.object(fuel_fetcher, "_fetch_gpp_country", side_effect=RuntimeError(SECRET)):
        with pytest.raises(RuntimeError) as ei:
            fuel_fetcher.fetch_all_fuel_prices()
    assert SECRET not in str(ei.value)


def test_fuel_http_get_wraps_without_url_or_detail():
    from requests import RequestException

    sess = mock.Mock()
    sess.get.side_effect = RequestException(SECRET)
    with pytest.raises(RuntimeError) as ei:
        fuel_fetcher._http_get(sess, "https://internal.example/secret")
    assert SECRET not in str(ei.value) and "internal.example" not in str(ei.value)


def test_oanda_error_list_is_safe():
    calls = {"n": 0}

    def rate(code, session=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError(SECRET)
        return {"rate": 1.0}

    with mock.patch.object(oanda_fetcher, "fetch_usd_rate", side_effect=rate):
        payload = oanda_fetcher.fetch_all_rates()
    assert payload["errors"] and all(SECRET not in e for e in payload["errors"])
    assert payload["errors"][0].endswith("rate unavailable")


def test_oanda_total_failure_message_is_safe():
    with mock.patch.object(oanda_fetcher, "fetch_usd_rate", side_effect=RuntimeError(SECRET)):
        with pytest.raises(RuntimeError) as ei:
            oanda_fetcher.fetch_all_rates()
    assert SECRET not in str(ei.value)


# ---- NaN / inf on quote ----
@pytest.mark.parametrize("field,val", [
    ("weight_kg", "inf"), ("weight_kg", "nan"), ("weight_kg", "-inf"),
    ("base_rate", "inf"), ("volume_cbm", "nan"), ("margin_percent", "inf"),
])
def test_quote_non_finite_is_400(client, field, val):
    r = client.post("/api/quote", json={"rate_basis": "per_kg", "base_rate": 2, "weight_kg": 100, field: val})
    assert r.status_code == 400
    text = r.get_data(as_text=True)
    assert "nan" not in text.lower() and "Infinity" not in text


def test_post_tool_result_nested_nan_rejected(client):
    with mock.patch.object(app_module, "calculate_truck_requirement",
                           return_value={"a": {"b": [1.0, float("nan")]}}):
        r = client.post("/api/truck", json={})
    assert r.status_code == 400
    assert r.get_json() == {"error": "Inputs are too large to calculate a result"}


def test_quote_valid_still_ok(client):
    r = client.post("/api/quote", json={"rate_basis": "per_kg", "base_rate": 2, "weight_kg": 100})
    assert r.status_code == 200


# ---- 503 feed failures ----
def test_fuel_surcharge_bad_diesel_price_503(client):
    snap = {"uae": {"currency": "AED", "grades": [{"name": "Diesel", "price": "n/a"}]}}
    with mock.patch.object(app_module, "_fuel_snapshot", return_value=snap):
        r = client.get("/api/fuel-surcharge")
    assert r.status_code == 503
    assert r.get_json() == {"error": "Diesel price unavailable"}


def test_fuel_surcharge_missing_snapshot_503(client):
    with mock.patch.object(app_module, "_fuel_snapshot", return_value=None):
        r = client.get("/api/fuel-surcharge")
    assert r.status_code == 503


@pytest.mark.parametrize("rates", [
    None,
    {"USD": {"rate": 1.0}},
    {"USD": {"rate": 1.0}, "AED": {}},
    {"USD": {"rate": 0}, "AED": {"rate": 3.67}},
    {"USD": {"rate": "x"}, "AED": {"rate": 3.67}},
])
def test_landed_cost_rate_feed_failure_503(client, rates):
    with mock.patch.object(app_module, "_snapshot", return_value={"rates": rates}):
        r = client.post("/api/landed-cost", json={"goods_value": 100, "quantity": 1})
    assert r.status_code == 503
    assert r.get_json() == {"error": "Rates not loaded"}


def test_landed_cost_missing_snapshot_503(client):
    with mock.patch.object(app_module, "_snapshot", return_value=None):
        r = client.post("/api/landed-cost", json={"goods_value": 100})
    assert r.status_code == 503


# ---- 413 ----
@pytest.mark.parametrize("path", ["/api/quote", "/api/landed-cost", "/api/truck"])
def test_body_too_large_413(client, path):
    big = '{"x":"' + "a" * (1024 * 1024 + 10) + '"}'
    r = client.post(path, data=big, content_type="application/json")
    assert r.status_code == 413
    assert r.get_json() == {"error": "Request body too large (limit 1 MB)"}


# ---- /api/convert ----
import json  # noqa: E402

RATES = {"rates": {"USD": {"rate": 1.0}, "AED": {"rate": 3.6725}}, "updated_at": None, "source": "OANDA"}


@pytest.mark.parametrize("amount", ["inf", "nan", "-inf", "1e308", "9" * 400])
def test_convert_non_finite_amount_400(client, amount):
    with mock.patch.object(app_module, "_snapshot", return_value=RATES):
        r = client.get(f"/api/convert?amount={amount}&from=USD&to=AED")
    assert r.status_code == 400
    body = json.loads(r.get_data(as_text=True))  # strict-ish: must parse
    assert set(body) == {"error"}
    assert "NaN" not in r.get_data(as_text=True) and "Infinity" not in r.get_data(as_text=True)


@pytest.mark.parametrize("rates", [
    {"USD": {"rate": "x"}, "AED": {"rate": 3.67}},
    {"USD": {"rate": 1.0}, "AED": {}},
    {"USD": {"rate": 1.0}},
    None,
])
def test_convert_bad_rate_503_json(client, rates):
    with mock.patch.object(app_module, "_snapshot", return_value={"rates": rates}):
        r = client.get("/api/convert?amount=10&from=USD&to=AED")
    assert r.status_code == 503
    assert r.is_json
    assert r.get_json() == {"error": "Rates not loaded yet"}


def test_convert_valid(client):
    with mock.patch.object(app_module, "_snapshot", return_value=RATES):
        r = client.get("/api/convert?amount=10&from=USD&to=AED")
    assert r.status_code == 200
    assert r.get_json()["result"] == pytest.approx(36.725)


def test_allow_nan_disabled():
    assert app_module.app.json.allow_nan is False
