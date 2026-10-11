import importlib
import os
import unittest
from unittest import mock

import pandas as pd


def reload_train(env=None):
    """Import train.py fresh, with the given environment variables set."""
    with mock.patch.dict(os.environ, env or {}, clear=False):
        import train

        return importlib.reload(train)


class TestParams(unittest.TestCase):
    def test_defaults(self):
        train = reload_train()
        self.assertEqual(train.PARAMS["learning_rate"], 0.1)
        self.assertEqual(train.PARAMS["max_iter"], 200)
        self.assertEqual(train.PARAMS["max_depth"], 6)
        self.assertEqual(train.PARAMS["random_state"], 42)

    def test_env_overrides(self):
        train = reload_train(
            {"LEARNING_RATE": "0.05", "MAX_ITER": "50", "MAX_DEPTH": "3"}
        )
        self.assertEqual(train.PARAMS["learning_rate"], 0.05)
        self.assertEqual(train.PARAMS["max_iter"], 50)
        self.assertEqual(train.PARAMS["max_depth"], 3)

    def test_tracking_settings_from_env(self):
        train = reload_train(
            {
                "MLFLOW_TRACKING_URI": "http://mlflow.mlops.svc.cluster.local",
                "MLFLOW_EXPERIMENT": "my-experiment",
            }
        )
        self.assertEqual(
            train.TRACKING_URI, "http://mlflow.mlops.svc.cluster.local"
        )
        self.assertEqual(train.EXPERIMENT, "my-experiment")


class TestMain(unittest.TestCase):
    """Run main() end to end on a tiny fake dataset, with MLflow mocked."""

    def fake_dataset(self):
        n = 200
        X = pd.DataFrame(
            {
                "age": range(n),
                "job": pd.Categorical(["a", "b"] * (n // 2)),
            }
        )
        y = pd.Series(["1", "2"] * (n // 2), name="Class")
        return mock.Mock(data=X, target=y)

    def test_main_logs_params_metrics_and_model(self):
        train = reload_train({"MAX_ITER": "5"})
        with mock.patch.object(
            train, "fetch_openml", return_value=self.fake_dataset()
        ), mock.patch.object(train, "mlflow") as fake_mlflow:
            train.main()

        fake_mlflow.set_tracking_uri.assert_called_once_with(train.TRACKING_URI)
        fake_mlflow.set_experiment.assert_called_once_with(train.EXPERIMENT)
        fake_mlflow.log_params.assert_called_once()

        logged = fake_mlflow.log_metrics.call_args[0][0]
        self.assertEqual(set(logged), {"roc_auc", "pr_auc", "f1"})
        for value in logged.values():
            self.assertTrue(0.0 <= value <= 1.0)

        fake_mlflow.sklearn.log_model.assert_called_once()
        kwargs = fake_mlflow.sklearn.log_model.call_args.kwargs
        self.assertNotIn("registered_model_name", kwargs)


if __name__ == "__main__":
    unittest.main()
