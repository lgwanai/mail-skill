---
plan: 03-00
phase: 03-natural-language-search
wave: 1
status: completed
completed_at: 2026-04-04
---

# Plan 03-00 Summary: Test Stubs & Empty Modules

## Changes Made

### 1. Created scripts/mail_manager/date_parser.py

Empty module with `DateRange` dataclass and function stubs:
- `DateRange` dataclass with `start` and `end` datetime fields
- `parse_date_expression(text: str) -> DateRange | None` stub
- `extract_date_from_query(query: str) -> tuple[DateRange | None, str]` stub

### 2. Created scripts/mail_manager/query_parser.py

Empty module with `ParsedQuery` dataclass and function stubs:
- `ParsedQuery` dataclass with `date_range`, `senders`, `keywords`, `original_query` fields
- `parse_natural_query(query: str, sender_list: list[str]) -> ParsedQuery` stub
- `match_senders(query_sender: str, sender_list: list[str]) -> list[str]` stub
- `extract_keywords(query: str) -> list[str]` stub

### 3. Created tests/test_date_parser.py

Test stubs with:
- Placeholder test that passes
- Skipped tests for `test_parse_date_expression` and `test_extract_date_from_query`

### 4. Created tests/test_query_parser.py

Test stubs with:
- Placeholder test that passes
- Skipped tests for `parse_natural_query`, `match_senders`, `extract_keywords`

## Verification Results

- **Tests**: Placeholder tests pass
- **mypy**: Success, no issues
- **ruff**: All checks passed

## Requirements Covered

- Wave 0 prerequisite for SRCH-01, SRCH-02, SRCH-03 ✓

## Foundation Established

- TDD workflow enabled for Wave 1+ plans
- Empty modules importable without errors
- Test files ready for implementation tests
