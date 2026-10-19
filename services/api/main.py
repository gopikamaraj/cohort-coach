"""FastAPI app entry point."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai.config import load_env
from services.api.judge import router as judge_router
from services.api.practice import router as practice_router
from services.api.profiles import router as profiles_router
from services.api.sheets import router as sheets_router

load_env()

VERSION = "0.1.0"

app = FastAPI(title="Cohort Coach API", version=VERSION)
# Browsers may call the API only from the PWA's own origin (PWA_ORIGIN). No wildcard, and no
# cookies or credentials: the app has no login.
if origin := os.environ.get("PWA_ORIGIN"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.rstrip("/")],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )
app.include_router(judge_router)
app.include_router(practice_router)
app.include_router(profiles_router)
app.include_router(sheets_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}
