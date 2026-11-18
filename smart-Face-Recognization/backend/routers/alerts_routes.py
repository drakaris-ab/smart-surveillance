 
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database.database import SessionLocal
from backend.database.models import AlertFace

router = APIRouter(prefix="/alerts", tags=["Alerts"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/active")
def get_active_alerts(db: Session = Depends(get_db)):
    """Return only unconsumed alerts"""
    return db.query(AlertFace).filter(AlertFace.consumed == False).order_by(AlertFace.timestamp.desc()).all()

@router.get("/history")
def get_alert_history(db: Session = Depends(get_db)):
    """Return all alerts (history)"""
    return db.query(AlertFace).order_by(AlertFace.timestamp.desc()).all()

@router.post("/consume/{alert_id}")
def consume_alert(alert_id: int, db: Session = Depends(get_db)):
    """Mark alert as consumed once UI displays it"""
    alert = db.query(AlertFace).filter(AlertFace.id == alert_id).first()
    if alert:
        alert.consumed = True
        db.commit()
    return {"status": "cleared", "alert_id": alert_id}
