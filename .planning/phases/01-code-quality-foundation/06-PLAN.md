---
phase: 01-code-quality-foundation
plan: 06
type: execute
wave: 4
depends_on: [05]
files_modified: [scripts/mail_manager/client.py, scripts/mail_manager/db.py, scripts/mail_cli.py, scripts/mail_manager/errors.py, scripts/mail_manager/models.py]
autonomous: true
requirements: [QUAL-04]
user_setup: []

must_haves:
  truths:
    - "ruff check passes on all Python files"
    - "ruff format has been applied to all files"
    - "All code follows PEP 8 standard"
    - "Test coverage reaches 60%+ baseline"
  artifacts:
    - path: "scripts/mail_manager/*.py"
      provides: "Formatted and linted Python modules"
    - path: "tests/*.py"
      provides: "Formatted and linted test files"
  key_links:
    - from: "pyproject.toml"
      to: "ruff execution"
      via: "[tool.ruff] configuration"
      pattern: "ruff check scripts/"
---

<objective>
Apply ruff formatting and linting to all Python files, fix any linting issues, and verify test coverage meets baseline.

Purpose: Ensure all code follows PEP 8 standard, fix any linting issues, and establish coverage baseline.
Output: All Python files formatted and passing ruff checks
</objective>

<execution_context>
@/Users/wuliang/.claude/get-shit-done/workflows/execute-plan.md
@/Users/wuliang/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-code-quality-foundation/01-CONTEXT.md
@.planning/phases/01-code-quality-foundation/01-RESEARCH.md
@.planning/phases/01-code-quality-foundation/01-VALIDATION.md
@.planning/phases/01-code-quality-foundation/01-PLAN.md

<interfaces>
<!-- Configuration from Plan 01 pyproject.toml -->
From pyproject.toml:
```toml
[tool.ruff]
line-length = 100
target-version = "py38"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP"]
ignore = ["E501", "B008", "C901"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Run ruff format on all Python files</name>
  <files>scripts/**/*.py, tests/**/*.py</files>
  <action>
Run ruff format to auto-format all Python files in the project.

Command:
```bash
ruff format scripts/ tests/
```

This will apply consistent formatting based on pyproject.toml configuration:
- Quote style: double
- Indent style: space
- Line length: 100

After formatting, verify with:
```bash
ruff format --check scripts/ tests/
```

Expected: All files pass format check.
  </action>
  <verify>
    <automated>ruff format --check scripts/ tests/ 2>&1</automated>
  </verify>
  <done>All Python files are formatted according to ruff configuration</done>
</task>

<task type="auto">
  <name>Task 2: Run ruff check and fix linting issues</name>
  <files>scripts/**/*.py, tests/**/*.py</files>
  <action>
Run ruff check to identify linting issues, then fix them.

1. First, run ruff check with auto-fix:
```bash
ruff check scripts/ tests/ --fix
```

2. Review remaining issues:
```bash
ruff check scripts/ tests/
```

3. For any issues that cannot be auto-fixed:
   - E501 (line too long): Should be ignored per config
   - C901 (too complex): Allowed during transition per VALIDATION.md
   - B008 (function call in default argument): Allowed per config
   - For other issues, fix manually or add to ignore list if justified

Common fixes needed:
- Unused imports: Remove them
- Import order: ruff --fix handles this
- Missing newlines at end of files: Add them

Expected: 0 errors after fixes.
  </action>
  <verify>
    <automated>ruff check scripts/ tests/ 2>&1 | grep -c "error" || echo "0"</automated>
  </verify>
  <done>All Python files pass ruff linting with 0 errors</done>
</task>

<task type="auto">
  <name>Task 3: Run full test suite and verify coverage baseline</name>
  <files>tests/**/*.py</files>
  <action>
Run the full test suite with coverage reporting.

Command:
```bash
pytest tests/ --cov=scripts --cov-report=term-missing --cov-fail-under=60
```

This verifies:
1. All tests pass
2. Coverage reaches at least 60% (baseline per VALIDATION.md)
3. Coverage report shows which files/lines need more tests

If coverage is below 60%:
- Review the coverage report
- Identify files with low coverage
- Add tests for uncovered critical paths (fetch, search, send, reply)

Note: The target is 80%+ by phase end, but 60% is acceptable at this stage.
  </action>
  <verify>
    <automated>pytest tests/ --cov=scripts --cov-report=term-missing --cov-fail-under=60 2>&1 | tail -30</automated>
  </verify>
  <done>Test suite passes with 60%+ coverage; coverage report identifies remaining gaps</done>
</task>

</tasks>

<verification>
After all tasks complete, run the phase gate command:
```bash
pytest --cov-fail-under=60 && \
mypy scripts/ --ignore-missing-imports && \
ruff check scripts/ && \
ruff format --check scripts/
```

All checks must pass.
</verification>

<success_criteria>
- ruff format applied to all Python files
- ruff check passes with 0 errors on all files
- pytest passes with 60%+ coverage
- mypy passes on all scripts
- All code follows PEP 8 standard (enforced by ruff)
</success_criteria>

<output>
After completion, create `.planning/phases/01-code-quality-foundation/06-SUMMARY.md`
</output>
