#!/usr/bin/env python3
# Trusted-base bootstrap for the snapshot regression. Only base-owned code runs; the PR head is read purely as Git
# data (fetched ref + bounded cat-file), never checked out or imported. Composes the SHA-pinned base helper loaded
# from bytes into an isolated namespace. Consistency checks only, not attestation.
import hashlib, json, os, signal, stat, sys, time, types, uuid

HELPER = 'check_review_inventory_ci.py'
HELPER_SHA = '0ef2b742fcdf45a14dbbc409eca181fab98910f0d55f009515f0c3aed901d4b3'
REPO, REPO_ID, HEADBR = 'moruku36/multi-ai-workflow', 1365934149, 'feat/review-inventory-snapshot-v1'
WF = '.github/workflows/snapshot-trusted.yml'
INV, SNAP = 'tools/review_inventory.py', 'tools/review_inventory_snapshot.py'
TST, DOC = 'tests/check_review_inventory_snapshot.py', 'docs/review-inventory-input-contract.md'
PINS = {
  INV: 'd48f1d1ecdd9885beca1db2fca9b7067ed6784cbeaff9c5e9d08eccaa98ae782',
  SNAP: '077bc2890841c6c5cd4a90fa2193cbde094037de684141b7af11144c5a5c5a58',
  TST: 'dc4b3a896a98c58b41f8376fc9d041fe87f248e0fe05cdcf5a4ca27d789aff58',
  DOC: '34c4ab75603ba5a3c693ed68cea5c03fe6b618f23fe423a8791f96626107b597',
}
ADDED = sorted((SNAP, TST, DOC))
# path -> (stage file, container destination); the snapshot test sits at the old guard-visible alias path.
RUN = {INV: ('review_inventory.py', '/target/tools/review_inventory.py'),
  SNAP: ('review_inventory_snapshot.py', '/target/tools/review_inventory_snapshot.py'),
  TST: ('check_review_inventory.py', '/target/tests/check_review_inventory.py')}
TESTS = (
  'test_positive_and_installation_only', 'test_installation_states', 'test_absence_and_owner_incomplete',
  'test_overlap_isolation', 'test_facts_installation_claims', 'test_retained_union_overflow', 'test_digest',
  'test_structure_limits', 'test_public_redaction', 'test_no_mutation_and_determinism',
)
H = None

DRIVER = r'''
import hashlib, json, os, runpy, stat, sys, unittest
PINS, EXPECTED, BAD = %P%, %T%, %B%
mi = {}
for line in open('/proc/self/mountinfo'):
  f = line.split(' - ', 1)[0].split()
  mi[f[4]] = set(f[5].split(','))
for p, h in PINS.items():
  assert p in mi and 'ro' in mi[p], p
  assert stat.S_ISREG(os.stat(p).st_mode), p
  assert hashlib.sha256(open(p, 'rb').read()).hexdigest() == h, p
ns = runpy.run_path('/target/tests/check_review_inventory.py', run_name='snapshot_target')
cls = ns['SnapshotTests']
assert issubclass(cls, unittest.TestCase)
names = sorted(unittest.TestLoader().getTestCaseNames(cls))
assert names == sorted(EXPECTED), names
r = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(unittest.TestSuite(cls(n) for n in names))
S = {'tests': r.testsRun, 'names': names, 'failures': len(r.failures), 'errors': len(r.errors),
  'skipped': len(r.skipped), 'expected_failures': len(r.expectedFailures),
  'unexpected_successes': len(r.unexpectedSuccesses)}
S['ok'] = bool(r.wasSuccessful() and r.testsRun == 10 and not any(S[k] for k in BAD))
print('SNAPSHOT_RESULT ' + json.dumps(S, sort_keys=True), flush=True)
sys.exit(0 if S['ok'] else 1)
'''


