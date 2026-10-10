# Python, uv, FastAPI

## uv
- `pyproject.toml` = what you want (ranges). `uv.lock` = exact resolved versions with hashes. Commit both.
- `uv add` / `uv remove` update toml, lock and `.venv`. After a manual toml edit, run `uv sync` (or `uv run`, which syncs).
- `uv sync --frozen` never changes the lock and fails if it is stale. Use it in Docker and CI.
- `>=3.12` in `requires-python` is a range. `.python-version` holds the one version used for the venv (`uv python pin`).
- The lock does not record the Python patch version.
- `uv init --bare` creates only `pyproject.toml`.
- `uv add pkg>=x` installs the newest release that satisfies it. Bounds are floors, not pins.
- A model trained with one scikit-learn version should be served with the same one. Compare both lock files.
- Extras: `uvicorn[standard]` adds uvloop, httptools, websockets, watchfiles. Plain uvicorn is enough for REST.
- `--dev` puts a package (e.g. httpx for `TestClient`) in a dev group that production images skip.

## Docker
Multi-stage: builder (runtime deps) -> test (runs unittest) -> runtime (venv and code only, non-root user).
The runtime stage must `COPY --from=test` something, otherwise BuildKit skips the test stage.
`useradd --uid 1000` gives a numeric non-root user, needed for `runAsNonRoot` in Kubernetes.

## FastAPI lifespan
Code before `yield` runs once at startup, code after it at shutdown. Load the model there, not per request.
A `try/except` around the load lets the app start without a model: `/health` answers, `/predict` returns 503, `/reload` can load later.
`@app.on_event` is deprecated. `TestClient` without a `with` block does not run lifespan, so tests inject the model by hand.
