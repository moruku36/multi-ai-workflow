"""Three mocked scenarios. UNEXECUTED; no execution allowance."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import automatic_dual_review as a


@contextmanager
def offline(finish='stop'):
    raw = json.dumps({'model': a.connection.MODEL, 'choices': [{
        'finish_reason': finish, 'message': {
            'content': '{"findings":[],"unresolved":[]}'}}]}).encode()
    with patch.dict(os.environ, {'MIMO_API_KEY': 'dummy'}, clear=True), \
            patch.object(a.dual_review, 'verify_skill', return_value='a' * 40), \
            patch.object(a.Path, 'read_text', return_value='guidance'), \
            patch.object(a.connection.secrets, 'token_urlsafe', return_value='dummy'), \
            patch.object(a.connection.Relay, '_forward', autospec=True,
                         return_value=raw) as up:
        yield up


class Compat(unittest.TestCase):
    def test_alibaba(self):
        call = {'id': 'c', 'type': 'function', 'function': {
            'name': 'task_done', 'arguments': '{}'}}
        p = {'model': a.connection.MODEL, 'thinking': {'type': 'enabled'},
            'max_completion_tokens': 9999,
            'tools': [{'type': 'function', 'function': {'name': 'task_done'}},
                      {'type': 'function', 'function': {'name': 'code_comment'}}],
            'tool_choice': 'auto', 'messages': [
                {'role': 'user', 'content': '雪'},
                {'role': 'assistant', 'content': None, 'reasoning_content': 'history',
                 'tool_calls': [call]},
                {'role': 'tool', 'tool_call_id': 'c', 'content': 'ok'}]}
        with offline() as up:
            r = a.BoundedReviewRelay(live=True, api_key='dummy', attempt_cap=1)
            args = (json.dumps(p).encode(), 'Bearer ' + r.token,
                    '/v1/chat/completions')
            r.exchange(*args)
            sent = up.call_args.args[1]
            expected = dict(p, thinking={'type': 'disabled'}, max_tokens=2048)
            expected.pop('max_completion_tokens')
            self.assertEqual(sent, json.dumps(expected, ensure_ascii=False).encode())
            with self.assertRaises(a.connection.ProbeError):
                r.exchange(*args)
            self.assertEqual((r.attempts, r.completed, r.payload_budget.bytes),
                             (1, 1, len(sent)))
            up.assert_called_once()

    def test_cloudflare(self):
        with offline() as up:
            out = a.cloudflare('diff', {}, attempt_cap=1)
            r, body = up.call_args.args
            p = json.loads(body)
            self.assertEqual((p['thinking'], p['max_tokens'], r.attempts,
                              r.completed, r.payload_budget.bytes),
                             ({'type': 'disabled'}, 2048, 1, 1, len(body)))
            self.assertEqual((out['findings'], out['unresolved']), ([], []))
            up.assert_called_once()

    def test_length(self):
        with offline('length') as up:
            with self.assertRaises(a.LaneError) as caught:
                a.cloudflare('diff', {}, attempt_cap=1)
            self.assertEqual(json.loads(up.call_args.args[1])['thinking'], {'type': 'disabled'})
            d = caught.exception.diagnostics
            self.assertEqual((d['response_reason'], d['http_attempts'],
                              d['completed_responses']), ('length_stop', 1, 0))
            up.assert_called_once()


if __name__ == '__main__':
    unittest.main()
