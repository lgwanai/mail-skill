---
phase: 4
slug: smart-classification
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-04
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_classifier.py -v` |
| **Full suite command** | `pytest --cov=scripts/mail_manager --cov-report=term-missing` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_classifier.py tests/test_cli.py -v -k classify`
- **After every plan wave:** Run `pytest --cov=scripts/mail_manager --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-00-01 | 00 | 0 | CLAS-all | unit | `pytest tests/test_classifier.py -v` | ❌ W0 | ⬜ pending |
| 04-00-02 | 00 | 0 | CLAS-all | unit | `pytest tests/test_classifier.py -v` | ❌ W0 | ⬜ pending |
| 04-00-03 | 00 | 0 | CLAS-all | unit | `pytest tests/test_classifier.py -v` | ❌ W0 | ⬜ pending |
| 04-00-04 | 00 | 0 | CLAS-all | unit | `pytest tests/test_classifier.py -v` | ❌ W0 | ⬜ pending |
| 04-01-01 | 01 | 1 | CLAS-01, CLAS-02 | unit | `pytest tests/test_db.py -v -k classification` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | CLAS-01, CLAS-02 | unit | `pytest tests/test_db.py -v -k classification` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | CLAS-01, CLAS-02 | unit | `pytest tests/test_classifier.py -v -k load_rules` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | CLAS-03 | unit | `pytest tests/test_classifier.py -v -k match` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | CLAS-03 | unit | `pytest tests/test_classifier.py -v -k classify` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 3 | CLAS-04, CLAS-05 | unit | `pytest tests/test_db.py -v -k search_by_importance` | ✅ | ⬜ pending |
| 04-03-02 | 03 | 3 | CLAS-04, CLAS-05 | unit | `pytest tests/test_cli.py -v -k classify` | ✅ | ⬜ pending |
| 04-03-03 | 03 | 3 | CLAS-04, CLAS-05 | unit | `pytest tests/test_cli.py -v -k classification` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_classifier.py` — stubs for classifier tests
- [ ] `scripts/mail_manager/classifier.py` — empty module with Classification dataclass
- [ ] `scripts/mail_manager/rules.py` — empty module with load_rules signature
- [ ] `config/classification_rules.yaml` — default rules file

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | - | All automated | - |

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
