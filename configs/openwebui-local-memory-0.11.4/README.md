# Open WebUI 0.11.4 local Memory runbook

[日本語版](README.ja.md)

Scope: **Open WebUI 0.11.4 only**, a local Ollama Qwen3 model, standard per-user **Memory**. This directory is separate from the legacy `configs/level1-ollama` files, which are unchanged. Nothing here changes a running service, installs anything, calls a network, or reads credentials.

Status labels used below: **source-read** (read in the installed 0.11.4 source, not run), **offline-mock** (passes in the synthetic mock only; proves nothing about the live app), **live-gate** (unverified; needs a scheduled human check).

## 1. Three different things

| | What it is | Writes memory? | Status |
|---|---|---|---|
| (a) Standard Memory | Per-user rows in the `memory` table plus a per-user vector collection. Managed in Settings, API `/api/v1/memories`. Gated by `memories.enable`, the user permission `features.memories`, the model capability `memory`, and the per-chat Memory toggle. Retrieved memories are injected into the prompt (`memories.system_context.enable`). | Only when the user adds/edits/deletes in Settings | source-read |
| (b) Builtin memory tools | Model Builtin Tools > **Memory** (`builtinTools.memory`). Exposes `add_memory`, `update_memory`, `replace_memory_content`, `delete_memory` plus read tools to the model. **Default is ON.** The tools call the same router functions directly. | **Yes, model-initiated** | source-read |
| (b2) Background review | `memories.background_review.enable` (default off). After every N user turns the server asks a model for add/replace/remove operations and applies them. | **Yes, automatic** | source-read |
| (c) Chat-history search | Builtin Tools > **Chats** (`search_chats`, `view_chat`). Reads the user's own earlier chats. It is not Memory and saves nothing. | No | source-read |

### Save approval: not proven, so not used

- Nothing in the memory write paths asks the user to confirm. `add_memory` and friends write immediately; `update_memory` applies a batch immediately.
- `chat.tool_permissions.enable` plus `params.tool_approval_mode = ask` pauses tool calls for approval, but the mode comes from the client request, can be `full`, is skipped for automations/channels, and does not apply to background review. It is **not** a save-approval guarantee and this runbook does not rely on it.
- A prompt or system-prompt rule ("ask before saving") is not enforcement either. Quoted or injected text in a chat can ask the model to call a tool; only not exposing the tool prevents that.

**Decision:** the builtin **Memory** tool stays **OFF for every model** (local and external alike, so no model can initiate a memory write) and background review stays **OFF**. **Conversational "remember this" is NOT implemented and NOT guaranteed.** A user saying "remember X" in chat does not save X. The only supported write path is manual CRUD in Settings.

## 2. Required configuration (set by hand; see `reference-settings.reference.json`, which is non-importable)

- `memories.enable` = true.
- `memories.background_review.enable` = false.
- The inspector reads **persisted `config` rows**, which are not the same as the **effective runtime settings**: environment variables can override a persisted row, and a key with no row falls back to a code default (or an environment value) that the inspector cannot see. Treat every inspector result as "persisted rows only" until confirmed live.
- Embedding: keep the built-in sentence-transformers **MiniLM** (`rag.embedding_engine` empty, `rag.embedding_model` = `sentence-transformers/all-MiniLM-L6-v2`). Do not change the embedding model. In-process MiniLM means **no configured embedding endpoint is called**; it does **not** mean total network silence. Model download/load or Hub traffic is not excluded by anything here. An Ollama URL also being present does not matter while the engine is empty. Whether MiniLM is already downloaded and whether any outbound call happens at runtime is a **live egress gate** (section 9, step 8).
- **Every** model, local or external (Admin > Models): **Builtin Tools > Memory OFF**. The default is ON, and ON lets the model write memories on its own.
- Local memory model only (the dedicated Qwen3 entry): **Capabilities > Memory ON**.
- Every non-local model (OpenAI-compatible, RunPod): **Capabilities > Memory OFF**. Memory text is placed in the prompt sent to whatever model the chat uses, so a memory-enabled chat on an external model would send memories to that model's endpoint.
- Nothing in this repo reads or sets credentials, and nothing auto-shares memory with OpenAI or RunPod. An OpenAI base URL being configured is not use.

Verify the config-table part with the inspector (section 6). Per-model settings live in model records, which the inspector never reads; check them in the UI.

## 3. Manual Memory CRUD (the only supported write path)

UI labels were found in the 0.11.4 frontend bundle (`Personalization`, `Memory`, `Manage`, `Add Memory`, `Edit Memory`, `Clear memory`, and the toasts "Memory added/updated/deleted successfully"). The exact Settings placement of every control is a **live-gate** until a human confirms it in the running app. The API semantics below are **source-read**; the UI controls that call them are not verified.

