from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
import re
import time
import uuid

if __package__:
    from ._central_review_hub_support import (
        ANCHOR,
        Blocked,
        HUB,
        LANES,
        LEDGER,
        OWNER,
        RECEIPT,
        REPO,
        current,
        discover,
        failed_lane_metadata,
        json_bytes,
        object_api,
        pages,
        positive,
        require,
        sha,
        stamp,
        strict_json,
        token,
        utc,
        validate_config,
    )
else:
    from _central_review_hub_support import (
        ANCHOR,
        Blocked,
        HUB,
        LANES,
        LEDGER,
        OWNER,
        RECEIPT,
        REPO,
        current,
        discover,
        failed_lane_metadata,
        json_bytes,
        object_api,
        pages,
        positive,
        require,
        sha,
        stamp,
        strict_json,
        token,
        utc,
        validate_config,
    )


class HttpFailure(Blocked):
    """Carries only a coarse numeric status; never body, header or URL."""

    def __init__(self, status):
        super().__init__()
        self.status = status


class CheckWriteFailure(Blocked):
    """Fixed-vocabulary check write/readback failure; no data-dependent text."""

    def __init__(self, kind, phase, category, status=None):
        super().__init__()
        self.detail = {"kind": kind, "phase": phase, "category": category}
        if type(status) is int and 100 <= status <= 599:
            self.detail["http_status"] = status


class GitHub:
    """Fixed host, bounded responses/deadline, no redirect or automatic retry."""

    def __init__(self, limits, deadline):
        self.limits, self.deadline = limits, deadline
        self.key = token("GH_TOKEN")

    def __call__(self, method, path, payload=None):
        require(method in ("GET", "POST", "PATCH") and path.startswith("/")
                and not any(c in path for c in "\r\n#"))
        remaining = self.deadline - time.monotonic()
        require(remaining > 0)
        timeout = min(self.limits["github_timeout_seconds"], remaining)
        body = None if payload is None else json_bytes(payload)
        require(body is None or len(body) <= 60000)
        conn = http.client.HTTPSConnection("api.github.com", timeout=timeout)
        end = min(self.deadline, time.monotonic() + timeout)
        try:
            conn.request(method, path, body, {
                "Authorization": "Bearer " + self.key,
                "User-Agent": "central-review-hub", "Accept": "application/vnd.github+json",
                "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"})
            response = conn.getresponse()
            if response.status != (201 if method == "POST" else 200):
                raise HttpFailure(response.status)
            link = response.getheader("Link", "")
            require(len(link) <= 4096)
            # Never follow the URL. Only a bounded, locally constructed next page.
            more = False
            if link:
                for part in link.split(","):
                    match = re.fullmatch(r'<[^<>]+>; rel="(next|prev|first|last)"', part.strip())
                    require(match is not None)
                    if match[1] == "next":
                        require(not more)
                        more = True
            chunks, size = [], 0
            while True:
                left = end - time.monotonic()
                require(left > 0)
                if conn.sock is not None:
                    conn.sock.settimeout(left)
                chunk = response.read1(min(65536, self.limits["github_response_bytes"] + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                require(size <= self.limits["github_response_bytes"])
            return strict_json(b"".join(chunks)), more
        finally:
            conn.close()


def checks(api, repository, head, name, maximum):
    return pages(api, f"/repos/{repository}/commits/{head}/check-runs?"
                 f"check_name={name}&filter=all", "check_runs", maximum)


def check_summary(report, maximum):
    body = json_bytes(report).decode("ascii")
    # All source-derived strings have gone through plain(); no fence breakers
    # or mentions survive. Raw source/provider bodies are never included.
    summary = ("Partial source-only review; same provider/model; independence unverified. "
               "Untrusted finding previews require human resolution. No quality acceptance "
               "or merge authorization. Unknown outcomes consume reservations.\n\n```json\n"
               + body + "\n```")
    require(len(summary.encode()) <= maximum)
    return {"title": "Central review receipt", "summary": summary}


def write_failure(kind, phase, error):
    if isinstance(error, HttpFailure):
        return CheckWriteFailure(kind, phase, "http_status", error.status)
    if isinstance(error, (Blocked, json.JSONDecodeError, UnicodeDecodeError)):
        return CheckWriteFailure(kind, phase, "invalid_response")
    return CheckWriteFailure(kind, phase, "unavailable")


def check_matches(saved, check_id, name, head, identity, status, conclusion, output):
    """Pure exact readback match; extra GitHub fields (including output) allowed."""
    if not isinstance(saved, dict):
        return False
    saved_output = saved.get("output")
    if not isinstance(saved_output, dict):
        return False
    return (type(saved.get("id")) is int and saved["id"] == check_id
            and saved.get("name") == name and saved.get("head_sha") == head
            and saved.get("external_id") == identity and saved.get("status") == status
            and "conclusion" in saved and saved["conclusion"] == conclusion
            and saved_output.get("title") == output.get("title")
            and saved_output.get("summary") == output.get("summary"))


def readback(api, kind, repository, check_id, name, head, identity, status,
             conclusion, output):
    # Exactly one GET by the already-known ID; never retried.
    try:
        saved, more = api("GET", f"/repos/{repository}/check-runs/{check_id}")
    except Exception as error:
        raise write_failure(kind, "readback_fetch", error) from None
    if more is not False or not check_matches(saved, check_id, name, head, identity,
                                              status, conclusion, output):
        raise CheckWriteFailure(kind, "readback_validate", "mismatch")


def create_check(api, repository, name, head, identity, output, **extra):
    kind = "ledger" if name == LEDGER else "receipt"
    payload = {"name": name, "head_sha": head, "external_id": identity,
               "status": "in_progress", "output": output, **extra}
    try:
        created = object_api(api, "POST", f"/repos/{repository}/check-runs", payload)
        check_id = positive(created.get("id"))
    except Exception as error:
        raise write_failure(kind, "post_ack", error) from None
    # Acknowledgment alone is insufficient: require durable readable state.
    readback(api, kind, repository, check_id, name, head, identity,
             payload["status"], payload.get("conclusion"), output)
    return check_id


def validate_one_shot(request, *, controller_revision, now):
    """Legacy read-only proposal validation; never grants execution authority.

    Retained for existing offline checks. Production uses signed envelopes,
    not this proposal's evidence digest or caller-supplied revision.
    """
    require(isinstance(request, dict) and set(request) == {
        'repository', 'pr', 'base', 'head', 'controller_revision', 'expires_at',
        'eligible_since', 'lane_attempt_limits', 'authorization_evidence_sha256'})
    repository = request['repository']
    require(isinstance(repository, str) and REPO.fullmatch(repository)
            and repository.split('/')[0] == OWNER and repository.lower() != HUB.lower())
    positive(request['pr'])
    for key in ('base', 'head', 'controller_revision'):
        sha(request[key])
    require(request['controller_revision'] == sha(controller_revision))
    require(utc(request['eligible_since']) <= now < utc(request['expires_at']))
    require((utc(request['expires_at']) - now).total_seconds() <= 3600)
    limits = request['lane_attempt_limits']
    require(isinstance(limits, dict) and set(limits) == set(LANES))
    for lane, cap in (('alibaba', 8), ('cloudflare', 1)):
        require(type(limits[lane]) is int and 1 <= limits[lane] <= cap)
    require(isinstance(request['authorization_evidence_sha256'], str)
            and re.fullmatch(r'[0-9a-f]{64}', request['authorization_evidence_sha256']))
    return dict(request)


class Hub:
    """The injected seams never replace production lanes with synthetic success."""

    def __init__(self, config, *, api, sources, lanes, preflight, now=None, deadline=None):
        self.config = validate_config(config)
        self.limits = config["limits"]
        self.api, self.sources, self.lanes, self.preflight = api, sources, lanes, preflight
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.deadline = deadline or (time.monotonic() + self.limits["run_timeout_seconds"])
        self.aggregate = {"status": "BLOCKED_OR_UNKNOWN", "reservations": 0,
                          "completed": 0, "failed_or_unknown": 0}
        self.run_id = uuid.uuid4().hex

    def prepare_one_shot(self, envelope):
        """Verify operator AND launcher; no injectable authorization callback.

        Runtime provenance verification uses GitHub OIDC, not a local paid route.
        The old digest-only proposal contract is deliberately unsupported.
        """
        import central_one_shot_auth as auth
        from central_one_shot_provenance import verify_launcher
        revision = auth.controller_revision(self.deadline)
        validation_started = time.monotonic()
        request, authorization_deadline = auth.verify_envelope(
            envelope, revision=revision, now=self.now(),
            validation_started=validation_started, deadline=self.deadline)
        verify_launcher(revision=revision, envelope=envelope, deadline=authorization_deadline)
        auth.active(request, self.now())
        require(time.monotonic() < authorization_deadline)
        return request, authorization_deadline

    def run_one_shot(self, envelope):
        try:
            request, authorization_deadline = self.prepare_one_shot(envelope)
            binary = self.preflight()
            since = utc(request["eligible_since"])
            # Exactly one target. Never call installation/PR discovery here.
            candidates = [(since, request["repository"], request["pr"],
                           request["base"], request["head"])]
            return self._run_targets(candidates, since, binary, authorization=request,
                                     authorization_deadline=authorization_deadline)
        except Exception:
            self.aggregate["status"] = "BLOCKED_OR_UNKNOWN"
            self.aggregate["failed_or_unknown"] = max(1, self.aggregate["failed_or_unknown"])
            return dict(self.aggregate)

    def ledger(self):
        # A missing anchor, unavailable collection, corrupt row or any
        # truncation stops ALL paid work; no local/empty-ledger fallback.
        anchor = object_api(self.api, "GET", f"/repos/{HUB}/commits/{ANCHOR}")
        require(anchor.get("sha") == ANCHOR)
        rows = checks(self.api, HUB, ANCHOR, LEDGER, self.limits["ledger_entries"])
        identities, today, current_run = set(), 0, 0
        day = self.now().date()
        for row in rows:
            require(row.get("name") == LEDGER and row.get("head_sha") == ANCHOR)
            external = row.get("external_id")
            require(isinstance(external, str) and re.fullmatch(r"central-v1:[0-9a-f]{64}", external))
            started = utc(row.get("started_at"))
            meta = strict_json(row["output"]["summary"])
            require(isinstance(meta, dict) and set(meta) == {
                "schema_version", "run_id", "reserved_at", "identity_hash", "consumed",
                "state", "refunds", "retries"})
            require(type(meta["schema_version"]) is int and meta["schema_version"] == 1
                    and meta["consumed"] is True and meta["refunds"] is False
                    and meta["retries"] is False and meta["state"] == "RESERVED_OUTCOME_UNKNOWN"
                    and isinstance(meta["run_id"], str) and re.fullmatch(r"[0-9a-f]{32}", meta["run_id"])
                    and external == "central-v1:" + meta["identity_hash"])
            reserved = utc(meta["reserved_at"])
            # Count across a midnight boundary conservatively on either date.
            require(started.date() <= day and reserved.date() <= day)
            today += int(day in (started.date(), reserved.date()))
            current_run += int(meta["run_id"] == self.run_id)
            identities.add(external)
        return identities, today, current_run

    def target_seen(self, repository, base, head):
        identity = base + ":" + head
        rows = checks(self.api, repository, head, RECEIPT, self.limits["target_receipts"])
        require(all(row.get("name") == RECEIPT and row.get("head_sha") == head for row in rows))
        return any(row.get("external_id") == identity for row in rows)

    def update_target(self, repository, check_id, identity, head, report, conclusion=None):
        payload = {"status": "completed" if conclusion else "in_progress",
                   "output": check_summary(report, self.limits["target_output_bytes"])}
        if conclusion:
            payload.update(conclusion=conclusion, completed_at=stamp(self.now()))
        try:
            object_api(self.api, "PATCH", f"/repos/{repository}/check-runs/{check_id}", payload)
        except Exception as error:
            raise write_failure("receipt", "patch_ack", error) from None
        readback(self.api, "receipt", repository, check_id, RECEIPT, head, identity,
                 payload["status"], conclusion or None, payload["output"])

    def run(self, environ=None):
        env = os.environ if environ is None else environ
        try:
            if env.get("CENTRAL_REVIEW_ENABLED") != "true" or not self.config["enabled"]:
                self.aggregate["status"] = "DISABLED"
                return dict(self.aggregate)
            since = utc(env.get("CENTRAL_REVIEW_SINCE"))
            require(since <= self.now() and self.config["paid_execution_authorized"])
            binary = self.preflight()
            self.ledger()
            candidates = discover(self.api, self.limits, since)
            return self._run_targets(candidates, since, binary)
        except Exception:
            self.aggregate["status"] = "BLOCKED_OR_UNKNOWN"
            self.aggregate["failed_or_unknown"] = max(1, self.aggregate["failed_or_unknown"])
        return dict(self.aggregate)

    def _run_targets(self, candidates, since, binary, authorization=None,
                     authorization_deadline=None):
        """ONE reservation/receipt lifecycle, shared by both production modes."""
        try:
            attempt_deadline = None
            if authorization is not None:
                from central_one_shot_auth import active, validate_lane_attempt_limits
                require(authorization_deadline is not None)
                validate_lane_attempt_limits(authorization["lane_attempt_limits"])
                attempt_deadline = min(self.deadline, authorization_deadline)

            def check_authorization():
                if authorization is not None:
                    active(authorization, self.now())
                    require(time.monotonic() < attempt_deadline)

            any_failure = False
            for _updated, repository, number, base, head in candidates:
                require(time.monotonic() < self.deadline)
                if authorization is not None:
                    check_authorization()
                    require(len(candidates) == 1 and (repository, number, base, head) == tuple(
                        authorization[k] for k in ("repository", "pr", "base", "head")))
                if self.aggregate["reservations"] >= self.limits["reservations_per_run"]:
                    break
                if current(self.api, repository, number, since) != (base, head):
                    require(authorization is None)
                    continue
                digest = hashlib.sha256((repository.lower() + "\0" + base + "\0" + head).encode()).hexdigest()
                external, target_identity = "central-v1:" + digest, base + ":" + head
                identities, today, run_count = self.ledger()
                if external in identities or self.target_seen(repository, base, head):
                    require(authorization is None)
                    continue
                if today >= self.limits["reservations_per_utc_day"]:
                    require(authorization is None)
                    break
                require(run_count < self.limits["reservations_per_run"])
                check_authorization()
                # Global reservation BEFORE target reservation BEFORE sources.
                # Increment locally before a possibly ambiguous POST; never retry.
                self.aggregate["reservations"] += 1
                meta = {"schema_version": 1, "run_id": self.run_id,
                        "reserved_at": stamp(self.now()), "identity_hash": digest,
                        "consumed": True, "state": "RESERVED_OUTCOME_UNKNOWN",
                        "refunds": False, "retries": False}
                create_check(self.api, HUB, LEDGER, ANCHOR, external,
                             {"title": "Consumed reservation; no retry or refund",
                              "summary": json_bytes(meta).decode()},
                             status="completed", conclusion="action_required",
                             started_at=stamp(self.now()),
                             completed_at=stamp(self.now()))
                identities, today, run_count = self.ledger()
                require(external in identities and today <= self.limits["reservations_per_utc_day"]
                        and run_count <= self.limits["reservations_per_run"])
                # Recheck existing target reservations; never edit somebody
                # else's reservation, even if it failed or is incomplete.
                require(not self.target_seen(repository, base, head))
                report = {"schema_version": 1, "base_tip_sha": base, "head_sha": head,
                          "status": "RESERVED_OUTCOME_UNKNOWN", "lanes": {},
                          "merge_authorized": False, "review_quality_accepted": False,
                          "independence": "NOT_VERIFIED_SAME_PROVIDER"}
                if authorization is not None:
                    # Fixed, public-safe attribution; no token/signature/private evidence.
                    from central_one_shot_auth import canonical, DOMAIN
                    report["one_shot"] = {
                        "issuer": authorization["issuer"], "key_id": authorization["key_id"],
                        "controller_revision": authorization["controller_revision"],
                        "eligible_since": authorization["eligible_since"],
                        "expires_at": authorization["expires_at"],
                        "lane_attempt_limits": dict(authorization["lane_attempt_limits"]),
                        "payload_sha256": hashlib.sha256(DOMAIN + canonical(authorization)).hexdigest()}
                check_authorization()
                check_id = create_check(self.api, repository, RECEIPT, head, target_identity,
                                        check_summary(report, self.limits["target_output_bytes"]))
                with ExitStack() as source_stack:
                    # Only source entry/extraction and binding validation are
                    # recoverable here. API/marker ambiguity stops the whole run.
                    try:
                        binding, diff, snapshots = source_stack.enter_context(
                            self.sources(repository, base, head))
                        require(binding["base_tip_sha"] == base and binding["head_sha"] == head)
                        sha(binding["base_sha"])
                        require(re.fullmatch(r"[0-9a-f]{64}", binding["diff_sha256"]))
                    except Exception:
                        report["status"] = "SOURCE_BLOCKED_OR_UNKNOWN"
                        self.update_target(repository, check_id, target_identity, head, report, "failure")
                        self.aggregate["failed_or_unknown"] += 1
                        any_failure = True
                        continue
                    report = {**binding, **report}
                    for lane in LANES:
                        require(time.monotonic() < self.deadline)
                        check_authorization()
                        require(current(self.api, repository, number, since) == (base, head))
                        # Never carry paid calls into a new UTC day using an
                        # earlier day's reservation. Keep the consumed marker.
                        require(utc(meta["reserved_at"]).date() == self.now().date())
                        report["lanes"][lane] = {**binding, "status": "OUTCOME_UNKNOWN"}
                        self.update_target(repository, check_id, target_identity, head, report)
                        # A durable unknown marker must be readable before any
                        # provider request, including after an earlier failure.
                        require(time.monotonic() < self.deadline)
                        require(current(self.api, repository, number, since) == (base, head))
                        require(utc(meta["reserved_at"]).date() == self.now().date())
                        check_authorization()
                        try:
                            outcome = (self.lanes(lane, binary, diff, snapshots) if authorization is None
                                       else self.lanes(lane, binary, diff, snapshots,
                                                       attempt_cap=authorization["lane_attempt_limits"][lane],
                                                       attempt_deadline=attempt_deadline))
                            require(isinstance(outcome, dict) and outcome.get("status") in
                                    ("completed", "FAILED_OR_UNKNOWN"))
                        except Exception:
                            outcome = failed_lane_metadata(lane)
                        if outcome["status"] == "FAILED_OR_UNKNOWN":
                            outcome = failed_lane_metadata(lane, outcome.get("diagnostics"))
                        report["lanes"][lane] = {**outcome, **binding}
                        self.update_target(repository, check_id, target_identity, head, report)
                    complete = all(report["lanes"][lane]["status"] == "completed" for lane in LANES)
                    findings = sum(r.get("finding_count", 0) for r in report["lanes"].values())
                    gaps = sum(r.get("gap_count", 0) for r in report["lanes"].values())
                    try:
                        stale = current(self.api, repository, number, since) != (base, head)
                    except Exception:
                        stale = True  # Unverifiable current revision is a failure.
                    report["status"] = ("STALE_OR_UNVERIFIABLE" if stale else
                                        "BOTH_RECORDED_NOT_ACCEPTED" if complete else "INCOMPLETE")
                    conclusion = ("failure" if stale or not complete else
                                  "action_required" if findings or gaps else "success")
                    self.update_target(repository, check_id, target_identity, head, report, conclusion)
                    failed = stale or not complete
                    self.aggregate["failed_or_unknown"] += int(failed)
                    self.aggregate["completed"] += int(not failed)
                    any_failure |= failed
            self.aggregate["status"] = "BLOCKED_OR_UNKNOWN" if any_failure else "COMPLETE"
        except Exception as error:
            self.aggregate["status"] = "BLOCKED_OR_UNKNOWN"
            self.aggregate["failed_or_unknown"] = max(1, self.aggregate["failed_or_unknown"])
            if isinstance(error, CheckWriteFailure):
                result = dict(self.aggregate)
                result["check_write_failure"] = dict(error.detail)
                return result
        return dict(self.aggregate)
