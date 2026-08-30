"""Append-only audit writer — one entry per state transition (FR-6, NFR-auditability)."""
from sqlalchemy.orm import Session
from app.models import AuditLogEntry

def log_stage(db: Session, case_id: str, stage: str, input_snapshot: dict,
              output: dict, rule_fired: str | None = None) -> AuditLogEntry:
    entry = AuditLogEntry(case_id=case_id, stage=stage, input_snapshot=input_snapshot,
                           output=output, rule_fired=rule_fired)
    db.add(entry)
    db.commit()
    return entry
