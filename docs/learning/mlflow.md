# MLflow

## MLflow 3 storage
- `log_model` creates a LoggedModel entity. Files go to `/mlartifacts/<experiment>/models/<model-id>/artifacts/`.
- Model artifacts are no longer stored under the run. The run page shows a link to the logged model.
  The banner "viewing artifacts assigned to a logged model" is MLflow's own message, not a copy.
- `log_artifact(s)` is what creates a run's own `artifacts/` folder. Without it, no run folders exist on disk.
- Load by registry name or `models:/<model-id>`, never by path. `runs:/<run-id>/model` is the MLflow 2 style.

## Registry
- `registered_model_name=` registers a version. The alias `champion` points at one version.
- Serving loads `models:/bank-marketing@champion`.
- Registering every run fills the registry. A promotion gate (register or move the alias only if better) keeps it clean.

## Versions
Client 3.17.0 against server 3.14.0 works here. A newer client can call endpoints an older server lacks.
No exact match is required. If errors appear around `log_model` or the registry, check versions first.

## skops
MLflow 3 saves sklearn models with skops and refuses types not on its trusted list.
`HistGradientBoostingClassifier` needs `skops_trusted_types=[...]`. List only types from the error message.
Loading may need the same list. **(unverified)**

## Reloading a new champion in serving
| Method | Notes |
| --- | --- |
| Call `/reload` from the promotion step | Simple, but reaches one pod |
| MLflow webhook | Event names and 3.14 support **(unverified)**. A lost event is never retried |
| Polling the alias | Robust: compares the loaded version with the registry, so errors are temporary |
| `kubectl rollout restart` | Zero downtime, no code change |
Use polling as the base. A webhook can be added for speed.
