from __future__ import annotations


def calculate_fuel_surcharge(
    baseline_price: float,
    current_price: float,
    *,
    currency: str = "LOCAL",
    unit: str = "per litre",
) -> dict:
    if baseline_price <= 0:
        raise ValueError("Baseline must be greater than zero")
    delta = current_price - baseline_price
    fsc = round((delta / baseline_price) * 100, 2)
    return {
        "summary": f"Apply {fsc}% fuel surcharge.",
        "baseline_price": round(baseline_price, 2),
        "current_price": round(current_price, 2),
        "fsc_percent": fsc,
        "currency": currency,
        "unit": unit,
        "formula": "FSC % = ((current − baseline) ÷ baseline) × 100",
        "disclaimer": "Indicative only — confirm your tariff.",
    }