---
phase: 7
slug: email-summary-report
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v --cov=scripts --cov-report=term-missing` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v --cov=scripts --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-00-01 | 00 | 0 | Test Stubs | unit | `pytest tests/test_summary_report.py --collect-only` | ❌ W0 | ⬜ pending |
| 07-01-01 | 01 | 1 | SUMMARY-01 | unit | `pytest tests/test_summary_report.py::TestGroupEmails -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | SUMMARY-02 | unit | `pytest tests/test_summary_report.py::TestSummarizeEmail -x` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 1 | SUMMARY-03 | unit | `pytest tests/test_summary_report.py::TestOverallSummary -x` | ❌ W0 | ⬜ pending |
| 07-03-01 | 03 | 2 | SUMMARY-04 | unit | `pytest tests/test_summary_report.py::TestFormatReport -x` | ❌ W0 | ⬜ pending |
| 07-04-01 | 04 | 3 | CLI | integration | `pytest tests/test_cli.py::TestSummaryReport -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_summary_report.py` — stubs for SUMMARY-01, SUMMARY-02, SUMMARY-03, SUMMARY-04
- [ ] Existing infrastructure covers all phase requirements (pytest, conftest.py, LLMClient mocks)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LLM summary quality | SUMMARY-02, SUMMARY-03 | Subjective evaluation | Review generated summaries for accuracy and usefulness |
| Report formatting | SUMMARY-04 | Visual assessment | Check Markdown output is clear and readable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
