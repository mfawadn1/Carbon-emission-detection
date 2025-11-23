# backend/crud.py
from . import models, schemas
from .database import SessionLocal
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import uuid, json

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Auth
def create_user(db: Session, first_name, last_name, email, password):
    hashed = pwd_ctx.hash(password)
    user = models.User(first_name=first_name, last_name=last_name, email=email, password_hash=hashed)
    db.add(user); db.commit(); db.refresh(user)
    return user

def authenticate_user(db: Session, email, password):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return None
    if not pwd_ctx.verify(password, user.password_hash):
        return None
    # create a token
    token = uuid.uuid4().hex
    user.token = token
    db.add(user); db.commit(); db.refresh(user)
    return user

def get_user_by_token(db: Session, token):
    return db.query(models.User).filter(models.User.token == token).first()

def get_user_by_email(db: Session, email):
    return db.query(models.User).filter(models.User.email == email).first()

# Entries
def create_entry(db: Session, user_id, category, details, emissions):
    ent = models.Entry(user_id=user_id, category=category, details=json.dumps(details), emissions_kgco2=emissions)
    db.add(ent); db.commit(); db.refresh(ent)
    return ent

def get_entries_for_user(db: Session, user_id):
    return db.query(models.Entry).filter(models.Entry.user_id == user_id).order_by(models.Entry.timestamp.desc()).all()

# Photos
def create_photo(db: Session, user_id, filename, detected_json, est):
    p = models.Photo(user_id=user_id, filename=filename, detected_json=json.dumps(detected_json), estimated_kgco2=est)
    db.add(p); db.commit(); db.refresh(p)
    return p

def get_photos_for_user(db: Session, user_id):
    return db.query(models.Photo).filter(models.Photo.user_id == user_id).order_by(models.Photo.created_at.desc()).all()

# Leaderboard
def leaderboard_last_7_days(db: Session):
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=7)
    rows = db.query(models.Entry.user_id, models.User.first_name, models.User.last_name, models.User.email).join(models.User).distinct().all()
    # compute totals per user
    from collections import defaultdict
    totals = defaultdict(float)
    entries = db.query(models.Entry).filter(models.Entry.timestamp >= cutoff).all()
    for e in entries:
        totals[e.user_id] += (e.emissions_kgco2 or 0.0)
    result = []
    for uid, name, lname, email in rows:
        result.append({"user_id": uid, "name": f"{name} {lname}", "last7_kgco2": round(totals.get(uid, 0.0),4)})
    result.sort(key=lambda x: x["last7_kgco2"])
    return result

# Goals
def create_goal(db: Session, user_id, type_, params):
    import json
    g = models.Goal(user_id=user_id, type=type_, params=json.dumps(params))
    db.add(g); db.commit(); db.refresh(g)
    return g

def get_goals_for_user(db: Session, user_id):
    return db.query(models.Goal).filter(models.Goal.user_id == user_id).order_by(models.Goal.created_at.desc()).all()
