"""Three offline cases authored for this draft. UNEXECUTED; no new trial budget."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import automatic_dual_review as auto
import central_review_hub as hub


class BoundedDraft(unittest.TestCase):
    def test_serialized_payload_cumulative_and_request_caps(self):
        budget = auto.PayloadBudget(8, cumulative_bytes=65536)
        # Source character count is insufficient: JSON escaping expands bytes.
        expanded = auto.json.dumps({'source': '\u0001' * 12000}).encode()
        with self.assertRaises(ValueError):
            budget.reserve(expanded)
        budget.reserve(b'x' * 32768)
        budget.reserve(b'y' * 32768)
        with self.assertRaises(ValueError):
            budget.reserve(b'z')
        self.assertEqual(budget.attempts, 2)

    def test_one_shot_rejects_manifest_authority_and_excluded_hub(self):
        request = {'repository': hub.HUB, 'pr': 52, 'base': 'a' * 40,
                   'head': 'b' * 40, 'controller_revision': 'c' * 40,
                   'eligible_since': '2030-01-01T00:00:00Z',
                   'expires_at': '2030-01-02T12:30:00Z',
                   'lane_attempt_limits': {'alibaba': 8, 'cloudflare': 1},
                   'authorization_evidence_sha256': 'd' * 64}
        for extra in ({}, {'paid_execution_authorized': True}):
            with self.assertRaises(hub.Blocked):
                hub.validate_one_shot({**request, **extra}, controller_revision='c' * 40,
                                      now=hub.utc('2030-01-02T12:00:00Z'))

    def test_one_shot_expiry_revision_and_attempts(self):
        request = {'repository': hub.OWNER + '/sample', 'pr': 1, 'base': 'a' * 40,
                   'head': 'b' * 40, 'controller_revision': 'c' * 40,
                   'eligible_since': '2030-01-01T00:00:00Z',
                   'expires_at': '2030-01-02T12:30:00Z',
                   'lane_attempt_limits': {'alibaba': 8, 'cloudflare': 1},
                   'authorization_evidence_sha256': 'd' * 64}
        now = hub.utc('2030-01-02T12:00:00Z')
        for delta in ({'expires_at': '2030-01-02T11:59:59Z'},
                      {'controller_revision': 'e' * 40},
                      {'lane_attempt_limits': {'alibaba': 9, 'cloudflare': 1}}):
            with self.assertRaises(hub.Blocked):
                hub.validate_one_shot({**request, **delta}, controller_revision='c' * 40, now=now)
