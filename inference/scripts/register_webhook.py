"""Register the MLflow webhook that tells the API to reload on a new champion.

Safe to run repeatedly: it only creates the webhook if one with this name is missing.
"""
import os

import mlflow

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
WEBHOOK_URL = os.getenv(
    "WEBHOOK_URL", "http://inference.serving.svc.cluster.local/webhook/mlflow"
)
SECRET = os.getenv("WEBHOOK_SECRET")
NAME = "champion-reload"

mlflow.set_tracking_uri(TRACKING_URI)
client = mlflow.MlflowClient()

existing = [w for w in client.list_webhooks() if w.name == NAME]
if existing:
    print(f"webhook {NAME!r} already exists, nothing to do")
else:
    kwargs = dict(
        name=NAME,
        url=WEBHOOK_URL,
        events=["model_version_alias.created"],
        description="Reload the serving model when an alias is set",
    )
    if SECRET:
        kwargs["secret"] = SECRET
    client.create_webhook(**kwargs)
    print(f"created webhook {NAME!r} -> {WEBHOOK_URL}")
