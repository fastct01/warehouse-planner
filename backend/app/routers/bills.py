import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..security import get_current_user
from ..database import get_db
from ..services.storage import upload_file
from ..services.ocr_worker import process_bill_upload

router = APIRouter(prefix="/projects/{project_id}/bills", tags=["bills"])

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/tiff"}


def _own_project(project_id: int, user: models.User, db: Session) -> models.Project:
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _rq_queue() -> Queue:
    redis_conn = Redis.from_url(settings.REDIS_URL)
    return Queue("energy-bills", connection=redis_conn)


# ── Monthly bills (manual) ────────────────────────────────────────────────────

@router.get("", response_model=List[schemas.MonthlyBillOut])
def get_bills(
    project_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _own_project(project_id, user, db)
    return (
        db.query(models.MonthlyBill)
        .filter(models.MonthlyBill.project_id == project_id)
        .order_by(models.MonthlyBill.year, models.MonthlyBill.month)
        .all()
    )


@router.post("/manual", response_model=List[schemas.MonthlyBillOut])
def save_bills_manual(
    project_id: int,
    bills: List[schemas.MonthlyBillCreate],
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Replace all bill data for this project with the provided rows."""
    _own_project(project_id, user, db)
    db.query(models.MonthlyBill).filter(
        models.MonthlyBill.project_id == project_id
    ).delete()

    created = []
    for bill_data in bills:
        bill = models.MonthlyBill(**bill_data.model_dump(), project_id=project_id)
        db.add(bill)
        created.append(bill)

    db.commit()
    for b in created:
        db.refresh(b)
    return created


# ── File upload & OCR ─────────────────────────────────────────────────────────

@router.post("/upload", response_model=schemas.UploadOut, status_code=202)
async def upload_bill(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """
    Upload a PDF or image bill. File is stored in MinIO and an OCR job is
    queued. Poll GET /uploads/{upload_id} to check processing status.
    """
    _own_project(project_id, user, db)

    content_type = file.content_type or ""
    filename = file.filename or "upload.pdf"
    if content_type not in ALLOWED_TYPES and not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF and image files are accepted.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    # Store in MinIO
    object_key = f"project-{project_id}/{uuid.uuid4()}-{filename}"
    upload_file(object_key, file_bytes, content_type or "application/pdf")

    # Create DB record
    upload = models.Upload(
        project_id=project_id,
        filename=filename,
        file_path=object_key,
        file_type="pdf" if filename.lower().endswith(".pdf") else "image",
        status="pending",
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    # Enqueue OCR job
    _rq_queue().enqueue(process_bill_upload, upload.id)

    return upload


@router.get("/uploads", response_model=List[schemas.UploadOut])
def list_uploads(
    project_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _own_project(project_id, user, db)
    return (
        db.query(models.Upload)
        .filter(models.Upload.project_id == project_id)
        .order_by(models.Upload.created_at.desc())
        .all()
    )


@router.get("/uploads/{upload_id}", response_model=schemas.UploadOut)
def get_upload(
    project_id: int,
    upload_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _own_project(project_id, user, db)
    upload = db.query(models.Upload).filter(
        models.Upload.id == upload_id,
        models.Upload.project_id == project_id,
    ).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload


@router.get("/uploads/{upload_id}/result", response_model=schemas.BillRawOut)
def get_upload_result(
    project_id: int,
    upload_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Return the extracted bill fields for user review."""
    _own_project(project_id, user, db)
    upload = db.query(models.Upload).filter(
        models.Upload.id == upload_id,
        models.Upload.project_id == project_id,
    ).first()
    if not upload or not upload.bill_raw:
        raise HTTPException(status_code=404, detail="Result not ready yet.")
    return upload.bill_raw


@router.patch("/uploads/{upload_id}/result", response_model=schemas.BillRawOut)
def patch_upload_result(
    project_id: int,
    upload_id: int,
    data: schemas.BillRawPatch,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """User corrections to extracted fields + approve/reject."""
    _own_project(project_id, user, db)
    upload = db.query(models.Upload).filter(
        models.Upload.id == upload_id,
        models.Upload.project_id == project_id,
    ).first()
    if not upload or not upload.bill_raw:
        raise HTTPException(status_code=404, detail="Result not found.")

    bill_raw = upload.bill_raw
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(bill_raw, field, value)

    # If approved, create / update the canonical MonthlyBill entry
    if data.status == "approved" and bill_raw.bill_period_end:
        _upsert_monthly_bill(bill_raw, db)

    db.commit()
    db.refresh(bill_raw)
    return bill_raw


def _upsert_monthly_bill(bill_raw: models.BillRaw, db: Session) -> None:
    """Convert an approved BillRaw into a MonthlyBill row."""
    end = bill_raw.bill_period_end
    existing = db.query(models.MonthlyBill).filter(
        models.MonthlyBill.project_id == bill_raw.project_id,
        models.MonthlyBill.year == end.year,
        models.MonthlyBill.month == end.month,
    ).first()

    if existing:
        existing.kwh = bill_raw.kwh or existing.kwh
        existing.cost_gbp = bill_raw.total_cost or existing.cost_gbp
        existing.peak_demand_kw = bill_raw.peak_kw
        existing.tariff_name = bill_raw.tariff_name
    else:
        db.add(models.MonthlyBill(
            project_id=bill_raw.project_id,
            year=end.year,
            month=end.month,
            kwh=bill_raw.kwh or 0,
            cost_gbp=bill_raw.total_cost or 0,
            peak_demand_kw=bill_raw.peak_kw,
            tariff_name=bill_raw.tariff_name,
        ))
