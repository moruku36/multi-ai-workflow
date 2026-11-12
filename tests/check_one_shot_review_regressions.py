#!/usr/bin/env python3
"""Three focused offline scenarios; authored, UNEXECUTED.
No parameterized subcases, crypto subprocesses, target execution or network.
"""
from datetime import timedelta
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import automatic_dual_review as auto
import central_one_shot_auth as auth
import central_review_hub as hub
from check_central_review_hub import NOW, BASE, HEAD, TARGET
from check_one_shot_integration import REVISION, payload, target_ready


def validate(request, *, started=100.0):
    return auth.validate_payload(request, REVISION, NOW,
                                 validation_started=started, deadline=1000.0)


def run_target(controller, request, frozen_deadline):
    since = hub.utc(request["eligible_since"])
    return controller._run_targets(
        [(since, TARGET, 1, BASE, HEAD)], since, Path("/offline/opencodereview"),
        authorization=request, authorization_deadline=frozen_deadline)


class OneShotReviewRegressions(unittest.TestCase):
    def test_frozen_deadline_survives_delay_and_clock_rollback(self):
        request = payload()
        request["expires_at"] = "2030-01-02T12:00:10Z"
        clock = {"mono": 100.0, "utc": NOW}
        with patch.object(hub.time, "monotonic", side_effect=lambda: clock["mono"]):
            frozen = validate(request, started=clock["mono"])
            self.assertEqual(frozen, 110.0)
            # Verification/preflight consumes five seconds; UTC then rolls back.
            clock.update(mono=105.0, utc=NOW - timedelta(seconds=60))
            h = target_ready(self)
            controller = h.controller()
            controller.now = lambda: clock["utc"]

            def lane(name, binary, diff, snapshots, *, attempt_cap, attempt_deadline):
                self.assertEqual(name, "alibaba")
                self.assertEqual(attempt_deadline, frozen)
                sender = auto.BoundedReviewRelay(
                    live=True, api_key="offline-test-only", attempt_cap=attempt_cap,
                    attempt_deadline=attempt_deadline)
                sender._forward(b"{}")
                self.assertEqual(sender.payload_budget.attempts, 1)
                # Even with UTC still active, the original bound must stop lane2.
                clock.update(mono=frozen, utc=NOW - timedelta(seconds=120))
                return h.lane(name, binary, diff, snapshots)

            h.lanes.side_effect = lane
            with patch.object(auto.connection.Relay, "_forward", return_value=b"offline") as upstream:
                result = run_target(controller, request, frozen)
                self.assertEqual(result["status"], "BLOCKED_OR_UNKNOWN")
                self.assertEqual(result["reservations"], 1)
                self.assertEqual(h.lanes.call_count, 1)
                self.assertEqual(upstream.call_count, 1)
                self.assertEqual(len(h.ledger()), 1)
                self.assertEqual(len(h.receipts()), 1)

    def test_signed_lane_caps_reject_zero_before_reservations(self):
        request = payload()
        request["lane_attempt_limits"]["alibaba"] = 0
        with patch.object(hub.time, "monotonic", return_value=100.0):
            with self.assertRaises(auth.Blocked):
                validate(request)
            h = target_ready(self)
            result = run_target(h.controller(), request, 1000.0)
            self.assertEqual(result["status"], "BLOCKED_OR_UNKNOWN")
            self.assertEqual(result["reservations"], 0)
            h.api.assert_not_called()
            h.sources.assert_not_called()
            h.lanes.assert_not_called()

    def test_total_authorization_window_is_positive_and_at_most_one_hour(self):
        request = payload()
        request.update(eligible_since="2030-01-02T11:00:00Z",
                       expires_at="2030-01-02T12:00:01Z")
        # One second remains, but the signed total interval is 3601 seconds.
        with patch.object(hub.time, "monotonic", return_value=100.0):
            with self.assertRaises(auth.Blocked):
                validate(request)
            h = target_ready(self)
            result = run_target(h.controller(), request, 1000.0)
            self.assertEqual(result["status"], "BLOCKED_OR_UNKNOWN")
            self.assertEqual(result["reservations"], 0)
            h.api.assert_not_called()
            h.sources.assert_not_called()
            h.lanes.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=1)
