# Quality Baseline P1 Minimal Setup & P3 Evaluation Preparation Report

[English](quality-baseline-evaluation-p1-p3.md) | [日本語](quality-baseline-evaluation-p1-p3.ja.md)

- Date: 2026-10-26 (JST)
- Target Repository: `multi-ai-workflow`
- Canonical Design: `docs/mailbox-quality-roadmap-2026-10-26.ja.md`
- Working Branch: `feature/quality-baseline-p1-p3`
- Goal: Establish the initial phase ("Deterministic Checks -> Alibaba OCR + MiMo API -> Cloudflare Audit for Critical Changes only") to reduce full-text re-reading and redundant reviews by Codex.
- **Current Scope Clarification**: The current state is strictly "synthetic samples and input preparation", NOT full Alibaba OCR integration. Pinned OCR CLI versions, standalone live connections, and hard billing budget enforcements are intentionally left unimplemented.
- Scope Boundaries: Focus strictly on P1 minimal setup and P3 evaluation input preparation. No Mailbox adapters, no daemons, no cross-repo deployment, no unapproved package installation, and no external API calls.

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
  1. Python syntax check (`py_compile.compile` across 16 Python files)
  2. Required test suites execution (`REQUIRED_TEST_SUITES` strictly checks for directory presence, non-zero execution, skipped counts, and failures)
  3. Fixtures integrity check (validating manifest presence, patch existence, and non-empty files)
  4. Documentation formatting check (detecting irregular trailing whitespaces/tabs)
  5. External tool inspection and explicit recording of unverified scope
- **Strict Quality Criteria**:
  - Missing required suites or 0 executed tests are treated as immediate FAIL.
  - Test skips (`tests_skipped`) are tracked and reported separately.
  - Dedicated regression test suite (`tests/test_quality_baseline.py`, 6 tests) verifies runner and fixture integrity.

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

## 2. P3: Synthetic Samples & Input Preparation (Pre-OCR Integration Phase)

### 2.1 Current Scope & Unimplemented Items

- **Current Completed Scope**:
  - Creation of publicly shareable synthetic patches.
  - Ground truth metadata definition (strictly excluded from reviewer inputs).
  - Offline dry-run verification runner (`tools/eval_ocr_mimo.py`).
- **Items Intentionally Left Unimplemented**:
  - Alibaba OCR official CLI (`ocr`) fixed version pinning and installation.
  - Standalone live network connection to MiMo API.
  - Hardware-enforced billing/token budget ceiling (requires external proxy/credential limits).

### 2.2 Synthetic Samples & Ground Truth

To prevent leaking private code, credentials, or personal information, synthetic patches are stored in `tests/fixtures/synthetic_samples/`:

1. **Clean Sample (`clean_refactor.patch`)**:
   - Refactor: Preserves exact semantics without behavior alterations (type annotations, list comprehension equivalence).
   - Purpose: Measure False Positives (hallucination / excessive nitpicking).
   - Expected Defects: **0**
2. **Defect-Seeded Sample (`defect_seeded.patch`)**:
   - Natural diff free of any hint comments (`DEFECT` or answer annotations removed):
     - Line 11: Path Traversal (`target_path = self.base_path / user_supplied_name`, CWE-22, CRITICAL)
     - Line 12: Resource Leak (unclosed `open()`, CWE-775, MEDIUM)
     - Line 18: Arbitrary Code Execution (`eval(filter_expr)`, CWE-95, CRITICAL)
     - Line 20: Silent Failure (`except Exception: pass`, CWE-391, LOW)
   - Purpose: Measure Recall (missed defect rate), severity scoring, and actionable findings.
   - Expected Defects: **4**
3. **Ground Truth Manifest (`synthetic_samples_manifest.json`)**:
   - Structured metadata defining line numbers, CWEs, and severity.
   - **Crucial**: Strictly excluded from reviewer input prompts; used exclusively for offline evaluation.

### 2.3 Evaluation Metrics Recording Framework

The evaluation will record the following metrics independently:
- **Actionable Findings**: Valid findings with actionable fixes and clear impact.
- **False Positives**: Incorrect or unwarranted warnings on clean code.
- **Missed Defects (Seeded Misses)**: Ground truth defects overlooked by the reviewer.
- **Coverage Scope**: Evaluated vs. excluded file boundaries.
- **Latency**: Duration in seconds.
- **Usage & Cost**: Input/output tokens and actual cost in USD/JPY (`UNKNOWN` if unobserved).
*Note: Upstream's "~1/9 token ratio" is not treated as a guarantee, and zero findings or partial failures will not be treated as success.*

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
  - Ground truth metadata strictly excluded from reviewer input.
  - No API keys or secrets printed, logged, or committed.
  - Immediate fail-closed stop on authorization refusal or unexpected error.

---

## 5. Current State & Handoff

- **Status**: P1 minimal setup completed; P3 synthetic preparation completed (offline dry-run verified, 6 regression tests passing).
- **Handoff**: Stopping execution without automatic merge or proceeding to subsequent phases (P2 live communication or P4 integration).
