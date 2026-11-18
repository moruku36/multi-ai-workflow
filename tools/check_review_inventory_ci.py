#!/usr/bin/env python3
# Bootstrap controller: introduced by a separately reviewed PR into main; only base-owned code runs.
# The PR head is read purely as Git data (a fetched ref plus bounded cat-file of four blobs), never checked out or imported.
# PR-head code is not trusted attestation; SIGKILL/runner loss cannot prove cleanup.
import hashlib, json, os, posixpath, selectors, signal, stat, subprocess, sys, time, uuid

DOCKER, GIT, PY = '/usr/bin/docker', '/usr/bin/git', '/usr/local/bin/python3.13'
MANIFEST_DIGEST = 'sha256:f3dac913ab53b78c64f26d5518fcd7043d5a1a46522d6a493b598c3ed12f62a6'
# The verified OCI manifest binds this config digest for manifest-ID stores.
CONFIG_DIGEST = 'sha256:c7ea9065843cd8081ac483d8ce0cd7f2dfed7dd77180c8c535cbfc9ee9a85a9c'
REF = 'docker.io/library/python@' + MANIFEST_DIGEST
REPO_DIGESTS = ('python@' + MANIFEST_DIGEST, REF)
PLATFORM = ('linux', 'amd64')
BASE = {'HOME': '/nonexistent', 'PATH': '/usr/bin:/bin'}
DENV = dict(BASE, DOCKER_HOST='unix:///var/run/docker.sock', DOCKER_CLI_HINTS='false')
GENV = dict(BASE, LC_ALL='C', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
  GIT_NO_REPLACE_OBJECTS='1', GIT_TERMINAL_PROMPT='0', GIT_ATTR_NOSYSTEM='1')
NCAP, TCAP, RES = 57344, 65536, 0.25
DF = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FL = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
PINS = {
  'tools/review_inventory.py': 'd48f1d1ecdd9885beca1db2fca9b7067ed6784cbeaff9c5e9d08eccaa98ae782',
  'tests/check_review_inventory.py': '1d6475e89f5be0f77e5a8cd3f3711a0687dcf12467f4f23c73f1f45565bbcc93',
  'docs/review-inventory.md': '03fd95074c92f9532eee4a0d35e798b3a190a02bb95386aeab761075d31fcb79',
  'docs/review-inventory.ja.md': '7c5125578f278eb3af847299d07b3471bef2986ae08030be4ab1d1c39f64dc46',
}
ALLOWED = tuple(PINS)
# Event/workflow identity is a consistency check inside the trusted runner boundary, not attestation.
REPO, REPO_ID, HEADBR = 'moruku36/multi-ai-workflow', 1365934149, 'feat/review-inventory-consumer-v1'
WF_PATH = '.github/workflows/inventory-trusted.yml'  # must match this workflow's file name
EVENT_CAP = 1 << 20
RKEYS = {'tests', 'names', 'failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes', 'ok'}
GFILES = ('/usr/bin/env', '/usr/local/bin/python3.13', '/usr/local/lib/python3.13/os.py')
STAGED_DST = ('/target/tools/review_inventory.py', '/target/tests/check_review_inventory.py')
GMOUNTS = ('/proc/sys', '/proc/sysrq-trigger') + STAGED_DST
DCAP = SCAP = 65536
MAXPATHS = 20
TESTS = (
  'test_every_record_visible_with_reason', 'test_evidence_ladder_and_enforcement',
  'test_pagination_and_invalid_limit', 'test_malformed_rows_facts_and_keys_propagate',
  'test_duplicates_quarantine_every_member', 'test_scope_never_implies_owner_wide_enforcement',
  'test_identity_and_branch_must_be_consistent', 'test_public_view_withholds_identifiers',
  'test_missing_installation_is_manual_not_eligible', 'test_summary_keeps_every_entry_in_denominator',
)
BAD = ('failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes')
RO = 'ro,nosuid,nodev,noexec,size=4k,mode=755'
TMPFS = {'/scratch': 'rw,nosuid,nodev,noexec,size=16m,mode=1777', '/dev/pts': RO, '/dev/mqueue': RO}
OPTS = ['--platform=linux/amd64', '--pull=never', '--network=none', '--read-only',
  '--user=65534:65534', '--cap-drop=ALL', '--security-opt=no-new-privileges',
  '--no-healthcheck', '--log-driver=none', '--cpus=0.5', '--memory=128m',
  '--memory-swap=128m', '--pids-limit=16', '--ulimit=cpu=5:5', '--ulimit=nofile=32:32',
  '--ulimit=fsize=1048576:1048576', '--ulimit=core=0:0', '--ipc=none',
  '--workdir=/scratch', '--entrypoint=/usr/bin/env']
CFG = {'User': '65534:65534', 'WorkingDir': '/scratch', 'Entrypoint': ['/usr/bin/env']}
HC = {'ReadonlyRootfs': True, 'NetworkMode': 'none', 'IpcMode': 'none', 'Privileged': False,
  'NanoCpus': 500000000, 'Memory': 134217728, 'MemorySwap': 134217728, 'PidsLimit': 16,
  'CapDrop': ['ALL'], 'Tmpfs': TMPFS}
