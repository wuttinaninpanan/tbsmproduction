# =============================================================================
# Production image (Linux + Docker). Serves the app with gunicorn; static files
# are collected at startup and served by WhiteNoise (no separate nginx needed).
#
# Tailwind CSS is built during development (`python manage.py tailwind build`)
# and its output (theme/static/css/dist/styles.css) is committed, so this image
# does NOT need Node — it just collects and serves the already-built CSS.
# =============================================================================
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Runtime OS deps only (gettext for i18n; curl for healthchecks). No C
# toolchain: every dependency (psycopg[binary], pillow, ...) ships a prebuilt
# wheel, so gcc/python3-dev were dead weight (~250 MB).
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    gettext \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Poetry installs into the system environment (no nested venv inside the image).
RUN pip install --upgrade pip setuptools poetry
RUN poetry config virtualenvs.create false

# Dependencies first (better layer caching) — production deps only.
COPY pyproject.toml poetry.lock* /app/
RUN poetry lock --no-interaction --no-ansi \
    && poetry install --no-root --only main --no-interaction --no-ansi

# App source.
COPY . /app

RUN chmod +x docker/entrypoint.prod.sh

EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.prod.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
