import os
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from supabase import create_client, Client

logger = logging.getLogger("database")

# Load .env if it exists
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                # Permit human-friendly inline comments in local .env files without
                # accidentally appending them to an API key.
                value = v.strip().split(" #", 1)[0].rstrip()
                os.environ.setdefault(k.strip(), value)

# Supabase Client Initialization
SUPABASE_URL = os.environ.get("VITE_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_KEY")
    or os.environ.get("SUPABASE_KEY")
    or os.environ.get("VITE_SUPABASE_PUBLISHABLE_KEY")
)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Supabase credentials missing. Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env "
        "(or SUPABASE_KEY for a legacy setup)."
    )

try:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase client initialized successfully.")
except Exception as e:
    raise RuntimeError(f"Failed to initialize Supabase client: {e}")

# --- We no longer use SQLite ---
# SQLAlchemy models are kept only for potential local testing, but we never instantiate them.
# They are not used when use_supabase() is True.

Base = declarative_base()

# --- SQLAlchemy Models (kept for reference, but not used in production) ---
class Spec(Base):
    __tablename__ = "specs"
    id = Column(String, primary_key=True, index=True)
    property_type = Column(String, nullable=False)
    property_sqft = Column(Integer, nullable=False)
    property_bedrooms = Column(Integer, nullable=False)
    property_bathrooms = Column(Float, nullable=False)
    property_levels = Column(Integer, default=1)
    clean_type = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    clutter_level = Column(String, nullable=False)
    has_pets = Column(Boolean, nullable=False)
    weeks_since_last_clean = Column(Integer, nullable=False)
    add_on_fridge = Column(Boolean, default=False)
    add_on_oven = Column(Boolean, default=False)
    add_on_windows = Column(Boolean, default=False)
    add_on_baseboards = Column(Boolean, default=False)
    add_on_laundry = Column(Boolean, default=False)
    access_parking = Column(String, nullable=False)
    access_entry_method = Column(String, nullable=False)
    access_walk_up_floor = Column(Integer, default=0)
    schedule_preferred_date = Column(String, nullable=False)
    schedule_preferred_time_window = Column(String, nullable=False)
    schedule_flexibility = Column(String, nullable=True)
    open_questions = Column(JSON, default=list)
    confirmed_by_user = Column(Boolean, default=False)
    intake_source = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    calls = relationship("Call", back_populates="spec", cascade="all, delete-orphan")
    quotes = relationship("Quote", back_populates="spec", cascade="all, delete-orphan")

class Company(Base):
    __tablename__ = "companies"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    persona = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    calls = relationship("Call", back_populates="company")
    quotes = relationship("Quote", back_populates="company")

