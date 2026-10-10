import unittest
from unittest import mock

from fastapi.testclient import TestClient

from app import main, model_store


class TestStartup(unittest.TestCase):
    def test_refuses_to_start_without_champion(self):
        err = model_store.ChampionNotFound("none")
        with mock.patch.object(main, "load_champion_or_fail", side_effect=err):
            with self.assertRaises(RuntimeError):
                with TestClient(main.app):
                    pass

    def test_refuses_to_start_when_registry_is_down(self):
        with mock.patch.object(main, "load_champion_or_fail", side_effect=ConnectionError("down")):
            with self.assertRaises(RuntimeError):
                with TestClient(main.app):
                    pass

    def test_starts_when_the_model_loads(self):
        with mock.patch.object(main, "load_champion_or_fail"):
            with TestClient(main.app) as client:
                self.assertEqual(client.get("/health").status_code, 200)


class TestStartupRetry(unittest.TestCase):
    def test_retries_connection_errors_then_succeeds(self):
        with mock.patch.object(model_store, "load_champion", side_effect=[ConnectionError("x"), None]) as load, \
             mock.patch.object(model_store.time, "sleep") as sleep:
            model_store.load_champion_or_fail()
        self.assertEqual(load.call_count, 2)
        sleep.assert_called_once()

    def test_does_not_retry_a_missing_champion(self):
        err = model_store.ChampionNotFound("none")
        with mock.patch.object(model_store, "load_champion", side_effect=err) as load, \
             mock.patch.object(model_store.time, "sleep") as sleep:
            with self.assertRaises(model_store.ChampionNotFound):
                model_store.load_champion_or_fail()
        load.assert_called_once()
        sleep.assert_not_called()

    def test_gives_up_after_the_last_attempt(self):
        with mock.patch.dict("os.environ", {"STARTUP_LOAD_ATTEMPTS": "3"}), \
             mock.patch.object(model_store, "load_champion", side_effect=ConnectionError("x")) as load, \
             mock.patch.object(model_store.time, "sleep"):
            with self.assertRaises(ConnectionError):
                model_store.load_champion_or_fail()
        self.assertEqual(load.call_count, 3)


if __name__ == "__main__":
    unittest.main()
