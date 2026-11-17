#!/usr/bin/env python3
'''Synthetic offline checks for the PR57 Cloudflare body and Alibaba stop diagnostics.'''
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))

import automatic_dual_review as adr  # noqa: E402
import ocr_mimo_connection as connection  # noqa: E402

CJK = chr(0x3042)
# 18000 CJK characters each for source and diff: 54k UTF-8 bytes apiece, inside the
# original 65536 per-input caps, and small enough that the real skill guidance still
# fits under the unchanged 196608 sender cap.
FIT_CHARS = 18000


def unicode_inputs(diff_chars, source_chars):
    diff = '+' + CJK * diff_chars
    snapshots = {'docs/a.md': [None, CJK * source_chars], 'docs/b.md': ['x', 'y' + CJK]}
    return diff, snapshots


def good_response():
    return json.dumps({
        'model': connection.MODEL,
        'choices': [{'finish_reason': 'stop', 'message': {
            'content': json.dumps({'findings': [], 'unresolved': []})}}],
        'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}).encode()


def valid_request(pad=0):
    return json.dumps({
        'model': connection.MODEL,
        'messages': [{'role': 'user', 'content': 'x' * pad}],
        'max_tokens': adr.MAX_OUTPUT_TOKENS,
        'stream': False}).encode()


class RouteRepair(unittest.TestCase):
    def test_unicode_body_roundtrips_and_fits_where_ascii_overflows(self):
        diff, snapshots = unicode_inputs(FIT_CHARS, FIT_CHARS)
        body = adr.build_guidance_body(diff, snapshots, 'guidance')
        self.assertLessEqual(len(body), adr.MAX_GUIDANCE_REQUEST_BYTES)
        payload = json.loads(body)
        self.assertEqual(payload['model'], connection.MODEL)
        self.assertIs(payload['stream'], False)
        self.assertEqual(payload['max_tokens'], adr.MAX_OUTPUT_TOKENS)
        self.assertEqual(payload['thinking'], {'type': 'disabled'})
        self.assertEqual([m['role'] for m in payload['messages']], ['system', 'user'])
        user = json.loads(payload['messages'][1]['content'])
        self.assertEqual(user['untrusted_diff'], diff)
        self.assertEqual(user['untrusted_sources'], snapshots)
        # ASCII-escaped double encoding (old style) expands each CJK char to 6 bytes
        # and must still overflow the cap for the same inputs.
        old_style = json.dumps(json.dumps(
            {'untrusted_diff': diff, 'untrusted_sources': snapshots})).encode()
        self.assertGreater(len(old_style), adr.MAX_GUIDANCE_REQUEST_BYTES)

    def test_cloudflare_sender_accepts_unicode_body_without_network(self):
        diff, snapshots = unicode_inputs(FIT_CHARS, FIT_CHARS)
        sent = []

        def fake_forward(self, body):
            sent.append(body)
            return good_response()

        with mock.patch.dict(os.environ, {'MIMO_API_KEY': 'synthetic-key'}), \
                mock.patch.object(adr.dual_review, 'verify_skill', return_value='rev'), \
                mock.patch.object(connection.Relay, '_forward', fake_forward):
            result = adr.cloudflare(diff, snapshots)
        self.assertEqual(len(sent), 1)
        self.assertLessEqual(len(sent[0]), adr.MAX_GUIDANCE_REQUEST_BYTES)
        user = json.loads(json.loads(sent[0])['messages'][1]['content'])
        self.assertEqual(user['untrusted_diff'], diff)
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['unresolved'], [])

    def test_oversize_body_fails_closed_before_transport(self):
        # Scenario 1: a single oversize guidance body is rejected before any transport.
        diff, snapshots = unicode_inputs(70000, 70000)
        sent = []

        def fake_forward(self, body):
            sent.append(body)
            return good_response()

        with mock.patch.dict(os.environ, {'MIMO_API_KEY': 'synthetic-key'}), \
                mock.patch.object(adr.dual_review, 'verify_skill', return_value='rev'), \
                mock.patch.object(connection.Relay, '_forward', fake_forward):
            with self.assertRaises(adr.LaneError) as caught:
                adr.cloudflare(diff, snapshots)
        self.assertEqual(sent, [])
        self.assertEqual(caught.exception.diagnostics['stop_reason'], 'payload_size')
        self.assertEqual(caught.exception.diagnostics['failure_stage'], 'request_http')

        # Scenario 2: pure budget check, no network and no transport claim. A second
        # reservation that would exceed the cumulative budget is refused and leaves the
        # counters unchanged.
        budget = adr.PayloadBudget(2, request_bytes=8, cumulative_bytes=10)
        budget.reserve(b'123456')
        with self.assertRaises(adr.BudgetExceeded) as over:
            budget.reserve(b'123456')
        self.assertEqual(over.exception.reason, 'cumulative_payload')
        self.assertEqual(budget.attempts, 1)
        self.assertEqual(budget.bytes, 6)

    def test_alibaba_attempt_cap_reason_sends_nothing(self):
        # One valid mocked response consumes the whole cap of 1; the second exchange is
        # rejected with no additional transport call.
        sent = []

        def fake_forward(self, body):
            sent.append(body)
            return good_response()

        with mock.patch.object(connection.Relay, '_forward', fake_forward):
            relay = adr.BoundedReviewRelay(live=True, api_key='synthetic-key', attempt_cap=1)
            auth = 'Bearer ' + relay.token
            relay.exchange(valid_request(), auth, '/v1/chat/completions')
            self.assertEqual(len(sent), 1)
            self.assertEqual(relay.attempts, 1)
            self.assertEqual(relay.completed, 1)
            with self.assertRaises(connection.ProbeError):
                relay.exchange(valid_request(), auth, '/v1/chat/completions')
        self.assertEqual(len(sent), 1)
        self.assertEqual(relay.attempts, 1)
        self.assertEqual(relay.completed, 1)
        self.assertTrue(relay.halted)
        self.assertEqual(relay.stop_reason, 'attempt_cap')
        diag = adr.relay_diagnostics('alibaba', 'relay_halted', relay, 0)
        self.assertEqual(diag['stop_reason'], 'attempt_cap')
        self.assertIs(diag['relay_halted'], True)

    def test_alibaba_deadline_reason_sends_nothing(self):
        sent = []

        def fake_forward(self, body):
            sent.append(body)
            return good_response()

        with mock.patch.object(connection.Relay, '_forward', fake_forward):
            relay = adr.BoundedReviewRelay(live=True, api_key='synthetic-key',
                                           attempt_deadline=time.monotonic() - 1)
            with self.assertRaises(connection.ProbeError):
                relay.exchange(b'{}', 'Bearer ' + relay.token, '/v1/chat/completions')
        self.assertEqual(sent, [])
        self.assertEqual(relay.stop_reason, 'deadline')
        diag = adr.relay_diagnostics('alibaba', 'relay_halted', relay, 0)
        self.assertEqual(diag['stop_reason'], 'deadline')

    def test_safe_diagnostics_rejects_arbitrary_stop_reason(self):
        hostile = 'secret-token /private/path ' + CJK
        for value in (hostile, 7, None, ['deadline'], 'Deadline'):
            out = adr.safe_diagnostics('alibaba', {
                'failure_stage': 'relay_halted', 'stop_reason': value,
                'http_attempts': 8, 'completed_responses': 8, 'relay_halted': True})
            self.assertNotIn('stop_reason', out)
            self.assertNotIn(hostile, json.dumps(out))

        class Hostile:
            stop_reason = hostile
            attempts, completed, halted, usage = 1, 0, True, None

        diag = adr.relay_diagnostics('cloudflare', 'request_http', Hostile())
        self.assertNotIn('stop_reason', diag)
        ok = adr.safe_diagnostics('cloudflare', {
            'failure_stage': 'request_http', 'stop_reason': 'cumulative_payload'})
        self.assertEqual(ok['stop_reason'], 'cumulative_payload')


if __name__ == '__main__':
    unittest.main()
