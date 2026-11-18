#!/usr/bin/env python3
'''P2a repository inventory ledger: pure, offline, DISCONNECTED shadow module.

Classifies already-fetched repository records plus caller-supplied facts. No
network, credentials, hub import or activation. Facts and trust flags are bare
caller claims, NOT authenticated evidence: 'enforced' here means 'claimed
enforced'. Design: docs/global-review-design.ja.md section 4, 5, 6, 9.

Every record stays visible and unknown stays None. Malformed rows or facts,
duplicate IDs, truncation or an unreconciled scope make the listing incomplete
(complete); owner completeness (owner_complete) is derived from listing
completeness plus an explicit, exactly reconciled owner universe. Only an
owner-complete ledger can claim all_enforced.
'''
from __future__ import annotations

import re

SCHEMA_VERSION = 3
DEFAULT_LIMIT = 250  # same bound as the existing hub's installation listing
REPO = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z')
LOGIN = re.compile(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}\Z')

ENROLLMENT = ('discovered', 'consent_pending', 'configured', 'protection_verified',
              'acceptance_pending', 'enforced', 'degraded')
COVERAGE = ('eligible', 'manual_required', 'excluded', 'unverified')
_PRECEDENCE = {name: rank for rank, name in enumerate(COVERAGE)}
FACT_KEYS = {'installation_id', 'consent', 'configured', 'protection_verified',
             'acceptance', 'degraded'}

# reason code -> (coverage class it forces, operator action)
REASONS = {
    'invalid_record': ('unverified', 'fix_inventory_input'),
    'invalid_facts': ('unverified', 'fix_inventory_input'),
    'duplicate_repository_id': ('unverified', 'fix_inventory_input'),
    'not_owner_managed': ('excluded', 'provide_review_evidence_only'),
    'hub_self_excluded': ('excluded', 'use_trusted_controller_update_path'),
    'archived': ('excluded', 'enrollment_stopped_protection_not_possible'),
    'disabled': ('excluded', 'enrollment_stopped_protection_not_possible'),
    'private_consent_pending': ('manual_required', 'decide_external_send_consent'),
    'private_unsupported': ('manual_required', 'keep_manual_no_external_send'),
    'fork_manual_required': ('manual_required', 'manual_review_required'),
    'installation_missing': ('manual_required', 'install_or_verify_app_access'),
}
_ENROLLMENT_ACTION = {
    'discovered': 'configure_policy_and_protection',
    'consent_pending': 'decide_external_send_consent',
    'configured': 'readback_protection',
    'protection_verified': 'run_negative_merge_acceptance',
    'acceptance_pending': 'complete_acceptance',
    'enforced': 'none_monitor_drift',
    'degraded': 'investigate_degradation_and_hold_merge',
}
_REASON_ORDER = tuple(REASONS)  # action priority follows this order


def _is_int(value):
    return type(value) is int and value > 0


def _clean_facts(raw):
    '''Return (facts, ok); strict types, any inconsistency gives ok False.'''
    blank = {'installation_id': None, 'consent': None, 'configured': False,
             'protection_verified': None, 'acceptance': None, 'degraded': False}
    if raw is None:
        return blank, True
    if not isinstance(raw, dict) or not set(raw) <= FACT_KEYS:
        return blank, False
    f = dict(blank, **raw)
    ok = (
        (f['installation_id'] is None or _is_int(f['installation_id']))
        and f['consent'] in (None, 'pending', 'granted', 'denied')
        and type(f['configured']) is bool
        and type(f['degraded']) is bool
        and (f['protection_verified'] is None or type(f['protection_verified']) is bool)
        and f['acceptance'] in (None, 'pending', 'passed')
    )
    # Evidence must not outrun the step before it.
    if ok and f['protection_verified'] is True and not f['configured']:
        ok = False
    if ok and f['acceptance'] is not None and f['protection_verified'] is not True:
        ok = False
    return (f if ok else blank), ok


def _clean_repo(raw):
    '''Return (fields, ok); invalid or missing fields become None, never guessed.'''
    fields = {'repository_id': None, 'full_name': None, 'owner': None,
              'visibility': None, 'fork': None, 'archived': None,
              'disabled': None, 'default_branch': None}
    if not isinstance(raw, dict):
        return fields, False
    ok = True
    if _is_int(raw.get('id')):
        fields['repository_id'] = raw['id']
    else:
        ok = False
    name = raw.get('full_name')
    if isinstance(name, str) and REPO.fullmatch(name):
        fields['full_name'] = name
    else:
        ok = False
    owner = raw.get('owner')
    login = owner.get('login') if isinstance(owner, dict) else None
    if isinstance(login, str) and LOGIN.fullmatch(login):
        fields['owner'] = login
    else:
        ok = False
    if ok and name.split('/')[0].lower() != login.lower():
        ok = False  # full_name prefix and owner.login must agree
    if type(raw.get('private')) is bool:
        fields['visibility'] = 'private' if raw['private'] else 'public'
    else:
        ok = False
    for key in ('fork', 'archived', 'disabled'):
        if type(raw.get(key)) is bool:
            fields[key] = raw[key]
        else:
            ok = False
    branch = raw.get('default_branch')
    if (isinstance(branch, str) and 0 < len(branch) <= 250
            and not any(ord(c) < 32 or ord(c) == 127 for c in branch)):
        fields['default_branch'] = branch
    else:
        ok = False
    return fields, ok


