# Python, uv and FastAPI

## uv
- `pyproject.toml` is what you want (ranges). `uv.lock` is what was resolved (exact versions with hashes). Commit both.
- `uv add` and `uv remove` update toml, lock and `.venv`. After a manual toml edit, run `uv sync`.
- `uv sync --frozen` never changes the lock and fails if it is stale. Use it in Docker and CI.
- `requires-python = ">=3.12"` is a range. `.python-version` holds the version used for the venv (`uv python pin`).
- `uv run` looks for `pyproject.toml` in the current folder. From the repository root it used a bare Python and failed with
  `No module named 'mlflow'`. Run it from `training/` or `inference/`.
- A model trained with one scikit-learn version should be served with the same one. Compare both lock files.
- `uvicorn[standard]` adds uvloop, httptools, websockets and watchfiles. Plain uvicorn is enough for REST.
- `--dev` puts packages such as `httpx` (needed by FastAPI's `TestClient`) in a group that production images skip.

## Docker
Multi-stage: builder (runtime dependencies), test (dev group, runs unittest), runtime (venv and code only, non-root user).
The runtime stage must `COPY --from=test` something, otherwise BuildKit skips the test stage and a failing test would not stop the build.
`useradd --uid 1000` gives a numeric user, which `runAsNonRoot` in Kubernetes needs.

## Tests
- `python -m unittest discover -s tests -t .` finds `test*.py`. `-t .` makes the project folder the import root.
  `NO TESTS RAN` exits non-zero, so an empty test folder fails the Docker build instead of passing silently.
- A fake must behave like the real object. `predict_proba` returns a NumPy array, and a fake returning a list failed at `[0, 1]`.
  The failure was in the test double, not in the code.
- `TestClient(app)` without a `with` block does not run `lifespan`, so tests inject the model by hand.
- Assert on log output with `assertLogs`, and on silence with `assertNoLogs` (Python 3.10 and later).

## FastAPI
- `lifespan`: code before `yield` runs once at startup, code after it at shutdown. Load the model there, not per request.
- Fail fast at startup: the API refuses to start without a champion, so a bad deploy never replaces a working pod. At runtime a failed
  reload keeps the current model. A bounded startup retry covers connection errors only. A missing champion is not retried.
- Uvicorn accepts no connections during `lifespan`, so a slow model load looks like a failing probe. A `startupProbe` holds the other probes back.
- `include_in_schema=False` hides a route from the docs page. The route still exists. What blocks outside access is the Ingress path allow-list.
- Read shared state once per request (`model, version = state[...]`), so a reload in another thread cannot mix a model with the wrong version.

## Logging
- Python's root logger defaults to `WARNING`, and uvicorn configures only its own loggers. `log.info(...)` in application code printed nothing
  until `logging.basicConfig` was called. Configure once, at the entry point. Library modules only call `getLogger`.
- Messages follow `event=name key=value`, so they are easy to read and to search. Levels: INFO for state changes and request outcomes,
  WARNING for expected problems, ERROR for broken things, DEBUG for routine no-ops.
- Never log request inputs (personal banking data). Redact header values that look like credentials.

## Shell gotchas
- PowerShell is for `wsl` and `wsl --shutdown` only. In Windows PowerShell 5.1 `curl` is an alias for `Invoke-WebRequest`, and `&&` is not valid.
- `kubectl auth can-i create pods/exec` answers `no` even when the rule exists. Use `--subresource=exec`.
- A heredoc truncates long pastes unpredictably. Check the line count and the headings after writing a file.
