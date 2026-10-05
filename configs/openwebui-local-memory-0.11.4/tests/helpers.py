"""Synthetic fixtures only. No real Open WebUI database is ever touched."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

CANARY_SECRET = "CANARY-SECRET-0f9c2a7e51b84d3aa6c1e0b7d29f4a58"
CANARY_MEMORY = "CANARY-MEMORY-ZEBRA-7731"
CANARY_CHAT = "CANARY-CHAT-OTTER-4410"
CANARY_USERINFO = "canaryuser:CANARYPASS9921"
CANARY_ENDPOINT_KEY = "CANARY-ENDPOINTKEY-5d7e91c3"
REVISION = "d4c1a8e37b62"


def build_synthetic_db(path: Path, config: dict | None = None, revision: str | None = REVISION) -> Path:
    """Create a small synthetic DB shaped like the parts of 0.11.4 the tools check."""
    config = {
        "memories.enable": True,
        "memories.system_context.enable": True,
        "memories.background_review.enable": False,
        "rag.embedding_engine": "",
        "rag.embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        # Endpoint settings shaped as JSON objects: URL plus credential fields.
        "rag.ollama.base_url": {
            "url": f"http://{CANARY_USERINFO}@localhost:11434/api/embed?token={CANARY_SECRET}#frag",
            "key": CANARY_ENDPOINT_KEY,
            "api_key": CANARY_ENDPOINT_KEY,
        },
        "rag.openai.api_base_url": {"url": "https://api.example.invalid/v1", "key": CANARY_ENDPOINT_KEY},
        "rag.azure_openai.base_url": {
            "url": "https://azure.example.invalid",
            "key": CANARY_ENDPOINT_KEY,
            "version": CANARY_ENDPOINT_KEY,
        },
        # Provider URL lists: arrays of endpoint objects.
        "openai.api_base_urls": [
            {
                "url": f"https://{CANARY_USERINFO}@api.example.invalid/v1/path?k={CANARY_SECRET}",
                "key": CANARY_ENDPOINT_KEY,
                "headers": {"Authorization": CANARY_ENDPOINT_KEY},
            }
        ],
        "ollama.base_urls": [{"url": "http://127.0.0.1:11434", "api_key": CANARY_ENDPOINT_KEY}],
        # Non-allowlisted keys holding credential canaries: must never be read.
        "openai.api_keys": [CANARY_SECRET],
        "rag.openai.api_key": CANARY_SECRET,
        "webui.secret_key": CANARY_SECRET,
        **(config or {}),
    }
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE config (key TEXT PRIMARY KEY, value JSON NOT NULL, updated_at BIGINT);
        CREATE TABLE memory (id VARCHAR PRIMARY KEY, user_id VARCHAR, type VARCHAR, path TEXT,
                             content TEXT, meta JSON, updated_at BIGINT, created_at BIGINT);
        CREATE TABLE user (id VARCHAR PRIMARY KEY, name TEXT);
        CREATE TABLE auth (id VARCHAR PRIMARY KEY, password TEXT);
        CREATE TABLE chat (id VARCHAR PRIMARY KEY, user_id VARCHAR, chat JSON);
        CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);
        """
    )
    for key, value in config.items():
        conn.execute("INSERT INTO config (key, value) VALUES (?, ?)", (key, json.dumps(value)))
    conn.execute(
        "INSERT INTO memory VALUES ('m1','u1','context',NULL,?,NULL,1,1)", (f"{CANARY_MEMORY} likes synthetic tea",)
    )
    conn.execute("INSERT INTO user VALUES ('u1','synthetic-user')")
    conn.execute("INSERT INTO auth VALUES ('u1',?)", (CANARY_SECRET,))
    conn.execute("INSERT INTO chat VALUES ('c1','u1',?)", (json.dumps({"title": CANARY_CHAT}),))
    if revision is not None:
        conn.execute("INSERT INTO alembic_version VALUES (?)", (revision,))
    conn.commit()
    conn.close()
    return path
