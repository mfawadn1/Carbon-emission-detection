# backend/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, Any, Dict

class SignupIn(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    token: str
    user_id: str
    first_name: str
    last_name: str
    email: EmailStr

class EntryIn(BaseModel):
    category: str
    details: Optional[Dict[str, Any]] = {}
    # emissions can be computed server-side; optional override
    emissions_kgco2: Optional[float] = None

class GoalIn(BaseModel):
    type: str
    params: Dict[str, Any]
