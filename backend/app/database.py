import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True #validates connections before use
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all tables if they don't exist yet."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """
    Dependency: FastAPI calls this to get a DB session per request.
    Yields a session, closes it when request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