def _enrollment(facts, coverage):
    claimed = (facts['configured'] or facts['protection_verified'] is True
               or facts['acceptance'] is not None)
    if coverage != 'eligible':
        # Progress claims on an ineligible repository are drift, never a pass.
        return 'degraded' if claimed else 'discovered'
    if facts['degraded']:
        return 'degraded'
    if not facts['configured']:
        return 'discovered'
    if facts['protection_verified'] is not True:
        return 'configured'
    if facts['acceptance'] == 'passed':
        return 'enforced'
    if facts['acceptance'] == 'pending':
        return 'acceptance_pending'
    return 'protection_verified'


def classify(raw_repo, raw_facts=None, *, owner, hub, extra=()):
    '''One ledger entry. Always returns an entry for any repository/facts input;
    owner, hub and extra are trusted, valid parameters (not validated here).'''
    fields, repo_ok = _clean_repo(raw_repo)
    facts, facts_ok = _clean_facts(raw_facts)
    reasons = set(extra)
    if not repo_ok:
        reasons.add('invalid_record')
    if not facts_ok:
        reasons.add('invalid_facts')
    if repo_ok:
        if fields['owner'].lower() != owner.lower():
            reasons.add('not_owner_managed')
        if fields['full_name'].lower() == hub.lower():
            reasons.add('hub_self_excluded')
        if fields['archived']:
            reasons.add('archived')
        if fields['disabled']:
            reasons.add('disabled')
        if fields['visibility'] == 'private':
            reasons.add('private_consent_pending' if facts['consent'] != 'granted'
                        else 'private_unsupported')
        if fields['fork']:
            reasons.add('fork_manual_required')
        if (fields['visibility'] == 'public' and not fields['fork']
                and facts['installation_id'] is None):
            reasons.add('installation_missing')
    coverage = 'eligible'
    for code in reasons:
        if _PRECEDENCE[REASONS[code][0]] > _PRECEDENCE[coverage]:
            coverage = REASONS[code][0]
    enrollment = _enrollment(facts, coverage)
    if (fields['visibility'] == 'private' and coverage != 'eligible'
            and enrollment == 'discovered' and facts['consent'] != 'granted'):
        enrollment = 'consent_pending'
    pv = facts['protection_verified']
    action = next((REASONS[c][1] for c in _REASON_ORDER if c in reasons),
                  _ENROLLMENT_ACTION[enrollment])
    entry = dict(fields)
    entry.update({
        'installation_id': facts['installation_id'],
        'consent': facts['consent'],
        'enrollment': enrollment,
        'protection': 'unknown' if pv is None else ('verified' if pv else 'unverified'),
        'coverage_class': coverage,
        'reasons': sorted(reasons),
        'enforced': enrollment == 'enforced' and coverage == 'eligible',
        'operator_action': action,
    })
    return entry


