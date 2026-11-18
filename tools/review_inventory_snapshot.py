#!/usr/bin/env python3
'''Disconnected snapshot adapter for tools/review_inventory.py (pure stdlib).

Validates an already-fetched owner/installation envelope, then delegates to
review_inventory.build_inventory (schema 3). No IO, clock, network, hub import
or import-time action. Labels, timestamps and digests are unauthenticated caller
claims, never proof of coverage or protection.
Contract: docs/review-inventory-input-contract.md.
'''
from __future__ import annotations

import datetime
import hashlib
import json

import review_inventory as inv

API_VERSION = 1
MAX_ROWS, MAX_NODES, MAX_DEPTH, MAX_STR = 250, 20000, 8, 300
TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
SOURCES = ('offline_fixture', 'recorded_api_response')
ENV_KEYS = frozenset(('hub', 'owner', 'acquisition', 'owner_repositories',
                      'installation', 'facts', 'digest'))
INST_KEYS = frozenset(('id', 'status', 'account_id', 'account_login',
                       'observed_at', 'complete', 'truncated', 'repositories'))
ACQ_KEYS = frozenset(('source', 'scope', 'observed_at', 'owner_listing'))
# Codes that also degrade complete / owner_complete / all_enforced.
DEGRADING = frozenset(('installation_incomplete', 'installation_unknown_status',
                       'installation_rows_unreconciled',
                       'installation_rows_conflict', 'owner_rows_foreign',
                       'facts_installation_conflict'))


def _fail(code):
    raise ValueError(code)


def _pint(value):
    return type(value) is int and value > 0


def _bounded(root):
    '''Iterative JSON-tree check: no recursion, cycles, aliases, floats or tuples.'''
    stack, seen, nodes = [(root, 0)], set(), 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            _fail('snapshot_too_large')
        kind = type(value)
        if value is None or kind is bool:
            continue
        if kind is int:
            if abs(value) >= 2 ** 63:
                _fail('snapshot_too_large')
        elif kind is str:
            if len(value) > MAX_STR:
                _fail('snapshot_too_large')
        elif kind is list or kind is dict:
            if id(value) in seen:
                _fail('snapshot_not_json')
            seen.add(id(value))
            if len(value) > MAX_NODES:
                _fail('snapshot_too_large')
            if kind is list:
                stack.extend((x, depth + 1) for x in value)
            else:
                for key, item in value.items():
                    if type(key) is not str or len(key) > MAX_STR:
                        _fail('snapshot_not_json')
                    stack.append((item, depth + 1))
        else:
            _fail('snapshot_not_json')


def canonical_digest(envelope):
    '''sha256 of the envelope minus its own digest key (sorted-key compact ASCII
    JSON, no NaN). Binds data to a label; it is NOT a signature.'''
    if type(envelope) is not dict:
        _fail('snapshot_invalid_envelope')
    _bounded(envelope)
    body = {k: v for k, v in envelope.items() if k != 'digest'}
    text = json.dumps(body, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False)
    return 'sha256:' + hashlib.sha256(text.encode('ascii')).hexdigest()


def _time(value):
    if type(value) is not str or len(value) != 20:
        _fail('snapshot_invalid_time')
    try:
        ok = datetime.datetime.strptime(value, TIME_FORMAT).strftime(TIME_FORMAT) == value
    except ValueError:
        ok = False
    if not ok:
        _fail('snapshot_invalid_time')
    return value


def _rows(value, absent_ok):
    if value is None and absent_ok:
        return None
    if type(value) is not list or len(value) > MAX_ROWS:
        _fail('snapshot_invalid_rows')
    return value


def _owner(value):
    if (type(value) is not dict or set(value) != {'id', 'login'}
            or not _pint(value['id']) or type(value['login']) is not str
            or not inv.LOGIN.fullmatch(value['login'])):
        _fail('snapshot_invalid_owner')
    return value


def _acq(value):
    if (type(value) is not dict or set(value) != ACQ_KEYS
            or value['source'] not in SOURCES
            or value['scope'] not in ('owner', 'installation')):
        _fail('snapshot_invalid_acquisition')
    _time(value['observed_at'])
    listing = value['owner_listing']
    if (type(listing) is not dict or set(listing) != {'complete', 'truncated'}
            or type(listing['complete']) is not bool
            or type(listing['truncated']) is not bool):
        _fail('snapshot_invalid_acquisition')
    return value


