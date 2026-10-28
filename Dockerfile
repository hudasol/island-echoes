# Island Echoes. Build: docker build -t island-echoes .
# With dense retrieval installed: docker build --build-arg WITH_ML=1 -t island-echoes .
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv/app

ARG WITH_ML=0
COPY requirements.txt requirements.lock requirements-ml.txt ./
RUN pip install -r requirements.lock \
    && if [ "$WITH_ML" = "1" ]; then pip install -r requirements-ml.txt; fi

COPY app ./app
COPY data ./data
COPY web ./web

# The app writes only to data/cache (source cache, telemetry). Everything else is read only at run time.
RUN useradd --system --uid 10001 --no-create-home app \
    && mkdir -p data/cache \
    && chown -R app:app data/cache
USER app

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT', '8000'), timeout=4)"

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --no-access-log"]
