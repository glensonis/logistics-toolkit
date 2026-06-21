from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PalletSpec:
    name: str
    length_m: float
    width_m: float
    default_height_m: float
    default_weight_kg: float


@dataclass(frozen=True)
class TruckSpec:
    id: str
    name: str
    region: str
    category: str
    payload_kg: float
    volume_cbm: float
    bed_length_m: float
    bed_width_m: float
    bed_height_m: float
    notes: str
    standard_label: str
    dg_classes: frozenset[str] = field(default_factory=frozenset)
    is_dg_vehicle: bool = False


PALLET_TYPES: dict[str, PalletSpec] = {
    "euro": PalletSpec("Euro Pallet", 1.20, 0.80, 1.45, 800),
    "standard": PalletSpec("Standard Pallet (120x100)", 1.20, 1.00, 1.45, 900),
    "us": PalletSpec("US Pallet (48x40)", 1.22, 1.02, 1.45, 900),
    "half": PalletSpec("Half Pallet", 0.80, 0.60, 1.20, 400),
    "custom": PalletSpec("Custom Pallet", 1.20, 1.00, 1.45, 900),
}

DG_CLASSES: dict[str, str] = {
    "1": "Class 1 - Explosives",
    "2": "Class 2 - Gases",
    "3": "Class 3 - Flammable Liquids",
    "4": "Class 4 - Flammable Solids",
    "5": "Class 5 - Oxidizers",
    "6": "Class 6 - Toxic / Infectious",
    "7": "Class 7 - Radioactive",
    "8": "Class 8 - Corrosives",
    "9": "Class 9 - Miscellaneous",
}

PACKING_GROUPS: dict[str, str] = {
    "I": "Packing Group I (high danger)",
    "II": "Packing Group II (medium danger)",
    "III": "Packing Group III (low danger)",
    "NA": "Not applicable",
}

UAE_GENERAL_FLEET: list[TruckSpec] = [
    TruckSpec("uae_pickup_1t", "1 Ton Pickup (UAE)", "uae", "general", 1000, 2.4, 2.0, 1.5, 1.0, "Last-mile and light parcels within emirate limits", "UAE Primary"),
    TruckSpec("uae_lorry_3t", "3 Ton Lorry (UAE)", "uae", "general", 3000, 13, 4.2, 2.0, 1.9, "Urban distribution, FMCG, light pallet moves", "UAE Primary"),
    TruckSpec("uae_truck_7t", "7 Ton Truck (UAE)", "uae", "general", 7500, 32, 6.2, 2.4, 2.4, "Inter-emirate road freight, mixed pallet cargo", "UAE Primary"),
    TruckSpec("uae_truck_10t", "10 Ton Truck (UAE)", "uae", "general", 10000, 38, 7.6, 2.4, 2.5, "Warehouse transfers and medium industrial loads", "UAE Primary"),
    TruckSpec("uae_rigid_20t", "20 Ton Rigid (UAE)", "uae", "general", 20000, 52, 9.2, 2.4, 2.6, "Heavy palletized cargo and project spares", "UAE Primary"),
    TruckSpec("uae_trailer_40ft", "40 ft Trailer (UAE)", "uae", "general", 25000, 65, 12.0, 2.4, 2.6, "FTL moves, port-to-warehouse, containerized style freight", "UAE Primary"),
    TruckSpec("uae_lowbed", "Lowbed / Flatbed (UAE)", "uae", "oversized", 35000, 75, 13.5, 2.5, 3.0, "Oversized machinery and non-enclosed project cargo", "UAE Primary"),
    TruckSpec("uae_reefer_10t", "10 Ton Reefer (UAE)", "uae", "reefer", 9000, 34, 7.2, 2.4, 2.5, "Chilled and frozen cargo under UAE cold-chain practice", "UAE Primary"),
]

