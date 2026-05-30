from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# TODO: import & include routes once app/routes.py built
# from app.routes import router
# app.include_router(router)

app = FastAPI(
    title="Wind Turbine Digital Twin API",
    description="Real-time monitoring for a simulated wind turbine",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Wind Turbine Digital Twin API is running"}

@app.get("/health")
async def health():
    return {"status": "ok"}
