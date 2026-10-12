"""Promotion gate: register a candidate model and move the champion alias only if it is better.

decide() is a pure function, so the policy can be tested without MLflow. promote_if_better() holds the side effects.
Order matters for serving: the metric tag is written before any alias moves, and the previous alias is set before the
champion alias, so the webhook that fires on the champion change sees a complete version.
"""
import logging
import os
from dataclasses import dataclass

import mlflow
from mlflow.exceptions import MlflowException

log = logging.getLogger("training.promote")

CHAMPION = "champion"
PREVIOUS = "previous"
METRIC = os.getenv("PROMOTION_METRIC", "pr_auc")
MIN_DELTA = float(os.getenv("PROMOTION_MIN_DELTA", "0.002"))


@dataclass(frozen=True)
class Decision:
    promote: bool
    reason: str


def decide(candidate, champion, min_delta):
    """champion is None when there is nothing to beat."""
    if champion is None:
        return Decision(True, "no_champion")
    if candidate >= champion + min_delta:
        return Decision(True, "improved")
    return Decision(False, "not_better")


def current_champion(client, model_name):
    """The model version behind the champion alias, or None if there is none.

    MLflow reports a missing alias as INVALID_PARAMETER_VALUE, a code it also uses for bad input,
    so ask which aliases exist instead of trusting the error code.
    """
    try:
        return client.get_model_version_by_alias(model_name, CHAMPION)
    except MlflowException:
        try:
            aliases = client.get_registered_model(model_name).aliases
        except MlflowException as exc:
            if getattr(exc, "error_code", "") == "RESOURCE_DOES_NOT_EXIST":
                return None
            raise
        if CHAMPION not in aliases:
            return None
        raise


def champion_metric(client, version):
    """The champion's metric: the version tag written at promotion time, else the source run's metric."""
    tagged = (version.tags or {}).get(METRIC)
    if tagged is not None:
        return float(tagged)
    if getattr(version, "run_id", None):
        try:
            value = client.get_run(version.run_id).data.metrics.get(METRIC)
        except MlflowException:
            return None
        if value is not None:
            return float(value)
    return None


def promote_if_better(*, run_id, model_uri, metric_value, model_name, client=None, min_delta=None):
    client = client or mlflow.MlflowClient()
    min_delta = MIN_DELTA if min_delta is None else min_delta

    champion = current_champion(client, model_name)
    champion_value = champion_metric(client, champion) if champion is not None else None

    if champion is not None and champion_value is None:
        decision = Decision(False, "champion_metric_unknown")
    else:
        decision = decide(metric_value, champion_value, min_delta)

    log.info(
        "event=promotion_decision decision=%s reason=%s metric=%s candidate=%.4f champion_version=%s champion=%s min_delta=%s",
        "promote" if decision.promote else "reject", decision.reason, METRIC, metric_value,
        champion.version if champion is not None else None, champion_value, min_delta,
    )

    client.set_tag(run_id, "promotion", "promoted" if decision.promote else "rejected")
    client.set_tag(run_id, "promotion_reason", decision.reason)
    if champion is not None:
        client.set_tag(run_id, "champion_version_at_decision", str(champion.version))

    if not decision.promote:
        if decision.reason == "champion_metric_unknown":
            log.warning(
                "event=promotion_blocked reason=champion_metric_unknown champion_version=%s fix=\"set the %s tag on that model version\"",
                champion.version, METRIC,
            )
        return decision

    version = mlflow.register_model(model_uri, model_name)
    new_version = str(version.version)

    client.set_model_version_tag(model_name, new_version, METRIC, repr(float(metric_value)))
    client.set_model_version_tag(model_name, new_version, "source_run_id", run_id)
    if champion is not None:
        client.set_registered_model_alias(model_name, PREVIOUS, champion.version)
    client.set_registered_model_alias(model_name, CHAMPION, new_version)
    client.set_tag(run_id, "registered_version", new_version)

    log.info(
        "event=promoted model=%s version=%s previous_version=%s",
        model_name, new_version, champion.version if champion is not None else None,
    )
    return decision
