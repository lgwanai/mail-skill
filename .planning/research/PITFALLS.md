# Domain Pitfalls: Intelligent Email System Enhancement

**Domain:** Email management with NLU search, classification, templates, and attachment service
**Researched:** 2026-04-04
**Confidence:** MEDIUM (based on codebase analysis and domain expertise)

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: NLU Search Breaks Existing Search Semantics

**What goes wrong:** Adding natural language understanding layer changes how search queries are interpreted, breaking existing workflows that rely on exact/FTS matching.

**Why it happens:** NLU layers often extract entities (dates, senders) and rewrite queries, which can:
- Over-extract: "find the report" becomes a search for literal "report" when user meant a specific document
- Under-extract: "last week from Wang" fails if "Wang" is not recognized as a sender pattern
- Change precedence: FTS5 phrase matching gets lost when query is preprocessed

**Consequences:**
- Users lose trust in search functionality
- Existing search patterns that worked stop working
- Debugging becomes difficult (NLU black box)

**Prevention:**
- Implement NLU as an OPTIONAL layer with fallback to raw FTS
- Preserve original query alongside extracted entities
- Log NLU transformations for debugging
- Test against existing search test cases (when tests exist)

**Detection:**
- Search regression tests failing
- User complaints about "search worked before"
- NLU extraction logs showing over-aggressive entity extraction

**Phase to address:** Smart NLU Search implementation phase

---

### Pitfall 2: Classification Labels Drift and Become Meaningless

**What goes wrong:** Auto-classification starts with good intentions but labels become inconsistent, duplicated, or abandoned over time.

