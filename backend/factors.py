# backend/factors.py
# Starter emission factors. Tune these later per region/authority.
FACTORS = {
    # transport
    "car_petrol_kgco2_per_km": 0.192,
    "car_petrol_kgco2_per_liter": 2.31,
    "bus_kgco2_per_km": 0.105,
    "train_kgco2_per_km": 0.041,
    "flight_short_kgco2_per_km": 0.255,
    # electricity
    "electricity_kgco2_per_kwh": 0.475,
    # food (per kg)
    "beef_kgco2_per_kg": 27.0,
    "chicken_kgco2_per_kg": 6.9,
    "avg_meal_kgco2": 2.5,
    # waste
    "waste_kgco2_per_kg": 1.0
}

# Photo label -> mapping for quick estimation (label normalised to lowercase)
PHOTO_LABEL_MAP = {
    "beef burger": {"category": "food", "kg": 0.2, "factor_key": "beef_kgco2_per_kg"},
    "burger": {"category": "food", "kg": 0.2, "factor_key": "beef_kgco2_per_kg"},
    "beef": {"category": "food", "kg": 0.2, "factor_key": "beef_kgco2_per_kg"},
    "chicken": {"category": "food", "kg": 0.2, "factor_key": "chicken_kgco2_per_kg"},
    "chicken sandwich": {"category": "food", "kg": 0.2, "factor_key": "chicken_kgco2_per_kg"},
    "soda can": {"category": "drink", "kg": 0.02, "factor_key": "avg_meal_kgco2"},
    # Add more mappings as you discover labels
}