EMPTY = ('CapAdd', 'Binds', 'Devices', 'DeviceRequests', 'ExtraHosts', 'Links', 'VolumesFrom',
  'Sysctls', 'GroupAdd', 'PortBindings', 'Dns', 'DnsOptions', 'DnsSearch', 'PidMode',
  'UsernsMode', 'UTSMode', 'CgroupParent', 'PublishAllPorts', 'AutoRemove')

# The guard measures the container, then os.execv replaces its interpreter with a fresh one that runs the
# controller-owned driver. exec keeps the same process/cgroup/mount/limit boundary but clears guard interpreter
# state. The exact-source target result is still not independent attestation. The target never runs in the guard.
GUARD_SRC = r'''
import hashlib, json, os, resource, stat, sys
assert (os.getuid(), os.getgid()) == (65534, 65534)
assert dict(os.environ) == {'HOME': '/scratch', 'TMPDIR': '/scratch', 'XDG_CACHE_HOME': '/scratch', 'LC_ALL': 'C'}
assert sys.version_info[:3] == (3, 13, 18), sys.version
assert os.path.realpath(sys.executable) == '/usr/local/bin/python3.13'
assert os.path.realpath(os.__file__) == '/usr/local/lib/python3.13/os.py'
meas = {}
for p in ('/usr/bin/env', '/usr/local/bin/python3.13', '/usr/local/lib/python3.13/os.py'):
  s = os.stat(p)
  assert stat.S_ISREG(s.st_mode) and s.st_uid == 0 and not s.st_mode & 0o022, p
  meas[p] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
mounts = {}
mask, mask_info = '/proc/latency_stats', None
for line in open('/proc/self/mountinfo'):
  a, b = (x.split() for x in line.rstrip().split(' - ', 1))
  if a[4] == mask:
    assert mask_info is None, mask
    mask_info = a[2], a[3], b[:2]
    continue
  mounts[a[4]] = (set(a[5].split(',')), b[0])
for p in ('/', '/sys', '/sys/fs/cgroup', '/dev/pts', '/dev/mqueue', '/etc/hosts', '/etc/hostname', '/etc/resolv.conf'):
  assert 'ro' in mounts[p][0], (p, mounts[p])
assert not os.path.exists('/dev/shm') and 'rw' in mounts['/scratch'][0]
ro_named = {}
for p in ('/proc/sys', '/proc/sysrq-trigger', '/target/tools/review_inventory.py', '/target/tests/check_review_inventory.py'):
  ro_named[p] = {'present': p in mounts, 'ro': p in mounts and 'ro' in mounts[p][0]}
for p in ro_named:
  assert ro_named[p] == {'present': True, 'ro': True}, p
s = os.stat('/dev')
assert s.st_uid == 0 and stat.S_IMODE(s.st_mode) == 0o755
# runc can bind the /dev tmpfs null node over this optional proc file.
if mask_info is not None:
  dev, root, fs_source = mask_info
  assert root == '/null' and fs_source == ['tmpfs', 'tmpfs'], mask
  try:
    mounted = os.stat(mask, follow_symlinks=False)
    null = os.stat('/dev/null', follow_symlinks=False)
  except OSError:
    raise AssertionError(mask) from None
  null_nodes = all(stat.S_ISCHR(x.st_mode) and x.st_rdev == os.makedev(1, 3) for x in (mounted, null))
  assert null_nodes, mask
  assert (mounted.st_dev, mounted.st_ino) == (null.st_dev, null.st_ino), mask
  assert dev == '%d:%d' % (os.major(mounted.st_dev), os.minor(mounted.st_dev)), mask
OKRW = ('/dev', '/proc/interrupts', '/proc/kcore', '/proc/keys', '/proc/timer_list')
for p, (o, fs) in mounts.items():
  assert 'rw' not in o or p == '/scratch' or fs == 'proc' or (fs == 'tmpfs' and p in OKRW), (p, fs)
st = dict(l.split(':', 1) for l in open('/proc/self/status').read().splitlines() if ':' in l)
assert st['NoNewPrivs'].strip() == '1' and st['Seccomp'].strip() == '2'
assert all(int(st[k].strip(), 16) == 0 for k in ('CapEff', 'CapPrm', 'CapBnd'))
sec = {'seccomp': int(st['Seccomp'].strip()), 'no_new_privs': int(st['NoNewPrivs'].strip()),
  'cap_eff': int(st['CapEff'].strip(), 16), 'cap_prm': int(st['CapPrm'].strip(), 16), 'cap_bnd': int(st['CapBnd'].strip(), 16)}
for n, w in (('RLIMIT_CPU', 5), ('RLIMIT_NOFILE', 32), ('RLIMIT_FSIZE', 1048576), ('RLIMIT_CORE', 0)):
  assert resource.getrlimit(getattr(resource, n)) == (w, w), n
cg = lambda n: open('/sys/fs/cgroup/' + n).read().strip()
for k, v in (('memory.max', '134217728'), ('memory.swap.max', '0'), ('pids.max', '16')):
  assert cg(k) == v, k
quota, period = cg('cpu.max').split()
assert int(quota) > 0 and int(period) == 2 * int(quota), 'cpu.max is not 0.5 CPU'
G = {'files': meas, 'seccomp': sec, 'mounts': ro_named, 'latency_mask': 'absent' if mask_info is None else 'verified'}
DRIVER = %D%
print('INFRA_GUARD_OK ' + json.dumps(G, sort_keys=True), flush=True)
sys.stdout.flush()
os.execv(sys.executable, [sys.executable, '-I', '-S', '-B', '-c', DRIVER])
#--DRIVER--
import json, runpy, sys, unittest
EXPECTED = %T%
ns = runpy.run_path('/target/tests/check_review_inventory.py', run_name='inventory_target')
cls = ns['InventoryTests']
assert issubclass(cls, unittest.TestCase)
names = sorted(unittest.TestLoader().getTestCaseNames(cls))
assert names == sorted(EXPECTED), names
r = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(unittest.TestSuite(cls(n) for n in names))
S = {'tests': r.testsRun, 'names': names, 'failures': len(r.failures), 'errors': len(r.errors),
  'skipped': len(r.skipped), 'expected_failures': len(r.expectedFailures),
  'unexpected_successes': len(r.unexpectedSuccesses)}
S['ok'] = bool(r.wasSuccessful() and r.testsRun == 10 and not any(S[k] for k in %B%))
print('INVENTORY_RESULT ' + json.dumps(S, sort_keys=True), flush=True)
sys.exit(0 if S['ok'] else 1)
'''.replace('%T%', repr(TESTS)).replace('%B%', repr(BAD))
GUARD_HEAD, DRIVER = GUARD_SRC.split('#--DRIVER--' + chr(10))
GUARD = GUARD_HEAD.replace('%D%', repr(DRIVER))


