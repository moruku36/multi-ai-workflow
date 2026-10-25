# Quality Baseline P1 Minimal Setup & P3 Standalone Evaluation Preparation Report

[English](quality-baseline-evaluation-p1-p3.md) | [日本語](quality-baseline-evaluation-p1-p3.ja.md)

- Date: 2026-10-26 (JST)
- Target Repository: `multi-ai-workflow`
- Canonical Design: `docs/mailbox-quality-roadmap-2026-10-26.ja.md`
- Working Branch: `feature/quality-baseline-p1-p3`
- Goal: Establish the initial phase ("Deterministic Checks -> Alibaba OCR + MiMo API -> Cloudflare Audit for Critical Changes only") to reduce full-text re-reading and redundant reviews by Codex.
- Scope Boundaries: Focus strictly on P1 minimal setup and P3 evaluation preparation. No Mailbox adapters, no daemons, no cross-repo deployment, no unapproved package installation, and no external API calls.

---

## 1. P1: Existing Environment Inventory & Deterministic Check Minimal Setup

### 1.1 Existing Assets Inventory

| Item | Status / Details | Note |
|---|---|---|
| **CI / Workflows** | Not configured (`.github/workflows` absent) | No automated CI configured on the repo itself |
| **Target Languages** | Python 3.11, Node.js 22.23 (v8), Shell, PowerShell, Markdown, Mermaid | Primarily workflow documentation and auxiliary scripts |
| **Test Suites** | 88 unittests under `configs/openwebui-local-memory-0.11.4` | All 88 tests pass (54 + 27 + 7) |
| **Build / Diagrams** | Pele 1.6.0 (vendored tarball) in `tools/architecture/` | `npm run build` generates SVGs from Mermaid (requires offline `npm ci`) |
| **Static Analysis** | `ruff` and `semgrep` not installed in global PATH | Python, Node.js, and npm are available |

### 1.2 Minimal Check-Only Runner (`tools/check_quality.py`)

A zero-external-dependency runner built exclusively with Python 3.11 standard library.
Executes check-only verification without auto-fixing or full reformatting.

- **Command**: `python tools/check_quality.py` (or `--json`)
- **Checks Executed**:
  1. Python syntax check (`py_compile.compile` across 14 Python files)
  2. Existing unittest execution (3 suites, 88 tests total)
  3. Documentation formatting check (detecting irregular trailing whitespaces/tabs)
  4. External tool inspection and explicit recording of unverified scope
- **Execution Result**:
  - `overall_status`: **PASSED**
  - Python Syntax: OK (14 files)
  - Unittests: OK (88 tests run, 0 failures, 0 errors)
  - Doc Format: OK (47 files)
  - Tool Status: Accurately detected `ruff` (MISSING) and `semgrep` (MISSING), recording reason for skipping.

### 1.3 Proposal for Initial Pilot Repository

`multi-ai-workflow` is predominantly a documentation repository. Formality-only Ruff/Semgrep should not be introduced here without substantial application code.

**Recommended Pilot Repository**: `web-security-control-lab`
- **Rationale**:
  - Contains substantial FastAPI / Python 3.11 application code (37 code files).
  - Pre-configured `pyproject.toml` with `[tool.ruff]` (E, F, W, I, line-length 100) and `[tool.pytest]`.
  - Dedicated `.venv` with `ruff.exe` and `pytest.exe` already installed, enabling immediate test runs without new dependency downloads.
  - As a security education lab, it serves as the ideal benchmark target for testing static analysis and vulnerability review accuracy.
- **Secondary Candidate**: `home-ai-engineering-lab` (52 code files with schemas, scripts, and tests).

---

## 2. P3: Alibaba OCR + MiMo API Standalone Evaluation Preparation

### 2.1 Alibaba OCR Specifications & Operating Model

- **Overview**: Alibaba `open-code-review` (CLI: `ocr`, Apache-2.0). Combines a deterministic Go engineering pipeline with LLM agents. Tracks Git diffs at exact line level to avoid line drift.
- **Standalone + MiMo Setup**:
  - Uses Xiaomi MiMo API (OpenAI-compatible endpoint) as the review inference backend.
  - **Distinction from Codex Delegation**: Configured as an independent standalone route rather than relying on Codex session quotas or host agent delegation.
