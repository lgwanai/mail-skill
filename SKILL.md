---
name: mail-skill
description: Comprehensive email management skill. Use this skill when the user wants to fetch, search, read, send, reply to, move, delete, mark, or summarize emails. It supports multiple accounts (IMAP/SMTP), manages emails via a local SQLite index to avoid duplicate fetching, and manages account-specific email signatures (set/save signatures).
---

# Mail Management Skill

This skill provides a robust command-line interface (`scripts/mail_cli.py`) for managing emails across multiple accounts.

## Core Capabilities
- **Fetch**: Retrieve emails via IMAP and save them locally (.eml, .json, and SQLite index). Skips already downloaded emails based on `message_id`. Extracts `In-Reply-To` and `References` for thread building.
- **Search (FTS5)**: Query the local database using SQLite FTS5 for fast full-text retrieval based on sender, subject, and body content.
- **Read**: View the full content of an email, rendered via Jinja2 into a clean vertical Markdown card, including its text and attachment metadata.
- **Thread Timeline**: Use the `thread` command to build and display a full conversation timeline (A→B→C→D) based on email references, rendered vertically for easy chat-interface reading.
- **Send/Reply/Forward**: Send new emails or reply/forward existing ones via SMTP.
- **Manage**: Mark as read/starred, move between folders, or delete emails.
- **Summarize**: Since the skill provides full email text, you (Claude/Trae) can use your own intelligence to summarize the content, extract to-dos, or identify key dates.
- **Set Signature**: Manage and store the user's email signature persistently per account in `mail_data/<email>/signature.md`. The CLI will automatically append it to outgoing emails.

## Workflow

### 1. Initial Setup
The user must provide an `.env` file in the root directory (or use `example.env` as a template). Ensure `python-dotenv`, `imap-tools`, `beautifulsoup4` are installed (`pip install -r requirements.txt`).

### 2. Fetching Emails
Fetching emails is an asynchronous process because it can take time. When you run the `fetch` command, it will return a `task_id` immediately.

```bash
./scripts/mail_cli.py fetch --limit 50 --days 7
```
*Note: By default, it only fetches from `INBOX`. If you need to fetch from all folders (e.g., if the user has server-side routing rules), use `--folder ALL`. You can also specify multiple folders like `--folder "INBOX,Sent"`. The `--limit` applies per folder. If you need to fetch more than 100 emails per folder, you MUST append the `--confirm` flag, and you should ask the user for confirmation first.*

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
**Important Search Flags**:
- **Semantic / Fuzzy Search**: If the user is asking to find emails by fuzzy concepts, ideas, or vague descriptions (e.g., "find the email about the project launch last week"), you MUST use the `--hybrid` flag. This combines keyword search with vector semantic search and reranks the results for high accuracy.
```bash
./scripts/mail_cli.py search --query "project launch" --hybrid --limit 5
```
- **Rebuilding Index**: If the user mentions that search is empty but emails exist (e.g., they fetched emails before the search features were added), run the `rebuild-index` command to sync all old emails into the FTS5 and Vector databases:
```bash
./scripts/mail_cli.py rebuild-index --account "<email_account>"
```

### 5. Reading an Email
To read the full text and get attachment info, use the `message_id` from the search results. The output is formatted as a vertical Markdown table for easy reading in chat interfaces:
```bash
./scripts/mail_cli.py read "<message_id>" --account "<email_account>"
```

### 6. Viewing an Email Thread
To view the full context of a conversation (A→B→C→D) based on a specific email, use the `thread` command. It traces `In-Reply-To` and `References` headers and outputs a chronological vertical table:
```bash
./scripts/mail_cli.py thread "<message_id>" --account "<email_account>"
```

### 7. Sending Emails
```bash
./scripts/mail_cli.py send --to "recipient@example.com" --subject "Hello" --body "Message body" --attach "path/to/file1.txt" "path/to/folder1"
```
**🚨 CRITICAL SENDING RULE**: Before you execute the `send` or `reply` command, you MUST present the complete draft of the email (including recipients, subject, and the exact body text) to the user and ask for their explicit confirmation. Do not send the email until the user says "Yes", "Looks good", "Send it", etc.

To send an HTML email, provide the `--html-body` parameter:
```bash
./scripts/mail_cli.py send --to "recipient@example.com" --subject "Hello" --body "Plain text fallback" --html-body "<h1>Hello</h1><p>Message body</p>"
```
To pack multiple files and/or folders into a single zip file before sending, use `--zip-as`:
```bash
./scripts/mail_cli.py send --to "recipient@example.com" --subject "Docs" --body "Here are the files" --attach "file1.txt" "folder2" --zip-as "project_docs.zip"
```

### 8. Managing Emails
- **Mark**: `./scripts/mail_cli.py mark "<message_id>" --read 1 --starred 1 --account "<email_account>"`
- **Move**: `./scripts/mail_cli.py move "<message_id>" "Archive" --account "<email_account>"`
- **Delete**: `./scripts/mail_cli.py delete "<message_id>" --account "<email_account>"`

### 9. Exporting
Export local database for analysis:
```bash
./scripts/mail_cli.py export --format csv --output emails.csv --account "<email_account>"
```

### 10. Managing Email Signatures
When the user asks you to "set my email signature", "save this signature", or "use this as my signature":
1. First, determine which account they are referring to. If they don't specify, ask them or check `.env` / `references/MEMORY.md` for the default account.
2. The signature file for an account MUST be stored at `mail_data/<safe_email_address>/signature.md` (where `<safe_email_address>` replaces `@` with `_at_`, `.` with `_`, and removes any other special characters except `-` and `_`). For example, `test@example.com` becomes `test_at_example_com`.
3. Open and edit this specific `mail_data/<safe_email_address>/signature.md` file using your file writing/editing tools. If the directory doesn't exist, create it.
4. Save the exact signature content into the file.
5. Confirm to the user that their signature has been saved for that specific account and will be automatically used by the CLI in future emails.



## Best Practices
- **Always Search Local First**: Do not fetch unless the user explicitly asks to "check for new emails" or if a local search yields no results.
- **Mandatory Send Confirmation**: Never assume a drafted email is perfect. Always show the draft and wait for user confirmation before executing `./scripts/mail_cli.py send` or `reply`.
- **Handling Replies**: Use the `reply` command. It automatically handles the `In-Reply-To` headers, sets the `To` / `Cc` addresses correctly, and prepends `Re:` to the subject. Use `--all` to reply to all original senders and CCs. Example: `./scripts/mail_cli.py reply "<message_id>" --body "My reply" --all`
- **Smart Summarization**: Use the `summarize` command for quick professional reports. For deeper analysis of a single thread, use `read` and analyze the content directly.
- **Persistent Memory (CRITICAL)**: 
  - ALWAYS read `references/MEMORY.md` to get user's important contacts (like boss's email) and preferences at the start of your task.
  - DO NOT manually append signatures to the `--body` argument when calling `send` or `reply`. The CLI will automatically read the account's `signature.md` and append it for you.
  - Whenever the user tells you to remember a new contact or preference, you MUST edit `references/MEMORY.md`. Whenever they tell you to save a signature, edit the account's `signature.md` as described in section 9.
