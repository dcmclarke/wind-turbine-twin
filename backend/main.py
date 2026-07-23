import os
from contextlib import asynccontextmanager
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.telemetry import router as telemetry_router
from app.database import init_db
from app.routes.icing import router as icing_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Wind Turbine Digital Twin API",
    description="Real-time SCADA monitoring with IEA T19 icing detection",
    version="2.0.0",
    lifespan=lifespan
)

_allowed_origins = ["http://localhost:3000", "http://localhost:5173"]
if frontend_url := os.getenv("FRONTEND_URL"):
    _allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telemetry_router)
app.include_router(icing_router)

@app.get("/")
async def root():
    return {"message": "Wind Turbine Digital Twin API is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
