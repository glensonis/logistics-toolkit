import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module  # noqa: E402

SAFE = app_module.BAD_INPUT_MSG


@pytest.fixture()
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


@pytest.mark.parametrize("qs", [
    "current=abc", "current=-1", "baseline=xyz&current=3", "baseline=-2&current=3",
    "current=nan", "current=", "current=inf",
])
def test_fuel_surcharge_bad_input(client, qs):
    r = client.get(f"/api/fuel-surcharge?{qs}")
    assert r.status_code == 400
    assert r.get_json() == {"error": SAFE}
    assert "could not convert" not in r.get_data(as_text=True)


def test_fuel_surcharge_valid(client):
    r = client.get("/api/fuel-surcharge?baseline=3.5&current=4.0&currency=AED")
    assert r.status_code == 200
    assert isinstance(r.get_json(), dict)


@pytest.mark.parametrize("body", [
    {"fx_rate": 1, "goods_value": "abc"},
    {"fx_rate": 1},
    {"fx_rate": 1, "goods_value": -5},
    {"fx_rate": "bad", "goods_value": 100},
    {"fx_rate": -1, "goods_value": 100},
    {"fx_rate": 1, "goods_value": 100, "duty_percent": "x"},
    {"fx_rate": 1, "goods_value": 100, "vat_percent": -5},
    [1, 2, 3],
])
def test_landed_cost_bad_input(client, body):
    r = client.post("/api/landed-cost", json=body)
    assert r.status_code == 400
    assert r.get_json() == {"error": SAFE}


def test_landed_cost_bad_json(client):
    r = client.post("/api/landed-cost", data="{not json", content_type="application/json")
    assert r.status_code == 400
    assert r.get_json() == {"error": SAFE}


def test_landed_cost_valid(client):
    r = client.post("/api/landed-cost", json={
        "fx_rate": 3.6725, "goods_value": 1000, "quantity": 10,
        "duty_percent": 5, "vat_percent": 5, "to_currency": "AED"})
    assert r.status_code == 200
    assert "landed_total" in r.get_json()


def test_desk_post_does_not_leak_exception(client):
    secret = "SECRET_INTERNAL_DETAIL /etc/passwd"

    def boom(_payload):
        raise RuntimeError(secret)

    with app_module.app.test_request_context("/x", method="POST", json={}):
        resp, status = app_module._desk_post(boom)
    assert status == 500
    assert secret not in resp.get_data(as_text=True)
    assert resp.get_json() == {"error": "Internal error while processing the request"}
