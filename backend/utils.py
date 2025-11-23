# backend/utils.py
from .factors import FACTORS, PHOTO_LABEL_MAP
import json, math

# emission factors (same as earlier)
# We'll include a small copy so backend can import without circular imports.
FACTORS = {
    "car_petrol_kgco2_per_km": 0.192,
    "car_petrol_kgco2_per_liter": 2.31,
    "bus_kgco2_per_km": 0.105,
    "train_kgco2_per_km": 0.041,
    "flight_short_kgco2_per_km": 0.255,
    "electricity_kgco2_per_kwh": 0.475,
    "beef_kgco2_per_kg": 27.0,
    "chicken_kgco2_per_kg": 6.9,
    "avg_meal_kgco2": 2.5,
    "waste_kgco2_per_kg": 1.0
}

PHOTO_LABEL_MAP = {
    "beef burger": {"category": "food", "kg": 0.2, "factor_key": "beef_kgco2_per_kg"},
    "burger": {"category": "food", "kg": 0.2, "factor_key": "beef_kgco2_per_kg"},
    "beef": {"category": "food", "kg": 0.25, "factor_key": "beef_kgco2_per_kg"},
    "chicken": {"category": "food", "kg": 0.2, "factor_key": "chicken_kgco2_per_kg"},
    "soda can": {"category": "drink", "kg": 0.02, "factor_key": "avg_meal_kgco2"},
}

def calc_transport_km(vehicle_type, km, passengers=1, fuel_liters=None):
    km = float(km or 0)
    passengers = int(passengers or 1)
    if vehicle_type == "car_petrol":
        if fuel_liters:
            return float(fuel_liters) * FACTORS["car_petrol_kgco2_per_liter"]
        return km * FACTORS["car_petrol_kgco2_per_km"] / max(passengers,1)
    if vehicle_type == "bus":
        return km * FACTORS["bus_kgco2_per_km"]
    if vehicle_type == "train":
        return km * FACTORS["train_kgco2_per_km"]
    if vehicle_type == "flight_short":
        return km * FACTORS["flight_short_kgco2_per_km"]
    return 0.0

def calc_electricity_kwh(kwh):
    return float(kwh or 0) * FACTORS["electricity_kgco2_per_kwh"]

def calc_waste(kg):
    return float(kg or 0) * FACTORS["waste_kgco2_per_kg"]

def estimate_from_photo_labels(labels):
    total = 0.0
    details = []
    for lbl in labels:
        name = (lbl.get("label") or "").lower()
        conf = float(lbl.get("confidence") or 0.0)
        mapped = PHOTO_LABEL_MAP.get(name)
        if mapped and conf > 0.2:
            factor = FACTORS.get(mapped["factor_key"], FACTORS["avg_meal_kgco2"])
            kg_value = mapped.get("kg", 0.2)
            est = kg_value * factor
            total += est
            details.append({"label": name, "confidence": conf, "estimated_kgco2": round(est,4)})
        else:
            details.append({"label": name, "confidence": conf, "estimated_kgco2": None})
    return round(total,4), details