GCC_GENERAL_FLEET: list[TruckSpec] = [
    TruckSpec("gcc_pickup_1t", "1 Ton Pickup (GCC)", "gcc", "general", 900, 2.2, 1.9, 1.5, 1.0, "Cross-border light delivery reference standard", "GCC Secondary"),
    TruckSpec("gcc_lorry_3t", "3 Ton Lorry (GCC)", "gcc", "general", 2800, 12, 4.0, 2.0, 1.9, "KSA / Oman / Qatar city leg reference", "GCC Secondary"),
    TruckSpec("gcc_truck_7t", "7 Ton Truck (GCC)", "gcc", "general", 7000, 28, 6.0, 2.4, 2.3, "GCC regional linehaul reference", "GCC Secondary"),
    TruckSpec("gcc_truck_10t", "10 Ton Truck (GCC)", "gcc", "general", 9500, 36, 7.4, 2.4, 2.4, "GCC medium freight reference", "GCC Secondary"),
    TruckSpec("gcc_rigid_20t", "20 Ton Rigid (GCC)", "gcc", "general", 18000, 48, 9.0, 2.4, 2.5, "GCC heavy rigid reference", "GCC Secondary"),
    TruckSpec("gcc_trailer_40ft", "40 ft Trailer (GCC)", "gcc", "general", 23000, 62, 12.0, 2.4, 2.6, "GCC semi-trailer FTL reference", "GCC Secondary"),
    TruckSpec("gcc_lowbed", "Lowbed / Flatbed (GCC)", "gcc", "oversized", 32000, 72, 13.0, 2.5, 2.9, "GCC oversized and project cargo reference", "GCC Secondary"),
    TruckSpec("gcc_reefer_10t", "10 Ton Reefer (GCC)", "gcc", "reefer", 8500, 32, 7.0, 2.4, 2.4, "GCC temperature-controlled reference", "GCC Secondary"),
]

UAE_DG_FLEET: list[TruckSpec] = [
    TruckSpec("uae_dg_van_3t", "DG 3 Ton Van (UAE)", "uae", "dg", 2500, 11, 4.0, 2.0, 1.9, "Limited quantity and small DG consignments", "UAE Primary", frozenset({"2", "3", "4", "5", "6", "8", "9"}), True),
    TruckSpec("uae_dg_7t", "DG 7 Ton Truck (UAE)", "uae", "dg", 6500, 28, 6.0, 2.4, 2.4, "Palletized DG with placarding and segregation", "UAE Primary", frozenset({"2", "3", "4", "5", "6", "8", "9"}), True),
    TruckSpec("uae_dg_10t", "DG 10 Ton Truck (UAE)", "uae", "dg", 9000, 34, 7.4, 2.4, 2.5, "Medium DG freight between approved DG routes", "UAE Primary", frozenset({"2", "3", "4", "5", "6", "8", "9"}), True),
    TruckSpec("uae_dg_trailer", "DG 40 ft Trailer (UAE)", "uae", "dg", 22000, 60, 12.0, 2.4, 2.6, "Bulk DG FTL with UAE DG transport approval", "UAE Primary", frozenset({"2", "3", "4", "5", "6", "8", "9"}), True),
    TruckSpec("uae_dg_tanker", "DG Tanker (UAE)", "uae", "dg_tanker", 18000, 0, 0, 0, 0, "Bulk flammable liquids and corrosives in tanker service", "UAE Primary", frozenset({"3", "8"}), True),
    TruckSpec("uae_dg_reefer", "DG Reefer 10T (UAE)", "uae", "dg_reefer", 8000, 30, 7.0, 2.4, 2.4, "Temperature-controlled DG and pharma chemicals", "UAE Primary", frozenset({"3", "6", "8", "9"}), True),
    TruckSpec("uae_dg_explosives", "DG Explosives Vehicle (UAE)", "uae", "dg_special", 1500, 8, 3.5, 1.9, 1.8, "Class 1 only with special UAE permit and escort", "UAE Primary", frozenset({"1"}), True),
    TruckSpec("uae_dg_radioactive", "DG Radioactive Vehicle (UAE)", "uae", "dg_special", 2000, 10, 4.0, 2.0, 1.9, "Class 7 only with radiation shielding approval", "UAE Primary", frozenset({"7"}), True),
]

