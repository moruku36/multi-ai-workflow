#!/usr/bin/env python3
"""Exactly three single-scenario cases; UNEXECUTED. Approved +3-case budget unused.
All upstream/effects mocked; no HTTP, CLI, Git, workers or filesystem writes.
"""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import automatic_dual_review as auto
import central_review_hub as hub

UNSAFE = 'untrusted-provider-text-not-for-receipts'


class ReviewResponseReason(unittest.TestCase):
    def test_cloudflare_length_stays_incomplete(self):
        raw = json.dumps({'model': auto.connection.MODEL, 'choices': [{
            'finish_reason': 'length', 'message': {'content': UNSAFE}}],
            'usage': {'completion_tokens': 2048}}).encode()
        with patch.dict(os.environ, {'MIMO_API_KEY': 'offline-dummy'}, clear=True), \
                patch.object(auto.dual_review, 'verify_skill', return_value='a' * 40), \
                patch.object(auto.Path, 'read_text', return_value='offline guidance'), \
                patch.object(auto.connection.secrets, 'token_urlsafe', return_value='offline-token'), \
                patch.object(auto.connection.Relay, '_forward', return_value=raw) as upstream:
            with self.assertRaises(auto.LaneError) as caught:
                auto.cloudflare('offline diff', {}, attempt_cap=1)
        diagnostics = caught.exception.diagnostics
        self.assertEqual(diagnostics['failure_stage'], 'response_validation')
        self.assertEqual(diagnostics['response_reason'], 'length_stop')
        self.assertEqual(diagnostics['http_attempts'], 1)
        self.assertEqual(diagnostics['completed_responses'], 0)
        self.assertTrue(diagnostics['relay_halted'])
        self.assertEqual(diagnostics['usage'][0]['completion_tokens'], 2048)
        self.assertNotIn(UNSAFE, json.dumps(diagnostics))
        upstream.assert_called_once()

    def test_alibaba_live_sender_keeps_malformed_reason(self):
        raw = json.dumps({'model': auto.connection.MODEL, 'choices': [{
            'finish_reason': 'stop', 'message': []}]}).encode()
        request = json.dumps({'model': auto.connection.MODEL,
                              'messages': [{'role': 'user', 'content': 'offline'}]}).encode()
        # Patch below the automatic sender, leaving inherited exchange validation real.
        with patch.object(auto.connection.secrets, 'token_urlsafe', return_value='offline-token'), \
                patch.object(auto.connection.Relay, '_forward', return_value=raw) as upstream:
            relay = auto.BoundedReviewRelay(live=True, api_key='offline-dummy', attempt_cap=1)
            with self.assertRaises(auto.connection.ProbeError) as caught:
                relay.exchange(request, 'Bearer ' + relay.token, '/v1/chat/completions')
        self.assertEqual(str(caught.exception), 'review stopped; outcome may be unknown')
        self.assertIsNone(caught.exception.__cause__)
        self.assertTrue(relay.halted)
        self.assertEqual((relay.attempts, relay.completed, relay.payload_budget.attempts), (1, 0, 1))
        error = auto.LaneError('alibaba', 'relay_halted', relay)
        self.assertEqual(error.diagnostics['response_reason'], 'malformed_response')
        upstream.assert_called_once()

    def test_receipt_and_central_projection_allowlist(self):
        relay = SimpleNamespace(attempts=1, completed=0, halted=True, usage=[])
        raw = json.dumps({'model': 'different-model', 'choices': [{
            'finish_reason': 'stop', 'message': {'content': UNSAFE}}]}).encode()
        auto.observe_response_reason('cloudflare', relay, raw)
        error = auto.LaneError('cloudflare', 'response_validation', relay)
        self.assertEqual(error.diagnostics['response_reason'], 'model_mismatch')
        poisoned = dict(error.diagnostics, response_reason=UNSAFE, stderr=UNSAFE)
        direct = auto.safe_diagnostics('cloudflare', poisoned)
        rejected = hub.failed_lane_metadata('cloudflare', poisoned)
        self.assertNotIn('response_reason', direct)
        self.assertNotIn('response_reason', rejected['diagnostics'])
        self.assertNotIn(UNSAFE, json.dumps([direct, rejected]))
        safe = auto.safe_diagnostics('cloudflare', dict(error.diagnostics, headers=UNSAFE))
        saved = hub.failed_lane_metadata('cloudflare', safe)
        self.assertEqual(saved['status'], 'FAILED_OR_UNKNOWN')
        self.assertEqual(saved['diagnostics']['response_reason'], 'model_mismatch')
        self.assertEqual(auto.safe_diagnostics('cloudflare', saved['diagnostics']), safe)
        self.assertNotIn(UNSAFE, json.dumps(saved))


if __name__ == '__main__':
    unittest.main()
