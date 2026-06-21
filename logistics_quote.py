from __future__ import annotations

from typing import Any

from logistics_chargeable import calculate_chargeable_weight


def calculate_freight_quote(payload: dict[str, Any]) -> dict[str, Any]:
    basis = str(payload.get("rate_basis") or "per_kg")
    base_rate = float(payload.get("base_rate") or 0)
    weight = max(0.0, float(payload.get("weight_kg") or 0))
    volume = max(0.0, float(payload.get("volume_cbm") or 0))
    distance = max(0.0, float(payload.get("distance_km") or 0))
    fsc_pct = max(0.0, float(payload.get("fsc_percent") or 0))
    margin_pct = max(0.0, float(payload.get("margin_percent") or 0))
    tolls = max(0.0, float(payload.get("tolls_fees") or 0))
    currency = str(payload.get("currency") or "AED").upper()[:6]

    if basis == "per_kg":
        ch = calculate_chargeable_weight({
            "actual_weight_kg": weight,
            "volume_cbm": volume,
            "volumetric_preset": "custom",
            "volumetric_factor": float(payload.get("volumetric_factor") or 167),
        })
        chargeable = ch["chargeable_weight_kg"]
        if chargeable <= 0:
            raise ValueError("Enter weight or volume")
        base_freight = chargeable * base_rate
    elif basis == "per_cbm":
        if volume <= 0:
            raise ValueError("Enter volume")
        base_freight = volume * base_rate
    elif basis == "per_km":
        if distance <= 0:
            raise ValueError("Enter distance")
        base_freight = distance * base_rate
    else:
        base_freight = base_rate

    fsc_amt = round(base_freight * (fsc_pct / 100), 2)
    acc = sum(max(0, float(a.get("amount") or 0)) for a in (payload.get("accessorials") or []) if isinstance(a, dict))
    subtotal = round(base_freight + fsc_amt + acc + tolls, 2)
    margin_amt = round(subtotal * (margin_pct / 100), 2)
    sell = round(subtotal + margin_amt, 2)
    return {
        "summary": f"Quote: {currency} {sell}",
        "currency": currency,
        "subtotal": subtotal,
        "sell_total": sell,
        "margin_amount": margin_amt,
        "line_items": [
            {"label": "Base freight", "amount": round(base_freight, 2)},
            {"label": "Sell total", "amount": sell},
        ],
        "copy_text": f"Base freight: {currency} {round(base_freight, 2)}\nTOTAL: {currency} {sell}",
        "disclaimer": "Indicative quote — confirm tariff before invoicing.",
    }