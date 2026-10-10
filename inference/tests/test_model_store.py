import unittest
from unittest import mock

from mlflow.exceptions import MlflowException
from mlflow.protos.databricks_pb2 import RESOURCE_DOES_NOT_EXIST

from app import model_store

LOGGER = "inference.model"


def logged(cm, text):
    return any(text in line for line in cm.output)


class Base(unittest.TestCase):
    def setUp(self):
        model_store.state.update(model=None, version=None)


class TestChampionVersion(Base):
    def _client_raising(self, exc):
        client = mock.Mock()
        client.get_model_version_by_alias.side_effect = exc
        return mock.patch.object(model_store.mlflow, "MlflowClient", return_value=client)

    def test_missing_alias_becomes_champion_not_found(self):
        exc = MlflowException("no alias", error_code=RESOURCE_DOES_NOT_EXIST)
        with self._client_raising(exc), self.assertRaises(model_store.ChampionNotFound):
            model_store._champion_version()

    def test_other_errors_pass_through(self):
        with self._client_raising(RuntimeError("connection refused")), self.assertRaises(RuntimeError):
            model_store._champion_version()


class TestReloadIfChanged(Base):
    def _patches(self, version=None, error=None):
        champion = mock.patch.object(
            model_store, "_champion_version", return_value=version, side_effect=error
        )
        loader = mock.patch.object(model_store.mlflow.sklearn, "load_model", return_value=object())
        return champion, loader

    def test_first_load_logs_found_and_loaded(self):
        champion, loader = self._patches(version="2")
        with champion, loader, self.assertLogs(LOGGER, level="INFO") as cm:
            model_store.reload_if_changed()
        self.assertTrue(logged(cm, "event=champion_found"))
        self.assertTrue(logged(cm, "event=model_loaded"))
        self.assertEqual(model_store.state["version"], "2")

    def test_new_champion_logs_old_and_new_version(self):
        model_store.state.update(model=object(), version="3")
        champion, loader = self._patches(version="4")
        with champion, loader, self.assertLogs(LOGGER, level="INFO") as cm:
            model_store.reload_if_changed()
        self.assertTrue(logged(cm, "event=model_changed"))
        self.assertTrue(logged(cm, "from_version=3 to_version=4"))
        self.assertEqual(model_store.state["version"], "4")

    def test_unchanged_champion_is_silent_at_info(self):
        model_store.state.update(model=object(), version="3")
        champion, loader = self._patches(version="3")
        with champion, loader as load, self.assertNoLogs(LOGGER, level="INFO"):
            model_store.reload_if_changed()
        load.assert_not_called()

    def test_missing_champion_warns_and_keeps_model(self):
        model = object()
        model_store.state.update(model=model, version="3")
        champion, loader = self._patches(error=model_store.ChampionNotFound("gone"))
        with champion, loader, self.assertLogs(LOGGER, level="WARNING") as cm:
            model_store.reload_if_changed()
        self.assertTrue(logged(cm, "event=champion_missing"))
        self.assertTrue(logged(cm, "keeping_version=3"))
        self.assertIs(model_store.state["model"], model)

    def test_unreachable_registry_logs_error_and_keeps_model(self):
        model_store.state.update(model=object(), version="3")
        champion, loader = self._patches(error=RuntimeError("connection refused"))
        with champion, loader, self.assertLogs(LOGGER, level="ERROR") as cm:
            model_store.reload_if_changed()
        self.assertTrue(logged(cm, "event=registry_unreachable"))
        self.assertEqual(model_store.state["version"], "3")

    def test_failed_load_keeps_the_old_version(self):
        model = object()
        model_store.state.update(model=model, version="3")
        champion = mock.patch.object(model_store, "_champion_version", return_value="4")
        loader = mock.patch.object(model_store.mlflow.sklearn, "load_model", side_effect=RuntimeError("bad file"))
        with champion, loader, self.assertLogs(LOGGER, level="ERROR") as cm:
            model_store.reload_if_changed()
        self.assertTrue(logged(cm, "event=model_load_failed"))
        self.assertEqual(model_store.state["version"], "3")
        self.assertIs(model_store.state["model"], model)


if __name__ == "__main__":
    unittest.main()
