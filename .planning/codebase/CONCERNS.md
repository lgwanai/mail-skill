# Concerns: Mail Skill

## High Priority

### 1. Missing Test Coverage
**Location:** Project-wide
**Issue:** No tests exist for any functionality
**Impact:** 
- No regression protection
- Difficult to refactor safely
- Unknown behavior edge cases

**Recommendation:** 
- Add pytest framework
- Start with critical path tests (fetch, send, search)
- Target 80% coverage

### 2. Security: Credentials in Config File
**Location:** `config.txt`
**Issue:** Email passwords stored in plaintext
**Impact:**
- Credentials exposed if file is shared
- No encryption at rest

**Recommendation:**
- Document security implications clearly
- Consider encrypted storage option
- Support system keychain integration

### 3. Error Handling Inconsistency
**Location:** `mail_cli.py`, `client.py`
**Issue:** Mix of JSON error responses and exceptions
**Impact:**
- Agent may not parse errors consistently
- Some errors logged, others returned

**Recommendation:**
- Standardize on JSON error format
- Add error codes for programmatic handling

## Medium Priority

### 4. No Type Annotations
**Location:** All Python files
**Issue:** Functions lack type hints
**Impact:**
- Harder to understand function signatures
- No static type checking benefits

**Recommendation:**
- Add type annotations to all functions
- Run mypy for type checking

### 5. Large File: mail_cli.py
**Location:** `scripts/mail_cli.py` (999 lines)
**Issue:** Single file contains all CLI commands
**Impact:**
- Difficult to navigate
- Mixes concerns (formatting, business logic)

**Recommendation:**
- Split into command modules
- Extract formatting utilities

### 6. ChromaDB Initialization Overhead
**Location:** `db.py` - `_get_chroma_collection()`
**Issue:** Embedding model loaded on every search call
**Impact:**
- Slow first search
- Memory overhead

**Recommendation:**
- Lazy-load with caching
- Consider model warmup on startup

## Low Priority

### 7. Hardcoded Text (Chinese)
**Location:** `mail_cli.py` - `cmd_summarize()`, `cmd_thread()`
**Issue:** Chinese text hardcoded in code
**Impact:**
- Not internationalized
- Difficult to translate

**Recommendation:**
- Extract to locale files
- Support language configuration

### 8. No Logging Configuration
**Location:** `mail_cli.py`
**Issue:** Basic logging setup, no file output
**Impact:**
- Difficult to debug production issues
- No log rotation

**Recommendation:**
- Add structured logging
- Support log file configuration

### 9. Multiprocessing for Async Tasks
**Location:** `mail_cli.py` - `cmd_fetch()`
**Issue:** Uses multiprocessing instead of async
**Impact:**
- Heavier resource usage
- Harder to coordinate

**Recommendation:**
- Consider asyncio alternative
- Document tradeoffs

## Technical Debt Summary

| Priority | Count | Estimated Effort |
|----------|-------|------------------|
| High | 3 | 2-3 days |
| Medium | 3 | 1-2 days |
| Low | 3 | 1 day |

**Total Estimated Cleanup:** 4-6 days
