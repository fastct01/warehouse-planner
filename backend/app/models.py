from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, JSON
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
    uploads = relationship(
        "Upload", back_populates="project", cascade="all, delete-orphan"
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


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)       # MinIO object key
    file_type = Column(String, nullable=False)       # pdf | image
    # pending | processing | done | failed
    status = Column(String, default="pending")
    error_message = Column(String)
    ocr_raw_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="uploads")
    bill_raw = relationship("BillRaw", back_populates="upload", uselist=False)


class BillRaw(Base):
    __tablename__ = "bills_raw"

    id = Column(Integer, primary_key=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    bill_period_start = Column(Date)
    bill_period_end = Column(Date)
    kwh = Column(Float)
    total_cost = Column(Float)
    peak_kw = Column(Float)
    tariff_name = Column(String)
    supplier = Column(String)
    currency = Column(String, default="GBP")
    confidence = Column(Float, default=0.0)
    extraction_method = Column(String, default="pdfplumber")
    # pending_review | approved | rejected
    status = Column(String, default="pending_review")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    upload = relationship("Upload", back_populates="bill_raw")


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
