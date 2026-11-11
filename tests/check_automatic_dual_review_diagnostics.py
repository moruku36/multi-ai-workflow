#!/usr/bin/env python3
"""Exactly one offline case; unexecuted. Requires an owner-approved +1 extension."""
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import automatic_dual_review as auto


class Diagnostics(unittest.TestCase):
    def test_failed_cli_persists_safe_diagnostics_after_cleanup(self):
        # One main invocation, one Alibaba failure; no real HTTP, Git, CLI or keys.
        unsafe = '/private/fixture/provider-text Authorization: Bearer offline-dummy'
        relay = SimpleNamespace(attempts=1, completed=0, halted=False,
                                usage=[], token='offline-loopback-token')

        def finish_request():
            # An in-flight request settles during shutdown, before serialization.
            relay.attempts, relay.completed, relay.halted = 2, 1, True
            relay.usage = [{'prompt_tokens': 13, 'completion_tokens': unsafe,
                            'total_tokens': auto.MAX_USAGE_TOKENS + 1, 'extra': unsafe}]

        shutdown = Mock(side_effect=finish_request)
        close = Mock(side_effect=OSError(unsafe))

        class OfflineServer:
            def __init__(self, *_args):
                self.server_port = 1
                self.serve_forever = Mock()
                self.shutdown, self.server_close = shutdown, close

        worker = Mock()
        worker.is_alive.return_value = False
        base, head = 'a' * 40, 'b' * 40
        binding = {'base_sha': base, 'head_sha': head, 'diff_sha256': 'c' * 64}
        snapshots = {'sample.py': ['value = 1\n', 'value = 2\n']}
        pr = {'number': 1, 'base': {'ref': 'main', 'sha': base,
                                  'repo': {'full_name': 'example/repo'}},
              'head': {'sha': head}}
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root = Path(tmp)
            event = root / 'event.json'
            event.write_text(json.dumps({'pull_request': pr}))
            stack.enter_context(patch.object(auto.os, 'environ', {
                'GITHUB_EVENT_PATH': str(event), 'GITHUB_REPOSITORY': 'example/repo',
                'RUNNER_TEMP': str(root), 'OCR_BINARY': str(root / 'unused-cli'),
                'MIMO_API_KEY': 'offline-dummy'}))
            stack.enter_context(patch.object(auto.Path, 'home', return_value=root))
            stack.enter_context(patch.object(auto.dual_review, 'verify_skill', return_value='fixture'))
            reserve = stack.enter_context(patch.object(auto, 'reserve', return_value=1))
            stack.enter_context(patch.object(auto, 'git', return_value=b''))
            stack.enter_context(patch.object(auto, 'collect', return_value=(binding, 'diff', snapshots)))
            stack.enter_context(patch.object(auto, 'cloudflare', return_value={
                'findings': [], 'unresolved': [], 'http_attempts': 1, 'usage': {}}))
            api = stack.enter_context(patch.object(auto, 'api', return_value=pr))
            stack.enter_context(patch.object(auto.connection, 'checked_binary',
                                             return_value=(root / 'unused-cli', 'd' * 64)))
            stack.enter_context(patch.object(auto.connection, 'child_environment', return_value={}))
            stack.enter_context(patch.object(auto.ReviewRelay, '_forward',
                                             side_effect=AssertionError('upstream forbidden')))
            stack.enter_context(patch.object(auto, 'ReviewRelay', return_value=relay))
            stack.enter_context(patch.object(auto, 'HTTPServer', OfflineServer))
            stack.enter_context(patch.object(auto.threading, 'Thread', return_value=worker))
            cli = stack.enter_context(patch.object(auto.subprocess, 'run', return_value=
                SimpleNamespace(returncode=7, stdout=unsafe, stderr=unsafe)))

            with self.assertRaisesRegex(ValueError, '^review incomplete$'):
                auto.main()

            receipt_text = (root / 'dual-review-results' / 'receipt.json').read_text()
            receipt = json.loads(receipt_text)
            lane = receipt['lanes']['alibaba']
            self.assertEqual(lane, {**binding, 'status': 'FAILED_OR_UNKNOWN', 'diagnostics': {
                'failure_stage': 'cli_exit_nonzero', 'http_attempts': 2,
                'completed_responses': 1, 'relay_halted': True, 'cli_exit_code': 7,
                'usage': [{'prompt_tokens': 13, 'completion_tokens': 'unknown',
                           'total_tokens': 'unknown'}]}})
            self.assertNotIn(unsafe, receipt_text)
            self.assertEqual(receipt['status'], 'INCOMPLETE')
            self.assertFalse(receipt['merge_authorized'])
            self.assertEqual(api.call_count, 2)
            self.assertEqual(api.call_args.args[:2], ('PATCH', '/repos/example/repo/check-runs/1'))
            self.assertEqual(api.call_args.args[2]['conclusion'], 'failure')
            reserve.assert_called_once_with('example/repo', base, head)
            cli.assert_called_once()
            self.assertEqual(cli.call_args.kwargs['timeout'], 150)
            self.assertFalse(cli.call_args.kwargs['cwd'].parent.exists())
            shutdown.assert_called_once_with()
            close.assert_called_once_with()
            worker.join.assert_called_once_with(timeout=31)


if __name__ == '__main__':
    unittest.main()
