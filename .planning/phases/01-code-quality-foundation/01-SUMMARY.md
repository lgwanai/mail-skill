---
phase: 01-code-quality-foundation
plan: 01
subsystem: infrastructure
tags: [tooling, configuration, error-handling, type-annotations]
dependency_graph:
  requires: []
  provides:
    - pyproject.toml for pytest/mypy/ruff configuration
    - requirements-dev.txt for dev dependencies
    - errors.py for standardized error handling
    - models.py for type-safe data structures
  affects: [02, 03, 04]  # All subsequent plans depend on this
tech_stack:
  added:
    - pytest 7.4+ (testing framework)
    - pytest-cov 4.1+ (coverage measurement)
    - pytest-mock 3.11+ (mocking utilities)
    - mypy 1.5+ (static type checking)
    - ruff 0.1+ (linting and formatting)
  patterns:
    - dataclass for type-safe data structures
    - error code classification (USER/SERVER/BIZ)
    - standardized JSON response envelope
key_files:
  created:
    - path: pyproject.toml
      lines: 80
      purpose: Tool configuration for pytest, mypy, ruff
    - path: requirements-dev.txt
      lines: 13
      purpose: Development dependencies
    - path: scripts/mail_manager/errors.py
      lines: 92
      purpose: Error code definitions and response helpers
    - path: scripts/mail_manager/models.py
      lines: 74
      purpose: Dataclasses for type annotations
  modified: []
decisions:
  - id: D01-01
    decision: Use pytest with relaxed coverage threshold (60% -> 80%)
    rationale: Start with achievable target, ramp up as tests are added
  - id: D01-02
    decision: mypy in relaxed mode (allow Any, ignore missing imports)
    rationale: Gradual typing approach for existing codebase without types
  - id: D01-03
    decision: Error codes classified as USER/SERVER/BIZ
    rationale: Clear categorization by error source for better debugging
  - id: D01-04
    decision: Python 3.8 compatible with __future__ annotations
    rationale: Support older Python versions while using modern type syntax
metrics:
  duration_minutes: 5
  completed_date: 2026-04-04
  tasks_completed: 4
  files_created: 4
  files_modified: 0
---

# Phase 1 Plan 1: Foundation Configuration Summary

One-liner: Established project tooling configuration (pytest, mypy, ruff) and shared modules (error codes, data models) for all subsequent quality improvements.

## Objective

Create the foundational configuration files and shared modules that all subsequent plans will depend on. Establish tool configuration (pytest, mypy, ruff) and create shared error handling + data models before adding tests and type annotations.

## Completed Tasks

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Create pyproject.toml with tool configurations | 4047003 | Done |
| 2 | Create requirements-dev.txt with development dependencies | 9f620af | Done |
| 3 | Create errors.py with error code definitions | c9667d1 | Done |
| 4 | Create models.py with dataclasses for type annotations | ccc57a0 | Done |

## Output Artifacts

### pyproject.toml
- pytest configuration with coverage (60% threshold, excluding mail_cli.py)
- mypy configuration in relaxed mode for gradual typing
- ruff configuration for PEP 8 linting and formatting

### requirements-dev.txt
- pytest>=7.4.0, pytest-cov>=4.1.0, pytest-mock>=3.11.0
- mypy>=1.5.0
- ruff>=0.1.0

### scripts/mail_manager/errors.py
- ErrorCodes class with USER_xxx, SERVER_xxx, BIZ_xxx classifications
- error_response() helper for standardized error JSON
- success_response() helper for standardized success JSON
- ErrorResponse dataclass for structured error handling

### scripts/mail_manager/models.py
- EmailData dataclass matching existing email_data dict structure
- Attachment dataclass for email attachments
- CommandResult dataclass with to_dict() for CLI responses

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- [x] pyproject.toml has [tool.pytest.ini_options], [tool.mypy], [tool.ruff] sections
- [x] requirements-dev.txt contains all required dependencies
- [x] errors.py imports without errors (ErrorCodes, error_response, success_response)
- [x] models.py imports without errors (EmailData, Attachment, CommandResult)

## Self-Check

```
FOUND: /Users/wuliang/workspace/mail-skill/pyproject.toml
FOUND: /Users/wuliang/workspace/mail-skill/requirements-dev.txt
FOUND: /Users/wuliang/workspace/mail-skill/scripts/mail_manager/errors.py
FOUND: /Users/wuliang/workspace/mail-skill/scripts/mail_manager/models.py
FOUND: 4047003 in git log
FOUND: 9f620af in git log
FOUND: c9667d1 in git log
FOUND: ccc57a0 in git log
```

## Self-Check: PASSED