def build_inventory(repos, facts_by_id=None, *, owner, hub, truncated, scope,
                    owner_ids=None, owner_truncated=None, limit=DEFAULT_LIMIT):
    '''Build the whole ledger.

    truncated: pagination state of the repos reader (True/False; None = unknown
    = incomplete). scope 'owner': repos is the full owner listing; owner_ids and
    owner_truncated are installation-only and rejected here. scope 'installation':
    repos is a subset; owner-complete only if owner_ids (finite list/tuple/set/
    frozenset of distinct positive ints, from an independent owner reader) equals
    the valid listed IDs exactly AND owner_truncated is literally False. All of
    this is unauthenticated caller claim. Any other scope is invalid.
    '''
    if not _is_int(limit):
        raise ValueError('limit must be a positive int')
    bad = set()
    if not isinstance(repos, list):
        repos, bad = [], {'invalid_input'}
    fmap = {}
    if isinstance(facts_by_id, dict):
        for k, v in facts_by_id.items():
            if _is_int(k):  # bool keys alias 1/0 and are rejected here
                fmap[k] = v
            else:
                bad.add('invalid_facts_key')
    elif facts_by_id is not None:
        bad.add('invalid_facts_input')
    if truncated is True:
        bad.add('pagination_truncated')
    elif truncated is not False:
        bad.add('pagination_state_unknown')
    if len(repos) >= limit:
        bad.add('possibly_truncated_at_limit')
    ids = [r.get('id') if isinstance(r, dict) else None for r in repos]
    counts = {}
    for rid in ids:
        if _is_int(rid):
            counts[rid] = counts.get(rid, 0) + 1
    if set(fmap) - set(counts):
        bad.add('unmatched_facts_key')
    entries = []
    for index, (raw, rid) in enumerate(zip(repos, ids)):
        good = _is_int(rid)
        dup = good and counts[rid] > 1
        entry = classify(raw, fmap.get(rid) if good else None, owner=owner, hub=hub,
                         extra=('duplicate_repository_id',) if dup else ())
        for code in ('duplicate_repository_id', 'invalid_record', 'invalid_facts'):
            if code in entry['reasons']:
                bad.add(code + '_present')  # every conflicting member is quarantined
        entry['key'] = ('dup:%d:%d' % (rid, index) if dup else
                        'repo:%d' % rid if good else 'unidentified:%d' % index)
        entries.append(entry)
    entries.sort(key=lambda e: e['key'])
    owner_bad = set()  # owner-universe reasons, separate from listing reasons
    if scope == 'owner':
        scoped = owner_ids is None and owner_truncated is None
        if not scoped:
            owner_bad.add('owner_metadata_not_allowed')
    elif scope == 'installation':
        if owner_ids is None:
            owner_bad.add('owner_universe_absent')
        elif (type(owner_ids) not in (list, tuple, set, frozenset)
              or not all(_is_int(i) for i in owner_ids)
              or len(set(owner_ids)) != len(owner_ids)):
            owner_bad.add('owner_universe_invalid')
        else:
            if set(owner_ids) != set(counts):
                owner_bad.add('owner_universe_mismatch')
            if owner_truncated is not False:
                owner_bad.add('owner_truncated_or_unknown')
        scoped = not owner_bad
    else:
        scoped, scope = False, None
        bad.add('invalid_scope')
    complete = not bad
    owner_complete = complete and scoped
    return {
        'schema_version': SCHEMA_VERSION,
        'evidence': 'caller_claims_unauthenticated',
        'scope': scope,
        'complete': complete,
        'owner_complete': owner_complete,
        'incomplete_reasons': sorted(bad),
        'owner_incomplete_reasons': sorted(owner_bad),
        'entries': entries,
        'summary': summarize(entries, owner_complete),
    }


def summarize(entries, owner_complete):
    '''Counts with every entry in the denominator; unknowns are not zeroed.'''
    by_enrollment = {name: 0 for name in ENROLLMENT}
    by_coverage = {name: 0 for name in COVERAGE}
    by_reason = {}
    for e in entries:
        by_enrollment[e['enrollment']] += 1
        by_coverage[e['coverage_class']] += 1
        for code in e['reasons']:
            by_reason[code] = by_reason.get(code, 0) + 1
    total = len(entries)
    enforced = sum(1 for e in entries if e['enforced'])
    return {
        'total': total,
        'enforced': enforced,
        'unprotected_or_unknown': total - enforced,
        'by_enrollment': by_enrollment,
        'by_coverage_class': by_coverage,
        'by_reason': dict(sorted(by_reason.items())),
        # Never true for a subset, incomplete or empty ledger.
        'all_enforced': bool(owner_complete and total > 0 and enforced == total),
    }


_PUBLIC_KEYS = ('visibility', 'fork', 'archived', 'disabled', 'enrollment',
                'protection', 'coverage_class', 'reasons', 'enforced',
                'operator_action')
_PUBLIC_TOP = ('schema_version', 'evidence', 'scope', 'complete', 'owner_complete',
               'incomplete_reasons', 'owner_incomplete_reasons', 'summary')
_WITHHELD = frozenset(('invalid_record', 'duplicate_repository_id'))


def public_view(inventory, *, visibility_trusted=False):
    '''Redacted projection. Key, repository ID and name appear only when
    visibility_trusted is literally True (a caller claim of a trusted visibility
    readback, not credentials or release authority) AND the row is a valid,
    non-duplicate public one. All other rows (private, unknown, malformed and
    every unresolved duplicate) get content-ordered restricted:N keys and no
    identifiers; their identities belong only in the private ledger.'''
    shown, hidden = [], []
    for e in inventory['entries']:
        item = {k: e[k] for k in _PUBLIC_KEYS}
        if (visibility_trusted is True and e['visibility'] == 'public'
                and e['full_name'] is not None
                and not _WITHHELD & set(e['reasons'])):
            item.update(key=e['key'], repository_id=e['repository_id'],
                        full_name=e['full_name'])
            shown.append(item)
        else:
            hidden.append(item)
    hidden.sort(key=lambda i: repr(sorted(i.items())))
    for n, item in enumerate(hidden):
        item['key'] = 'restricted:%d' % n
    out = {k: inventory[k] for k in _PUBLIC_TOP}
    out['entries'] = shown + hidden
    return out
