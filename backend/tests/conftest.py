import os
import tempfile
from pathlib import Path

import pytest

# Configure the app before it is imported: throwaway SQLite database,
# no background feed, HTTP ingestion on.
_tmp = Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
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