GCC_DG_FLEET: list[TruckSpec] = [
    TruckSpec("gcc_dg_van_3t", "DG 3 Ton Van (GCC)", "gcc", "dg", 2300, 10, 3.8, 2.0, 1.8, "GCC LQ DG reference vehicle", "GCC Secondary", frozenset({"2", "3", "4", "5", "6", "8", "9"}), True),
    TruckSpec("gcc_dg_7t", "DG 7 Ton Truck (GCC)", "gcc", "dg", 6000, 26, 5.8, 2.4, 2.3, "GCC palletized DG reference", "GCC Secondary", frozenset({"2", "3", "4", "5", "6", "8", "9"}), True),
    TruckSpec("gcc_dg_10t", "DG 10 Ton Truck (GCC)", "gcc", "dg", 8500, 32, 7.2, 2.4, 2.4, "GCC medium DG reference", "GCC Secondary", frozenset({"2", "3", "4", "5", "6", "8", "9"}), True),
    TruckSpec("gcc_dg_trailer", "DG 40 ft Trailer (GCC)", "gcc", "dg", 20000, 58, 12.0, 2.4, 2.6, "GCC DG FTL reference", "GCC Secondary", frozenset({"2", "3", "4", "5", "6", "8", "9"}), True),
    TruckSpec("gcc_dg_tanker", "DG Tanker (GCC)", "gcc", "dg_tanker", 16000, 0, 0, 0, 0, "GCC bulk liquid DG reference", "GCC Secondary", frozenset({"3", "8"}), True),
    TruckSpec("gcc_dg_reefer", "DG Reefer 10T (GCC)", "gcc", "dg_reefer", 7500, 28, 6.8, 2.4, 2.4, "GCC cold-chain DG reference", "GCC Secondary", frozenset({"3", "6", "8", "9"}), True),
    TruckSpec("gcc_dg_explosives", "DG Explosives Vehicle (GCC)", "gcc", "dg_special", 1300, 7, 3.2, 1.8, 1.7, "GCC Class 1 special permit reference", "GCC Secondary", frozenset({"1"}), True),
    TruckSpec("gcc_dg_radioactive", "DG Radioactive Vehicle (GCC)", "gcc", "dg_special", 1800, 9, 3.8, 2.0, 1.8, "GCC Class 7 special permit reference", "GCC Secondary", frozenset({"7"}), True),
]


def _positive(value: float, field: str) -> float:
    if value <= 0:
        raise ValueError(f"{field} must be greater than zero")
    return value


def _pallet_spec(pallet_type: str, custom_length_m: float, custom_width_m: float) -> PalletSpec:
    spec = PALLET_TYPES.get(pallet_type, PALLET_TYPES["standard"])
    if pallet_type == "custom":
        return PalletSpec(
            "Custom Pallet",
            _positive(custom_length_m, "Custom pallet length"),
            _positive(custom_width_m, "Custom pallet width"),
            spec.default_height_m,
            spec.default_weight_kg,
        )
    return spec


def _fleet_for_region(region: str, dangerous_goods: bool) -> tuple[list[TruckSpec], list[TruckSpec]]:
    region = (region or "uae").lower()
    if dangerous_goods:
        primary = UAE_DG_FLEET if region == "uae" else GCC_DG_FLEET
        secondary = GCC_DG_FLEET if region == "uae" else UAE_DG_FLEET
    else:
        primary = UAE_GENERAL_FLEET if region == "uae" else GCC_GENERAL_FLEET
        secondary = GCC_GENERAL_FLEET if region == "uae" else UAE_GENERAL_FLEET
    return primary, secondary


def _truck_matches_cargo(
    truck: TruckSpec,
    *,
    temperature_controlled: bool,
    oversized: bool,
    dangerous_goods: bool,
    dg_class: str,
    bulk_liquid: bool,
) -> bool:
    if dangerous_goods and not truck.is_dg_vehicle:
        return False
    if not dangerous_goods and truck.is_dg_vehicle:
        return False
    if dangerous_goods and dg_class and dg_class not in truck.dg_classes:
        return False

    if bulk_liquid:
        return truck.category == "dg_tanker"
    if truck.category == "dg_tanker":
        return False

    if oversized:
        return truck.category == "oversized" or "trailer" in truck.id

    if temperature_controlled:
        return truck.category in {"reefer", "dg_reefer"}

    if dangerous_goods:
        return truck.category in {"dg", "dg_special", "dg_reefer"}

    return truck.category == "general"


