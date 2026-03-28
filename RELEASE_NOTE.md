# Mail Skill Release Notes

## [Latest Update] - Markdown to HTML Auto-Rendering for Outgoing Emails

### ✨ New Features & Improvements

#### 🎨 Beautiful Outgoing HTML Emails
- **Markdown Auto-Conversion**: The `send` and `reply` commands now automatically convert plain Markdown bodies into richly formatted HTML emails. You no longer need to manually write HTML; just let the AI output standard Markdown.
- **Tech-Style CSS Theme**: Introduced a built-in `email_theme.html.j2` template that applies a clean, modern, "tech" style CSS to the outgoing email. It features elegant zebra-striped tables with hover effects, clear header hierarchies with bottom borders, and cleanly styled blockquotes and code blocks.
- **Dependency Update**: Added `markdown` library to `requirements.txt` to support the new conversion engine.

---

## v1.3.0 (2026-03-27) - FTS5 Search, Thread Timeline & Markdown Rendering

### ✨ New Features & Improvements

#### 🔍 FTS5 Full-Text Search
- **SQLite FTS5 Integration**: Upgraded the local storage engine to use SQLite's FTS5 virtual tables. This provides lightning-fast, millisecond-level full-text search across email subjects, senders, and body content without relying on external indexing services.

#### 🧵 Email Thread Timeline
- **Conversation Tracking**: The fetch engine now parses and saves `In-Reply-To` and `References` headers.
- **New `thread` Command**: Introduced a dedicated CLI command to build and trace the complete lifecycle of a conversation (e.g., A replies to B, C replies to A). This constructs a chronological timeline of the entire email thread.

#### 🎨 Vertical Card Rendering
- **Jinja2 Templates**: Integrated the Jinja2 template engine to format CLI outputs.
- **Chat-Friendly Display**: The `read` and `thread` commands now output structured, vertical Markdown tables (cards). This includes clear fields for Sender, Recipient, CC, Date, Subject, Snippet, and Attachments, significantly improving readability within AI chat interfaces.

---

## v1.2.0 (2026-03-24) - Advanced Sending, AI Memory & Attachment Packing

### ✨ New Features & Improvements

#### 📧 Enhanced Email Fetching & Sending
- **Multi-Folder Fetching**: Fixed an issue where only the `INBOX` was fetched. You can now use `--folder ALL` to fetch emails from all server directories (crucial for users with server-side routing rules) or pass a comma-separated list of folders (e.g., `--folder "INBOX,Sent"`). The fetch limit now applies per folder.
- **HTML Email Support**: Added the `--html-body` parameter to the `send` and `reply` commands, allowing the transmission of rich text HTML emails alongside plain text fallbacks.
- **Dedicated `reply` Command**: Introduced a native `reply` command that automatically sets up `In-Reply-To` and `References` headers to maintain email threads. It supports replying to just the sender or to everyone (`--all`).
- **Multiple Recipients**: Upgraded the `--to`, `--cc`, and `--bcc` arguments in CLI to accept multiple email addresses (space-separated lists).

#### 🗂️ Smart Attachment Handling
- **Folder Zipping**: You can now pass folder paths directly to the `--attach` parameter. The system will automatically compress the folder into a `.zip` file before attaching it.
- **Unified Zip Packing**: Introduced the `--zip-as` parameter. When provided, it takes all specified files and folders, packs them into a single zip archive with the specified name, and attaches that single file to the email.

#### 🧠 AI Persistent Memory Architecture
- **Isolated Memory Store**: Created a dedicated `references/` directory to store context that the Agent should never forget across sessions.
- **Contacts & Preferences**: Agent uses `references/MEMORY.md` to memorize and retrieve user preferences and important contact aliases (e.g., "Boss's email").
- **Account-Specific Signatures**: Email signatures are now strictly tied to their respective email accounts. They are stored in `mail_data/<account_email>/signature.md`. The CLI automatically reads this file and appends the signature to both plain text and HTML bodies during `send` and `reply` commands, preventing cross-account signature mix-ups.

---

## v1.1.0 (2026-03-22)
- **Feature**: **Multi-Account Storage Isolation**. Added support for configuring multiple email accounts simultaneously. Data (EML, JSON, attachments, and SQLite databases) is now strictly isolated into separate folders based on the email address, preventing data mixing.
- **Bug Fix**: **Netease Mail Compatibility**. Fixed `Unsafe Login` and `[Errno 61] Connection refused` errors when logging into Netease email servers (163.com, 126.com, yeah.net) via IMAP by properly sending the `ID` command before authentication.
- **Chore**: Excluded internal/draft files (`idea.md`, `163邮箱故障排查指南.md`) from the distribution package to ensure a clean release.

## v1.0.1 (2026-03-21)
- **Bug Fix**: Fixed an issue where `imap_uid` was not saved to the local database, which caused server-side operations (`move`, `mark`, `delete`) to fail.
- **Enhancement**: Added automatic folder creation to the `move` command. If the destination folder does not exist on the server, it will be created before moving the email.

## v1.0.0 (2026-03-21)

🎉 **Initial Release: Mail Skill for AI Agents**

This is the first official release of the Mail Skill, designed specifically to empower AI Agents (OpenClaw, Claude Code, Trae, WorkBuddy, OpenCode, etc.) with robust, secure, and intelligent email management capabilities.

### ✨ Key Features

- **Secure Local Storage**:
  - Emails (EML & JSON) and attachments are downloaded and stored entirely locally.
  - No third-party servers; your credentials and data remain strictly on your machine.
- **Comprehensive Email Operations**:
  - `fetch`: Asynchronously pull emails via IMAP with idempotency (prevents duplicate downloads based on `message_id`).
  - `search`: Millisecond-level local search via a lightweight SQLite index.
  - `read`: Access full email body content and attachment paths.
  - `send`: Send new emails, reply, or forward via SMTP.
  - `mark` / `move` / `delete`: Manage inbox organization (mark read/unread, star, move to folders, delete).
- **Intelligent Summarization**:
  - `summarize`: A built-in command that automatically categorizes fetched emails into a professional Markdown report.
  - Auto-extracts verification codes, flags important emails, highlights action-required threads, and groups routine notifications.
- **Agent-Optimized Workflow**:
  - Async fetching with a progress polling mechanism (`fetch-status`) to prevent Agent timeouts on large mailboxes.
  - Safety confirmations for bulk operations (e.g., fetching >100 emails).
  - Included `SKILL.md` perfectly instructs the LLM on how to orchestrate these tools seamlessly.

### 🛠️ Technical Details
- Built with Python (`imap-tools`, `beautifulsoup4`).
- Configuration managed via `.env` file (supports multi-account setups).
- CLI-based architecture (`mail_cli.py`) ensures maximum compatibility across different Agent execution environments.
