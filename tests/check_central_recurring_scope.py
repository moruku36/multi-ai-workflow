import contextlib
import io
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import central_recurring_scope as scope  # noqa: E402
from central_review_hub import Blocked, load_config  # noqa: E402

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
CONFIG = {'enabled': True, 'paid_execution_authorized': True, 'limits': {}}
GOOD_ENV = {
    'CENTRAL_RECURRING_REPOSITORIES': 'multi-ai-workflow,local-ai-sidekick',
    'CENTRAL_REVIEW_ENABLED': 'true',
    'CENTRAL_REVIEW_SINCE': '2026-11-19T00:00:00Z',
}
PATH = '/installation/repositories?&per_page=2&page=1'
OWNER_ID = 12478466


def env(**changes):
    merged = dict(GOOD_ENV)
    merged.update(changes)
    return merged


def row(repo_id, full_name, **changes):
    base = {
        'id': repo_id,
        'full_name': full_name,
        'private': False,
        'visibility': 'public',
        'disabled': False,
        'fork': False,
        'archived': False,
        'default_branch': 'main',
        'owner': {'login': 'moruku36', 'id': OWNER_ID},
    }
    base.update(changes)
    return base


def without(data, key):
    trimmed = dict(data)
    del trimmed[key]
    return trimmed


def hub(**changes):
    return row(scope.HUB_ID, scope.HUB, **changes)


def target(**changes):
    return row(scope.TARGET_ID, scope.TARGET, **changes)


class MockAPI:
    # Returns what the real GitHub.__call__ returns: (data, has_next_page).
    def __init__(self, rows, total=None, has_next=False):
        self.rows = rows
        self.total = len(rows) if total is None else total
        self.has_next = has_next
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append(args)
        data = {'repositories': self.rows, 'total_count': self.total}
        return data, self.has_next


