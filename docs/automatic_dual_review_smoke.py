"""Source-only activation fixture; this module is not executed by the workflow.

The pinned reviewer supports Python; Markdown selection remains a separate fix.
Both review lanes must record the same immutable diff with normal validation.
Completion is not independent quality acceptance or merge authorization.
"""

SMOKE_PURPOSE = "automatic dual-review activation"
