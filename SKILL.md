---
name: mail-skill
description: >
  Comprehensive email management skill for AI agents. Fetches, searches, reads,
  sends, and summarizes emails via IMAP/SMTP. Features include semantic search
  with vector embeddings, AI-powered replies, email classification, thread
  tracking, and attachment preview. Supports multiple accounts with isolated
  storage. Triggers: "check my email", "search emails", "send email", "reply to",
  "email summary", "fetch emails", "mail from", "inbox".
---

# Mail Skill

A powerful email management skill that acts as your personal email assistant.

## When to Activate

- User asks to check, fetch, or read emails
- User wants to search emails (keyword or natural language)
- User needs to send, reply to, or forward emails
- User requests email summaries or reports
- User mentions email threads or conversations
- User asks about attachments in emails
- User wants to organize or classify emails

## Quick Start

```bash
# Configure via web UI (first time)
python scripts/mail_cli.py config

# Fetch latest emails
python scripts/mail_cli.py fetch --days 7

# Search emails
python scripts/mail_cli.py search --query "project update"

# Send an email
python scripts/mail_cli.py send --to recipient@example.com --subject "Hello" --body "Message content"
```

## Core Commands

### Fetch Emails

```bash
# Fetch recent emails (default: last 7 days, max 50)
python scripts/mail_cli.py fetch

# Fetch from specific folder
python scripts/mail_cli.py fetch --folder INBOX

# Fetch from all folders
python scripts/mail_cli.py fetch --folder ALL

# Fetch more emails (requires confirmation)
python scripts/mail_cli.py fetch --limit 200 --confirm

# Fetch only unread
python scripts/mail_cli.py fetch --unread

# Check fetch task status (async)
python scripts/mail_cli.py fetch-status <task_id>
```

**Output**: JSON with `task_id` for async tracking. Emails are stored in `./mail_data/<account>/`.

### Search Emails

```bash
# Full-text search
python scripts/mail_cli.py search --query "budget report"

# Semantic search (vector embeddings)
python scripts/mail_cli.py search --query "project timeline" --vector

# Hybrid search (FTS + Vector with reranking)
python scripts/mail_cli.py search --query "meeting notes" --hybrid

# Filter by attributes
python scripts/mail_cli.py search --sender "boss@company.com" --folder INBOX --is-read 0

# Filter by classification
python scripts/mail_cli.py search --importance high --category work

# Filter by tag
python scripts/mail_cli.py search --tag "follow-up"
```

**Output**: JSON with `count` and `results` array containing `message_id`, `subject`, `sender`, `date`, `snippet`.

### Natural Language Search

```bash
# Smart search understands natural language
python scripts/mail_cli.py smart-search "emails from John last week about budget"
python scripts/mail_cli.py smart-search "unread emails from boss yesterday"
python scripts/mail_cli.py smart-search "emails about project deadline this month"
```

**Output**: JSON with `parsed_query` (extracted date range, sender, keywords) and `results`.

### Read Email

```bash
# Read full email with enhanced Markdown formatting
python scripts/mail_cli.py read <message_id>

# Brief table view
python scripts/mail_cli.py read <message_id> --brief
```

**Output**: Markdown-formatted email with sender, recipients, date, subject, body, attachments, and thread context.

### Send Email

```bash
# Basic send
python scripts/mail_cli.py send --to recipient@example.com --subject "Subject" --body "Body text"

# With CC/BCC
python scripts/mail_cli.py send --to main@example.com --cc other@example.com --subject "Subject" --body "Body"

# With attachments
python scripts/mail_cli.py send --to recipient@example.com --subject "Report" --body "See attached" --attach ./report.pdf

# Zip folders as attachment
python scripts/mail_cli.py send --to recipient@example.com --subject "Files" --body "Here" --attach ./folder --zip-as "files.zip"
```

**Note**: Body text supports Markdown and is automatically converted to styled HTML.

### Reply to Email

