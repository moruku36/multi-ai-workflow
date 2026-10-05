"""Synthetic MOCK of the user-Memory semantics described in the runbook.

This is NOT Open WebUI and does not import it. It models, from reading the
0.11.4 source (routers/memories.py, utils/memory.py, utils/tools.py):
  * per-user rows keyed by user id, manual add/edit/delete only;
  * an embedding step on every write and on every query;
  * rows inserted BEFORE embedding (a failed embedding leaves an un-indexed row);
  * retrieval limited to the requesting user's vectors;
  * builtin memory write tools exposed only when ``builtinTools.memory`` is true
    (the real default is true; the runbook requires turning it off).
Passing these tests proves the intended policy/semantics are self-consistent,
not that the live application behaves this way. See the runbook's live gates.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import socket
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

WRITE_TOOLS = {"add_memory", "update_memory", "replace_memory_content", "delete_memory"}
READ_TOOLS = {"search_memories", "list_memory_paths", "read_memory_path", "list_memories"}


class NotExposed(Exception):
    """A tool that the model/config does not expose was invoked."""


class EgressAttempt(AssertionError):
    pass


@contextmanager
def egress_guard():
    """Fail loudly (and record) if anything tries to open a network connection."""
    attempts: list[str] = []
    real_connect, real_create, real_gai = socket.socket.connect, socket.create_connection, socket.getaddrinfo

    def blocked(*args, **kwargs):
        attempts.append("network")
        raise EgressAttempt("network access attempted during synthetic test")

    socket.socket.connect = blocked
    socket.create_connection = blocked
    socket.getaddrinfo = blocked
    try:
        yield attempts
    finally:
        socket.socket.connect, socket.create_connection, socket.getaddrinfo = real_connect, real_create, real_gai


class ExternalEndpoint:
    """Recorder standing in for an external embedding/task endpoint."""

    def __init__(self):
        self.payloads: list[str] = []

    def post(self, text: str) -> list[float]:
        self.payloads.append(text)
        return LocalEmbedder().embed(text)


class LocalEmbedder:
    """Deterministic in-process bag-of-words embedder (stands in for MiniLM)."""

    DIM = 64

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls = 0

    def embed(self, text: str) -> list[float]:
        self.calls += 1
        if self.fail:
            raise RuntimeError("embedding unavailable")
        vec = [0.0] * self.DIM
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            vec[int(hashlib.sha256(token.encode()).hexdigest(), 16) % self.DIM] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class MemoryService:
    def __init__(
        self,
        db_path: Path,
        *,
        embedder: LocalEmbedder | None = None,
        embedding_engine: str = "",
        external: ExternalEndpoint | None = None,
        permitted_users: set[str] | None = None,
        threshold: float = 0.2,
    ):
        self.db_path = Path(db_path)
        self.embedder = embedder or LocalEmbedder()
        self.embedding_engine = embedding_engine  # '' = built-in/local; 'external' = misconfigured
        self.external = external
        self.permitted_users = permitted_users
        self.threshold = threshold
        self.db = sqlite3.connect(self.db_path)
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS memory (id TEXT PRIMARY KEY, user_id TEXT, content TEXT,
                                               indexed INTEGER, created_at INTEGER, updated_at INTEGER);
            CREATE TABLE IF NOT EXISTS memory_vector (id TEXT PRIMARY KEY, user_id TEXT, vec TEXT);
            """
        )
        self.db.commit()

    def close(self):
        self.db.close()

    # -- embedding ---------------------------------------------------------
    def _embed(self, text: str) -> list[float]:
        if self.embedding_engine == "external":
            return self.external.post(text)
        return self.embedder.embed(text)

    # -- manual Settings-style CRUD (the only write path) -------------------
    def _check(self, user_id: str):
        if self.permitted_users is not None and user_id not in self.permitted_users:
            return {"ok": False, "error": "access prohibited"}
        return None

    def add(self, user_id: str, content: str) -> dict:
        denied = self._check(user_id)
        if denied:
            return denied
        content = (content or "").strip()
        if not content:
            return {"ok": False, "error": "memory content cannot be empty"}
        memory_id, now = str(uuid.uuid4()), int(time.time())
        self.db.execute("INSERT INTO memory VALUES (?,?,?,0,?,?)", (memory_id, user_id, content, now, now))
        self.db.commit()  # row first, as in the real router
        try:
            vec = self._embed(content)
        except Exception as exc:
            return {"ok": False, "id": memory_id, "error": f"embedding failed: {exc}", "indexed": False}
        self.db.execute("INSERT OR REPLACE INTO memory_vector VALUES (?,?,?)", (memory_id, user_id, json.dumps(vec)))
        self.db.execute("UPDATE memory SET indexed=1 WHERE id=?", (memory_id,))
        self.db.commit()
        return {"ok": True, "id": memory_id, "indexed": True}

    def update(self, user_id: str, memory_id: str, content: str) -> dict:
        denied = self._check(user_id)
        if denied:
            return denied
        row = self.db.execute("SELECT id FROM memory WHERE id=? AND user_id=?", (memory_id, user_id)).fetchone()
        if row is None:
            return {"ok": False, "error": "not found"}
        content = (content or "").strip()
        if not content:
            return {"ok": False, "error": "memory content cannot be empty"}
        self.db.execute("UPDATE memory SET content=?, updated_at=? WHERE id=?", (content, int(time.time()), memory_id))
        self.db.commit()
        try:
            vec = self._embed(content)
        except Exception as exc:
            return {"ok": False, "id": memory_id, "error": f"embedding failed: {exc}"}
        self.db.execute("INSERT OR REPLACE INTO memory_vector VALUES (?,?,?)", (memory_id, user_id, json.dumps(vec)))
        self.db.commit()
        return {"ok": True, "id": memory_id}

    def delete(self, user_id: str, memory_id: str) -> dict:
        denied = self._check(user_id)
        if denied:
            return denied
        cur = self.db.execute("DELETE FROM memory WHERE id=? AND user_id=?", (memory_id, user_id))
        self.db.commit()
        if cur.rowcount == 0:
            return {"ok": False, "error": "not found"}
        self.db.execute("DELETE FROM memory_vector WHERE id=? AND user_id=?", (memory_id, user_id))
        self.db.commit()
        return {"ok": True}

    def list(self, user_id: str) -> list[dict]:
        rows = self.db.execute("SELECT id, content FROM memory WHERE user_id=? ORDER BY created_at", (user_id,))
        return [{"id": r[0], "content": r[1]} for r in rows]

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM memory").fetchone()[0]

    # -- retrieval ---------------------------------------------------------
    def retrieve(self, user_id: str, query: str, k: int = 3) -> list[dict]:
        qvec = self._embed(query)
        rows = self.db.execute(
            "SELECT m.id, m.content, v.vec FROM memory m JOIN memory_vector v ON v.id=m.id "
            "WHERE m.user_id=? AND v.user_id=?",
            (user_id, user_id),
        ).fetchall()
        scored = sorted(((_cosine(qvec, json.loads(v)), i, c) for i, c, v in rows), reverse=True)
        return [{"id": i, "content": c, "score": s} for s, i, c in scored[:k] if s >= self.threshold]

    def build_chat_request(self, user_id: str, messages: list[dict]) -> dict:
        """A fresh request: nothing is carried over from any previous chat."""
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        hits = self.retrieve(user_id, last_user)
        system = []
        if hits:
            body = "\n".join(f"- {h['content']}" for h in hits)
            system = [{"role": "system", "content": f"<memory_context>\n{body}\n</memory_context>"}]
        return {"messages": system + list(messages), "memory_ids": [h["id"] for h in hits]}


