import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module  # noqa: E402

G400 = app_module.GENERIC_400
G500 = app_module.GENERIC_500
SECRET = "SECRET_INTERNAL_DETAIL /etc/passwd"
HUGE = "9" * 400


@pytest.fixture()
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def _err(r):
    data = r.get_json()
    assert set(data) == {"error"}
    return data["error"]


# ---- fuel surcharge ----
@pytest.mark.parametrize("qs,msg", [
    ("current=abc", "Current price must be a number"),
    ("current=-1", "Current price must be 0 or more"),
    ("baseline=xyz&current=3", "Baseline must be a number"),
    ("baseline=-2&current=3", "Baseline must be greater than 0"),
    ("baseline=0&current=3", "Baseline must be greater than 0"),
    ("current=nan", "Current price must be a finite number"),
    ("current=inf", "Current price must be a finite number"),
    ("current=", "Current price is required"),
    (f"current={HUGE}", None),
    (f"baseline={HUGE}&current=3", None),
])
def test_fuel_surcharge_bad_input(client, qs, msg):
    r = client.get(f"/api/fuel-surcharge?{qs}")
    assert r.status_code == 400
    e = _err(r)
    if msg:
        assert e == msg
    assert HUGE not in e and "could not convert" not in e


def test_fuel_surcharge_huge_int_is_400_not_500(client):
    r = client.get(f"/api/fuel-surcharge?baseline=3&current={'9' * 400}")
    assert r.status_code == 400


def test_fuel_surcharge_valid(client):
    r = client.get("/api/fuel-surcharge?baseline=3.5&current=4.0&currency=AED")
    assert r.status_code == 200
    assert "fsc_percent" in r.get_json()


# ---- landed cost ----
VALID = {"fx_rate": 3.6725, "goods_value": 1000, "quantity": 10,
         "duty_percent": 5, "vat_percent": 5, "to_currency": "AED"}


@pytest.mark.parametrize("patch,msg", [
    ({"goods_value": "abc"}, "Goods value must be a number"),
    ({"goods_value": None}, "Goods value is required"),
    ({"goods_value": -5}, "Goods value must be greater than 0"),
    ({"goods_value": 0}, "Goods value must be greater than 0"),
    ({"fx_rate": "bad"}, "FX rate must be a number"),
    ({"fx_rate": -1}, "FX rate must be 0 or more"),
    ({"duty_percent": "x"}, "Duty % must be a number"),
    ({"vat_percent": -5}, "VAT % must be 0 or more"),
    ({"duty_percent": "1e308"}, "Duty % must be 1000 or less"),
    ({"vat_percent": "1e308"}, "VAT % must be 1000 or less"),
    ({"duty_percent": 1001}, "Duty % must be 1000 or less"),
    ({"quantity": 0}, "Quantity must be 1 or more"),
    ({"quantity": 2.5}, "Quantity must be a whole number"),
    ({"goods_value": HUGE}, None),
    ({"clearance_fees": "1e308", "other_fees": "1e308"}, "Inputs are too large to calculate a result"),
])
def test_landed_cost_bad_input(client, patch, msg):
    body = {**VALID, **patch}
    r = client.post("/api/landed-cost", json=body)
    assert r.status_code == 400
    e = _err(r)
    if msg:
        assert e == msg
    assert HUGE not in e


def test_landed_cost_non_object_body(client):
    r = client.post("/api/landed-cost", json=[1, 2, 3])
    assert r.status_code == 400
    assert _err(r) == G400


def test_landed_cost_bad_json(client):
    r = client.post("/api/landed-cost", data="{not json", content_type="application/json")
    assert r.status_code == 400
    assert _err(r) == app_module.BAD_JSON_MSG


def test_landed_cost_valid_and_quantity_respected(client):
    r = client.post("/api/landed-cost", json=VALID)
    assert r.status_code == 200
    d = r.get_json()
    assert d["landed_total"] > 0
    assert d["landed_per_unit"] == pytest.approx(d["landed_total"] / 10, abs=0.01)


def test_landed_cost_passes_parsed_numbers(client):
    with mock.patch.object(app_module, "calculate_landed_cost", return_value={"ok": 1.0}) as m:
        r = client.post("/api/landed-cost", json={**VALID, "goods_value": "1000", "duty_percent": "5"})
    assert r.status_code == 200
    payload, fx = m.call_args[0]
    assert payload["goods_value"] == 1000.0 and payload["duty_percent"] == 5.0
    assert payload["quantity"] == 10 and fx == pytest.approx(3.6725)


# ---- truck / warehouse / desk tools ----
@pytest.mark.parametrize("path,target", [
    ("/api/truck", "calculate_truck_requirement"),
    ("/api/warehouse", "calculate_warehouse_space"),
])
def test_unexpected_exception_does_not_leak(client, path, target):
    with mock.patch.object(app_module, target, side_effect=RuntimeError(SECRET)):
        r = client.post(path, json={})
    assert r.status_code == 500
    assert _err(r) == G500
    assert SECRET not in r.get_data(as_text=True)


@pytest.mark.parametrize("path,target", [
    ("/api/truck", "calculate_truck_requirement"),
    ("/api/warehouse", "calculate_warehouse_space"),
])
def test_plain_valueerror_is_generic_400(client, path, target):
    with mock.patch.object(app_module, target, side_effect=ValueError(SECRET)):
        r = client.post(path, json={})
    assert r.status_code == 400
    assert _err(r) == G400
    assert SECRET not in r.get_data(as_text=True)


@pytest.mark.parametrize("path,target", [
    ("/api/truck", "calculate_truck_requirement"),
    ("/api/warehouse", "calculate_warehouse_space"),
])
def test_user_input_error_message_shown(client, path, target):
    with mock.patch.object(app_module, target, side_effect=app_module.UserInputError("Enter total weight")):
        r = client.post(path, json={})
    assert r.status_code == 400
    assert _err(r) == "Enter total weight"


@pytest.mark.parametrize("path", ["/api/truck", "/api/warehouse", "/api/quote"])
def test_malformed_json_400(client, path):
    r = client.post(path, data="{oops", content_type="application/json")
    assert r.status_code == 400
    assert _err(r) == app_module.BAD_JSON_MSG


def test_truck_real_validation_message(client):
    r = client.post("/api/truck", json={})
    assert r.status_code == 400
    assert "Traceback" not in r.get_data(as_text=True)


def test_desk_post_does_not_leak_exception(client):
    def boom(_payload):
        raise RuntimeError(SECRET)

    with app_module.app.test_request_context("/x", method="POST", json={}):
        resp, status = app_module._desk_post(boom)
    assert status == 500
    assert SECRET not in resp.get_data(as_text=True)
    assert resp.get_json() == {"error": G500}


def test_desk_post_plain_valueerror_generic(client):
    def bad(_payload):
        raise ValueError(SECRET)

    with app_module.app.test_request_context("/x", method="POST", json={}):
        resp, status = app_module._desk_post(bad)
    assert status == 400
    assert resp.get_json() == {"error": G400}


def test_logs_do_not_contain_raw_input(client, caplog):
    caplog.set_level("INFO")
    with mock.patch.object(app_module, "calculate_truck_requirement", side_effect=ValueError(SECRET)):
        client.post("/api/truck", json={})
    client.get(f"/api/fuel-surcharge?current={HUGE}")
    assert SECRET not in caplog.text
    assert HUGE not in caplog.text
