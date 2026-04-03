# Architecture Patterns: Mail Skill v2.0 Intelligent Enhancement

**Domain:** Email management system with intelligent search, classification, and attachment serving
**Researched:** 2026-04-04
**Confidence:** MEDIUM (based on codebase analysis and established patterns; WebSearch unavailable for verification)

## Recommended Architecture

### System Overview

```
+------------------------------------------------------------------+
|                        AI Agent (CLI)                             |
+------------------------------------------------------------------+
                               |
                               v
+------------------------------------------------------------------+
|                     mail_cli.py (Entry Point)                     |
|  - Command routing (existing + new commands)                      |
|  - Async task management                                          |
|  - Output formatting (JSON/Markdown)                              |
+------------------------------------------------------------------+
                               |
        +----------------------+----------------------+
        |                      |                      |
        v                      v                      v
+---------------+    +------------------+    +------------------+
|  MailClient   |    |  MailDatabase    |    | NEW: NLU Layer   |
|  (existing)   |    |  (existing)      |    |  QueryParser     |
+---------------+    +------------------+    +------------------+
        |                      |                      |
        v                      v                      |
+---------------+    +------------------+             |
| IMAP/SMTP     |    | SQLite + FTS5 +  |<------------+
| Servers       |    | ChromaDB         |
+---------------+    +------------------+
                              |
        +---------------------+---------------------+
        |                     |                     |
        v                     v                     v
+---------------+    +------------------+    +------------------+
| NEW:          |    | NEW:             |    | NEW:             |
| Attachment    |    | Classification   |    | Template         |
| Server        |    | Engine            |    | Manager          |
| (HTTP)        |    |                   |    |                  |
+---------------+    +------------------+    +------------------+
```

### New Components Integration

The v2.0 enhancements add four major components that integrate with the existing architecture:

1. **NLU Query Layer** - Natural language understanding for search
2. **Classification Engine** - Email importance/category classification
3. **Attachment Server** - Local HTTP server for file preview/download
4. **Template Manager** - Reply template storage and retrieval

---

## Component Boundaries

### Component 1: NLU Query Layer (NEW)

**File:** `scripts/mail_manager/query_parser.py`

**Responsibility:** Parse natural language queries into structured search criteria

**Communicates With:**
- Receives: Raw query string from CLI
- Returns: Structured SearchCriteria object to MailDatabase

**Interface:**
```python
@dataclass
class SearchCriteria:
    """Structured search parameters extracted from natural language"""
    keywords: list[str]           # Free-text keywords
    sender: str | None            # Parsed sender email/name
    recipient: str | None         # Parsed recipient
    date_from: datetime | None    # Parsed start date
    date_to: datetime | None      # Parsed end date
    date_relative: str | None     # "last week", "yesterday", etc.
    has_attachment: bool | None   # Attachment presence
    folder: str | None            # Folder filter
    importance: str | None        # "important", "urgent"
    original_query: str           # Preserve original for vector search

class QueryParser:
    def __init__(self, llm_client: LLMClient | None = None):
        """Initialize with optional LLM for complex parsing"""

    def parse(self, query: str) -> SearchCriteria:
        """Parse natural language query into structured criteria"""
```

**Design Decision:** Use rule-based parsing first (regex patterns for dates, senders), fall back to LLM for complex queries. This balances speed and accuracy.

### Component 2: Classification Engine (NEW)

**File:** `scripts/mail_manager/classifier.py`

**Responsibility:** Classify emails by importance and category

**Communicates With:**
- Receives: Email data from MailDatabase
- Stores: Classification results in SQLite (new columns)
- Reads: Classification rules from config

