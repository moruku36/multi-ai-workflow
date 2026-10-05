"""Private, version-pinned allowlist for automatic Memory context reads.

Intended to be copied into Open WebUI 0.11.4 only as part of the accompanying
memory.py patch. This is not installed in the running service.
"""

from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlsplit

ALLOWED_MODEL_ID = "YOUR_LOCAL_OLLAMA_MODEL_ID"


def _is_loopback_url(value: Any) -> bool:
    """Accept only bare HTTP(S) loopback URLs; never DNS-resolve names."""
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    try:
        parts = urlsplit(value)
        host = parts.hostname
        _ = parts.port  # reject malformed ports
        if parts.scheme not in {"http", "https"} or not host:
            return False
        if parts.username or parts.password or parts.query or parts.fragment:
            return False
        if parts.path not in {"", "/"}:
            return False
        if host.lower() == "localhost" or host.lower().endswith(".localhost"):
            return True
        return ipaddress.ip_address(host).is_loopback
    except (TypeError, ValueError):
        return False


def is_allowed_memory_context_route(request: Any, model: Any, base_urls: Any) -> bool:
    """Return true only for the exact server model on a verified loopback Ollama route.

    Any missing app state, inconsistent provider map, config error, malformed
    index, or non-loopback URL fails closed. No Memory DB method is called here.
    """
    if not isinstance(model, dict) or model.get("id") != ALLOWED_MODEL_ID:
        return False
    app = getattr(request, "app", None)
    state = getattr(app, "state", None)
    models = getattr(state, "MODELS", None)
    ollama_models = getattr(state, "OLLAMA_MODELS", None)
    openai_models = getattr(state, "OPENAI_MODELS", None)
    if not all(isinstance(value, dict) for value in (models, ollama_models, openai_models)):
        return False
    if ALLOWED_MODEL_ID not in models or ALLOWED_MODEL_ID not in ollama_models:
        return False
    if ALLOWED_MODEL_ID in openai_models:
        return False
    route = ollama_models[ALLOWED_MODEL_ID]
    indices = route.get("urls") if isinstance(route, dict) else None
    if not isinstance(indices, list) or not indices:
        return False
    if not isinstance(base_urls, list):
        return False
    for index in indices:
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(base_urls):
            return False
        entry = base_urls[index]
        url = entry.get("url") if isinstance(entry, dict) else entry
        if not _is_loopback_url(url):
            return False
    return True
