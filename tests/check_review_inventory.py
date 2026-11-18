#!/usr/bin/env python3
'''Offline checks for tools/review_inventory.py (authored, NOT executed).

Synthetic data only: no network, hub import or writes. Ten methods (<=10).
'''
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import review_inventory as inv  # noqa: E402

OWNER, HUB = 'moruku36', 'moruku36/multi-ai-workflow'
ENF = {'installation_id': 9, 'configured': True, 'protection_verified': True,
       'acceptance': 'passed'}


def repo(rid, name, **over):
    rec = {'id': rid, 'full_name': '%s/%s' % (OWNER, name), 'owner': {'login': OWNER},
           'private': False, 'fork': False, 'archived': False, 'disabled': False,
           'default_branch': 'main'}
    rec.update(over)
    return rec


def build(repos, facts=None, truncated=False, scope='owner', **kw):
    return inv.build_inventory(repos, facts, owner=OWNER, hub=HUB,
                               truncated=truncated, scope=scope, **kw)


def ents(ledger, rid):
    return [e for e in ledger['entries'] if e['repository_id'] == rid]


class InventoryTests(unittest.TestCase):
    def test_every_record_visible_with_reason(self):
        repos = [repo(1, 'ok'), repo(2, 'priv', private=True), repo(3, 'fk', fork=True),
                 repo(4, 'old', archived=True), repo(5, 'off', disabled=True),
                 repo(6, 'multi-ai-workflow'),
                 repo(7, 'x', owner={'login': 'someone'}, full_name='someone/x')]
        led = build(repos, {1: {'installation_id': 9}})
        self.assertEqual((len(led['entries']), led['summary']['total']), (7, 7))
        self.assertEqual(ents(led, 1)[0]['coverage_class'], 'eligible')
        for rid, code in ((2, 'private_consent_pending'), (3, 'fork_manual_required'),
                          (4, 'archived'), (5, 'disabled'), (6, 'hub_self_excluded'),
                          (7, 'not_owner_managed')):
            self.assertIn(code, ents(led, rid)[0]['reasons'])
        self.assertEqual(ents(led, 2)[0]['enrollment'], 'consent_pending')
        self.assertFalse(any(e['enforced'] for e in led['entries']))

    def test_evidence_ladder_and_enforcement(self):
        led = build([repo(1, 'a'), repo(2, 'b'), repo(3, 'c'), repo(4, 'd', fork=True),
                     repo(5, 'e', private=True), repo(6, 'f', archived=True)],
                    {1: {'installation_id': 9},
                     2: {'installation_id': 9, 'configured': True},
                     3: dict(ENF, acceptance='pending'), 4: ENF,
                     5: dict(ENF, consent='granted'), 6: ENF})
        self.assertEqual([ents(led, i)[0]['enrollment'] for i in (1, 2, 3)],
                         ['discovered', 'configured', 'acceptance_pending'])
        self.assertEqual(ents(led, 1)[0]['protection'], 'unknown')
        for rid in (4, 5, 6):  # claimed progress on an ineligible repo is drift
            self.assertEqual(ents(led, rid)[0]['enrollment'], 'degraded')
        self.assertFalse(any(e['enforced'] for e in led['entries']))
        self.assertFalse(led['summary']['all_enforced'])
        self.assertTrue(build([repo(1, 'a')], {1: ENF})['summary']['all_enforced'])

    def test_pagination_and_invalid_limit(self):
        one = [repo(1, 'a')]
        self.assertIn('pagination_truncated',
                      build(one, {1: ENF}, truncated=True)['incomplete_reasons'])
        unknown = build(one, {1: ENF}, truncated=None)
        self.assertIn('pagination_state_unknown', unknown['incomplete_reasons'])
        self.assertFalse(unknown['summary']['all_enforced'])
        at_limit = build([repo(1, 'a'), repo(2, 'b')], limit=2)
        self.assertIn('possibly_truncated_at_limit', at_limit['incomplete_reasons'])
        for bad in (0, -1, True, '5', None):  # never disable the bound
            with self.subTest(limit=bad):
                with self.assertRaises(ValueError):
                    build(one, limit=bad)

    def test_malformed_rows_facts_and_keys_propagate(self):
        led = build([repo(1, 'a'), {'id': 3}, 'junk', repo(5, 'e', private='yes')],
                    {1: ENF})
        self.assertEqual(len(led['entries']), 4)
        self.assertIn('invalid_record_present', led['incomplete_reasons'])
        self.assertFalse(led['complete'] or led['summary']['all_enforced'])
        for e in led['entries']:
            if e['repository_id'] != 1:
                self.assertEqual(e['coverage_class'], 'unverified')
                self.assertFalse(e['enforced'])
        for f in ({'configured': 'yes'}, {'surprise': 1}, {'protection_verified': True},
                  {'configured': True, 'acceptance': 'passed'}):
            with self.subTest(facts=f):
                led = build([repo(1, 'a')], {1: dict(f, installation_id=9)})
                e = led['entries'][0]
                self.assertIn('invalid_facts', e['reasons'])
                self.assertEqual((e['coverage_class'], e['enforced'], e['protection']),
                                 ('unverified', False, 'unknown'))
                self.assertIn('invalid_facts_present', led['incomplete_reasons'])
        alias = build([repo(1, 'a')], {True: ENF})  # True == 1 must not attach
        self.assertFalse(alias['entries'][0]['enforced'])
        self.assertIn('invalid_facts_key', alias['incomplete_reasons'])
        stray = build([repo(1, 'a')], {1: ENF, 2: ENF, '3': ENF})
        self.assertTrue({'unmatched_facts_key', 'invalid_facts_key'}
                        <= set(stray['incomplete_reasons']))
        self.assertFalse(stray['summary']['all_enforced'])

    def test_duplicates_quarantine_every_member(self):
        led = build([repo(1, 'a'), repo(1, 'zz', private=True), repo(2, 'c')], {1: ENF})
        dupes = ents(led, 1)
        self.assertEqual(len(dupes), 2)
        for e in dupes:
            self.assertIn('duplicate_repository_id', e['reasons'])
            self.assertEqual(e['coverage_class'], 'unverified')
            self.assertFalse(e['enforced'])
        self.assertEqual({e['visibility'] for e in dupes}, {'public', 'private'})
        self.assertEqual({e['full_name'] for e in dupes},
                         {'moruku36/a', 'moruku36/zz'})
        self.assertEqual(len({e['key'] for e in led['entries']}), 3)
        self.assertFalse(led['complete'])
        # Trusted projection: both duplicate rows are restricted, ID2 still shown.
        shown = inv.public_view(led, visibility_trusted=True)
        self.assertEqual(len(shown['entries']), 3)
        text = repr(shown)
        for s in ('moruku36/a', 'moruku36/zz', 'dup:1'):
            self.assertNotIn(s, text)
        self.assertIn('moruku36/c', text)
        hidden = [e for e in shown['entries'] if e['key'].startswith('restricted:')]
        self.assertEqual(len(hidden), 2)
        for e in hidden:
            for k in ('repository_id', 'full_name', 'default_branch', 'owner',
                      'installation_id'):
                self.assertNotIn(k, e)
        self.assertNotIn('moruku36/c', repr(inv.public_view(led)))  # default redacts
        self.assertEqual(len(dupes), 2)  # private ledger keeps both identities

    def test_scope_never_implies_owner_wide_enforcement(self):
        one = [repo(1, 'a')]

        def inst(**kw):
            return build(one, {1: ENF}, scope='installation', **kw)
        sub = inst()  # retained clean subset, no universe: listing ok, owner unknown
        self.assertTrue(sub['complete'])
        self.assertFalse(sub['owner_complete'] or sub['summary']['all_enforced'])
        self.assertIn('owner_universe_absent', sub['owner_incomplete_reasons'])
        for ids, tr in (([], False), ([1, 2], False), ([1], None), ([1], True),
                        ([1], 0), ([True], False), ([1, 1], False), ('1', False),
                        ([], None)):
            with self.subTest(ids=ids, truncated=tr):
                led = inst(owner_ids=ids, owner_truncated=tr)
                self.assertFalse(led['owner_complete'] or led['summary']['all_enforced'])
                self.assertTrue(led['owner_incomplete_reasons'])
        extra = build([repo(1, 'a'), repo(2, 'b')], {1: ENF, 2: ENF},
                      scope='installation', owner_ids=[1], owner_truncated=False)
        self.assertFalse(extra['owner_complete'] or extra['summary']['all_enforced'])
        self.assertIn('owner_universe_mismatch', extra['owner_incomplete_reasons'])
        for ids in ([1], (1,), {1}, frozenset({1})):
            led = inst(owner_ids=ids, owner_truncated=False)
            self.assertTrue(led['owner_complete'] and led['summary']['all_enforced'])
            self.assertEqual(led['owner_incomplete_reasons'], [])
        empty = build([], scope='installation', owner_ids=[], owner_truncated=False)
        self.assertTrue(empty['owner_complete'])
        self.assertFalse(empty['summary']['all_enforced'])  # total == 0
        self.assertTrue(build(one, {1: ENF})['owner_complete'])
        mixed = build(one, {1: ENF}, owner_ids=[1])  # owner scope rejects metadata
        self.assertFalse(mixed['owner_complete'])
        self.assertIn('owner_metadata_not_allowed', mixed['owner_incomplete_reasons'])
        for bad in (None, 'team'):
            led = build(one, {1: ENF}, scope=bad)
            self.assertIn('invalid_scope', led['incomplete_reasons'])
            self.assertFalse(led['complete'] or led['summary']['all_enforced'])

    def test_identity_and_branch_must_be_consistent(self):
        led = build([repo(1, 'a', full_name='foreign/a'),
                     repo(2, 'b', owner={'login': 'someone'}),
                     repo(3, 'c', default_branch='m' * 251),
                     repo(4, 'd', default_branch='ma\nin'),
                     repo(5, 'e', default_branch=''),
                     repo(6, 'f', default_branch='m' * 250)],
                    {i: ENF for i in range(1, 7)})
        for rid in range(1, 6):
            e = ents(led, rid)[0]
            self.assertIn('invalid_record', e['reasons'])
            self.assertEqual(e['coverage_class'], 'unverified')
            self.assertFalse(e['enforced'])
        self.assertTrue(ents(led, 6)[0]['enforced'])

    def test_public_view_withholds_identifiers(self):
        led = build([repo(1, 'pubrepo'), repo(2, 'secret-name', private=True),
                     {'id': 3, 'full_name': 'moruku36/odd'}], {1: ENF})
        text = repr(inv.public_view(led))  # trust not established: nothing named
        for s in ('pubrepo', 'secret-name', 'odd', 'repo:', 'repository_id',
                  'default_branch'):
            self.assertNotIn(s, text)
        for loose in ('yes', 1):  # only literal True releases identities
            self.assertNotIn('pubrepo',
                             repr(inv.public_view(led, visibility_trusted=loose)))
        shown = inv.public_view(led, visibility_trusted=True)
        self.assertEqual(len(shown['entries']), 3)
        self.assertIn('moruku36/pubrepo', repr(shown))
        self.assertNotIn('secret-name', repr(shown))
        self.assertNotIn('odd', repr(shown))
        hidden = [e for e in shown['entries'] if e['key'].startswith('restricted:')]
        self.assertEqual(len(hidden), 2)
        for e in hidden:
            self.assertNotIn('repository_id', e)
            self.assertNotIn('full_name', e)

    def test_missing_installation_is_manual_not_eligible(self):
        e = build([repo(1, 'a')], {1: {'configured': True}})['entries'][0]
        self.assertIn('installation_missing', e['reasons'])
        self.assertEqual(e['coverage_class'], 'manual_required')
        self.assertFalse(e['enforced'])

    def test_summary_keeps_every_entry_in_denominator(self):
        s = build([repo(1, 'pub'), repo(2, 'priv', private=True)], {1: ENF})['summary']
        self.assertEqual((s['total'], s['enforced'], s['unprotected_or_unknown']),
                         (2, 1, 1))
        self.assertFalse(s['all_enforced'])


if __name__ == '__main__':
    unittest.main()