class Failure(Exception):
  pass


SIG = {'n': 0, 'clean': False}
GITB = [0]


def on_signal(num, _frame):
  SIG['n'] = SIG['n'] or num


def require(cond, msg):
  if not cond:
    raise Failure(msg)


def due(end, what=''):
  require(not SIG['n'] or SIG['clean'], 'signal %d' % SIG['n'])
  require(time.monotonic() < end, 'deadline ' + what)


def tx(raw):
  return raw[:300].decode('utf-8', 'replace')


def step(notes, label, fn, *a, ok=()):
  try:
    fn(*a)
  except ok:
    pass
  except BaseException as exc:
    notes.append('%s failed: %s' % (label, repr(exc)[:80]))


def bounded_run(argv, env, end, cap, acct):
  stop = end - RES
  due(stop, 'launch')
  p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
    stderr=subprocess.PIPE, env=env, close_fds=True, start_new_session=True)
  sel = res = err = None
  notes, bufs = [], (bytearray(), bytearray())
  try:
    sel = selectors.DefaultSelector()
    for i, f in enumerate((p.stdout, p.stderr)):
      os.set_blocking(f.fileno(), False)
      sel.register(f, selectors.EVENT_READ, i)
    while sel.get_map():
      due(stop, 'run')
      for k, _ in sel.select(max(0.0, min(0.1, stop - time.monotonic()))):
        require(acct[0] < cap, 'output ceiling')
        try:
          d = os.read(k.fd, min(4096, cap - acct[0]))
        except BlockingIOError:
          continue
        if d:
          acct[0] += len(d)
          bufs[k.data].extend(d)
        else:
          sel.unregister(k.fileobj)
    due(stop, 'wait')
    res = (p.wait(timeout=max(0.0, stop - time.monotonic())), bytes(bufs[0]), bytes(bufs[1]))
  except BaseException as exc:
    err = exc
  finally:
    step(notes, 'killpg', os.killpg, p.pid, signal.SIGKILL, ok=ProcessLookupError)
    step(notes, 'reap (UNKNOWN)', p.wait, max(0.0, end - time.monotonic()))
    for c in (sel, p.stdout, p.stderr):
      if c is not None:
        step(notes, 'close', c.close)
  if notes:
    raise Failure('; '.join(notes) + ('; primary: ' + repr(err)[:200] if err else ''))
  if err:
    raise err
  require(time.monotonic() <= end, 'overrun: ' + argv[0])
  return res


