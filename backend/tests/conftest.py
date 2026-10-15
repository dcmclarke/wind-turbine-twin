import os
import tempfile
from pathlib import Path

import pytest

# Configure the app before it is imported: throwaway database, no
# background feed, HTTP ingestion on. The tests delete every row, so they
# never use DATABASE_URL: SQLite by default, or TEST_DATABASE_URL if set
# (CI sets it to run the same tests on PostgreSQL).
_tmp = Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["INGEST_MODE"] = "none"
os.environ["ALLOW_HTTP_INGEST"] = "true"


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.database import SessionLocal
    from app.services.ingest import reset
    from main import app

    with TestClient(app) as c:
        with SessionLocal() as db:
            reset(db)
        yield c
