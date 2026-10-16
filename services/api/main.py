"""FastAPI app entry point."""

from fastapi import FastAPI

VERSION = "0.1.0"

app = FastAPI(title="Cohort Coach API", version=VERSION)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}
