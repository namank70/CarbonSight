# backend/main.py

import os
import json
import math
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# -----------------------------
# App
# -----------------------------
app = FastAPI(title="ClimateChain API", version="2.0.0")

# -----------------------------
# CORS
# -----------------------------
origins_env = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
ALLOW_ORIGINS = [o.strip() for o in origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Model + data
# -----------------------------
rf = joblib.load("rf_model.pkl")
with open("rf_feature_columns.json", "r") as f:
    FEATURE_COLUMNS = json.load(f)

factors = pd.read_csv("Dataset/emission_factors.csv")
energy = pd.read_csv("Dataset/energy_grid_intensity.csv")
PRODUCTS_PATH = "Dataset/products_option1.csv" if os.path.exists("Dataset/products_option1.csv") else "Dataset/products.csv"
products = pd.read_csv(PRODUCTS_PATH)
ROUTES_PATH = "Dataset/routes_option1.csv" if os.path.exists("Dataset/routes_option1.csv") else "Dataset/routes.csv"
routes = pd.read_csv(ROUTES_PATH)

factor_map = factors.set_index(["stage", "type"])["factor"].to_dict()
grid_map = energy.set_index(["metric", "region"])["value"].to_dict()

CATEGORY_ALIASES = {
    "bottle": "water_bottle",
    "bag": "jeans",
}

# Score grading quality drops when a category has too few rows.
# Use proxy categories that have richer historical distributions.
SCORING_PROXY_CATEGORY = {
    "ai_gpu_chip": "smartphone",
    "gpu_server": "laptop",
    "data_center_cooling": "laptop",
    "fiber_optic_roll": "laptop",
    "grid_battery_container": "laptop",
    "hydrogen_electrolyzer": "laptop",
    "lithium_battery_pack": "laptop",
    "solar_panel": "laptop",
}
MIN_SAMPLES_FOR_CATEGORY_SCORING = 20

ALL_CATEGORIES = [
    "t_shirt",
    "bottle",
    "laptop",
    "bag",
    "ai_gpu_chip",
    "gpu_server",
    "data_center_cooling",
    "fiber_optic_roll",
    "grid_battery_container",
    "hydrogen_electrolyzer",
    "lithium_battery_pack",
    "solar_panel",
]

COUNTRY_COORDS = {
    "usa": (38.0, -97.0),
    "mexico": (23.6, -102.5),
    "germany": (51.2, 10.4),
    "turkey": (39.0, 35.0),
    "china": (35.8, 104.1),
    "india": (22.7, 79.0),
    "bangladesh": (23.7, 90.4),
    "vietnam": (14.1, 108.3),
    "taiwan": (23.7, 121.0),
    "south_korea": (36.4, 127.8),
}

COUNTRY_CONTINENT = {
    "usa": "north_america",
    "mexico": "north_america",
    "germany": "europe",
    "turkey": "europe",
    "china": "asia",
    "india": "asia",
    "bangladesh": "asia",
    "vietnam": "asia",
    "taiwan": "asia",
    "south_korea": "asia",
}

LAND_CONNECTED_PAIRS = {
    ("usa", "mexico"),
    ("germany", "turkey"),
    ("india", "bangladesh"),
    ("india", "china"),
    ("india", "vietnam"),
    ("china", "vietnam"),
    ("china", "south_korea"),
}

SHIPPING_PRIORITIES = ["greenest", "fastest"]

MATERIAL_OPTIONS = sorted(factors.loc[factors["stage"] == "material", "type"].unique().tolist())
PACKAGING_OPTIONS = sorted(factors.loc[factors["stage"] == "packaging", "type"].unique().tolist())
NONZERO_PACKAGING_OPTIONS = sorted(
    [p for p in PACKAGING_OPTIONS if factor_map.get(("packaging", p), 0.0) > 0]
)
COUNTRY_OPTIONS = sorted(energy.loc[energy["metric"] == "grid_intensity", "region"].unique().tolist())

CATEGORY_CO2_DISTRIBUTIONS = {
    category: np.sort(group["co2e_total_kg"].dropna().to_numpy(dtype=float))
    for category, group in products.groupby("category")
}
GLOBAL_CO2_DISTRIBUTION = np.sort(products["co2e_total_kg"].dropna().to_numpy(dtype=float))

CATEGORY_BOUNDS = {}
for category, group in products.groupby("category"):
    CATEGORY_BOUNDS[category] = {
        "unit_weight_kg": (
            float(group["unit_weight_kg"].quantile(0.01)),
            float(group["unit_weight_kg"].quantile(0.99)),
        ),
        "distance_km": (
            float(group["distance_km"].quantile(0.01)),
            float(group["distance_km"].quantile(0.99)),
        ),
        "manufacturing_energy_kwh": (
            float(group["manufacturing_energy_kwh"].quantile(0.01)),
            float(group["manufacturing_energy_kwh"].quantile(0.99)),
        ),
        "recycled_content_pct": (
            float(group["recycled_content_pct"].quantile(0.01)),
            float(group["recycled_content_pct"].quantile(0.99)),
        ),
    }

DEFAULT_DISTANCE_KM = float(products["distance_km"].median())
LOWEST_IMPACT_PACKAGING = min(PACKAGING_OPTIONS, key=lambda p: factor_map.get(("packaging", p), 999.0))
LOWEST_IMPACT_NONZERO_PACKAGING = min(NONZERO_PACKAGING_OPTIONS, key=lambda p: factor_map.get(("packaging", p), 999.0))
DEFAULT_MATERIAL_FACTOR = 2.5

CATEGORY_ALLOWED_MATERIALS = {
    "ai_gpu_chip": ["electronics_mix", "silicon_mix", "copper"],
    "gpu_server": ["electronics_mix", "aluminum_structural", "copper"],
    "data_center_cooling": ["industrial_steel", "copper", "aluminum_structural"],
    "fiber_optic_roll": ["glass", "plastic_pet", "copper"],
    "grid_battery_container": ["lithium_mix", "industrial_steel", "aluminum_structural", "nickel", "cobalt"],
    "hydrogen_electrolyzer": ["industrial_steel", "nickel", "electronics_mix"],
    "lithium_battery_pack": ["lithium_mix", "nickel", "cobalt", "aluminum_structural", "industrial_steel"],
    "solar_panel": ["glass", "silicon_mix", "aluminum_structural", "copper"],
}

CATEGORY_ALLOWED_PACKAGING = {
    "t_shirt": ["recycled_cardboard_box", "cardboard_box", "plastic_wrap"],
    "bottle": ["aluminum_can", "glass_bottle", "recycled_cardboard_box", "cardboard_box", "plastic_wrap"],
    "laptop": ["recycled_cardboard_box", "cardboard_box", "plastic_wrap"],
    "bag": ["recycled_cardboard_box", "cardboard_box", "plastic_wrap"],
    "ai_gpu_chip": ["recycled_cardboard_box", "cardboard_box", "reusable_pack", "plastic_wrap"],
    "gpu_server": ["recycled_cardboard_box", "cardboard_box", "reusable_pack", "plastic_wrap"],
    "data_center_cooling": ["reusable_pack", "recycled_cardboard_box", "cardboard_box"],
    "fiber_optic_roll": ["reusable_pack", "recycled_cardboard_box", "cardboard_box"],
    "grid_battery_container": ["reusable_pack", "recycled_cardboard_box", "cardboard_box", "plastic_wrap"],
    "hydrogen_electrolyzer": ["reusable_pack", "recycled_cardboard_box", "cardboard_box", "plastic_wrap"],
    "lithium_battery_pack": ["reusable_pack", "recycled_cardboard_box", "cardboard_box", "plastic_wrap"],
    "solar_panel": ["cardboard_box", "recycled_cardboard_box", "reusable_pack", "plastic_wrap"],
}

# Physical anchor materials that should remain present in each category.
# Rule semantics: at least one of these materials must be present in
# material_1 or material_2 for the category.
REQUIRED_ANCHOR_MATERIALS = {
    "ai_gpu_chip": ["silicon_mix", "electronics_mix"],
    "gpu_server": ["electronics_mix"],
    "data_center_cooling": ["industrial_steel"],
    "fiber_optic_roll": ["glass"],
    "grid_battery_container": ["lithium_mix"],
    "hydrogen_electrolyzer": ["nickel", "industrial_steel"],
    "lithium_battery_pack": ["lithium_mix"],
    "solar_panel": ["silicon_mix", "glass"],
}

CATEGORY_PRESETS = {
    "t_shirt": {
        "unit_weight_kg": 0.22,
        "manufacturing_energy_kwh": 0.8,
        "recycled_content_pct": 45,
        "material_1": "organic_cotton",
        "material_share_1": 0.8,
        "material_2": "recycled_polyester",
        "material_share_2": 0.2,
        "transport_mode": "auto",
        "packaging_type": "recycled_cardboard_box",
        "certification": "gots",
    },
    "bottle": {
        "unit_weight_kg": 0.05,
        "manufacturing_energy_kwh": 0.35,
        "recycled_content_pct": 35,
        "material_1": "recycled_plastic_pet",
        "material_share_1": 1.0,
        "material_2": "",
        "material_share_2": 0.0,
        "transport_mode": "auto",
        "packaging_type": "aluminum_can",
        "certification": "none",
    },
    "laptop": {
        "unit_weight_kg": 1.7,
        "manufacturing_energy_kwh": 10.5,
        "recycled_content_pct": 25,
        "material_1": "aluminum_structural",
        "material_share_1": 0.65,
        "material_2": "electronics_mix",
        "material_share_2": 0.35,
        "transport_mode": "auto",
        "packaging_type": "recycled_cardboard_box",
        "certification": "energy_star",
    },
    "bag": {
        "unit_weight_kg": 0.8,
        "manufacturing_energy_kwh": 2.2,
        "recycled_content_pct": 30,
        "material_1": "industrial_steel",
        "material_share_1": 0.7,
        "material_2": "recycled_polyester",
        "material_share_2": 0.3,
        "transport_mode": "auto",
        "packaging_type": "recycled_cardboard_box",
        "certification": "none",
    },
    "ai_gpu_chip": {
        "unit_weight_kg": 0.08,
        "manufacturing_energy_kwh": 220.0,
        "recycled_content_pct": 12,
        "material_1": "silicon_mix",
        "material_share_1": 0.7,
        "material_2": "electronics_mix",
        "material_share_2": 0.3,
        "transport_mode": "auto",
        "packaging_type": "recycled_cardboard_box",
        "certification": "energy_star",
    },
    "gpu_server": {
        "unit_weight_kg": 55.0,
        "manufacturing_energy_kwh": 1400.0,
        "recycled_content_pct": 20,
        "material_1": "electronics_mix",
        "material_share_1": 0.7,
        "material_2": "aluminum_structural",
        "material_share_2": 0.3,
        "transport_mode": "auto",
        "packaging_type": "recycled_cardboard_box",
        "certification": "energy_star",
    },
    "data_center_cooling": {
        "unit_weight_kg": 1800.0,
        "manufacturing_energy_kwh": 900.0,
        "recycled_content_pct": 30,
        "material_1": "industrial_steel",
        "material_share_1": 0.7,
        "material_2": "copper",
        "material_share_2": 0.3,
        "transport_mode": "auto",
        "packaging_type": "reusable_pack",
        "certification": "none",
    },
    "fiber_optic_roll": {
        "unit_weight_kg": 220.0,
        "manufacturing_energy_kwh": 220.0,
        "recycled_content_pct": 15,
        "material_1": "glass",
        "material_share_1": 0.6,
        "material_2": "plastic_pet",
        "material_share_2": 0.4,
        "transport_mode": "auto",
        "packaging_type": "reusable_pack",
        "certification": "none",
    },
    "grid_battery_container": {
        "unit_weight_kg": 20000.0,
        "manufacturing_energy_kwh": 32000.0,
        "recycled_content_pct": 25,
        "material_1": "lithium_mix",
        "material_share_1": 0.7,
        "material_2": "industrial_steel",
        "material_share_2": 0.3,
        "transport_mode": "auto",
        "packaging_type": "reusable_pack",
        "certification": "none",
    },
    "hydrogen_electrolyzer": {
        "unit_weight_kg": 4200.0,
        "manufacturing_energy_kwh": 6200.0,
        "recycled_content_pct": 20,
        "material_1": "industrial_steel",
        "material_share_1": 0.65,
        "material_2": "nickel",
        "material_share_2": 0.35,
        "transport_mode": "auto",
        "packaging_type": "reusable_pack",
        "certification": "none",
    },
    "lithium_battery_pack": {
        "unit_weight_kg": 480.0,
        "manufacturing_energy_kwh": 9500.0,
        "recycled_content_pct": 20,
        "material_1": "lithium_mix",
        "material_share_1": 0.75,
        "material_2": "aluminum_structural",
        "material_share_2": 0.25,
        "transport_mode": "auto",
        "packaging_type": "reusable_pack",
        "certification": "none",
    },
    "solar_panel": {
        "unit_weight_kg": 21.0,
        "manufacturing_energy_kwh": 550.0,
        "recycled_content_pct": 18,
        "material_1": "glass",
        "material_share_1": 0.6,
        "material_2": "silicon_mix",
        "material_share_2": 0.4,
        "transport_mode": "auto",
        "packaging_type": "cardboard_box",
        "certification": "none",
    },
}

if {"manufacturing_country", "destination_country", "distance_km"}.issubset(routes.columns):
    ROUTE_PAIR_DISTANCE = (
        routes.dropna(subset=["manufacturing_country", "destination_country", "distance_km"])
        .groupby(["manufacturing_country", "destination_country"])["distance_km"]
        .median()
        .to_dict()
    )
else:
    ROUTE_PAIR_DISTANCE = {}

if {"manufacturing_country", "destination_country", "distance_km_raw"}.issubset(routes.columns):
    ROUTE_PAIR_RAW_DISTANCE = (
        routes.dropna(subset=["manufacturing_country", "destination_country", "distance_km_raw"])
        .groupby(["manufacturing_country", "destination_country"])["distance_km_raw"]
        .median()
        .to_dict()
    )
else:
    ROUTE_PAIR_RAW_DISTANCE = {}


def normalize_category(category: str) -> str:
    return CATEGORY_ALIASES.get(category, category)


def requires_second_material(category: str) -> bool:
    # If the category preset includes material_2, keep dual-material structure.
    preset = CATEGORY_PRESETS.get(category)
    if not preset:
        return False
    return bool(str(preset.get("material_2", "")).strip())


def ensure_distinct_second_material(product: dict, allowed_mats: List[str]) -> bool:
    m1 = product.get("material_1")
    m2 = product.get("material_2")
    if not m2:
        return False
    if m1 != m2:
        return True
    fallback_m2 = next((m for m in allowed_mats if m != m1), None)
    if not fallback_m2:
        return False
    product["material_2"] = fallback_m2
    if float(product.get("material_share_2", 0.0) or 0.0) <= 0:
        product["material_share_1"], product["material_share_2"] = 0.7, 0.3
    return True


def scoring_category(category: str) -> str:
    mapped = normalize_category(category)
    dist = CATEGORY_CO2_DISTRIBUTIONS.get(mapped)
    if dist is not None and len(dist) >= MIN_SAMPLES_FOR_CATEGORY_SCORING:
        return mapped

    proxy = SCORING_PROXY_CATEGORY.get(mapped)
    proxy_dist = CATEGORY_CO2_DISTRIBUTIONS.get(proxy) if proxy else None
    if proxy_dist is not None and len(proxy_dist) >= MIN_SAMPLES_FOR_CATEGORY_SCORING:
        return proxy

    return mapped


def allowed_materials_for_category(category: str) -> List[str]:
    if category in CATEGORY_ALLOWED_MATERIALS:
        return [m for m in CATEGORY_ALLOWED_MATERIALS[category] if m in MATERIAL_OPTIONS]

    mapped = normalize_category(category)
    mask = products["category"] == mapped
    if not mask.any():
        return MATERIAL_OPTIONS
    m1 = products.loc[mask, "material_1"].dropna().unique().tolist()
    m2 = products.loc[mask, "material_2"].dropna()
    m2 = [m for m in m2.tolist() if m]
    all_mats = sorted(set(m1 + m2))
    return all_mats if all_mats else MATERIAL_OPTIONS


def allowed_packaging_for_category(category: str) -> List[str]:
    mapped = normalize_category(category)
    allowed = CATEGORY_ALLOWED_PACKAGING.get(category) or CATEGORY_ALLOWED_PACKAGING.get(mapped)
    if not allowed:
        return NONZERO_PACKAGING_OPTIONS
    filtered = [p for p in allowed if p in NONZERO_PACKAGING_OPTIONS]
    return filtered if filtered else NONZERO_PACKAGING_OPTIONS


def required_anchor_materials_for_category(category: str) -> List[str]:
    mapped = normalize_category(category)
    mats = REQUIRED_ANCHOR_MATERIALS.get(category) or REQUIRED_ANCHOR_MATERIALS.get(mapped) or []
    return [m for m in mats if m in MATERIAL_OPTIONS]


def has_required_anchor_material(product: dict, category: str) -> bool:
    required = required_anchor_materials_for_category(category)
    if not required:
        return True
    present = {product.get("material_1", ""), product.get("material_2", "")}
    return any(m in present for m in required)


def preferred_primary_anchor_for_category(category: str) -> Optional[str]:
    required = set(required_anchor_materials_for_category(category))
    if not required:
        return None
    preset = CATEGORY_PRESETS.get(category, {})
    preset_m1 = preset.get("material_1", "")
    return preset_m1 if preset_m1 in required else None


def enforce_required_anchor_material(product: dict, category: str, allowed_mats: List[str]) -> bool:
    """
    Ensure anchor material presence (e.g., lithium_mix for battery categories).
    Returns True when product satisfies rule after possible adjustment.
    """
    required = [m for m in required_anchor_materials_for_category(category) if m in allowed_mats]
    if not required:
        return True
    if has_required_anchor_material(product, category):
        return True

    anchor = required[0]
    m1 = product.get("material_1")
    m2 = product.get("material_2", "")

    # Prefer placing anchor in material_2 when possible to preserve primary intent.
    if m1 != anchor:
        product["material_2"] = anchor
        if float(product.get("material_share_2", 0.0) or 0.0) <= 0:
            product["material_share_1"], product["material_share_2"] = 0.75, 0.25
        return True

    # Fallback: anchor as material_1, keep material_2 as first different allowed option.
    product["material_1"] = anchor
    fallback_m2 = next((m for m in allowed_mats if m != anchor), "")
    product["material_2"] = fallback_m2
    if fallback_m2:
        if float(product.get("material_share_2", 0.0) or 0.0) <= 0:
            product["material_share_1"], product["material_share_2"] = 0.75, 0.25
    else:
        product["material_share_1"], product["material_share_2"] = 1.0, 0.0
    return True


def enforce_primary_anchor_structure(product: dict, category: str, allowed_mats: List[str]) -> bool:
    """
    Keep anchor material as primary when category preset defines it that way.
    Example: lithium_battery_pack should keep lithium_mix as material_1.
    """
    primary_anchor = preferred_primary_anchor_for_category(category)
    if not primary_anchor:
        return True

    changed = False
    if product.get("material_1") != primary_anchor:
        old_m1 = product.get("material_1", "")
        product["material_1"] = primary_anchor
        changed = True

        # Preserve previous primary material as secondary if valid and distinct.
        if old_m1 and old_m1 != primary_anchor and old_m1 in allowed_mats:
            product["material_2"] = old_m1
        elif not product.get("material_2") or product.get("material_2") == primary_anchor:
            fallback_m2 = next((m for m in allowed_mats if m != primary_anchor), "")
            product["material_2"] = fallback_m2

    # Keep shares realistic around preset ratio when a second material exists.
    preset = CATEGORY_PRESETS.get(category, {})
    target_s1 = float(preset.get("material_share_1", 0.75) or 0.75)
    target_s1 = float(np.clip(target_s1, 0.55, 0.9))

    if product.get("material_2"):
        if (
            float(product.get("material_share_1", 0.0) or 0.0) < target_s1
            or float(product.get("material_share_2", 0.0) or 0.0) <= 0
        ):
            product["material_share_1"] = target_s1
            product["material_share_2"] = 1.0 - target_s1
            changed = True
    else:
        product["material_share_1"], product["material_share_2"] = 1.0, 0.0

    # If material_2 exists, ensure it stays distinct and valid.
    if product.get("material_2") == product.get("material_1"):
        if ensure_distinct_second_material(product, allowed_mats):
            changed = True

    return True


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def is_land_connected(origin: str, destination: str) -> bool:
    if origin == destination:
        return True
    pair = tuple(sorted((origin, destination)))
    if pair in LAND_CONNECTED_PAIRS:
        return True
    return COUNTRY_CONTINENT.get(origin) == COUNTRY_CONTINENT.get(destination) and origin != "taiwan" and destination != "taiwan"


def infer_route_type(origin: str, destination: str) -> str:
    if origin == destination:
        return "domestic_land"
    if COUNTRY_CONTINENT.get(origin) != COUNTRY_CONTINENT.get(destination):
        return "ocean"
    return "land" if is_land_connected(origin, destination) else "ocean"


def recommended_mode_for_route(route_type: str, priority: str) -> str:
    if priority == "fastest":
        return "air"
    if route_type in {"land", "domestic_land"}:
        return "rail"
    return "ship"


def allowed_modes_for_route(route_type: str, priority: str) -> List[str]:
    if priority == "fastest":
        if route_type in {"land", "domestic_land"}:
            return ["truck", "rail", "air"]
        return ["air", "ship"]
    if route_type in {"land", "domestic_land"}:
        return ["rail", "truck"]
    return ["ship", "air"]


def compute_material_carbon_intensity(material_1, share_1, material_2="", share_2=0.0):
    m1 = factor_map.get(("material", material_1), DEFAULT_MATERIAL_FACTOR) * share_1
    m2 = 0.0 if not material_2 else factor_map.get(("material", material_2), DEFAULT_MATERIAL_FACTOR) * share_2
    return m1 + m2


def compute_manufacturing_intensity(kwh, country):
    return kwh * grid_map.get(("grid_intensity", country), 0.0)


def compute_transport_intensity(distance_km, transport_mode):
    return distance_km * factor_map.get(("transport", transport_mode), 0.0)


def compute_packaging_kg(packaging_type: str, unit_weight_kg: float) -> float:
    """
    Convert packaging factor (kg CO2e per unit) into a weight-sensitive estimate.
    Sublinear scaling avoids over-penalizing heavy products while still reflecting
    that larger/heavier units usually require more packaging.
    """
    base = float(factor_map.get(("packaging", packaging_type), 0.0))
    weight = max(float(unit_weight_kg or 0.0), 0.001)
    # 0.5 kg unit is reference. Clamp multiplier to stay realistic.
    multiplier = float(np.clip((weight / 0.5) ** 0.35, 0.6, 12.0))
    return base * multiplier


def score_from_category_percentile(co2_kg: float, category: str) -> float:
    mapped = scoring_category(category)
    distribution = CATEGORY_CO2_DISTRIBUTIONS.get(mapped, GLOBAL_CO2_DISTRIBUTION)
    if len(distribution) == 0:
        return 50.0
    percentile = np.searchsorted(distribution, co2_kg, side="right") / len(distribution)
    return float(np.clip(100 * (1 - percentile), 0, 100))


def grade_from_score(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    if score >= 25:
        return "E"
    return "F"


def make_model_features(p: dict):
    material_carbon_intensity = compute_material_carbon_intensity(
        p.get("material_1", ""),
        float(p.get("material_share_1", 0.0) or 0.0),
        p.get("material_2", ""),
        float(p.get("material_share_2", 0.0) or 0.0),
    )
    manufacturing_intensity = compute_manufacturing_intensity(
        float(p.get("manufacturing_energy_kwh", 0.0) or 0.0),
        p.get("manufacturing_country", ""),
    )
    transport_intensity = compute_transport_intensity(
        float(p.get("distance_km", 0.0) or 0.0),
        p.get("transport_mode", ""),
    )

    row = {col: 0.0 for col in FEATURE_COLUMNS}
    numeric_values = {
        "unit_weight_kg": float(p.get("unit_weight_kg", 0.0) or 0.0),
        "distance_km": float(p.get("distance_km", 0.0) or 0.0),
        "manufacturing_energy_kwh": float(p.get("manufacturing_energy_kwh", 0.0) or 0.0),
        "recycled_content_pct": float(p.get("recycled_content_pct", 0.0) or 0.0),
        "material_carbon_intensity": material_carbon_intensity,
        "manufacturing_intensity": manufacturing_intensity,
        "transport_intensity": transport_intensity,
    }
    for col, value in numeric_values.items():
        if col in row:
            row[col] = value

    for base in ["manufacturing_country", "transport_mode", "packaging_type", "certification"]:
        value = p.get(base, "")
        dummy_col = f"{base}_{value}"
        if dummy_col in row:
            row[dummy_col] = 1.0

    return pd.DataFrame([row], columns=FEATURE_COLUMNS)


def predict_co2(p: dict) -> float:
    return float(rf.predict(make_model_features(p))[0])


def approximate_breakdown(product: dict, predicted_total_kg: float) -> Dict[str, Any]:
    material_kg = compute_material_carbon_intensity(
        product.get("material_1", ""),
        float(product.get("material_share_1", 0.0) or 0.0),
        product.get("material_2", ""),
        float(product.get("material_share_2", 0.0) or 0.0),
    )
    manufacturing_kg = factor_map.get(("manufacturing", product.get("manufacturing_country", "")), 0.0) + compute_manufacturing_intensity(
        float(product.get("manufacturing_energy_kwh", 0.0) or 0.0),
        product.get("manufacturing_country", ""),
    )
    transport_factor = factor_map.get(("transport", product.get("transport_mode", "")), 0.0)
    tons = max(float(product.get("unit_weight_kg", 0.0) or 0.0), 0.0) / 1000.0
    transport_kg = max(float(product.get("distance_km", 0.0) or 0.0), 0.0) * transport_factor * tons
    packaging_kg = compute_packaging_kg(
        product.get("packaging_type", ""),
        float(product.get("unit_weight_kg", 0.0) or 0.0),
    )

    raw = {
        "materials_kg": max(material_kg, 0.0),
        "manufacturing_kg": max(manufacturing_kg, 0.0),
        "transport_kg": max(transport_kg, 0.0),
        "packaging_kg": max(packaging_kg, 0.0),
    }
    raw_total = sum(raw.values())
    scale = (predicted_total_kg / raw_total) if raw_total > 0 else 0.0
    scaled = {k: v * scale for k, v in raw.items()}
    shares = {k.replace("_kg", "_percent"): (100 * v / predicted_total_kg if predicted_total_kg > 0 else 0.0) for k, v in scaled.items()}
    return {
        "components_kg": {k: round(v, 3) for k, v in scaled.items()},
        "shares_percent": {k: round(v, 1) for k, v in shares.items()},
        "model_total_kg": round(predicted_total_kg, 3),
        "method": "Breakdown is an explainability proxy scaled to the ML total.",
    }


def normalize_and_validate(product: dict, category: str) -> tuple[dict, Dict[str, Any], List[str]]:
    p = product.copy()
    warnings = []

    p["shipping_priority"] = p.get("shipping_priority", p.get("priority", "greenest"))
    if p["shipping_priority"] not in SHIPPING_PRIORITIES:
        p["shipping_priority"] = "greenest"

    p["destination_country"] = p.get("destination_country", p.get("consumer_country", "usa"))
    if p["destination_country"] not in COUNTRY_COORDS:
        p["destination_country"] = "usa"
        warnings.append("Unknown destination_country; defaulted to usa.")

    if p.get("manufacturing_country") not in COUNTRY_COORDS:
        warnings.append("Unknown manufacturing_country for routing; distance fallback used.")

    # Auto-normalize shares to sum to 1
    s1 = max(float(p.get("material_share_1", 0.0) or 0.0), 0.0)
    s2 = max(float(p.get("material_share_2", 0.0) or 0.0), 0.0) if p.get("material_2", "") else 0.0
    total = s1 + s2
    if total <= 0:
        s1, s2 = 1.0, 0.0
        p["material_2"] = ""
    else:
        s1, s2 = s1 / total, s2 / total
    p["material_share_1"], p["material_share_2"] = s1, s2

    p["unit_weight_kg"] = max(float(p.get("unit_weight_kg", 0.0) or 0.0), 0.001)
    p["manufacturing_energy_kwh"] = max(float(p.get("manufacturing_energy_kwh", 0.0) or 0.0), 0.05)
    p["recycled_content_pct"] = float(np.clip(float(p.get("recycled_content_pct", 0.0) or 0.0), 0.0, 100.0))

    route_type = infer_route_type(p.get("manufacturing_country", ""), p.get("destination_country", ""))
    recommended_mode = recommended_mode_for_route(route_type, p["shipping_priority"])
    allowed_modes = allowed_modes_for_route(route_type, p["shipping_priority"])

    if p.get("transport_mode") == "auto":
        p["transport_mode"] = recommended_mode
    elif p.get("transport_mode") not in allowed_modes:
        p["transport_mode"] = recommended_mode
        warnings.append(f"Transport mode auto-adjusted to {recommended_mode} for this route.")

    p["distance_km"] = resolve_distance_km(p.get("manufacturing_country", ""), p.get("destination_country", ""))

    # Realism + category constraints for packaging.
    allowed_packs = allowed_packaging_for_category(category)
    best_packaging = min(allowed_packs, key=lambda pk: factor_map.get(("packaging", pk), 999.0))
    if p.get("packaging_type") not in allowed_packs:
        p["packaging_type"] = best_packaging
        warnings.append(f"Packaging adjusted to {best_packaging} for this category.")
    elif factor_map.get(("packaging", p.get("packaging_type", "")), 0.0) <= 0:
        p["packaging_type"] = best_packaging
        warnings.append(f"Packaging set to {best_packaging}; zero-packaging is disabled.")

    # Product constraints for materials
    allowed_mats = allowed_materials_for_category(category)
    best_material = min(allowed_mats, key=lambda m: factor_map.get(("material", m), 999.0))

    if p.get("material_1") not in allowed_mats:
        p["material_1"] = best_material
        warnings.append("Material 1 adjusted to category-compatible option.")
    if p.get("material_2") and p.get("material_2") not in allowed_mats:
        p["material_2"] = ""
        p["material_share_1"], p["material_share_2"] = 1.0, 0.0
        warnings.append("Material 2 removed because it is not valid for this product category.")

    # Enforce dual-material realism for selected hardware categories.
    if requires_second_material(category):
        if not p.get("material_2"):
            fallback_m2 = next((m for m in allowed_mats if m != p.get("material_1")), None)
            if fallback_m2:
                p["material_2"] = fallback_m2
                if float(p.get("material_share_2", 0.0) or 0.0) <= 0:
                    p["material_share_1"], p["material_share_2"] = 0.7, 0.3
                warnings.append("Material 2 added to preserve dual-material structure for this category.")
        elif p.get("material_2") == p.get("material_1"):
            if ensure_distinct_second_material(p, allowed_mats):
                warnings.append("Material 2 adjusted to keep materials distinct for this category.")
    elif p.get("material_2") and p.get("material_2") == p.get("material_1"):
        if ensure_distinct_second_material(p, allowed_mats):
            warnings.append("Material 2 adjusted to avoid duplicate material pair.")

    if not has_required_anchor_material(p, category):
        enforce_required_anchor_material(p, category, allowed_mats)
        warnings.append("Anchor material adjusted to preserve physical realism for this category.")

    if preferred_primary_anchor_for_category(category):
        enforce_primary_anchor_structure(p, category, allowed_mats)

    route_info = {
        "origin_country": p.get("manufacturing_country"),
        "destination_country": p.get("destination_country"),
        "route_type": route_type,
        "distance_km": round(p["distance_km"], 1),
        "recommended_transport_mode": recommended_mode,
        "allowed_transport_modes": allowed_modes,
        "shipping_priority": p["shipping_priority"],
    }
    return p, route_info, warnings


def confidence_warnings(p: dict, category: str) -> List[str]:
    mapped = normalize_category(category)
    bounds = CATEGORY_BOUNDS.get(mapped)
    if not bounds:
        return []

    warnings = []
    for k in ["unit_weight_kg", "distance_km", "manufacturing_energy_kwh", "recycled_content_pct"]:
        lo, hi = bounds[k]
        v = float(p.get(k, 0.0))
        if v < lo or v > hi:
            warnings.append(f"{k} is outside typical {mapped} range ({round(lo, 3)} to {round(hi, 3)}).")
    return warnings


def resolve_distance_km(origin: str, destination: str) -> float:
    pair = (origin, destination)
    d = float(ROUTE_PAIR_DISTANCE.get(pair, 0.0))
    if d > 0:
        return round(d, 1)
    d_raw = float(ROUTE_PAIR_RAW_DISTANCE.get(pair, 0.0))
    if d_raw > 0:
        return round(d_raw, 1)

    origin_coords = COUNTRY_COORDS.get(origin)
    destination_coords = COUNTRY_COORDS.get(destination)
    if origin_coords and destination_coords:
        hav = haversine_km(origin_coords[0], origin_coords[1], destination_coords[0], destination_coords[1])
        if hav > 0:
            return round(hav, 1)
    return round(DEFAULT_DISTANCE_KM, 1)


def distance_advice(origin: str, destination: str, priority: str = "greenest") -> Dict[str, Any]:
    origin_key = origin if origin in COUNTRY_COORDS else "usa"
    destination_key = destination if destination in COUNTRY_COORDS else "usa"
    route_type = infer_route_type(origin_key, destination_key)
    recommended_mode = recommended_mode_for_route(route_type, priority if priority in SHIPPING_PRIORITIES else "greenest")
    allowed_modes = allowed_modes_for_route(route_type, priority if priority in SHIPPING_PRIORITIES else "greenest")

    distance_km = resolve_distance_km(origin_key, destination_key)

    return {
        "origin": origin_key,
        "destination": destination_key,
        "priority": priority if priority in SHIPPING_PRIORITIES else "greenest",
        "distance_km": distance_km,
        "route_type": route_type,
        "recommended_mode": recommended_mode,
        "allowed_modes": allowed_modes,
    }


def recommend_greener_version(p: dict, category: str, route_info: Dict[str, Any]) -> dict:
    base = p.copy()
    current = base.copy()
    current_co2 = predict_co2(current)
    allowed_mats = allowed_materials_for_category(category)
    allowed_modes = route_info["allowed_transport_modes"]
    low_packaging = sorted(allowed_packaging_for_category(category), key=lambda pk: factor_map.get(("packaging", pk), 1e9))[:4]

    def neighbors(prod: dict) -> List[dict]:
        cand = []
        cur_transport_factor = factor_map.get(("transport", prod.get("transport_mode", "")), 1e9)
        cur_packaging_factor = factor_map.get(("packaging", prod.get("packaging_type", "")), 1e9)
        cur_material_intensity = compute_material_carbon_intensity(
            prod.get("material_1", ""),
            float(prod.get("material_share_1", 0.0) or 0.0),
            prod.get("material_2", ""),
            float(prod.get("material_share_2", 0.0) or 0.0),
        )

        for mode in allowed_modes:
            mode_factor = factor_map.get(("transport", mode), 1e9)
            if mode != prod.get("transport_mode") and mode_factor < cur_transport_factor:
                c = prod.copy()
                c["transport_mode"] = mode
                cand.append(c)

        for pk in low_packaging:
            pack_factor = factor_map.get(("packaging", pk), 1e9)
            if pk != prod.get("packaging_type") and pack_factor < cur_packaging_factor:
                c = prod.copy()
                c["packaging_type"] = pk
                cand.append(c)

        best_mats = sorted(allowed_mats, key=lambda m: factor_map.get(("material", m), 1e9))[:4]
        for field in ["material_1", "material_2"]:
            for m in best_mats:
                if m != prod.get(field):
                    c = prod.copy()
                    c[field] = m
                    new_intensity = compute_material_carbon_intensity(
                        c.get("material_1", ""),
                        float(c.get("material_share_1", 0.0) or 0.0),
                        c.get("material_2", ""),
                        float(c.get("material_share_2", 0.0) or 0.0),
                    )
                    if new_intensity < cur_material_intensity:
                        cand.append(c)

        # Optional single-material simplification is disabled for categories
        # where a dual-material structure should be preserved.
        if not requires_second_material(category):
            for m in best_mats:
                c = prod.copy()
                c["material_1"] = m
                c["material_2"] = ""
                c["material_share_1"] = 1.0
                c["material_share_2"] = 0.0
                new_intensity = compute_material_carbon_intensity(
                    c.get("material_1", ""),
                    float(c.get("material_share_1", 0.0) or 0.0),
                    c.get("material_2", ""),
                    float(c.get("material_share_2", 0.0) or 0.0),
                )
                if new_intensity < cur_material_intensity:
                    cand.append(c)

        for f in [0.95, 0.9, 0.85]:
            c = prod.copy()
            c["manufacturing_energy_kwh"] = max(float(prod.get("manufacturing_energy_kwh", 0.0)) * f, 0.05)
            cand.append(c)

        for r in [70.0, 85.0, 100.0]:
            if float(prod.get("recycled_content_pct", 0.0)) < r:
                c = prod.copy()
                c["recycled_content_pct"] = r
                cand.append(c)

        if requires_second_material(category):
            filtered = []
            for c in cand:
                if not c.get("material_2"):
                    continue
                if c.get("material_1") == c.get("material_2"):
                    c = c.copy()
                    if not ensure_distinct_second_material(c, allowed_mats):
                        continue
                if not has_required_anchor_material(c, category):
                    c = c.copy()
                    enforce_required_anchor_material(c, category, allowed_mats)
                    if not has_required_anchor_material(c, category):
                        continue
                if preferred_primary_anchor_for_category(category):
                    c = c.copy()
                    enforce_primary_anchor_structure(c, category, allowed_mats)
                if c.get("material_2") == c.get("material_1"):
                    c = c.copy()
                    if not ensure_distinct_second_material(c, allowed_mats):
                        continue
                filtered.append(c)
            return filtered
        filtered = []
        for c in cand:
            if not has_required_anchor_material(c, category):
                c = c.copy()
                enforce_required_anchor_material(c, category, allowed_mats)
                if not has_required_anchor_material(c, category):
                    continue
            if preferred_primary_anchor_for_category(category):
                c = c.copy()
                enforce_primary_anchor_structure(c, category, allowed_mats)
            if c.get("material_2") and c.get("material_2") == c.get("material_1"):
                c = c.copy()
                if not ensure_distinct_second_material(c, allowed_mats):
                    continue
            filtered.append(c)
        return filtered

    for _ in range(10):
        best_local = current
        best_local_co2 = current_co2
        for c in neighbors(current):
            co2 = predict_co2(c)
            if co2 < best_local_co2 - 1e-6:
                best_local = c
                best_local_co2 = co2
        if best_local_co2 >= current_co2 - 1e-6:
            break
        current = best_local
        current_co2 = best_local_co2

    return current


def climatechain_analyze(product_dict: dict, category: str):
    normalized, route_info, input_warnings = normalize_and_validate(product_dict, category)
    co2_orig = predict_co2(normalized)
    greener = recommend_greener_version(normalized, category, route_info)
    co2_green = predict_co2(greener)
    reduction_pct = 100 * (co2_orig - co2_green) / co2_orig if co2_orig > 0 else 0

    changes = []
    tracked_fields = [
        "transport_mode",
        "packaging_type",
        "material_1",
        "material_2",
        "manufacturing_country",
        "manufacturing_energy_kwh",
        "recycled_content_pct",
        "material_share_1",
        "material_share_2",
    ]
    for k in tracked_fields:
        if normalized.get(k) != greener.get(k):
            one_change = normalized.copy()
            one_change[k] = greener.get(k)
            co2_one = predict_co2(one_change)
            savings = max(co2_orig - co2_one, 0.0)
            changes.append(
                {
                    "field": k,
                    "from": normalized.get(k),
                    "to": greener.get(k),
                    "estimated_savings_kg_per_unit": round(savings, 3),
                }
            )

    score_orig = score_from_category_percentile(co2_orig, category)
    score_green = score_from_category_percentile(co2_green, category)
    breakdown_orig = approximate_breakdown(normalized, co2_orig)
    breakdown_green = approximate_breakdown(greener, co2_green)
    conf_warnings = confidence_warnings(normalized, category)

    return {
        "used_origin": normalized.get("manufacturing_country"),
        "used_destination": normalized.get("destination_country"),
        "used_distance_km": round(float(normalized.get("distance_km", 0.0) or 0.0), 1),
        "used_transport_mode": normalized.get("transport_mode"),
        "original": {
            "predicted_co2_kg": round(co2_orig, 3),
            "score_0_100": round(score_orig, 1),
            "grade": grade_from_score(score_orig),
        },
        "recommended": {
            "predicted_co2_kg": round(co2_green, 3),
            "score_0_100": round(score_green, 1),
            "grade": grade_from_score(score_green),
        },
        "impact": {"reduction_percent": round(reduction_pct, 1)},
        "changes": sorted(changes, key=lambda x: x["estimated_savings_kg_per_unit"], reverse=True),
        "recommended_product": greener,
        "breakdown": {"original": breakdown_orig, "recommended": breakdown_green},
        "routing": route_info,
        "warnings": input_warnings + conf_warnings,
        "lifecycle_boundary": "Estimate includes manufacturing + packaging + transport per unit; excludes use-phase and end-of-life.",
        "confidence": {
            "status": "low" if conf_warnings else "normal",
            "out_of_range_fields": conf_warnings,
        },
    }


# -----------------------------
# Schemas
# -----------------------------
class Product(BaseModel):
    unit_weight_kg: float
    manufacturing_energy_kwh: float
    recycled_content_pct: float

    material_1: str
    material_share_1: float
    material_2: str = ""
    material_share_2: float = 0.0

    manufacturing_country: str
    destination_country: str = "usa"
    transport_mode: str
    packaging_type: str
    certification: str
    shipping_priority: str = "greenest"
    distance_km: Optional[float] = None


# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def root():
    return {"message": "ClimateChain API running", "routes": ["/health", "/metadata", "/distance", "/analyze/{category}"]}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/distance")
def distance(
    origin: str = Query(...),
    destination: str = Query(...),
    priority: str = Query("greenest"),
):
    return distance_advice(origin, destination, priority)


@app.get("/metadata")
def metadata() -> Dict[str, Any]:
    categories = ALL_CATEGORIES
    certs = ["none", "gots", "fsc", "fair_trade", "energy_star"]
    regions = sorted(energy.loc[energy["metric"] == "grid_intensity", "region"].unique().tolist())
    materials_by_category = {cat: allowed_materials_for_category(cat) for cat in categories}
    category_allowed_materials = {
        cat: materials_by_category.get(cat, MATERIAL_OPTIONS) for cat in categories
    }
    category_presets = {
        cat: CATEGORY_PRESETS.get(cat, CATEGORY_PRESETS["t_shirt"]) for cat in categories
    }

    return {
        "categories": categories,
        "materials": MATERIAL_OPTIONS,
        "materials_by_category": materials_by_category,
        "category_allowed_materials": category_allowed_materials,
        "category_presets": category_presets,
        "transport_modes": sorted(factors.loc[factors["stage"] == "transport", "type"].unique().tolist()),
        "packaging_types": PACKAGING_OPTIONS,
        "manufacturing_countries": regions,
        "destination_countries": sorted(COUNTRY_COORDS.keys()),
        "consumer_countries": sorted(COUNTRY_COORDS.keys()),
        "shipping_priorities": SHIPPING_PRIORITIES,
        "certifications": certs,
        "lifecycle_boundary": "manufacturing + packaging + transport",
    }


@app.post("/analyze/{category}")
def analyze(category: str, product: Product):
    return climatechain_analyze(product.model_dump(), category)
