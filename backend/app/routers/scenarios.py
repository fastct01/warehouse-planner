from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas
from ..security import get_current_user
from ..database import get_db
from ..services.scenario_engine import run_all_scenarios

router = APIRouter(prefix="/projects/{project_id}/scenarios", tags=["scenarios"])


def _own_project(project_id: int, user: models.User, db: Session) -> models.Project:
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/run", response_model=List[schemas.ScenarioResultOut])
def run_scenarios(
    project_id: int,
    params: Optional[schemas.ScenarioParams] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    project = _own_project(project_id, user, db)

    bills = (
        db.query(models.MonthlyBill)
        .filter(models.MonthlyBill.project_id == project_id)
        .all()
    )
    if not bills:
        raise HTTPException(
            status_code=400, detail="No bill data found. Add monthly bills first."
        )

    annual_kwh = sum(b.kwh for b in bills)
    annual_cost = sum(b.cost_gbp for b in bills)

    # Normalise to 12-month equivalent if we have more or fewer bills
    months = len(bills)
    if months != 12:
        annual_kwh = (annual_kwh / months) * 12
        annual_cost = (annual_cost / months) * 12

    # Default solar size: covers ~30% of annual load at 900 kWh/kWp/yr
    solar_kw = (params.solar_kw if params and params.solar_kw else None) or round(
        annual_kwh * 0.30 / 900, 1
    )
    battery_kwh = (params.battery_kwh if params and params.battery_kwh else None) or round(
        solar_kw * 1.5
    )

    results = run_all_scenarios(
        annual_kwh=annual_kwh,
        annual_cost=annual_cost,
        building_type=project.building_type,
        location=project.location,
        floor_area=project.floor_area_m2,
        solar_kw=solar_kw,
        battery_kwh=battery_kwh,
    )

    # Replace previous scenario results
    db.query(models.ScenarioResult).filter(
        models.ScenarioResult.project_id == project_id
    ).delete()

    saved = []
    for r in results:
        row = models.ScenarioResult(
            project_id=project_id,
            scenario_type=r["scenario"],
            name=r["name"],
            capex_gbp=r["capex_gbp"],
            annual_savings_kwh=r["annual_savings_kwh"],
            annual_savings_gbp=r["annual_savings_gbp"],
            payback_years=r.get("payback_years"),
            npv_gbp=r.get("npv_gbp"),
            params={"solar_kw": solar_kw, "battery_kwh": battery_kwh},
            assumptions=r.get("assumptions"),
        )
        db.add(row)
        saved.append(row)

    db.commit()
    for s in saved:
        db.refresh(s)
    return saved


@router.get("", response_model=List[schemas.ScenarioResultOut])
def get_scenarios(
    project_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _own_project(project_id, user, db)
    return (
        db.query(models.ScenarioResult)
        .filter(models.ScenarioResult.project_id == project_id)
        .all()
    )
