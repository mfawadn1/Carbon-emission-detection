# streamlit_app/app.py
import streamlit as st
import requests, os, json, io, base64
from PIL import Image
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")

st.set_page_config(page_title="CarbonTracker", layout="wide", initial_sidebar_state="expanded")

# -------------------------------
# Helpers
# -------------------------------
def post_form(path: str, form_data: dict = None, files: dict = None):
    """Send a POST to backend where token and other fields are expected as form fields."""
    url = API_BASE.rstrip("/") + path
    try:
        if files:
            resp = requests.post(url, data=form_data or {}, files=files, timeout=60)
        else:
            resp = requests.post(url, data=form_data or {}, timeout=30)
        resp.raise_for_status()
        return resp
    except Exception as e:
        raise

def get_json(path: str, params: dict = None):
    url = API_BASE.rstrip("/") + path
    resp = requests.get(url, params=params or {}, timeout=30)
    resp.raise_for_status()
    return resp.json()

def display_line_chart(dates, values, title=""):
    fig, ax = plt.subplots(figsize=(8,3))
    ax.plot(pd.to_datetime(dates), values, marker="o")
    ax.set_title(title)
    ax.set_ylabel("kg CO2")
    ax.grid(alpha=0.2)
    st.pyplot(fig)

# -------------------------------
# Sidebar: Auth (Signup / Login)
# -------------------------------
if "token" not in st.session_state:
    st.session_state["token"] = None
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

st.sidebar.title("Account")
mode = st.sidebar.radio("Account action", ["Login","Signup","Profile"])

if mode == "Signup":
    with st.sidebar.form("signup_form"):
        first = st.text_input("First name")
        last = st.text_input("Last name")
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Create account")
        if submitted:
            try:
                payload = {"first_name": first, "last_name": last, "email": email, "password": pwd}
                r = requests.post(f"{API_BASE}/signup", json=payload, timeout=30)
                if r.ok:
                    data = r.json()
                    st.success("Account created — logged in")
                    st.session_state["token"] = data.get("token") or ""
                    st.session_state["user_info"] = {"user_id": data.get("user_id"), "first_name": data.get("first_name"), "last_name": data.get("last_name"), "email": data.get("email")}
                else:
                    st.error(r.text)
            except Exception as e:
                st.error(f"Signup failed: {e}")

elif mode == "Login":
    with st.sidebar.form("login_form"):
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            try:
                r = requests.post(f"{API_BASE}/login", json={"email": email, "password": pwd}, timeout=30)
                if r.ok:
                    data = r.json()
                    st.success("Logged in")
                    st.session_state["token"] = data.get("token")
                    st.session_state["user_info"] = {"user_id": data.get("user_id"), "first_name": data.get("first_name"), "last_name": data.get("last_name"), "email": data.get("email")}
                else:
                    st.error("Login failed: " + r.text)
            except Exception as e:
                st.error("Login failed: " + str(e))

else:
    if st.session_state["user_info"]:
        st.sidebar.write("Logged in as", st.session_state["user_info"]["first_name"])
        if st.sidebar.button("Logout"):
            st.session_state["token"] = None
            st.session_state["user_info"] = None
            st.experimental_rerun()
    else:
        st.sidebar.info("Please log in or sign up")

# -------------------------------
# Main app (requires login)
# -------------------------------
if not st.session_state["token"]:
    st.title("Welcome to CarbonTracker")
    st.write("Please login or sign up to access the dashboard.")
    st.stop()

token = st.session_state["token"]

# top navigation tabs
tabs = st.tabs(["Dashboard","Survey & Prediction","Add Activity","Photo Upload","History","Goals","Leaderboard","AI Assistant"])
tab_dashboard, tab_survey, tab_add, tab_photo, tab_history, tab_goals, tab_leader, tab_ai = tabs

