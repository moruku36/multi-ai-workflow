#!/usr/bin/env python3
'''Offline tests for tools/review_inventory_snapshot.py (stdlib only).'''
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import review_inventory_snapshot as snap  # noqa: E402

T = '2026-11-19T00:00:00Z'


def row(i, **kw):
    r = {'id': i, 'name': 'r%d' % i, 'full_name': 'me/r%d' % i, 'private': False,
         'fork': False, 'archived': False, 'disabled': False,
         'default_branch': 'main', 'owner': {'id': 7, 'login': 'me'}}
    r.update(kw)
    return r


def inst(rows, **kw):
    d = {'id': 5, 'status': 'active', 'account_id': 7, 'account_login': 'me',
         'observed_at': T, 'complete': True, 'truncated': False, 'repositories': rows}
    d.update(kw)
    return d


def env(orows=None, **kw):
    orows = [row(1), row(2)] if orows is None else orows
    e = {'hub': 'me/hub', 'owner': {'id': 7, 'login': 'me'},
         'acquisition': {'source': 'offline_fixture', 'scope': 'owner', 'observed_at': T,
                         'owner_listing': {'complete': True, 'truncated': False}},
         'owner_repositories': orows, 'installation': inst(copy.deepcopy(orows)),
         'facts': []}
    e.update(kw)
    return e


def run(e):
    return snap.adapt_snapshot(e)


