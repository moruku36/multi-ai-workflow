#!/usr/bin/env python3
"""SQLite-consistent backup of an Open WebUI 0.11.4 database. Never restores.

  * The source is opened ``mode=ro`` and copied with SQLite's online backup API,
    so the copy is a consistent snapshot even if Open WebUI is running (stopping
    it first is still the safest practice).
  * The destination must be given explicitly, must not exist, must be outside
    this repository and outside any git working tree, and is never the source.
  * The copy contains EVERYTHING in the database (memories, chats, users,
    hashed credentials). Treat it as private data: it requires
    ``--confirm-private-destination``.
  * Fails closed: unknown schema/migration revision, failed copy or failed
    verification removes the partial file, prints an error, exits non-zero and
    never prints a success line.
  * No restore, no overwrite, no network. Restore is a documented manual step.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

SUPPORTED_REVISION = "d4c1a8e37b62"  # alembic head of Open WebUI 0.11.4
REQUIRED_TABLES = {"alembic_version", "config", "memory", "user", "chat"}
REQUIRED_COLUMNS = {
    "config": {"key", "value"},
    "memory": {"id", "user_id", "content", "type", "path", "created_at", "updated_at"},
}
REPO_ROOT = Path(__file__).resolve().parents[2]

EXIT_OK, EXIT_FAILED, EXIT_USAGE = 0, 1, 2


class BackupError(Exception):
    pass


def _authorizer(action, arg1, arg2, dbname, source):
    # Schema/metadata and the alembic revision only; no row content is read here.
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ and arg1 == "sqlite_master":
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ and arg1 == "alembic_version" and arg2 == "version_num":
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and arg1 in {"table_info", "query_only"}:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def verify_schema(conn: sqlite3.Connection, label: str) -> None:
    """Fail closed unless the database matches the supported 0.11.4 layout."""
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = REQUIRED_TABLES - tables
        if missing:
            raise BackupError(f"{label}: unknown schema (missing required tables: {', '.join(sorted(missing))})")
        for table, needed in REQUIRED_COLUMNS.items():
            have = {r[1] for r in conn.execute(f"PRAGMA table_info('{table}')")}
            if not needed <= have:
                raise BackupError(f"{label}: unknown schema ({table} table lacks expected columns)")
        revisions = [r[0] for r in conn.execute("SELECT version_num FROM alembic_version")]
    except sqlite3.Error as exc:
        raise BackupError(f"{label}: cannot verify schema ({type(exc).__name__})") from None
    if revisions != [SUPPORTED_REVISION]:
        raise BackupError(f"{label}: unsupported migration revision (this tool supports Open WebUI 0.11.4 only)")


def _readonly_conn(path: Path) -> sqlite3.Connection:
    uri = "file:" + quote(path.resolve().as_posix(), safe="/:") + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=10)
        conn.execute("PRAGMA query_only=ON")
        conn.set_authorizer(_authorizer)
        return conn
    except sqlite3.Error as exc:
        raise BackupError(f"cannot open source read-only ({type(exc).__name__})") from None


def _inside_git_worktree(path: Path) -> bool:
    return any((p / ".git").exists() for p in [path, *path.parents])


def validate_destination(source: Path, dest: Path) -> Path:
    if not dest.is_absolute():
        raise BackupError("destination must be an absolute path chosen explicitly")
    dest = dest.resolve()
    if dest.exists() or Path(str(dest) + ".partial").exists():
        raise BackupError("destination already exists; refusing to overwrite")
    if not dest.parent.is_dir():
        raise BackupError("destination directory does not exist")
    if dest == source.resolve():
        raise BackupError("destination is the source database")
    for root in (REPO_ROOT.resolve(),):
        if dest == root or root in dest.parents:
            raise BackupError("destination must be outside this repository")
    if _inside_git_worktree(dest.parent):
        raise BackupError("destination must be outside any git working tree")
    return dest


def backup(source: Path, dest: Path) -> tuple[str, int]:
    """Copy ``source`` to ``dest``; returns (sha256, size). Raises BackupError."""
    if not source.is_file():
        raise BackupError("source database not found")
    dest = validate_destination(source, dest)
    partial = Path(str(dest) + ".partial")
    src = _readonly_conn(source)
    dst = None
    try:
        verify_schema(src, "source")
        try:
            dst = sqlite3.connect(str(partial))
            src.backup(dst)  # whole-database, consistent snapshot
            dst.commit()
        except sqlite3.Error as exc:
            raise BackupError(f"copy failed ({type(exc).__name__})") from None
        dst.close()
        dst = None
        check = sqlite3.connect("file:" + quote(partial.resolve().as_posix(), safe="/:") + "?mode=ro", uri=True)
        try:
            if check.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise BackupError("verification failed: integrity_check on the copy")
            check.set_authorizer(_authorizer)
            verify_schema(check, "copy")
        except sqlite3.Error as exc:
            raise BackupError(f"verification failed ({type(exc).__name__})") from None
        finally:
            check.close()
        try:
            os.chmod(partial, 0o600)
        except OSError:
            pass
        os.rename(partial, dest)  # fails if dest appeared meanwhile; never overwrites
    except BaseException:
        if dst is not None:
            dst.close()
        src.close()
        partial.unlink(missing_ok=True)
        raise
    src.close()
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    return digest, dest.stat().st_size


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", required=True, type=Path, help="Open WebUI SQLite file (opened read-only)")
    parser.add_argument("--dest", required=True, type=Path, help="NEW absolute file path outside the repository")
    parser.add_argument(
        "--confirm-private-destination",
        action="store_true",
        help="acknowledge the copy contains private memories/chats and the destination is private",
    )
    args = parser.parse_args(argv)
    if not args.confirm_private_destination:
        print("ERROR: pass --confirm-private-destination to acknowledge the backup holds private data.", file=sys.stderr)
        return EXIT_USAGE
    try:
        digest, size = backup(args.source, args.dest)
    except BackupError as exc:
        print(f"ERROR: backup NOT created: {exc}", file=sys.stderr)
        return EXIT_FAILED
    except Exception as exc:  # unexpected: still fail, never claim success
        print(f"ERROR: backup NOT created: unexpected {type(exc).__name__}", file=sys.stderr)
        return EXIT_FAILED
    print(f"Backup created and verified (integrity_check ok, schema matches 0.11.4). bytes={size} sha256={digest}")
    print("Vector store files are not part of this backup; see the runbook restore section.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
