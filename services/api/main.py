"""FastAPI app entry point.

`create_app(pilot=True)` (or PILOT_MODE=1) builds the pilot app: sign-in, sheet upload and
intervention audio only. Every other router is simply not mounted, so every other path is a 404,
and the interactive API docs are off. Hiding a menu item would not be enough.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai.config import load_env, pilot_mode
from services.api.channels.pwa import router as flow_router
from services.api.channels.telegram.webhook import router as telegram_router
from services.api.cohorts.routes import router as cohorts_router
from services.api.feedback import router as feedback_router
from services.api.judge import router as judge_router
from services.api.lessons import router as lessons_router
from services.api.officer import router as officer_router
from services.api.practice import router as practice_router
from services.api.profiles import router as profiles_router
from services.api.programme import router as programme_router
from services.api.review import router as review_router
from services.api.roles import router as roles_router
from services.api.sheets import router as sheets_router
from services.api.stages import router as stages_router
from services.pilot.routes import router as pilot_router

load_env()

VERSION = "0.1.0"


@asynccontextmanager
async def _pilot_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Fail at start-up, not on the first upload, if the sheets bucket is not set up, and delete
    anything past the retention period."""
    from services.api.profiles import _factory
    from services.pilot.sheets import purge_expired
    from services.pilot.storage import audio_store, sheets_store

    store = sheets_store()
    audio_store()
    with _factory()() as db:
        purge_expired(db, store)
    yield


def create_app(pilot: bool | None = None) -> FastAPI:
    pilot = pilot_mode() if pilot is None else pilot
    app = FastAPI(
        title="Cohort Coach API",
        version=VERSION,
        lifespan=_pilot_lifespan if pilot else None,
        docs_url=None if pilot else "/docs",
        redoc_url=None if pilot else "/redoc",
        openapi_url=None if pilot else "/openapi.json",
    )
    # Browsers may call the API only from the PWA's own origin (PWA_ORIGIN). No wildcard, and no
    # cookies or credentials: the app sends its sign-in token in a header.
    if origin := os.environ.get("PWA_ORIGIN"):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[origin.rstrip("/")],
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=[
                "Content-Type",
                "X-Admin-Key",
                "X-Device-Id",
                "X-Judge",
                "X-Role",
                "Authorization",
            ],
            allow_credentials=False,
        )
    if pilot:
        app.include_router(pilot_router)
    else:
        app.include_router(judge_router)
        app.include_router(lessons_router)
        app.include_router(cohorts_router)
        app.include_router(officer_router)
        app.include_router(roles_router)
        app.include_router(flow_router)
        app.include_router(telegram_router)
        app.include_router(feedback_router)
        app.include_router(practice_router)
        app.include_router(profiles_router)
        app.include_router(programme_router)
        app.include_router(review_router)
        app.include_router(sheets_router)
        app.include_router(stages_router)

    @app.get("/api/health")
    def health() -> dict[str, str | bool]:
        # `pilot` appears only in pilot mode, so the normal health answer is unchanged.
        return {"status": "ok", "version": VERSION, **({"pilot": True} if pilot else {})}

    return app


app = create_app()
