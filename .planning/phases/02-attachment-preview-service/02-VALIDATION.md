---
phase: 2
slug: attachment-preview-service
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-04
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing from Phase 1) |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_server.py -v --tb=short` |
| **Full suite command** | `pytest tests/ --cov=scripts --cov-fail-under=60` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_server.py -v --tb=short`
- **After every plan wave:** Run `pytest tests/ --cov=scripts --cov-fail-under=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | ATCH-01 | unit | `pytest tests/test_server.py::TestAttachmentServer -v` | Wave 0 | pending |
| 2-01-02 | 01 | 1 | ATCH-02 | unit | `pytest tests/test_server.py::TestLocalhostBinding -v` | Wave 0 | pending |
| 2-01-03 | 01 | 1 | ATCH-04 | unit | `pytest tests/test_server.py::TestPathValidation -v` | Wave 0 | pending |
| 2-01-04 | 01 | 1 | ATCH-05 | unit | `pytest tests/test_server.py::TestServerState -v` | Wave 0 | pending |
| 2-02-01 | 02 | 2 | ATCH-03 | unit | `pytest tests/test_cli.py::TestCmdAttachments -v` | Wave 0 | pending |
| 2-02-02 | 02 | 2 | ATCH-06 | unit | `pytest tests/test_cli.py::TestCmdAttachments -v` | Wave 0 | pending |

*Status: pending | green | red | flaky*

---

## Wave 0 Requirements

- [x] `tests/test_server.py` — created in Plan 01 Task 1 (TDD approach)
- [x] `tests/conftest.py` — shared fixtures (already exists from Phase 1)

*Plan 01 Task 1 creates test file before implementation (TDD). No pre-existing test scaffolding needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Browser download | ATCH-03 | Requires browser interaction | 1. Run `mail attachments` 2. Click link in terminal 3. Verify download in browser |
| Cross-command port reuse | ATCH-05 | Timing-dependent | 1. Run `mail attachments` 2. Run `mail attachments` again 3. Verify same port used |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated
