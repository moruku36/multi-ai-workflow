"""Qualify the extracted engine against the existing in-memory Hub contract."""
import time
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

from check_central_review_hub import BASE, ENV, HEAD, NOW, TARGET, Harness
from check_one_shot_integration import payload, target_ready
import _central_review_hub_engine as engine
import _central_review_hub_support as support


class GitHubPaginationTests(unittest.TestCase):
    def test_link_relations(self):
        cases = (
            ("", False),
            ('<https://example.invalid/?page=2>; rel="next", '
             '<https://example.invalid/?page=3>; rel="last"', True),
            ('<https://example.invalid/?page=1>; rel="first", '
             '<https://example.invalid/?page=2>; rel="prev"', False),
            ('<https://example.invalid/?label=rel="next">; rel="last"', False),
            ('<https://example.invalid/>; rel="unsupported"', None),
            ('<https://example.invalid/>; rel="next", '
             '<https://example.invalid/?page=3>; rel="next"', None),
            ('<' + 'x' * 4096 + '>; rel="last"', None),
        )
        path = "/example?page=1"
        for link, expected in cases:
            with self.subTest(link=link[:100]):
                response = Mock(status=200)
                response.getheader.return_value = link
                response.read1.side_effect = [b"{}", b""]
                connection = Mock(sock=None)
                connection.getresponse.return_value = response
                with patch.object(engine, "token", return_value="fixture"), patch.object(
                    engine.http.client, "HTTPSConnection", return_value=connection
                ):
                    api = engine.GitHub(support.load_config()["limits"], time.monotonic() + 5)
                    if expected is None:
                        with self.assertRaises(support.Blocked):
                            api("GET", path)
                        response.read1.assert_not_called()
                    else:
                        self.assertEqual(api("GET", path), ({}, expected))
                    self.assertEqual(connection.request.call_args.args[:2], ("GET", path))
                    connection.close.assert_called_once_with()

    def test_counted_pages_require_the_complete_collection(self):
        path = "/example?filter=all"
        first = [{"id": identity} for identity in range(1, 51)]
        final = [{"id": 51}]
        api = Mock(side_effect=[
            ({"total_count": 51, "rows": first}, True),
            ({"total_count": 51, "rows": final}, False),
        ])
        self.assertEqual(support.pages(api, path, "rows", 60), first + final)
        self.assertEqual([call.args[1] for call in api.call_args_list],
                         [path + "&per_page=50&page=1", path + "&per_page=50&page=2"])

        incomplete = Mock(return_value=({"total_count": 51, "rows": first}, False))
        with self.assertRaises(support.Blocked):
            support.pages(incomplete, path, "rows", 60)
        incomplete.assert_called_once_with("GET", path + "&per_page=50&page=1")