**Interface:**
```python
@dataclass
class Classification:
    """Email classification result"""
    importance: str           # "critical", "high", "normal", "low"
    category: str             # "work", "personal", "notification", "promo"
    confidence: float         # 0.0 to 1.0
    reasoning: str | None     # Optional explanation

class EmailClassifier:
    def __init__(self, db: MailDatabase, rules_path: str | None = None):
        """Initialize classifier with database and optional rules file"""

    def classify(self, email: dict) -> Classification:
        """Classify a single email"""

    def classify_batch(self, emails: list[dict]) -> list[Classification]:
        """Classify multiple emails efficiently"""

    def reclassify_all(self) -> int:
        """Re-classify all emails, return count updated"""
```

**Database Extension:**
```sql
ALTER TABLE emails ADD COLUMN importance TEXT DEFAULT 'normal';
ALTER TABLE emails ADD COLUMN category TEXT DEFAULT 'uncategorized';
ALTER TABLE emails ADD COLUMN classification_confidence REAL;
```

### Component 3: Attachment Server (NEW)

**File:** `scripts/mail_manager/attachment_server.py`

**Responsibility:** Serve local attachments via HTTP for preview/download

**Communicates With:**
- Receives: Start/stop commands from CLI
- Reads: Attachment files from local storage
- Logs: Access history for debugging

**Interface:**
```python
class AttachmentServer:
    def __init__(self, storage_root: str, port: int = 0):
        """
        Initialize server.
        port=0 means auto-select available port
        """

    def start(self) -> int:
        """Start server in background thread, return actual port"""

    def stop(self) -> None:
        """Stop the server"""

    def get_url(self, message_id: str, filename: str) -> str:
        """Generate download URL for an attachment"""

    @property
    def is_running(self) -> bool:
        """Check if server is active"""
```

**Implementation Approach:**
- Use Python's built-in `http.server` with `ThreadingHTTPServer`
- Auto-select port (try 8080, then 8081-8099)
- Support range requests for large files
- Support content-type headers for browser preview

### Component 4: Template Manager (NEW)

**File:** `scripts/mail_manager/templates.py`

**Responsibility:** Manage reply templates for quick responses

**Communicates With:**
- Reads: Template files from filesystem
- Returns: Template content to CLI for composition

**Interface:**
```python
@dataclass
class ReplyTemplate:
    """A reply template"""
    id: str                   # Template identifier
    name: str                 # Human-readable name
    subject: str | None       # Optional subject template
    body: str                 # Body template with placeholders
    tags: list[str]           # Tags for filtering
    variables: list[str]      # Required variables (e.g., ["name", "date"])

class TemplateManager:
    def __init__(self, templates_dir: str):
        """Initialize with templates directory"""

    def list_templates(self, tag: str | None = None) -> list[ReplyTemplate]:
        """List available templates, optionally filtered by tag"""

    def get_template(self, template_id: str) -> ReplyTemplate | None:
        """Get a specific template"""

    def render(self, template_id: str, variables: dict) -> str:
        """Render template with provided variables"""

    def create_template(self, template: ReplyTemplate) -> None:
        """Create a new template file"""
```

---

## Data Flow

### Intelligent Search Flow (NEW)

```
1. Agent calls 'smart-search "上周王总的预算邮件"'
2. CLI invokes QueryParser.parse()
   a. Regex extracts date patterns ("上周" -> last week)
   b. Regex extracts sender pattern ("王总")
   c. Keywords extracted ("预算邮件")
   d. Returns SearchCriteria object
3. CLI calls MailDatabase.search_intelligent(criteria)
   a. Build SQL WHERE clause from structured criteria
   b. Execute FTS5 search with keywords
   c. Combine with vector search using keywords
   d. Rerank results
4. Results formatted and returned to agent
```

### Classification Flow (NEW)

```
1. Triggered by:
   - New email fetch (automatic classification)
   - Manual 'classify' command
   - Batch reclassification
2. Classifier receives email data
3. Apply rule-based classification first:
   - Sender-based rules (known senders)
   - Keyword-based rules (urgent, important)
   - Pattern-based rules (verification codes)
4. If confidence low, optionally use LLM
5. Store classification in database
6. Update FTS index with classification metadata
```