class PreTokenTests(unittest.TestCase):
    def test_valid(self):
        scope.verify_pre_token(CONFIG, GOOD_ENV, NOW)

    def test_rejections(self):
        future = (NOW + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        bad = [
            (CONFIG, env(CENTRAL_REVIEW_ENABLED='false')),
            (CONFIG, env(CENTRAL_RECURRING_REPOSITORIES='multi-ai-workflow')),
            (CONFIG, env(CENTRAL_RECURRING_REPOSITORIES='local-ai-sidekick,multi-ai-workflow')),
            (CONFIG, env(CENTRAL_REVIEW_SINCE='')),
            (CONFIG, env(CENTRAL_REVIEW_SINCE='not-a-cutoff')),
            (CONFIG, {key: value for key, value in GOOD_ENV.items()
                      if key != 'CENTRAL_REVIEW_SINCE'}),
            (CONFIG, env(CENTRAL_REVIEW_SINCE=future)),
            (dict(CONFIG, enabled=False), GOOD_ENV),
            (dict(CONFIG, paid_execution_authorized=False), GOOD_ENV),
        ]
        for config, environ in bad:
            with self.subTest(environ=environ, config=config):
                with self.assertRaises(Blocked):
                    scope.verify_pre_token(config, environ, NOW)


class ReadbackTests(unittest.TestCase):
    def test_exact_success_any_order_single_bounded_get(self):
        for rows in ([hub(), target()], [target(), hub()]):
            with self.subTest(order=[r['id'] for r in rows]):
                api = MockAPI(rows)
                scope.verify_installation(api)
                self.assertEqual(api.calls, [('GET', PATH)])

    def test_hub_fork_and_branch_are_not_review_criteria(self):
        anchor = without(hub(fork=True), 'default_branch')
        api = MockAPI([anchor, target(default_branch='develop')])
        scope.verify_installation(api)
        self.assertEqual(api.calls, [('GET', PATH)])

    def test_failures(self):
        cases = {
            'missing': MockAPI([hub()]),
            'extra rows': MockAPI([hub(), target(), row(7, 'moruku36/other')]),
            'extra count': MockAPI([hub(), target()], total=3),
            'incomplete count': MockAPI([hub()], total=2),
            'next page': MockAPI([hub(), target()], has_next=True),
            'id substitution': MockAPI([hub(), row(7, scope.TARGET)]),
            'name substitution': MockAPI([hub(), row(scope.TARGET_ID, 'moruku36/Local-AI-Sidekick')]),
            'duplicate': MockAPI([target(), target()]),
            'hub identity': MockAPI([row(9, scope.HUB), target()]),
        }
        for label, api in cases.items():
            with self.subTest(label):
                with self.assertRaises(Blocked):
                    scope.verify_installation(api)

    def test_ineligible_anchor_and_target(self):
        cases = {
            'target private': [hub(), target(private=True)],
            'target internal': [hub(), target(visibility='internal')],
            'target missing visibility': [hub(), without(target(), 'visibility')],
            'target fork': [hub(), target(fork=True)],
            'target archived': [hub(), target(archived=True)],
            'target disabled': [hub(), target(disabled=True)],
            'target foreign owner': [hub(), target(owner={'login': 'someone', 'id': OWNER_ID})],
            'anchor private': [hub(private=True), target()],
            'anchor internal': [hub(visibility='internal'), target()],
            'anchor missing visibility': [without(hub(), 'visibility'), target()],
            'anchor disabled': [hub(disabled=True), target()],
            'anchor archived': [hub(archived=True), target()],
            'anchor missing archive metadata': [without(hub(), 'archived'), target()],
            'anchor foreign owner': [hub(owner={'login': 'someone', 'id': OWNER_ID}), target()],
        }
        for label, rows in cases.items():
            with self.subTest(label):
                with self.assertRaises(Blocked):
                    scope.verify_installation(MockAPI(rows))

    def test_owner_identity_required_on_each_row(self):
        owners = {
            'wrong id': {'login': 'moruku36', 'id': OWNER_ID + 1},
            'missing id': {'login': 'moruku36'},
            'string id': {'login': 'moruku36', 'id': str(OWNER_ID)},
            'float id': {'login': 'moruku36', 'id': float(OWNER_ID)},
            'bool id': {'login': 'moruku36', 'id': True},
            'null id': {'login': 'moruku36', 'id': None},
            'wrong login valid id': {'login': 'someone', 'id': OWNER_ID},
            'missing login valid id': {'id': OWNER_ID},
        }
        for label, owner in owners.items():
            for name, rows in (
                ('hub', [hub(owner=owner), target()]),
                ('target', [hub(), target(owner=owner)]),
            ):
                with self.subTest(label=label, row=name):
                    with self.assertRaises(Blocked):
                        scope.verify_installation(MockAPI(rows))


class MainTests(unittest.TestCase):
    def run_main(self, args, **kwargs):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = scope.main(args, **kwargs)
        return code, err.getvalue()

    def test_bad_arguments_fail_with_opaque_message(self):
        for args in ([], ['pre-token', 'readback'], ['other']):
            with self.subTest(args=args):
                code, text = self.run_main(args)
                self.assertEqual(code, 1)
                self.assertEqual(text, scope.MESSAGE + '\n')

    def test_pre_token_needs_no_credential_or_api(self):
        with mock.patch.object(scope, 'load_config', return_value=CONFIG), \
                mock.patch.object(scope, 'GitHub') as github, \
                mock.patch.dict(os.environ, GOOD_ENV, clear=True):
            code, text = self.run_main(['pre-token'], clock=lambda: NOW)
        self.assertEqual((code, text), (0, ''))
        github.assert_not_called()

    def test_readback_dispatches_with_configured_limits(self):
        config = dict(CONFIG, limits={'marker': 1})
        api = MockAPI([hub(), target()])
        with mock.patch.object(scope, 'load_config', return_value=config), \
                mock.patch.object(scope, 'GitHub', return_value=api) as github, \
                mock.patch.object(scope.time, 'monotonic', return_value=10):
            code, text = self.run_main(['readback'])
        self.assertEqual((code, text), (0, ''))
        github.assert_called_once_with({'marker': 1}, 55)
        self.assertEqual(len(api.calls), 1)

    def test_disabled_flags_never_reach_github(self):
        real = load_config()
        self.assertIs(real['enabled'], False)
        self.assertIs(real['paid_execution_authorized'], False)
        configurations = (real, dict(real, enabled=True), dict(real, paid_execution_authorized=True))
        for disabled in configurations:
            with self.subTest(config=disabled):
                with mock.patch.object(scope, 'load_config', return_value=disabled), \
                        mock.patch.object(scope, 'GitHub') as github, \
                        mock.patch.object(scope, 'verify_installation') as readback:
                    code, text = self.run_main(['readback'])
                self.assertEqual((code, text), (1, scope.MESSAGE + '\n'))
                github.assert_not_called()
                readback.assert_not_called()

    def test_readback_failure_is_opaque(self):
        api = MockAPI([hub()])
        with mock.patch.object(scope, 'load_config', return_value=CONFIG), \
                mock.patch.object(scope, 'GitHub', return_value=api):
            code, text = self.run_main(['readback'])
        self.assertEqual((code, text), (1, scope.MESSAGE + '\n'))


if __name__ == '__main__':
    unittest.main()