**Why it happens:**
- No canonical label taxonomy defined upfront
- Classification confidence thresholds too low (false positives)
- No human feedback loop for correction
- Labels like "important" become subjective (what's important to whom?)

**Consequences:**
- Users stop trusting classification
- Label database becomes noisy
- Retraining/reclassification becomes expensive

**Prevention:**
- Define a small, fixed set of classification categories (5-7 max)
- Implement confidence thresholds with explicit "uncertain" bucket
- Add user correction feedback that updates classifier
- Make classification advisory, not prescriptive (show confidence)

**Detection:**
- High false positive rate in manual review
- Users manually reclassifying emails
- Labels with very few emails or labels with most emails

**Phase to address:** Smart Classification phase (after search is stable)

---

### Pitfall 3: Attachment Service Security Surface Area

**What goes wrong:** Local HTTP server for attachments exposes files to unauthorized access or command injection.

**Why it happens:**
- HTTP server on localhost is still network-accessible on shared machines
- Path traversal: `GET /attachments/../../../etc/passwd`
- No authentication on the attachment server
- Predictable URLs allow enumeration
- File type sniffing vulnerabilities (serving `.exe` as safe types)

**Consequences:**
- Credential/attachment exposure
- Remote code execution via malicious attachments
- Compliance violations (data exfiltration)

**Prevention:**
- Bind to localhost (127.0.0.1) only, not 0.0.0.0
- Implement path sanitization with explicit allowlist
- Generate one-time tokens for each attachment access
- Set Content-Disposition: attachment to prevent inline execution
- Restrict to specific file types or force download

**Detection:**
- Security scan showing open HTTP ports
- Path traversal tests succeeding
- Attachments opening in browser instead of downloading

**Phase to address:** Attachment Service phase (requires security review BEFORE implementation)

---

### Pitfall 4: Template System Creates Send Errors

**What goes wrong:** Reply templates with placeholders cause emails to be sent with unfilled or incorrectly filled placeholders.

**Why it happens:**
- Template placeholders like `{name}` not validated before send
- Missing context variables filled with empty string or literal placeholder
- Templates applied to wrong recipient types (formal template to casual contact)
- No preview before send

**Consequences:**
- Unprofessional emails sent with `{NAME}` visible
- Wrong information in templates
- Users abandon template feature entirely

**Prevention:**
- Require all placeholders to be filled before send (validation)
- Provide preview step showing rendered template
- Template metadata specifying required fields
- Fallback values for missing fields

**Detection:**
- Emails sent with literal placeholder text
- User complaints about wrong template content
- Template validation warnings ignored

**Phase to address:** Template System phase

---

## Moderate Pitfalls

### Pitfall 5: Embedding Model Drift After Initial Indexing

**What goes wrong:** Vector search quality degrades when embedding model is changed or updated, making old embeddings incompatible.

**Why it happens:** The codebase currently allows model override via `EMBEDDING_MODEL_NAME` environment variable. Changing models mid-stream creates incompatible vector spaces.

**Prevention:**
- Pin embedding model version in configuration
- Store model name with embeddings
- Require full reindex when model changes
- Document model change process clearly

**Detection:**
- Search results becoming nonsensical after model change
- ChromaDB returning low similarity scores

---

### Pitfall 6: Multiprocessing Fetch Leaves Orphaned Processes

**What goes wrong:** Using `multiprocessing.Process` for async fetch (current implementation at line 266) can leave zombie processes if parent crashes.

**Why it happens:** The current implementation starts a process and returns immediately. If the parent CLI crashes, the child process continues as orphan.

**Prevention:**
- Implement process monitoring/cleanup
- Use task files with heartbeat timestamps
- Add timeout-based cleanup for stalled tasks
- Consider `subprocess` with proper lifecycle management

**Detection:**
- Zombie processes visible in `ps aux`
- Task files stuck in "running" state indefinitely
- Memory/CPU consumption from orphaned processes

---

### Pitfall 7: ChromaDB Lazy Loading Causes First-Search Latency

**What goes wrong:** First search after startup is slow because embedding model is loaded on-demand (noted in CONCERNS.md).

**Why it happens:** `_get_chroma_collection()` lazy-loads the embedding model on first call, which can take 5-30 seconds depending on model size.

**Prevention:**
- Implement warmup function called at startup
- Cache the collection instance after first load
- Show loading indicator during first search
- Consider model preloading in background thread

**Detection:**
- First search taking >5 seconds
- User complaints about "slow search"
- Memory spike on first search

---

### Pitfall 8: Inconsistent Error Handling Confuses AI Agent

**What goes wrong:** Mixed error handling patterns (JSON vs exceptions) make it difficult for AI agents to parse and respond to errors reliably.

**Why it happens:** Some commands return `{"status": "error", "message": "..."}` while others raise exceptions. The CLI catches some exceptions but not all.

**Prevention:**
- Standardize on JSON response format for ALL commands
- Add error codes for programmatic handling (e.g., `{"status": "error", "code": "EMAIL_NOT_FOUND", "message": "..."}`)
- Document error response schema
- Add error handling middleware/pattern

**Detection:**
- AI agent failing to parse errors
- Some errors showing stack traces instead of JSON

---

## Minor Pitfalls

### Pitfall 9: Chinese Text in FTS5 Tokenization

**What goes wrong:** FTS5 with default tokenizer doesn't handle Chinese well, requiring LIKE fallback which is slow.

**Why it happens:** The current code already handles this with LIKE fallback, but it's a performance concern for large email databases.

**Prevention:**
- Consider jieba or similar Chinese tokenizer for FTS5
- Pre-process Chinese text with word segmentation
- Monitor LIKE fallback frequency

**Detection:**
- Search latency for Chinese queries
- Log analysis showing frequent LIKE fallback

---

### Pitfall 10: Account Path Sanitization Edge Cases

**What goes wrong:** Email address sanitization for directory names (`_get_account_paths`) may create collisions or unexpected paths.

**Why it happens:** The sanitization logic replaces `@` with `_at_` and `.` with `_`, but edge cases like `user@chinamobile.com` vs `user_at_chinamobile_com` could theoretically collide.

**Prevention:**
- Use hashing or unique IDs for account directories
- Map canonical email to directory path in database
- Test with various email formats (subdomains, plus addressing)

**Detection:**
- Account data appearing in wrong directory
- Path not found errors for valid accounts

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| NLU Search | Breaking existing FTS semantics | Parallel implementation, fallback, extensive testing |
| Classification | Label drift and false positives | Fixed taxonomy, confidence thresholds, user feedback |
| Attachment Service | Security vulnerabilities | Security review FIRST, path sanitization, authentication |
| Template System | Sending unfilled placeholders | Validation, preview, required field enforcement |
| Code Quality | Breaking existing functionality | Test coverage BEFORE refactoring |
| Email Detail UI | Information overload | Progressive disclosure, summary-first design |

---

## Sources

- Codebase analysis: `mail_cli.py`, `client.py`, `db.py`
- Existing concerns documented in `.planning/codebase/CONCERNS.md`
- Domain expertise: Email systems, NLU applications, security patterns
- Confidence: MEDIUM (no external validation, based on code analysis and domain knowledge)
