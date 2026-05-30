from sqlalchemy import Column, Integer, Float, DateTime
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone
from pydantic import BaseModel

# SQLAlchemy Base - datebase table classes inherit from this
class Base(DeclarativeBase):
    pass

# DATABSE TABLE this becomes turbine_readings table in Postgres
class TurbineReading(Base):
    __tablename__ = "turbine_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))
    wind_speed = Column(Float, nullable=False)
    power_output = Column(Float, nullable=False)
    rpm = Column(Integer, nullable=False)
    temperature = Column(Float, nullable=False)

    # PYDANTIC SCHEMAS these define JSON looks like going in out

class TelemetryInput(BaseModel):
    """What the sensor sends us: just wind_speed"""
    wind_speed: float

class TelemetryOutput(BaseModel):
    """What we send back: full reading"""
    id: int
    timestamp: datetime
    wind_speed: float
    power_output: float
    rpm: int
    temperature: float

    model_config = {"from_attributes": True}
