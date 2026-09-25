from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import feeds
from app.config import get_settings
from app.database import get_db
from app.models import IceEvent, Reading
from app.routes.readings import recent_events, recent_readings
from app.schemas import DashboardOut, ReferenceCurveOut, RunOut, StatusOut, TotalsOut
from app.services.ingest import CFG, CURVE, load_state

router = APIRouter(prefix="/api", tags=["status"])


def build_status(db: Session) -> StatusOut:
    latest = db.scalar(select(Reading).order_by(Reading.timestamp.desc()).limit(1))
    active = db.scalar(select(IceEvent).where(IceEvent.ended_at.is_(None)))

    state = load_state(db)
    run = None
    if state.run_flag is not None:
        run = RunOut(flag=state.run_flag.value, length=len(state.run),
                     required=CFG.samples_required(state.run_flag))

    totals = TotalsOut(
        readings=db.scalar(select(func.count(Reading.id))) or 0,
        events=db.scalar(select(func.count(IceEvent.id))) or 0,
        energy_lost_kwh=round(db.scalar(select(func.coalesce(func.sum(IceEvent.energy_lost_kwh), 0.0))), 2),
    )
    return StatusOut(
        feed=feeds.describe(get_settings()),
        latest=latest,
        active_event=active,
        run=run,
        totals=totals,
        reference_range=tuple(round(x, 2) for x in CURVE.wind_range),
    )


@router.get("/status", response_model=StatusOut)
def get_status(db: Session = Depends(get_db)):
    """Current detector state: latest reading, active event, run in progress."""
    return build_status(db)


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(limit: int = Query(288, ge=1, le=2000), db: Session = Depends(get_db)):
    """Status, recent readings and events in one response, for the dashboard's poll."""
    return DashboardOut(
        status=build_status(db),
        readings=recent_readings(db, limit),
        events=recent_events(db, 50),
    )


@router.get("/reference-curve", response_model=ReferenceCurveOut)
def get_reference_curve():
    """The clean-blade reference curve the detector compares against."""
    return ReferenceCurveOut(
        **CURVE.to_dict(),
        icing_samples=CFG.icing_samples,
        stop_samples=CFG.stop_samples,
        rated_power=CFG.rated_power,
    )
