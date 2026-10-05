from __future__ import annotations

import contextlib
import hashlib
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path

import helpers
from helpers import CANARY_MEMORY, build_synthetic_db

import backup_db as bk


def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = bk.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.src = build_synthetic_db(self.dir / "src.db")
        self.out = self.dir / "out"
        self.out.mkdir()

    def backup(self, dest: Path, confirm: bool = True):
        args = ["--source", str(self.src), "--dest", str(dest)]
        if confirm:
            args.append("--confirm-private-destination")
        return run_cli(*args)

    def test_success_copies_consistently_without_touching_source(self):
        before = digest(self.src)
        dest = self.out / "backup.db"
        code, out, err = self.backup(dest)
        self.assertEqual(code, 0, err)
        self.assertIn("Backup created and verified", out)
        self.assertEqual(before, digest(self.src))
        conn = sqlite3.connect(dest)
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
        self.assertIn(CANARY_MEMORY, conn.execute("SELECT content FROM memory").fetchone()[0])  # full copy
        self.assertFalse(Path(str(dest) + ".partial").exists())

    def test_captures_uncheckpointed_wal_content(self):
        conn = sqlite3.connect(self.src)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("INSERT INTO memory VALUES ('m2','u1','context',NULL,'CANARY-WAL-ROW',NULL,2,2)")
        conn.commit()  # connection stays open: the row lives in the -wal file
        self.addCleanup(conn.close)
        dest = self.out / "wal.db"
        self.assertEqual(self.backup(dest)[0], 0)
        copy = sqlite3.connect(dest)
        self.addCleanup(copy.close)
        self.assertEqual(copy.execute("SELECT COUNT(*) FROM memory WHERE id='m2'").fetchone()[0], 1)

    def test_requires_explicit_private_confirmation(self):
        code, out, err = self.backup(self.out / "b.db", confirm=False)
        self.assertEqual(code, 2)
        self.assertFalse((self.out / "b.db").exists())
        self.assertNotIn("created", out)

    def test_refuses_overwrite(self):
        dest = self.out / "exists.db"
        dest.write_bytes(b"precious")
        code, out, err = self.backup(dest)
        self.assertEqual(code, 1)
        self.assertEqual(dest.read_bytes(), b"precious")
        self.assertNotIn("Backup created", out)

    def test_refuses_destination_inside_repository(self):
        inside = bk.REPO_ROOT / "should-never-exist.db"
        code, out, err = self.backup(inside)
        self.assertEqual(code, 1)
        self.assertFalse(inside.exists())
        self.assertIn("outside this repository", err)

    def test_refuses_destination_inside_any_git_worktree(self):
        work = self.dir / "other-repo"
        (work / ".git").mkdir(parents=True)
        code, _, err = self.backup(work / "b.db")
        self.assertEqual(code, 1)
        self.assertIn("git working tree", err)

    def test_refuses_source_as_destination_relative_and_missing_parent(self):
        self.assertEqual(self.backup(self.src)[0], 1)
        self.assertEqual(run_cli("--source", str(self.src), "--dest", "rel.db", "--confirm-private-destination")[0], 1)
        self.assertEqual(self.backup(self.dir / "no-such-dir" / "b.db")[0], 1)

    def test_fail_closed_on_unknown_schema_and_revision(self):
        other = self.dir / "other.db"
        conn = sqlite3.connect(other)
        conn.execute("CREATE TABLE x (a)")
        conn.commit()
        conn.close()
        dest = self.out / "x.db"
        code, out, err = run_cli("--source", str(other), "--dest", str(dest), "--confirm-private-destination")
        self.assertEqual(code, 1)
        self.assertFalse(dest.exists())
        self.assertNotIn("Backup created", out)

        wrong = build_synthetic_db(self.dir / "wrong.db", revision="deadbeef0000")
        code, out, err = run_cli("--source", str(wrong), "--dest", str(dest), "--confirm-private-destination")
        self.assertEqual(code, 1)
        self.assertIn("unsupported migration revision", err)
        self.assertFalse(dest.exists())

        norev = build_synthetic_db(self.dir / "norev.db", revision=None)
        self.assertEqual(
            run_cli("--source", str(norev), "--dest", str(dest), "--confirm-private-destination")[0], 1
        )
        self.assertFalse(dest.exists())

    def test_failed_copy_leaves_nothing_and_reports_failure(self):
        junk = self.dir / "junk.db"
        junk.write_bytes(b"not a database" * 100)
        dest = self.out / "j.db"
        code, out, err = run_cli("--source", str(junk), "--dest", str(dest), "--confirm-private-destination")
        self.assertEqual(code, 1)
        self.assertFalse(dest.exists())
        self.assertFalse(Path(str(dest) + ".partial").exists())
        self.assertNotIn("Backup created", out)

    def test_verification_failure_removes_partial(self):
        original = bk.verify_schema

        def fail_on_copy(conn, label):
            if label == "copy":
                raise bk.BackupError("simulated verification failure")
            return original(conn, label)

        bk.verify_schema = fail_on_copy
        self.addCleanup(setattr, bk, "verify_schema", original)
        dest = self.out / "v.db"
        code, out, err = self.backup(dest)
        self.assertEqual(code, 1)
        self.assertFalse(dest.exists())
        self.assertFalse(Path(str(dest) + ".partial").exists())
        self.assertNotIn("Backup created", out)

    def test_missing_source_fails(self):
        code, _, _ = run_cli(
            "--source", str(self.dir / "none.db"), "--dest", str(self.out / "n.db"), "--confirm-private-destination"
        )
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
