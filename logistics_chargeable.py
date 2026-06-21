from __future__ import annotations

from typing import Any

PRESETS = {"road_167": 167, "road_333": 333, "air_167": 167}


def calculate_chargeable_weight(payload: dict[str, Any]) -> dict[str, Any]:
    actual = max(0.0, float(payload.get("actual_weight_kg") or 0))
    volume = max(0.0, float(payload.get("volume_cbm") or 0))
    preset = str(payload.get("volumetric_preset") or "road_167")
    if preset == "custom":
        factor = float(payload.get("volumetric_factor") or 0)
        if factor <= 0:
            raise ValueError("Enter a valid custom volumetric factor")
    else:
        factor = PRESETS.get(preset, 167)
    if actual <= 0 and volume <= 0:
        raise ValueError("Enter actual weight or volume")
    vol_weight = volume * factor
    chargeable = max(actual, vol_weight)
    binding = "weight" if actual >= vol_weight else "volume"
    return {
        "summary": f"Chargeable weight is {chargeable:.2f} kg ({binding} binding).",
        "chargeable_weight_kg": round(chargeable, 2),
        "volumetric_weight_kg": round(vol_weight, 2),
        "binding_constraint": binding,
        "volumetric_factor": factor,
    }