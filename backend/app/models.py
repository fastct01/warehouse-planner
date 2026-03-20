from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    projects = relationship("Project", back_populates="owner")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    # office | hospital | data_centre | factory
    building_type = Column(String, nullable=False)
    location = Column(String, nullable=False)
    floor_area_m2 = Column(Float)
    # 9-5_weekdays | extended_hours | 24_7
    operating_pattern = Column(String, default="9-5_weekdays")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="projects")
    monthly_bills = relationship(
        "MonthlyBill", back_populates="project", cascade="all, delete-orphan"
    )
    scenario_results = relationship(
        "ScenarioResult", back_populates="project", cascade="all, delete-orphan"
    )


class MonthlyBill(Base):
    __tablename__ = "monthly_bills"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1–12
    kwh = Column(Float, nullable=False)
    cost_gbp = Column(Float, nullable=False)
    peak_demand_kw = Column(Float)
    tariff_name = Column(String)

    project = relationship("Project", back_populates="monthly_bills")


class ScenarioResult(Base):
    __tablename__ = "scenario_results"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    scenario_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    capex_gbp = Column(Float)
    annual_savings_kwh = Column(Float)
    annual_savings_gbp = Column(Float)
    payback_years = Column(Float)
    npv_gbp = Column(Float)
    params = Column(JSON)
    assumptions = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="scenario_results")
