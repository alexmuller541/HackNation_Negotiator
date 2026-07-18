"""
intake_router.py — Aleks's intake backend for The Negotiator (cleaning vertical).

Two endpoints, written so Umra can drop them straight into the main FastAPI app:

    POST /intake/doc   PDF or photo  -> Claude Vision -> DRAFT job_spec JSON,
                       validated against the JobSpec model below, with every
                       still-missing required field flagged. Does NOT persist.

    POST /specs        A job_spec JSON (from the doc route OR the voice
                       Interviewer transcript) -> persisted to Supabase ->
                       returns the spec_id. This is the SINGLE write-path for
                       all intake (both paths produce the identical shape).

Plug-in (in Umra's app):

    from intake_router import router as intake_router
    app.include_router(intake_router)

Environment variables (read lazily, so the module still imports without them):
    ANTHROPIC_API_KEY      - Claude API key (vision extraction)
    SUPABASE_URL           - e.g. https://xxxx.supabase.co
    SUPABASE_SERVICE_KEY   - service-role key (server-side writes)
    INTAKE_MODEL           - optional, defaults to claude-opus-4-8

Expected Supabase table (Umra owns the DB; create this to match the writes):

    create table specs (
        id                uuid primary key,
        spec              jsonb not null,      -- the full JobSpec
        clean_type        text,               -- denormalised for the report
        intake_source     text,               -- document | voice_interview | both
        confirmed_by_user boolean default false,
        missing_fields    text[] default '{}',
        created_at        timestamptz default now()
    );

The confirm gate (PATCH /specs/{id}/confirm) is Umra's — this file never
confirms a spec; it only drafts and persists.

Dependencies: fastapi, anthropic, supabase, pydantic  (all pip-installable).
"""
from __future__ import annotations

import base64
import os
import uuid
from enum import Enum
from typing import List, Optional

import anthropic
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field, ValidationError
from supabase import Client, create_client

router = APIRouter(tags=["intake"])

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
INTAKE_MODEL = os.environ.get("INTAKE_MODEL", "claude-opus-4-8")
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB raw (Anthropic caps the request at 32 MB after base64)
_IMAGE_MEDIA_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_PDF_MEDIA_TYPE = "application/pdf"
_EXT_TO_MEDIA = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "pdf": _PDF_MEDIA_TYPE,
}

# Fields a cleaning company needs before it can give a real (not bait) quote.
# Any of these left null in a draft is surfaced to the user for confirmation.
REQUIRED_FIELDS: List[tuple[str, str]] = [
    ("property.type", "property type"),
    ("property.sqft", "square footage"),
    ("property.bedrooms", "bedrooms"),
    ("property.bathrooms", "bathrooms"),
    ("clean_type", "clean type"),
    ("frequency", "frequency"),
    ("schedule.preferred_date", "preferred date"),
]


# --------------------------------------------------------------------------- #
# Job-spec models (cleaning vertical — mirrors verticals/cleaning.yaml spec_fields)
#
# NOTE: the schemas currently in schemas/*.json are the OLD moving vertical.
# These models are the cleaning-vertical contract for the v4 plan; Umra's
# `specs.spec` jsonb column stores exactly this shape from both intake paths.
# --------------------------------------------------------------------------- #
class PropertyType(str, Enum):
    apartment = "apartment"
    house = "house"
    condo = "condo"
    townhouse = "townhouse"
    other = "other"


class CleanType(str, Enum):
    standard = "standard"
    deep = "deep"
    move_out = "move_out"


class Frequency(str, Enum):
    one_time = "one_time"
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"


class ClutterLevel(str, Enum):
    light = "light"
    moderate = "moderate"
    heavy = "heavy"


class IntakeSource(str, Enum):
    document = "document"
    voice_interview = "voice_interview"
    both = "both"


class Property(BaseModel):
    type: Optional[PropertyType] = Field(None, description="Dwelling type. null if not stated.")
    sqft: Optional[int] = Field(None, description="Approximate interior square footage. null if not stated — never guess.")
    bedrooms: Optional[float] = Field(None, description="Number of bedrooms (0.5 for a den/half). null if unknown.")
    bathrooms: Optional[float] = Field(None, description="Number of bathrooms (0.5 for a half-bath). null if unknown.")
    levels: Optional[int] = Field(None, description="Number of floors/levels in the unit. null if unknown.")


