from pydantic import BaseModel
from datetime import date
from typing import Optional


class NormalizedBill(BaseModel):
    bill_period_start: Optional[date] = None
    bill_period_end: Optional[date] = None
    kwh: Optional[float] = None
    total_cost: Optional[float] = None
    peak_kw: Optional[float] = None
    tariff_name: Optional[str] = None
    supplier: Optional[str] = None
    currency: str = "GBP"
    confidence: float = 0.0
    ocr_raw_json: dict = {}
    extraction_method: str = "pdfplumber"
