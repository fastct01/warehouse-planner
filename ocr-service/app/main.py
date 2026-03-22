from fastapi import FastAPI, UploadFile, File, HTTPException

from .config import settings
from .extractor import extract_bill
from .schemas import NormalizedBill

app = FastAPI(title="Energy Bill OCR Service", version="1.0.0")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mindee_enabled": bool(settings.MINDEE_API_KEY),
    }


@app.post("/ocr/utility-bill", response_model=NormalizedBill)
async def ocr_utility_bill(file: UploadFile = File(...)):
    """
    Accept a PDF or image of a utility bill and return structured fields.
    Uses Mindee API if MINDEE_API_KEY is set, otherwise pdfplumber + regex.
    """
    allowed = {"application/pdf", "image/jpeg", "image/png", "image/tiff"}
    content_type = file.content_type or ""
    if content_type not in allowed and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{content_type}'. Send PDF, JPEG, PNG, or TIFF.",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")

    result = extract_bill(file_bytes, file.filename or "upload.pdf", settings.MINDEE_API_KEY)
    return result
