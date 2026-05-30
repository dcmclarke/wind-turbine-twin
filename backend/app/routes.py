from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.models import TurbineReading, TelemetryInput, TelemetryOutput
from app.database import get_db
from app.turbine import Turbine

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

# Single instance for demo purposes.
# In production: use a shared state store (Redis) or persist state to DB.
turbine = Turbine()

@router.post("", response_model=TelemetryOutput)
def ingest_telemetry(data: TelemetryInput, db: Session = Depends(get_db)):
    """
    Recieve wind_speed from sensor.
    Run physics simulation. Save to database. Return full reading.
    """
    # 1. Update turbine state with new wind speed
    state = turbine.update(data.wind_speed)

    # 2. Save to database
    reading = TurbineReading(
        wind_speed=state["wind_speed"],
        power_output=state["power_output"],
        rpm=state["rpm"],
        temperature=state["temperature"]
    )
    db.add(reading)
    db.commit()
    db.refresh(reading) #gets auto-generated id and timestamp back

    return reading

@router.get("/latest", response_model=TelemetryOutput)
def get_latest(db: Session = Depends(get_db)):
    """
    Return the most recent turbine reading.
    React dashboard calls this every 2 seconds.
    """
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
    """
    Return last N readings for the chart.
    ?limit=50 by default, React can request more or less.
    """
    readings = (
        db.query(TurbineReading)
        .order_by(TurbineReading.timestamp.desc())
        .limit(limit)
        .all()
    )

    # Reverse so oldest is first (charts read left to right)
    return list(reversed(readings))
