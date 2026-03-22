"""
Bill extraction logic.
  - Default: pdfplumber text extraction + regex field parsing
  - Optional: Mindee API (set MINDEE_API_KEY)
"""
import io
import re
from datetime import date
from typing import Optional

import pdfplumber
from dateutil import parser as dateparser

from .schemas import NormalizedBill


# ── Regex patterns for UK utility bills ───────────────────────────────────────

KWH_PATTERNS = [
    r"(\d[\d,]+\.?\d*)\s*kWh",
    r"[Ee]lectricity\s+used[:\s]+(\d[\d,]+\.?\d*)",
    r"[Tt]otal\s+units?[:\s]+(\d[\d,]+\.?\d*)",
    r"[Cc]onsumption[:\s]+(\d[\d,]+\.?\d*)\s*kWh",
    r"[Uu]nits?\s+used[:\s]+(\d[\d,]+\.?\d*)",
]

COST_PATTERNS = [
    r"[Tt]otal\s+(?:amount\s+)?(?:due|payable|charged)[^£\d]*£?\s*([\d,]+\.?\d*)",
    r"[Aa]mount\s+(?:due|payable)[^£\d]*£?\s*([\d,]+\.?\d*)",
    r"[Tt]otal\s+bill[^£\d]*£?\s*([\d,]+\.?\d*)",
    r"[Bb]alance\s+(?:due|owing)[^£\d]*£?\s*([\d,]+\.?\d*)",
    r"[Tt]otal\s+charges?[^£\d]*£?\s*([\d,]+\.?\d*)",
    r"£\s*([\d,]+\.\d{2})",  # any £X.XX as fallback
]

PERIOD_PATTERNS = [
    # "from 01/01/2024 to 31/01/2024" or "01/01/2024 – 31/01/2024"
    r"(?:[Ff]rom\s+|[Bb]illing\s+[Pp]eriod[:\s]+)?(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})"
    r"\s*(?:to|–|-|through)\s*"
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    # "1 January 2024 to 31 January 2024"
    r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})"
    r"\s*(?:to|–|-)\s*"
    r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})",
]

PEAK_PATTERNS = [
    r"[Mm]aximum\s+[Dd]emand[:\s]+(\d[\d.]*)\s*kW",
    r"\bMD[:\s]+(\d[\d.]*)\s*kV?A?",
    r"[Pp]eak\s+[Dd]emand[:\s]+(\d[\d.]*)\s*kW",
    r"(\d[\d.]*)\s*kVA\b",
]

SUPPLIER_KEYWORDS = [
    "British Gas", "EDF Energy", "EDF", "E.ON", "EON", "Octopus Energy",
    "Octopus", "Scottish Power", "ScottishPower", "SSE", "npower", "Npower",
    "Shell Energy", "OVO Energy", "OVO", "Good Energy", "Ecotricity",
    "TotalEnergies", "Total Energies", "Utilita", "Bulb",
]


def _parse_float(s: str) -> Optional[float]:
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _parse_date(s: str) -> Optional[date]:
    try:
        return dateparser.parse(s, dayfirst=True).date()
    except Exception:
        return None


def _find_first(patterns: list[str], text: str) -> Optional[re.Match]:
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return m
    return None


# ── pdfplumber extractor ───────────────────────────────────────────────────────

