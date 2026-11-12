#!/usr/bin/env python3
"""Five authored cases, UNEXECUTED. No production credentials or live providers.

The signature case uses a PUBLIC, deterministic test-only seed in a temporary
directory and the real system OpenSSL 3 verifier. Never use this seed operationally.
The other cases use in-memory APIs and patched transports, not live acceptance.
"""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import automatic_dual_review as auto
import central_one_shot_auth as auth
import central_one_shot_provenance as provenance
import central_review_hub as hub
from check_central_review_hub import Harness, NOW, ENV, BASE, HEAD, TARGET

REVISION = "c" * 40


def payload():
    return {
        "schema_version": 1, "domain": "central-review-hub/one-shot/v1",
        "issuer": "test-operator", "key_id": "test-key",
        "authorization": {"kind": "one_target_dual_review", "targets": 1,
                          "reruns": False, "refunds": False},
        "repository": TARGET, "pr": 1, "base": BASE, "head": HEAD,
        "controller_revision": REVISION, "eligible_since": "2030-01-02T11:30:00Z",
        "expires_at": "2030-01-02T12:30:00Z",
        "lane_attempt_limits": {"alibaba": 1, "cloudflare": 1},
    }


def target_ready(case):
    h = Harness(case)
    h.memory.pulls[TARGET][0]["updated_at"] = "2030-01-02T11:45:00Z"
    return h