### Attachment Preview Flow (NEW)

```
1. Agent calls 'attachments <message_id>'
2. CLI checks if AttachmentServer is running
   a. If not, start server on auto-selected port
   b. Store port in memory/env for session
3. For each attachment:
   a. Generate URL: http://localhost:{port}/{account}/{message_id}/{filename}
   b. Format as clickable link (terminal-compatible)
4. User clicks link -> browser opens -> file downloads/previews
```

### Template Reply Flow (NEW)

```
1. Agent calls 'reply <message_id> --template <template_id>'
2. CLI loads template from TemplateManager
3. CLI extracts variables from original email (sender name, date, etc.)
4. CLI renders template with variables
5. User reviews/edits (optional)
6. Send via existing MailClient.send_email()
```

---

## Patterns to Follow

### Pattern 1: Lazy Component Initialization

**What:** Initialize expensive components only when needed

**When:** AttachmentServer, LLM-based classifiers

**Why:** Avoid startup overhead and resource usage when features not used

**Example:**
```python
class AttachmentServerManager:
    _instance: AttachmentServer | None = None

    @classmethod
    def get_server(cls, storage_root: str) -> AttachmentServer:
        if cls._instance is None or not cls._instance.is_running:
            cls._instance = AttachmentServer(storage_root)
            cls._instance.start()
        return cls._instance
```

### Pattern 2: Extensible Classification Rules

**What:** Rule-based classification with configurable rules file

**When:** Email classification

**Why:** Allows users to customize without code changes

**Example:**
```yaml
# config/classification_rules.yaml
rules:
  - name: "Critical Senders"
    type: sender_match
    senders: ["boss@company.com", "hr@company.com"]
    importance: critical

  - name: "Verification Codes"
    type: keyword_match
    keywords: ["验证码", "verification code", "安全码"]
    category: notification
    importance: high
```

### Pattern 3: Structured Query Result

**What:** Return structured objects from parsers, not dictionaries

**When:** QueryParser results, Classification results

**Why:** Type safety, IDE support, explicit interfaces

**Example:**
```python
# Use dataclass with type annotations
@dataclass
class SearchCriteria:
    keywords: list[str]
    sender: str | None
    # ...

# NOT
def parse(query: str) -> dict:  # Unclear structure
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Blocking HTTP Server in Main Thread

**What:** Running attachment server in main thread blocks CLI

**Why bad:** CLI becomes unresponsive, cannot handle other commands

**Instead:** Use ThreadingHTTPServer in background thread, or separate process

```python
# WRONG
httpd = HTTPServer(('', port), Handler)
httpd.serve_forever()  # Blocks!

# CORRECT
httpd = ThreadingHTTPServer(('', port), Handler)
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()
```

### Anti-Pattern 2: Storing Classification Without Persistence

**What:** Computing classification on-the-fly without storing

**Why bad:** Recomputes every time, slow for large datasets

**Instead:** Store in database with index, recompute only on demand

### Anti-Pattern 3: Tight Coupling to LLM

**What:** Requiring LLM for all NLU operations

**Why bad:** Adds latency, cost, and external dependency

**Instead:** Rule-based first, LLM fallback for complex queries only

---

## Scalability Considerations

| Concern | At 100 emails | At 10K emails | At 100K emails |
|---------|---------------|---------------|----------------|
| Classification | Real-time, in-memory | Batch processing, background | Async queue + background worker |
| Search (FTS) | Instant | < 100ms | < 500ms with proper indexing |
| Search (Vector) | Instant | < 200ms | < 1s, consider partitioning |
| Attachment Server | Single-threaded OK | Thread pool | Consider separate service |
| Template Management | File-based OK | File-based OK | Consider database storage |

---

## Integration Points with Existing Code

### CLI (`mail_cli.py`) Changes

Add new commands:
```python
# New subparsers to add
smart_search_p = subparsers.add_parser("smart-search", help="Natural language search")
smart_search_p.add_argument("query", help="Natural language query")