class Ctl:
  def __init__(self, end):
    self.end, self.cend, self.acct = end, None, [0]
    self.ev = {}

  def call(self, args, cl=False):
    rc, out, err = bounded_run([DOCKER] + args, DENV, self.cend if cl else self.end,
      TCAP if cl else NCAP, self.acct)
    require(rc == 0 and not err, 'docker %s rc=%d: %s' % (args[0], rc, tx(err)))
    return out

  def cleanup(self, st):
    t0 = time.monotonic()
    self.cend = t0 + 5
    E = {'container': [], 'stage': [], 'reap': []}

    def note(kind, x):
      E['reap' if 'reap (UNKNOWN)' in str(x) else kind].append(str(x)[:160])
    n, absent = st['name'], not st['created']
    if st['created']:
      try:
        self.call(['rm', '-f', n], True)
      except Exception as x:
        note('container', 'rm: ' + str(x))
      try:
        absent = not self.call(['ps', '-aq', '--no-trunc', '--filter', 'name=^/%s$' % n], True).strip()
        if not absent:
          note('container', 'still present')
      except Exception as x:
        note('container', 'absence UNKNOWN: ' + str(x))
    if st['stage']:
      try:
        require(absent, 'stage kept: absence unproven')
        remove_stage(st['stage'], self.cend)
      except Exception as x:
        note('stage', x)
    el = time.monotonic() - t0
    return {'absent': absent, 'cleanup_elapsed': round(el, 3), 'cleanup_overrun': el > 5, 'errors': E}


def remove_stage(stage, end):
  due(end, 'stage')
  if os.path.lexists(stage):
    for n in os.listdir(stage):
      due(end, 'unlink')
      os.unlink(stage + '/' + n)
    due(end, 'rmdir')
    os.rmdir(stage)
  require(not os.path.lexists(stage), 'stage still present')


def walk(path, last):
  require(path.startswith('/') and posixpath.normpath(path) == path, 'bad path: ' + path)
  fd = os.open('/', DF)
  parts = [p for p in path.split('/') if p]
  for i, p in enumerate(parts):
    try:
      nxt = os.open(p, last if i == len(parts) - 1 else DF, dir_fd=fd)
    finally:
      os.close(fd)
    fd = nxt
  return fd


def read_pinned(root, rel, end):
  f = walk(root + '/' + rel, FL)
  try:
    a = os.fstat(f)
    require(stat.S_ISREG(a.st_mode) and a.st_nlink == 1 and a.st_size <= 131072
      and not a.st_mode & 0o111, 'bad file: ' + rel)
    data = b''
    while len(data) <= 131072:
      due(end, 'read')
      chunk = os.read(f, min(8192, 131073 - len(data)))
      if not chunk:
        break
      data += chunk
    z = os.fstat(f)
    key = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    require(key(a) == key(z) and len(data) == a.st_size, 'unstable: ' + rel)
    return data
  finally:
    os.close(f)


def blob_id(data):
  return hashlib.sha1(b'blob %d' % len(data) + bytes(1) + data).hexdigest()


def git(d, end, *args):
  rc, out, err = bounded_run([GIT, '-C', d] + list(args), GENV, end, 4 << 20, GITB)
  require(rc == 0 and not err, 'git %s failed (stderr suppressed)' % args[0])
  return out


def tree(d, sha, end):
  ent = {}
  for rec in git(d, end, 'ls-tree', '-r', '-z', '--full-tree', sha).split(bytes(1)):
    if rec:
      meta, path = rec.split(bytes([9]), 1)
      mode, kind, obj = meta.decode('ascii').split(' ')
      ent[path.decode('utf-8', 'surrogateescape')] = (mode, kind, obj)
  return ent


def static_checks(files, tmap):
  bad = []
  for path, data in sorted(files.items()):
    try:
      text = data.decode('utf-8')
    except UnicodeDecodeError:
      bad.append(path + ': not UTF-8')
      continue
    for n, l in enumerate(text.split(chr(10)), 1):
      if l != l.rstrip() or chr(0) in l or chr(13) in l:
        bad.append('%s:%d: whitespace/NUL/CR' % (path, n))
    for seg in (text.split('](')[1:] if path.endswith('.md') else ()):
      t = seg.split(')')[0].split('#')[0].split(' ')[0].split(chr(10))[0]
      r = posixpath.normpath(posixpath.join(posixpath.dirname(path), t))
      if t and not (t.startswith('/') or ':' in t.split('/')[0]) and (
          r.startswith('..') or not any(k == r or k.startswith(r + '/') for k in tmap)):
        bad.append('%s: bad link' % path)
  return bad[:20]


def git_cap(d, end, cap, *args):
  rc, out, err = bounded_run([GIT, '-C', d] + list(args), GENV, end, cap, [0])
  require(rc == 0 and not err, 'git %s failed (stderr suppressed)' % args[0])
  return out


def verify_refs(ctx, end):
  d = ctx['base_dir']
  os.close(walk(d, DF))
  require(ctx['base'] == ctx['sha'], 'base != event SHA')
  for k, ref in (('base', 'HEAD'), ('head', ctx['headref'])):
    got = git(d, end, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}').decode('ascii').strip()
    require(got == ctx[k], k + ' ref != expected SHA')
  return d


