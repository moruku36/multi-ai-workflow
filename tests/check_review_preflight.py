"""Exactly two independent offline cases, authored UNEXECUTED; no subcases."""
from contextlib import contextmanager, ExitStack
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import automatic_dual_review as auto

BASE, HEAD, MERGE = 'a' * 40, 'b' * 40, 'c' * 40
DIFF = b'PRIVATE_SOURCE_DIFF\n'
SOURCES = {'sample.py': ['PRIVATE_BEFORE\n', 'PRIVATE_AFTER\n']}
TREE = b'100644 blob ' + b'e' * 40 + b'\tsample.py\0'
BINDING = {'base_sha': MERGE, 'head_sha': HEAD, 'diff_sha256': 'd' * 64}


@contextmanager
def offline():
    # Only temporary receipt I/O is real; no ambient credentials or crypto.
    with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
        enter = stack.enter_context
        pr = {'number': 1, 'base': {'sha': BASE, 'ref': 'main',
              'repo': {'full_name': 'example/repo'}}, 'head': {'sha': HEAD}}
        enter(patch.dict(auto.os.environ, {
            'GITHUB_EVENT_PATH': str(Path(tmp) / 'event.json'),
            'GITHUB_REPOSITORY': 'example/repo', 'RUNNER_TEMP': tmp,
            'MIMO_API_KEY': 'PRIVATE_DUMMY_KEY', 'OCR_BINARY': '/offline/ocr'}, clear=True))
        enter(patch.object(auto.Path, 'read_text', return_value=json.dumps({'pull_request': pr})))
        enter(patch.object(auto.dual_review, 'verify_skill', return_value='offline'))
        enter(patch.object(auto.subprocess, 'run', side_effect=AssertionError('process')))
        enter(patch.object(auto.http.client, 'HTTPSConnection', side_effect=AssertionError('network')))
        h = SimpleNamespace(receipt=Path(tmp) / 'dual-review-results/receipt.json', order=Mock())
        h.git = enter(patch.object(auto, 'git'))
        h.digest = enter(patch.object(auto.hashlib, 'sha256'))
        h.digest.return_value.hexdigest.return_value = BINDING['diff_sha256']
        h.api = enter(patch.object(auto, 'api', side_effect=[
            {'check_runs': []}, {'id': 7}, pr, {}]))
        h.collect = enter(patch.object(auto, 'collect', wraps=auto.collect))
        h.reserve = enter(patch.object(auto, 'reserve', wraps=auto.reserve))
        h.alibaba = enter(patch.object(auto, 'alibaba',
                          return_value={'findings': [], 'unresolved': []}))
        h.cloudflare = enter(patch.object(auto, 'cloudflare',
                             return_value={'findings': [], 'unresolved': []}))
        for name in ('collect', 'reserve', 'alibaba', 'cloudflare'):
            h.order.attach_mock(getattr(h, name), name)
        yield h


class ReviewPreflight(unittest.TestCase):
    def test_oversized_collect_rejects_before_reservation(self):
        with offline() as h:
            h.git.side_effect = [b'', MERGE.encode(), DIFF, b'sample.py\0', TREE,
                                 str(auto.MAX_SNAPSHOT_BYTES + 1).encode()]
            with self.assertRaises(ValueError) as stopped:
                auto.main()
            self.assertEqual(str(stopped.exception), 'source snapshots exceed budget')
            h.collect.assert_called_once_with(auto.ROOT, BASE, HEAD)
            h.reserve.assert_not_called()
            h.api.assert_not_called()
            h.alibaba.assert_not_called()
            h.cloudflare.assert_not_called()
            h.digest.assert_not_called()
            self.assertEqual(h.git.call_count, 6)
            text = h.receipt.read_bytes().decode()
            self.assertEqual(json.loads(text), {
                'schema_version': '1.0', 'base_tip_sha': BASE, 'head_sha': HEAD,
                'merge_authorized': False, 'review_quality_accepted': False,
                'independence': 'NOT_VERIFIED_SAME_PROVIDER',
                'status': 'PREFLIGHT_REJECTED', 'lanes': {}})
            self.assertNotIn(str(stopped.exception), text)
            self.assertNotIn('PRIVATE', text)
            self.assertNotIn(auto.connection.MODEL, text)

    def test_ready_collect_reserve_both_lanes_immutable(self):
        with offline() as h:
            h.git.side_effect = [b'', MERGE.encode(), DIFF, b'sample.py\0', TREE,
                b'15', SOURCES['sample.py'][0].encode(), TREE,
                b'14', SOURCES['sample.py'][1].encode()]
            auto.main()
            self.assertEqual(h.order.mock_calls, [
                call.collect(auto.ROOT, BASE, HEAD), call.reserve('example/repo', BASE, HEAD),
                call.alibaba(Path('/offline/ocr'), SOURCES), call.cloudflare(DIFF.decode(), SOURCES)])
            self.assertEqual(h.git.call_args_list[0],
                             call(auto.ROOT, 'fetch', '--no-tags', 'origin', BASE, HEAD))
            h.digest.assert_called_once_with(DIFF)
            self.assertEqual(h.api.call_count, 4)
            reservation = h.api.call_args_list[1].args
            self.assertEqual(reservation[:2], ('POST', '/repos/example/repo/check-runs'))
            self.assertEqual(reservation[2]['external_id'], BASE + ':' + HEAD)
            self.assertEqual(reservation[2]['head_sha'], HEAD)
            saved = json.loads(h.receipt.read_bytes())
            self.assertEqual(saved['base_tip_sha'], BASE)
            self.assertEqual({k: saved[k] for k in BINDING}, BINDING)
            self.assertEqual(saved['status'], 'BOTH_RECORDED_NOT_ACCEPTED')
            self.assertEqual({k: v['status'] for k, v in saved['lanes'].items()},
                             {'alibaba': 'completed', 'cloudflare': 'completed'})
            self.assertEqual({k: saved['lanes']['alibaba'][k] for k in BINDING}, BINDING)
            self.assertEqual({k: saved['lanes']['cloudflare'][k] for k in BINDING}, BINDING)
            self.assertFalse(saved['merge_authorized'])
            self.assertFalse(saved['review_quality_accepted'])


if __name__ == '__main__':
    unittest.main(verbosity=1)