# -------------------------------
# Dashboard tab (FIXED)
# -------------------------------
with tab_dashboard:
    st.header("Dashboard")

    # fetch entries
    try:
        entries = requests.get(f"{API_BASE}/entries", params={"token": token}, timeout=30).json()
    except Exception as e:
        st.error("Could not fetch data: " + str(e))
        entries = []

    df = pd.DataFrame(entries)

    if df.empty:
        st.info("No activity yet. Add an activity or upload a photo to start tracking.")
    else:
        # normalize timestamp
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date

        # ===========================================
        # DAILY EMISSIONS (LINE CHART) — last 30 days
        # ===========================================
        daily = df.groupby("date")["emissions_kgco2"].sum().reset_index()
        daily_sorted = daily.sort_values("date")
        last30 = daily_sorted.tail(30)

        fig1, ax1 = plt.subplots()
        ax1.plot(last30["date"], last30["emissions_kgco2"], marker="o")
        ax1.set_title("Daily CO2 Emissions (Last 30 Days)")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("kg CO2")
        ax1.grid(alpha=0.2)
        st.pyplot(fig1)

        # ===========================================
        # CATEGORY BREAKDOWN (BAR CHART)
        # ===========================================
        # ensure category column exists
        if "category" not in df.columns:
            df["category"] = "unknown"
        cat = df.groupby("category")["emissions_kgco2"].sum().reset_index()

        fig2, ax2 = plt.subplots()
        ax2.bar(cat["category"], cat["emissions_kgco2"])
        ax2.set_title("CO2 by Category")
        ax2.set_xlabel("Category")
        ax2.set_ylabel("kg CO2")
        st.pyplot(fig2)

        # ===========================================
        # CATEGORY SHARE (PIE CHART) - safe
        # ===========================================
        if cat["emissions_kgco2"].sum() > 0:
            fig3, ax3 = plt.subplots()
            ax3.pie(cat["emissions_kgco2"], labels=cat["category"], autopct="%1.1f%%")
            ax3.set_title("CO2 Share by Category")
            st.pyplot(fig3)
        else:
            st.info("No category emissions to display in pie chart.")

        # ===========================================
        # METRIC: Average last 7 days
        # ===========================================
        if len(daily_sorted) >= 7:
            avg7 = daily_sorted.tail(7)["emissions_kgco2"].mean()
            st.metric("Avg daily (last 7 days)", round(avg7, 3))
        else:
            # show average of available days if some exist
            if len(daily_sorted) > 0:
                avg = daily_sorted["emissions_kgco2"].mean()
                st.metric("Avg daily (available)", round(avg,3))
            else:
                st.metric("Avg daily (last 7 days)", "Not enough data")

# -------------------------------
# Survey & Prediction tab
# -------------------------------
with tab_survey:
    st.header("Detailed Carbon Survey")
    st.write("Fill in your household and lifestyle details for a personalized prediction + AI suggestions.")
    with st.form("survey_form"):
        # transportation
        weekly_car_km = st.number_input("Avg car km per week", min_value=0.0, value=0.0)
        weekly_bus_km = st.number_input("Avg bus km per week", min_value=0.0, value=0.0)
        weekly_train_km = st.number_input("Avg train km per week", min_value=0.0, value=0.0)
        flights_per_year = st.number_input("Number of return flights per year (short-haul)", min_value=0)
        # electricity
        monthly_kwh = st.number_input("Electricity (kWh per month)", min_value=0.0, value=200.0)
        # food
        beef_meals_per_week = st.number_input("Beef meals per week", min_value=0)
        avg_meals_per_week = st.number_input("Total meals per week", min_value=7, value=21)
        # waste
        waste_kg_per_week = st.number_input("Waste (kg per week)", min_value=0.0, value=2.0)
        submitted = st.form_submit_button("Predict & Get Suggestions")
        if submitted:
            # build payload
            payload = {
                "weekly_car_km": weekly_car_km,
                "weekly_bus_km": weekly_bus_km,
                "weekly_train_km": weekly_train_km,
                "flights_per_year": flights_per_year,
                "monthly_kwh": monthly_kwh,
                "beef_meals_per_week": beef_meals_per_week,
                "avg_meals_per_week": avg_meals_per_week,
                "waste_kg_per_week": waste_kg_per_week
            }
            prompt = f"Estimate annual CO2 footprint given this user data: {json.dumps(payload)}. Provide a numeric estimate (kg CO2/year) and 5 practical suggestions to reduce it."
            # call assistant (server-side Gemini)
            try:
                r = post_form("/gemini_client", form_data={"token": token, "prompt": prompt})
                ai_text = r.json().get("response") if hasattr(r, "json") else "No AI response"
            except Exception as e:
                ai_text = "AI error: " + str(e)

            # crude prediction by formula on client for immediate feedback
            pred = 0.0
            pred += weekly_car_km * 52 * 0.192
            pred += weekly_bus_km * 52 * 0.105
            pred += weekly_train_km * 52 * 0.041
            pred += flights_per_year * 500 * 0.255  # rough average short-haul distance 500km roundtrip
            pred += monthly_kwh * 12 * 0.475
            pred += beef_meals_per_week * 52 * 5.4  # each beef meal ~5.4 kg
            pred += waste_kg_per_week * 52 * 1.0
            st.subheader("Predicted annual CO2 (client-side estimate)")
            st.metric("Estimate (kg CO2 / year)", round(pred, 2))
            st.subheader("AI Suggestions & Review")
            st.write(ai_text)

