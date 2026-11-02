"""FastAPI app entry point. One back end serves the whole product; there is no other mode."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai.config import load_env
from engine.sim_switch import check_startup as check_child_model
from services.api.admin_data import router as admin_data_router
from services.api.assistant import router as assistant_router
from services.api.channels.pwa import router as flow_router
from services.api.channels.telegram.webhook import router as telegram_router
from services.api.cohorts.class_only import router as class_only_router
from services.api.cohorts.routes import router as cohorts_router
from services.api.feedback import router as feedback_router
from services.api.judge import router as judge_router
from services.api.lesson_audio_api import router as lesson_audio_router
from services.api.lessons import router as lessons_router
from services.api.officer import router as officer_router
from services.api.pack_audio import router as pack_audio_router
from services.api.papers import router as papers_router
from services.api.papers import rules_router as paper_rules_router
from services.api.practice import router as practice_router
from services.api.profiles import router as profiles_router
from services.api.programme import router as programme_router
from services.api.review import router as review_router
from services.api.roles import router as roles_router
from services.api.sheets import router as sheets_router
from services.api.stages import router as stages_router
from services.cohort_chat.api import router as cohort_chat_router
from services.cohort_run.api import router as cohort_run_router
from services.demo.api import router as demo_router
from services.media.api import router as media_router
from services.modules.api import router as modules_router
from services.papers_hub.api import router as paper_hub_router
from services.pilot_demo.api import router as pilot_demo_router
from services.sheets_keep.api import router as sheet_keep_router
from services.speech.chain import startup_warning as speech_startup_warning
from services.tester import tester_stats_enabled
from services.usage.api import router as usage_router
from services.usage.middleware import ActionMeterMiddleware

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
    check_child_model()  # a bad SIMULATOR_MODEL (or, in bayesian mode, BAYES_PARAMS) stops the API
    if os.environ.get("SPEECH_MODE", "live") != "stub":
        speech_startup_warning()  # log only: Bodhan first before its gates pass (never blocks)
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
                "X-Action-Id",
                "X-Action-Name",
            ],
            allow_credentials=False,
        )
    app.add_middleware(ActionMeterMiddleware)  # per-action cost and time (services/usage)
    app.include_router(usage_router)
    app.include_router(judge_router)
    app.include_router(assistant_router)
    app.include_router(lessons_router)
    app.include_router(class_only_router)
    app.include_router(modules_router)
    app.include_router(cohort_chat_router)

    if os.environ.get("SEED_PAPERS_FILE"):  # fresh deployment: papers copied in once

        @app.on_event("startup")
        def _seed_papers() -> None:
            from pathlib import Path

            from services.api.profiles import _factory
            from services.api.seed import load_papers

            path = Path(os.environ["SEED_PAPERS_FILE"])
            if path.is_file():
                with _factory()() as db:
                    load_papers(db, path)

    if os.environ.get("CHAT_POLLER", "1") == "1":  # the server owns the chat's AI timer

        @app.on_event("startup")
        def _start_chat_poller() -> None:
            from services.cohort_chat.poller import start

            start()
    app.include_router(pack_audio_router)
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
    app.include_router(lesson_audio_router)
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
