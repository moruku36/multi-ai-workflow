#!/usr/bin/env python3
"""Allowlist inspector for the Open WebUI 0.11.4 ``config`` table.

Local-only and read-only. It:
  * opens the SQLite file with ``mode=ro`` and ``PRAGMA query_only=ON``;
  * installs an SQLite authorizer so the connection cannot read anything except
    ``config.key`` / ``config.value`` (memory, chat, user and auth tables are
    unreachable even if the SQL were changed);
  * selects only the explicitly allowlisted setting keys below (no API keys,
    secrets, tokens or ``*.api_configs`` entries are ever fetched);
  * projects endpoint settings inside SQLite (JSON1) so that only the URL
    string(s) ever reach Python: an endpoint stored as a JSON object yields its
    nested ``url`` field only, an array yields one URL per element, and the raw
    object (which may carry credential fields) is never selected. If JSON1 is
    unavailable the inspector fails closed instead of selecting raw values;
  * never prints a raw stored value: values are validated per key, endpoint
    URLs are reduced to scheme/host/port, and anything unexpected is redacted;
  * fails closed on an unknown schema and never reports success on failure.

It reports persisted ``config`` rows only. Effective runtime settings can differ
(environment overrides, unsaved UI state), so every result needs live
confirmation. It makes no network calls (hostnames are classified lexically,
never resolved), so it cannot prove where a host name or address really points.

Exit codes: 0 = checks passed, 1 = a policy check failed, 2 = usage/schema/open
failure (nothing trustworthy was read), 3 = a value could not be interpreted.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import math
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit

# key -> (kind, default when the key is not persisted, as of Open WebUI 0.11.4)
ALLOWLIST: dict[str, tuple[str, object]] = {
    "memories.enable": ("bool", True),
    "memories.system_context.enable": ("bool", True),
    "memories.background_review.enable": ("bool", False),
    "memories.review_interval_turns": ("int", 10),
    "memories.user_char_limit": ("int", 2000),
    "memories.context_char_limit": ("int", 2000),
    "rag.embedding_engine": ("engine", ""),
    "rag.embedding_model": ("model", "sentence-transformers/all-MiniLM-L6-v2"),
    "rag.embedding_batch_size": ("int", None),
    "rag.relevance_threshold": ("float", 0.0),
    "rag.ollama.base_url": ("url", None),
    "rag.openai.api_base_url": ("url", None),
    "rag.azure_openai.base_url": ("url", None),
    "ollama.base_urls": ("url_list", None),
    "openai.api_base_urls": ("url_list", None),
    "task.model.default": ("model", ""),
    "task.model.external": ("model", ""),
    "chat.tool_permissions.enable": ("bool", False),
}

MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@\-]{0,127}$")
ENGINE_RE = re.compile(r"^[a-z_]{0,32}$")
HOST_RE = re.compile(r"^[A-Za-z0-9._\-]{1,253}$")
SECRET_PREFIX_RE = re.compile(r"^(sk|pk|rk|ghp|gho|xox[abp]|hf|AIza)[-_]", re.IGNORECASE)
LONG_RUN_RE = re.compile(r"[A-Za-z0-9]{32,}")
REDACTED = "<redacted>"

EXIT_OK, EXIT_POLICY, EXIT_UNTRUSTED, EXIT_UNINTERPRETABLE = 0, 1, 2, 3


class InspectError(Exception):
    """Raised when the database cannot be trusted; carries no stored values."""


# ---------------------------------------------------------------- sqlite


JSON_FUNCTIONS = {"json_valid", "json_type", "json_extract"}
JSON_EACH_COLUMNS = {"key", "value", "type", "json", "root"}


def _authorizer(action, arg1, arg2, dbname, source):
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION and arg2 in JSON_FUNCTIONS:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ and arg1 == "json_each" and arg2 in JSON_EACH_COLUMNS:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ and arg1 == "config" and arg2 in {"key", "value"}:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and arg1 in {"table_info", "query_only"}:
        return sqlite3.SQLITE_OK
    # PRAGMA table_info('config') consults the schema table for that one table.
    if action == sqlite3.SQLITE_READ and arg1 == "sqlite_master" and arg2 in {"name", "sql", "type", "tbl_name"}:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def open_readonly(db_path: Path) -> sqlite3.Connection:
    path = Path(db_path)
    if not path.is_file():
        raise InspectError("database file not found")
    uri = "file:" + quote(path.resolve().as_posix(), safe="/:") + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=5)
        conn.execute("PRAGMA query_only=ON")
        conn.set_authorizer(_authorizer)
    except sqlite3.Error as exc:
        raise InspectError(f"cannot open database read-only ({type(exc).__name__})") from None
    return conn


def check_config_schema(conn: sqlite3.Connection) -> None:
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info('config')")}
    except sqlite3.Error as exc:
        raise InspectError(f"cannot read config schema ({type(exc).__name__})") from None
    if not {"key", "value"} <= columns:
        raise InspectError("unknown schema: config table with key/value columns not found")


UNSUPPORTED = object()  # endpoint value whose shape could not be projected safely
ENDPOINT_KINDS = {"url", "url_list"}


def _endpoint_keys(kind: str) -> list[str]:
    return [key for key, (k, _) in ALLOWLIST.items() if k == kind]


def check_json1(conn: sqlite3.Connection) -> None:
    """Fail closed when SQLite cannot project JSON; never fall back to raw values."""
    try:
        probe = conn.execute("SELECT json_valid('{}'), json_type('[]'), json_extract('{\"a\":1}', '$.a')").fetchone()
        conn.execute("SELECT key FROM json_each('[]')").fetchall()
    except sqlite3.Error as exc:
        raise InspectError(f"SQLite JSON1 unavailable; refusing to read endpoint settings ({type(exc).__name__})") from None
    if probe != (1, "array", 1):
        raise InspectError("SQLite JSON1 behaves unexpectedly; refusing to read endpoint settings")


def fetch_allowlisted(conn: sqlite3.Connection) -> dict[str, str | None]:
    """Raw JSON text for non-endpoint keys only; endpoint keys are never selected raw."""
    keys = [key for key, (kind, _) in ALLOWLIST.items() if kind not in ENDPOINT_KINDS]
    marks = ",".join("?" for _ in keys)
    try:
        rows = conn.execute(f"SELECT key, value FROM config WHERE key IN ({marks})", keys).fetchall()
    except sqlite3.Error as exc:
        raise InspectError(f"cannot read allowlisted config rows ({type(exc).__name__})") from None
    return {key: value for key, value in rows if key in ALLOWLIST}


def _url_from_object(expr: str) -> str:
    return f"CASE json_type({expr}, '$.url') WHEN 'text' THEN json_extract({expr}, '$.url') END"


def fetch_endpoints(conn: sqlite3.Connection) -> dict[str, object]:
    """Project endpoint settings to URL strings inside SQLite.

    Returns key -> URL string | UNSUPPORTED for ``url`` keys and key -> list of
    those for ``url_list`` keys. A stored JSON object contributes only its
    nested ``url`` field; its other (credential) fields are never in a select
    list, so they cannot reach Python. Scalar strings are accepted because the
    0.11.4 source stores ``rag.*`` base URLs and the provider URL lists that way.
    """
    check_json1(conn)
    result: dict[str, object] = {}
    url_keys, list_keys = _endpoint_keys("url"), _endpoint_keys("url_list")
    try:
        marks = ",".join("?" for _ in url_keys)
        sql = (
            "SELECT key, CASE WHEN json_valid(value) THEN json_type(value) END, "
            "CASE WHEN json_valid(value) THEN CASE json_type(value) "
            "WHEN 'text' THEN json_extract(value, '$') "
            f"WHEN 'object' THEN {_url_from_object('value')} END END "
            f"FROM config WHERE key IN ({marks})"
        )
        for key, vtype, url in conn.execute(sql, url_keys).fetchall():
            result[key] = url if vtype in {"text", "object"} and isinstance(url, str) else UNSUPPORTED
        marks = ",".join("?" for _ in list_keys)
        types = conn.execute(
            f"SELECT key, CASE WHEN json_valid(value) THEN json_type(value) END FROM config WHERE key IN ({marks})",
            list_keys,
        ).fetchall()
        for key, vtype in types:
            result[key] = [] if vtype == "array" else UNSUPPORTED
        sql = (
            # j.type, not json_type(j.value): a text element's value is not itself JSON.
            "SELECT c.key, j.type, CASE j.type "
            "WHEN 'text' THEN j.value "
            f"WHEN 'object' THEN {_url_from_object('j.value')} END "
            "FROM config AS c, json_each(c.value) AS j "
            f"WHERE c.key IN ({marks}) AND json_valid(c.value) AND json_type(c.value) = 'array' "
            "ORDER BY c.key, CAST(j.key AS INTEGER)"
        )
        for key, etype, url in conn.execute(sql, list_keys).fetchall():
            result[key].append(url if etype in {"text", "object"} and isinstance(url, str) else UNSUPPORTED)
    except sqlite3.Error as exc:
        raise InspectError(f"cannot project endpoint settings ({type(exc).__name__})") from None
    return result


# ------------------------------------------------------------- redaction


def classify_host(host: str) -> str:
    """Lexical classification only; never resolves names (no network)."""
    lowered = host.lower().strip("[]")
    if lowered == "localhost" or lowered.endswith(".localhost"):
        return "loopback"
    if lowered in {"host.docker.internal", "host.containers.internal"}:
        return "local-host-alias"
    try:
        ip = ipaddress.ip_address(lowered)
    except ValueError:
        return "non-local-or-unknown"
    if ip.is_unspecified:
        return "unknown"
    if ip.is_loopback:
        return "loopback"
    if ip.is_private or ip.is_link_local:
        return "private-network"
    return "non-local-or-unknown"


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def redact_url(raw: object) -> dict:
    """Reduce a URL to scheme/host/port. Drops userinfo, path, query, fragment."""
    if not isinstance(raw, str):
        return {"value": REDACTED, "locality": "unknown"}
    if raw.strip() == "":
        return {"value": "(empty)", "locality": "none"}
    try:
        parts = urlsplit(raw.strip())
        host = parts.hostname
        port = parts.port
    except ValueError:
        return {"value": REDACTED, "locality": "unknown"}
    if parts.scheme not in {"http", "https"} or not host or not (HOST_RE.match(host) or _is_ip_literal(host)):
        return {"value": REDACTED, "locality": "unknown"}
    shown_host = f"[{host}]" if ":" in host else host
    shown = f"{parts.scheme}://{shown_host}" + (f":{port}" if port else "")
    return {
        "value": shown,
        "locality": classify_host(host),
        "dropped": [
            name
            for name, present in (
                ("userinfo", "@" in parts.netloc),
                ("path", parts.path not in ("", "/")),
                ("query", bool(parts.query)),
                ("fragment", bool(parts.fragment)),
            )
            if present
        ],
    }


def _safe_token(text: str, pattern: re.Pattern) -> str:
    if not pattern.match(text) or SECRET_PREFIX_RE.match(text) or LONG_RUN_RE.search(text):
        return REDACTED
    return text


def render_value(kind: str, parsed: object) -> dict:
    """Return a printable description of ``parsed``; never the raw object."""
    if kind == "bool":
        return {"value": parsed} if isinstance(parsed, bool) else {"value": REDACTED, "invalid": True}
    if kind == "int":
        ok = isinstance(parsed, int) and not isinstance(parsed, bool)
        return {"value": parsed} if ok else {"value": REDACTED, "invalid": True}
    if kind == "float":
        ok = isinstance(parsed, (int, float)) and not isinstance(parsed, bool) and math.isfinite(parsed)
        return {"value": parsed} if ok else {"value": REDACTED, "invalid": True}
    if kind in {"engine", "model"}:
        if not isinstance(parsed, str):
            return {"value": REDACTED, "invalid": True}
        shown = _safe_token(parsed, ENGINE_RE if kind == "engine" else MODEL_RE) if parsed else ""
        return {"value": shown if shown != "" else "(empty)", "invalid": shown == REDACTED}
    if kind == "url":
        info = redact_url(None if parsed is UNSUPPORTED else parsed)
        info["invalid"] = info["value"] == REDACTED
        return info
    if kind == "url_list":
        if not isinstance(parsed, list):
            return {"value": REDACTED, "invalid": True}
        items = [redact_url(None if item is UNSUPPORTED else item) for item in parsed]
        return {"items": items, "invalid": any(i["value"] == REDACTED for i in items)}
    return {"value": REDACTED, "invalid": True}


# -------------------------------------------------------------- reporting


def build_report(stored: dict[str, str | None], endpoints: dict[str, object] | None = None) -> dict:
    endpoints = endpoints or {}
    settings: dict[str, dict] = {}
    for key, (kind, default) in ALLOWLIST.items():
        if kind in ENDPOINT_KINDS:
            if key in endpoints:
                settings[key] = {"persisted": True, **render_value(kind, endpoints[key])}
            else:
                settings[key] = {"persisted": False}
            continue
        if key not in stored:
            settings[key] = {"persisted": False, "default_if_absent": default if default is not None else "(none)"}
            continue
        raw = stored[key]
        # SQLite's JSON/NUMERIC affinity can return native int/float values
        # directly. Text values remain JSON encoded by Open WebUI.
        if isinstance(raw, (bool, int, float)) or raw is None:
            parsed = raw
        elif isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except (TypeError, ValueError):
                parsed = UNSUPPORTED
        else:
            parsed = UNSUPPORTED
        if parsed is UNSUPPORTED:
            settings[key] = {"persisted": True, "value": REDACTED, "invalid": True}
            continue
        settings[key] = {"persisted": True, **render_value(kind, parsed)}
    return {"settings": settings, "findings": derive_findings(settings)}


def _effective(settings: dict, key: str):
    entry = settings[key]
    if entry.get("invalid"):
        return None
    value = entry["value"] if entry.get("persisted") else entry.get("default_if_absent")
    return "" if value == "(empty)" else value


def derive_findings(settings: dict) -> list[dict]:
    findings = []

    def add(level: str, text: str) -> None:
        findings.append({"level": level, "text": text})

    if _effective(settings, "memories.enable") is not True:
        add("INFO", "memories.enable is not true (or unreadable): standard Memory is not confirmed enabled.")
    if _effective(settings, "memories.background_review.enable") is not False:
        add("FAIL", "memories.background_review.enable is not false: the server may write memories without an explicit user action.")
    engine = _effective(settings, "rag.embedding_engine")
    model = _effective(settings, "rag.embedding_model")
    if engine == "":
        if model == "sentence-transformers/all-MiniLM-L6-v2":
            add(
                "OK",
                "Persisted/default embedding is the in-process sentence-transformers MiniLM configuration: no configured "
                "embedding endpoint is called. This does not prove network silence (model download/load or hub traffic is "
                "not excluded) and environment overrides are unknown; keep the live egress gate.",
            )
        else:
            add("WARN", "Built-in embedding engine with a model other than the reference MiniLM; confirm the model is a local download.")
    elif engine == "ollama":
        locality = settings["rag.ollama.base_url"].get("locality")
        if locality == "loopback":
            add("WARN", "Embedding engine is ollama at a loopback URL; memory text goes to that service. Loopback is lexical: confirm live that the listener is the intended local process.")
        elif locality == "local-host-alias":
            add("WARN", "UNVERIFIED: embedding engine is ollama at a container host alias (e.g. host.docker.internal). This is not asserted to be loopback; it resolves to the container host and needs live host verification.")
        elif locality == "private-network":
            add("FAIL", "Embedding engine is ollama at a private-network address (RFC1918/link-local). That is another machine or VM, not provably this machine: it fails strict local-only unless a live host verification proves it is the same host.")
        else:
            add("FAIL", "Embedding engine is ollama but its URL is not provably local (or is absent/unreadable): memory text could leave this machine.")
    else:
        add("FAIL", "Embedding engine is a non-builtin, non-ollama engine (e.g. openai, azure_openai): memory text may be sent to an external service.")
    if _effective(settings, "rag.relevance_threshold") in (0, 0.0):
        add("INFO", "rag.relevance_threshold is 0: retrieval returns the nearest memories regardless of similarity.")
    for key in ("rag.openai.api_base_url", "rag.azure_openai.base_url", "openai.api_base_urls"):
        entry = settings[key]
        urls = entry.get("items") if "items" in entry else ([entry] if entry.get("persisted") else [])
        if any(u.get("locality") == "non-local-or-unknown" for u in urls):
            add("INFO", f"{key} points at a non-local-looking host. Configuration alone does not prove it is used; no credentials were read.")
    for key in ("task.model.default", "task.model.external"):
        if settings[key].get("persisted") and settings[key].get("value") not in ("(empty)", REDACTED):
            add("INFO", f"{key} is set: auxiliary tasks route to that model; confirm in the live UI that it is local.")
    if _effective(settings, "chat.tool_permissions.enable") is True:
        add("INFO", "chat.tool_permissions.enable is true; this is NOT treated as a memory-save approval gate.")
    return findings


def format_text(report: dict) -> str:
    lines = ["Open WebUI 0.11.4 persisted config rows (allowlist; values redacted; credential fields never selected)", ""]
    for key, entry in report["settings"].items():
        if "items" in entry:
            body = "; ".join(f"{i['value']} [{i['locality']}]" for i in entry["items"]) or "(empty list)"
        elif entry.get("persisted"):
            body = str(entry["value"])
            if "locality" in entry:
                body += f" [{entry['locality']}]"
        else:
            body = "not persisted" + (
                f" (code default {entry['default_if_absent']!r}; env override unknown)" if "default_if_absent" in entry else ""
            )
        flag = "  <INVALID>" if entry.get("invalid") else ""
        lines.append(f"{key}: {body}{flag}")
    lines.append("")
    lines.extend(f"[{f['level']}] {f['text']}" for f in report["findings"])
    lines.append("")
    lines.append(
        "These are persisted rows, not effective runtime settings: environment variables may override them. "
        "Confirm in the live admin UI and keep a live egress check."
    )
    return "\n".join(lines)


def run(db_path: Path) -> tuple[int, dict | None, str]:
    try:
        conn = open_readonly(db_path)
        try:
            check_config_schema(conn)
            report = build_report(fetch_allowlisted(conn), fetch_endpoints(conn))
        finally:
            conn.close()
    except InspectError as exc:
        return EXIT_UNTRUSTED, None, f"ERROR: {exc}"
    if any(entry.get("invalid") for entry in report["settings"].values()):
        return EXIT_UNINTERPRETABLE, report, format_text(report) + "\nERROR: at least one value could not be interpreted."
    if any(f["level"] == "FAIL" for f in report["findings"]):
        return EXIT_POLICY, report, format_text(report) + "\nRESULT: policy check FAILED."
    return EXIT_OK, report, format_text(report) + "\nRESULT: no policy failures among allowlisted settings."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--db", required=True, type=Path, help="path to the Open WebUI SQLite file (opened read-only)")
    parser.add_argument("--json", action="store_true", help="print the redacted report as JSON")
    args = parser.parse_args(argv)
    code, report, text = run(args.db)
    if args.json and report is not None:
        print(json.dumps({"exit_code": code, **report}, indent=2, sort_keys=True))
    else:
        print(text, file=sys.stderr if code == EXIT_UNTRUSTED else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