class ChatSession:
    """Ordinary conversation. It never writes memory; it can only read."""

    def __init__(self, service: MemoryService, user_id: str, model_meta: dict | None = None):
        self.service, self.user_id = service, user_id
        # None -> the runbook's required configuration (builtin Memory tool off).
        # An explicit {} models a model with no overrides, i.e. the real default (on).
        self.model_meta = {"builtinTools": {"memory": False}} if model_meta is None else model_meta
        self.history: list[dict] = []

    def exposed_tools(self) -> set[str]:
        if self.model_meta.get("builtinTools", {}).get("memory", True):  # real default: True
            return READ_TOOLS | WRITE_TOOLS
        return set()

    def call_tool(self, name: str, **kwargs):
        if name not in self.exposed_tools():
            raise NotExposed(name)
        raise NotImplementedError("tool bodies are out of scope for the mock")

    def send(self, text: str) -> dict:
        self.history.append({"role": "user", "content": text})
        request = self.service.build_chat_request(self.user_id, self.history)
        reply = "(synthetic assistant reply)"
        if re.search(r"\b(remember|save|memorize)\b", text, re.IGNORECASE):
            reply += (
                " Not saved: conversational 'remember this' is not implemented. "
                "Add memories manually in Settings > Personalization > Memory."
            )
        self.history.append({"role": "assistant", "content": reply})
        return {"reply": reply, "request": request}
