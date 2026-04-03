# Architecture: Mail Skill

## Overview

Mail Skill is a Python-based email management system designed for AI agents. It provides a local email client with semantic search, vector-based retrieval, and professional email composition capabilities.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        AI Agent (CLI)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     mail_cli.py (Entry Point)                │
│  - Command routing (fetch, search, send, reply, etc.)        │
│  - Async task management                                      │
│  - Output formatting (JSON/Markdown)                          │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  MailClient     │ │  MailDatabase   │ │  Templates      │
│  (client.py)    │ │  (db.py)        │ │  (Jinja2)       │
└─────────────────┘ └─────────────────┘ └─────────────────┘
        │                   │
        ▼                   ▼
┌─────────────────┐ ┌─────────────────┐
│  IMAP Server    │ │  SQLite +       │
│  SMTP Server    │ │  ChromaDB       │
└─────────────────┘ └─────────────────┘
```

## Core Components

### 1. MailClient (`scripts/mail_manager/client.py`)

**Purpose:** Email server communication

**Key Responsibilities:**
- IMAP connection management with SSL support
- Email fetching with search criteria (date, unread, folder)
- SMTP email sending with HTML support
- Server-side operations (mark read/starred, move, delete)
- Special handling for Netease (163/126/yeah) servers

**Key Methods:**
- `fetch_emails()` - Retrieve emails from IMAP with filtering
- `send_email()` - Send via SMTP with attachments
- `mark_as_read()`, `mark_as_starred()` - Flag operations
- `move_emails()`, `delete_emails()` - Folder operations

### 2. MailDatabase (`scripts/mail_manager/db.py`)

**Purpose:** Local storage and search indexing

**Storage:**
- **SQLite** - Primary relational storage with FTS5 full-text search
- **ChromaDB** - Vector embeddings for semantic search

**Key Features:**
- Multi-account isolated storage (per-account databases)
- FTS5 virtual table for fast text search
- Vector embeddings with configurable models (OpenAI/local)
- Hybrid search with BAAI reranking
- Email thread timeline reconstruction

**Key Methods:**
- `save_email()` - Persist email with attachments
- `search_fts()` - Full-text search
- `search_vector()` - Semantic vector search
- `search_hybrid()` - Combined search with reranking
- `get_thread_timeline()` - Thread reconstruction

### 3. CLI Interface (`scripts/mail_cli.py`)

**Purpose:** Command-line interface for AI agent interaction

**Commands:**
- `fetch` - Async email fetching with task tracking
- `search` - Query emails (FTS/vector/hybrid)
- `read` - View specific email
- `send` - Compose and send new email
- `reply` - Reply to existing email
- `mark` - Update read/starred flags
- `move`, `delete` - Folder operations
- `summarize` - Generate email digest
- `thread` - View conversation thread
- `rebuild-index` - Rebuild search indices

## Data Flow

### Email Fetch Flow
```
1. Agent calls 'fetch' command
2. CLI spawns background process (multiprocessing)
3. MailClient connects to IMAP
4. Emails retrieved and saved to SQLite
5. Attachments stored locally
6. Vector embeddings generated
7. Task status tracked in JSON file
```

### Email Search Flow
```
1. Agent calls 'search' with query
2. CLI routes to search type (FTS/vector/hybrid)
3. SQLite FTS5 or ChromaDB queried
4. Results formatted as JSON/Markdown
5. Returned to agent
```

### Email Send Flow
```
1. Agent calls 'send' or 'reply'
2. Body processed (markdown → HTML)
3. Signature appended (if configured)
4. Attachments processed (zip if folder)
5. MailClient sends via SMTP
```

## Storage Structure

```
mail_data/
├── {account_email}/
│   ├── mail_index.db      # SQLite database
│   ├── chroma_db/         # Vector embeddings
│   ├── attachments/       # Email attachments
│   │   └── {message_id}/
│   ├── eml/               # Raw email files
│   ├── json/              # Parsed email JSON
│   └── signature.md       # Account signature
└── tasks/                 # Async task tracking
```

## Configuration

**File:** `config.txt` (environment format)

**Account Configuration:**
- Email credentials (app password)
- IMAP/SMTP server settings
- SSL configuration

**Optional Features:**
- OpenAI API for embeddings
- Custom embedding models
- Storage paths

## Key Design Decisions

1. **Per-Account Isolation** - Each email account has separate storage to prevent data mixing
2. **Async Fetching** - Large fetches run in background to avoid blocking
3. **Hybrid Search** - Combines FTS precision with vector semantic understanding
4. **Markdown-to-HTML** - Automatic conversion for professional email formatting
5. **Safety Lock** - Send/reply operations require explicit confirmation

## Dependencies

- `imap-tools` - IMAP email operations
- `chromadb` - Vector database
- `sentence-transformers` - Local embeddings and reranking
- `jinja2` - Template rendering
- `markdown` - Markdown to HTML conversion
- `beautifulsoup4` - HTML parsing
