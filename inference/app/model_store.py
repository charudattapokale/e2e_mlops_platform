import logging
import os
import threading
import time

import mlflow
import mlflow.sklearn
from mlflow.exceptions import MlflowException

log = logging.getLogger("inference.model")

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "bank-marketing")
MODEL_ALIAS = os.getenv("MODEL_ALIAS", "champion")

state = {"model": None, "version": None}
_reload_lock = threading.Lock()


class ChampionNotFound(Exception):
    """The alias does not point at any model version yet."""


def _champion_version():
    """Ask the registry which version the alias points at. Callers decide how to log the outcome."""
    mlflow.set_tracking_uri(TRACKING_URI)
    try:
        return mlflow.MlflowClient().get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS).version
    except MlflowException as exc:
        if getattr(exc, "error_code", "") == "RESOURCE_DOES_NOT_EXIST":
            raise ChampionNotFound(f"alias {MODEL_ALIAS!r} not found for model {MODEL_NAME!r}") from exc
        raise


def _load_version(version):
    """Load one specific version. State changes only after the load succeeded."""
    log.info("event=champion_found model=%s alias=%s version=%s", MODEL_NAME, MODEL_ALIAS, version)
    started = time.perf_counter()
    model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}/{version}")
    seconds = time.perf_counter() - started

    previous = state["version"]
    state.update(model=model, version=version)

    if previous is None:
        log.info("event=model_loaded model=%s version=%s load_seconds=%.2f", MODEL_NAME, version, seconds)
    elif previous == version:
        log.info("event=model_reloaded model=%s version=%s load_seconds=%.2f", MODEL_NAME, version, seconds)
    else:
        log.info(
            "event=model_changed model=%s from_version=%s to_version=%s load_seconds=%.2f",
            MODEL_NAME, previous, version, seconds,
        )


def load_champion():
    """Load whatever the alias points at now. Raises ChampionNotFound if there is no champion."""
    _load_version(_champion_version())


def load_champion_or_fail():
    """Startup load. Retries connection problems briefly, never retries a missing champion."""
    attempts = int(os.getenv("STARTUP_LOAD_ATTEMPTS", "5"))
    delay = float(os.getenv("STARTUP_RETRY_SECONDS", "3"))
    for attempt in range(1, attempts + 1):
        try:
            load_champion()
            return
        except ChampionNotFound:
            raise
        except Exception as exc:
            if attempt == attempts:
                raise
            log.warning(
                "event=startup_load_retry attempt=%d of=%d wait_seconds=%.0f error=%s",
                attempt, attempts, delay, exc,
            )
            time.sleep(delay)


def reload_if_changed():
    """Used by the webhook (and later polling). Never raises: a failure keeps the current model."""
    with _reload_lock:
        current = state["version"]
        try:
            version = _champion_version()
        except ChampionNotFound:
            log.warning(
                "event=champion_missing model=%s alias=%s keeping_version=%s",
                MODEL_NAME, MODEL_ALIAS, current,
            )
            return
        except Exception:
            log.exception(
                "event=registry_unreachable model=%s alias=%s keeping_version=%s",
                MODEL_NAME, MODEL_ALIAS, current,
            )
            return

        if version == current:
            log.debug("event=champion_unchanged model=%s version=%s", MODEL_NAME, version)
            return

        try:
            _load_version(version)
        except Exception:
            log.exception(
                "event=model_load_failed model=%s version=%s keeping_version=%s",
                MODEL_NAME, version, current,
            )
