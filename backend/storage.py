# backend/storage.py
import json
from pathlib import Path
from threading import Lock

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)
lock = Lock()

def _path(name):
    return DATA_DIR / name

def _read(name):
    p = _path(name)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def _write(name, obj):
    p = _path(name)
    with lock:
        with p.open("w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

def read_users(): return _read("users.json")
def write_users(v): return _write("users.json", v)

def read_entries(): return _read("entries.json")
def write_entries(v): return _write("entries.json", v)

def read_photos(): return _read("photos.json")
def write_photos(v): return _write("photos.json", v)

def read_goals(): return _read("goals.json")
def write_goals(v): return _write("goals.json", v)
