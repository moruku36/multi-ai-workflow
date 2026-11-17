import json, os, sys, time
from unittest import TestCase, main, mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import automatic_dual_review as adr
import ocr_mimo_connection as c

A, N, P, CAP = chr(0x3042), 18000, '/v1/chat/completions', adr.MAX_GUIDANCE_REQUEST_BYTES
OK = json.dumps({'model': c.MODEL, 'choices': [{'finish_reason': 'stop', 'message': {
    'content': '{"findings": [], "unresolved": []}'}}],
    'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}).encode()
REQ = json.dumps({'model': c.MODEL, 'messages': [{'role': 'user', 'content': ''}],
    'max_tokens': adr.MAX_OUTPUT_TOKENS, 'stream': False}).encode()


def inputs(d, s):
  return '+' + A * d, {'docs/a.md': [None, A * s], 'docs/b.md': ['x', 'y' + A]}


def relay(**kw):
  r = adr.BoundedReviewRelay(live=True, api_key='k', **kw)
  return r, 'Bearer ' + r.token


def diag(r):
  return adr.relay_diagnostics('alibaba', 'relay_halted', r, 0)


class RouteRepair(TestCase):
  eq = TestCase.assertEqual

  def setUp(self):
    self.sent = []
    self.addCleanup(mock.patch.stopall)
    mock.patch.dict(os.environ, {'MIMO_API_KEY': 'k'}).start()
    mock.patch.object(adr.dual_review, 'verify_skill', return_value='r').start()
    mock.patch.object(c.Relay, '_forward', lambda s, b: self.sent.append(b) or OK).start()

  def test_body(self):
    diff, snaps = inputs(N, N)
    body = adr.build_guidance_body(diff, snaps, 'g')
    p, src = json.loads(body), {'untrusted_diff': diff, 'untrusted_sources': snaps}
    self.assertIs(p['stream'], False)
    self.eq((len(body) <= CAP, len(json.dumps(json.dumps(src)).encode()) > CAP,
        p['model'], p['max_tokens'], p['thinking'], [m['role'] for m in p['messages']],
        json.loads(p['messages'][1]['content'])),
        (True, True, c.MODEL, adr.MAX_OUTPUT_TOKENS, {'type': 'disabled'},
         ['system', 'user'], src))

  def test_sender(self):
    diff, snaps = inputs(N, N)
    res = adr.cloudflare(diff, snaps)
    user = json.loads(json.loads(self.sent[0])['messages'][1]['content'])
    self.eq((len(self.sent), len(self.sent[0]) <= CAP, user['untrusted_diff'],
        res['findings'], res['unresolved']), (1, True, diff, [], []))

  def test_oversize(self):
    with self.assertRaises(adr.LaneError) as e:
      adr.cloudflare(*inputs(70000, 70000))
    d = e.exception.diagnostics
    self.eq((self.sent, d['stop_reason'], d['failure_stage']),
        ([], 'payload_size', 'request_http'))
    b = adr.PayloadBudget(2, request_bytes=8, cumulative_bytes=10)
    b.reserve(b'123456')
    with self.assertRaises(adr.BudgetExceeded) as o:
      b.reserve(b'123456')
    self.eq((o.exception.reason, b.attempts, b.bytes), ('cumulative_payload', 1, 6))

  def test_cap(self):
    r, a = relay(attempt_cap=1)
    r.exchange(REQ, a, P)
    self.eq((len(self.sent), r.attempts, r.completed), (1, 1, 1))
    with self.assertRaises(c.ProbeError):
      r.exchange(REQ, a, P)
    d = diag(r)
    self.eq((len(self.sent), r.attempts, r.completed, r.halted, r.stop_reason,
        d['stop_reason']), (1, 1, 1, True, 'attempt_cap', 'attempt_cap'))
    self.assertIs(d['relay_halted'], True)

  def test_deadline(self):
    r, a = relay(attempt_deadline=time.monotonic() - 1)
    with self.assertRaises(c.ProbeError):
      r.exchange(b'{}', a, P)
    self.eq((self.sent, r.stop_reason, diag(r)['stop_reason']), ([], 'deadline', 'deadline'))

  def test_hostile(self):
    bad = 'secret/' + A
    for v in (bad, 7, None, ['deadline'], 'Deadline'):
      out = adr.safe_diagnostics('alibaba', dict(
          failure_stage='relay_halted', stop_reason=v, http_attempts=8,
          completed_responses=8, relay_halted=True))
      self.assertNotIn('stop_reason', out)
      self.assertNotIn(bad, json.dumps(out))
    class H:
      stop_reason, attempts, completed, halted, usage = bad, 1, 0, True, None
    self.assertNotIn('stop_reason', adr.relay_diagnostics('cloudflare', 'request_http', H()))
    ok = adr.safe_diagnostics('cloudflare', dict(
        failure_stage='request_http', stop_reason='cumulative_payload'))
    self.eq(ok['stop_reason'], 'cumulative_payload')


if __name__ == '__main__':
  main()
