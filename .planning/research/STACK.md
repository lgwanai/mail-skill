# Technology Stack

**Project:** Mail Skill v2.0 - Intelligent Email Management Enhancement
**Researched:** 2026-04-04
**Confidence:** MEDIUM (Limited external tool access; recommendations based on training data with architectural fit analysis)

## Recommended Stack Additions

### NLU / Intent Parsing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **dateparser** | >=1.2.0 | Natural language date extraction | Lightweight, no ML required. Handles Chinese/English relative dates ("上周", "last Monday"). Essential for "上周王总的预算邮件" queries. |
| **Rule-based NLU layer** | Custom | Intent classification + entity extraction | Build on existing hybrid search. Use regex + heuristics for sender/topic/time extraction. No heavy ML framework needed. |

**Rationale:** The project already has ChromaDB + sentence-transformers for semantic understanding. Adding a full NLU framework like spaCy or Rasa would be overkill. A lightweight dateparser + custom rule-based extraction layer integrates cleanly with the existing `search_hybrid()` function.

**NOT Recommended:**
- **spaCy** - Heavy dependency (~400MB models), overkill for email query parsing
- **Rasa NLU** - Requires training data, server setup, adds complexity
- **transformers (Hugging Face)** - Already using sentence-transformers; avoid duplicate ML infrastructure

### Email Classification / Importance Ranking

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Existing: CrossEncoder (BAAI/bge-reranker-base)** | Already installed | Relevance scoring for search | Already used in `search_hybrid()`. Reuse for importance scoring with custom query templates ("important emails", "action required"). |
| **Rule-based classifier** | Custom | Category assignment | Extend existing `cmd_summarize()` keyword logic into persistent categories. Zero ML overhead. |
| **Optional: scikit-learn** | >=1.3.0 | ML classification (future) | If keyword rules insufficient, add lightweight NaiveBayes classifier. Not needed for MVP. |

**Rationale:** The existing `cmd_summarize()` already uses keyword-based categorization (important_keywords, verification_keywords, action_keywords). Extend this pattern rather than introducing new ML frameworks. CrossEncoder scores can double as importance indicators.

**NOT Recommended:**
- **Full ML classification pipelines** - Overkill for ~10 categories, requires training data
- **Deep learning classifiers** - Inference latency violates <2s constraint

### Template System

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Existing: Jinja2** | >=3.1.0 | Template rendering | Already installed and used for email_table.md.j2. Extend with reply templates. |
| **YAML template definitions** | Custom | Template storage | Human-readable, supports metadata (name, description, variables). Store in `references/templates/replies/`. |

**Rationale:** Jinja2 is battle-tested and already a dependency. No new template engine needed. YAML provides clean storage format for template metadata.

**NOT Recommended:**
- **Mako / Chameleon** - Another template engine, adds confusion
- **Markdown-only templates** - Need variable interpolation, Jinja2 provides this

### Attachment HTTP Server

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **http.server (stdlib)** | Python 3.8+ | Simple HTTP file server | Zero dependencies, built-in, sufficient for local file serving. Use `http.server.ThreadingHTTPServer` for concurrent requests. |
| **socket (stdlib)** | Python 3.8+ | Find free port | Use `socket.bind(('', 0))` to auto-assign available port. |

**Rationale:** Project constraint: "附件服务采用本地 HTTP 服务器 | 无需云服务配置，完全本地化，自动找空闲端口". Python stdlib `http.server` is sufficient for serving local attachments. No need for FastAPI/Flask for simple file serving.

**NOT Recommended:**
- **FastAPI** - Overkill for static file serving, adds async complexity
- **Flask** - Adds unnecessary dependency for simple file server
- **aiohttp** - Async overhead not needed for local file serving

### Code Quality / Testing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pytest** | >=8.0.0 | Test framework | Industry standard, excellent fixture system, integrates with coverage tools. |
| **pytest-cov** | >=4.1.0 | Coverage reporting | Fulfills 80% coverage requirement. |
| **ruff** | >=0.3.0 | Linting + formatting | Replaces flake8, isort, black in single tool. Fast (Rust-based). |
| **mypy** | >=1.8.0 | Type checking | Static analysis for type hints. |

**Rationale:** Testing infrastructure is currently missing. pytest is the Python standard. ruff is the modern choice (replaces multiple tools). mypy for type safety.

**NOT Recommended:**
- **unittest** - Verbose, pytest is more ergonomic
- **flake8 + black + isort** - Three tools when ruff does all three
- **pylint** - Slower, more opinionated than ruff

## Current Stack (Unchanged)

These are already in place and should not be modified:

| Package | Version | Purpose |
|---------|---------|---------|
| `imap-tools` | >=1.5.0 | IMAP email operations |
| `chromadb` | >=0.4.0 | Vector embeddings |
| `sentence-transformers` | >=2.2.2 | Embeddings + reranking |
| `beautifulsoup4` | >=4.12.0 | HTML parsing |
| `markdown` | >=3.4.0 | Markdown to HTML |
| `jinja2` | >=3.1.0 | Template rendering |
| `python-dotenv` | >=1.0.0 | Configuration |

## Installation

```bash
# New dependencies for v2.0
pip install dateparser>=1.2.0

# Development dependencies (testing, linting)
pip install pytest>=8.0.0 pytest-cov>=4.1.0 ruff>=0.3.0 mypy>=1.8.0

# Optional future (if ML classification needed)
# pip install scikit-learn>=1.3.0
```

## Architecture Integration

```
┌─────────────────────────────────────────────────────────────┐
│                        AI Agent (CLI)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     mail_cli.py (Entry Point)                │
│  + NEW: nlu_parser.py (intent parsing)                       │
│  + NEW: classifier.py (email categorization)                 │
│  + NEW: attachment_server.py (HTTP file server)              │
│  + NEW: template_manager.py (reply templates)                │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  MailClient     │ │  MailDatabase   │ │  Templates      │
│  (existing)     │ │  (existing)     │ │  + Reply Tpls   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ dateparser      │
                    │ + CrossEncoder  │
                    │ (reuse existing)│
                    └─────────────────┘
```

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| NLU / Intent Parsing | MEDIUM | dateparser is well-known; rule-based approach fits existing architecture |
| Email Classification | HIGH | Reuses existing CrossEncoder; extends proven keyword pattern |
| Template System | HIGH | Jinja2 already installed; YAML is standard for config |
| HTTP File Server | HIGH | stdlib http.server is battle-tested for simple file serving |
| Code Quality | HIGH | pytest/ruff/mypy are 2025 Python standards |

## Sources

- Python stdlib documentation (http.server, socket)
- Existing codebase analysis (db.py, mail_cli.py)
- Training knowledge of Python ecosystem best practices
- Project constraints from PROJECT.md
