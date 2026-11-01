"""FastAPI app entry point. One back end serves the whole product; there is no other mode."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai.config import load_env
from engine.child_model import model_from_env
from services.api.admin_data import router as admin_data_router
from services.api.assistant import router as assistant_router
from services.api.channels.pwa import router as flow_router
from services.api.channels.telegram.webhook import router as telegram_router
from services.api.cohorts.routes import router as cohorts_router
from services.api.feedback import router as feedback_router
from services.api.judge import router as judge_router
from services.api.lessons import router as lessons_router
from services.api.officer import router as officer_router
from services.api.papers import router as papers_router
from services.api.papers import rules_router as paper_rules_router
from services.api.practice import router as practice_router
from services.api.profiles import router as profiles_router
from services.api.programme import router as programme_router
from services.api.review import router as review_router
from services.api.roles import router as roles_router
from services.api.sheets import router as sheets_router
from services.api.stages import router as stages_router
from services.cohort_run.api import router as cohort_run_router
from services.demo.api import router as demo_router
from services.media.api import router as media_router
from services.papers_hub.api import router as paper_hub_router
from services.pilot_demo.api import router as pilot_demo_router
from services.sheets_keep.api import router as sheet_keep_router
from services.tester import tester_stats_enabled

load_env()

VERSION = "0.1.0"


@asynccontextmanager
async def _tester_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Make the tester tables and views, and delete tester data past the retention period."""
    from services.api.profiles import _factory
    from services.tester.models import ensure_tester_schema
    from services.tester.routes import quiet_access_log, run_retention

    quiet_access_log()
    factory = _factory()
    ensure_tester_schema(factory.kw["bind"])
    with factory() as db:
        run_retention(db)
    yield


def create_app() -> FastAPI:
    model_from_env()  # a bad SIMULATOR_MODEL (or BAYES_* value) stops the API here, with a message
    app = FastAPI(
        title="Cohort Coach API",
        version=VERSION,
        lifespan=_tester_lifespan if tester_stats_enabled() else None,
    )
    # Browsers may call the API only from the PWA's own origin (PWA_ORIGIN). No wildcard, and no
    # cookies or credentials.
    if origin := os.environ.get("PWA_ORIGIN"):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[origin.rstrip("/")],
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=[
                "Content-Type",
                "X-Admin-Key",
                "X-Device-Id",
                "X-Device-Hash",
                "X-Team-Token",
                "X-Judge",
                "X-Role",
                "X-Person",
                "X-Class-Id",
                "X-Demo-Person",
                "X-Demo-Session",
            ],
            allow_credentials=False,
        )
    app.include_router(judge_router)
    app.include_router(assistant_router)
    app.include_router(lessons_router)
    app.include_router(cohorts_router)
    app.include_router(officer_router)
    app.include_router(roles_router)
    app.include_router(flow_router)
    app.include_router(telegram_router)
    app.include_router(feedback_router)
    app.include_router(admin_data_router)
    app.include_router(practice_router)
    app.include_router(profiles_router)
    app.include_router(programme_router)
    app.include_router(review_router)
    app.include_router(papers_router)
    app.include_router(paper_rules_router)
    app.include_router(paper_hub_router)
    app.include_router(pilot_demo_router)
    app.include_router(demo_router)
    app.include_router(cohort_run_router)
    app.include_router(sheets_router)
    app.include_router(sheet_keep_router)
    app.include_router(stages_router)
    app.include_router(media_router)
    if tester_stats_enabled():
        from services.tester.routes import router as tester_router

        app.include_router(tester_router)

    @app.get("/api/health")
    def health() -> dict[str, str | bool]:
        from ai.config import ai_mode, dev_testing

        # ai_mode lets every screen say when answers are replayed (recorded) or the AI is off
        out: dict[str, str | bool] = {"status": "ok", "version": VERSION, "ai_mode": ai_mode()}
        if dev_testing():  # testing shortcuts on a developer's machine only (DEV_TESTING=1)
            out["dev_testing"] = True
        return out

    return app


app = create_app()
