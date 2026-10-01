FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /uvx /bin/
WORKDIR /code
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
ENV PATH="/code/.venv/bin:$PATH"
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
