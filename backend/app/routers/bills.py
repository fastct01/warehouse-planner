from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..security import get_current_user
from ..database import get_db
from ..services.bill_extractor import extract_from_pdf

router = APIRouter(prefix="/projects/{project_id}/bills", tags=["bills"])


def _own_project(project_id: int, user: models.User, db: Session) -> models.Project:
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


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


@router.post("/upload")
async def upload_bill(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """
    Phase 2 stub: upload a PDF bill for extraction.
    Returns extracted fields for user review before saving.
    """
    _own_project(project_id, user, db)
    content = await file.read()
    extracted = extract_from_pdf(content, file.filename or "upload.pdf")
    return {"filename": file.filename, **extracted}
