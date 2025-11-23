# backend/models.py
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import uuid

def gen_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: gen_id("user"))
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    token = Column(String, nullable=True)  # simple token
    created_at = Column(DateTime, default=datetime.utcnow)

    entries = relationship("Entry", back_populates="user")
    photos = relationship("Photo", back_populates="user")
    goals = relationship("Goal", back_populates="user")

class Entry(Base):
    __tablename__ = "entries"
    id = Column(String, primary_key=True, default=lambda: gen_id("entry"))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    category = Column(String, nullable=False)  # transport, electricity, food, waste, purchase, photo-analysis
    details = Column(Text)  # JSON string
    emissions_kgco2 = Column(Float, default=0.0)

    user = relationship("User", back_populates="entries")

class Photo(Base):
    __tablename__ = "photos"
    id = Column(String, primary_key=True, default=lambda: gen_id("photo"))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    detected_json = Column(Text)  # JSON string of detections
    estimated_kgco2 = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="photos")

class Goal(Base):
    __tablename__ = "goals"
    id = Column(String, primary_key=True, default=lambda: gen_id("goal"))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)  # reduce_percent | absolute_target
    params = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="goals")