def bind(ctx, end):
  d = verify_refs(ctx, end)
  bt, ht = tree(d, ctx['base'], end), tree(d, ctx['head'], end)
  ch = sorted(p for p in set(ht) | set(bt) if ht.get(p) != bt.get(p))
  require(len(ch) <= MAXPATHS, 'path count cap')
  require(ch == sorted(ALLOWED) and not any(p in bt for p in ALLOWED), 'unexpected diff paths')
  diff = git_cap(d, end, DCAP + 1, 'diff', '--binary', '--full-index', '--no-textconv',
    '--no-ext-diff', '--no-color', '--no-renames', ctx['base'], ctx['head'], '--')
  require(len(diff) <= DCAP, 'diff cap')
  man, data, total = {}, {}, 0
  for path in ALLOWED:
    mode, kind, oid = ht[path]
    require((mode, kind) == ('100644', 'blob') and len(oid) == 40 and set(oid) <= set('0123456789abcdef'),
      'head not 100644 blob')
    size = int(git_cap(d, end, 32, 'cat-file', '-s', oid).decode('ascii').strip())
    require(0 <= size <= SCAP, 'blob size cap')
    body = git_cap(d, end, size + 1, 'cat-file', 'blob', oid)
    require(len(body) == size and blob_id(body) == oid, 'blob != object id')
    h = hashlib.sha256(body).hexdigest()
    require(h == PINS[path], 'pin drift: ' + path)
    data[path], total = body, total + size
    man[path] = [h, oid, 'absent']
  meta = json.dumps([[p, '100644', man[p][1], len(data[p]), man[p][0], 'absent'] for p in ALLOWED],
    separators=(',', ':')).encode()
  snap = total + len(meta)
  require(snap <= SCAP, 'snapshot cap')
  bad = static_checks(data, ht)
  require(not bad, 'static: ' + '; '.join(bad[:5]))
  caps = {'diff_bytes': len(diff), 'diff_cap': DCAP, 'diff_sha256': hashlib.sha256(diff).hexdigest(),
    'paths': len(ch), 'path_cap': MAXPATHS, 'snapshot_bytes': snap, 'snapshot_cap': SCAP}
  return {'manifest': man, 'data': data, 'changed': ch, 'caps': caps}


def make_stage(temp, files, st, end):
  tfd = walk(temp, DF)
  name = 'inventory-offline-' + uuid.uuid4().hex
  try:
    due(end, 'mkdir')
    os.mkdir(name, 0o700, dir_fd=tfd)
    st['stage'] = temp + '/' + name
    due(end, 'mkdir')
    sfd = os.open(name, DF, dir_fd=tfd)
    try:
      for fn, body in files.items():
        due(end, 'create')
        fd = os.open(fn, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444, dir_fd=sfd)
        try:
          v = memoryview(body)
          while v:
            due(end, 'write')
            n = os.write(fd, v)
            due(end, 'write')
            require(n > 0, 'zero write: ' + fn)
            v = v[n:]
          due(end, 'fchmod')
          os.fchmod(fd, 0o444)
          due(end, 'fchmod')
        finally:
          os.close(fd)
    finally:
      os.close(sfd)
  finally:
    os.close(tfd)
  return st['stage']


def verify_manifest(desc, where):
  require(isinstance(desc, dict) and desc.get('digest') == MANIFEST_DIGEST
    and desc.get('mediaType') == 'application/vnd.oci.image.manifest.v1+json'
    and type(desc.get('size')) is int and desc['size'] == 1752, where + ' manifest descriptor')
  p = desc.get('platform')
  if p is not None:
    require(isinstance(p, dict) and (p.get('os'), p.get('architecture')) == PLATFORM
      and p.get('variant', '') in ('', 'v1'), where + ' manifest platform')


def desc_fields(d):
  p = d.get('platform')
  return {'mediaType': d['mediaType'], 'digest': d['digest'], 'size': d['size'],
    'platform': None if p is None else '%s/%s' % (p.get('os'), p.get('architecture'))}


def docker_info(ctl):
  v = json.loads(ctl.call(['image', 'inspect', '--format', '{{json .}}', REF]))
  image_id, digs, desc = v.get('Id'), v.get('RepoDigests'), v.get('Descriptor')
  require((v.get('Os'), v.get('Architecture')) == PLATFORM, 'image platform')
  require(isinstance(digs, list) and any(d in REPO_DIGESTS for d in digs), 'image digest')
  require(image_id in (CONFIG_DIGEST, MANIFEST_DIGEST), 'unexpected Engine image ID')
  if desc is not None:
    verify_manifest(desc, 'image')
  ctl.ev['image'] = {'id_kind': 'config_id' if image_id == CONFIG_DIGEST else 'manifest_id',
    'manifest_descriptor': None if desc is None else desc_fields(desc)}
  return image_id, digs, image_id == MANIFEST_DIGEST and desc is not None