class OneShotIntegration(unittest.TestCase):
    def test_real_signature_accepts_exact_payload_and_rejects_tampering(self):
        deadline = time.monotonic() + 25
        auth.openssl3(deadline)  # Missing OpenSSL 3 is a failure, never a silent skip.
        with tempfile.TemporaryDirectory(prefix="central-test-signature-") as directory:
            scratch = Path(directory).resolve()
            (scratch / "config").mkdir()
            # RFC 8410 PKCS#8 wrapping of a public deterministic TEST seed.
            (scratch / "test-key.der").write_bytes(
                bytes.fromhex("302e020100300506032b657004220420") + bytes(range(32)))
            public = auth.bounded_command(
                [auth.OPENSSL, "pkey", "-inform", "DER", "-in", "test-key.der",
                 "-pubout", "-outform", "DER"], cwd=scratch, deadline=deadline)
            self.assertEqual(public[:12], bytes.fromhex("302a300506032b6570032100"))
            self.assertEqual(len(public), 44)
            policy = {"schema_version": 1, "keys": [{
                "issuer": "test-operator", "key_id": "test-key", "algorithm": "Ed25519",
                "public_key": base64.b64encode(public[12:]).decode("ascii")}]}
            (scratch / "config/central-one-shot-trust.json").write_bytes(auth.canonical(policy))
            p = payload()
            (scratch / "payload").write_bytes(auth.DOMAIN + auth.canonical(p))
            auth.bounded_command(
                [auth.OPENSSL, "pkeyutl", "-sign", "-inkey", "test-key.der",
                 "-keyform", "DER", "-rawin", "-in", "payload", "-out", "signature"],
                cwd=scratch, deadline=deadline)
            signed = {"payload": p, "signature": base64.b64encode(
                (scratch / "signature").read_bytes()).decode("ascii")}
            with patch.object(auth, "ROOT", scratch):
                self.assertEqual(auth.verify_envelope(auth.canonical(signed), revision=REVISION,
                                                     now=NOW, deadline=deadline), p)
                changed = deepcopy(signed)
                changed["payload"]["head"] = "e" * 40
                with self.assertRaises(auth.Blocked):
                    auth.verify_envelope(auth.canonical(changed), revision=REVISION,
                                         now=NOW, deadline=deadline)
                (scratch / "config/central-one-shot-trust.json").write_bytes(
                    auth.canonical({"schema_version": 1, "keys": []}))
                with self.assertRaises(auth.Blocked):
                    auth.verify_envelope(auth.canonical(signed), revision=REVISION,
                                         now=NOW, deadline=deadline)

    def test_launcher_claims_and_environment_self_assertions_are_not_authority(self):
        audience = provenance.audience(b"test-envelope")
        instant = int(NOW.timestamp())
        claims = {
            "iss": provenance.ISSUER, "aud": audience, "repository": hub.HUB,
            "repository_owner": hub.OWNER, "ref": "refs/heads/main", "ref_type": "branch",
            "sha": REVISION, "workflow_ref": provenance.WORKFLOW, "workflow_sha": REVISION,
            "runner_environment": "github-hosted",
            "sub": "repo:" + hub.HUB + ":ref:refs/heads/main",
            "event_name": "workflow_dispatch", "run_id": "1", "run_attempt": "1",
            "iat": instant - 1, "nbf": instant - 1, "exp": instant + 300,
        }
        provenance.validate_claims(claims, revision=REVISION, expected_audience=audience,
                                   now=NOW, one_shot=True)
        with self.assertRaises(auth.Blocked):
            provenance.validate_claims({**claims, "workflow_sha": "e" * 40},
                                       revision=REVISION, expected_audience=audience,
                                       now=NOW, one_shot=True)
        with patch.dict(provenance.os.environ, {"GITHUB_ACTIONS": "true",
                        "GITHUB_SHA": REVISION, "GITHUB_REF": "refs/heads/main"}, clear=True):
            with patch.object(provenance, "get_json") as transport:
                with self.assertRaises(auth.Blocked):
                    provenance.verify_launcher(revision=REVISION, envelope=b"test-envelope",
                                               deadline=time.monotonic() + 5)
                transport.assert_not_called()

    def test_same_ledger_orders_receipts_caps_deadline_and_blocks_replay(self):
        h = target_ready(self)
        seen = []
        def lane(name, binary, diff, snapshots, *, attempt_cap, attempt_deadline):
            self.assertEqual(attempt_cap, 1)
            self.assertGreater(attempt_deadline, time.monotonic())
            seen.append(name)
            return h.lane(name, binary, diff, snapshots)
        h.lanes.side_effect = lane
        request = payload()
        since = hub.utc(request["eligible_since"])
        candidates = [(since, TARGET, 1, BASE, HEAD)]
        with patch.object(hub, "discover", side_effect=AssertionError("must not discover")):
            result = h.controller()._run_targets(candidates, since, Path("/offline/opencodereview"),
                                                  authorization=request)
        self.assertEqual(result["completed"], 1)
        self.assertEqual(seen, list(hub.LANES))
        self.assertEqual(len(h.ledger()), 1)
        self.assertEqual(len(h.receipts()), 1)
        self.assertFalse(h.memory.unread_writes)
        repeated = h.controller()._run_targets(candidates, since, Path("/offline/opencodereview"),
                                                authorization=request)
        self.assertEqual(repeated["status"], "BLOCKED_OR_UNKNOWN")
        self.assertEqual(h.lanes.call_count, 2)
        self.assertEqual(h.controller().run(ENV)["reservations"], 0)
        self.assertEqual(h.lanes.call_count, 2)

    def test_unknown_reservation_ack_stops_and_remains_consumed(self):
        h = target_ready(self)
        original = h.memory
        def lost_ack(method, path, data=None):
            result = original(method, path, data)
            if method == "POST" and path == "/repos/" + hub.HUB + "/check-runs":
                raise OSError("simulated lost acknowledgment")
            return result
        h.api.side_effect = lost_ack
        request = payload()
        since = hub.utc(request["eligible_since"])
        candidates = [(since, TARGET, 1, BASE, HEAD)]
        result = h.controller()._run_targets(candidates, since, Path("/offline/opencodereview"),
                                              authorization=request)
        self.assertEqual(result["status"], "BLOCKED_OR_UNKNOWN")
        self.assertEqual(len(h.ledger()), 1)
        h.sources.assert_not_called()
        h.lanes.assert_not_called()
        h.api.side_effect = original
        again = h.controller()._run_targets(candidates, since, Path("/offline/opencodereview"),
                                             authorization=request)
        self.assertEqual(again["status"], "BLOCKED_OR_UNKNOWN")
        self.assertEqual(len(h.ledger()), 1)
        h.lanes.assert_not_called()

    def test_actual_sender_caps_failures_and_expiry_stop_before_http(self):
        response = json.dumps({"model": auto.connection.MODEL, "choices": [{
            "finish_reason": "stop", "message": {"content": "done"}}]}).encode()
        raw = json.dumps({"model": auto.connection.MODEL,
                          "messages": [{"role": "user", "content": "test"}]}).encode()
        with patch.object(auto.connection.Relay, "_forward", return_value=response) as upstream:
            relay = auto.BoundedReviewRelay(live=True, api_key="test-only", attempt_cap=1)
            relay.exchange(raw, "Bearer " + relay.token, "/v1/chat/completions")
            with self.assertRaises(auto.connection.ProbeError):
                relay.exchange(raw, "Bearer " + relay.token, "/v1/chat/completions")
            self.assertEqual(upstream.call_count, 1)
            self.assertEqual(relay.payload_budget.attempts, 1)
        with patch.object(auto.connection.Relay, "_forward", side_effect=OSError("offline")) as upstream:
            sender = auto.BoundedGuidanceSender(live=True, api_key="test-only", attempt_cap=1)
            with self.assertRaises(OSError):
                sender._forward(b"{}")
            with self.assertRaises(ValueError):
                sender._forward(b"{}")
            self.assertEqual(upstream.call_count, 1)
            self.assertEqual(sender.payload_budget.attempts, 1)
            self.assertEqual(sender.payload_budget.bytes, 2)
        with patch.object(auto.connection.Relay, "_forward") as upstream:
            expired = auto.BoundedGuidanceSender(live=True, api_key="test-only",
                                                 attempt_cap=1,
                                                 attempt_deadline=time.monotonic() - 1)
            with self.assertRaises(ValueError):
                expired._forward(b"{}")
            upstream.assert_not_called()
            self.assertEqual(expired.payload_budget.attempts, 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