```bash
# Reply to sender
python scripts/mail_cli.py reply <message_id> --body "Reply content"

# Reply to all (sender + CC)
python scripts/mail_cli.py reply <message_id> --body "Reply to all" --all

# With attachments
python scripts/mail_cli.py reply <message_id> --body "See attached" --attach ./file.pdf
```

**Note**: Original email history is appended automatically. Signature is added if `signature.md` exists.

### Thread View

```bash
# Show email thread timeline
python scripts/mail_cli.py thread <message_id>

# With LLM-generated summary
python scripts/mail_cli.py thread <message_id> --summary
```

**Output**: Timeline of related emails with sender/recipient matching.

### Email Summarization

```bash
# Summarize recent emails (categorized)
python scripts/mail_cli.py summarize --limit 10

# Summarize emails from a fetch task
python scripts/mail_cli.py summarize --task-id <task_id>
```

**Output**: Markdown report with categories:
- Verification codes (extracted codes highlighted)
- Important emails (priority keywords detected)
- Action required (reply/follow-up needed)
- Other regular emails

### Summary Report by Sender

```bash
# Generate report grouped by sender (last 7 days)
python scripts/mail_cli.py summary-report

# Custom date range
python scripts/mail_cli.py summary-report --date-from 2024-01-01 --date-to 2024-01-31

# Save to file
python scripts/mail_cli.py summary-report --output report.md
```

**Output**: Markdown report with sender-grouped emails and LLM-generated summaries.

## Email Management

### Mark as Read/Starred

```bash
# Mark as read
python scripts/mail_cli.py mark <message_id> --read 1

# Mark as unread
python scripts/mail_cli.py mark <message_id> --read 0

# Star/unstar
python scripts/mail_cli.py mark <message_id> --starred 1

# Batch mark
python scripts/mail_cli.py batch-mark --from-search "newsletter" --read 1
```

### Tags (Labels)

```bash
# Add tag
python scripts/mail_cli.py tag add <message_id> "follow-up"

# Remove tag
python scripts/mail_cli.py tag remove <message_id> "follow-up"

# List tags
python scripts/mail_cli.py tag list <message_id>

# Batch add tags
python scripts/mail_cli.py tag batch-add "important" --from-search "from:boss"
```

### Classification

```bash
# Classify single email
python scripts/mail_cli.py classify <message_id>

# Auto-classify all unclassified
python scripts/mail_cli.py classify --limit 100

# Manual reclassify
python scripts/mail_cli.py reclassify <message_id> --importance high --category work
```

**Categories**: `work`, `personal`, `notification`, `promo`, `uncategorized`
**Importance**: `critical`, `high`, `normal`, `low`

### Move/Delete

```bash
# Move to folder
python scripts/mail_cli.py move <message_id> Archive

# Delete email
python scripts/mail_cli.py delete <message_id>
```

## Attachments

### List Attachments

```bash
# List attachments with preview URLs
python scripts/mail_cli.py attachments --limit 50
```

**Output**: JSON with `preview_url` for each attachment (local HTTP server URL).

### Parse Attachment Content

```bash
# Parse attachments for specific email
python scripts/mail_cli.py parse-attachments --message-id <message_id>

# Parse all unprocessed attachments
python scripts/mail_cli.py parse-attachments --all
```

**Supported formats**: PDF, Excel (.xlsx/.xls), PowerPoint (.pptx), images (OCR via vision model), text files.

## AI Features

### AI-Generated Reply

```bash
# Generate and preview reply
python scripts/mail_cli.py ai-reply <message_id> --dry-run

# Generate with intent guidance
python scripts/mail_cli.py ai-reply <message_id> --intent "polite decline"

# Include thread context
python scripts/mail_cli.py ai-reply <message_id> --with-thread

# Send directly (with confirmation)
python scripts/mail_cli.py ai-reply <message_id>
```

