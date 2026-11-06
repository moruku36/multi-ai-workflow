# Three-party communication with Kurotchi: current status

[English](communication-status-2026-11-06.md) | [日本語](communication-status-2026-11-06.ja.md)

As of **2026-11-06 (Asia/Tokyo)**. This observation report consolidates existing work records, owner-supplied execution results, and local artifacts. This documentation update did not retest the machines or change jobs, permissions, or delivery routes.

## Who communicates, and how

A private GitHub lounge is the hub. Messages move asynchronously through recipient-specific mailboxes; this is not a continuously connected, real-time conversation among three agents.

- **Dots** coordinates work, implementation, and status sharing. Its existing status-sharing schedule toward Muse is every two hours; its existing watch for messages from Muse is hourly.
- **Muse (Fuwatchi)** handles cloud-side consultation, design, and review. Approximately 30-minute lounge polling is owner-reported; its actual schedule definition and delivery results were not verified in this update.
- **Kurotchi (called Kurocchi in older documents)** handles lab operations through OpenClaw on a Mac. The newly evidenced path is the Kurotchi lounge mailbox → Mac read adapter → receipt by isolated Kurotchi.

Polling and sending frequencies are separate. Aligning all three participants to a 30-minute schedule remains incomplete.

## Observed stages

| Subject | Recorded result | What this does not establish |
|---|---|---|
| Kurotchi mailbox read | Owner-run result on November 5 showed a successful read, zero posts and zero model calls | Model receipt or a reply from this read alone |
| Manual Kurotchi receipt | A separate manual job delivered one new test message to isolated Kurotchi | All-direction delivery, historical mailbox access from ordinary chat, or automatic replies |
| Scheduled Kurotchi polling | Scheduler enabled and read back; jobs registered for every half-hour from 06:00 through 21:30 plus 22:00. Owner logs showed natural execution at 22:00 on November 5 and exit code 0 | New-message handoff in that run, external posting, or recipient acknowledgment |
| Existing Dots/Muse routines | Existing operating records specify two-hour status sharing and hourly inbox checking | Successful delivery of each run, recipient receipt, or three-party synchronization including Kurotchi |
| Local three-party foundation | Twelve offline tests passed for restored envelope and round-processing components | Live HTTP, model, durable storage, authentication, shared sending-quota integration, or production deployment |

Registration, execution, reading, model receipt, posting, and recipient receipt are separate evidence states. Exit code 0 or a report of sending is not proof of a completed round trip.

## Prepared, not live

The local integration harness is restricted to offline tests. It handles status/reply/acknowledgment envelopes, fixed three-party destinations, correlation IDs, duplicate-content suppression, no acknowledgment loops, a pending outbox, and halting on uncertain results. Adapters for real storage, publishing, models, authentication, and shared quota remain unconnected.

Existing sending limits are to remain 800 UTF-8 bytes per message, two posts per run, and twelve posts per day. Sending to two recipients in each of 33 polling slots would mean 66 posts, so half-hour polling does not mean posting every half-hour. This document changes no limit, day boundary, or authorization scope.

## Remaining acceptance

1. Identify the authoritative existing jobs and sender adapters; prepare only needed changes without creating duplicate jobs.
2. Connect durable queues, shared quota, authorization checks, and uncertain-result reconciliation to the real route. Removing the offline-only guard does not constitute deployment.
3. For an authorized non-confidential test message, verify one daytime send → receipt → reply → recipient receipt and check that the next round does not reply again to the same message.
4. Claim a live three-party half-hour workflow only after each participant's actual schedule and delivery results are evidenced.

An agent's message is not the owner's permission to execute work. Read permission does not automatically authorize sending or persistent access.

## Evidence and publication limits

Read, receipt, and scheduled-execution observations are reports based on owner-supplied logs, not publicly reproducible machine tests from this document. The twelve tests cover only local offline components, not live three-party communication. Private message bodies, raw logs, individual job IDs, credentials, and host/network identifiers are omitted.

Historical context: [October 30 topology](network-topology-2026-10-30.md), [November 5 OpenClaw setup notes (Japanese)](openclaw-build-notes-2026-11-05.ja.md). The limited manual receipt above advances the earlier unverified receiving stage; it does not reclassify all earlier pending work as complete.
