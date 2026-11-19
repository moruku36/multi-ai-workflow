"""Bounded, fixed-vocabulary failure diagnostics for the automatic dual review lanes."""
from ocr_mimo_review import MAX_CALLS

# Stages identify the stopping point, not a proven provider/root cause.
FAILURE_STAGES = {
    'alibaba': frozenset((
        'preflight', 'relay_setup', 'workspace_setup', 'cli_execution', 'cli_launch',
        'cli_timeout', 'cli_exit_nonzero', 'relay_halted', 'no_completed_response',
        'output_missing', 'output_oversized', 'output_read', 'output_parse',
        'output_status', 'output_warnings', 'output_model', 'output_coverage',
        'findings_validation', 'cleanup', 'lane_result', 'lane_worker', 'internal')),
    'cloudflare': frozenset((
        'preflight', 'request_setup', 'request_http', 'response_parse',
        'response_validation', 'report_parse', 'findings_validation',
        'report_validation', 'lane_result', 'lane_worker', 'internal')),
}
USAGE_KEYS = ('prompt_tokens', 'completion_tokens', 'total_tokens')
MAX_USAGE_TOKENS = 10**9  # Serialization bound, not a billing limit.
RESPONSE_REASONS = frozenset((
    'length_stop', 'model_mismatch', 'malformed_response', 'unexpected_tools'))
# Where our own sender/relay budget stopped; never a provider or transport diagnosis.
STOP_REASONS = frozenset((
    'attempt_cap', 'deadline', 'payload_size', 'cumulative_payload'))
HALT_REASONS = frozenset((
    'request_framing', 'request_read', 'relay_rejected', 'response_write',
    'handler_error'))
HALT_OBSERVATIONS = frozenset(('post_cli', 'settled_cleanup'))


def bounded_count(value, maximum):
    return value if type(value) is int and 0 <= value <= maximum else 'unknown'


def safe_usage(value, maximum):
    if type(value) is dict:
        value = [value]
    if type(value) is not list:
        return 'unknown'
    return [{key: bounded_count(row.get(key), MAX_USAGE_TOKENS)
             if type(row) is dict else 'unknown' for key in USAGE_KEYS}
            for row in value[:maximum]]


def safe_diagnostics(lane, values=None):
    """Project only fixed vocabulary, bounded numbers/bools and safe usage.

    Reapply at receipt boundaries; never serialize arbitrary exception attributes,
    strings, stderr, paths, provider bodies, credentials or headers.
    """
    values = values if type(values) is dict else {}
    maximum = MAX_CALLS if lane == 'alibaba' else 1
    stage = values.get('failure_stage')
    halted, code = values.get('relay_halted'), values.get('cli_exit_code')
    result = {
        'failure_stage': stage if type(stage) is str and stage in FAILURE_STAGES[lane]
                         else 'internal',
        'http_attempts': bounded_count(values.get('http_attempts'), maximum),
        'completed_responses': bounded_count(values.get('completed_responses'), maximum),
        'relay_halted': halted if type(halted) is bool else 'unknown',
        'cli_exit_code': code if lane == 'alibaba' and type(code) is int
                         and -255 <= code <= 255 else None,
        'usage': safe_usage(values.get('usage'), maximum),
    }
    reason = values.get('response_reason')
    if type(reason) is str and reason in RESPONSE_REASONS:
        result['response_reason'] = reason
    stop = values.get('stop_reason')
    if type(stop) is str and stop in STOP_REASONS:
        result['stop_reason'] = stop
    first, seen = values.get('first_halt_reason'), values.get('halt_observation')
    if (lane == 'alibaba' and result['relay_halted'] is True
            and type(first) is str and first in HALT_REASONS
            and type(seen) is str and seen in HALT_OBSERVATIONS):
        result['first_halt_reason'], result['halt_observation'] = first, seen
    return result


def relay_diagnostics(lane, stage, relay=None, cli_exit_code=None, *,
                      first_halt_reason=None, halt_observation=None):
    reason = stop = None
    try:
        reason = getattr(relay, 'response_reason', None)
        stop = getattr(relay, 'stop_reason', None)
    except Exception:
        pass
    return safe_diagnostics(lane, {
        'stop_reason': stop,
        'failure_stage': stage, 'cli_exit_code': cli_exit_code,
        'http_attempts': getattr(relay, 'attempts', None),
        'completed_responses': getattr(relay, 'completed', None),
        'relay_halted': getattr(relay, 'halted', None),
        'usage': getattr(relay, 'usage', None), 'response_reason': reason,
        'first_halt_reason': first_halt_reason, 'halt_observation': halt_observation})


class LaneError(ValueError):
    """Only this bounded diagnostic projection crosses a failed-lane boundary."""

    def __init__(self, lane, stage, relay=None, cli_exit_code=None, *,
                 first_halt_reason=None, halt_observation=None):
        super().__init__('Review lane incomplete or unknown')
        self.lane = lane
        self.diagnostics = relay_diagnostics(
            lane, stage, relay, cli_exit_code,
            first_halt_reason=first_halt_reason, halt_observation=halt_observation)
