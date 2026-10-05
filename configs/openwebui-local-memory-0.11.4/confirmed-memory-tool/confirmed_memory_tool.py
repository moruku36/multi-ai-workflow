"""
title: Confirmed Memory Save
author: local draft (not installed)
version: 0.2.0-draft
required_open_webui_version: 0.11.4
description: Saves one memory only after the user clicks Confirm in an Open WebUI dialog.

Private review draft. Pinned to Open WebUI 0.11.4. Not installed anywhere.
"""

from __future__ import annotations

import hashlib
import re
import threading
import time
import unicodedata
from typing import Any, Awaitable, Callable, Optional

PINNED_OPEN_WEBUI_VERSION = "0.11.4"
MAX_MEMORY_CHARS = 300
UNCERTAIN_OUTCOME_MESSAGE = (
    "Save outcome is uncertain. "
    "Check Open WebUI Memory settings before retrying."
)
DUPLICATE_COOLDOWN_SECONDS = 600.0
DUPLICATE_MESSAGE = (
    "Not saved by this call: the same memory was already attempted recently. "
    "Check Open WebUI Memory settings before retrying."
)

# Process-local dedupe state only. Keys are (user id, SHA-256 of normalized text);
# no plaintext is kept. Lost on restart and not shared across worker processes.
_state_lock = threading.Lock()
_inflight: set = set()
_attempted: dict = {}
_clock: Callable[[], float] = time.monotonic

# (request, user_dict, memory_text) -> the memory object returned by the standard route.
MemoryWriter = Callable[[Any, dict, str], Awaitable[Any]]
EventCall = Callable[[dict], Awaitable[Any]]


def validate_candidate(candidate: Any) -> tuple[Optional[str], str]:
    """Return (clean_text, error). Exactly one of them is empty."""
    if not isinstance(candidate, str):
        return None, "Memory text must be a string."
    text = candidate.strip()
    if not text:
        return None, "Memory text is empty."
    if len(text) > MAX_MEMORY_CHARS:
        return None, f"Memory text exceeds {MAX_MEMORY_CHARS} characters."
    if "\n" in text or "\r" in text:
        return None, "Only one single-line memory can be proposed at a time."
    return text, ""


def _user_id(user: Any) -> Optional[str]:
    if not isinstance(user, dict):
        return None
    uid = user.get("id")
    if isinstance(uid, str) and uid.strip():
        return uid
    return None


def _fingerprint(user_id: str, text: str) -> tuple[str, str]:
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip().casefold()
    return user_id, hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _reserve(key: tuple[str, str]) -> bool:
    """Reserve key unless it is in flight or was attempted within the cooldown."""
    with _state_lock:
        now = _clock()
        for k in [k for k, t in _attempted.items() if now - t >= DUPLICATE_COOLDOWN_SECONDS]:
            del _attempted[k]
        if key in _inflight or key in _attempted:
            return False
        _inflight.add(key)
        return True


def _mark_attempted(key: tuple[str, str]) -> None:
    with _state_lock:
        _attempted[key] = _clock()


def _release(key: tuple[str, str]) -> None:
    with _state_lock:
        _inflight.discard(key)


def _reset_dedupe_state_for_tests() -> None:
    with _state_lock:
        _inflight.clear()
        _attempted.clear()


def _confirmation_event(text: str) -> dict:
    return {
        "type": "confirmation",
        "data": {
            "title": "Save this memory?",
            "message": text,
        },
    }


def _memory_id(memory: Any) -> Any:
    if isinstance(memory, dict):
        return memory.get("id")
    return getattr(memory, "id", None)


async def propose_and_save(
    candidate: Any,
    *,
    request: Any,
    user: Any,
    event_call: Optional[EventCall],
    writer: MemoryWriter,
) -> str:
    """Show the confirmation dialog, and write only if it returns literal True."""
    text, error = validate_candidate(candidate)
    if text is None:
        return f"Not saved. {error}"
    uid = _user_id(user)
    if request is None or uid is None:
        return "Not saved. No authenticated user session is available."
    if event_call is None:
        return "Not saved. Confirmation dialog is unavailable."

    # Reserve before the dialog so a duplicate opens no second modal.
    key = _fingerprint(uid, text)
    if not _reserve(key):
        return DUPLICATE_MESSAGE
    try:
        try:
            answer = await event_call(_confirmation_event(text))
        except Exception:
            return "Not saved. Confirmation could not be completed."
        # Only the dialog's literal boolean True is consent. Everything else is no-write.
        if answer is not True:
            return "Not saved. The user did not confirm."

        # Mark BEFORE invoking the writer so any failure, cancellation or partial commit
        # blocks automatic retry for the cooldown. No compensating delete, no retry.
        _mark_attempted(key)
        # The 0.11.4 add route is non-atomic: it can commit the SQL row before
        # embedding/vector/event steps, so any failure or empty result is an uncertain
        # outcome. Never claim "Not saved" or "Saved" for those.
        try:
            memory = await writer(request, user, text)
        except Exception:
            return UNCERTAIN_OUTCOME_MESSAGE
        if memory is None or not _memory_id(memory):
            return UNCERTAIN_OUTCOME_MESSAGE
        return "Saved 1 memory after user confirmation."
    finally:
        _release(key)


async def open_webui_memory_writer(request: Any, user: dict, text: str) -> Any:
    """Call the standard 0.11.4 add route so the installed embedding path is used."""
    # Imported lazily: only resolvable inside a running Open WebUI process.
    from open_webui.models.users import UserModel
    from open_webui.routers.memories import AddMemoryForm, add_memory

    user_model = UserModel(**user)
    return await add_memory(request, AddMemoryForm(content=text), user_model)


class Tools:
    def __init__(self, writer: Optional[MemoryWriter] = None) -> None:
        self._writer: MemoryWriter = writer or open_webui_memory_writer

    async def save_confirmed_memory(
        self,
        memory_text: str,
        __request__: Any = None,
        __user__: Optional[dict] = None,
        __event_call__: Optional[EventCall] = None,
    ) -> str:
        """
        Propose ONE short, single-line memory about the user. The user sees a
        confirmation dialog with the exact text and nothing is saved unless they
        click Confirm. Saying "yes" in chat does not count.

        :param memory_text: One concise fact to remember (max 300 characters).
        """
        return await propose_and_save(
            memory_text,
            request=__request__,
            user=__user__,
            event_call=__event_call__,
            writer=self._writer,
        )
