import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))

import central_pilot_pre_token as pre  # noqa: E402

OWNER, HUB_NAME = pre.HUB.split('/', 1)
GOOD_SCOPE = HUB_NAME + ',local-ai-sidekick'
GOOD_REQUEST = ({'repository': OWNER + '/local-ai-sidekick'}, 1)


def patch_prepare(**kwargs):
    return mock.patch.object(pre.Hub, 'prepare_one_shot', autospec=True, **kwargs)


class PilotPreTokenTests(unittest.TestCase):
    def test_verified_scope_passes_with_exact_ascii_bytes(self):
        with patch_prepare(return_value=GOOD_REQUEST) as prepare:
            pre.verify('{}', GOOD_SCOPE)
        self.assertEqual(prepare.call_args.args[1], b'{}')
        self.assertIs(type(prepare.call_args.args[1]), bytes)

    def test_wrong_verified_repository_or_owner_fails(self):
        for repository in (OWNER + '/other-repo', 'someone-else/local-ai-sidekick'):
            with self.subTest(repository=repository):
                with patch_prepare(return_value=({'repository': repository}, 1)):
                    with self.assertRaises(ValueError):
                        pre.verify('{}', GOOD_SCOPE)

    def test_empty_or_malformed_scope_fails(self):
        for scope in ('', HUB_NAME, GOOD_SCOPE + ',x', HUB_NAME + ', local-ai-sidekick',
                      'local-ai-sidekick,' + HUB_NAME, 'local-ai-sidekick'):
            with self.subTest(scope=scope):
                with patch_prepare(return_value=GOOD_REQUEST):
                    with self.assertRaises(ValueError):
                        pre.verify('{}', scope)

    def test_invalid_envelope_denied_before_verifier(self):
        for envelope in ('', 'x' * 8193, '\u00e9'):
            with self.subTest(length=len(envelope)):
                with patch_prepare(return_value=GOOD_REQUEST) as prepare:
                    with self.assertRaises(ValueError):
                        pre.verify(envelope, GOOD_SCOPE)
                prepare.assert_not_called()

    def test_verifier_failure_exits_1_without_echo(self):
        env = {'CENTRAL_ONE_SHOT_ENVELOPE': 'secret-envelope',
               'CENTRAL_ONE_SHOT_REPOSITORIES': GOOD_SCOPE}
        with mock.patch.dict(os.environ, env, clear=True), \
                patch_prepare(side_effect=RuntimeError('secret-envelope')), \
                mock.patch.object(sys, 'stderr') as err, \
                mock.patch.object(sys, 'stdout') as out:
            self.assertEqual(pre.main(), 1)
        written = ''.join(c.args[0] for c in err.write.call_args_list)
        self.assertEqual(written, pre.FAILURE + '\n')
        out.write.assert_not_called()


if __name__ == '__main__':
    unittest.main()
