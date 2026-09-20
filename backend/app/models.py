from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()


class Section(Base):
    __tablename__ = "sections"

    section_id = Column(String, primary_key=True)          # e.g. "NDLS-CNB"
    section_name = Column(String, nullable=False)
    zone = Column(String)
    division = Column(String)
    from_station = Column(String)
    to_station = Column(String)
    daily_train_frequency = Column(Integer, default=0)
    is_electrified = Column(Boolean, default=True)          # used to gate TRACTION requests

    requests = relationship("MaintenanceRequest", back_populates="section")
    availabilities = relationship("CorridorAvailability", back_populates="section")


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"

    request_id = Column(Integer, primary_key=True, autoincrement=True)
    department = Column(String, nullable=False)   # ENGINEERING / SIGNAL_TELECOM / TRACTION
    section_id = Column(String, ForeignKey("sections.section_id"), nullable=False)
    defect_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)      # CRITICAL / MAJOR / MINOR
    reported_date = Column(DateTime, nullable=False)
    overdue_days = Column(Integer, default=0)
    preferred_window_start = Column(DateTime, nullable=True)
    preferred_window_end = Column(DateTime, nullable=True)
    estimated_duration_min = Column(Integer, default=120)
    status = Column(String, default="PENDING")     # PENDING / SCHEDULED / COMPLETED
    source = Column(String, default="synthetic")    # synthetic | live (submitted via UI)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    section = relationship("Section", back_populates="requests")
    assignments = relationship("BlockAssignment", back_populates="request")


class CorridorAvailability(Base):
    __tablename__ = "corridor_availability"

    availability_id = Column(Integer, primary_key=True, autoincrement=True)
    section_id = Column(String, ForeignKey("sections.section_id"), nullable=False)
    date = Column(DateTime, nullable=False)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)

    section = relationship("Section", back_populates="availabilities")


class BlockPlan(Base):
    __tablename__ = "block_plans"

    plan_id = Column(Integer, primary_key=True, autoincrement=True)
    horizon = Column(String, nullable=False)   # WEEKLY / MONTHLY
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)
    mode = Column(String, default="OPTIMIZED")  # OPTIMIZED | NAIVE (for before/after comparison)
    total_requests = Column(Integer, default=0)
    scheduled_count = Column(Integer, default=0)
    total_priority_score = Column(Float, default=0)
    conflicts_count = Column(Integer, default=0)
    total_downtime_min = Column(Integer, default=0)

    assignments = relationship("BlockAssignment", back_populates="plan")


class BlockAssignment(Base):
    __tablename__ = "block_assignments"

    assignment_id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("block_plans.plan_id"), nullable=False)
    request_id = Column(Integer, ForeignKey("maintenance_requests.request_id"), nullable=False)
    assigned_window_start = Column(DateTime, nullable=True)
    assigned_window_end = Column(DateTime, nullable=True)
    priority_score = Column(Float, default=0)
    reasoning = Column(Text, nullable=True)      # human-readable explanation
    is_conflict = Column(Boolean, default=False)  # used by the naive/manual "before" plan
    coordinated_with = Column(String, nullable=True)  # comma-joined request_ids merged into same window
    locked = Column(Boolean, default=False)       # true after a controller "what-if" override

    plan = relationship("BlockPlan", back_populates="assignments")
    request = relationship("MaintenanceRequest", back_populates="assignments")
