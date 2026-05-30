import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# Create db engine (the connection)
engine = create_engine(DATABASE_URL)

# SessionLocal is factory for creating db sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create tables in the database"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """
    Dependency function - FastAPI calls this to get a DB session per request.
    Yields a session, then closes it when the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
