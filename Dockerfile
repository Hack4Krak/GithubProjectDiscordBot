FROM python:3.14-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ADD . /app

WORKDIR /app
RUN uv sync --locked

EXPOSE $PORT
CMD exec .venv/bin/gunicorn src.server:app \
  --workers 1 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind "${IP_ADDRESS:-0.0.0.0}:${PORT:-8000}" \
  --log-level info
