from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.models import TurbineReading, IcingEvent, IcingStatusOutput, IcingEventOutput
from app.database import get_db
from app.detector.instance import detector

router = APIRouter(prefix="/api/icing", tags=["icing"])


@router.get("/status", response_model=IcingStatusOutput)
def get_icing_status(db: Session = Depends(get_db)):
    """
    Current icing detection state.
    Called by the React dashboard every 2 seconds.
    Returns detector window state plus the most recent power ratio.
    """
    state = detector.get_state()

    # Get the last power ratio from the database
    latest = (
        db.query(TurbineReading)
        .order_by(TurbineReading.id.desc())
        .first()
    )
    last_ratio = latest.power_ratio if latest else None

    return IcingStatusOutput(
        is_icing=state["is_icing"],
        trigger_count=state["trigger_count"],
        window_fill=state["window_fill"],
        last_ratio=last_ratio,
    )


@router.get("/history", response_model=List[IcingEventOutput])
def get_icing_history(limit: int = 20, db: Session = Depends(get_db)):
    """
    Past and current icing events log.
    Ordered most recent first.
    """
    events = (
        db.query(IcingEvent)
        .order_by(IcingEvent.started_at.desc())
        .limit(limit)
        .all()
    )
    return events