1. **List / read:** user menu > Settings > Personalization > Memory > **Manage**. Each of your memories is listed with its text. (API: `GET /api/v1/memories/`.)
2. **Add:** **Add Memory**, type one short fact, save. (API: `POST /api/v1/memories/add`.) A manual add stores a row, then embeds it. If embedding fails the request errors but the row may already exist without a vector, so it will not be retrieved. Remove it or reindex.
3. **Edit / correct:** open the entry (**Edit Memory**), change the text, save. The vector is rebuilt. (API: `POST /api/v1/memories/{id}/update`.)
4. **Delete one:** the API call `DELETE /api/v1/memories/{id}` is source-read and scoped to your user. Whether the Settings UI actually offers a **per-entry** delete action is a separate **live-gate**: do not assume it exists. If you cannot find one on first use, stop and record that; do not fall back to **Clear memory**, which removes every memory of your account (`DELETE /api/v1/memories/delete/user`).
5. **New-conversation retrieval check:** start a new chat on the local model with Memory enabled for the chat, ask something that relates to the fact, and see whether the reply uses it. Then delete the entry and ask again in another new chat.

Notes: a memory added through the API without a type is stored as `context`, which is retrieved by vector similarity; with `rag.relevance_threshold` at 0 the nearest items are returned even when unrelated. Memories of type `user` are always injected. Keep entries short and non-secret; never store credentials or other people's private data.

## 4. Local-only use

- Use a dedicated conversation (or a dedicated model entry) on the local Ollama Qwen3 model for memory-enabled chats. Turn the per-chat Memory toggle off for chats on any other model.
- Memory is per user account. Another account never receives your memories (offline-mock; the routes filter by `user.id` in the source).
- Auxiliary tasks (titles, tags, search queries) are routed by `task.model.default` / `task.model.external` and by the chat model's connection type. Which model they actually use, and therefore whether any chat or memory text reaches a non-local endpoint, is a **live-gate**.

## 5. Memory vs chat-history search

Memory is a short, curated list that you maintain and that is injected (by similarity) into prompts. Chat-history search (`search_chats` / `view_chat`) pulls text from your earlier conversations on demand and is only available if the model's Chats builtin tool is on. Neither makes the other work; deleting a memory does not delete chat history and vice versa. If you do not want a model to read old chats, turn the Chats builtin tool off for that model.

## 6. Tools

All tools are local, standard-library Python, and use only temporary synthetic data in tests.

### `inspect_config.py` (allowlist inspector)

```
python inspect_config.py --db <path-to-webui.db> [--json]
```

- Opens the file `mode=ro` with `query_only` and an SQLite authorizer that only permits `config.key`/`config.value`. Memory, chat, user and auth tables cannot be read even by altered SQL.
- Selects only the allowlisted keys in the source file; API keys, secrets and `*.api_configs` are never requested.
- Endpoint settings (`rag.ollama.base_url`, `rag.openai.api_base_url`, `rag.azure_openai.base_url`, and the provider lists `ollama.base_urls` / `openai.api_base_urls`) may be stored as JSON objects that also hold credential fields, and the lists may be arrays of such objects. The inspector projects them **inside SQLite with JSON1**, so only the nested `url` string (one per list element) is returned to Python; the object itself is never selected. If JSON1 is missing or the shape is not a URL string / object with a `url` string, it fails closed (value `<redacted>`, exit 3, or exit 2 without JSON1) and never falls back to selecting the raw value. Provider connections are inspected as URLs only, never their credentials or per-connection config. Scalar URL strings are accepted too (that is what the 0.11.4 source writes for these keys).
- Reports persisted rows, not effective runtime settings (see section 2); a key without a row is shown with its code default and "env override unknown".
- Never prints a raw value: wrong types, odd formats, and secret-looking strings print as `<redacted>`; endpoints are reduced to scheme/host/port (userinfo, path, query and fragment are dropped) with a lexical `loopback`/`local-host-alias`/`private-network`/`non-local-or-unknown` label (names are not resolved; no network).
- Strict local-only policy for an Ollama embedding engine: **loopback** is WARN (acceptable, confirm the listener live); a container **host alias** such as `host.docker.internal` is WARN marked **UNVERIFIED** (not asserted to be loopback; needs live host verification); a **private-network** address (RFC1918/link-local) is a **FAIL** because it is not provably this machine; anything else is FAIL.
- Exit 0 = no policy failure, 1 = policy failure (e.g. background review on, non-local embedding), 2 = could not trust the file (missing, unreadable, unknown schema), 3 = a value could not be interpreted. Nothing prints a success line unless exit is 0.
- Run it against a **copy** of the database, or while the service is stopped, if you want zero contention. It is read-only either way.

