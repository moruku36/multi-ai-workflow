# Memory context route guard

This version-pinned reference checks the active model and server-side provider route before the automatic Memory context path may read memory rows or query vectors. The allowlist is bound to `YOUR_LOCAL_OLLAMA_MODEL_ID` and loopback Ollama routes. Unknown, malformed, missing, or conflicting route state fails closed.

`memory.py.patch` adds the guard call before the first Memory read. It is a zero-context patch for the pinned Open WebUI 0.11.4 source and requires a patch tool that supports zero-context hunks. Verify the exact source version and review the resulting diff before applying it.

This check covers automatic system-context injection only. It does not configure built-in Memory tools, background review, auxiliary model routing, or effective environment overrides. The tests are synthetic and make no application, database, or network calls.