class Call(Base):
    __tablename__ = "calls"
    id = Column(String, primary_key=True, index=True)
    spec_id = Column(String, ForeignKey("specs.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    status = Column(String, default="queued")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    spec = relationship("Spec", back_populates="calls")
    company = relationship("Company", back_populates="calls")
    quotes = relationship("Quote", back_populates="call", cascade="all, delete-orphan")

class Quote(Base):
    __tablename__ = "quotes"
    id = Column(String, primary_key=True, index=True)
    call_id = Column(String, ForeignKey("calls.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    spec_id = Column(String, ForeignKey("specs.id"), nullable=False)
    outcome = Column(String, nullable=False)
    pricing_model = Column(String, nullable=True)
    opening_total = Column(Float, nullable=True)
    final_total = Column(Float, nullable=True)
    total = Column(Float, nullable=True)
    moved_because = Column(String, nullable=True)
    conditions = Column(JSON, default=list)
    red_flags = Column(JSON, default=list)
    red_flag_reasons = Column(JSON, default=list)
    callback_contact = Column(String, nullable=True)
    callback_window = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    transcript_url = Column(String, nullable=True)
    recording_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    call = relationship("Call", back_populates="quotes")
    company = relationship("Company", back_populates="quotes")
    spec = relationship("Spec", back_populates="quotes")
    line_items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan")

class QuoteItem(Base):
    __tablename__ = "quote_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    quote_id = Column(String, ForeignKey("quotes.id"), nullable=False)
    call_id = Column(String, nullable=True)
    label = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    disclosed_voluntarily = Column(Boolean, default=True)
    negotiable = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    quote = relationship("Quote", back_populates="line_items")


# --- Force Supabase only ---
def use_supabase() -> bool:
    """
    Returns True if Supabase client is available.
    Raises RuntimeError if not – we do NOT fall back to SQLite.
    """
    if supabase_client is None:
        raise RuntimeError("Supabase client is not initialized. Check your credentials.")
    return True


# --- Serialization Helpers (unchanged) ---
def to_flat_spec(spec_id: str, data: dict) -> dict:
    prop = data.get("property", {}) or {}
    cond = data.get("condition", {}) or {}
    addons = data.get("add_ons", {}) or {}
    acc = data.get("access", {}) or {}
    sched = data.get("schedule", {}) or {}
    return {
        "id": spec_id,
        "property_type": prop.get("type", "apartment"),
        "property_sqft": prop.get("sqft", 0),
        "property_bedrooms": prop.get("bedrooms", 0),
        "property_bathrooms": prop.get("bathrooms", 0.0),
        "property_levels": prop.get("levels", 1),
        "clean_type": data.get("clean_type", "standard"),
        "frequency": data.get("frequency", "one_time"),
        "clutter_level": cond.get("clutter_level", "medium"),
        "has_pets": cond.get("has_pets", False),
        "weeks_since_last_clean": cond.get("weeks_since_last_clean", 0),
        "add_on_fridge": addons.get("fridge", False),
        "add_on_oven": addons.get("oven", False),
        "add_on_windows": addons.get("windows", False),
        "add_on_baseboards": addons.get("baseboards", False),
        "add_on_laundry": addons.get("laundry", False),
        "access_parking": acc.get("parking", "street"),
        "access_entry_method": acc.get("entry_method", ""),
        "access_walk_up_floor": acc.get("walk_up_floor", 0),
        "schedule_preferred_date": sched.get("preferred_date", ""),
        "schedule_preferred_time_window": sched.get("preferred_time_window", ""),
        "schedule_flexibility": sched.get("flexibility"),
        "open_questions": data.get("open_questions", []),
        "confirmed_by_user": data.get("confirmed_by_user", False),
        "intake_source": data.get("intake_source", "voice_interview"),
        "created_at": datetime.utcnow().isoformat()   # explicitly set
    }

def from_flat_spec(flat: dict) -> dict:
    return {
        "id": flat["id"],
        "property": {
            "type": flat["property_type"],
            "sqft": flat["property_sqft"],
            "bedrooms": flat["property_bedrooms"],
            "bathrooms": flat["property_bathrooms"],
            "levels": flat["property_levels"]
        },
        "clean_type": flat["clean_type"],
        "frequency": flat["frequency"],
        "condition": {
            "clutter_level": flat["clutter_level"],
            "has_pets": flat["has_pets"],
            "weeks_since_last_clean": flat["weeks_since_last_clean"]
        },
        "add_ons": {
            "fridge": flat["add_on_fridge"],
            "oven": flat["add_on_oven"],
            "windows": flat["add_on_windows"],
            "baseboards": flat["add_on_baseboards"],
            "laundry": flat["add_on_laundry"]
        },
        "access": {
            "parking": flat["access_parking"],
            "entry_method": flat["access_entry_method"],
            "walk_up_floor": flat["access_walk_up_floor"]
        },
        "schedule": {
            "preferred_date": flat["schedule_preferred_date"],
            "preferred_time_window": flat["schedule_preferred_time_window"],
            "flexibility": flat["schedule_flexibility"]
        },
        "open_questions": flat["open_questions"] or [],
        "confirmed_by_user": flat["confirmed_by_user"],
        "intake_source": flat["intake_source"],
        "created_at": flat.get("created_at")
    }

def to_spec_db(spec_id: str, data: dict) -> Spec:
    flat = to_flat_spec(spec_id, data)
    # delete id so it is set on constructor explicitly
    del flat["id"]
    return Spec(id=spec_id, **flat)

def from_spec_db(spec: Spec) -> dict:
    return from_flat_spec(spec.__dict__)


# --- Unified Wrapper Interface (Supabase's live JSON-spec schema) ---

def _spec_from_row(row: dict) -> dict:
    spec = dict(row.get("spec") or {})
    spec.update({
        "id": str(row["id"]),
        "confirmed_by_user": row.get("confirmed_by_user", False),
        "intake_source": row.get("intake_source") or spec.get("intake_source") or "voice_interview",
        "open_questions": spec.get("open_questions") or row.get("missing_fields") or [],
        "created_at": row.get("created_at"),
    })
    return spec

def db_create_spec(data: dict) -> dict:
    spec_id = str(uuid.uuid4())
    spec = dict(data)
    spec["confirmed_by_user"] = False
    row = {
        "id": spec_id,
        "spec": spec,
        "clean_type": spec.get("clean_type"),
        "intake_source": spec.get("intake_source", "voice_interview"),
        "confirmed_by_user": False,
        "missing_fields": spec.get("open_questions") or [],
    }
    supabase_client.table("specs").insert(row).execute()
    return _spec_from_row(row)

def db_get_spec(spec_id: str) -> Optional[dict]:
    resp = supabase_client.table("specs").select("*").eq("id", spec_id).execute()
    return _spec_from_row(resp.data[0]) if resp.data else None

def db_update_spec(spec_id: str, data: dict) -> Optional[dict]:
    if not db_get_spec(spec_id):
        return None
    spec = dict(data)
    spec["confirmed_by_user"] = False
    supabase_client.table("specs").update({
        "spec": spec,
        "clean_type": spec.get("clean_type"),
        "intake_source": spec.get("intake_source", "voice_interview"),
        "missing_fields": spec.get("open_questions") or [],
    }).eq("id", spec_id).execute()
    return db_get_spec(spec_id)

def db_confirm_spec(spec_id: str) -> dict:
    spec = db_get_spec(spec_id)
    if not spec:
        raise Exception("Spec not found")
    spec["confirmed_by_user"] = True
    supabase_client.table("specs").update({"confirmed_by_user": True, "spec": spec}).eq("id", spec_id).execute()
    for company in supabase_client.table("companies").select("*").execute().data:
        existing = supabase_client.table("calls").select("id").eq("spec_id", spec_id).eq("company_id", company["id"]).execute()
        if not existing.data:
            supabase_client.table("calls").insert({"id": str(uuid.uuid4()), "spec_id": spec_id, "company_id": company["id"], "status": "queued"}).execute()
    return db_get_spec(spec_id)

def db_start_call(spec_id: str, company_id: str) -> dict:
    response = supabase_client.table("calls").select("*").eq("spec_id", spec_id).eq("company_id", company_id).execute()
    if response.data:
        call = response.data[0]
        call_id = call["id"]
        supabase_client.table("calls").update({"status": "calling", "updated_at": datetime.utcnow().isoformat()}).eq("id", call_id).execute()
    else:
        call_id = str(uuid.uuid4())
        supabase_client.table("calls").insert({"id": call_id, "spec_id": spec_id, "company_id": company_id, "status": "calling"}).execute()
    company = supabase_client.table("companies").select("name").eq("id", company_id).execute().data
    return {"call_id": call_id, "spec_id": spec_id, "company_id": company_id, "company_name": company[0]["name"] if company else "Unknown", "status": "calling"}

def db_get_calls(spec_id: str) -> List[Dict[str, Any]]:
    calls = supabase_client.table("calls").select("*").eq("spec_id", spec_id).execute().data
    companies = {row["id"]: row for row in supabase_client.table("companies").select("*").execute().data}
    results: List[Dict[str, Any]] = []
    for call in calls:
        company = companies.get(call["company_id"], {"name": "Unknown", "persona": "Unknown"})
        quote_rows = supabase_client.table("quotes").select("*").eq("call_id", call["id"]).execute().data
        quote_data = None
        if quote_rows:
            quote = quote_rows[0]
            items = supabase_client.table("quote_items").select("*").eq("call_id", call["id"]).execute().data
            line_items = [{"label": item["label"], "amount": float(item["amount"])} for item in items]
            total = quote.get("final_total") or sum(item["amount"] for item in line_items)
            quote_data = {
                "id": quote["id"], "outcome": quote["outcome"], "pricing_model": quote.get("pricing_model"),
                "total": float(total) if total is not None else None, "opening_total": quote.get("initial_total"),
                "final_total": quote.get("final_total"), "conditions": quote.get("conditions") or [],
                "red_flags": quote.get("red_flags") or [], "red_flag_reasons": [], "notes": quote.get("notes"),
                "transcript_url": call.get("transcript_url"), "recording_url": call.get("recording_url"), "line_items": line_items,
            }
        results.append({"call_id": call["id"], "company_id": call["company_id"], "company_name": company["name"], "persona": company.get("persona", "Unknown"), "status": call["status"], "quote": quote_data, "updated_at": call.get("updated_at")})
    return results

def _quote_for_call(call: dict) -> dict:
    response = supabase_client.table("quotes").select("*").eq("call_id", call["id"]).execute()
    if response.data:
        return response.data[0]
    quote = {"id": str(uuid.uuid4()), "call_id": call["id"], "company_id": call["company_id"], "spec_id": call["spec_id"], "outcome": "quote", "pricing_model": "flat", "initial_total": 0, "final_total": 0, "conditions": [], "red_flags": []}
    supabase_client.table("quotes").insert(quote).execute()
    return quote

def db_log_quote_item(call_id: str, label: str, amount: float, disclosed_voluntarily: bool, negotiable: bool) -> dict:
    response = supabase_client.table("calls").select("*").eq("id", call_id).execute()
    if not response.data:
        raise Exception(f"Call session {call_id} not found")
    call = response.data[0]
    if call["status"] == "queued":
        supabase_client.table("calls").update({"status": "calling"}).eq("id", call_id).execute()
    quote = _quote_for_call(call)
    supabase_client.table("quote_items").insert({"id": str(uuid.uuid4()), "call_id": call_id, "label": label, "amount": amount, "disclosed_voluntarily": disclosed_voluntarily, "negotiable": negotiable}).execute()
    items = supabase_client.table("quote_items").select("amount").eq("call_id", call_id).execute().data
    total = sum(float(item["amount"]) for item in items)
    update = {"final_total": total}
    if not quote.get("initial_total"):
        update["initial_total"] = total
    supabase_client.table("quotes").update(update).eq("id", quote["id"]).execute()
    return {"success": True, "current_quote_total": total}

def db_get_best_bid(spec_id: str, exclude_company: str = None) -> dict:
    quotes = supabase_client.table("quotes").select("*").eq("spec_id", spec_id).eq("outcome", "quote").execute().data
    companies = {row["id"]: row["name"] for row in supabase_client.table("companies").select("id,name").execute().data}
    eligible = [(float(quote["final_total"]), companies.get(quote["company_id"], "")) for quote in quotes if quote.get("final_total") and (not exclude_company or exclude_company.lower() not in companies.get(quote["company_id"], "").lower())]
    if not eligible:
        return {"best_bid": None, "company_name": None}
    best_bid, company_name = min(eligible, key=lambda item: item[0])
    return {"best_bid": best_bid, "company_name": company_name}

def db_log_outcome(call_id: str, data: dict, run_red_flags_fn) -> dict:
    response = supabase_client.table("calls").select("*").eq("id", call_id).execute()
    if not response.data:
        raise Exception(f"Call session {call_id} not found")
    call = response.data[0]
    quote = _quote_for_call(call)
    final_total = data.get("final_total") if data.get("final_total") is not None else data.get("total")
    update = {"outcome": data["outcome"], "pricing_model": data.get("pricing_model") or "flat", "conditions": data.get("conditions") or [], "notes": data.get("notes"), "callback_contact": data.get("callback_contact"), "callback_window": data.get("callback_window")}
    if final_total is not None:
        update["final_total"] = final_total
    if data.get("opening_total") is not None:
        update["initial_total"] = data["opening_total"]
    elif not quote.get("initial_total") and final_total is not None:
        update["initial_total"] = final_total
    supabase_client.table("quotes").update(update).eq("id", quote["id"]).execute()
    spec = db_get_spec(call["spec_id"])
    items = supabase_client.table("quote_items").select("*").eq("call_id", call_id).execute().data
    line_items = [{"label": item["label"], "amount": float(item["amount"])} for item in items]
    quote_for_rules = {"total": update.get("final_total", quote.get("final_total")), "final_total": update.get("final_total", quote.get("final_total")), "opening_total": update.get("initial_total", quote.get("initial_total")), "outcome": update["outcome"], "pricing_model": update["pricing_model"], "conditions": update["conditions"], "notes": update["notes"] or ""}
    red_flags, red_flag_reasons = run_red_flags_fn(spec or {}, quote_for_rules, line_items)
    supabase_client.table("quotes").update({"red_flags": red_flags}).eq("id", quote["id"]).execute()
    call_update = {"status": "declined" if data["outcome"] == "declined" else "done", "updated_at": datetime.utcnow().isoformat()}
    if data.get("transcript_url"):
        call_update["transcript_url"] = data["transcript_url"]
    if data.get("recording_url"):
        call_update["recording_url"] = data["recording_url"]
    supabase_client.table("calls").update(call_update).eq("id", call_id).execute()
    return {"success": True, "quote_id": quote["id"], "red_flags": red_flags, "red_flag_reasons": red_flag_reasons}

def init_db():
    """Ensure the three role-play companies exist; compatible with UUID primary keys."""
    response = supabase_client.table("companies").select("id").limit(1).execute()
    if not response.data:
        supabase_client.table("companies").insert([
            {"name": "Apex Cleaning Co", "persona": "Premium"},
            {"name": "Budget Cleaners", "persona": "Lowballer"},
            {"name": "Sparkle & Shine", "persona": "Upseller"},
        ]).execute()

# Call init_db when the module is loaded (optional)
# We'll call it explicitly from main.py on startup.