### `backup_db.py` (consistent backup; never restores)

```
python backup_db.py --source <webui.db> --dest <NEW absolute path outside the repo> --confirm-private-destination
```

- Uses SQLite's online backup API from a read-only source, so the copy is a consistent snapshot, including content still in the write-ahead log.
- Refuses: an existing destination (no overwrite), a destination inside this repo or any git working tree, a relative path, the source itself, an unknown schema or a migration revision other than 0.11.4's (`d4c1a8e37b62`).
- Verifies the copy (`integrity_check`, schema) before moving it into place; on any failure the partial file is removed, an error is printed, and the exit code is non-zero. Success prints the size and SHA-256.
- The backup contains **everything**: memories, chats, users, password hashes. Store it privately. It does not include the vector store directory.

## 7. Manual restore / rollback (human only, service stopped)

There is no restore tool by design.

1. Stop Open WebUI completely (confirm the process has exited). Do not restore while it runs.
2. Make a safety copy of the current database file **and** its `-wal`/`-shm` siblings, and of the vector store directory (`vector_db`, with the default Chroma store), into a private directory outside the repo. Optionally use `backup_db.py` first.
3. Check the backup you intend to restore: compare its SHA-256 with the value printed at backup time.
4. Replace the database file with the backup. Delete any stale `-wal`/`-shm` files next to the target.
5. Restore the matching vector store copy if you have one from the same moment. If you do not, the stored vectors may disagree with the restored rows; rebuild them with the Memory reset/reindex endpoints (`POST /api/v1/memories/reset` for your user, admin `POST /api/v1/memories/reindex`). Whether the UI exposes those is a **live-gate**. Reindexing uses the configured embedding (MiniLM).
6. Start Open WebUI, sign in, and run the live acceptance steps below. If anything is wrong, stop again and put the safety copy from step 2 back the same way.

## 8. Offline acceptance (synthetic; mock only)

```
python -m unittest discover -s tests -v
```

Run from this directory. It needs only the Python standard library and uses temporary databases with canary strings. The memory scenarios run against `tests/memory_mock.py`, a **mock of the documented semantics, not Open WebUI**: add then retrieve in a fresh chat-equivalent request; correct; delete individually; ordinary chat is not saved; denied/failed/empty writes report failure; per-user isolation; quoted or injected text cannot create a write (the write tools are not exposed); persistence across a simulated restart; no canary reaches an external embedding/task endpoint or a socket (with a control showing the detector works). Tool tests cover the read-only connection, redaction, fail-closed schema handling, backup refusals and cleanup. Passing proves these tools and this policy are self-consistent, nothing more.

## 9. Live acceptance (later, human-scheduled; do not run now)

Requires approval and a scheduled window. Use a throwaway test account and synthetic facts only.

1. With the service stopped, make a private backup (section 6), then start it.
2. In the admin UI confirm: Memory on; **every** model (local and external) has Builtin Tools > Memory off; only the dedicated local model has Capabilities > Memory on and external models have it off; background review off. Also confirm the effective embedding engine/model and endpoint (environment overrides are invisible to the inspector).
3. Run `inspect_config.py` against a copy; expect exit 0.
4. In Settings, add a synthetic fact, list it, edit it; **locate the per-entry delete control (live-gate; if there is none, stop and record it)** and delete the entry individually; start a new chat on the local model and confirm the fact is used before deletion and not after.
5. Say "remember my code word is X" in chat; confirm nothing is saved and nothing in the Memory list changes.
6. Add a fact in a second test account; confirm the first account never sees it.
7. Restart the service; confirm a remaining memory still retrieves.
8. Live egress gate: while exercising 4 and 7 (and during a cold start), watch outbound connections from the process (operating-system tools) and confirm none to OpenAI, RunPod, or any non-local address. In-process MiniLM does not call a configured embedding endpoint, but model download/load or Hub traffic is not ruled out by this runbook: confirm whether the first MiniLM load/update check needs the network, and record it either way.
9. Check which model serves titles/tags (task model settings) and that it is local.

## 10. Unverified / live-only

- Exact UI layout and labels; whether a **per-entry** delete control and Reset/reindex exist in the UI (the delete API is source-read; the UI control is not).
- Whether each live model's Builtin Tools > Memory is currently on (default is on) and can be turned off per model.
- Whether a private-network or host-alias embedding URL (if one is ever configured) really points at this machine.
- Whether MiniLM is present locally and whether any outbound call occurs at load.
- Which model handles auxiliary tasks and whether it is local.
- Effective values when environment variables override persisted config.
- Real retrieval quality and threshold behaviour with Qwen3 and MiniLM.
- Backup/restore on the live database, including WAL handling and vector-store consistency.
