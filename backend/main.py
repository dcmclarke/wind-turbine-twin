import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import feeds
from app.config import get_settings
from app.database import init_db
from app.routes.readings import router as readings_router
from app.routes.status import router as status_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    feeds.start(settings)
    yield
    feeds.stop()


app = FastAPI(
    title="Wind Turbine Icing Detection API",
    description=(
        "IEA Wind Task 19 icing detection on 10-minute SCADA data from the "
        "ETH Zurich Aventa AV-7 research turbine."
    ),
    version="3.0.0",
    lifespan=lifespan,
)

_allowed_origins = ["http://localhost:3000", "http://localhost:5173"]
if settings.frontend_url:
    _allowed_origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(status_router)
app.include_router(readings_router)


@app.get("/")
async def root():
    return {"message": "Wind Turbine Icing Detection API is running", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}
