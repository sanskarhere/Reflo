"""Entities from docs/ARCHITECTURE.md section 3.5 — kept 1:1 with the design doc."""
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db import Base

class RecoveryCase(Base):
    __tablename__ = "recovery_cases"
    id = Column(String, primary_key=True)
    subscription_id = Column(String, index=True)
    customer_id = Column(String, index=True)
    source_payment_id = Column(String, unique=True, index=True, nullable=True)  # Razorpay payment id — dedupe key
    amount = Column(Integer)  # paise
    error_code = Column(String, nullable=True)     # raw Razorpay failure signal, classifier input
    error_reason = Column(String, nullable=True)   # raw Razorpay failure signal, classifier input
    root_cause = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    mandate_status = Column(String, default="active")  # set at ingestion time, from webhooks.py
    decision = Column(String, nullable=True)       # proposed action, pre-gate
    gate_result = Column(String, nullable=True)     # approved | blocked
    status = Column(String, default="DETECTED")     # state machine, section 3.2
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLogEntry(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, ForeignKey("recovery_cases.id"), index=True)
    stage = Column(String)          # DETECTED | CLASSIFIED | DECIDED | GATED | EXECUTING | terminal
    input_snapshot = Column(JSON)
    output = Column(JSON)
    rule_fired = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class BatchRun(Base):
    __tablename__ = "batch_runs"
    id = Column(String, primary_key=True)
    batch_size = Column(Integer)
    recovered_amount = Column(Integer, default=0)
    recovery_rate = Column(Float, nullable=True)
    baseline_rate = Column(Float, nullable=True)
    blocked_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
