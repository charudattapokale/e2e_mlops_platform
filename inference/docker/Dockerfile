# ---- Stage 1: builder (runtime dependencies only) ----
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# ---- Stage 2: test (adds the dev group, e.g. httpx, runs the unit tests) ----
FROM builder AS test
RUN uv sync --frozen --no-install-project
COPY app ./app
COPY tests ./tests
RUN /app/.venv/bin/python -m unittest discover -s tests -t . -v \
    && touch /tmp/tests-passed

# ---- Stage 3: runtime (venv without dev tools, code only, non-root) ----
FROM python:3.12-slim AS runtime
RUN useradd --create-home --uid 1000 api
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app ./app
COPY --from=test /tmp/tests-passed /tmp/tests-passed

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
