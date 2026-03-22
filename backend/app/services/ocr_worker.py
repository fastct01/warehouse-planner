"""
RQ worker task: download file from MinIO, call OCR service,
save BillRaw result, update Upload status.
"""
import httpx
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..config import settings
from ..models import Upload, BillRaw
from .storage import download_file


def _make_session():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()


def process_bill_upload(upload_id: int) -> None:
    """RQ job: OCR a bill upload and store the extracted fields."""
    db = _make_session()
    try:
        upload = db.get(Upload, upload_id)
        if not upload:
            return

        upload.status = "processing"
        db.commit()

        # 1. Fetch file from MinIO
        file_bytes = download_file(upload.file_path)

        # 2. Call OCR microservice
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{settings.OCR_SERVICE_URL}/ocr/utility-bill",
                files={"file": (upload.filename, file_bytes, _content_type(upload.filename))},
            )
            response.raise_for_status()
            ocr_data = response.json()

        # 3. Persist raw OCR JSON on upload
        upload.ocr_raw_json = ocr_data
        upload.status = "done"
        db.commit()

        # 4. Create BillRaw record
        bill_raw = BillRaw(
            upload_id=upload.id,
            project_id=upload.project_id,
            bill_period_start=_parse_date(ocr_data.get("bill_period_start")),
            bill_period_end=_parse_date(ocr_data.get("bill_period_end")),
            kwh=ocr_data.get("kwh"),
            total_cost=ocr_data.get("total_cost"),
            peak_kw=ocr_data.get("peak_kw"),
            tariff_name=ocr_data.get("tariff_name"),
            supplier=ocr_data.get("supplier"),
            currency=ocr_data.get("currency", "GBP"),
            confidence=ocr_data.get("confidence", 0.0),
            extraction_method=ocr_data.get("extraction_method", "pdfplumber"),
            status="pending_review",
        )
        db.add(bill_raw)
        db.commit()

    except Exception as exc:
        if upload:
            upload.status = "failed"
            upload.error_message = str(exc)[:500]
            db.commit()
        raise
    finally:
        db.close()


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        from dateutil import parser as dp
        return dp.parse(value).date()
    except Exception:
        return None


def _content_type(filename: str) -> str:
    fname = (filename or "").lower()
    if fname.endswith(".pdf"):
        return "application/pdf"
    if fname.endswith(".png"):
        return "image/png"
    if fname.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    return "application/octet-stream"
