from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any, Dict
from datetime import datetime, date


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Projects ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    building_type: str
    location: str
    floor_area_m2: Optional[float] = None
    operating_pattern: Optional[str] = "9-5_weekdays"

class ProjectOut(ProjectCreate):
    id: int
    user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Bills ─────────────────────────────────────────────────────────────────────

class MonthlyBillCreate(BaseModel):
    year: int
    month: int
    kwh: float
    cost_gbp: float
    peak_demand_kw: Optional[float] = None
    tariff_name: Optional[str] = None

class MonthlyBillOut(MonthlyBillCreate):
    id: int
    project_id: int

    model_config = {"from_attributes": True}


# ── Uploads & raw bills ───────────────────────────────────────────────────────

class UploadOut(BaseModel):
    id: int
    project_id: int
    filename: str
    file_type: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillRawOut(BaseModel):
    id: int
    upload_id: int
    project_id: int
    bill_period_start: Optional[date] = None
    bill_period_end: Optional[date] = None
    kwh: Optional[float] = None
    total_cost: Optional[float] = None
    peak_kw: Optional[float] = None
    tariff_name: Optional[str] = None
    supplier: Optional[str] = None
    currency: str
    confidence: float
    extraction_method: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BillRawPatch(BaseModel):
    """Payload for user corrections to an extracted bill."""
    bill_period_start: Optional[date] = None
    bill_period_end: Optional[date] = None
    kwh: Optional[float] = None
    total_cost: Optional[float] = None
    peak_kw: Optional[float] = None
    tariff_name: Optional[str] = None
    supplier: Optional[str] = None
    status: Optional[str] = None  # approved | rejected


# ── Scenarios ─────────────────────────────────────────────────────────────────

class ScenarioParams(BaseModel):
    solar_kw: Optional[float] = None
    battery_kwh: Optional[float] = None

class ScenarioResultOut(BaseModel):
    id: int
    project_id: int
    scenario_type: str
    name: str
    capex_gbp: Optional[float] = None
    annual_savings_kwh: Optional[float] = None
    annual_savings_gbp: Optional[float] = None
    payback_years: Optional[float] = None
    npv_gbp: Optional[float] = None
    params: Optional[Dict[str, Any]] = None
    assumptions: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Project detail (includes nested data) ─────────────────────────────────────

class ProjectDetail(ProjectOut):
    monthly_bills: List[MonthlyBillOut] = []
    scenario_results: List[ScenarioResultOut] = []
