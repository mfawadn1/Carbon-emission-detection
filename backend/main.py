# backend/main.py
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import engine, Base
from . import models, crud, schemas, gemini_client, utils
import os, io, json
from .database import SessionLocal
from typing import List
import shutil, uuid

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Carbon Detection & Emission API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------
# Auth endpoints
# -----------------
@app.post("/signup", response_model=schemas.TokenOut)
def signup(payload: schemas.SignupIn, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(db, payload.first_name, payload.last_name, payload.email, payload.password)
    return {"token": user.token or "", "user_id": user.id, "first_name": user.first_name, "last_name": user.last_name, "email": user.email}

@app.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": user.token, "user_id": user.id, "first_name": user.first_name, "last_name": user.last_name, "email": user.email}

def require_user(token: str = Form(...), db: Session = Depends(get_db)):
    user = crud.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

# -----------------
# Entries
# -----------------
@app.post("/entries")
def add_entry(token: str = Form(...), category: str = Form(...), details: str = Form(...), db: Session = Depends(get_db)):
    """
    details: JSON string sent from client (Streamlit). Server will compute emissions if not provided.
    """
    user = crud.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        details_obj = json.loads(details)
    except:
        details_obj = {}
    emissions = float(details_obj.get("estimated_kgco2", 0.0) or 0.0)
    # compute if zero
    if emissions == 0.0:
        if category == "transport":
            emissions = utils.calc_transport_km(
                details_obj.get("vehicle_type"),
                float(details_obj.get("km", 0)),
                int(details_obj.get("passengers", 1)),
                details_obj.get("fuel_liters")
            )
        elif category == "electricity":
            emissions = utils.calc_electricity_kwh(details_obj.get("kwh", 0))
        elif category == "waste":
            emissions = utils.calc_waste(details_obj.get("kg", 0))
        else:
            emissions = float(details_obj.get("estimated_kgco2", 0) or 0.0)
    ent = crud.create_entry(db, user.id, category, details_obj, emissions)
    return {"entry_id": ent.id, "emissions_kgco2": round(emissions,4)}

@app.get("/entries")
def list_entries(token: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    rows = crud.get_entries_for_user(db, user.id)
    # convert details JSON string back
    out = []
    for r in rows:
        try:
            det = json.loads(r.details or "{}")
        except:
            det = {}
        out.append({
            "id": r.id,
            "timestamp": r.timestamp.isoformat(),
            "category": r.category,
            "details": det,
            "emissions_kgco2": r.emissions_kgco2
        })
    return out

# -----------------
# Photo upload & analysis
# -----------------
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/photos/upload")
def photos_upload(token: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = crud.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    contents = file.file.read()
    # save file
    fname = f"{uuid.uuid4().hex}_{file.filename}"
    dest = os.path.join(UPLOAD_DIR, fname)
    with open(dest, "wb") as f:
        f.write(contents)

    # call Gemini / Vision
    try:
        detections = gemini_client.call_gemini_vision(contents)
    except Exception as e:
        detections = [{"label":"unknown","confidence":0.0}]

    est_total, details = utils.estimate_from_photo_labels(detections)

    photo = crud.create_photo(db, user.id, dest, detections, est_total)
    # also create entry
    ent = crud.create_entry(db, user.id, "photo-analysis", {"file": fname, "detection_details": details}, est_total)
    return {"photo_id": photo.id, "estimated_kgco2": est_total, "detection_details": details}

# -----------------
# Leaderboard
# -----------------
@app.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    return crud.leaderboard_last_7_days(db)

# -----------------
# Goals
# -----------------
@app.post("/goals")
def create_goal(token: str = Form(...), type: str = Form(...), params: str = Form(...), db: Session = Depends(get_db)):
    user = crud.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        params_obj = json.loads(params)
    except:
        params_obj = {}
    g = crud.create_goal(db, user.id, type, params_obj)
    return {"goal_id": g.id}

@app.get("/goals")
def list_goals(token: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    rows = crud.get_goals_for_user(db, user.id)
    out = []
    for r in rows:
        try:
            p = json.loads(r.params or "{}")
        except:
            p = {}
        out.append({"id": r.id, "type": r.type, "params": p})
    return out

# -----------------
# Assistant endpoint (AI suggestions & prediction)
# -----------------
@app.post("/gemini_client")
def assistant_query(token: str = Form(...), prompt: str = Form(...), db: Session = Depends(get_db)):
    user = crud.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    # we can seed assistant with user's recent data summary
    entries = crud.get_entries_for_user(db, user.id)
    # build small context
    total_recent = sum((e.emissions_kgco2 or 0.0) for e in entries[:50])
    context = f"User {user.first_name} {user.last_name} has recent total emissions ~{round(total_recent,4)} kgCO2 across {len(entries)} entries."
    full_prompt = context + "\n\nUser prompt:\n" + prompt
    res = gemini_client.call_gemini_text(full_prompt)
    return {"response": res.get("content"), "raw": res.get("raw", {})}
