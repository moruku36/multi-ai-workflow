# Confirmed Memory Tool (private draft, Open WebUI 0.11.4)

A minimal native Open WebUI custom Tool with one operation, `save_confirmed_memory`.
**Not installed. Installation instructions are intentionally withheld**; the feature stays uninstalled until the parent reviews it.

## Post-confirmation failures can have an uncertain outcome

The Open WebUI 0.11.4 standard `add_memory` route calls `Memories.insert_new_memory` (which commits
the SQL row) and only afterwards runs the embedding function, the vector upsert/reindex and the event
publish. If any later step raises, the row may already exist. This does not weaken the pre-confirmation
gate: the writer is never called unless the event callback returns literal `True`.

Once the writer has been invoked after literal `True` confirmation, an exception, a `None` result or a
result without an `id` is reported as "Save outcome is uncertain. Check Open WebUI Memory settings
before retrying." The same user and candidate are blocked from another attempt for 10 minutes. There
is no automatic retry or compensating delete. The user should check the Memory list in the UI before
trying again. This draft remains uninstalled until parent review.

## Compatibility

Pinned to **Open WebUI 0.11.4** only. It relies on the injected `__request__`, `__user__`
and `__event_call__`, and on `open_webui.routers.memories.add_memory(request, AddMemoryForm, user)`.
Re-verify against the source before using any other version.

## Behaviour

1. Accepts at most one candidate: a non-empty, single-line string of up to 300 characters.
2. Takes identity only from the injected `__user__` (must carry a string `id`). There is no
   `user_id` or consent parameter in the model-facing signature.
3. Always sends `{"type": "confirmation", "data": {"title", "message"}}` through `__event_call__`;
   `message` is the exact text that would be stored.
4. Writes only if the dialog result `is True` (the literal boolean). `False`, `None`, error dicts
   (timeout/disconnect), strings like `"yes"`, truthy values, exceptions, a missing callback,
   or a missing request/user/id all result in **no write** (these all happen before the writer is called).
5. Writes through the standard `add_memory` route (rebuilding a `UserModel` from the injected dict),
   so the installed embedding/vector path is used. No direct DB access, no external provider.
6. Reports success only if the route returns a memory with an `id`. After the writer is invoked,
   any exception or empty/id-less result is reported as an uncertain outcome (see warning above),
   never as "Not saved".

7. Duplicate guard (local process only): the key is the injected user id plus a SHA-256 of the
   normalized text (NFKC, whitespace-collapsed, case-folded); no plaintext is cached. A key is reserved
   before the dialog opens, so an in-flight duplicate shows no second dialog and never calls the writer.
   Cancel, timeout or dialog error before the writer runs releases the reservation. After literal `True`
   the key is marked attempted *before* the writer is invoked and blocks repeats for 10 minutes
   (`DUPLICATE_COOLDOWN_SECONDS`), even if the writer raised or partially committed. A duplicate gets
   "already attempted recently; check Open WebUI Memory settings before retrying". There is no
   compensating delete and no automatic writer retry. Other users are unaffected.

   **Scope limit:** this state is in-memory and per process. It does not survive restarts and is not
   shared across workers, so it is **not** cross-process or restart idempotency.

Text in the chat or in the candidate (e.g. "user approved") cannot count as consent; only the dialog can.

## Not implemented: update / delete

Assistant-triggered update and delete are deliberately **absent**: the exact 0.11.4 route signatures
and owner-scoped reads were not verified for this draft. Review, edit and delete memories yourself in
**Open WebUI → Settings → Personalization → Memory → Manage**, where every action is per item.

Do not enable built-in auto-memory writes alongside this tool.

## Backup / restore safety

Before any future install or memory change, follow the backup and restore guidance in the parent
directory (`../README.md`, `../backup_db.py`). This draft contains and uses no real memory contents.

## Tests

Synthetic only (fake dialog, request, user, writer; no app imports, DB, GPU or network):

```
python -m unittest discover -s configs/openwebui-local-memory-0.11.4/confirmed-memory-tool/tests -v
```
