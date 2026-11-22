import json
import re
import unittest
from urllib.parse import urlsplit

from check_central_review_hub import BASE, ENV, HEAD, NOW, TARGET, Harness, pull
import _central_review_hub_engine as hub
import _central_review_hub_support as support


def shadow_controller(harness):
    config = support.load_config()
    config.update(enabled=True, paid_execution_authorized=True)
    return hub.Hub(config, api=harness.api, sources=harness.sources, lanes=harness.lanes,
                   preflight=harness.preflight, now=lambda: NOW)


class CentralHubReadbackCases(unittest.TestCase):
    def assertSafeSummary(self, summary):
        text = json.dumps(summary, sort_keys=True)
        for forbidden in (TARGET, hub.OWNER, HEAD, BASE, "secret", "Bearer"):
            self.assertNotIn(forbidden, text)

    def test_lost_ledger_post_acknowledgment_stops_without_retry(self):
        h, calls = Harness(self), []

        def api(method, path, payload=None):
            calls.append((method, urlsplit(path).path))
            result = h.memory(method, path, payload)
            if method == "POST" and payload["name"] == hub.LEDGER:
                raise TimeoutError("Bearer secret-token " + TARGET)
            return result

        h.api.side_effect = api
        summary = shadow_controller(h).run(ENV)
        self.assertEqual(summary["status"], "BLOCKED_OR_UNKNOWN")
        self.assertEqual(summary["check_write_failure"], {
            "kind": "ledger", "phase": "post_ack", "category": "unavailable"})
        self.assertEqual(len(h.ledger()), 1)
        self.assertEqual(calls[-1], ("POST", "/repos/" + hub.HUB + "/check-runs"))
        self.assertEqual(calls.count(calls[-1]), 1)
        self.assertFalse([c for c in calls if re.search(r"/check-runs/[0-9]+$", c[1])
                          and c[1].startswith("/repos/" + hub.HUB)])
        self.assertEqual(h.receipts(), [])
        h.sources.assert_not_called()
        h.lanes.assert_not_called()
        self.assertSafeSummary(summary)

    def test_receipt_readback_failure_reports_status_and_stops(self):
        h, calls = Harness(self), []
        h.memory.pulls[TARGET].append(pull(2, head="c" * 40))

        def api(method, path, payload=None):
            route = urlsplit(path).path
            calls.append((method, route))
            detail = re.fullmatch(r"/repos/([^/]+/[^/]+)/check-runs/([0-9]+)", route)
            if method == "GET" and detail and h.memory.checks[
                    detail.group(1), int(detail.group(2))]["name"] == hub.RECEIPT:
                raise hub.HttpFailure(403)
            return h.memory(method, path, payload)

        h.api.side_effect = api
        summary = shadow_controller(h).run(ENV)
        self.assertEqual(summary["status"], "BLOCKED_OR_UNKNOWN")
        self.assertEqual(summary["check_write_failure"], {
            "kind": "receipt", "phase": "readback_fetch",
            "category": "http_status", "http_status": 403})
        self.assertEqual(len(h.ledger()), 1)
        self.assertEqual(len(h.receipts()), 1)
        self.assertEqual(sum(1 for c in calls if c[0] == "GET" and re.fullmatch(
            r"/repos/" + re.escape(TARGET) + r"/check-runs/[0-9]+", c[1])), 1)
        self.assertEqual(sum(1 for c in calls if c[0] == "POST" and c[1].endswith("/check-runs")
                             and c[1].startswith("/repos/" + TARGET)), 1)
        h.sources.assert_not_called()
        h.lanes.assert_not_called()
        self.assertSafeSummary(summary)

    def test_receipt_patch_readback_mismatch_stops_without_retry(self):
        h, calls, patched = Harness(self), [], []
        detail_route = r"/repos/" + re.escape(TARGET) + r"/check-runs/[0-9]+"

        def api(method, path, payload=None):
            route = urlsplit(path).path
            calls.append((method, route))
            result = h.memory(method, path, payload)
            if re.fullmatch(detail_route, route):
                if method == "PATCH":
                    patched.append(route)
                elif patched:
                    row = dict(result[0])
                    row["output"] = dict(row["output"], title="tampered")
                    return row, False
            return result

        h.api.side_effect = api
        summary = shadow_controller(h).run(ENV)
        self.assertEqual(summary["status"], "BLOCKED_OR_UNKNOWN")
        self.assertEqual(summary["check_write_failure"], {
            "kind": "receipt", "phase": "readback_validate", "category": "mismatch"})
        self.assertEqual(len(patched), 1)
        self.assertEqual(calls[-1], ("GET", patched[0]))
        self.assertEqual(sum(1 for c in calls if c[0] == "GET"
                             and re.fullmatch(detail_route, c[1])), 2)
        self.assertEqual(len(h.receipts()), 1)
        h.sources.assert_called_once_with(TARGET, BASE, HEAD)
        h.lanes.assert_not_called()
        self.assertSafeSummary(summary)

    def test_receipt_patch_acknowledgment_loss_stops_without_readback(self):
        h, calls = Harness(self), []
        detail_route = r"/repos/" + re.escape(TARGET) + r"/check-runs/[0-9]+"

        def api(method, path, payload=None):
            route = urlsplit(path).path
            calls.append((method, route))
            result = h.memory(method, path, payload)
            if method == "PATCH" and re.fullmatch(detail_route, route):
                raise OSError("Bearer secret-token")
            return result

        h.api.side_effect = api
        summary = shadow_controller(h).run(ENV)
        self.assertEqual(summary["status"], "BLOCKED_OR_UNKNOWN")
        self.assertEqual(summary["check_write_failure"], {
            "kind": "receipt", "phase": "patch_ack", "category": "unavailable"})
        self.assertEqual(calls[-1][0], "PATCH")
        self.assertEqual(sum(1 for c in calls if c[0] == "PATCH"
                             and re.fullmatch(detail_route, c[1])), 1)
        self.assertEqual(len(h.receipts()), 1)
        h.sources.assert_called_once_with(TARGET, BASE, HEAD)
        h.lanes.assert_not_called()
        self.assertSafeSummary(summary)


if __name__ == "__main__":
    unittest.main()
