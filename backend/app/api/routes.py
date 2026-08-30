"""Routes from docs/ARCHITECTURE.md section 3.6."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db

router = APIRouter()

@router.post("/events/payment-failed")
def payment_failed_webhook(payload: dict, db: Session = Depends(get_db)):
    raise NotImplementedError

@router.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    raise NotImplementedError

@router.get("/cases/{case_id}/audit")
def get_case_audit(case_id: str, db: Session = Depends(get_db)):
    raise NotImplementedError

@router.get("/batch/{batch_id}/metrics")
def get_batch_metrics(batch_id: str, db: Session = Depends(get_db)):
    raise NotImplementedError

@router.get("/rules")
def get_rules():
    raise NotImplementedError