def _norm(row, owner):
    '''Shallow projection; never mutates input. An explicit visibility that is
    not public/private or contradicts the bool, or a row owner.id that disagrees
    with the target login, becomes private=None so the landed classifier marks
    the row invalid (never silently public). Absent visibility keeps the landed
    bool-only contract.'''
    if type(row) is not dict:
        return row
    bad = False
    if 'visibility' in row:
        vis, flag = row['visibility'], row.get('private')
        bad = not (vis in ('public', 'private') and type(flag) is bool
                   and (vis == 'private') == flag)
    who = row.get('owner')
    if type(who) is dict and 'id' in who and type(who.get('login')) is str:
        mine = who['login'].casefold() == owner['login'].casefold()
        bad = bad or mine != (type(who['id']) is int and who['id'] == owner['id'])
    return dict(row, private=None) if bad else row


def _install(value, owner, observed):
    '''Return (state, installation, rows, fault). Rows are always kept. Only state
    'bound' (identity binding AND complete metadata) may grant access.'''
    if value is None:
        return 'absent', None, [], False
    if (type(value) is not dict or set(value) != INST_KEYS or not _pint(value['id'])
            or type(value['status']) is not str
            or type(value['complete']) is not bool
            or type(value['truncated']) is not bool):
        _fail('snapshot_invalid_installation')
    rows = _rows(value['repositories'], False)
    _time(value['observed_at'])
    fault = not value['complete'] or value['truncated'] or len(rows) >= MAX_ROWS
    if value['status'] not in ('active', 'suspended'):
        state = 'unknown_status'
    elif value['status'] != 'active':
        state = 'not_active'
    elif (type(value['account_id']) is not int or value['account_id'] != owner['id']
            or type(value['account_login']) is not str
            or value['account_login'].casefold() != owner['login'].casefold()):
        state = 'mismatch'
    elif value['observed_at'] != observed:
        state = 'stale'
    else:
        state = 'incomplete' if fault else 'bound'
    return state, value, rows, fault


def _facts(value):
    if type(value) is not list or len(value) > MAX_ROWS:
        _fail('snapshot_invalid_facts')
    out = {}
    for item in value:
        if (type(item) is not dict or set(item) != {'repository_id', 'facts'}
                or not _pint(item['repository_id']) or type(item['facts']) is not dict):
            _fail('snapshot_invalid_facts')
        if item['repository_id'] in out:
            _fail('snapshot_facts_duplicate')
        out[item['repository_id']] = dict(item['facts'])
    return out


def _trunc(complete, truncated):
    if truncated is True:
        return True
    return False if complete is True and truncated is False else None


def _row_id(row):
    if type(row) is dict and _pint(row.get('id')):
        return row['id']
    return None


def _name_conflicts(rows):
    '''IDs sharing one casefolded structurally valid full_name with another ID.'''
    names = {}
    for r in rows:
        i = _row_id(r)
        n = r.get('full_name') if i is not None else None
        if type(n) is str and inv.REPO.fullmatch(n):
            names.setdefault(n.casefold(), set()).add(i)
    return {i for ids in names.values() if len(ids) > 1 for i in ids}


def _foreign(row, login):
    who = row.get('owner') if type(row) is dict else None
    return (type(who) is dict and type(who.get('login')) is str
            and who['login'].casefold() != login.casefold())


def _split(irows, orows, login):
    '''Count and validate installation rows BEFORE any set collapse. Returns
    (extras, access_ids, codes). Only a unique, structurally valid row exactly
    equal (normalized fields) to the unique valid owner row of the same ID is
    folded away and may get access; every other row is retained so the ledger
    quarantines its ID. orows None = installation-only scope.'''
    cnt, ocnt, owners, ok, extras = {}, {}, {}, set(), []
    rows = list(irows) + list(orows or ())
    bad = _name_conflicts(rows)
    codes = {'installation_rows_conflict'} if bad else set()
    foreign = [r for r in rows if _foreign(r, login)]
    if foreign:
        codes.add('owner_rows_foreign')
    for r in irows:
        i = _row_id(r)
        if i is not None:
            cnt[i] = cnt.get(i, 0) + 1
    for r in orows or ():
        i = _row_id(r)
        if i is not None:
            ocnt[i] = ocnt.get(i, 0) + 1
            owners[i] = r
    for r in irows:
        i = _row_id(r)
        fields, valid = inv._clean_repo(r)
        if i is None:
            extras.append(r)
            codes.add('installation_rows_conflict')
        elif orows is None:
            extras.append(r)
            if cnt[i] == 1 and valid:
                ok.add(i)
            else:
                codes.add('installation_rows_conflict')
        elif i not in ocnt:
            extras.append(r)
            codes.add('installation_rows_unreconciled')
        else:
            ofields, ovalid = inv._clean_repo(owners[i])
            if cnt[i] == 1 and ocnt[i] == 1 and valid and ovalid and fields == ofields:
                ok.add(i)
            else:
                extras.append(r)
                codes.add('installation_rows_conflict')
    return extras, ok - bad - {_row_id(r) for r in foreign}, codes


