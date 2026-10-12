import importlib
import os
import unittest
from unittest import mock

import pandas as pd


def fake_dataset():
    n = 200
    X = pd.DataFrame({"age": range(n), "job": pd.Categorical(["a", "b"] * (n // 2))})
    y = pd.Series(["1", "2"] * (n // 2), name="Class")
    return mock.Mock(data=X, target=y)


class TestPromotionHook(unittest.TestCase):
    def run_main(self, promote_value):
        with mock.patch.dict(os.environ, {"MAX_ITER": "5"}):
            os.environ.pop("PROMOTE", None)
            if promote_value is not None:
                os.environ["PROMOTE"] = promote_value
            import train
            train = importlib.reload(train)
            with mock.patch.object(train, "fetch_openml", return_value=fake_dataset()), \
                 mock.patch.object(train, "mlflow"), \
                 mock.patch.object(train, "promote_if_better") as gate:
                train.main()
        return train, gate

    def test_gate_is_called_when_promote_is_true(self):
        train, gate = self.run_main("true")
        gate.assert_called_once()
        kwargs = gate.call_args.kwargs
        self.assertEqual(kwargs["model_name"], train.MODEL_NAME)
        self.assertTrue(0.0 <= kwargs["metric_value"] <= 1.0)

    def test_the_switch_ignores_case(self):
        _, gate = self.run_main("TRUE")
        gate.assert_called_once()

    def test_gate_is_skipped_by_default(self):
        _, gate = self.run_main(None)
        gate.assert_not_called()

    def test_gate_is_skipped_when_promote_is_false_or_empty(self):
        for value in ("false", ""):
            _, gate = self.run_main(value)
            gate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