def provenance(ctl):
  v = json.loads(ctl.call(['version', '--format', '{{json .}}']))
  c, s = v.get('Client') or {}, v.get('Server') or {}
  require(s.get('Version'), 'no docker server version')
  run = {k: os.environ.get(k, 'unset')[:80] for k in ('ImageOS', 'ImageVersion', 'RUNNER_OS', 'RUNNER_ARCH')}
  return {'client': c.get('Version'), 'server': s.get('Version'), 'api': s.get('ApiVersion'),
    'server_os_arch': '%s/%s' % (s.get('Os'), s.get('Arch')), 'runner': run, 'runner_self_reported': True}


def verify_container(v, name, image_id, cmd, binds, expect_manifest):
  desc = v.get('ImageManifestDescriptor')
  require(desc is not None or not expect_manifest, 'missing container manifest descriptor')
  if desc is not None:
    verify_manifest(desc, 'container')
  h, c, ms = v['HostConfig'], v['Config'], v['Mounts'] or []
  ul = {(u['Name'], u['Soft'], u['Hard']) for u in h['Ulimits'] or []}
  seen = {(m['Source'], m['Destination'], m['RW']) for m in ms if m['Type'] == 'bind'}
  bad = [n for n, ok in (
    ('identity', v.get('Image') == image_id and v['Name'] == '/' + name),
    ('config', c['Cmd'] == cmd and all(c[k] == x for k, x in CFG.items())),
    ('host', all(h[k] == x for k, x in HC.items()) and not any(h.get(k) for k in EMPTY)),
    ('secopt', h['SecurityOpt'] in (['no-new-privileges'], ['no-new-privileges:true'])),
    ('log', h['LogConfig']['Type'] == 'none'),
    ('ulimits', ul == {('cpu', 5, 5), ('nofile', 32, 32), ('fsize', 1048576, 1048576), ('core', 0, 0)}),
    ('mount types', all(m['Type'] == 'bind' or (m['Type'] == 'tmpfs' and m['Destination'] in TMPFS) for m in ms)),
    ('binds', seen == {(s, d, False) for s, d in binds})) if not ok]
  require(not bad, 'container differs: ' + ', '.join(bad))
  return {'manifest_descriptor': None if desc is None else desc_fields(desc),
    'mounts': [[m['Destination'], m['Type'], m.get('RW')] for m in sorted(ms, key=lambda m: m['Destination'])]}


def check_guard(g):
  hx = lambda v: isinstance(v, str) and len(v) == 64 and set(v) <= set('0123456789abcdef')
  require(isinstance(g, dict) and set(g) == {'files', 'seccomp', 'mounts', 'latency_mask'}, 'guard keys')
  f, s, m = g['files'], g['seccomp'], g['mounts']
  require(isinstance(f, dict) and set(f) == set(GFILES) and all(hx(v) for v in f.values()), 'guard files')
  require(isinstance(s, dict) and set(s) == {'seccomp', 'no_new_privs', 'cap_eff', 'cap_prm', 'cap_bnd'}
    and all(type(v) is int for v in s.values()) and s['seccomp'] == 2 and s['no_new_privs'] == 1
    and s['cap_eff'] == 0 and s['cap_prm'] == 0 and s['cap_bnd'] == 0, 'guard process state')
  require(isinstance(m, dict) and set(m) == set(GMOUNTS) and all(isinstance(v, dict) and set(v) == {'present', 'ro'}
    and type(v['present']) is bool and type(v['ro']) is bool for v in m.values()), 'guard mounts')
  require(all(m[p] == {'present': True, 'ro': True} for p in GMOUNTS), 'required mounts not present and read-only')
  require(g['latency_mask'] in ('absent', 'verified'), 'guard latency mask')
  return g


def parse_target(text):
  ls = text.split(chr(10))
  gi = [i for i, l in enumerate(ls) if l.startswith('INFRA_GUARD_OK ')]
  ri = [i for i, l in enumerate(ls) if l.startswith('INVENTORY_RESULT ')]
  require(len(gi) == 1 and len(ri) == 1 and gi[0] < ri[0], 'markers')
  require(text.count('INFRA_GUARD_OK ') == 1 and text.count('INVENTORY_RESULT ') == 1, 'marker duplicates')
  res = json.loads(ls[ri[0]].split(' ', 1)[1])
  guard = json.loads(ls[gi[0]].split(' ', 1)[1])
  isint = lambda v: type(v) is int
  require(isinstance(res, dict) and set(res) == RKEYS, 'result keys')
  require(res['ok'] is True and isint(res['tests']) and res['tests'] == 10 and res['names'] == sorted(TESTS)
    and all(isint(res[k]) and res[k] == 0 for k in BAD), 'result not ten passes')
  return check_guard(guard), res


def clean_path(p, what):
  require(isinstance(p, str) and 2 <= len(p) <= 1024 and p.isascii() and p.startswith('/')
    and not p.startswith('//') and p == posixpath.normpath(p)
    and not any(c in p for c in (',', chr(34))) and not any(ord(c) < 32 or ord(c) == 127 for c in p),
    'bad ' + what + ' path')
  return p


