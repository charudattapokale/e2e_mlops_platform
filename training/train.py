import logging
import os

import mlflow
import mlflow.sklearn
from sklearn.datasets import fetch_openml
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

from promote import METRIC, promote_if_better

TRAINING_VERSION = "0.3.0"
log = logging.getLogger("training")

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "bank-marketing")
MODEL_NAME = "bank-marketing"

PARAMS = {
    "learning_rate": float(os.getenv("LEARNING_RATE", "0.1")),
    "max_iter": int(os.getenv("MAX_ITER", "200")),
    "max_depth": int(os.getenv("MAX_DEPTH", "6")),
    "random_state": 42,
}


def should_promote():
    """Off by default, so local runs and unit tests never touch the registry. The training Job turns it on."""
    return os.getenv("PROMOTE", "false").lower() == "true"


def main():
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)-7s %(name)s %(message)s")
    log.info(
        "event=training_started version=%s image=%s experiment=%s params=%s promote=%s",
        TRAINING_VERSION, os.getenv("IMAGE_REF", "unknown"), EXPERIMENT, PARAMS, should_promote(),
    )
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)

    # Bank marketing (OpenML id 1461): will the client subscribe to a term deposit?
    data = fetch_openml(data_id=1461, as_frame=True)
    X = data.data
    y = (data.target.astype(str) == "2").astype(int)  # class 2 = subscribed

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    with mlflow.start_run() as run:
        mlflow.log_params(PARAMS)
        mlflow.log_param("n_train", len(X_train))

        model = HistGradientBoostingClassifier(
            categorical_features="from_dtype", **PARAMS
        )
        model.fit(X_train, y_train)

        proba = model.predict_proba(X_test)[:, 1]
        metrics = {
            "roc_auc": roc_auc_score(y_test, proba),
            "pr_auc": average_precision_score(y_test, proba),
            "f1": f1_score(y_test, proba > 0.5),
        }
        mlflow.log_metrics(metrics)

        # Logged to the run, not registered: registering is the promotion gate's decision
        model_info = mlflow.sklearn.log_model(
            model,
            name="model",
            skops_trusted_types=[
                "sklearn.ensemble._hist_gradient_boosting.predictor.TreePredictor",
                "functools.partial",
                "sklearn.utils.validation.check_array",
            ],
        )
        log.info(
            "event=training_finished run_id=%s model_id=%s %s=%.4f",
            run.info.run_id, model_info.model_id, METRIC, metrics[METRIC],
        )

        if should_promote():
            promote_if_better(
                run_id=run.info.run_id,
                model_uri=model_info.model_uri,
                metric_value=metrics[METRIC],
                model_name=MODEL_NAME,
            )
        else:
            log.info("event=promotion_skipped reason=PROMOTE_is_not_true")


if __name__ == "__main__":
    main()