classify_p = subparsers.add_parser("classify", help="Classify email importance")
classify_p.add_argument("message_id", help="Message to classify")

attachments_p = subparsers.add_parser("attachments", help="List attachments with preview URLs")
attachments_p.add_argument("message_id")

template_p = subparsers.add_parser("templates", help="Manage reply templates")
# ... subcommands: list, show, create
```

### Database (`db.py`) Changes

```python
# Add to _init_db()
cursor.execute('ALTER TABLE emails ADD COLUMN importance TEXT DEFAULT "normal"')
cursor.execute('ALTER TABLE emails ADD COLUMN category TEXT DEFAULT "uncategorized"')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_importance ON emails(importance)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON emails(category)')

# New method
def search_intelligent(self, criteria: SearchCriteria) -> list[dict]:
    """Search using structured criteria from NLU layer"""
```

### Storage Structure Update

```
mail_data/
├── {account_email}/
│   ├── mail_index.db           # Extended with classification columns
│   ├── chroma_db/              # Existing
│   ├── attachments/            # Existing, now served via HTTP
│   ├── eml/                    # Existing
│   ├── json/                   # Existing
│   ├── signature.md            # Existing
│   └── templates/              # NEW: Reply templates
│       ├── acknowledge.md
│       ├── follow_up.md
│       └── ...
└── server_state.json           # NEW: Track running HTTP server
```

---

## Suggested Build Order

Based on dependencies and risk:

### Phase 1: Foundation (No External Dependencies)
1. **Template Manager** - Simplest, file-based, no external dependencies
   - Creates new module
   - Extends CLI
   - Low risk, immediate value

### Phase 2: Database Enhancement
2. **Classification Engine (Schema + Basic Rules)** - Extends database
   - Schema migration
   - Rule-based classification (no LLM)
   - CLI commands for classification
   - Enables better email organization

### Phase 3: Network Component
3. **Attachment Server** - New capability, networking
   - HTTP server implementation
   - Port management
   - CLI integration
   - Higher risk, requires testing

### Phase 4: Intelligence Layer
4. **NLU Query Parser** - Most complex
   - Rule-based date/sender extraction
   - Integration with existing search
   - Optional LLM integration later
   - Highest complexity, but builds on all previous

### Phase 5: Enhancement
5. **LLM Integration (Optional)** - Enhancement to classification and NLU
   - LLM client abstraction
   - Fallback from rules to LLM
   - Configuration for API keys

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Component Boundaries | HIGH | Clear separation from existing code, minimal coupling |
| Data Flow | HIGH | Follows existing patterns, logical progression |
| Build Order | HIGH | Dependencies correctly identified |
| Attachment Server | MEDIUM | Network code has edge cases, needs testing |
| Classification Engine | MEDIUM | Rule-based straightforward, LLM integration may need refinement |
| NLU Query Parser | MEDIUM | Complex domain, Chinese NLU has unique challenges |

---

## Gaps to Address

1. **Chinese NLU Specifics** - Date parsing ("上周", "大前天") and name extraction may need Chinese-specific libraries (e.g., jieba, pkuseg)

2. **Attachment Server Security** - Should localhost-only binding be enforced? Should there be token-based authentication?

3. **Template Variables** - What standard variables should be auto-populated from original email?

4. **Classification Persistence** - Should reclassification preserve history?

5. **Server State Management** - How to handle server port persistence across CLI invocations? (Suggestion: write to `server_state.json`)

---

## Sources

- Existing codebase analysis (`scripts/mail_cli.py`, `scripts/mail_manager/*.py`)
- Python `http.server` documentation (built-in module)
- ChromaDB integration patterns from existing `db.py`
- Project requirements from `.planning/PROJECT.md`