class SnapshotTests(unittest.TestCase):
    def code(self, e, c):
        with self.assertRaises(ValueError) as cm:
            run(e)
        self.assertEqual(str(cm.exception), c)

    def test_positive_and_installation_only(self):
        r = run(env())
        self.assertEqual(r['installation_state'], 'bound')
        self.assertEqual(r['adapter_reasons'], [])
        self.assertFalse(r['ledger']['summary']['all_enforced'])
        self.assertEqual(r['evidence'], 'unauthenticated_snapshot')
        self.assertFalse(r['digest_verified'])
        e = env(owner_repositories=None)
        e['acquisition']['scope'] = 'installation'
        r = run(e)
        self.assertEqual(r['installation_state'], 'bound')
        self.assertFalse(r['ledger']['owner_complete'])
        self.assertFalse(r['ledger']['summary']['all_enforced'])
        self.assertEqual(r['status'], 'incomplete')

    def test_installation_states(self):
        cases = [('not_active', {'status': 'suspended'}),
                 ('unknown_status', {'status': 'x'}),
                 ('mismatch', {'account_id': 8}),
                 ('stale', {'observed_at': '2026-11-18T00:00:00Z'}),
                 ('incomplete', {'complete': False}),
                 ('incomplete', {'truncated': True})]
        for state, kw in cases:
            with self.subTest(kw=kw):
                r = run(env(installation=inst([row(1), row(2)], **kw)))
                self.assertEqual(r['installation_state'], state)
                self.assertIn('installation_' + state, r['adapter_reasons'])
        rows = [row(i) for i in range(1, 251)]
        r = run(env(orows=rows))
        self.assertEqual(r['installation_state'], 'incomplete')
        self.assertEqual(r['status'], 'incomplete')

    def test_absence_and_owner_incomplete(self):
        r = run(env(installation=None))
        self.assertEqual(r['installation_state'], 'absent')
        self.assertIn('installation_absent', r['adapter_reasons'])
        e = env()
        e['acquisition']['owner_listing']['complete'] = False
        self.assertEqual(run(e)['status'], 'incomplete')
        self.code(env(owner_repositories=None), 'snapshot_scope_mismatch')

    def test_overlap_isolation(self):
        cases = [('installation_rows_unreconciled', [row(1), row(2), row(9)]),
                 ('installation_rows_conflict', [row(1), row(1), row(2)]),
                 ('installation_rows_conflict', [row(1, visibility='internal'), row(2)]),
                 ('installation_rows_conflict', [row(1, visibility='private'), row(2)]),
                 ('installation_rows_conflict',
                  [row(1, owner={'id': 99, 'login': 'me'}), row(2)]),
                 ('installation_rows_conflict', [row(1), {'id': 2}])]
        for reason, rows in cases:
            with self.subTest(reason=reason, rows=rows):
                r = run(env(installation=inst(rows)))
                self.assertIn(reason, r['adapter_reasons'])
                self.assertEqual(r['status'], 'incomplete')

        e = env(installation=inst([row(1), row(1), row(2)]),
                facts=[{'repository_id': 2, 'facts': {'installation_id': 5}}])
        self.assertNotIn('facts_installation_conflict', run(e)['adapter_reasons'])
        dup = [row(1), row(2, full_name='ME/R1')]
        facts = [{'repository_id': i, 'facts': {'installation_id': 5}} for i in (1, 2)]
        r = run(env(orows=dup, facts=facts))
        self.assertIn('installation_rows_conflict', r['adapter_reasons'])
        self.assertIn('facts_installation_conflict', r['adapter_reasons'])
        self.assertFalse(r['ledger']['summary']['all_enforced'])
        alien = row(3, full_name='you/r3', owner={'id': 8, 'login': 'you'})
        r = run(env(orows=[row(1), alien],
                    installation=inst([row(1), copy.deepcopy(alien)]),
                    facts=[{'repository_id': 3, 'facts': {'installation_id': 5}}]))
        self.assertIn('owner_rows_foreign', r['adapter_reasons'])
        self.assertIn('facts_installation_conflict', r['adapter_reasons'])
        self.assertFalse(r['ledger']['owner_complete'])
        e = env(owner_repositories=None, installation=inst([row(1), alien]))
        e['acquisition']['scope'] = 'installation'
        r = run(e)
        self.assertIn('owner_rows_foreign', r['adapter_reasons'])
        self.assertFalse(r['ledger']['owner_complete'])

    def test_facts_installation_claims(self):
        bad = [{'repository_id': 1, 'facts': {'installation_id': 999}}]
        r = run(env(facts=bad))
        self.assertIn('facts_installation_conflict', r['adapter_reasons'])
        self.assertEqual(r['status'], 'incomplete')
        good = [{'repository_id': 1, 'facts': {'installation_id': 5}}]
        self.assertNotIn('facts_installation_conflict', run(env(facts=good))['adapter_reasons'])
        r = run(env(installation=None, facts=good))
        self.assertIn('facts_installation_conflict', r['adapter_reasons'])
        self.code(env(facts=good + copy.deepcopy(good)), 'snapshot_facts_duplicate')

    def test_retained_union_overflow(self):
        rows = [row(i) for i in range(1, 201)]
        extra = [row(i) for i in range(1001, 1101)]
        mixed = copy.deepcopy(rows[:150]) + extra
        self.code(env(orows=rows, installation=inst(mixed)), 'snapshot_invalid_rows')

    def test_digest(self):
        e = env()
        e['digest'] = snap.canonical_digest(e)
        self.assertTrue(e['digest'].startswith('sha256:'))
        self.assertTrue(run(e)['digest_verified'])
        e['hub'] = 'me/other'
        self.code(e, 'snapshot_digest_mismatch')
        e['digest'] = None
        self.code(e, 'snapshot_digest_mismatch')

    def test_structure_limits(self):
        shared = row(1)
        cyc = []
        cyc.append(cyc)
        deep = {}
        for _ in range(10):
            deep = {'a': deep}
        bad_time = env()
        bad_time['acquisition']['observed_at'] = '2026-11-19'
        cases = [(env(orows=[shared], installation=inst([shared])), 'snapshot_not_json'),
                 (env(facts=[cyc]), 'snapshot_not_json'),
                 (env(orows=[row(1, stars=1.5)]), 'snapshot_not_json'),
                 (env(orows=[row(1, name='x' * 301)]), 'snapshot_too_large'),
                 (env(facts=[deep]), 'snapshot_too_large'),
                 (env(facts=list(range(20001))), 'snapshot_too_large'),
                 (env(extra=1), 'snapshot_invalid_envelope'),
                 ([], 'snapshot_invalid_envelope'),
                 (env(hub='x'), 'snapshot_invalid_hub'),
                 (bad_time, 'snapshot_invalid_time')]
        for e, c in cases:
            with self.subTest(code=c):
                self.code(e, c)

    def test_public_redaction(self):
        r = run(env())
        text = json.dumps(r['public'])
        for needle in ('me/r1', 'r1', '2026-11-19', 'sha256', r['digest']):
            self.assertNotIn(needle, text)
        for key in ('"id"', '"full_name"', '"repository_id"', '"installation_id"'):
            self.assertNotIn(key, text)
        self.assertEqual(r['public']['adapter']['installation_state'], 'bound')

    def test_no_mutation_and_determinism(self):
        e = env(facts=[{'repository_id': 1, 'facts': {'installation_id': 5}}])
        before = copy.deepcopy(e)
        a, b = run(e), run(e)
        self.assertEqual(e, before)
        self.assertEqual(a['digest'], b['digest'])
        self.assertEqual(a['adapter_reasons'], b['adapter_reasons'])


if __name__ == '__main__':
    unittest.main()
