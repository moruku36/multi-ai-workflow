"""Fail-closed pilot scope check run before any App token is created.

Reuses the auth-only Hub.prepare_one_shot verification. It receives no App or
provider credentials and emits only a fixed message on failure.
"""
import os
import sys
import time

from central_review_hub import HUB, Hub, load_config, require

MAX_BYTES = 8192
MAX_SECONDS = 60
FAILURE = 'central pilot pre-token verification failed'


def verify(envelope, scope):
    raw = envelope.encode('ascii')
    require(0 < len(raw) <= MAX_BYTES)
    config = load_config()
    limit = min(MAX_SECONDS, config['limits']['run_timeout_seconds'])
    hub = Hub(config, api=None, sources=None, lanes=None, preflight=None,
              deadline=time.monotonic() + limit)
    request, _deadline = hub.prepare_one_shot(raw)
    hub_owner, hub_name = HUB.split('/', 1)
    owner, name = request['repository'].split('/', 1)
    require(owner == hub_owner)
    require(scope == hub_name + ',' + name)


def main():
    try:
        verify(os.environ.get('CENTRAL_ONE_SHOT_ENVELOPE', ''),
               os.environ.get('CENTRAL_ONE_SHOT_REPOSITORIES', ''))
    except Exception:
        sys.stderr.write(FAILURE + '\n')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
