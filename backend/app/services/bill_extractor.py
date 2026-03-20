"""
Bill extraction service.

Phase 1: Returns a stub so the upload endpoint exists and the review UI can be built.
Phase 2: Replace the body of `extract_from_pdf` with a real OCR integration
         (e.g. Google Document AI, AWS Textract, or Azure Form Recognizer).
"""
from typing import Dict, Any


def extract_from_pdf(content: bytes, filename: str) -> Dict[str, Any]:
    """
    Extract bill fields from raw PDF bytes.

    Returns a dict with `status` and `extracted` fields.
    The caller (upload endpoint) returns this to the frontend for user review.
    """
    return {
        "status": "manual_review_required",
        "note": "Automated extraction coming in Phase 2. Please enter data manually.",
        "extracted": {
            "year": None,
            "month": None,
            "kwh": None,
            "cost_gbp": None,
            "peak_demand_kw": None,
            "tariff_name": None,
        },
    }
