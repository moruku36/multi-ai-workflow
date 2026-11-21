# Credential-minimizing scope check for the dormant recurring central path.
#
# The recurring installation token must cover exactly the hub (ledger only) and
# one public advisory target. Anything else fails closed before the controller.
import os
import sys
import time
from datetime import datetime, timezone

from central_review_hub import GitHub, HUB, OWNER, eligible_repo, load_config, pages, require, utc

HUB_ID = 1365934149
OWNER_ID = 12478466
TARGET = 'moruku36/local-ai-sidekick'
TARGET_ID = 1369269341
COHORT = ((HUB_ID, HUB), (TARGET_ID, TARGET))
EXPECTED_SCOPE = ','.join(full.split('/', 1)[1] for _, full in COHORT)
READBACK_SECONDS = 45
MESSAGE = 'central recurring scope check failed'


def verify_enabled(config):
    # Exact keys of the real configuration; no unrelated boolean inference.
    require(config['enabled'] is True)
    require(config['paid_execution_authorized'] is True)


def verify_pre_token(config, environ, now):
    # Credential-free and API-free: validate scope, enablement and cutoff.
    require(environ.get('CENTRAL_RECURRING_REPOSITORIES') == EXPECTED_SCOPE)
    require(environ.get('CENTRAL_REVIEW_ENABLED') == 'true')
    verify_enabled(config)
    require(utc(environ.get('CENTRAL_REVIEW_SINCE')) <= now)


def require_public(row):
    # Actual REST fields; the hub is a ledger anchor only, never a review target.
    owner = row.get('owner')
    require(row.get('private') is False)
    require(row.get('visibility') == 'public')
    require(row.get('disabled') is False)
    require(isinstance(owner, dict) and owner.get('login') == OWNER)
    # Exact integer owner ID; bool, float, string and null are rejected.
    require(type(owner.get('id')) is int and owner['id'] == OWNER_ID)


def verify_installation(api):
    # Bounded complete read of the token's repositories against the cohort.
    rows = pages(api, '/installation/repositories?', 'repositories', len(COHORT))
    by_id = {row['id']: row for row in rows}
    require({(repo_id, row.get('full_name')) for repo_id, row in by_id.items()} == set(COHORT))
    for row in rows:
        require_public(row)
    # The hub anchors the immutable-SHA ledger: archived or unknown is blocked.
    require(by_id[HUB_ID].get('archived') is False)
    found = eligible_repo(by_id[TARGET_ID])
    require(found is not None and found[0] == TARGET)


def main(argv=None, clock=None):
    args = sys.argv[1:] if argv is None else list(argv)
    try:
        require(len(args) == 1 and args[0] in ('pre-token', 'readback'))
        config = load_config()
        if args[0] == 'pre-token':
            now = clock() if clock else datetime.now(timezone.utc)
            verify_pre_token(config, os.environ, now)
        else:
            verify_enabled(config)
            deadline = time.monotonic() + READBACK_SECONDS
            api = GitHub(config['limits'], deadline)
            verify_installation(api)
    except Exception:
        print(MESSAGE, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
