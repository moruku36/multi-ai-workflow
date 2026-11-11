#!/usr/bin/env python3
"""Two offline cases. Execution and reruns need an explicit budget extension.

One real pinned CLI / Git / loopback case checks Markdown dispatch with mocked
upstream transport. One fully mocked case checks incomplete coverage rejection.
Neither case calls an upstream API or uses a real provider credential.
"""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import automatic_dual_review as auto


class AlibabaIntegrationRepair(unittest.TestCase):
    def run_offline_lane(self, snapshots, files_reviewed):
        relay = SimpleNamespace(attempts=1, completed=1, halted=False,
                                usage=[], token='offline-loopback-token')
        worker = Mock()
        worker.is_alive.return_value = False
        server = SimpleNamespace(server_port=1, serve_forever=Mock(),
                                 shutdown=Mock(), server_close=Mock())

        # alibaba subclasses HTTPServer; a Mock instance is not a class base.
        # Keep a real class here while giving it only offline mocked methods.
        class OfflineServer:
            def __init__(self, *_args, **_kwargs):
                self.__dict__.update(vars(server))

        def cli_reply(argv, **kwargs):
            repo = kwargs['cwd']
            rule_path = Path(argv[argv.index('--rule') + 1])
            self.assertEqual(rule_path.parent, repo.parent)
            self.assertEqual(json.loads(rule_path.read_text()), {'include': ['**/*.md']})
            self.assertFalse((repo / 'rules.json').exists())
            self.assertTrue((repo / 'docs' / 'acceptance.md').is_file())
            tools_path = Path(argv[argv.index('--tools') + 1])
            tools = json.loads(tools_path.read_text())
            self.assertEqual([t['name'] for t in tools], ['task_done', 'code_comment'])
            self.assertTrue(all(t['main_task'] and not t['plan_task'] for t in tools))
            self.assertEqual(kwargs['env']['OCR_LLM_MODEL'], auto.connection.MODEL)
            self.assertNotIn('MIMO_API_KEY', kwargs['env'])
            self.assertEqual(argv[argv.index('--timeout') + 1], '1')
            self.assertEqual(argv[argv.index('--concurrency') + 1], '1')
            self.assertIn('--no-filter', argv)
            self.assertEqual(kwargs['timeout'], 150)
            output = Path(argv[argv.index('--output') + 1])
            output.write_text(json.dumps({
                'status': 'complete', 'llm': {'model': auto.connection.MODEL},
                'summary': {'files_reviewed': files_reviewed}, 'comments': []}))
            return SimpleNamespace(returncode=0)

        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root = Path(tmp)
            stack.enter_context(patch.object(auto.os, 'environ', {'MIMO_API_KEY': 'offline-dummy'}))
            stack.enter_context(patch.object(auto.Path, 'home', return_value=root))
            stack.enter_context(patch.object(auto.connection, 'checked_binary',
                                             return_value=(root / 'unused-cli', 'd' * 64)))
            stack.enter_context(patch.object(auto.ReviewRelay, '_forward',
                                             side_effect=AssertionError('upstream forbidden')))
            stack.enter_context(patch.object(auto, 'ReviewRelay', return_value=relay))
            stack.enter_context(patch.object(auto, 'HTTPServer', OfflineServer))
            stack.enter_context(patch.object(auto.threading, 'Thread', return_value=worker))
            stack.enter_context(patch.object(auto, 'git', return_value=b''))
            cli = stack.enter_context(patch.object(auto.subprocess, 'run', side_effect=cli_reply))
            try:
                return auto.alibaba(root / 'unused-cli', snapshots)
            finally:
                cli.assert_called_once()
                server.shutdown.assert_called_once_with()
                server.server_close.assert_called_once_with()
                worker.join.assert_called_once_with(timeout=31)

    def test_actual_cli_markdown_loopback(self):
        # Real pinned CLI selects this new Markdown file; only upstream is mocked.
        # The adapter requires completed responses and full coverage before return.
        binary = Path(os.environ['OCR_TEST_BINARY'])
        snapshots = {'docs/acceptance.md': [None, '# Review\n\none\ntwo\nthree\nfour\nfive\nsix\n']}
        with patch.dict(os.environ, {'MIMO_API_KEY': 'offline-dummy-not-a-key'}):
            with patch.object(auto.ReviewRelay, '_forward',
                              lambda self, raw: self.mock_review(json.loads(raw))):
                result = auto.alibaba(binary, snapshots)
        self.assertEqual(result['findings'], [])
        self.assertGreater(result['http_attempts'], 0)

    def test_partial_cli_coverage_remains_failure(self):
        # A successful process/model response covering only the Python file fails.
        snapshots = {'sample.py': ['value = 1\n', 'value = 2\n'],
                     'docs/acceptance.md': [None, '# Review\n']}
        with self.assertRaises(auto.AlibabaLaneError) as caught:
            self.run_offline_lane(snapshots, files_reviewed=1)
        self.assertEqual(caught.exception.diagnostics['failure_stage'], 'output_coverage')


if __name__ == '__main__':
    unittest.main()
