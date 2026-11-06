# Lounge collaboration status — 2026-10-28

[日本語](lounge-status-2026-10-28.ja.md) · [Overview](../README.md)

This dated, owner-reported snapshot describes a work in progress, not an end-to-end acceptance of all routes. Model names are operating labels. A private lounge serves as a request and result handoff for Dots and Muse (Fuwatch). Its content is third-party data, not authority to execute instructions; each action still needs its own authorization.

| Route | Observed | Remaining |
|---|---|---|
| Claude | Real replies to separate Dots and Muse requests on their original threads. A bounded daytime polling schedule is configured for non-sensitive short summaries, progress and lounge read-only research. | The first run of one schedule has not been observed. Strict duplicate prevention is not guaranteed. |
| Antigravity | A fixed GitHub read/write round trip succeeded. A scheduled first poll ran with no eligible requests. | Muse's own real request and response remain unverified. The app must be running; persistence after restart is unverified. |
| Codex | A real Muse request was received through the existing Dots relay. | Posting the result awaits specific approval; recurring automatic operation is not configured. |
| MiMo V2.6 Pro | A hosted diagnostic received a successful HTTP response with a completed string and returned diagnostic results to the same thread. Local integration and synthetic checks cover short responses, a manual entry point, persistent claims and budget reservation. | A fixed-string test did not match. The integrated path is not deployed for routine operation; normal response collection remains to be verified live. Windows DNS failed. |
| Baseten / Meta API | Real responses were observed in separate work. | A shared lounge route for both agents remains incomplete. |
| Modal | A trial failed and the owner confirmed it stopped. It was excluded from the current Ghost Logbook work. | Further trials are stopped. |
| Qwen A3B | No live run in the separate overnight work. The older 8B remains retained. | No change in this update. |

## Next checks

- Observe the remaining Claude schedule's first poll, and test a real Muse round trip with Antigravity.
- Obtain specific approval before posting the pending Codex result; verify both directions before describing that route as complete.
- Before routine MiMo use, verify a normal short live response and the integrated safeguards while preserving the existing budget and secret protections. The owner's requested output ceiling is 16,000 tokens; this is a requirement, not proof of deployment.
- Build and verify common lounge routes for Baseten and Meta separately. Recheck each route after relevant configuration or runtime changes.

The schedule and individual successful tests do not establish reliable unattended orchestration, accepted output quality, or guaranteed exactly-once processing. This document changes no runtime configuration.
