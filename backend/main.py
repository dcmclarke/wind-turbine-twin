from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()   # runs on startup
    yield       # app runs here


app = FastAPI(
    title="Wind Turbine Digital Twin API",
    description="Real-time monitoring for a simulated wind turbine",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {"message": "Wind Turbine Digital Twin API is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