def _score_truck(truck: TruckSpec, trucks_needed: int) -> tuple:
    return (trucks_needed, truck.payload_kg, truck.volume_cbm if truck.volume_cbm else 999)


def _build_recommendation(truck: TruckSpec, total_weight_kg: float, total_volume_cbm: float, required_weight: float, required_volume: float) -> dict[str, Any]:
    if truck.category == "dg_tanker":
        trucks_needed = max(1, math.ceil(required_weight / truck.payload_kg))
        weight_util = min(100.0, (total_weight_kg / (truck.payload_kg * trucks_needed)) * 100)
        volume_util = 0.0
        binding = "weight"
    else:
        trucks_by_weight = math.ceil(required_weight / truck.payload_kg)
        trucks_by_volume = math.ceil(required_volume / max(truck.volume_cbm, 0.01))
        trucks_needed = max(trucks_by_weight, trucks_by_volume, 1)
        weight_util = min(100.0, (total_weight_kg / (truck.payload_kg * trucks_needed)) * 100)
        volume_util = min(100.0, (total_volume_cbm / (truck.volume_cbm * trucks_needed)) * 100)
        binding = "weight" if trucks_by_weight >= trucks_by_volume else "volume"

    return {
        "id": truck.id,
        "name": truck.name,
        "region": truck.region,
        "standard_label": truck.standard_label,
        "category": truck.category,
        "trucks_needed": trucks_needed,
        "payload_kg": truck.payload_kg,
        "volume_cbm": truck.volume_cbm,
        "weight_utilization_pct": round(weight_util, 1),
        "volume_utilization_pct": round(volume_util, 1),
        "binding_constraint": binding,
        "notes": truck.notes,
        "fits_single_truck": trucks_needed == 1,
        "is_dg_vehicle": truck.is_dg_vehicle,
    }


def _validate_dg_payload(payload: dict[str, Any]) -> dict[str, Any]:
    dg_class = str(payload.get("dg_class") or "").strip()
    un_number = str(payload.get("un_number") or "").strip().upper()
    packing_group = str(payload.get("packing_group") or "NA").strip().upper()
    proper_name = str(payload.get("proper_shipping_name") or "").strip()
    technical_name = str(payload.get("technical_name") or "").strip()
    limited_quantity = bool(payload.get("limited_quantity"))
    marine_pollutant = bool(payload.get("marine_pollutant"))
    flash_point_c = payload.get("flash_point_c")
    dg_quantity = float(payload.get("dg_quantity") or 0)
    dg_quantity_unit = str(payload.get("dg_quantity_unit") or "kg").lower()

    if not dg_class:
        raise ValueError("Select a DG class for dangerous goods shipments")
    if dg_class not in DG_CLASSES:
        raise ValueError("Invalid DG class")
    if un_number and not re.fullmatch(r"UN\d{4}", un_number):
        raise ValueError("UN number must look like UN1203")
    if packing_group not in PACKING_GROUPS:
        raise ValueError("Invalid packing group")
    if not proper_name:
        raise ValueError("Enter the proper shipping name for DG cargo")
    if dg_quantity <= 0:
        raise ValueError("Enter the net DG quantity")

    return {
        "dg_class": dg_class,
        "dg_class_label": DG_CLASSES[dg_class],
        "un_number": un_number or "Not provided",
        "proper_shipping_name": proper_name,
        "technical_name": technical_name or "Not provided",
        "packing_group": packing_group,
        "packing_group_label": PACKING_GROUPS[packing_group],
        "limited_quantity": limited_quantity,
        "marine_pollutant": marine_pollutant,
        "flash_point_c": flash_point_c,
        "dg_quantity": dg_quantity,
        "dg_quantity_unit": dg_quantity_unit,
    }