- **Cost & Quota Boundaries**:
  - Upstream's "~1/9 token ratio" is treated strictly as an unverified author reference, not as a local performance guarantee.
  - `max-token-budget` is not treated as a strict billing ceiling; external boundaries (max calls, token limits, timeouts, hard cost ceilings) must enforce execution safety.
  - Zero findings or partial failures are not treated as success.

### 2.2 Synthetic Samples & Ground Truth

To prevent leaking private code, credentials, or personal information, synthetic patches are stored in `tests/fixtures/synthetic_samples/`:

1. **Clean Sample (`clean_refactor.patch`)**:
   - Refactor: Type annotations, list comprehension, built-in `sum()`.
   - Purpose: Measure False Positives (hallucination / excessive nitpicking).
   - Expected Defects: **0**
2. **Defect-Seeded Sample (`defect_seeded.patch`)**:
   - Four distinct seeded defects:
     - DEFECT-01: Path Traversal (`target_path = self.base_path / user_supplied_name`, CWE-22, CRITICAL)
     - DEFECT-02: Resource Leak (unclosed `open()`, CWE-775, MEDIUM)
     - DEFECT-03: Arbitrary Code Execution (`eval(filter_expr)`, CWE-95, CRITICAL)
     - DEFECT-04: Silent Failure (`except Exception: pass`, CWE-391, LOW)
   - Purpose: Measure Recall (missed defect rate), severity scoring, and actionable findings.
   - Expected Defects: **4**
3. **Ground Truth Manifest (`synthetic_samples_manifest.json`)**:
   - Structured metadata defining line numbers, CWEs, and severity.

### 2.3 Evaluation Metrics Recording Framework

The evaluation will record the following metrics independently:
- **Actionable Findings**: Valid findings with actionable fixes and clear impact.
- **False Positives**: Incorrect or unwarranted warnings on clean code.
- **Missed Defects (Seeded Misses)**: Ground truth defects overlooked by the reviewer.
- **Coverage Scope**: Evaluated vs. excluded file boundaries.
- **Latency**: Duration in seconds.
- **Usage & Cost**: Input/output tokens and actual cost in USD/JPY (`UNKNOWN` if unobserved).

---

## 3. Future Branch: Cloudflare security-audit-skill Routing

Cloudflare's `security-audit-skill` is an intensive audit process involving human and multi-agent flows, not a zero-cost CI linter.

### Routing Criteria (Trigger Conditions)
- **Standard Diffs**: Deterministic check -> Alibaba OCR + MiMo API review.
- **High-Risk Diffs (Branch to Cloudflare Focused Audit)**:
  - Changes to authentication and authorization logic.
  - Changes to credential/secret boundaries (API keys, certificates, tokens).
  - Direct execution of external input, shell command execution, file system access boundaries.
  - Permission changes (IAM, security policies, access control).
  - External supply-chain modifications (new third-party dependencies).
*Note: Full audit runs and multi-party review loops are deferred until these triggers are met.*

---

## 4. Live MiMo Connection Test Proposal (Awaiting Approval)

An offline dry-run runner (`tools/eval_ocr_mimo.py`) has been implemented and verified.
Upon user authorization, live testing can proceed under the following constraints:

### Proposal Parameters
- **Authorized Endpoint**: Pre-approved OpenAI-compatible MiMo endpoint
- **Model ID**: `mimo-v2.6-pro` (or designated authorized ID)
- **Enforced Bounds**:
  - Max calls: **2 calls** (limited to the 2 synthetic samples)
  - Max input tokens: **2,048 tokens / call**
  - Max output tokens: **1,024 tokens / call**
  - Timeout: **30s / call**
  - Cost ceiling: **$0.10 USD**
- **Safety Guards**:
  - Synthetic test patches only; zero private repository data.
  - No API keys or secrets printed, logged, or committed.
  - Immediate fail-closed stop on authorization refusal or unexpected error.

---

## 5. Current State & Handoff

- **Status**: P1 minimal setup completed; P3 standalone evaluation preparation completed (offline dry-run verified).
- **Handoff**: Stopping execution without automatic merge or proceeding to subsequent phases (P2 live communication or P4 integration).
