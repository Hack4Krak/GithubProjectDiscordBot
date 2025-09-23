FROM python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ADD src /app

WORKDIR /app
RUN uv sync --locked

CMD ["uv", "run", "src"]
EXPOSE 8000