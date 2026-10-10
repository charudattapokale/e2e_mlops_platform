import unittest
from unittest import mock

from fastapi.testclient import TestClient

from app import main, webhook


class TestWebhookLogging(unittest.TestCase):
    def test_payload_is_logged_and_signature_is_hidden(self):
        client = TestClient(main.app)
        with mock.patch.object(webhook, "reload_if_changed"), \
             self.assertLogs("inference.webhook", level="INFO") as cm:
            client.post(
                "/webhook/mlflow",
                json={"entity": "model_version_alias", "action": "created"},
                headers={"X-MLflow-Signature": "v1,secretvalue"},
            )
        text = "\n".join(cm.output)
        self.assertIn("event=webhook_received", text)
        self.assertIn("model_version_alias", text)
        self.assertNotIn("secretvalue", text)


if __name__ == "__main__":
    unittest.main()
