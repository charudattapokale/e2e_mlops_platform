# MLflow

## Storage in MLflow 3
- `log_model` creates a LoggedModel. Its files go to `/mlartifacts/<experiment>/models/<model-id>/artifacts/`, not under the run.
- The run page's Artifacts tab shows them with the banner "viewing artifacts assigned to a logged model": a view, not a copy.
  Checked on disk: only `models/` exists and no run folders, until `log_artifact` is called.
- Deleting a run in the UI is a soft delete: rows and files stay. `mlflow gc` removes them for good. Its flags for proxied
  artifacts were not verified.
- Load by registry name or `models:/<name>/<version>`, never by path.
- The client (3.17) was newer than the server (3.14) and worked. A newer client can call endpoints an older server lacks.
- `HistGradientBoostingClassifier` needed `skops_trusted_types=[...]` in `log_model` (MLflow 3 saves sklearn models with skops).
  Loading worked without a list.

## Registry and alias
- `registered_model_name=` creates a version. The alias `champion` points at one version. Serving reads the alias, then loads
  `models:/<name>/<version>`, so the alias cannot move between the two calls.
- A missing alias is reported as `INVALID_PARAMETER_VALUE` ("Registered model alias X not found"), a code that is also used for bad
  input. The error code cannot identify "no champion". Ask `get_registered_model(name).aliases` instead.
  Found by running the app with `MODEL_ALIAS=nonexistent`: the first version matched the wrong code and logged a traceback.
- Training logs models without registering them. A promotion gate is planned.

## Webhooks (MLflow 3.14 server)
Event `model_version_alias.created`. Experimental. SQL backend only. Defaults read from the installed package:

| Variable | Default | Note |
| --- | --- | --- |
| `MLFLOW_WEBHOOK_ALLOWED_SCHEMES` | `https` | comma-separated list |
| `MLFLOW_WEBHOOK_ALLOW_PRIVATE_IPS` | false | `true` allows 10.x Service addresses |
| `MLFLOW_WEBHOOK_REQUEST_MAX_RETRIES` | 3 | a longer outage loses the event |
| `MLFLOW_WEBHOOK_REQUEST_TIMEOUT` | 30 s | |
| `MLFLOW_WEBHOOK_CACHE_TTL` | 60 s | a new webhook may not fire for up to a minute |
| `MLFLOW_WEBHOOK_DELIVERY_MAX_WORKERS` | 10 | |

An in-cluster receiver (plain http, private Service address) needs the first two relaxed. They are set through the chart's
`extraEnvVars` in `infra/platform/mlflow.tf`. `kubectl set env` works for an experiment and is reverted by the next apply.

Observed delivery:
- Payload: `{"entity": "model_version_alias", "action": "created", "timestamp": ..., "data": {"name", "alias", "version"}}`.
- Headers: `x-mlflow-delivery-id`, `x-mlflow-timestamp`. No signature header, because the webhook had no secret.
- The model in the pod swapped about 160 ms after the alias moved.

Design:
- Registration is a row in Postgres. It survives MLflow restarts and is lost with `down.sh`. The registration script is idempotent and runs as a pipeline stage.
- The handler treats the payload as a hint and re-reads the registry, so a forged or duplicated request cannot inject a model.
- With a secret, MLflow signs requests with HMAC-SHA256 (docs). The signature header name is unknown until a webhook with a secret exists. Not built yet.

Security:
- With the guard loosened and no authentication, anyone who can reach the MLflow API can create a webhook that makes the server call internal
  addresses. Acceptable behind a port-forward on a laptop, not beyond.
- A published advisory describes a redirect bypass of the URL check. Its references point at 3.15.0 as the fix (read from search
  excerpts only, unverified). Consider a newer server image.

## Client behaviour
- The default HTTP timeout is 120 s and retries back off, so a dead MLflow can stall a caller for minutes. Bound it with
  `MLFLOW_HTTP_REQUEST_MAX_RETRIES`, `MLFLOW_HTTP_REQUEST_BACKOFF_FACTOR` and `MLFLOW_HTTP_REQUEST_TIMEOUT`.
- A `kubectl port-forward` stays bound to the pod it was opened against. After MLflow is replaced, an old tunnel can keep the local
  port without working. Close it before opening a new one.
