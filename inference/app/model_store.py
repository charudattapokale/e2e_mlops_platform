import logging
import os
import threading

import mlflow
import mlflow.sklearn

log = logging.getLogger("inference")

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "bank-marketing")
MODEL_ALIAS = os.getenv("MODEL_ALIAS", "champion")

state = {"model": None, "version": None}
_reload_lock = threading.Lock()


def load_champion():
    """Load the model the champion alias points at right now."""
    mlflow.set_tracking_uri(TRACKING_URI)
    version = mlflow.MlflowClient().get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS).version
    # Load by version number, not by alias: the alias could move between the two calls.
    model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}/{version}")
    state["model"] = model
    state["version"] = version
    log.info("Loaded %s version %s", MODEL_NAME, version)


def reload_if_changed():
    """Reload only if the alias points at a different version. A failure keeps the current model."""
    with _reload_lock:
        try:
            mlflow.set_tracking_uri(TRACKING_URI)
            current = mlflow.MlflowClient().get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS).version
            if current != state["version"]:
                load_champion()
        except Exception:
            log.exception("reload failed, keeping the model that is loaded now")