def read_event(path, end):
  clean_path(path, 'event')
  f = walk(path, FL)
  try:
    a = os.fstat(f)
    require(stat.S_ISREG(a.st_mode) and a.st_size <= EVENT_CAP, 'bad event file')
    data = b''
    while len(data) <= EVENT_CAP:
      due(end, 'event read')
      chunk = os.read(f, min(8192, EVENT_CAP + 1 - len(data)))
      if not chunk:
        break
      data += chunk
    require(len(data) <= EVENT_CAP, 'event too large')
  finally:
    os.close(f)
  try:
    return json.loads(data.decode('utf-8'))
  except ValueError:
    raise Failure('event not JSON') from None


def check_event(e, ev, head, base, esha, pr):
  ids = [e.get(k, '') for k in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT')]
  for v in ids:
    require(1 <= len(v) <= 20 and v.isascii() and v.isdigit() and v[0] != '0', 'bad run identity')
  wf = REPO + '/' + WF_PATH + '@refs/heads/main'
  require(e.get('GITHUB_EVENT_NAME') == 'pull_request_target' and e.get('GITHUB_REF') == 'refs/heads/main'
    and e.get('GITHUB_REPOSITORY') == REPO and e.get('GITHUB_WORKFLOW_REF') == wf
    and e.get('GITHUB_WORKFLOW_SHA') == esha, 'workflow identity')
  require(isinstance(ev, dict) and ev.get('action') in ('opened', 'synchronize'), 'event action')
  pro, repo = ev.get('pull_request'), ev.get('repository')
  require(isinstance(pro, dict) and isinstance(repo, dict), 'event shape')
  isn = lambda v: type(v) is int and v > 0 and v == pr
  require(isn(ev.get('number')) and isn(pro.get('number')), 'event PR number')
  rp = lambda r: isinstance(r, dict) and type(r.get('id')) is int and r['id'] == REPO_ID and r.get('full_name') == REPO
  b, h = pro.get('base'), pro.get('head')
  require(isinstance(b, dict) and isinstance(h, dict) and rp(repo) and rp(b.get('repo')) and rp(h.get('repo')),
    'event repository')
  require(b.get('ref') == 'main' and h.get('ref') == HEADBR and b.get('sha') == base and h.get('sha') == head
    and base == esha, 'event refs')
  return {'action': ev['action'], 'event_name': 'pull_request_target', 'workflow_ref': wf, 'workflow_sha': esha,
    'run_id': int(ids[0]), 'run_attempt': int(ids[1]), 'repository_id': REPO_ID, 'consistency_only': True}


def context():
  t0 = time.monotonic()
  e = os.environ
  head, base, ws, temp, esha = (e.get(k, '') for k in ('HEAD_SHA', 'BASE_SHA', 'GITHUB_WORKSPACE', 'RUNNER_TEMP', 'GITHUB_SHA'))
  for sha in (head, base, esha):
    require(len(sha) == 40 and set(sha) <= set('0123456789abcdef'), 'bad SHA input')
  ws, temp = clean_path(ws, 'workspace'), clean_path(temp, 'temp')
  for p in (ws, temp):
    os.close(walk(p, DF))
  pr = e.get('PR_NUMBER', '')
  require(1 <= len(pr) <= 10 and pr.isascii() and pr.isdigit() and pr[0] != '0', 'bad PR number')
  evd = check_event(e, read_event(e.get('GITHUB_EVENT_PATH', ''), t0 + 5), head, base, esha, int(pr))
  return {'head': head, 'base': base, 'sha': esha, 'base_dir': ws + '/base',
    'pr': int(pr), 'headref': 'refs/inventory/pr-%s-head' % pr, 'remote_ref': 'refs/pull/%s/head' % pr,
    'temp': temp, 'run': e.get('GITHUB_RUN_ID', ''), 'event': evd, 't0': t0}


def emit(ctx, mode, image_id, digs, prov, extra):
  extra.update(mode=mode, head=ctx['head'], base=ctx['base'], event_sha=ctx['sha'], run=ctx['run'], pr_number=ctx['pr'], image_ref=REF,
    event=ctx['event'], head_ref={'remote': ctx['remote_ref'], 'local_verified': ctx['headref'], 'verified_sha': ctx['head']},
    source_count=len(PINS), test_count=len(TESTS),
    engine_image_id=image_id, pinned_manifest_digest=MANIFEST_DIGEST, pinned_config_digest=CONFIG_DIGEST,
    config_digest_evidence='engine_image_id' if image_id == CONFIG_DIGEST else 'verified_manifest_pin',
    engine_image_id_kind='config_id' if image_id == CONFIG_DIGEST else 'manifest_id',
    repo_digests=digs, provenance=prov)
  print(json.dumps(extra, sort_keys=True, indent=1))


def provision(ctx):
  ctl = Ctl(ctx['t0'] + 60)
  bd = bind(ctx, ctl.end)
  ctl.call(['pull', '--quiet', '--platform=linux/amd64', REF])
  image_id, digs, _ = docker_info(ctl)
  prov = provenance(ctl)
  due(ctl.end, 'provision')
  emit(ctx, 'provision', image_id, digs, prov, {'target_executed': False, 'caps': bd['caps'], 'engine': ctl.ev})
  return 0


def run_target(ctx, ctl, st):
  end, name = ctl.end, st['name']
  bd = bind(ctx, end)
  image_id, digs, expect_manifest = docker_info(ctl)
  prov = provenance(ctl)
  files = {'empty': b'', 'review_inventory.py': bd['data']['tools/review_inventory.py'],
    'check_review_inventory.py': bd['data']['tests/check_review_inventory.py']}
  stage = make_stage(ctx['temp'], files, st, end)
  for f, body in files.items():
    require(read_pinned(stage, f, end) == body, 'staged file changed: ' + f)
  binds = [(stage + '/empty', p) for p in ('/etc/hosts', '/etc/hostname', '/etc/resolv.conf')]
  binds += [(stage + '/review_inventory.py', '/target/tools/review_inventory.py'),
    (stage + '/check_review_inventory.py', '/target/tests/check_review_inventory.py')]
  cmd = ['-i', 'HOME=/scratch', 'TMPDIR=/scratch', 'XDG_CACHE_HOME=/scratch', 'LC_ALL=C',
    PY, '-I', '-S', '-B', '-c', GUARD]
  for s, _ in binds:
    clean_path(s, 'mount source')
  args = ['create', '--name', name] + OPTS
  for p, o in TMPFS.items():
    args += ['--tmpfs', p + ':' + o]
  for s, d in binds:
    args += ['--mount', 'type=bind,src=%s,dst=%s,readonly' % (s, d)]
  st['created'] = True
  ctl.call(args + [image_id] + cmd)
  ctl.ev['container'] = verify_container(json.loads(ctl.call(['inspect', '--format', '{{json .}}', name])),
    name, image_id, cmd, binds, expect_manifest)
  raw = ctl.call(['start', '--attach', name])
  state = json.loads(ctl.call(['inspect', '--format', '{{json .State}}', name]))
  require(state['Running'] is False and state['ExitCode'] == 0 and not state['OOMKilled']
    and not state['Error'], 'container state: ' + json.dumps(state)[:300])
  text = raw.decode('utf-8')
  measured, result = parse_target(text)
  due(end, 'result')
  return {'text': text, 'measured': measured, 'result': result, 'image_id': image_id, 'digs': digs,
    'prov': prov, 'bd': bd, 'ev': ctl.ev}


def execute(ctx):
  t0 = ctx['t0']
  ctl = Ctl(t0 + 15)
  st = {'name': 'inventory-offline-' + uuid.uuid4().hex, 'stage': None, 'created': False}
  out, fail = None, Failure('did not complete')
  try:
    out = run_target(ctx, ctl, st)
    fail = None
  except BaseException as exc:
    fail = exc
  finally:
    SIG['clean'] = True
    normal = time.monotonic() - t0
    try:
      rep = ctl.cleanup(st)
    except BaseException as exc:
      rep = {'absent': False, 'cleanup_overrun': True, 'errors': {'cleanup': [repr(exc)[:200]]}}
  rep.update(normal_elapsed=round(normal, 3), interrupted=SIG['n'],
    failure=None if fail is None else repr(fail)[:600])
  if (fail is not None or SIG['n'] or normal > 15 or not rep['absent'] or rep['cleanup_overrun']
      or any(rep['errors'].values())):
    if st['created'] and not rep['absent']:
      sys.stderr.write('CONTAINMENT UNKNOWN; do not relaunch' + chr(10))
    sys.stderr.write('FAILED ' + json.dumps(rep, sort_keys=True)[:1800] + chr(10))
    return 1
  bd = out['bd']
  emit(ctx, 'execute', out['image_id'], out['digs'], out['prov'], {'changed_paths': bd['changed'], 'caps': bd['caps'],
    'sources[sha256,head_blob,base_blob]': bd['manifest'], 'guard_measured_in_container': out['measured']['files'], 'guard_evidence': out['measured'], 'engine': out['ev'],
    'result': out['result'], 'lifecycle': rep})
  print('--- target output (unauthenticated wrapper) ---')
  print(out['text'])
  print('INVENTORY_CI_PASS')
  return 0


def main():
  mode = sys.argv[1] if len(sys.argv) == 2 else ''
  old, rc = {}, 1
  try:
    try:
      for s in (signal.SIGTERM, signal.SIGINT):
        old[s] = signal.signal(s, on_signal)
      require(mode in ('provision', 'execute'), 'usage: provision|execute')
      ctx = context()
      rc = (provision if mode == 'provision' else execute)(ctx)
    except Exception as exc:
      sys.stderr.write('FAILED: ' + str(exc)[:1500] + chr(10))
  finally:
    for s, h in old.items():
      signal.signal(s, h)
  return rc or int(bool(SIG['n']))


if __name__ == '__main__':
  sys.exit(main())
