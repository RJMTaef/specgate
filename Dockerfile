FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable
RUN useradd --uid 10001 --create-home app
USER 10001
EXPOSE 8000
CMD [".venv/bin/uvicorn", "specgate.screening:app", "--host", "0.0.0.0", "--port", "8000"]
