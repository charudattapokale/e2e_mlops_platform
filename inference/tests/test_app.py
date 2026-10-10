import unittest
from unittest import mock

import numpy as np

from fastapi.testclient import TestClient

from app import main

SAMPLE = {
    "age": 40, "job": "blue-collar", "marital": "married", "education": "primary",
    "default": "no", "balance": 640, "housing": "yes", "loan": "no",
    "contact": "unknown", "day": 8, "month": "may", "duration": 347,
    "campaign": 2, "pdays": -1, "previous": 0, "poutcome": "unknown",
}


class FakeModel:
    def predict_proba(self, frame):
        assert list(frame.columns) == [f"V{i}" for i in range(1, 17)]
        return np.array([[0.3, 0.7]])


class TestApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        main.state.update(model=None, version=None)

    def test_health_without_model(self):
        r = self.client.get("/health")
        self.assertEqual(r.json(), {"status": "ok", "model_loaded": False})

    def test_predict_without_model_is_503(self):
        self.assertEqual(self.client.post("/predict", json=SAMPLE).status_code, 503)

    def test_predict_with_model(self):
        main.state.update(model=FakeModel(), version="3")
        r = self.client.post("/predict", json=SAMPLE)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["prediction"], 1)
        self.assertAlmostEqual(body["probability"], 0.7)
        self.assertEqual(body["model_version"], "3")

    def test_invalid_input_is_422(self):
        bad = dict(SAMPLE, age="not a number")
        self.assertEqual(self.client.post("/predict", json=bad).status_code, 422)

    def test_reload_failure_is_503(self):
        with mock.patch.object(main, "load_champion", side_effect=RuntimeError("x")):
            self.assertEqual(self.client.post("/reload").status_code, 503)


if __name__ == "__main__":
    unittest.main()
