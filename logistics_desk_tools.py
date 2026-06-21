"""Desk calculators — parity with glensonis.com/logistics APIs."""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Any

from logistics_calculators import calculate_truck_requirement
from logistics_chargeable import calculate_chargeable_weight
from logistics_fuel_surcharge import calculate_fuel_surcharge
from logistics_quote import calculate_freight_quote

def _round2(n: float) -> float:
    return round(n * 100) / 100


def _num(v: Any, fallback: float = 0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return fallback


def _int(v: Any, fallback: int = 0) -> int:
    return int(_num(v, fallback))


def _positive(v: Any, field: str) -> float:
    n = _num(v)
    if n <= 0:
        raise ValueError(f"{field} must be greater than zero")
    return n


def _bool(v: Any) -> bool:
    return v is True or str(v).lower() in {"true", "1", "yes"}


def _parse_date(v: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError as exc:
        raise ValueError(f"Invalid {field}") from exc


SEGREGATION_MATRIX: dict[str, list[str]] = {
    "1": ["2", "3", "4", "5", "6", "7", "8", "9"],
    "2": ["1", "3", "4", "5", "6", "7", "8"],
    "3": ["1", "2", "4", "5", "6", "7", "8"],
    "4": ["1", "2", "3", "5", "6", "7", "8"],
    "5": ["1", "2", "3", "4", "6", "7", "8"],
    "6": ["1", "2", "3", "4", "5", "7", "8"],
    "7": ["1", "2", "3", "4", "5", "6", "8", "9"],
    "8": ["1", "2", "3", "4", "5", "6", "7", "9"],
    "9": ["1", "7", "8"],
}

DOC_LIBRARY = [
    {"id": "invoice", "label": "Commercial invoice", "tags": ["base"]},
    {"id": "packing", "label": "Packing list", "tags": ["base"]},
    {"id": "coo", "label": "Certificate of origin", "tags": ["cross_border"]},
    {"id": "bol", "label": "Bill of lading / CMR", "tags": ["base"]},
    {"id": "msds", "label": "MSDS / SDS", "tags": ["dg"]},
    {"id": "dg_decl", "label": "Dangerous goods declaration", "tags": ["dg"]},
    {"id": "temp_log", "label": "Temperature monitoring record", "tags": ["reefer"]},
    {"id": "insurance", "label": "Insurance certificate", "tags": ["high_value", "insurance"]},
    {"id": "import_permit", "label": "Import permit / license", "tags": ["cross_border"]},
]


def calculate_receiving_capacity(payload: dict[str, Any]) -> dict[str, Any]:
    docks = max(1, _int(payload.get("dock_count"), 1))
    hours = _positive(payload.get("hours_per_day"), "Hours per day")
    unload_min = _positive(payload.get("avg_unload_minutes"), "Average unload time")
    scheduled = max(0, _int(payload.get("trucks_scheduled"), 0))
    slots_per_dock = int((hours * 60) // unload_min)
    total_slots = slots_per_dock * docks
    utilization = min(100.0, (scheduled / total_slots) * 100) if total_slots else 100.0
    overload = scheduled > total_slots
    spare = max(0, total_slots - scheduled)
    return {
        "summary": (
            f"Over capacity: {scheduled} trucks vs {total_slots} slots."
            if overload
            else f"{spare} spare dock slots ({_round2(utilization)}% utilized)."
        ),
        "total_slots": total_slots,
        "utilization_pct": _round2(utilization),
        "overload": overload,
        "spare_slots": spare,
    }


def calculate_inventory_doh(payload: dict[str, Any]) -> dict[str, Any]:
    on_hand = _positive(payload.get("on_hand_qty"), "On-hand quantity")
    daily = _positive(payload.get("daily_outbound"), "Daily outbound")
    lead = max(0, _num(payload.get("lead_time_days")))
    safety = max(0, _num(payload.get("safety_stock_days")))
    doh = on_hand / daily
    reorder = (lead + safety) * daily
    below = on_hand <= reorder
    return {
        "summary": (
            f"Below reorder point. {_round2(doh)} days on hand."
            if below
            else f"{_round2(doh)} days on hand. Reorder below {_round2(reorder)} units."
        ),
        "days_on_hand": _round2(doh),
        "reorder_point": _round2(reorder),
        "below_reorder": below,
    }


def calculate_pallet_build(payload: dict[str, Any]) -> dict[str, Any]:
    per_layer = max(1, _int(payload.get("cartons_per_layer"), 1))
    layers = max(1, _int(payload.get("layers"), 1))
    carton_kg = _positive(payload.get("carton_weight_kg"), "Carton weight")
    max_kg = _positive(payload.get("max_stack_weight_kg"), "Max stack weight")
    total_cartons = per_layer * layers
    total_weight = total_cartons * carton_kg
    weight_ok = total_weight <= max_kg
    return {
        "summary": (
            f"Stack weight {_round2(total_weight)} kg exceeds {_round2(max_kg)} kg."
            if not weight_ok
            else f"{total_cartons} cartons, {_round2(total_weight)} kg total."
        ),
        "cartons_total": total_cartons,
        "total_weight_kg": _round2(total_weight),
        "weight_ok": weight_ok,
    }


def calculate_fifo_fefo(payload: dict[str, Any]) -> dict[str, Any]:
    delivery = _parse_date(payload.get("delivery_date"), "Delivery date")
    batches = payload.get("batches") or []
    if not batches:
        raise ValueError("Add at least one batch")
    parsed = []
    for i, b in enumerate(batches):
        row = b if isinstance(b, dict) else {}
        expiry = _parse_date(row.get("expiry_date"), f"Batch {i + 1} expiry")
        shelf = (expiry - delivery).days
        parsed.append({
            "batch_id": str(row.get("batch_id") or f"Batch {i + 1}"),
            "expiry_date": expiry.isoformat(),
            "shelf_life_days": shelf,
        })
    parsed.sort(key=lambda x: x["expiry_date"])
    expired = [b for b in parsed if b["shelf_life_days"] < 0]
    return {
        "summary": (
            f"{len(expired)} batch(es) expire before delivery."
            if expired
            else "Ship in FEFO order: " + " → ".join(b["batch_id"] for b in parsed)
        ),
        "ship_order": parsed,
        "expired_before_delivery": expired,
    }


def calculate_landed_cost(payload: dict[str, Any], fx_rate: float = 1.0) -> dict[str, Any]:
    goods = _positive(payload.get("goods_value"), "Goods value")
    qty = max(1, _int(payload.get("quantity"), 1))
    duty_pct = max(0, _num(payload.get("duty_percent")))
    vat_pct = max(0, _num(payload.get("vat_percent")))
    clearance = max(0, _num(payload.get("clearance_fees")))
    other = max(0, _num(payload.get("other_fees")))
    to_ccy = str(payload.get("to_currency") or "AED").upper()
    cif = goods * fx_rate
    duty = cif * (duty_pct / 100)
    vat = (cif + duty + clearance + other) * (vat_pct / 100)
    landed = cif + duty + vat + clearance + other
    return {
        "summary": f"Landed cost: {to_ccy} {_round2(landed / qty)} per unit.",
        "landed_per_unit": _round2(landed / qty),
        "landed_total": _round2(landed),
        "fx_rate": _round2(fx_rate),
        "disclaimer": "Indicative only — verify with customs.",
    }


def generate_doc_checklist(payload: dict[str, Any]) -> dict[str, Any]:
    tags = {"base"}
    if _bool(payload.get("dangerous_goods")):
        tags.add("dg")
    if _bool(payload.get("temperature_controlled")):
        tags.add("reefer")
    if _bool(payload.get("cross_border")):
        tags.add("cross_border")
    if _bool(payload.get("high_value")):
        tags.add("high_value")
    items = [
        {"document": d["label"], "required": "base" in d["tags"]}
        for d in DOC_LIBRARY
        if any(t in tags for t in d["tags"])
    ]
    return {
        "summary": f"{len(items)} document(s) recommended.",
        "items": items,
        "disclaimer": "Planning checklist only — not legal advice.",
    }


def check_dg_segregation(payload: dict[str, Any]) -> dict[str, Any]:
    a = str(payload.get("class_a") or "").strip()
    b = str(payload.get("class_b") or "").strip()
    if a not in SEGREGATION_MATRIX or b not in SEGREGATION_MATRIX:
        raise ValueError("Select two valid DG classes (1-9)")
    if a == b:
        return {"summary": "Same class — check quantity limits.", "compatible": True, "segregate": False}
    seg = b in SEGREGATION_MATRIX.get(a, []) or a in SEGREGATION_MATRIX.get(b, [])
    return {
        "summary": f"Class {a} and {b} should be segregated." if seg else f"Class {a} and {b} may be compatible.",
        "compatible": not seg,
        "segregate": seg,
        "disclaimer": "Simplified matrix — confirm with SDS and local rules.",
    }


def calculate_trip_cost(payload: dict[str, Any]) -> dict[str, Any]:
    distance = _positive(payload.get("distance_km"), "Distance")
    fuel_per100 = _positive(payload.get("fuel_l_per_100km"), "Fuel consumption")
    fuel_price = _positive(payload.get("fuel_price"), "Fuel price")
    driver = max(0, _num(payload.get("driver_cost")))
    tolls = max(0, _num(payload.get("tolls_fees")))
    weight = max(0, _num(payload.get("weight_kg")))
    litres = (distance / 100) * fuel_per100
    fuel_cost = litres * fuel_price
    total = fuel_cost + driver + tolls
    return {
        "summary": f"Trip cost: {_round2(total)}",
        "fuel_cost": _round2(fuel_cost),
        "total_cost": _round2(total),
        "cost_per_kg": _round2(total / weight) if weight else None,
    }


def calculate_transit_eta(payload: dict[str, Any]) -> dict[str, Any]:
    pickup = _parse_date(payload.get("pickup_date"), "Pickup date")
    transit = max(1, _int(payload.get("transit_days"), 1))
    buffer = max(0, _int(payload.get("buffer_days"), 0))
    skip_we = _bool(payload.get("skip_weekends"))
    target = transit + buffer
    d = pickup
    added = 0
    while added < target:
        d += timedelta(days=1)
        if skip_we and d.weekday() >= 5:
            continue
        added += 1
    return {
        "summary": f"Estimated delivery: {d.isoformat()}",
        "pickup_date": pickup.isoformat(),
        "delivery_date": d.isoformat(),
        "disclaimer": "Planning estimate only.",
    }


def calculate_free_time(payload: dict[str, Any]) -> dict[str, Any]:
    arrival = _parse_date(payload.get("arrival_date"), "Arrival date")
    free_days = max(0, _int(payload.get("free_days"), 0))
    last_free = arrival + timedelta(days=free_days)
    today = date.today()
    remaining = (last_free - today).days
    return {
        "summary": (
            f"Free time expired {abs(remaining)} day(s) ago."
            if remaining < 0
            else f"{remaining} day(s) until last free day."
        ),
        "last_free_day": last_free.isoformat(),
        "days_remaining": remaining,
        "expired": remaining < 0,
        "disclaimer": "Confirm free-time terms on your tariff.",
    }


def calculate_multi_stop(payload: dict[str, Any]) -> dict[str, Any]:
    stops = payload.get("stops") or []
    if not stops:
        raise ValueError("Add at least one stop")
    tw = tv = tp = 0.0
    for s in stops:
        row = s if isinstance(s, dict) else {}
        tw += max(0, _num(row.get("weight_kg")))
        tv += max(0, _num(row.get("volume_cbm")))
        tp += max(0, _int(row.get("pallets")))
    truck = calculate_truck_requirement({
        "transport_region": payload.get("transport_region") or "uae",
        "total_weight_kg": tw,
        "total_volume_cbm": tv,
        "pallet_count": int(tp),
        "safety_margin_pct": _num(payload.get("safety_margin_pct"), 10),
    })
    return {
        "summary": f"{len(stops)} stops — {_round2(tw)} kg, {_round2(tv)} CBM. {truck['summary']}",
        "totals": {"weight_kg": _round2(tw), "volume_cbm": _round2(tv)},
        "truck": truck,
    }