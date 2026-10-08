# ---- Stage 1: builder (runtime dependencies only) ----
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# ---- Stage 2: test (same venv, plus code and tests) ----
FROM builder AS test

COPY train.py ./train.py
COPY tests ./tests
RUN /app/.venv/bin/python -m unittest discover -s tests -t . -v \
    && touch /tmp/tests-passed

# ---- Stage 3: runtime (only the venv and the code) ----
FROM python:3.12-slim AS runtime

RUN useradd --create-home --uid 1000 trainer
WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY train.py ./train.py
# Forces the test stage to run: the build fails here if a test failed
COPY --from=test /tmp/tests-passed /tmp/tests-passed

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER trainer
CMD ["python", "train.py"]