def _degrade(ledger, code):
    ledger['incomplete_reasons'] = sorted(set(ledger['incomplete_reasons']) | {code})
    ledger['complete'] = ledger['owner_complete'] = False
    ledger['summary']['all_enforced'] = False


def adapt_snapshot(envelope):
    '''Validate and classify one envelope. Structural faults raise ValueError
    with a fixed generic code; partial or faulty snapshots return a structured
    incomplete result. Keys: schema_version, status, digest, digest_verified,
    evidence, acquisition, installation_state, adapter_reasons, ledger (PRIVATE),
    public (redacted, visibility_trusted=False; no IDs, names, digest, time).'''
    if (type(envelope) is not dict or len(envelope) > len(ENV_KEYS)
            or not set(envelope) <= ENV_KEYS
            or not ENV_KEYS - {'digest'} <= set(envelope)):
        _fail('snapshot_invalid_envelope')
    digest = canonical_digest(envelope)
    verified = 'digest' in envelope
    if verified and envelope['digest'] != digest:
        _fail('snapshot_digest_mismatch')
    hub = envelope['hub']
    if type(hub) is not str or not inv.REPO.fullmatch(hub):
        _fail('snapshot_invalid_hub')
    owner = _owner(envelope['owner'])
    acq = _acq(envelope['acquisition'])
    orows = _rows(envelope['owner_repositories'], True)
    if (orows is not None) != (acq['scope'] == 'owner'):
        _fail('snapshot_scope_mismatch')
    state, inst, irows, fault = _install(envelope['installation'], owner,
                                         acq['observed_at'])
    fm = _facts(envelope['facts'])
    if orows is not None:
        orows = [_norm(r, owner) for r in orows]
    extras, ok, codes = _split([_norm(r, owner) for r in irows], orows,
                             owner['login'])
    if state != 'bound':
        codes.add('installation_' + state)
    if fault:
        codes.add('installation_incomplete')
    if orows is None:
        repos, scope = extras, 'installation'
        trunc = _trunc(inst['complete'], inst['truncated']) if inst else None
    else:
        repos, scope = orows + extras, 'owner'
        listing = acq['owner_listing']
        trunc = _trunc(listing['complete'], listing['truncated'])
    if len(repos) > MAX_ROWS:
        _fail('snapshot_invalid_rows')
    iid = inst['id'] if state == 'bound' else None
    bad = set()
    for rid, facts in fm.items():  # a supplied installation_id never grants access
        if 'installation_id' in facts:
            given = facts.pop('installation_id')
            if given is not None and not (iid is not None and rid in ok
                                          and type(given) is int and given == iid):
                bad.add(rid)
                codes.add('facts_installation_conflict')
    if iid is not None:
        for rid in ok - bad:
            fm.setdefault(rid, {})['installation_id'] = iid
    ledger = inv.build_inventory(repos, fm, owner=owner['login'], hub=hub,
                                 truncated=trunc, scope=scope, limit=MAX_ROWS)
    for code in sorted(codes & DEGRADING):
        _degrade(ledger, code)
    reasons = sorted(codes)
    status = 'owner_complete' if ledger['owner_complete'] else 'incomplete'
    public = inv.public_view(ledger, visibility_trusted=False)
    public['adapter'] = {'status': status, 'installation_state': state,
                         'digest_verified': verified, 'reasons': reasons}
    return {
        'schema_version': API_VERSION,
        'status': status,
        'digest': digest,
        'digest_verified': verified,
        'evidence': 'unauthenticated_snapshot',
        'acquisition': {'source': acq['source'], 'scope': acq['scope'],
                        'observed_at': acq['observed_at']},
        'installation_state': state,
        'adapter_reasons': reasons,
        'ledger': ledger,
        'public': public,
    }