**Flow**: Generates reply → Shows preview → Asks confirmation (y/n/e=edit) → Sends or cancels.

### Email Templates

```bash
# List templates
python scripts/mail_cli.py templates list

# Show template
python scripts/mail_cli.py templates show welcome

# Create template
python scripts/mail_cli.py templates create welcome --content "Hello {{name}}, ..." --required-vars name
```

## Configuration

Copy `example.config.txt` to `config.txt` and fill in your details:

```env
# Email Account
MAIL_ACCOUNT_1_EMAIL=your@email.com
MAIL_ACCOUNT_1_PASSWORD=your-app-password
MAIL_ACCOUNT_1_IMAP_SERVER=imap.gmail.com
MAIL_ACCOUNT_1_IMAP_PORT=993
MAIL_ACCOUNT_1_SMTP_SERVER=smtp.gmail.com
MAIL_ACCOUNT_1_SMTP_PORT=465
MAIL_ACCOUNT_1_USE_SSL=true

# AI Configuration (Optional - LLM and Embedding can use different providers)
# LLM_API_KEY=your_api_key
# LLM_API_BASE=https://api.deepseek.com/v1
# LLM_MODEL_NAME=deepseek-chat
# EMBEDDING_API_KEY=your_api_key
# EMBEDDING_API_BASE=https://api.siliconflow.cn/v1
# EMBEDDING_MODEL_NAME=BAAI/bge-large-zh-v1.5
# RERANKER_MODEL_NAME=BAAI/bge-reranker-base
```

## Data Storage

### Directory Structure

```
mail_data/
├── <account_sanitized>/         # Per-account storage
│   ├── mail_index.db           # Email index (SQLite + FTS5 + ChromaDB)
│   ├── eml/                    # Raw email files
│   ├── json/                   # Parsed email JSON
│   ├── attachments/            # Downloaded attachments
│   ├── signature.md            # Account signature (optional)
│   └── templates/              # Email templates (optional)
```

### Account Path Sanitization

Email addresses are sanitized for directory names:
- `user@example.com` → `user_at_example_com`
- Special characters removed, only alphanumeric, `-`, `_` kept

## Output Formats

All commands return JSON with consistent structure:

### Success Response

```json
{
  "status": "success",
  "message": "Operation completed",
  "data": { ... }
}
```

### Error Response

```json
{
  "status": "error",
  "error_code": "USER_EMAIL_NOT_FOUND",
  "message": "Email not found locally"
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `USER_EMAIL_NOT_FOUND` | Email/account not found |
| `USER_INVALID_PARAMETER` | Invalid input parameter |
| `USER_MISSING_PARAMETER` | Required parameter missing |
| `BIZ_ACCOUNT_NOT_CONFIGURED` | No email account configured |
| `SERVER_IMAP_CONNECTION_FAILED` | IMAP connection error |
| `SERVER_SMTP_SEND_FAILED` | SMTP send error |
| `SERVER_DATABASE_ERROR` | Database error |
| `INTERNAL_ERROR` | Internal server error |

## Search Capabilities

### Three Search Modes

1. **FTS (Full-Text Search)**: Fast keyword search using SQLite FTS5
2. **Vector Search**: Semantic similarity using OpenAI embeddings + ChromaDB
3. **Hybrid Search**: Combines FTS + Vector with cross-encoder reranking

### Rebuild Search Index

```bash
# Rebuild FTS5 and vector indices
python scripts/mail_cli.py rebuild-index
```

## Requirements

- Python 3.8+
- OpenAI API key (for AI features)
- Email account with IMAP/SMTP access

## Installation

```bash
pip install -r requirements.txt
```

## Troubleshooting

- **Config not found**: Run `python scripts/mail_cli.py config` to set up
- **IMAP connection failed**: Check server settings and app passwords
- **Search returns empty**: Run `rebuild-index` to rebuild search indices
- **Attachments not previewing**: Check if attachment server is running (auto-starts on demand)
