# Review request compatibility

[日本語](review-request-compat.ja.md)

2026-11-12: source repair; three mocked cases **UNEXECUTED**.
[MiMo API](https://mimo.mi.com/docs/en-US/api/chat/openai-api-post) defaults
`mimo-v2.6-pro` thinking to enabled; disabled is supported.
[Deep thinking](https://mimo.mi.com/docs/en-US/quick-start/usage-guide/text-generation/deep-thinking)
shares the output budget with the final answer. Both bounded automatic lanes now
explicitly disable thinking; Alibaba overrides CLI settings before charging final
request bytes. Messages/tools, all limits (output2048), validation/length rejection,
no retries and old reservations remain. Standalone/synthetic relays are unchanged.
Reasoning depth may decrease; live recovery and quality acceptance remain pending.

PR55 records Alibaba CLI failure and Cloudflare validation failure, not the original
finish reason/upstream status. Exact cause is **UNKNOWN**; output2048 alone does
not prove truncation. Pinned Alibaba v1.13.7 preserves native reasoning history.
New tests need an execution budget and supported isolation.
