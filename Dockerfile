# Build stage: pyswisseph and timezonefinder have no wheels for Python 3.12,
# so they compile here (the full image ships a C compiler) and only the
# installed packages reach the slim final image.
FROM python:3.12 AS build
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY aster_engine ./aster_engine
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim
COPY --from=build /install /usr/local
WORKDIR /app
COPY ephe ./ephe
ENV ASTER_EPHE_PATH=/app/ephe \
    PORT=8000 \
    PYTHONUNBUFFERED=1
RUN useradd --system --no-create-home engine
USER engine
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health')"
# PORT is set by platforms such as Cloud Run and Fly.io.
CMD ["sh", "-c", "exec uvicorn aster_engine.api:app --host 0.0.0.0 --port ${PORT}"]
