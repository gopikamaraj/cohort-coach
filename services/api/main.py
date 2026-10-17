"""FastAPI app entry point."""

from fastapi import FastAPI

from ai.config import load_env
from services.api.judge import router as judge_router

load_env()

VERSION = "0.1.0"

app = FastAPI(title="Cohort Coach API", version=VERSION)
app.include_router(judge_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}
