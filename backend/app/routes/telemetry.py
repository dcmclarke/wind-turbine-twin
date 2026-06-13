from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.models import TurbineReading, TelemetryInput, TelemetryOutput, IcingEvent
from app.database import get_db
from app.detector.instance import detector

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

@router.post("", response_model=TelemetryOutput)
def ingest_telemetry(data: TelemetryInput, db: Session = Depends(get_db)):
    # Parse timestamp
    try:
        timestamp = datetime.fromisoformat(data.timestamp)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid timestamp format")

    # Run detector
    result = detector.process(
        wind_speed=data.wind_speed,
        actual_power=data.power_output,
        timestamp=timestamp,
    )

    # Save reading
    reading = TurbineReading(
        timestamp=timestamp,
        wind_speed=data.wind_speed,
        power_output=data.power_output,
        rpm=data.rpm,
        yaw_angle=data.yaw_angle,
        rotor_status=data.rotor_status,
        power_ratio=result.power_ratio,
    )
    db.add(reading)

    # Icing event logic
    # Find any currently active icing event
    active_event = (
        db.query(IcingEvent)
        .filter(IcingEvent.is_active == True)
        .first()
    )

    if result.is_icing and active_event is None:
        # Icing just started — open a new event
        new_event = IcingEvent(
            started_at=timestamp,
            last_seen_at=timestamp,
            trigger_count=result.trigger_count,
            is_active=True,
        )
        db.add(new_event)

    elif result.is_icing and active_event is not None:
        # Icing continuing — update the existing event
        active_event.last_seen_at = timestamp
        active_event.trigger_count = result.trigger_count

    elif not result.is_icing and active_event is not None:
        # Icing just cleared — close the event
        active_event.is_active = False

    db.commit()
    db.refresh(reading)
    return reading


@router.get("/latest", response_model=TelemetryOutput)
def get_latest(db: Session = Depends(get_db)):
    """Return the most recent turbine reading."""
    reading = (
        db.query(TurbineReading)
        .order_by(TurbineReading.id.desc())
        .first()
    )
    if reading is None:
        raise HTTPException(status_code=404, detail="No readings yet")
    return reading


@router.get("/history", response_model=List[TelemetryOutput])
def get_history(limit: int = 50, db: Session = Depends(get_db)):
    """Return last N readings for the chart."""
    readings = (
        db.query(TurbineReading)
        .order_by(TurbineReading.timestamp.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(readings))