# -------------------------------
# Add Activity tab (multiple sub-tabs)
# -------------------------------
with tab_add:
    st.header("Add Activity")
    sub = st.tabs(["Transport","Electricity","Food/Waste","Purchase"])
    with sub[0]:
        st.subheader("Transport")
        vehicle = st.selectbox("Vehicle type", ["car_petrol","bus","train","flight_short"])
        km = st.number_input("Distance (km)", min_value=0.0)
        passengers = st.number_input("Passengers", min_value=1, value=1)
        fuel_liters = st.number_input("Fuel liters (optional)", min_value=0.0, value=0.0)
        if st.button("Submit transport"):
            details = {"vehicle_type": vehicle, "km": km, "passengers": int(passengers)}
            if fuel_liters>0:
                details["fuel_liters"] = float(fuel_liters)
            # send to backend
            try:
                r = post_form("/entries", form_data={"token": token, "category": "transport", "details": json.dumps(details)})
                st.success("Added: " + str(r.json() if hasattr(r, "json") else r.text))
            except Exception as e:
                st.error("Error adding entry: " + str(e))

    with sub[1]:
        st.subheader("Electricity")
        kwh = st.number_input("kWh used", min_value=0.0)
        appliance = st.text_input("Appliance (optional)")
        if st.button("Submit electricity"):
            details = {"kwh": float(kwh), "appliance": appliance}
            try:
                r = post_form("/entries", form_data={"token": token, "category": "electricity", "details": json.dumps(details)})
                st.success("Added electricity")
            except Exception as e:
                st.error("Error: " + str(e))

    with sub[2]:
        st.subheader("Food & Waste")
        food_desc = st.text_input("Food description")
        food_kg = st.number_input("Estimated kg", min_value=0.0, value=0.2)
        waste_kg = st.number_input("Waste (kg)", min_value=0.0, value=0.0)
        if st.button("Submit food/waste"):
            details = {"food_desc": food_desc, "food_kg": float(food_kg), "waste_kg": float(waste_kg)}
            try:
                r = post_form("/entries", form_data={"token": token, "category": "food", "details": json.dumps(details)})
                st.success("Added food/waste")
            except Exception as e:
                st.error("Error: " + str(e))

    with sub[3]:
        st.subheader("Purchase")
        desc = st.text_input("Item description")
        est = st.number_input("Estimated kgCO2", min_value=0.0, value=0.0)
        if st.button("Submit purchase"):
            details = {"desc": desc, "estimated_kgco2": float(est)}
            try:
                r = post_form("/entries", form_data={"token": token, "category": "purchase", "details": json.dumps(details)})
                st.success("Added purchase")
            except Exception as e:
                st.error("Error: " + str(e))

