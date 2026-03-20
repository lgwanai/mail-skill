---
name: mail-skill
description: Comprehensive email management skill. Use this skill when the user wants to fetch, search, read, send, reply to, move, delete, mark, or summarize emails. It supports multiple accounts (IMAP/SMTP) and manages emails via a local SQLite index to avoid duplicate fetching and improve search performance.
---

# Mail Management Skill

This skill provides a robust command-line interface (`scripts/mail_cli.py`) for managing emails across multiple accounts.

## Core Capabilities
- **Fetch**: Retrieve emails via IMAP and save them locally (.eml, .json, and SQLite index). Skips already downloaded emails based on `message_id`.
- **Search**: Query the local database for fast retrieval based on sender, subject, content, and date.
- **Read**: View the full content of an email, including its text and attachment metadata.
- **Send/Reply/Forward**: Send new emails or reply/forward existing ones via SMTP.
- **Manage**: Mark as read/starred, move between folders, or delete emails.
- **Summarize**: Since the skill provides full email text, you (Claude/Trae) can use your own intelligence to summarize the content, extract to-dos, or identify key dates.

## Workflow

### 1. Initial Setup
The user must provide an `.env` file in the root directory (or use `example.env` as a template). Ensure `python-dotenv`, `imap-tools`, `beautifulsoup4` are installed (`pip install -r requirements.txt`).

### 2. Fetching Emails
Fetching emails is an asynchronous process because it can take time. When you run the `fetch` command, it will return a `task_id` immediately.

```bash
./scripts/mail_cli.py fetch --limit 50 --days 7
```
*Note: If you need to fetch more than 100 emails, you MUST append the `--confirm` flag, and you should ask the user for confirmation first.*

Check the status of the fetch task using the returned `task_id`:
```bash
./scripts/mail_cli.py fetch-status "<task_id>"
```
Wait a few seconds and poll the status until it returns `"status": "completed"`. Once completed, **you MUST immediately use the `summarize` command to generate a professional report for the user**, passing the `task_id` so it only summarizes the newly fetched emails:

```bash
./scripts/mail_cli.py summarize --task-id "<task_id>"
```

### 3. Summarizing Emails
Generate a professional, categorized Markdown report of emails (overall stats, verification codes, important emails, action required, and others):
```bash
./scripts/mail_cli.py summarize --task-id "<task_id>"
```
If you just want to summarize recent emails without a specific task:
```bash
./scripts/mail_cli.py summarize --limit 20
```

### 4. Searching Emails
Search locally first. This is much faster and doesn't hit the server:
```bash
./scripts/mail_cli.py search --query "meeting" --limit 10
./scripts/mail_cli.py search --sender "boss@company.com" --is-read 0
```

### 5. Reading an Email
To read the full text and get attachment info, use the `message_id` from the search results:
```bash
./scripts/mail_cli.py read "<message_id>"
```

### 6. Sending Emails
```bash
./scripts/mail_cli.py send --to "recipient@example.com" --subject "Hello" --body "Message body" --attach "path/to/file1" "path/to/file2"
```

### 7. Managing Emails
- **Mark**: `./scripts/mail_cli.py mark "<message_id>" --read 1 --starred 1`
- **Move**: `./scripts/mail_cli.py move "<message_id>" "Archive"`
- **Delete**: `./scripts/mail_cli.py delete "<message_id>"`

### 8. Exporting
Export local database for analysis:
```bash
./scripts/mail_cli.py export --format csv --output emails.csv
```

## Best Practices
- **Always Search Local First**: Do not fetch unless the user explicitly asks to "check for new emails" or if a local search yields no results.
- **Handling Replies**: To reply, first `read` the original email to get context and sender, then use `send` with `Re: <subject>` and the recipient's address.
- **Smart Summarization**: Use the `summarize` command for quick professional reports. For deeper analysis of a single thread, use `read` and analyze the content directly.