def extract_with_pdfplumber(file_bytes: bytes, filename: str) -> NormalizedBill:
    """Extract bill fields from PDF text using regex heuristics."""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages_text)
    except Exception as e:
        return NormalizedBill(
            ocr_raw_json={"error": str(e), "filename": filename},
            extraction_method="pdfplumber",
        )

    raw = {"filename": filename, "page_count": len(pages_text), "text_snippet": text[:500]}
    hits = 0
    possible = 5  # kwh, cost, period_start, period_end, supplier

    # kWh
    kwh = None
    m = _find_first(KWH_PATTERNS, text)
    if m:
        kwh = _parse_float(m.group(1))
        if kwh:
            hits += 1

    # Total cost
    total_cost = None
    m = _find_first(COST_PATTERNS, text)
    if m:
        total_cost = _parse_float(m.group(1))
        if total_cost:
            hits += 1

    # Billing period
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    for pattern in PERIOD_PATTERNS:
        m = re.search(pattern, text)
        if m:
            period_start = _parse_date(m.group(1))
            period_end = _parse_date(m.group(2))
            if period_start:
                hits += 1
            if period_end:
                hits += 1
            break

    # Peak demand
    peak_kw = None
    m = _find_first(PEAK_PATTERNS, text)
    if m:
        peak_kw = _parse_float(m.group(1))

    # Supplier
    supplier = None
    for kw in SUPPLIER_KEYWORDS:
        if kw.lower() in text.lower():
            supplier = kw
            hits += 1
            break

    # Tariff: look for "tariff" keyword nearby
    tariff_name = None
    m = re.search(r"[Tt]ariff[:\s]+([A-Za-z0-9 \-]+)", text)
    if m:
        tariff_name = m.group(1).strip()[:60]

    confidence = round(hits / possible, 2)

    return NormalizedBill(
        bill_period_start=period_start,
        bill_period_end=period_end,
        kwh=kwh,
        total_cost=total_cost,
        peak_kw=peak_kw,
        tariff_name=tariff_name,
        supplier=supplier,
        currency="GBP",
        confidence=confidence,
        ocr_raw_json=raw,
        extraction_method="pdfplumber",
    )


# ── Mindee extractor (optional) ───────────────────────────────────────────────

def extract_with_mindee(file_bytes: bytes, filename: str, api_key: str) -> NormalizedBill:
    """
    Use Mindee's invoice API to parse the bill, then map to NormalizedBill.
    Falls back to pdfplumber on any error.
    """
    try:
        from mindee import Client, product

        client = Client(api_key=api_key)
        input_doc = client.source_from_bytes(file_bytes, filename)
        result = client.parse(product.InvoiceV4, input_doc)
        pred = result.document.inference.prediction

        raw = result.document.inference.prediction.__dict__

        # Map Mindee invoice fields to our schema
        kwh = None
        total_cost = None
        period_start = None
        period_end = None
        supplier = None
        tariff_name = None

        # Total amount
        if pred.total_amount and pred.total_amount.value:
            total_cost = float(pred.total_amount.value)

        # Supplier name from invoice
        if pred.supplier_name and pred.supplier_name.value:
            supplier = pred.supplier_name.value

        # Date as billing period end
        if pred.date and pred.date.value:
            period_end = pred.date.value

        # Scan line items for kWh
        for item in (pred.line_items or []):
            desc = (item.description or "").lower()
            if "kwh" in desc or "unit" in desc or "electricity" in desc:
                if item.total_amount and item.total_amount.value:
                    # Try to get kWh from quantity
                    if item.quantity and item.quantity.value:
                        kwh = float(item.quantity.value)
                    break

        # If no kWh from line items, try regex on raw text
        if kwh is None:
            pages = result.document.inference.pages
            full_text = " ".join(
                str(p) for p in pages
            )
            m = _find_first(KWH_PATTERNS, full_text)
            if m:
                kwh = _parse_float(m.group(1))

        confidence = sum([
            1 if kwh else 0,
            1 if total_cost else 0,
            1 if supplier else 0,
            1 if period_end else 0,
        ]) / 4

        return NormalizedBill(
            bill_period_start=period_start,
            bill_period_end=period_end,
            kwh=kwh,
            total_cost=total_cost,
            supplier=supplier,
            tariff_name=tariff_name,
            currency="GBP",
            confidence=round(confidence, 2),
            ocr_raw_json={"mindee": str(raw)[:2000]},
            extraction_method="mindee",
        )
    except Exception as e:
        # Fall back to pdfplumber
        result = extract_with_pdfplumber(file_bytes, filename)
        result.ocr_raw_json["mindee_error"] = str(e)
        return result


# ── Public entry point ─────────────────────────────────────────────────────────

def extract_bill(file_bytes: bytes, filename: str, mindee_api_key: str = "") -> NormalizedBill:
    if mindee_api_key:
        return extract_with_mindee(file_bytes, filename, mindee_api_key)
    return extract_with_pdfplumber(file_bytes, filename)
