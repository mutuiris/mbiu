FROM ghcr.io/astral-sh/uv:0.12.24 AS uv

FROM python:3.14.8-slim-trixie AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY config ./config
COPY mbiu ./mbiu

FROM python:3.14.8-slim-trixie
RUN useradd --system --uid 10001 --no-create-home mbiu
WORKDIR /app
COPY --from=build /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER 10001
EXPOSE 8000
# PORT is set by the host, 8000 locally
CMD ["sh", "-c", "exec uvicorn config.asgi:application --host 0.0.0.0 --port ${PORT:-8000}"]
