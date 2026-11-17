from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.routes.api import router


ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

app = FastAPI(
    title="ResumeIQ API",
    description="Explainable resume analysis, compression, and job-description matching.",
    version="1.0.0",
)
app.include_router(router)
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")