def _dg_compliance_notes(dg_info: dict[str, Any], primary: dict[str, Any]) -> list[str]:
    notes = [
        "UAE DG road transport requires approved vehicle, DG-trained driver, placards, MSDS/SDS, and emergency response plan.",
        f"Shipment: {dg_info['proper_shipping_name']} ({dg_info['dg_class_label']}, {dg_info['un_number']}).",
    ]
    if dg_info["limited_quantity"]:
        notes.append("Marked as Limited Quantity (LQ). Confirm LQ thresholds for the selected route and class.")
    if dg_info["marine_pollutant"]:
        notes.append("Marine pollutant flagged. Use leak-proof loading and segregate from foodstuffs.")
    if dg_info["dg_class"] == "3" and dg_info.get("flash_point_c") not in (None, ""):
        notes.append(f"Class 3 flash point noted at {dg_info['flash_point_c']} °C. Verify reefer or tanker requirement.")
    if dg_info["dg_class"] in {"1", "7"}:
        notes.append("Class 1 / Class 7 requires special UAE permit, escort, and authority approval before dispatch.")
    if primary["category"] == "dg_tanker":
        notes.append("Bulk liquid DG selected. Tanker vehicle, compatibility chart, and loading checklist are mandatory.")
    notes.append("GCC secondary standards are reference values for cross-border legs; confirm local authority rules in each country.")
    return notes