class Condition(BaseModel):
    clutter_level: Optional[ClutterLevel] = Field(None, description="How cluttered the space is. null if not indicated.")
    pets: Optional[bool] = Field(None, description="Whether pets live in the home. null if not indicated.")
    weeks_since_last_clean: Optional[int] = Field(None, description="Weeks since the last professional clean. null if unknown.")


class AddOns(BaseModel):
    fridge: bool = Field(False, description="Clean inside the refrigerator.")
    oven: bool = Field(False, description="Clean inside the oven.")
    windows: bool = Field(False, description="Interior window cleaning.")
    baseboards: bool = Field(False, description="Wipe down baseboards.")
    laundry: bool = Field(False, description="Wash / fold laundry.")


class Access(BaseModel):
    parking: Optional[str] = Field(None, description="Parking situation for the cleaners. null if not stated.")
    entry: Optional[str] = Field(None, description="How the cleaner gets in (lockbox, doorman, meet on site...). null if not stated.")
    walk_up_floor: Optional[int] = Field(None, description="Floor number if it is a walk-up (no elevator). null if not applicable/unknown.")


class Schedule(BaseModel):
    preferred_date: Optional[str] = Field(None, description="Preferred service date (YYYY-MM-DD if given). null if not stated.")
    flexibility_days: Optional[int] = Field(None, description="How many days the date can flex. null if unknown.")
    time_window: Optional[str] = Field(None, description="Preferred time of day / window. null if not stated.")


class JobSpec(BaseModel):
    """The cleaning job spec — produced identically by document intake and the
    voice interview, confirmed by the user, then reused verbatim on every call."""
    property: Property = Field(default_factory=Property)
    clean_type: Optional[CleanType] = Field(None, description="Type of clean requested. null if not stated.")
    frequency: Optional[Frequency] = Field(None, description="One-time vs recurring cadence. null if not stated.")
    condition: Condition = Field(default_factory=Condition)
    add_ons: AddOns = Field(default_factory=AddOns)
    access: Access = Field(default_factory=Access)
    schedule: Schedule = Field(default_factory=Schedule)
    notes: Optional[str] = Field(None, description="Anything else relevant the user mentioned.")
    confirmed_by_user: bool = Field(False, description="True only after the user confirms the spec (set by the confirm gate, not here).")
    intake_source: Optional[IntakeSource] = None


class DraftSpecResponse(BaseModel):
    job_spec: JobSpec
    missing_fields: List[str]
    intake_source: IntakeSource = IntakeSource.document


class SaveSpecResponse(BaseModel):
    spec_id: str
    missing_fields: List[str]
    confirmed_by_user: bool


# --------------------------------------------------------------------------- #
# Lazy clients (so importing this module never requires credentials)
# --------------------------------------------------------------------------- #
_anthropic_client: Optional[anthropic.Anthropic] = None
_supabase_client: Optional[Client] = None


def _anthropic() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "ANTHROPIC_API_KEY is not set")
        _anthropic_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    return _anthropic_client


def _supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "SUPABASE_URL / SUPABASE_SERVICE_KEY not set")
        _supabase_client = create_client(url, key)
    return _supabase_client


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _missing_fields(spec: JobSpec) -> List[str]:
    """Return the human-readable labels of required fields still null/empty."""
    data = spec.model_dump()
    missing: List[str] = []
    for path, label in REQUIRED_FIELDS:
        cur = data
        for part in path.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is None or cur == "":
            missing.append(label)
    return missing


def _resolve_media_type(upload: UploadFile) -> str:
    ct = (upload.content_type or "").lower().split(";")[0].strip()
    if ct in _IMAGE_MEDIA_TYPES or ct == _PDF_MEDIA_TYPE:
        return ct
    ext = (upload.filename or "").rsplit(".", 1)[-1].lower()
    if ext in _EXT_TO_MEDIA:
        return _EXT_TO_MEDIA[ext]
    raise HTTPException(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Unsupported file type '{upload.content_type or ext}'. Send a PDF or an image (jpeg/png/gif/webp).",
    )


