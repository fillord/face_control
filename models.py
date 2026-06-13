# ─── ORM Model Definitions ────────────────────────────────────────────────────
#
# All 9 model classes for the SQLite migration (D-07).
# This module defines db = SQLAlchemy(model_class=Base) and all table schemas.
# Import db and model classes into app.py; do NOT import app here (avoids
# circular import — see RESEARCH.md Open Question 3, RESOLVED).
#
# Column names copied 1:1 from data/*.json dict keys (D-06).
# Employee.label uses autoincrement=False — preserves LBPH recognizer label (D-14).
# AttendanceRecord.event_type records last attendance transition (D-01).

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, Boolean, Float
from typing import Optional


# ─── Base class ───────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


# ─── User ─────────────────────────────────────────────────────────────────────

class User(db.Model):
    """User accounts: superadmin, org_admin, dept_admin roles."""
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    dept_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


# ─── Employee ─────────────────────────────────────────────────────────────────

class Employee(db.Model):
    """Employee records. label is the LBPH recognizer id — must NOT autoincrement (D-14)."""
    __tablename__ = "employee"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="employee")
    # CRITICAL D-14: label is the LBPH recognizer integer id, NOT a surrogate key.
    # autoincrement=False ensures the value from JSON is preserved exactly post-migration.
    label: Mapped[int] = mapped_column(Integer, nullable=False, autoincrement=False)
    face_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    registered_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    dept_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


# ─── EmployeeSchedule ─────────────────────────────────────────────────────────

class EmployeeSchedule(db.Model):
    """Per-employee work schedule — extracted from the schedule sub-dict (D-02).
    work_days_json stores the list as a TEXT column (e.g. "[1,2,3,4,5]").
    Never queried by individual day in SQL — always loaded as a whole unit.
    """
    __tablename__ = "employee_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    emp_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False, default="09:00")
    end_time: Mapped[str] = mapped_column(String(5), nullable=False, default="18:00")
    work_days_json: Mapped[str] = mapped_column(Text, nullable=False, default="[1,2,3,4,5]")


# ─── Organization ─────────────────────────────────────────────────────────────

class Organization(db.Model):
    """Organizations with Phase 5 token fields (org_token, kiosk_pin, reg_token, etc.) (D-06)."""
    __tablename__ = "organization"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    kiosk_pin: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    org_token: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, unique=True)
    reg_token: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, unique=True)
    reg_pin: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reg_token_expires: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    kiosk_display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


# ─── Department ───────────────────────────────────────────────────────────────

class Department(db.Model):
    """Departments linked to organizations."""
    __tablename__ = "department"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    head_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)


# ─── AttendanceRecord ─────────────────────────────────────────────────────────

class AttendanceRecord(db.Model):
    """Attendance records normalized from {date: {emp_id: {check_in, check_out}}} (D-01).
    event_type records the last attendance transition: 'check_in' or 'check_out'.
    """
    __tablename__ = "attendance_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    emp_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    check_in_time: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    check_out_time: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    # D-01: records the last attendance transition; populated by the recognition route (plan 06-04)
    event_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)


# ─── LogEntry ─────────────────────────────────────────────────────────────────

class LogEntry(db.Model):
    """Event log entries — replaces append_log() JSON array writes (D-03).
    Capped at 10,000 rows via DELETE on oldest when count exceeds limit.
    """
    __tablename__ = "log_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[str] = mapped_column(String(32), nullable=False)
    event: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    emp_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    confidence_raw: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


# ─── TimesheetOverride ────────────────────────────────────────────────────────

class TimesheetOverride(db.Model):
    """Manual timesheet symbol overrides — composite PK on (emp_id, date) (D-04).
    Replaces fcntl-locked save_timesheet_overrides(); SQLAlchemy transactions handle safety.
    """
    __tablename__ = "timesheet_override"

    emp_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    date: Mapped[str] = mapped_column(String(10), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(4), nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    updated_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)


# ─── AppSetting ───────────────────────────────────────────────────────────────

class AppSetting(db.Model):
    """Key-value store for app settings — replaces config.json (D-05).
    Stores arbitrary config values including legacy admin password hash.
    """
    __tablename__ = "app_setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
