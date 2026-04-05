---
phase: 6
slug: smart-enhancements
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 6 — Validation Strategy

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
| 06-01-01 | 01 | 1 | THREAD-01 | unit | `pytest tests/test_thread.py -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | THREAD-02 | unit | `pytest tests/test_thread.py -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | THREAD-03 | unit | `pytest tests/test_thread.py -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | ATTACH-AI-01 | unit | `pytest tests/test_attachment_ai.py -x` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | ATTACH-AI-02 | unit | `pytest tests/test_attachment_ai.py -x` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 2 | REPLY-AI-01 | unit | `pytest tests/test_reply_ai.py -x` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 2 | REPLY-AI-02 | unit | `pytest tests/test_reply_ai.py -x` | ❌ W0 | ⬜ pending |
| 06-03-03 | 03 | 2 | REPLY-AI-03 | unit | `pytest tests/test_reply_ai.py -x` | ❌ W0 | ⬜ pending |
| 06-04-01 | 04 | 2 | CLI | integration | `pytest tests/test_cli.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_thread.py` — stubs for THREAD-01, THREAD-02, THREAD-03
- [ ] `tests/test_attachment_ai.py` — stubs for ATTACH-AI-01, ATTACH-AI-02
- [ ] `tests/test_reply_ai.py` — stubs for REPLY-AI-01, REPLY-AI-02, REPLY-AI-03
- [ ] Existing infrastructure covers all phase requirements (pytest, conftest.py)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LLM response quality | REPLY-AI-01, REPLY-AI-02 | Subjective evaluation | Review AI-polished replies for tone and relevance |
| Image OCR accuracy | ATTACH-AI-02 | Vision API varies | Spot-check image summaries |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
