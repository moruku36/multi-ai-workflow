# Open WebUI 0.11.4: Local Memory guard and confirmed save tool

This is a reusable reference for a single, pinned Open WebUI version. It contains server-side route checks for automatic Memory context and a confirmed-write tool. It has no live deployment status and includes only synthetic tests.

## Configure before use

1. Review the exact Open WebUI 0.11.4 source and apply `context-guard/memory.py.patch` only to the matching source file. It is a zero-context patch; use a patch tool that supports zero-context hunks and verify the resulting diff.
2. Replace `YOUR_LOCAL_OLLAMA_MODEL_ID` in both Python modules and the patch with the exact local model ID from your own instance. Review the local route and loopback assumptions before installation.
3. Keep the built-in Memory tools disabled for every model when all writes must pass through explicit confirmation. Attach **Confirmed Memory Save** only to the intended local model. Enable the Memory context capability only on local models allowed to receive that user's memories; keep it off for external models.
4. Make a private, consistent backup of the application database and vector store before changing a live instance. Preserve existing data and provider settings.
5. In **Workspace > Tools > Import JSON**, import `confirmed-memory-tool/confirmed_memory_tool.import.json`. Then use **Workspace > Models** to attach the tool to the intended local model only.
6. Run the synthetic tests before installation. Use synthetic facts for any later live acceptance and confirm the effective settings in the UI.

The route guard covers automatic context injection. Built-in Memory tools, background review, auxiliary model routing, and effective settings can be separate paths; inspect them for the exact release before relying on a local-only policy.

## Synthetic tests

```sh
python -m unittest discover -s configs/openwebui-local-memory-0.11.4/confirmed-memory-tool/tests -v
python -m unittest discover -s configs/openwebui-local-memory-0.11.4/public-template/context-guard/tests -v
```

The tests use mocks and synthetic data. They do not inspect a live database, load a model, or make network calls.
