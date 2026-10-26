# API image for staging and production (see docs/deploy.md). Not yet built on a real host.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# ffmpeg encodes the pilot's lesson audio (services/speech/audio.py needs it on PATH).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Only what the API needs: the engine, the AI layer, the services, the content files and the
# synthetic block. The PWA is a separate static site.
COPY pyproject.toml README.md LICENSE ./
COPY engine ./engine
COPY ai ./ai
COPY services ./services
COPY content ./content
COPY strings ./strings
# The pilot forms the item validator checks scripts against (read at run time).
COPY docs/design/pilot_forms.golden.json ./docs/design/pilot_forms.golden.json
COPY data/__init__.py ./data/__init__.py
# The simulated block only: never raw pilot files.
COPY data/synthetic ./data/synthetic
RUN pip install --no-cache-dir ".[prod]"

EXPOSE 8000
CMD ["sh", "-c", "uvicorn services.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