# Forced tool: guarantees Claude returns structured data matching JobSpec.
_EXTRACT_TOOL = {
    "name": "record_cleaning_spec",
    "description": "Record the cleaning job specification extracted from the document or photo.",
    "input_schema": JobSpec.model_json_schema(),
}

_EXTRACT_SYSTEM = (
    "You extract a home-cleaning job specification from an uploaded document "
    "(an existing cleaning quote/invoice) or a photo of a space. Fill only what "
    "the source actually supports. Set any field you cannot determine to null — "
    "never invent square footage, dates, prices, or room counts. For a photo, "
    "estimate visible attributes (approximate room type, clutter level) and leave "
    "everything not visible as null. Call record_cleaning_spec exactly once."
)


def _extract_spec_from_file(raw: bytes, media_type: str) -> JobSpec:
    b64 = base64.standard_b64encode(raw).decode("utf-8")
    if media_type == _PDF_MEDIA_TYPE:
        media_block = {"type": "document", "source": {"type": "base64", "media_type": _PDF_MEDIA_TYPE, "data": b64}}
    else:
        media_block = {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}}

    try:
        resp = _anthropic().messages.create(
            model=INTAKE_MODEL,
            max_tokens=2000,
            system=_EXTRACT_SYSTEM,
            tools=[_EXTRACT_TOOL],
            tool_choice={"type": "tool", "name": "record_cleaning_spec"},
            messages=[{
                "role": "user",
                "content": [
                    media_block,
                    {"type": "text", "text": "Extract the cleaning job spec from this file."},
                ],
            }],
        )
    except anthropic.APIError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Vision extraction failed: {e}")

    tool_input = next((b.input for b in resp.content if b.type == "tool_use"), None)
    if tool_input is None:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Vision model did not return a structured spec.")

    try:
        spec = JobSpec.model_validate(tool_input)
    except ValidationError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Vision output failed validation: {e.errors()}")

    spec.intake_source = IntakeSource.document
    spec.confirmed_by_user = False
    return spec


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@router.post("/intake/doc", response_model=DraftSpecResponse)
async def intake_doc(file: UploadFile = File(...)) -> DraftSpecResponse:
    """Accept a PDF or photo, extract a DRAFT cleaning spec via Claude Vision,
    and flag missing required fields. Does not persist — the caller reviews the
    draft, then POSTs the (edited) spec to /specs to get a spec_id."""
    media_type = _resolve_media_type(file)
    raw = await file.read()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 20 MB.")

    spec = _extract_spec_from_file(raw, media_type)
    return DraftSpecResponse(
        job_spec=spec,
        missing_fields=_missing_fields(spec),
        intake_source=IntakeSource.document,
    )


@router.post("/specs", response_model=SaveSpecResponse)
async def save_spec(spec: JobSpec) -> SaveSpecResponse:
    """Persist a job spec (from the doc route or the voice interview) and return
    its spec_id. Single write-path for all intake. Confirmation happens later
    via Umra's PATCH /specs/{id}/confirm."""
    missing = _missing_fields(spec)
    spec_id = str(uuid.uuid4())
    row = {
        "id": spec_id,
        "spec": spec.model_dump(mode="json"),
        "clean_type": spec.clean_type.value if spec.clean_type else None,
        "intake_source": spec.intake_source.value if spec.intake_source else None,
        "confirmed_by_user": spec.confirmed_by_user,
        "missing_fields": missing,
    }
    try:
        resp = _supabase().table("specs").insert(row).execute()
    except HTTPException:
        raise
    except Exception as e:  # supabase-py raises its own error types
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to persist spec: {e}")

    saved_id = spec_id
    if getattr(resp, "data", None):
        saved_id = resp.data[0].get("id", spec_id)
    return SaveSpecResponse(spec_id=saved_id, missing_fields=missing, confirmed_by_user=spec.confirmed_by_user)