def load_helper():
  here = os.path.dirname(os.path.realpath(__file__))
  fd = os.open(here + '/' + HELPER, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
  try:
    if not stat.S_ISREG(os.fstat(fd).st_mode):
      raise ValueError('helper not a regular file')
    data = b''
    while len(data) <= 131072:
      c = os.read(fd, 65536)
      if not c:
        break
      data += c
  finally:
    os.close(fd)
  if len(data) > 131072 or hashlib.sha256(data).hexdigest() != HELPER_SHA:
    raise ValueError('helper pin mismatch')
  mod = types.ModuleType('pinned_inventory_helper')
  exec(compile(data, HELPER, 'exec'), mod.__dict__)
  return mod, here


def require(cond, msg):
  H.require(cond, msg)


def guard_src():
  require(set(H.STAGED_DST) <= {d for _, d in RUN.values()}, 'guard mounts drift')
  pins = {d: PINS[p] for p, (_, d) in RUN.items()}
  d = DRIVER.replace('%T%', repr(TESTS)).replace('%B%', repr(H.BAD)).replace('%P%', repr(pins))
  marks = ('%D%', '%T%', '%B%', '%P%')
  require(H.GUARD_HEAD.count('%D%') == 1 and not any(m in d for m in marks), 'driver placeholder drift')
  g = H.GUARD_HEAD.replace('%D%', repr(d))
  require(not any(m in g for m in marks) and 'SNAPSHOT_RESULT' in g, 'guard placeholder drift')
  return g


def check_event(e, ev, head, base, esha, pr):
  ids = [e.get(k, '') for k in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT')]
  for v in ids:
    require(1 <= len(v) <= 20 and v.isascii() and v.isdigit() and v[0] != '0', 'bad run identity')
  wf = REPO + '/' + WF + '@refs/heads/main'
  require(e.get('GITHUB_EVENT_NAME') == 'pull_request_target' and e.get('GITHUB_REF') == 'refs/heads/main'
    and e.get('GITHUB_REPOSITORY') == REPO and e.get('GITHUB_WORKFLOW_REF') == wf
    and e.get('GITHUB_WORKFLOW_SHA') == esha, 'workflow identity')
  require(isinstance(ev, dict) and ev.get('action') in ('opened', 'synchronize'), 'event action')
  pro, repo = ev.get('pull_request'), ev.get('repository')
  require(isinstance(pro, dict) and isinstance(repo, dict), 'event shape')
  isn = lambda v: type(v) is int and v == pr
  require(isn(ev.get('number')) and isn(pro.get('number')), 'event PR number')
  rp = lambda r: isinstance(r, dict) and type(r.get('id')) is int and r['id'] == REPO_ID and r.get('full_name') == REPO
  b, h = pro.get('base'), pro.get('head')
  require(isinstance(b, dict) and isinstance(h, dict) and rp(repo) and rp(b.get('repo')) and rp(h.get('repo')),
    'event repository')
  require(b.get('ref') == 'main' and h.get('ref') == HEADBR and b.get('sha') == base and h.get('sha') == head
    and base == esha, 'event refs')
  return {'action': ev['action'], 'event_name': 'pull_request_target', 'workflow_ref': wf, 'workflow_sha': esha,
    'run_id': int(ids[0]), 'run_attempt': int(ids[1]), 'repository_id': REPO_ID, 'consistency_only': True}


def context(here):
  t0 = time.monotonic()
  e = os.environ
  head, base, ws, temp, esha = (e.get(k, '') for k in ('HEAD_SHA', 'BASE_SHA', 'GITHUB_WORKSPACE', 'RUNNER_TEMP', 'GITHUB_SHA'))
  for sha in (head, base, esha):
    require(len(sha) == 40 and set(sha) <= set('0123456789abcdef'), 'bad SHA input')
  ws, temp = H.clean_path(ws, 'workspace'), H.clean_path(temp, 'temp')
  for p in (ws, temp):
    os.close(H.walk(p, H.DF))
  require(os.path.realpath(ws + '/base/tools') == here, 'controller not from base checkout')
  pr = e.get('PR_NUMBER', '')
  require(1 <= len(pr) <= 10 and pr.isascii() and pr.isdigit() and pr[0] != '0', 'bad PR number')
  evd = check_event(e, H.read_event(e.get('GITHUB_EVENT_PATH', ''), t0 + 5), head, base, esha, int(pr))
  return {'head': head, 'base': base, 'sha': esha, 'base_dir': ws + '/base', 'pr': int(pr),
    'headref': 'refs/snapshot/pr-%s-head' % pr, 'remote_ref': 'refs/pull/%s/head' % pr, 'temp': temp,
    'run': e.get('GITHUB_RUN_ID', ''), 'event': evd, 't0': t0}


def blob(d, end, ent, path):
  mode, kind, oid = ent
  require((mode, kind) == ('100644', 'blob') and len(oid) == 40 and set(oid) <= set('0123456789abcdef'),
    'not a 100644 blob: ' + path)
  size = int(H.git_cap(d, end, 32, 'cat-file', '-s', oid).decode('ascii').strip())
  require(0 <= size <= H.SCAP, 'blob size cap: ' + path)
  body = H.git_cap(d, end, size + 1, 'cat-file', 'blob', oid)
  require(len(body) == size and H.blob_id(body) == oid, 'blob != object id: ' + path)
  require(hashlib.sha256(body).hexdigest() == PINS[path], 'pin drift: ' + path)
  try:
    body.decode('utf-8')
  except UnicodeDecodeError:
    raise H.Failure('not UTF-8: ' + path) from None
  require(bytes(1) not in body, 'NUL byte: ' + path)
  return body


def bind(ctx, end):
  d = H.verify_refs(ctx, end)
  bt, ht = H.tree(d, ctx['base'], end), H.tree(d, ctx['head'], end)
  ch = sorted(p for p in set(ht) | set(bt) if ht.get(p) != bt.get(p))
  require(len(ch) <= H.MAXPATHS and ch == ADDED and not any(p in bt for p in ADDED), 'unexpected diff paths')
  require(INV in bt and ht.get(INV) == bt[INV], 'classifier differs between base and head')
  diff = H.git_cap(d, end, H.DCAP + 1, 'diff', '--binary', '--full-index', '--no-textconv',
    '--no-ext-diff', '--no-color', '--no-renames', ctx['base'], ctx['head'], '--')
  require(len(diff) <= H.DCAP, 'diff cap')
  data, pins, meta, total = {}, {}, [], 0
  for p in PINS:
    ent = bt[p] if p == INV else ht[p]
    data[p] = blob(d, end, ent, p)
    pins[p] = [PINS[p], ent[2], len(data[p]), 'base' if p == INV else 'head']
    if p != INV:
      total += len(data[p])
      meta.append([p, ent[0], ent[2], len(data[p]), PINS[p]])
  snap = total + len(json.dumps(meta, separators=(',', ':')).encode())
  require(snap <= H.SCAP, 'full snapshot cap (raw bodies + serialized metadata)')
  bad = H.static_checks({p: data[p] for p in ADDED}, ht)
  require(not bad, 'static: ' + '; '.join(bad[:5]))
  caps = {'diff_bytes': len(diff), 'diff_cap': H.DCAP, 'diff_sha256': hashlib.sha256(diff).hexdigest(),
    'paths': len(ch), 'path_cap': H.MAXPATHS, 'changed_raw_snapshot_bytes': total,
    'snapshot_cap': H.SCAP, 'changed_snapshot_with_manifest_bytes': snap,
    'dependency_raw_bytes': sum(map(len, data.values()))}
  return {'data': data, 'changed': ch, 'caps': caps, 'pins': pins}


def emit(ctx, mode, image_id, digs, prov, extra):
  extra.update(mode=mode, head=ctx['head'], base=ctx['base'], event_sha=ctx['sha'], run=ctx['run'],
    pr_number=ctx['pr'], image_ref=H.REF, event=ctx['event'], helper_sha256=HELPER_SHA, test_count=len(TESTS),
    head_ref={'remote': ctx['remote_ref'], 'local_verified': ctx['headref'], 'verified_sha': ctx['head']},
    engine_image_id=image_id, engine_image_id_kind='config_id' if image_id == H.CONFIG_DIGEST else 'manifest_id',
    pinned_manifest_digest=H.MANIFEST_DIGEST, pinned_config_digest=H.CONFIG_DIGEST, repo_digests=digs, provenance=prov)
  print(json.dumps(extra, sort_keys=True, indent=1))


def provision(ctx):
  ctl = H.Ctl(ctx['t0'] + 60)
  bd = bind(ctx, ctl.end)
  ctl.call(['pull', '--quiet', '--platform=linux/amd64', H.REF])
  image_id, digs, _ = H.docker_info(ctl)
  prov = H.provenance(ctl)
  H.due(ctl.end, 'provision')
  emit(ctx, 'provision', image_id, digs, prov, {'target_executed': False, 'caps': bd['caps'],
    'pins': bd['pins'], 'engine': ctl.ev})
  return 0


def parse_target(text):
  ls = text.split(chr(10))
  gi = [i for i, l in enumerate(ls) if l.startswith('INFRA_GUARD_OK ')]
  ri = [i for i, l in enumerate(ls) if l.startswith('SNAPSHOT_RESULT ')]
  require(len(gi) == 1 and len(ri) == 1 and gi[0] < ri[0] and text.count('INFRA_GUARD_OK ') == 1
    and text.count('SNAPSHOT_RESULT ') == 1, 'markers')
  guard = json.loads(ls[gi[0]].split(' ', 1)[1])
  res = json.loads(ls[ri[0]].split(' ', 1)[1])
  require(isinstance(res, dict) and set(res) == H.RKEYS, 'result keys')
  require(res['ok'] is True and type(res['tests']) is int and res['tests'] == 10 and res['names'] == sorted(TESTS)
    and all(type(res[k]) is int and res[k] == 0 for k in H.BAD), 'result not ten passes')
  return H.check_guard(guard), res


def run_target(ctx, ctl, st):
  end, name = ctl.end, st['name']
  bd = bind(ctx, end)
  image_id, digs, expect_manifest = H.docker_info(ctl)
  prov = H.provenance(ctl)
  files = {'empty': b''}
  for p, (fn, _) in RUN.items():
    files[fn] = bd['data'][p]
  stage = H.make_stage(ctx['temp'], files, st, end)
  for f, body in files.items():
    require(H.read_pinned(stage, f, end) == body, 'staged file changed: ' + f)
  binds = [(stage + '/empty', p) for p in ('/etc/hosts', '/etc/hostname', '/etc/resolv.conf')]
  binds += [(stage + '/' + fn, dst) for fn, dst in RUN.values()]
  cmd = ['-i', 'HOME=/scratch', 'TMPDIR=/scratch', 'XDG_CACHE_HOME=/scratch', 'LC_ALL=C',
    H.PY, '-I', '-S', '-B', '-c', guard_src()]
  args = ['create', '--name', name] + H.OPTS
  for p, o in H.TMPFS.items():
    args += ['--tmpfs', p + ':' + o]
  for s, d in binds:
    H.clean_path(s, 'mount source')
    args += ['--mount', 'type=bind,src=%s,dst=%s,readonly' % (s, d)]
  st['created'] = True
  ctl.call(args + [image_id] + cmd)
  ctl.ev['container'] = H.verify_container(json.loads(ctl.call(['inspect', '--format', '{{json .}}', name])),
    name, image_id, cmd, binds, expect_manifest)
  raw = ctl.call(['start', '--attach', name])
  state = json.loads(ctl.call(['inspect', '--format', '{{json .State}}', name]))
  require(state['Running'] is False and state['ExitCode'] == 0 and not state['OOMKilled']
    and not state['Error'], 'container state: ' + json.dumps(state)[:300])
  guard, res = parse_target(raw.decode('utf-8'))
  H.due(end, 'result')
  return {'guard': guard, 'result': res, 'image_id': image_id, 'digs': digs, 'prov': prov, 'bd': bd,
    'out': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}}


def execute(ctx):
  t0 = ctx['t0']
  ctl = H.Ctl(t0 + 15)
  st = {'name': 'snapshot-offline-' + uuid.uuid4().hex, 'stage': None, 'created': False}
  out, fail = None, H.Failure('did not complete')
  try:
    out = run_target(ctx, ctl, st)
    fail = None
  except BaseException as exc:
    fail = exc
  finally:
    H.SIG['clean'] = True
    normal = time.monotonic() - t0
    try:
      rep = ctl.cleanup(st)
    except BaseException as exc:
      rep = {'absent': False, 'cleanup_overrun': True, 'errors': {'cleanup': [repr(exc)[:200]]}}
  n = H.SIG['n']
  rep.update(normal_elapsed=round(normal, 3), interrupted=n, failure=None if fail is None else repr(fail)[:600])
  if fail is not None or n or normal > 15 or not rep['absent'] or rep['cleanup_overrun'] or any(rep['errors'].values()):
    if st['created'] and not rep['absent']:
      sys.stderr.write('CONTAINMENT UNKNOWN; do not relaunch' + chr(10))
    sys.stderr.write('FAILED ' + json.dumps(rep, sort_keys=True)[:1800] + chr(10))
    return 1
  bd = out['bd']
  emit(ctx, 'execute', out['image_id'], out['digs'], out['prov'], {'changed_paths': bd['changed'],
    'caps': bd['caps'], 'pins': bd['pins'], 'guard_evidence': out['guard'], 'result': out['result'],
    'target_output': out['out'], 'engine': ctl.ev, 'lifecycle': rep})
  print('SNAPSHOT_CI_PASS')
  return 0


def main():
  global H
  mode = sys.argv[1] if len(sys.argv) == 2 else ''
  old, rc = {}, 1
  try:
    try:
      if mode not in ('provision', 'execute'):
        raise ValueError('usage: provision|execute')
      H, here = load_helper()
      for s in (signal.SIGTERM, signal.SIGINT):
        old[s] = signal.signal(s, H.on_signal)
      rc = (provision if mode == 'provision' else execute)(context(here))
    except Exception as exc:
      sys.stderr.write('FAILED: ' + ' '.join(str(exc).split())[:1500] + chr(10))
  finally:
    for s, h in old.items():
      signal.signal(s, h)
  return rc or int(bool(H is not None and H.SIG['n']))


if __name__ == '__main__':
  sys.exit(main())
