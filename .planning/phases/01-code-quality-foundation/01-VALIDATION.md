# Phase 1: Code Quality Foundation - Validation Strategy

**Phase:** 1
**Slug:** code-quality-foundation
**Created:** 2026-04-04

## Validation Dimensions

### Dimension 1: Test Coverage (QUAL-01)

| Check | Command | Pass Criteria |
|-------|---------|---------------|
| Core modules coverage | `pytest --cov=scripts/mail_manager --cov-report=term-missing` | ≥80% |
| Other modules coverage | `pytest --cov=scripts --cov-report=term-missing` | ≥60% |
| Critical path tests exist | `pytest tests/test_client.py tests/test_db.py tests/test_cli.py -v` | All pass |

**Sampling:**
- Per commit: `pytest tests/ -x -q`
- Wave gate: `pytest --cov=scripts --cov-report=term-missing`
- Phase gate: `pytest --cov-fail-under=80`

### Dimension 2: Type Checking (QUAL-02)

| Check | Command | Pass Criteria |
|-------|---------|---------------|
| mypy passes | `mypy scripts/` | 0 errors (warnings allowed) |
| All files have annotations | Manual: `grep -L "def " scripts/mail_manager/*.py` | All functions typed |

### Dimension 3: Error Handling (QUAL-03)

| Check | Command | Pass Criteria |
|-------|---------|---------------|
| Error format tests pass | `pytest tests/test_errors.py -v` | All pass |
| All commands use ErrorCodes | `grep -r "status.*error" scripts/` | Consistent format |
| No mixed error formats | `grep -r '"error"' scripts/` | None found (should use status: error) |

### Dimension 4: Linting (QUAL-04)

| Check | Command | Pass Criteria |
|-------|---------|---------------|
| ruff check passes | `ruff check scripts/` | 0 errors |
| ruff format applied | `ruff format --check scripts/` | All files formatted |
| pyproject.toml exists | `test -f pyproject.toml` | File exists |

## Test Files Required

| File | Purpose | Status |
|------|---------|--------|
| `tests/conftest.py` | Shared fixtures | Pending |
| `tests/test_client.py` | MailClient unit tests | Pending |
| `tests/test_db.py` | MailDatabase unit tests | Pending |
| `tests/test_cli.py` | CLI command tests | Pending |
| `tests/test_errors.py` | Error format tests | Pending |

## New Files Required

| File | Purpose | Status |
|------|---------|--------|
| `pyproject.toml` | Tool configuration | Pending |
| `requirements-dev.txt` | Development dependencies | Pending |
| `scripts/mail_manager/models.py` | Dataclasses for type annotations | Pending |
| `scripts/mail_manager/errors.py` | Error code definitions | Pending |

## Phase Gate Command

```bash
# Must pass all checks before phase can be marked complete
pytest --cov-fail-under=80 && \
mypy scripts/ --ignore-missing-imports && \
ruff check scripts/ && \
ruff format --check scripts/
```

## Coverage Exclusions

The following are excluded from coverage requirements:
- `scripts/mail_cli.py` - CLI entry point, tested via integration
- `*/__pycache__/*`
- Test files themselves

## Relaxed Criteria During Phase

Initial targets (can be relaxed during execution):
- Coverage: Start at 60%, ramp to 80% by phase end
- mypy: Warnings allowed, errors must be fixed
- ruff: Complexity warnings (C901) allowed during transition
