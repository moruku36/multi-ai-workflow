#!/usr/bin/env python3
"""Exactly four offline cases. Never invoke without an explicit budget extension."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import automatic_dual_review as auto

def commit(repo, message):
    auto.git(repo, 'add', '--all', '--force')
    auto.git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
             '-c', 'commit.gpgsign=false', 'commit', '-qm', message)
    return auto.git(repo, 'rev-parse', 'HEAD').decode().strip()

def fixture(root):
    repo = root / 'repo'
    repo.mkdir()
    auto.git(repo, 'init', '-q')
    (repo / 'sample.py').write_text('value = 1\n')
    base = commit(repo, 'before')
    (repo / 'sample.py').write_text('value = 2\n')
    head = commit(repo, 'after')
    return repo, base, head

class Selected(unittest.TestCase):
    def test_real_diff_binding_and_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base, head = fixture(Path(tmp))
            binding, diff, snapshots = auto.collect(repo, base, head)
            self.assertEqual(binding['head_sha'], head)
            self.assertEqual(binding['base_sha'], base)
            self.assertIn('+value = 2', diff)
            self.assertEqual(snapshots['sample.py'], ['value = 1\n', 'value = 2\n'])

    def test_unsupported_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, base, _ = fixture(Path(tmp))
            (repo / 'link').symlink_to('sample.py')
            head = commit(repo, 'link')
            with self.assertRaises(ValueError):
                auto.collect(repo, base, head)

    def test_actual_cli_loopback_no_upstream(self):
        binary = Path(os.environ['OCR_TEST_BINARY'])
        snapshots = {'sample.py': ['value = 1\n', 'value = 2\n']}
        # Real pinned CLI; only transport replaced with the existing loopback fixture.
        with patch.dict(os.environ, {'MIMO_API_KEY': 'offline-dummy-not-a-key'}):
            with patch.object(auto.ReviewRelay, '_forward',
                              lambda self, raw: self.mock_review(json.loads(raw))):
                result = auto.alibaba(binary, snapshots)
        self.assertEqual(result['findings'], [])
        self.assertGreater(result['http_attempts'], 0)

    def test_duplicate_unknown_reservation_stops_before_post(self):
        marker = {'check_runs': [{'external_id': 'base:head', 'status': 'in_progress'}]}
        with patch.object(auto, 'api', return_value=marker) as api:
            with self.assertRaises(ValueError):
                auto.reserve('example/repo', 'base', 'head')
        self.assertEqual(api.call_count, 1)
        self.assertEqual(api.call_args.args[0], 'GET')

if __name__ == '__main__':
    suite = unittest.TestSuite(Selected(name) for name in (
        'test_real_diff_binding_and_sources',
        'test_unsupported_symlink_rejected',
        'test_actual_cli_loopback_no_upstream',
        'test_duplicate_unknown_reservation_stops_before_post'))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(not result.wasSuccessful())
