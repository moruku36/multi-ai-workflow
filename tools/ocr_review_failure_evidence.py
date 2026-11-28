"""Internal vocabulary for observations from the pinned OCR failure output."""
from enum import Enum


CLI_RUN_FAILURE_FIELD = 'cli_run_failure_classification'


class CliRunFailure(Enum):
    INPUT = 'input'
    CONFIGURATION = 'configuration'
    TIMEOUT = 'timeout'
    CANCELLED = 'cancelled'
    BUDGET = 'budget'
    INTERNAL = 'internal'
    UNKNOWN = 'unknown'


def is_nonzero_cli_exit(code):
    return type(code) is int and -255 <= code <= 255 and code != 0


def _is_alibaba_cli_failure(lane, diagnostics):
    return (lane == 'alibaba' and type(diagnostics) is dict
            and diagnostics.get('failure_stage') == 'cli_exit_nonzero'
            and is_nonzero_cli_exit(diagnostics.get('cli_exit_code')))


def classification_from_lane_error(lane, error, diagnostics):
    """Read the optional typed observation from a caught LaneError."""
    evidence = getattr(error, '_cli_run_failure', None)
    if (error.lane == lane and type(evidence) is CliRunFailure
            and _is_alibaba_cli_failure(lane, diagnostics)):
        return evidence.value
    return None


def valid_pipe_classification(lane, diagnostics, value):
    """Check the finite value carried by Central's private child pipe."""
    return (_is_alibaba_cli_failure(lane, diagnostics) and type(value) is str
            and any(value == member.value for member in CliRunFailure))
