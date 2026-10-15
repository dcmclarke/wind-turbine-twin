from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models import IceEvent, Reading
from app.schemas import EventOut, ReadingIn, ReadingOut
from app.services.ingest import DuplicateReading, OutOfOrderReading, ingest

router = APIRouter(prefix="/api", tags=["readings"])


def recent_readings(db: Session, limit: int) -> list[Reading]:
    rows = db.scalars(select(Reading).order_by(Reading.timestamp.desc()).limit(limit)).all()
    return list(reversed(rows))


def recent_events(db: Session, limit: int) -> list[IceEvent]:
    return list(db.scalars(select(IceEvent).order_by(IceEvent.started_at.desc()).limit(limit)).all())


@router.get("/readings", response_model=list[ReadingOut])
def get_readings(limit: int = Query(144, ge=1, le=2000), db: Session = Depends(get_db)):
    """The most recent 10-minute readings, oldest first."""
    return recent_readings(db, limit)


@router.get("/events", response_model=list[EventOut])
def get_events(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    """Icing events, newest first."""
    return recent_events(db, limit)


@router.post("/readings", response_model=ReadingOut, status_code=201)
def post_reading(data: ReadingIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    """
    Ingest one 10-minute reading over HTTP.

    Disabled unless ALLOW_HTTP_INGEST=true, so the public demo can't be
    fed made-up data. The normal path is MQTT.
    """
    if not settings.allow_http_ingest:
        raise HTTPException(status_code=403, detail="HTTP ingestion is disabled on this server")
    try:
        return ingest(db, data, source="http")
    except DuplicateReading as e:
        raise HTTPException(status_code=409, detail=str(e))
    except OutOfOrderReading as e:
        raise HTTPException(status_code=422, detail=str(e))