def calculate_truck_requirement(payload: dict[str, Any]) -> dict[str, Any]:
    total_weight_kg = float(payload.get("total_weight_kg") or 0)
    total_volume_cbm = float(payload.get("total_volume_cbm") or 0)
    pallet_count = int(payload.get("pallet_count") or 0)
    pallet_type = str(payload.get("pallet_type") or "standard").lower()
    stack_levels = max(1, int(payload.get("stack_levels") or 1))
    pallet_weight_kg = float(payload.get("pallet_weight_kg") or 0)
    pallet_height_m = float(payload.get("pallet_height_m") or 0)
    custom_length_m = float(payload.get("custom_length_m") or 1.2)
    custom_width_m = float(payload.get("custom_width_m") or 1.0)
    safety_margin_pct = max(0.0, float(payload.get("safety_margin_pct") or 10))
    temperature_controlled = bool(payload.get("temperature_controlled"))
    oversized = bool(payload.get("oversized"))
    dangerous_goods = bool(payload.get("dangerous_goods"))
    transport_region = str(payload.get("transport_region") or "uae").lower()
    bulk_liquid = bool(payload.get("bulk_liquid"))

    if total_weight_kg <= 0 and pallet_count <= 0:
        raise ValueError("Enter total weight or pallet count")

    dg_info = None
    if dangerous_goods:
        dg_info = _validate_dg_payload(payload)
        if dg_info["dg_class"] == "3" and bulk_liquid:
            total_volume_cbm = max(total_volume_cbm, dg_info["dg_quantity"] if dg_info["dg_quantity_unit"] == "l" else dg_info["dg_quantity"] / 1000)

    pallet = _pallet_spec(pallet_type, custom_length_m, custom_width_m)
    per_pallet_weight = pallet_weight_kg or pallet.default_weight_kg
    per_pallet_height = pallet_height_m or pallet.default_height_m
    per_pallet_volume = pallet.length_m * pallet.width_m * per_pallet_height

    if pallet_count > 0:
        derived_weight = pallet_count * per_pallet_weight
        derived_volume = pallet_count * per_pallet_volume
        if total_weight_kg <= 0:
            total_weight_kg = derived_weight
        if total_volume_cbm <= 0:
            total_volume_cbm = derived_volume

    total_weight_kg = _positive(total_weight_kg, "Total weight")
    if bulk_liquid and dangerous_goods:
        total_volume_cbm = max(total_volume_cbm, 0.01)
    else:
        total_volume_cbm = _positive(total_volume_cbm, "Total volume")

    margin = 1 + (safety_margin_pct / 100)
    required_weight = total_weight_kg * margin
    required_volume = total_volume_cbm * margin

    primary_fleet, secondary_fleet = _fleet_for_region(transport_region, dangerous_goods)
    dg_class = dg_info["dg_class"] if dg_info else ""

    def recommend_from(fleet: list[TruckSpec]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for truck in fleet:
            if not _truck_matches_cargo(
                truck,
                temperature_controlled=temperature_controlled,
                oversized=oversized,
                dangerous_goods=dangerous_goods,
                dg_class=dg_class,
                bulk_liquid=bulk_liquid,
            ):
                continue
            rec = _build_recommendation(truck, total_weight_kg, total_volume_cbm, required_weight, required_volume)
            items.append(rec)
        items.sort(key=lambda item: _score_truck(next(t for t in fleet if t.id == item["id"]), item["trucks_needed"]))
        return items

    primary_recs = recommend_from(primary_fleet)
    if not primary_recs:
        raise ValueError("No suitable truck found for the selected cargo, DG class, and transport standard")

    secondary_recs = recommend_from(secondary_fleet)

    primary = primary_recs[0]
    alternatives = primary_recs[1:4]
    regional_reference = secondary_recs[:3]

    region_label = "UAE Primary" if transport_region == "uae" else "GCC Secondary"
    if primary["trucks_needed"] > 1:
        summary = (
            f"{region_label}: use {primary['trucks_needed']} x {primary['name']} "
            f"({primary['binding_constraint']} limited)."
        )
    else:
        summary = f"{region_label}: recommend {primary['name']}."

    if dangerous_goods and dg_info:
        summary += f" DG {dg_info['dg_class_label']} / {dg_info['un_number']}."
    if temperature_controlled:
        summary += " Temperature-controlled vehicle required."
    if bulk_liquid:
        summary += " Bulk liquid DG requires tanker service."

    compliance_notes = _dg_compliance_notes(dg_info, primary) if dg_info else [
        "UAE standards are applied as the primary sizing basis.",
        "GCC secondary values are shown for Oman, KSA, Qatar, Bahrain, and Kuwait cross-border reference.",
    ]

    return {
        "summary": summary,
        "primary": primary,
        "alternatives": alternatives,
        "regional_reference": regional_reference,
        "compliance_notes": compliance_notes,
        "transport_region": transport_region,
        "transport_region_label": region_label,
        "dangerous_goods": dangerous_goods,
        "dg_info": dg_info,
        "inputs": {
            "total_weight_kg": round(total_weight_kg, 2),
            "total_volume_cbm": round(total_volume_cbm, 2),
            "required_weight_kg": round(required_weight, 2),
            "required_volume_cbm": round(required_volume, 2),
            "pallet_count": pallet_count,
            "pallet_type": pallet.name,
            "stack_levels": stack_levels,
            "safety_margin_pct": safety_margin_pct,
            "bulk_liquid": bulk_liquid,
        },
        "dg_classes": DG_CLASSES,
        "packing_groups": PACKING_GROUPS,
        "pallet_types": {key: spec.name for key, spec in PALLET_TYPES.items()},
    }


def calculate_warehouse_space(payload: dict[str, Any]) -> dict[str, Any]:
    length_m = _positive(float(payload.get("length_m") or 0), "Warehouse length")
    width_m = _positive(float(payload.get("width_m") or 0), "Warehouse width")
    height_m = _positive(float(payload.get("height_m") or 0), "Warehouse height")
    aisle_width_m = _positive(float(payload.get("aisle_width_m") or 3.0), "Aisle width")
    staging_pct = min(50.0, max(0.0, float(payload.get("staging_pct") or 15)))
    clearance_pct = min(30.0, max(0.0, float(payload.get("clearance_pct") or 10)))

    pallet_type = str(payload.get("pallet_type") or "standard").lower()
    custom_length_m = float(payload.get("custom_length_m") or 1.2)
    custom_width_m = float(payload.get("custom_width_m") or 1.0)
    pallet_height_m = float(payload.get("pallet_height_m") or 0)
    stack_levels = max(1, int(payload.get("stack_levels") or 3))
    inventory_pallets = max(0, int(payload.get("inventory_pallets") or 0))
    inventory_weight_kg = max(0.0, float(payload.get("inventory_weight_kg") or 0))

    pallet = _pallet_spec(pallet_type, custom_length_m, custom_width_m)
    per_pallet_height = pallet_height_m or pallet.default_height_m

    gross_floor_area = length_m * width_m
    gross_volume = gross_floor_area * height_m
    staging_area = gross_floor_area * (staging_pct / 100)
    net_floor_area = gross_floor_area - staging_area

    usable_height = height_m * (1 - (clearance_pct / 100))
    max_stack_by_height = max(1, int(usable_height // per_pallet_height))
    effective_stack = min(stack_levels, max_stack_by_height)

    pallet_footprint = pallet.length_m * pallet.width_m
    pallet_storage_volume = pallet_footprint * per_pallet_height * effective_stack

    pallets_along_length = max(0, int((length_m - aisle_width_m) // pallet.length_m))
    pallets_along_width = max(0, int(width_m // pallet.width_m))
    if pallets_along_length <= 0 or pallets_along_width <= 0:
        raise ValueError("Warehouse dimensions are too small for the selected pallet size")

    rows = pallets_along_width
    cols = pallets_along_length
    aisle_blocks = max(1, int(math.ceil(rows / 2)))
    gross_pallet_slots = rows * cols
    max_pallets = max(0, gross_pallet_slots - aisle_blocks)
    max_storage_cbm = max_pallets * pallet_storage_volume
    max_weight_capacity_kg = max_pallets * pallet.default_weight_kg * effective_stack

    occupied_pallets = inventory_pallets or max_pallets
    if inventory_pallets <= 0 and inventory_weight_kg > 0:
        occupied_pallets = min(
            max_pallets,
            max(1, math.ceil(inventory_weight_kg / (pallet.default_weight_kg * effective_stack))),
        )

    occupied_cbm = min(max_storage_cbm, occupied_pallets * pallet_storage_volume)
    floor_utilization = min(100.0, (occupied_pallets / max_pallets) * 100) if max_pallets else 0
    volume_utilization = min(100.0, (occupied_cbm / max_storage_cbm) * 100) if max_storage_cbm else 0

    if inventory_pallets > max_pallets:
        suggestion = (
            f"Need {inventory_pallets} pallets but only {max_pallets} fit. "
            f"Consider {math.ceil(inventory_pallets / max_pallets)} warehouse zones or expansion."
        )
    elif floor_utilization >= 85:
        suggestion = "Warehouse is near capacity. Plan overflow or additional storage."
    elif floor_utilization >= 60:
        suggestion = "Moderate utilization. Monitor fast-moving SKUs and aisle access."
    else:
        suggestion = f"Good available space. Up to {max_pallets - occupied_pallets} more pallet positions free."

    return {
        "summary": suggestion,
        "warehouse": {
            "gross_floor_area_sqm": round(gross_floor_area, 2),
            "net_floor_area_sqm": round(net_floor_area, 2),
            "gross_volume_cbm": round(gross_volume, 2),
            "usable_height_m": round(usable_height, 2),
            "staging_area_sqm": round(staging_area, 2),
        },
        "pallet": {
            "type": pallet.name,
            "footprint_sqm": round(pallet_footprint, 2),
            "height_m": round(per_pallet_height, 2),
            "effective_stack_levels": effective_stack,
            "storage_cbm_per_position": round(pallet_storage_volume, 2),
        },
        "capacity": {
            "max_pallet_positions": max_pallets,
            "max_storage_cbm": round(max_storage_cbm, 2),
            "max_weight_capacity_kg": round(max_weight_capacity_kg, 2),
            "occupied_pallets": occupied_pallets,
            "occupied_storage_cbm": round(occupied_cbm, 2),
            "floor_utilization_pct": round(floor_utilization, 1),
            "volume_utilization_pct": round(volume_utilization, 1),
        },
        "layout": {
            "pallets_along_length": pallets_along_length,
            "pallets_along_width": pallets_along_width,
            "aisle_width_m": aisle_width_m,
        },
        "pallet_types": {key: spec.name for key, spec in PALLET_TYPES.items()},
    }