class CentralHubEngineTests(unittest.TestCase):
    def controller(self, harness):
        config = support.load_config()
        config.update(enabled=True, paid_execution_authorized=True)
        return engine.Hub(config, api=harness.api, sources=harness.sources,
                          lanes=harness.lanes, preflight=harness.preflight,
                          now=lambda: NOW)

    def assert_one_shot_reads(self, api_calls, *, require_detail):
        detail = f"/repos/{TARGET}/pulls/1"
        paths = [urlsplit(call.args[1]).path for call in api_calls if call.args[0] == "GET"]
        self.assertNotIn("/installation/repositories", paths)
        self.assertTrue(all(path == detail for path in paths
                            if path.startswith("/repos/") and "/pulls" in path))
        if require_detail:
            self.assertIn(detail, paths)

    def test_scheduled_run_completes_one_reservation(self):
        harness = Harness(self)
        result = self.controller(harness).run(ENV)
        self.assertEqual(result, {"status": "COMPLETE", "reservations": 1,
                                  "completed": 1, "failed_or_unknown": 0})
        harness.preflight.assert_called_once_with()
        harness.sources.assert_called_once_with(TARGET, BASE, HEAD)
        self.assertEqual([call.args[0] for call in harness.lanes.call_args_list],
                         list(support.LANES))
        self.assertEqual(len(harness.ledger()), 1)
        self.assertEqual(len(harness.receipts()), 1)
        self.assertFalse(harness.memory.unread_writes)

    def test_prepared_one_shot_uses_exact_detail_and_blocks_replay(self):
        modes = (("shipping", Harness.controller), ("shadow", self.controller))
        for mode, make_controller in modes:
            with self.subTest(mode=mode):
                self.check_prepared_one_shot(make_controller)

    def check_prepared_one_shot(self, make_controller):
        harness = target_ready(self)
        controller = make_controller(harness)
        envelope = b"fixture-envelope"
        authorization_deadline = time.monotonic() + 60
        expected_deadline = min(controller.deadline, authorization_deadline)

        def lane(name, binary, diff, snapshots, *, attempt_cap, attempt_deadline):
            self.assertEqual(attempt_cap, 1)
            self.assertEqual(attempt_deadline, expected_deadline)
            self.assertGreater(attempt_deadline, time.monotonic())
            return harness.lane(name, binary, diff, snapshots)

        harness.lanes.side_effect = lane
        with patch.object(controller, "prepare_one_shot",
                          return_value=(payload(), authorization_deadline)) as prepare:
            result = controller.run_one_shot(envelope)
        prepare.assert_called_once_with(envelope)
        self.assertEqual(result, {"status": "COMPLETE", "reservations": 1,
                                  "completed": 1, "failed_or_unknown": 0})
        self.assertEqual([call.args[0] for call in harness.lanes.call_args_list],
                         list(support.LANES))
        harness.sources.assert_called_once_with(TARGET, BASE, HEAD)
        self.assert_one_shot_reads(harness.api.call_args_list, require_detail=True)
        self.assertFalse(harness.memory.unread_writes)

        first_call_count = harness.api.call_count
        replay = make_controller(harness)
        with patch.object(replay, "prepare_one_shot",
                          return_value=(payload(), authorization_deadline)) as prepare:
            repeated = replay.run_one_shot(envelope)
        prepare.assert_called_once_with(envelope)
        self.assertEqual(repeated["status"], "BLOCKED_OR_UNKNOWN")
        self.assertEqual(repeated["reservations"], 0)
        self.assertEqual(repeated["completed"], 0)
        replay_calls = harness.api.call_args_list[first_call_count:]
        self.assert_one_shot_reads(replay_calls, require_detail=False)
        self.assertTrue(all(call.args[0] == "GET" for call in replay_calls))
        self.assertEqual(harness.lanes.call_count, len(support.LANES))
        harness.sources.assert_called_once_with(TARGET, BASE, HEAD)
        self.assertEqual(len(harness.ledger()), 1)
        self.assertEqual(len(harness.receipts()), 1)

        scheduled = make_controller(harness).run(ENV)
        self.assertEqual(scheduled["reservations"], 0)
        self.assertEqual(harness.lanes.call_count, len(support.LANES))

    def test_durable_ledger_lost_ack_blocks_and_consumes_reservation(self):
        harness = Harness(self)
        ledger_path = f"/repos/{support.HUB}/check-runs"

        def lost_ack(method, path, data=None):
            result = harness.memory(method, path, data)
            if method == "POST" and path == ledger_path:
                raise TimeoutError("fixture lost acknowledgment after persisted write")
            return result

        harness.api.side_effect = lost_ack
        result = self.controller(harness).run(ENV)
        self.assertEqual(result["status"], "BLOCKED_OR_UNKNOWN")
        self.assertEqual(result["completed"], 0)
        self.assertEqual(len(harness.ledger()), 1)
        self.assertEqual(harness.receipts(), [])
        harness.sources.assert_not_called()
        harness.lanes.assert_not_called()

        harness.api.side_effect = harness.memory
        replay = self.controller(harness).run(ENV)
        self.assertEqual(replay["reservations"], 0)
        self.assertEqual(replay["completed"], 0)
        writes = [call.args[:2] for call in harness.api.call_args_list
                  if call.args[0] in ("POST", "PATCH")]
        self.assertEqual(writes, [("POST", ledger_path)])
        self.assertEqual(len(harness.ledger()), 1)
        self.assertEqual(harness.receipts(), [])
        harness.sources.assert_not_called()
        harness.lanes.assert_not_called()


if __name__ == "__main__":
    unittest.main()
