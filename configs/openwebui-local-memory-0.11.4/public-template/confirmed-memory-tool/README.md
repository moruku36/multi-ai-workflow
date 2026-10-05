# Confirmed Memory Save tool

This tool writes a candidate memory only after an explicit approval dialog returns the literal boolean `True`. It validates bounded, nonempty input, uses the application's per-user Memory writer, and prevents immediate duplicate attempts within the current worker process.

Before use, replace `YOUR_LOCAL_OLLAMA_MODEL_ID` in the JSON tool source with the intended local model ID. Review the code against the exact Open WebUI release. Import the single tool record from `confirmed_memory_tool.import.json` through **Workspace > Tools > Import JSON**; then attach it only to the intended local model in **Workspace > Models**.

The dialog is the authorization gate. Consent phrases in the candidate text do not count. Update and delete are not exposed by this tool. Synthetic tests use mocks only.
