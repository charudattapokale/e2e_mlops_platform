import unittest
from unittest import mock

from mlflow.exceptions import MlflowException
from mlflow.protos.databricks_pb2 import INVALID_PARAMETER_VALUE, RESOURCE_DOES_NOT_EXIST

import promote

LOGGER = "training.promote"


def version(number, tags=None, run_id=None):
    v = mock.Mock()
    v.version = str(number)
    v.tags = tags or {}
    v.run_id = run_id
    return v


class FakeClient:
    def __init__(self, champion=None, model_missing=False, aliases=None, run_metrics=None, run_error=None):
        self.calls = []
        self._champion = champion
        self._model_missing = model_missing
        self._aliases = aliases or {}
        self._run_metrics = run_metrics or {}
        self._run_error = run_error

    def get_model_version_by_alias(self, name, alias):
        if self._champion is None:
            raise MlflowException("alias not found", error_code=INVALID_PARAMETER_VALUE)
        return self._champion

    def get_registered_model(self, name):
        if self._model_missing:
            raise MlflowException("model not found", error_code=RESOURCE_DOES_NOT_EXIST)
        return mock.Mock(aliases=self._aliases)

    def get_run(self, run_id):
        if self._run_error:
            raise self._run_error
        return mock.Mock(data=mock.Mock(metrics=self._run_metrics))

    def set_tag(self, run_id, key, value):
        self.calls.append(("run_tag", key, value))

    def set_model_version_tag(self, name, ver, key, value):
        self.calls.append(("version_tag", ver, key, value))

    def set_registered_model_alias(self, name, alias, ver):
        self.calls.append(("alias", alias, str(ver)))

    def aliases_set(self):
        return [c for c in self.calls if c[0] == "alias"]


class TestDecide(unittest.TestCase):
    def test_no_champion_is_accepted(self):
        self.assertEqual(promote.decide(0.1, None, 0.002), promote.Decision(True, "no_champion"))

    def test_clear_improvement_is_accepted(self):
        self.assertEqual(promote.decide(0.6, 0.5, 0.002), promote.Decision(True, "improved"))

    def test_gain_below_the_margin_is_rejected(self):
        self.assertEqual(promote.decide(0.5005, 0.5, 0.002), promote.Decision(False, "not_better"))

    def test_worse_is_rejected(self):
        self.assertFalse(promote.decide(0.4, 0.5, 0.002).promote)

    def test_gain_exactly_at_the_margin_is_accepted(self):
        # binary-exact numbers, so the comparison is not blurred by float rounding
        self.assertTrue(promote.decide(0.75, 0.5, 0.25).promote)
        self.assertFalse(promote.decide(0.74, 0.5, 0.25).promote)

    def test_zero_margin_accepts_a_tie(self):
        self.assertTrue(promote.decide(0.5, 0.5, 0.0).promote)


class TestCurrentChampion(unittest.TestCase):
    def test_returns_the_version_behind_the_alias(self):
        champion = version(2)
        self.assertIs(promote.current_champion(FakeClient(champion=champion), "m"), champion)

    def test_missing_alias_on_an_existing_model_is_none(self):
        self.assertIsNone(promote.current_champion(FakeClient(), "m"))

    def test_unregistered_model_is_none(self):
        self.assertIsNone(promote.current_champion(FakeClient(model_missing=True), "m"))

    def test_a_failed_lookup_for_an_existing_alias_is_not_hidden(self):
        with self.assertRaises(MlflowException):
            promote.current_champion(FakeClient(aliases={"champion": "2"}), "m")


class TestChampionMetric(unittest.TestCase):
    def test_reads_the_version_tag(self):
        self.assertEqual(promote.champion_metric(FakeClient(), version(2, tags={"pr_auc": "0.5"})), 0.5)

    def test_falls_back_to_the_source_run(self):
        client = FakeClient(run_metrics={"pr_auc": 0.7})
        self.assertEqual(promote.champion_metric(client, version(2, run_id="r0")), 0.7)

    def test_unknown_is_none(self):
        self.assertIsNone(promote.champion_metric(FakeClient(), version(2)))

    def test_a_deleted_run_is_none(self):
        client = FakeClient(run_error=MlflowException("gone", error_code=RESOURCE_DOES_NOT_EXIST))
        self.assertIsNone(promote.champion_metric(client, version(2, run_id="r0")))


class TestPromoteIfBetter(unittest.TestCase):
    def run_gate(self, client, value=0.6):
        with mock.patch.object(promote.mlflow, "register_model", return_value=mock.Mock(version="3")) as reg:
            decision = promote.promote_if_better(
                run_id="r1", model_uri="models:/m-abc", metric_value=value,
                model_name="bank-marketing", client=client,
            )
        return decision, reg

    def test_first_model_is_registered_and_becomes_champion(self):
        client = FakeClient(model_missing=True)
        decision, reg = self.run_gate(client)
        self.assertTrue(decision.promote)
        reg.assert_called_once_with("models:/m-abc", "bank-marketing")
        self.assertEqual(client.aliases_set(), [("alias", "champion", "3")])

    def test_improvement_sets_previous_before_champion(self):
        client = FakeClient(champion=version(2, tags={"pr_auc": "0.5"}))
        decision, _ = self.run_gate(client)
        self.assertTrue(decision.promote)
        self.assertEqual(client.aliases_set(), [("alias", "previous", "2"), ("alias", "champion", "3")])

    def test_metric_tag_is_written_before_the_alias_moves(self):
        client = FakeClient(champion=version(2, tags={"pr_auc": "0.5"}))
        self.run_gate(client)
        kinds = [c[0] for c in client.calls]
        tag_at = next(i for i, c in enumerate(client.calls) if c[:3] == ("version_tag", "3", "pr_auc"))
        self.assertLess(tag_at, kinds.index("alias"))

    def test_rejection_registers_nothing(self):
        client = FakeClient(champion=version(2, tags={"pr_auc": "0.7"}))
        decision, reg = self.run_gate(client, value=0.6)
        self.assertFalse(decision.promote)
        reg.assert_not_called()
        self.assertEqual(client.aliases_set(), [])

    def test_rejection_is_tagged_with_the_reason(self):
        client = FakeClient(champion=version(2, tags={"pr_auc": "0.7"}))
        self.run_gate(client, value=0.6)
        self.assertIn(("run_tag", "promotion", "rejected"), client.calls)
        self.assertIn(("run_tag", "promotion_reason", "not_better"), client.calls)

    def test_unknown_champion_metric_blocks_and_warns(self):
        client = FakeClient(champion=version(2))
        with self.assertLogs(LOGGER, level="WARNING") as cm:
            decision, reg = self.run_gate(client)
        self.assertEqual(decision.reason, "champion_metric_unknown")
        reg.assert_not_called()
        self.assertTrue(any("event=promotion_blocked" in line for line in cm.output))

    def test_the_decision_is_logged(self):
        with self.assertLogs(LOGGER, level="INFO") as cm:
            self.run_gate(FakeClient(model_missing=True))
        text = "\n".join(cm.output)
        self.assertIn("event=promotion_decision", text)
        self.assertIn("event=promoted", text)


if __name__ == "__main__":
    unittest.main()