# -------------------------------
# Photo Upload tab
# -------------------------------
with tab_photo:
    st.header("Photo Upload & Object Detection")
    uploaded = st.file_uploader("Upload a photo (food, receipt, trash, appliance)", type=["jpg","png","jpeg"])
    if uploaded is not None:
        st.image(Image.open(uploaded).convert("RGB"), caption="Preview", use_column_width=True)
        if st.button("Analyze photo"):
            try:
                files = {"file": (uploaded.name, uploaded.getvalue())}
                resp = post_form("/photos/upload", form_data={"token": token}, files=files)
                res = resp.json() if hasattr(resp, "json") else {}
                est = res.get("estimated_kgco2") or res.get("estimated_kgco2", 0)
                det = res.get("detection_details") or res.get("detection_details", [])
                st.success(f"Estimated {est} kgCO2")
                st.write("Detected:", det)
            except Exception as e:
                st.error("Photo analysis failed: " + str(e))

# -------------------------------
# History
# -------------------------------
with tab_history:
    st.header("History")
    try:
        rows = requests.get(f"{API_BASE}/entries", params={"token": token}, timeout=30).json()
    except Exception as e:
        st.error("Could not fetch history: " + str(e))
        rows = []
    if rows:
        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        # present in descending time order
        df = df.sort_values("timestamp", ascending=False)
        st.dataframe(df[["timestamp","category","emissions_kgco2","details"]].reset_index(drop=True))
    else:
        st.info("No entries yet")

# -------------------------------
# Goals
# -------------------------------
with tab_goals:
    st.header("Goals")
    with st.form("create_goal"):
        gtype = st.selectbox("Goal type", ["reduce_percent","absolute_target"])
        if gtype == "reduce_percent":
            pct = st.number_input("Target reduction (%)", min_value=1, max_value=100, value=20)
            start = st.date_input("Start date")
            end = st.date_input("End date")
            submitted = st.form_submit_button("Create goal")
            if submitted:
                params = {"target_percent": int(pct), "start": str(start), "end": str(end)}
                try:
                    r = post_form("/goals", form_data={"token": token, "type": "reduce_percent", "params": json.dumps(params)})
                    st.success("Goal created")
                except Exception as e:
                    st.error("Error creating goal: " + str(e))
        else:
            target = st.number_input("Target kgCO2 per week", min_value=0.0, value=50.0)
            start = st.date_input("Start date", key="gstart")
            end = st.date_input("End date", key="gend")
            submitted = st.form_submit_button("Create absolute goal")
            if submitted:
                params = {"target_kg_per_week": float(target), "start": str(start), "end": str(end)}
                try:
                    r = post_form("/goals", form_data={"token": token, "type": "absolute_target", "params": json.dumps(params)})
                    st.success("Goal created")
                except Exception as e:
                    st.error("Error creating goal: " + str(e))

# -------------------------------
# Leaderboard
# -------------------------------
with tab_leader:
    st.header("Leaderboard (Lowest last 7 days)")
    try:
        board = requests.get(f"{API_BASE}/leaderboard", timeout=30).json()
    except Exception as e:
        st.error("Could not fetch leaderboard: " + str(e))
        board = []
    if board:
        st.table(board)
    else:
        st.info("Leaderboard empty")

# -------------------------------
# AI Assistant
# -------------------------------
with tab_ai:
    st.header("AI Assistant")
    q = st.text_area("Ask the assistant (get suggestions, analysis, or a plan to reduce CO2)", height=150)
    if st.button("Ask AI"):
        if not q.strip():
            st.warning("Type a question")
        else:
            try:
                r = post_form("/gemini_client", form_data={"token": token, "prompt": q})
                res = r.json() if hasattr(r, "json") else {}
                st.write(res.get("response") or res)
            except Exception as e:
                st.error("AI query failed: " + str(e))
