from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

import helpers
from helpers import (
    CANARY_CHAT,
    CANARY_ENDPOINT_KEY,
    CANARY_MEMORY,
    CANARY_SECRET,
    CANARY_USERINFO,
    build_synthetic_db,
)

import inspect_config as ic


def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = ic.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class InspectConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def db(self, **kw) -> Path:
        return build_synthetic_db(self.dir / "t.db", **kw)

    def assertNoCanaries(self, text: str):
        for canary in (
            CANARY_SECRET,
            CANARY_MEMORY,
            CANARY_CHAT,
            CANARY_USERINFO,
            CANARY_ENDPOINT_KEY,
            "CANARYPASS9921",
            "token=",
        ):
            self.assertNotIn(canary, text)

    def test_allowlist_has_no_credential_like_keys(self):
        for key in ic.ALLOWLIST:
            self.assertIsNone(re.search(r"(api_key|secret|token|password|credential|\.key$)", key), key)

    def test_report_redacts_endpoints_and_never_leaks_canaries(self):
        path = self.db()
        code, out, err = run_cli("--db", str(path))
        self.assertEqual(code, 0, out + err)
        self.assertNoCanaries(out + err)
        self.assertIn("http://localhost:11434 [loopback]", out)
        self.assertIn("https://api.example.invalid [non-local-or-unknown]", out)
        code, out, _ = run_cli("--db", str(path), "--json")
        self.assertNoCanaries(out)
        self.assertIn("userinfo", out)  # reports that something was dropped, not what
        json.loads(out)

    def test_source_file_is_not_modified(self):
        path = self.db()
        before = digest(path)
        run_cli("--db", str(path))
        run_cli("--db", str(path), "--json")
        self.assertEqual(before, digest(path))

    def test_connection_is_read_only_and_cannot_reach_other_tables(self):
        conn = ic.open_readonly(self.db())
        self.addCleanup(conn.close)
        with self.assertRaises(sqlite3.Error):
            conn.execute("UPDATE config SET value='1'")
        with self.assertRaises(sqlite3.Error):
            conn.execute("DELETE FROM config")
        for table in ("memory", "chat", "user", "auth"):
            with self.assertRaises(sqlite3.DatabaseError, msg=table):
                conn.execute(f"SELECT * FROM {table}").fetchall()
        with self.assertRaises(sqlite3.DatabaseError):  # only config.key / config.value are readable
            conn.execute("SELECT * FROM config").fetchall()

    def test_only_allowlisted_rows_are_fetched(self):
        conn = ic.open_readonly(self.db())
        self.addCleanup(conn.close)
        fetched = ic.fetch_allowlisted(conn)
        self.assertTrue(set(fetched) <= set(ic.ALLOWLIST))
        self.assertNotIn("openai.api_keys", fetched)
        self.assertNotIn("webui.secret_key", fetched)

    def test_fail_closed_unknown_schema(self):
        bad = self.dir / "bad.db"
        conn = sqlite3.connect(bad)
        conn.execute("CREATE TABLE other (a, b)")
        conn.commit()
        conn.close()
        code, out, err = run_cli("--db", str(bad))
        self.assertEqual(code, 2)
        self.assertIn("unknown schema", err)
        self.assertNotIn("RESULT", out + err)

    def test_fail_closed_config_without_value_column(self):
        bad = self.dir / "bad2.db"
        conn = sqlite3.connect(bad)
        conn.execute("CREATE TABLE config (key TEXT, data TEXT)")
        conn.commit()
        conn.close()
        self.assertEqual(run_cli("--db", str(bad))[0], 2)

    def test_missing_file_and_garbage_file_fail(self):
        self.assertEqual(run_cli("--db", str(self.dir / "nope.db"))[0], 2)
        junk = self.dir / "junk.db"
        junk.write_bytes(b"not a database" * 100)
        self.assertEqual(run_cli("--db", str(junk))[0], 2)

    def test_background_review_enabled_is_a_policy_failure(self):
        code, out, _ = run_cli("--db", str(self.db(config={"memories.background_review.enable": True})))
        self.assertEqual(code, 1)
        self.assertIn("[FAIL]", out)
        self.assertNoCanaries(out)

    def test_non_local_embedding_is_a_policy_failure(self):
        cfg = {"rag.embedding_engine": "openai", "rag.embedding_model": "text-embedding-x"}
        self.assertEqual(run_cli("--db", str(self.db(config=cfg)))[0], 1)

    def test_ollama_embedding_with_remote_url_fails_but_loopback_only_warns(self):
        remote = {"rag.embedding_engine": "ollama", "rag.ollama.base_url": "https://gpu.example.invalid"}
        self.assertEqual(run_cli("--db", str(self.db(config=remote)))[0], 1)
        (self.dir / "t.db").unlink()
        local = {"rag.embedding_engine": "ollama", "rag.ollama.base_url": "http://127.0.0.1:11434"}
        code, out, _ = run_cli("--db", str(self.db(config=local)))
        self.assertEqual(code, 0)
        self.assertIn("[WARN]", out)

    def test_wrong_types_and_secret_looking_values_are_redacted_not_printed(self):
        cfg = {
            "memories.enable": "yes",  # wrong type
            "rag.embedding_model": "sk-" + CANARY_SECRET,  # key pasted into a model field
            "task.model.default": CANARY_SECRET,  # long opaque run
        }
        code, out, err = run_cli("--db", str(self.db(config=cfg)))
        self.assertEqual(code, 3)
        self.assertNoCanaries(out + err)
        self.assertNotIn("sk-", out)
        self.assertIn("could not be interpreted", out)

    def test_unparseable_json_is_redacted(self):
        path = self.db()
        conn = sqlite3.connect(path)
        conn.execute("UPDATE config SET value=? WHERE key='memories.enable'", (CANARY_SECRET,))
        conn.commit()
        conn.close()
        code, out, err = run_cli("--db", str(path))
        self.assertEqual(code, 3)
        self.assertNoCanaries(out + err)

    def test_absent_keys_report_defaults(self):
        path = self.dir / "min.db"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE config (key TEXT PRIMARY KEY, value JSON NOT NULL)")
        conn.commit()
        conn.close()
        code, out, _ = run_cli("--db", str(path))
        self.assertEqual(code, 0)
        self.assertIn("not persisted (code default False; env override unknown)", out)  # background review default off
        self.assertIn("in-process sentence-transformers MiniLM", out)

    # ---- endpoint projection (JSON-object / array-of-object schema)

    def _flatten(self, obj) -> str:
        return repr(obj)

    def test_endpoint_objects_project_only_the_url_into_python(self):
        conn = ic.open_readonly(self.db())
        self.addCleanup(conn.close)
        endpoints = ic.fetch_endpoints(conn)
        plain = ic.fetch_allowlisted(conn)
        # Python only ever sees URL strings (or lists of them) for endpoint keys.
        self.assertIsInstance(endpoints["rag.ollama.base_url"], str)
        self.assertTrue(endpoints["rag.ollama.base_url"].startswith("http://"))
        self.assertEqual(endpoints["rag.openai.api_base_url"], "https://api.example.invalid/v1")
        self.assertEqual(endpoints["rag.azure_openai.base_url"], "https://azure.example.invalid")
        self.assertEqual(len(endpoints["openai.api_base_urls"]), 1)
        self.assertEqual(endpoints["ollama.base_urls"], ["http://127.0.0.1:11434"])
        for key in ic._endpoint_keys("url") + ic._endpoint_keys("url_list"):
            self.assertNotIn(key, plain)  # endpoint rows are never selected raw
        for text in (self._flatten(endpoints), self._flatten(plain)):
            self.assertNotIn(CANARY_ENDPOINT_KEY, text)
            self.assertNotIn("Authorization", text)
            self.assertNotIn("api_key", text)

    def test_endpoint_sql_never_selects_the_raw_endpoint_value(self):
        conn = ic.open_readonly(self.db())
        self.addCleanup(conn.close)
        statements: list[str] = []
        conn.set_trace_callback(statements.append)
        ic.fetch_endpoints(conn)
        ic.fetch_allowlisted(conn)
        endpoint_keys = ic._endpoint_keys("url") + ic._endpoint_keys("url_list")
        selects = [s for s in statements if " FROM config" in s and any(k in s for k in endpoint_keys)]
        self.assertEqual(len(selects), 3)  # url keys, list container types, list elements
        for sql in selects:
            head = sql.split(" FROM ")[0]
            # strip balanced json_*( ... ) calls; the bare column must not remain in the select list
            while True:
                m = re.search(r"json_\w+\(", head)
                if not m:
                    break
                depth, i = 1, m.end()
                while depth:
                    depth += {"(": 1, ")": -1}.get(head[i], 0)
                    i += 1
                head = head[: m.start()] + head[i:]
            # the one allowed bare read: a list element that is itself a text scalar (source-proven schema)
            head = head.replace("WHEN 'text' THEN j.value", "")
            self.assertNotRegex(head, r"\b(c\.)?value\b|\bj\.value\b", sql)

    def test_endpoint_report_strips_userinfo_path_query_and_hides_credentials(self):
        code, out, err = run_cli("--db", str(self.db()), "--json")
        self.assertEqual(code, 0, out + err)
        self.assertNoCanaries(out + err)
        report = json.loads(out)
        ollama = report["settings"]["rag.ollama.base_url"]
        self.assertEqual(ollama["value"], "http://localhost:11434")
        self.assertEqual(sorted(ollama["dropped"]), ["fragment", "path", "query", "userinfo"])
        provider = report["settings"]["openai.api_base_urls"]["items"][0]
        self.assertEqual(provider["value"], "https://api.example.invalid")
        self.assertIn("userinfo", provider["dropped"])
        self.assertEqual(report["settings"]["rag.azure_openai.base_url"]["value"], "https://azure.example.invalid")
        self.assertNoCanaries(ic.format_text(report))

    def test_malformed_endpoint_shapes_fail_closed_without_leaking(self):
        cases = {
            "rag.ollama.base_url": [
                {"key": CANARY_ENDPOINT_KEY},  # object without url
                {"url": {"nested": CANARY_ENDPOINT_KEY}},  # url is not a string
                [CANARY_ENDPOINT_KEY],  # wrong container
                7,
            ],
            "openai.api_base_urls": [
                CANARY_ENDPOINT_KEY,  # scalar instead of array
                [{"key": CANARY_ENDPOINT_KEY}],  # element without url
                [None, 3],
                {"url": "https://x.example.invalid", "key": CANARY_ENDPOINT_KEY},  # object instead of array
            ],
        }
        for key, values in cases.items():
            for value in values:
                with self.subTest(key=key, value=repr(value)[:30]):
                    path = self.dir / "m.db"
                    path.unlink(missing_ok=True)
                    code, out, err = run_cli("--db", str(self.db_at(path, {key: value})))
                    self.assertEqual(code, 3, out + err)
                    self.assertNoCanaries(out + err)

    def db_at(self, path: Path, config: dict) -> Path:
        return build_synthetic_db(path, config=config)

    def test_invalid_json_in_endpoint_row_is_uninterpretable_not_a_crash(self):
        path = self.db()
        conn = sqlite3.connect(path)
        conn.execute("UPDATE config SET value=? WHERE key='rag.ollama.base_url'", ("{" + CANARY_ENDPOINT_KEY,))
        conn.commit()
        conn.close()
        code, out, err = run_cli("--db", str(path))
        self.assertEqual(code, 3)
        self.assertNoCanaries(out + err)

    def test_scalar_endpoint_strings_still_supported(self):
        cfg = {"rag.ollama.base_url": "http://127.0.0.1:11434", "openai.api_base_urls": ["https://a.example.invalid"]}
        conn = ic.open_readonly(self.db(config=cfg))
        self.addCleanup(conn.close)
        endpoints = ic.fetch_endpoints(conn)
        self.assertEqual(endpoints["rag.ollama.base_url"], "http://127.0.0.1:11434")
        self.assertEqual(endpoints["openai.api_base_urls"], ["https://a.example.invalid"])

    def test_missing_json1_fails_closed_and_never_falls_back_to_raw(self):
        conn = ic.open_readonly(self.db())
        self.addCleanup(conn.close)
        conn.set_authorizer(
            lambda action, a1, a2, db, src: sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_FUNCTION and a2 == "json_valid"
            else ic._authorizer(action, a1, a2, db, src)
        )
        with self.assertRaises(ic.InspectError) as ctx:
            ic.fetch_endpoints(conn)
        self.assertIn("JSON1", str(ctx.exception))
        self.assertNotIn(CANARY_ENDPOINT_KEY, str(ctx.exception))

    def test_ollama_embedding_policy_by_locality(self):
        def code_for(url: str, shape: str) -> tuple[int, str]:
            path = self.dir / "p.db"
            path.unlink(missing_ok=True)
            value = {"url": url, "key": CANARY_ENDPOINT_KEY} if shape == "object" else url
            code, out, err = run_cli(
                "--db", str(self.db_at(path, {"rag.embedding_engine": "ollama", "rag.ollama.base_url": value}))
            )
            self.assertNoCanaries(out + err)
            return code, out

        for shape in ("object", "string"):
            for url in ("http://10.0.0.7:11434", "http://192.168.1.20:11434", "http://172.16.4.2", "http://169.254.1.1"):
                code, out = code_for(url, shape)
                self.assertEqual(code, 1, (shape, url))
                self.assertIn("[FAIL]", out)
                self.assertIn("private-network", out)
                self.assertIn("not provably this machine", out)
            code, out = code_for("https://gpu.example.invalid", shape)
            self.assertEqual(code, 1)
            code, out = code_for("http://127.0.0.1:11434", shape)  # loopback stays acceptable (WARN)
            self.assertEqual(code, 0)
            self.assertIn("[WARN]", out)
            self.assertNotIn("UNVERIFIED", out)
            code, out = code_for("http://localhost:11434", shape)
            self.assertEqual(code, 0)
            code, out = code_for("http://host.docker.internal:11434", shape)
            self.assertEqual(code, 0)
            self.assertIn("UNVERIFIED", out)
            self.assertIn("not asserted to be loopback", out)
            self.assertIn("[local-host-alias]", out)

    def test_azure_openai_embedding_engine_fails_policy(self):
        cfg = {"rag.embedding_engine": "azure_openai", "rag.embedding_model": "text-embedding-3-small"}
        code, out, _ = run_cli("--db", str(self.db(config=cfg)))
        self.assertEqual(code, 1)
        self.assertIn("azure_openai", out)
        self.assertIn("https://azure.example.invalid [non-local-or-unknown]", out)

    def test_wording_separates_persisted_rows_from_effective_runtime(self):
        code, out, _ = run_cli("--db", str(self.db()))
        self.assertEqual(code, 0)
        self.assertIn("persisted config rows", out)
        self.assertIn("not effective runtime settings", out)
        self.assertIn("no configured embedding endpoint is called", out)
        self.assertIn("does not prove network silence", out)
        self.assertIn("egress", out)
        self.assertNotIn("no embedding endpoint used", out)
        self.assertNotIn("no credentials read)", out)

    def test_redact_url_variants(self):
        r = ic.redact_url(f"http://{CANARY_USERINFO}@[::1]:8080/a/b?q={CANARY_SECRET}#f")
        self.assertEqual(r["value"], "http://[::1]:8080")
        self.assertEqual(r["locality"], "loopback")
        self.assertEqual(sorted(r["dropped"]), ["fragment", "path", "query", "userinfo"])
        for bad in ("file:///etc/passwd", "ftp://x", "http://", "://", 5, None, "http://bad host/"):
            self.assertEqual(ic.redact_url(bad)["value"], ic.REDACTED, bad)
        self.assertEqual(ic.redact_url("")["value"], "(empty)")
        self.assertEqual(ic.classify_host("192.168.1.5"), "private-network")
        self.assertEqual(ic.classify_host("8.8.8.8"), "non-local-or-unknown")
        self.assertEqual(ic.classify_host("localhost"), "loopback")


if __name__ == "__main__":
    unittest.main()
