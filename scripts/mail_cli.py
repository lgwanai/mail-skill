#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import tempfile
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import markdown  # type: ignore[import-untyped]
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

# Ensure the parent directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mail_manager.client import MailClient
from mail_manager.db import MailDatabase
from mail_manager.errors import ErrorCodes, error_response, success_response
from mail_manager.query_parser import ParsedQuery, match_senders, parse_natural_query
from mail_manager.server import AttachmentServer, ServerState

if TYPE_CHECKING:
    from mail_manager.client import MailClient
    from mail_manager.db import MailDatabase

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Task tracking for async fetch
TASKS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mail_data", "tasks"
)
os.makedirs(TASKS_DIR, exist_ok=True)

# Sender list cache for smart-search performance optimization
_sender_cache: dict[str, tuple[float, list[str]]] = {}
CACHE_TTL = 300  # 5 minutes


def get_cached_senders(db: MailDatabase, account: str) -> list[str]:
    """Get unique senders from database with caching.

    Caches the sender list for 5 minutes to improve performance
    on repeated smart-search calls.

    Args:
        db: MailDatabase instance
        account: Account identifier for cache key

    Returns:
        list[str]: List of unique sender strings
    """
    cache_key = account
    now = time.time()
    if cache_key in _sender_cache:
        cached_time, senders = _sender_cache[cache_key]
        if now - cached_time < CACHE_TTL:
            return senders
    senders = db.get_unique_senders()
    _sender_cache[cache_key] = (now, senders)
    return senders


def load_config() -> dict[str, Any]:
    """Load configuration from config.txt file."""
    # Look for config.txt in the parent directory of scripts
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.txt"
    )
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv("config.txt")  # Try current directory

    config: dict[str, Any] = {
        "STORAGE_ROOT": os.getenv("MAIL_STORAGE_ROOT", "./mail_data"),
        "DB_PATH": os.getenv("MAIL_DB_PATH", "./mail_data/mail_index.db"),
        "ATTACHMENT_PATH": os.getenv("MAIL_ATTACHMENT_PATH", "./mail_data/attachments"),
        "ACCOUNTS": {},
    }

    # Parse accounts
    for key, value in os.environ.items():
        if key.startswith("MAIL_ACCOUNT_") and key.endswith("_EMAIL"):
            account_prefix = key[:-6]  # Remove _EMAIL

            config["ACCOUNTS"][value] = {
                "EMAIL": value,
                "PASSWORD": os.getenv(f"{account_prefix}_PASSWORD"),
                "IMAP_SERVER": os.getenv(f"{account_prefix}_IMAP_SERVER"),
                "IMAP_PORT": os.getenv(f"{account_prefix}_IMAP_PORT", "993"),
                "SMTP_SERVER": os.getenv(f"{account_prefix}_SMTP_SERVER"),
                "SMTP_PORT": os.getenv(f"{account_prefix}_SMTP_PORT", "465"),
                "USE_SSL": os.getenv(f"{account_prefix}_USE_SSL", "true"),
                "PREFIX": account_prefix,
            }

    return config


def get_client(config: dict[str, Any], email_account: str | None = None) -> MailClient:
    """Get a MailClient instance for the specified account."""
    if not config["ACCOUNTS"]:
        raise ValueError("No mail accounts configured in config.txt")

    if email_account and email_account in config["ACCOUNTS"]:
        account_config = config["ACCOUNTS"][email_account]
    else:
        # Use the first account
        account_config = list(config["ACCOUNTS"].values())[0]

    return MailClient(account_config)


def _process_attachments(
    attach_paths: list[str] | None, zip_as: str | None = None
) -> list[str] | None:
    """Process attachments: zip folders, or pack everything into one zip file."""
    if not attach_paths:
        return None

    final_attachments: list[str] = []
    temp_dir = tempfile.mkdtemp()

    if zip_as:
        if not zip_as.endswith(".zip"):
            zip_as += ".zip"
        zip_path = os.path.join(temp_dir, zip_as)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for path in attach_paths:
                if not os.path.exists(path):
                    logger.warning(f"Attachment path not found: {path}")
                    continue
                abs_path = os.path.abspath(path)
                if os.path.isfile(abs_path):
                    zipf.write(abs_path, arcname=os.path.basename(abs_path))
                elif os.path.isdir(abs_path):
                    parent_dir = os.path.dirname(abs_path)
                    for root, _dirs, files in os.walk(abs_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, parent_dir)
                            zipf.write(file_path, arcname=rel_path)
        final_attachments.append(zip_path)
    else:
        for path in attach_paths:
            if not os.path.exists(path):
                logger.warning(f"Attachment path not found: {path}")
                continue
            abs_path = os.path.abspath(path)
            if os.path.isfile(abs_path):
                final_attachments.append(abs_path)
            elif os.path.isdir(abs_path):
                dir_name = os.path.basename(abs_path) or "folder"
                zip_path = os.path.join(temp_dir, f"{dir_name}.zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    parent_dir = os.path.dirname(abs_path)
                    for root, _dirs, files in os.walk(abs_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, parent_dir)
                            zipf.write(file_path, arcname=rel_path)
                final_attachments.append(zip_path)

    return final_attachments


def _get_account_paths(config: dict[str, Any], email_address: str | None) -> dict[str, str]:
    """Generate isolated storage paths for a specific email account."""
    if not email_address:
        raise ValueError("Email address is required to get account paths")

    # Sanitize email address for directory name.
    # Replace special characters with underscore to match user's expected wuliang_at_chinamobile_com
    safe_email = email_address.replace("@", "_at_").replace(".", "_")
    # Remove any other characters that might be problematic, but keep alphanumeric, -, _, and @.
    safe_email = "".join(
        [c for c in safe_email if c.isalpha() or c.isdigit() or c in "-_"]
    ).rstrip()

    account_root = os.path.join(config["STORAGE_ROOT"], safe_email)

    return {
        "root": account_root,
        "db_path": os.path.join(account_root, "mail_index.db"),
        "attach_path": os.path.join(account_root, "attachments"),
        "eml_path": os.path.join(account_root, "eml"),
        "json_path": os.path.join(account_root, "json"),
        "signature_path": os.path.join(account_root, "signature.md"),
    }


def _get_template_env() -> Environment:
    """Get Jinja2 template environment."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tpl_dir = os.path.join(root, "references", "templates")
    return Environment(loader=FileSystemLoader(tpl_dir), autoescape=False)


def _render_table(template_name: str, context: dict[str, Any]) -> str:
    """Render a table template with the given context."""
    env = _get_template_env()
    tpl = env.get_template(template_name)
    return tpl.render(**context)


def _run_fetch_task(task_id: str, config: dict[str, Any], db_path: str, args: Any) -> None:
    """Run fetch task in background thread."""
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")

    def update_status(status: str, message: str = "", data: dict | None = None) -> None:
        info: dict[str, Any] = {
            "status": status,
            "message": message,
            "updated_at": datetime.now().isoformat(),
        }
        if data:
            info.update(data)
        with open(task_file, "w") as f:
            json.dump(info, f)

    try:
        client = get_client(config, args.account)
        paths = _get_account_paths(config, client.email)

        # Override db_path with isolated db_path
        db_path = paths["db_path"]

        # Ensure directories exist
        os.makedirs(paths["root"], exist_ok=True)
        os.makedirs(paths["attach_path"], exist_ok=True)
        os.makedirs(paths["eml_path"], exist_ok=True)
        os.makedirs(paths["json_path"], exist_ok=True)

        db = MailDatabase(db_path)
        update_status("running", f"Connecting and fetching emails for {client.email}...")

        # Fetch from server
        emails = client.fetch_emails(
            folder=args.folder,
            limit=args.limit,
            days_back=args.days,
            unread_only=args.unread,
            db_check_func=db.exists,
        )

        saved_count = 0
        fetched_ids = []
        for email_data in emails:
            # Save EML
            eml_filename = (
                "".join(
                    [
                        c
                        for c in email_data["message_id"]
                        if c.isalpha() or c.isdigit() or c in "-_."
                    ]
                ).rstrip()
                + ".eml"
            )
            eml_path = os.path.join(paths["eml_path"], eml_filename)
            with open(eml_path, "wb") as f:
                f.write(bytes(email_data["raw_email"]))
            email_data["local_path_eml"] = eml_path

            # Save attachments
            db_attachments = []
            if email_data["attachments"]:
                att_dir = os.path.join(
                    paths["attach_path"], email_data["message_id"].replace("/", "_")
                )
                os.makedirs(att_dir, exist_ok=True)

                for att in email_data["attachments"]:
                    if att.filename:
                        att_path = os.path.join(att_dir, att.filename)
                        with open(att_path, "wb") as f:
                            f.write(att.payload)
                        db_attachments.append(
                            {
                                "filename": att.filename,
                                "content_type": att.content_type,
                                "size": att.size,
                                "local_path": att_path,
                            }
                        )
            email_data["attachments"] = db_attachments

            # Save JSON
            json_filename = eml_filename.replace(".eml", ".json")
            json_path = os.path.join(paths["json_path"], json_filename)

            # Remove raw_email before saving JSON
            json_data = {k: v for k, v in email_data.items() if k not in ["raw_email", "html_body"]}
            # Convert datetime to string
            if "date" in json_data and isinstance(json_data["date"], datetime):
                json_data["date"] = json_data["date"].isoformat()

            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(json_data, jf, ensure_ascii=False, indent=2)
            email_data["local_path_json"] = json_path

            # Save to DB
            db.save_email(email_data)
            saved_count += 1
            fetched_ids.append(email_data["message_id"])

            # Update status periodically if many emails
            if saved_count % 10 == 0:
                update_status(
                    "running",
                    f"Saved {saved_count} of {len(emails)} emails...",
                    {"progress": saved_count, "total": len(emails)},
                )

        update_status(
            "completed",
            "Fetch completed successfully.",
            {"fetched_count": len(emails), "saved_count": saved_count, "fetched_ids": fetched_ids},
        )
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        update_status("failed", str(e))


def cmd_fetch(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Fetch emails from server to local database."""
    if args.limit > 100 and not args.confirm:
        print(
            json.dumps(
                {
                    "status": "requires_confirmation",
                    "message": f"You requested to fetch {args.limit} emails. This may take a long time. Please run the command again with --confirm to proceed.",
                }
            )
        )
        return

    task_id = str(uuid.uuid4())
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")

    # Initialize task file
    with open(task_file, "w") as f:
        json.dump(
            {
                "status": "starting",
                "message": "Initializing fetch task...",
                "updated_at": datetime.now().isoformat(),
            },
            f,
        )

    # Use multiprocessing to ensure it runs even if parent exits
    import multiprocessing

    p = multiprocessing.Process(
        target=_run_fetch_task, args=(task_id, config, config["DB_PATH"], args)
    )
    p.start()

    # Return immediately to the LLM
    print(
        json.dumps(
            {
                "status": "started",
                "task_id": task_id,
                "message": "Fetch task started in the background. Use the 'fetch-status' command to check progress.",
            }
        )
    )


def cmd_fetch_status(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Check status of a background fetch task."""
    task_file = os.path.join(TASKS_DIR, f"{args.task_id}.json")
    if not os.path.exists(task_file):
        print(json.dumps(error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Task not found")))
        return

    with open(task_file) as f:
        data = json.load(f)

    print(json.dumps(data, indent=2))


def cmd_search(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Search emails using FTS, vector, or hybrid search."""
    # Determine the isolated db_path
    client = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client.email)
    isolated_db = MailDatabase(paths["db_path"])

    # Get classification filters
    importance = getattr(args, "importance", None)
    category = getattr(args, "category", None)

    if args.query:
        if getattr(args, "hybrid", False):
            results = isolated_db.search_hybrid(args.query, limit=args.limit)
        elif getattr(args, "vector", False):
            results = isolated_db.search_vector(args.query, limit=args.limit)
        else:
            results = isolated_db.search_fts(args.query, limit=args.limit)

        filtered = []
        for r in results:
            if args.folder and r.get("folder") != args.folder:
                continue
            if args.sender and args.sender not in (r.get("sender") or ""):
                continue
            if args.subject and args.subject not in (r.get("subject") or ""):
                continue
            if args.is_read is not None and int(bool(r.get("is_read"))) != int(args.is_read):
                continue
            if args.has_attachment is not None and int(bool(r.get("has_attachment"))) != int(
                args.has_attachment
            ):
                continue
            if importance and r.get("importance") != importance:
                continue
            if category and r.get("category") != category:
                continue
            filtered.append(r)
        results = filtered
    else:
        results = isolated_db.search_emails(
            query=None,
            account=args.account,
            folder=args.folder,
            sender=args.sender,
            subject=args.subject,
            is_read=args.is_read,
            has_attachment=args.has_attachment,
            importance=importance,
            category=category,
            limit=args.limit,
        )

    # Format output
    output = []
    for r in results:
        # Convert datetime to string if needed
        output.append(
            {
                "message_id": r["message_id"],
                "subject": r["subject"],
                "sender": r["sender"],
                "date": r["date"],
                "folder": r["folder"],
                "is_read": r["is_read"],
                "importance": r.get("importance", "normal"),
                "category": r.get("category", "uncategorized"),
                "snippet": r["body_text"][:100] + "..."
                if r["body_text"] and len(r["body_text"]) > 100
                else r["body_text"],
            }
        )

    print(
        json.dumps(
            success_response(data={"count": len(results), "results": output}),
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_smart_search(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Search emails using natural language query.

    Parses the natural language query to extract date range, sender, and keywords,
    then executes appropriate search based on the extracted components.

    Args:
        args: Command line arguments with 'query' field containing natural language query
        config: Configuration dictionary
        db: MailDatabase instance (not used, we create isolated one per account)
    """
    from datetime import date

    # Determine the isolated db_path
    client = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client.email)
    isolated_db = MailDatabase(paths["db_path"])

    # Parse natural language query
    parsed: ParsedQuery = parse_natural_query(args.query, date.today())

    # Get unique senders for fuzzy matching
    senders = get_cached_senders(isolated_db, client.email)

    # Match sender if extracted
    matched_senders: list[str] = []
    if parsed.sender:
        matched_senders = match_senders(parsed.sender, senders)

    # Build search parameters
    date_from: str | None = None
    date_to: str | None = None
    if parsed.date_range:
        date_from = parsed.date_range.date_from.isoformat()
        date_to = parsed.date_range.date_to.isoformat()

    # Execute search
    results: list[dict]
    if parsed.keywords:
        # Use hybrid search for semantic matching
        results = isolated_db.search_hybrid(parsed.keywords, limit=args.limit)
        # Apply filters
        if date_from or date_to or matched_senders:
            filtered = []
            for r in results:
                if date_from and r.get("date") and r.get("date", "")[:10] < date_from[:10]:
                    continue
                if date_to and r.get("date") and r.get("date", "")[:10] > date_to[:10]:
                    continue
                if matched_senders:
                    sender_match = False
                    for ms in matched_senders:
                        if ms in (r.get("sender") or ""):
                            sender_match = True
                            break
                    if not sender_match:
                        continue
                filtered.append(r)
            results = filtered
    else:
        # Use structured search with filters only
        # For multiple matched senders, search each and combine
        if matched_senders:
            results = []
            for sender in matched_senders:
                sender_results = isolated_db.search_emails(
                    date_from=date_from,
                    date_to=date_to,
                    sender=sender,
                    limit=args.limit,
                )
                for r in sender_results:
                    if r not in results:
                        results.append(r)
        else:
            results = isolated_db.search_emails(
                date_from=date_from,
                date_to=date_to,
                limit=args.limit,
            )

    # Format output
    output = []
    for r in results[: args.limit]:
        output.append(
            {
                "message_id": r["message_id"],
                "subject": r["subject"],
                "sender": r["sender"],
                "date": r["date"],
                "folder": r["folder"],
                "is_read": r["is_read"],
                "snippet": r["body_text"][:100] + "..."
                if r["body_text"] and len(r["body_text"]) > 100
                else r["body_text"],
            }
        )

    # Build parsed_query response
    parsed_query_response = {
        "original": parsed.original_query,
        "date_range": {"from": date_from, "to": date_to} if date_from or date_to else None,
        "sender": matched_senders if matched_senders else None,
        "keywords": parsed.keywords,
    }

    print(
        json.dumps(
            success_response(
                data={
                    "parsed_query": parsed_query_response,
                    "count": len(output),
                    "results": output,
                }
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_read(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Read an email by message_id."""
    # Determine the isolated db_path
    client = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client.email)
    isolated_db = MailDatabase(paths["db_path"])

    email = isolated_db.get_email(args.message_id)
    if not email:
        print(
            json.dumps(error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Email not found locally"))
        )
        return
    table_md = _render_table(
        "email_table.md.j2",
        {
            "rows": [
                {
                    "sender": email.get("sender", ""),
                    "recipient": email.get("recipient", ""),
                    "cc": email.get("cc", ""),
                    "date": email.get("date", ""),
                    "subject": email.get("subject", ""),
                    "snippet": (email.get("body_text", "") or "")[:200]
                    .replace("\n", " ")
                    .replace("\r", ""),
                    "attachments": [att.get("local_path") for att in email.get("attachments", [])],
                }
            ]
        },
    )
    print(table_md)


def _append_signature(
    body_text: str, html_body: str | None, signature_path: str
) -> tuple[str, str | None]:
    """Append signature to the email body if the signature file exists and is not empty."""
    # Also support a fallback to just using the email address as the folder name
    # In case the directory wasn't sanitized with _at_
    fallback_path = (
        signature_path.replace("_at_", "@")
        .replace("_com", ".com")
        .replace("_net", ".net")
        .replace("_cn", ".cn")
        .replace("_org", ".org")
    )

    actual_path = signature_path
    if not os.path.exists(actual_path):
        # Try the raw email format if the sanitized one doesn't exist
        alt_path = os.path.join(
            os.path.dirname(os.path.dirname(signature_path)),
            os.path.basename(os.path.dirname(fallback_path)),
            "signature.md",
        )
        if os.path.exists(alt_path):
            actual_path = alt_path
        else:
            return body_text, html_body

    try:
        with open(actual_path, encoding="utf-8") as f:
            signature = f.read().strip()
    except Exception as e:
        logger.warning(f"Failed to read signature file {actual_path}: {e}")
        return body_text, html_body

    if not signature:
        return body_text, html_body

    # Append to plain text
    new_body_text = f"{body_text}\n\n--\n{signature}"

    # Append to HTML if it exists
    new_html_body = html_body
    if html_body:
        # Simple HTML signature append
        html_signature = markdown.markdown(signature)
        if "</body>" in html_body.lower():
            # Insert before closing body tag
            import re

            new_html_body = re.sub(
                r"(</body>)",
                rf'<br><br><div class="email-signature" style="color: #888; font-size: 0.9em; border-top: 1px solid #eee; padding-top: 10px; margin-top: 20px;">{html_signature}</div>\1',
                html_body,
                flags=re.IGNORECASE,
            )
        else:
            new_html_body = f'{html_body}<br><br><div class="email-signature" style="color: #888; font-size: 0.9em; border-top: 1px solid #eee; padding-top: 10px; margin-top: 20px;">{html_signature}</div>'

    return new_body_text, new_html_body


def _markdown_to_html(md_text: str) -> str:
    """Convert markdown text to styled HTML for emails."""
    html_content = markdown.markdown(md_text, extensions=["tables", "fenced_code", "nl2br"])
    # Render with our template
    try:
        return _render_table("email_theme.html.j2", {"content": html_content})
    except Exception as e:
        logger.warning(f"Could not load HTML template, using raw HTML: {e}")
        return html_content


def cmd_send(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Send a new email."""
    client = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client.email)

    try:
        # Replace literal "\n" strings with actual newline characters
        # This handles cases where AI passes "Line 1\nLine 2" as a single string argument
        body_text = args.body.replace("\\n", "\n")
        html_body = getattr(args, "html_body", None)

        # ALWAYS auto-convert markdown body to HTML if not provided, or override if provided
        # Since we want to FORCE markdown to HTML, we will ignore args.html_body and always generate it
        html_body = _markdown_to_html(body_text)

        # Append signature
        body_text, html_body = _append_signature(body_text, html_body, paths["signature_path"])

        attachments = _process_attachments(args.attach, getattr(args, "zip_as", None))

        client.send_email(
            to=args.to,
            subject=args.subject,
            body_text=body_text,
            html_body=html_body,
            cc=args.cc,
            bcc=args.bcc,
            attachments=attachments,
        )
        print(json.dumps(success_response(message="Email sent")))
    except Exception as e:
        print(json.dumps(error_response(ErrorCodes.SERVER_SMTP_SEND_FAILED, str(e))))


def cmd_reply(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Reply to an existing email."""
    import email.utils

    client = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client.email)
    isolated_db = MailDatabase(paths["db_path"])

    orig_email = isolated_db.get_email(args.message_id)
    if not orig_email:
        print(
            json.dumps(error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Email not found locally"))
        )
        return

    if not client.email:
        print(
            json.dumps(
                error_response(ErrorCodes.BIZ_ACCOUNT_NOT_CONFIGURED, "No email account configured")
            )
        )
        return

    my_email = client.email.lower()

    orig_sender = orig_email.get("sender", "")
    orig_to = orig_email.get("recipient", "")
    orig_cc = orig_email.get("cc", "")

    sender_addrs = email.utils.getaddresses([orig_sender]) if orig_sender else []
    to_addrs = email.utils.getaddresses([orig_to]) if orig_to else []
    cc_addrs = email.utils.getaddresses([orig_cc]) if orig_cc else []

    reply_to_addrs = []
    # Always reply to the original sender
    for name, addr in sender_addrs:
        if addr and addr.lower() != my_email:
            reply_to_addrs.append(email.utils.formataddr((name, addr)))

    # Fallback if we sent the original email to someone else
    if not reply_to_addrs:
        for name, addr in to_addrs:
            if addr and addr.lower() != my_email:
                reply_to_addrs.append(email.utils.formataddr((name, addr)))

    reply_cc_addrs = []
    if args.all:
        # Add other original 'To' recipients to our 'To' list
        for name, addr in to_addrs:
            fmt = email.utils.formataddr((name, addr))
            if addr and addr.lower() != my_email and fmt not in reply_to_addrs:
                reply_to_addrs.append(fmt)
        # Add original 'Cc' recipients to our 'Cc' list
        for name, addr in cc_addrs:
            fmt = email.utils.formataddr((name, addr))
            if (
                addr
                and addr.lower() != my_email
                and fmt not in reply_to_addrs
                and fmt not in reply_cc_addrs
            ):
                reply_cc_addrs.append(fmt)

    subject = orig_email.get("subject", "")
    if not subject.lower().startswith("re:"):
        subject = "Re: " + subject

    orig_msg_id = orig_email.get("message_id")

    try:
        body_text = args.body.replace("\\n", "\n")

        # Append original email history to body text
        orig_date = orig_email.get("date", "") or ""
        orig_sender_full = orig_email.get("sender", "") or ""
        orig_body = orig_email.get("body_text", "") or ""

        history_separator = f"\n\n--- Original Message ---\nFrom: {orig_sender_full}\nDate: {orig_date}\nTo: {orig_to}\nSubject: {orig_email.get('subject', '')}\n\n"

        # Add "> " prefix to original body for blockquote style in plain text
        quoted_orig_body = "\n".join([f"> {line}" for line in orig_body.split("\n")])
        body_text_with_history = body_text + history_separator + quoted_orig_body

        # ALWAYS auto-convert markdown body to HTML to ensure beautiful formatting
        html_reply_part = _markdown_to_html(body_text)

        # Format history for HTML
        html_history = f"""
        <br><br>
        <div class="gmail_quote" style="border-left: 1px solid #ccc; padding-left: 1ex; margin-left: 1ex; color: #555;">
            <div dir="ltr">
                <br>--- Original Message ---<br>
                <b>From:</b> {orig_sender_full}<br>
                <b>Date:</b> {orig_date}<br>
                <b>To:</b> {orig_to}<br>
                <b>Subject:</b> {orig_email.get("subject", "")}<br>
            </div>
            <br>
            <div>
                {orig_body.replace(chr(10), "<br>")}
            </div>
        </div>
        """

        # If the template conversion returned a full HTML doc, insert before </body>
        html_body: str
        if "</body>" in html_reply_part.lower():
            import re

            html_body = re.sub(
                r"(</body>)", rf"{html_history}\1", html_reply_part, flags=re.IGNORECASE
            )
        else:
            html_body = html_reply_part + html_history

        # Append signature
        body_text_with_history, html_body_result = _append_signature(
            body_text_with_history, html_body, paths["signature_path"]
        )
        # We know html_body_result is str because we passed a non-None html_body
        html_body = html_body_result or html_body

        attachments = _process_attachments(args.attach, getattr(args, "zip_as", None))

        client.send_email(
            to=reply_to_addrs,
            subject=subject,
            body_text=body_text_with_history,
            html_body=html_body,
            cc=reply_cc_addrs if reply_cc_addrs else None,
            attachments=attachments,
            in_reply_to=orig_msg_id,
            references=orig_msg_id,
        )
        print(
            json.dumps(
                success_response(
                    data={"to": reply_to_addrs, "cc": reply_cc_addrs}, message="Reply sent"
                )
            )
        )
    except Exception as e:
        print(json.dumps(error_response(ErrorCodes.SERVER_SMTP_SEND_FAILED, str(e))))


def cmd_mark(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Mark email as read/unread or starred."""
    # Determine the isolated db_path
    client_init = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client_init.email)
    isolated_db = MailDatabase(paths["db_path"])

    email = isolated_db.get_email(args.message_id)
    if not email:
        print(
            json.dumps(error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Email not found locally"))
        )
        return

    client = get_client(config, email["account"])

    try:
        imap_uid = email.get("imap_uid")
        if not imap_uid:
            print(
                json.dumps(
                    error_response(
                        ErrorCodes.USER_INVALID_MESSAGE_ID,
                        "Cannot mark email on server: missing imap_uid in database. Please fetch emails again.",
                    )
                )
            )
            return

        if args.read is not None:
            is_read = bool(args.read)
            client.mark_as_read(imap_uid, email["folder"], is_read)
            isolated_db.update_flags(args.message_id, is_read=is_read)

        if args.starred is not None:
            is_starred = bool(args.starred)
            client.mark_as_starred(imap_uid, email["folder"], is_starred)
            isolated_db.update_flags(args.message_id, is_starred=is_starred)

        print(json.dumps(success_response(message="Flags updated")))
    except Exception as e:
        print(json.dumps(error_response(ErrorCodes.SERVER_IMAP_CONNECTION_FAILED, str(e))))


def cmd_move(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Move email to another folder."""
    # Determine the isolated db_path
    client_init = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client_init.email)
    isolated_db = MailDatabase(paths["db_path"])

    email = isolated_db.get_email(args.message_id)
    if not email:
        print(
            json.dumps(error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Email not found locally"))
        )
        return

    client = get_client(config, email["account"])

    try:
        imap_uid = email.get("imap_uid")
        if not imap_uid:
            print(
                json.dumps(
                    error_response(
                        ErrorCodes.USER_INVALID_MESSAGE_ID,
                        "Cannot move email on server: missing imap_uid in database. Please fetch emails again.",
                    )
                )
            )
            return

        client.move_emails(imap_uid, args.target_folder, email["folder"])
        isolated_db.update_flags(args.message_id, folder=args.target_folder)
        print(json.dumps(success_response(message=f"Moved to {args.target_folder}")))
    except Exception as e:
        print(json.dumps(error_response(ErrorCodes.SERVER_IMAP_CONNECTION_FAILED, str(e))))


def cmd_delete(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Delete an email."""
    # Determine the isolated db_path
    client_init = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client_init.email)
    isolated_db = MailDatabase(paths["db_path"])

    email = isolated_db.get_email(args.message_id)
    if not email:
        print(
            json.dumps(error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Email not found locally"))
        )
        return

    client = get_client(config, email["account"])

    try:
        imap_uid = email.get("imap_uid")
        if not imap_uid:
            print(
                json.dumps(
                    error_response(
                        ErrorCodes.USER_INVALID_MESSAGE_ID,
                        "Cannot delete email on server: missing imap_uid in database. Please fetch emails again.",
                    )
                )
            )
            return

        client.delete_emails(imap_uid, email["folder"])
        isolated_db.delete_email(args.message_id)
        print(json.dumps(success_response(message="Email deleted")))
    except Exception as e:
        print(json.dumps(error_response(ErrorCodes.SERVER_IMAP_CONNECTION_FAILED, str(e))))


def cmd_export(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Export emails to JSON or CSV file."""
    # Determine the isolated db_path
    client = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client.email)
    isolated_db = MailDatabase(paths["db_path"])

    results = isolated_db.search_emails(limit=10000)  # Get all
    if args.format == "json":
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    elif args.format == "csv":
        import csv

        with open(args.output, "w", newline="", encoding="utf-8") as f:
            if not results:
                return
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "message_id",
                    "account",
                    "subject",
                    "sender",
                    "recipient",
                    "date",
                    "folder",
                    "is_read",
                ],
            )
            writer.writeheader()
            for r in results:
                writer.writerow(
                    {
                        "message_id": r["message_id"],
                        "account": r["account"],
                        "subject": r["subject"],
                        "sender": r["sender"],
                        "recipient": r["recipient"],
                        "date": r["date"],
                        "folder": r["folder"],
                        "is_read": r["is_read"],
                    }
                )
    print(json.dumps(success_response(message=f"Exported {len(results)} emails to {args.output}")))


def cmd_attachments(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """List attachments with preview URLs."""
    # Get account paths
    client = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client.email)
    isolated_db = MailDatabase(paths["db_path"])

    # Query emails with attachments
    results = isolated_db.search_emails(has_attachment=True, limit=args.limit)

    # Check/start server
    attachments_dir = paths["attach_path"]

    # Check existing state
    state_file = AttachmentServer.get_state_file(
        Path(paths["root"])
    )
    state = ServerState.load(state_file)

    if state and state.is_running():
        port = state.port
    else:
        server = AttachmentServer(attachments_dir)
        port = server.start()
        new_state = ServerState(
            port=port, pid=os.getpid(), started_at=datetime.now().isoformat()
        )
        new_state.save(state_file)

    # Build output
    attachments_list: list[dict[str, Any]] = []
    for email in results:
        for att in email.get("attachments", []):
            local_path = att.get("local_path", "")
            if local_path:
                # Generate relative path for URL
                rel_path = os.path.relpath(local_path, attachments_dir)
                encoded_path = quote(rel_path)
                url = f"http://127.0.0.1:{port}/{encoded_path}"
                attachments_list.append(
                    {
                        "filename": att.get("filename"),
                        "size": att.get("size"),
                        "content_type": att.get("content_type"),
                        "message_id": email.get("message_id"),
                        "subject": email.get("subject"),
                        "preview_url": url,
                    }
                )

    print(
        json.dumps(
            success_response(
                data={
                    "port": port,
                    "count": len(attachments_list),
                    "attachments": attachments_list,
                },
                message=f"Attachment server running on port {port}",
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_summarize(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Summarize emails using LLM."""
    # Determine the isolated db_path
    client = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client.email)
    isolated_db = MailDatabase(paths["db_path"])

    # If a task ID is provided, load its fetched IDs to summarize only those
    fetched_ids = []
    if args.task_id:
        task_file = os.path.join(TASKS_DIR, f"{args.task_id}.json")
        if os.path.exists(task_file):
            with open(task_file) as f:
                data = json.load(f)
                fetched_ids = data.get("fetched_ids", [])

    if fetched_ids:
        emails = [e for msg_id in fetched_ids if (e := isolated_db.get_email(msg_id)) is not None]
    else:
        # Fallback to recent emails if no task ID or it had no ids
        emails = isolated_db.search_emails(limit=args.limit)

    if not emails:
        print("未找到需要总结的邮件。")
        return

    # Categorize emails
    important_emails = []
    verification_emails = []
    action_required_emails = []
    other_emails = []

    important_keywords = [
        "重要",
        "紧急",
        "urgent",
        "important",
        "通知",
        "账单",
        "合同",
        "面试",
        "offer",
    ]
    verification_keywords = ["验证码", "activation code", "verify", "code", "安全码"]
    action_keywords = ["回复", "确认", "请查收", "跟进", "action required", "please reply"]

    for email in emails:
        subject = email.get("subject", "").lower()
        body = email.get("body_text", "").lower()
        snippet = body[:150].replace("\n", " ").replace("\r", "") + "..." if body else ""

        email_info = {
            "id": email.get("message_id"),
            "subject": email.get("subject", "无主题"),
            "sender": email.get("sender", "未知发件人"),
            "date": email.get("date", "")[:10] if email.get("date") else "",
            "snippet": snippet,
        }

        is_categorized = False

        # 1. Check for verification codes
        if any(kw in subject or kw in body[:500] for kw in verification_keywords):
            # Try to extract the code using a simple regex (4-6 digits)
            code_match = re.search(r"\b\d{4,6}\b", body[:500])
            if code_match:
                email_info["code"] = code_match.group()
            verification_emails.append(email_info)
            is_categorized = True

        # 2. Check for action required
        elif any(kw in subject or kw in body[:200] for kw in action_keywords):
            action_required_emails.append(email_info)
            is_categorized = True

        # 3. Check for important
        elif any(kw in subject for kw in important_keywords):
            important_emails.append(email_info)
            is_categorized = True

        # 4. Others
        if not is_categorized:
            other_emails.append(email_info)

    # Generate Markdown Report
    report = [
        f"## 📧 邮件收取简报 ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
        f"**总体汇总**：本次共收取/分析了 **{len(emails)}** 封邮件。",
        "---",
    ]

    if verification_emails:
        report.append("### 🔑 验证码与登录凭证")
        for e in verification_emails:
            code_str = f" **[提取码: {e.get('code')}]**" if "code" in e else ""
            report.append(f"- **{e['sender']}**: {e['subject']}{code_str}")
        report.append("")

    if important_emails:
        report.append("### 🚨 疑似重要邮件 (需优先关注)")
        for e in important_emails:
            report.append(f"- **{e['sender']}**: {e['subject']}")
            report.append(f"  > *摘要: {e['snippet']}*")
        report.append("")

    if action_required_emails:
        report.append("### ⏳ 待回复/待处理邮件")
        for e in action_required_emails:
            report.append(f"- **{e['sender']}**: {e['subject']}")
        report.append("")

    if other_emails:
        report.append("### 📩 其他常规邮件")
        for e in other_emails[:5]:  # Only show top 5 others to avoid clutter
            report.append(f"- {e['sender']}: {e['subject']}")
        if len(other_emails) > 5:
            report.append(f"- *(还有 {len(other_emails) - 5} 封常规邮件未展示)*")

    report.append("\n*提示: 您可以通过 `read <message_id>` 查看上述任一邮件的完整内容。*")

    print("\n".join(report))


def cmd_thread(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Display email thread timeline."""
    client = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client.email)
    isolated_db = MailDatabase(paths["db_path"])
    timeline = isolated_db.get_thread_timeline(args.message_id, limit=200)
    if not timeline:
        print("未找到关联邮件线程。")
        return
    rows = []
    for e in timeline:
        rows.append(
            {
                "sender": e.get("sender", ""),
                "recipient": e.get("recipient", ""),
                "cc": e.get("cc", ""),
                "date": e.get("date", ""),
                "subject": e.get("subject", ""),
                "snippet": (e.get("body_text", "") or "")[:200]
                .replace("\n", " ")
                .replace("\r", ""),
                "attachments": [att.get("local_path") for att in e.get("attachments", [])],
            }
        )
    table_md = _render_table("thread.md.j2", {"rows": rows})
    print(table_md)


def cmd_classify(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Classify emails automatically or get classification for one email."""
    from mail_manager.classifier import EmailClassifier

    client = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client.email)
    isolated_db = MailDatabase(paths["db_path"])

    message_id = getattr(args, "message_id", None)

    if message_id:
        # Classify single email
        email = isolated_db.get_email(message_id)
        if not email:
            print(json.dumps(error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, f"Email {message_id} not found")))
            return

        classifier = EmailClassifier()
        classification = classifier.classify(email)

        # Save to database
        isolated_db.update_classification(
            message_id=message_id,
            importance=classification.importance,
            category=classification.category,
            confidence=classification.confidence,
        )

        print(
            json.dumps(
                success_response(
                    data={
                        "message_id": message_id,
                        "importance": classification.importance,
                        "category": classification.category,
                        "confidence": classification.confidence,
                        "matched_rules": classification.matched_rules,
                    }
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        # Classify all unclassified emails
        emails = isolated_db.search_emails(limit=args.limit)
        classifier = EmailClassifier()
        count = 0
        for email in emails:
            # Check if needs classification (default values)
            if email.get("importance") == "normal" and email.get("category") == "uncategorized":
                classification = classifier.classify(email)
                isolated_db.update_classification(
                    message_id=email["message_id"],
                    importance=classification.importance,
                    category=classification.category,
                    confidence=classification.confidence,
                )
                count += 1
        print(json.dumps(success_response(data={"classified": count})))


def cmd_reclassify(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Manually reclassify an email."""
    client = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client.email)
    isolated_db = MailDatabase(paths["db_path"])

    message_id = args.message_id
    importance = getattr(args, "importance", None)
    category = getattr(args, "category", None)

    email = isolated_db.get_email(message_id)
    if not email:
        print(json.dumps(error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, f"Email {message_id} not found")))
        return

    # Update with manual override flag
    isolated_db.update_classification(
        message_id=message_id,
        importance=importance,
        category=category,
        confidence=1.0,  # Manual classification has full confidence
        manual_override=True,
    )

    print(
        json.dumps(
            success_response(
                data={
                    "message_id": message_id,
                    "importance": importance,
                    "category": category,
                    "manual_override": True,
                }
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_rebuild_index(args: Any, config: dict[str, Any], db: MailDatabase) -> None:
    """Rebuild ChromaDB index for vector search."""
    client = get_client(config, getattr(args, "account", None))
    paths = _get_account_paths(config, client.email)
    isolated_db = MailDatabase(paths["db_path"])

    print(f"Rebuilding search indices for {client.email}...")

    with isolated_db._get_connection() as conn:
        cursor = conn.cursor()

        # 1. Rebuild FTS5
        print("Rebuilding FTS5 index...")
        try:
            cursor.execute("INSERT INTO emails_fts(emails_fts) VALUES('rebuild')")
            conn.commit()
            print("✓ FTS5 rebuild complete.")
        except Exception as e:
            print(f"✗ FTS5 rebuild failed: {e}")

        # 2. Rebuild ChromaDB
        print("Rebuilding Vector index (this may take a while)...")
        try:
            collection = isolated_db._get_chroma_collection()
            cursor.execute("SELECT * FROM emails")
            rows = cursor.fetchall()

            # Batch upsert
            batch_size = 50
            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                ids = []
                documents = []
                metadatas = []

                for row in batch:
                    email_dict = dict(row)
                    doc_text = f"Subject: {email_dict.get('subject', '')}\nFrom: {email_dict.get('sender', '')}\nDate: {email_dict.get('date', '')}\n\n{email_dict.get('body_text', '')}"
                    if len(doc_text) > 8000:
                        doc_text = doc_text[:8000]

                    ids.append(email_dict["message_id"])
                    documents.append(doc_text)
                    metadatas.append(
                        {
                            "subject": email_dict.get("subject", "") or "",
                            "sender": email_dict.get("sender", "") or "",
                            "date": str(email_dict.get("date", "")),
                        }
                    )

                if ids:
                    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
                print(f"  Processed {min(i + batch_size, len(rows))}/{len(rows)} emails...")

            print("✓ Vector index rebuild complete.")
        except Exception as e:
            print(f"✗ Vector index rebuild failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Mail Manager CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # fetch
    fetch_p = subparsers.add_parser("fetch", help="Fetch emails from server asynchronously")
    fetch_p.add_argument("--account", help="Email account to use")
    fetch_p.add_argument(
        "--folder",
        default="INBOX",
        help="Folder to fetch from. Use 'ALL' to fetch from all folders, or comma-separated names like 'INBOX,Sent'",
    )
    fetch_p.add_argument("--limit", type=int, default=50, help="Max emails to fetch per folder")
    fetch_p.add_argument("--days", type=int, default=7, help="Fetch emails from last N days")
    fetch_p.add_argument("--unread", action="store_true", help="Fetch only unread emails")
    fetch_p.add_argument(
        "--confirm", action="store_true", help="Confirm fetching more than 100 emails"
    )

    # fetch-status
    fetch_status_p = subparsers.add_parser(
        "fetch-status", help="Check status of an async fetch task"
    )
    fetch_status_p.add_argument("task_id", help="Task ID returned by the fetch command")

    # search
    search_p = subparsers.add_parser("search", help="Search local emails")
    search_p.add_argument("--query", help="Text to search in subject/body/sender")
    search_p.add_argument(
        "--vector",
        action="store_true",
        help="Use vector semantic search instead of full-text search",
    )
    search_p.add_argument(
        "--hybrid", action="store_true", help="Use hybrid search (FTS + Vector) with reranking"
    )
    search_p.add_argument("--account", help="Filter by account")
    search_p.add_argument("--folder", help="Filter by folder")
    search_p.add_argument("--sender", help="Filter by sender")
    search_p.add_argument("--subject", help="Filter by subject")
    search_p.add_argument("--is-read", type=int, choices=[0, 1], help="1 for read, 0 for unread")
    search_p.add_argument("--has-attachment", type=int, choices=[0, 1], help="1 for has attachment")
    search_p.add_argument(
        "--importance", choices=["critical", "high", "normal", "low"], help="Filter by importance level"
    )
    search_p.add_argument(
        "--category",
        choices=["work", "personal", "notification", "promo", "uncategorized"],
        help="Filter by category",
    )
    search_p.add_argument("--limit", type=int, default=20, help="Max results")

    # smart-search
    smart_search_p = subparsers.add_parser(
        "smart-search", help="Search emails using natural language"
    )
    smart_search_p.add_argument("query", help="Natural language search query")
    smart_search_p.add_argument("--account", help="Account to search")
    smart_search_p.add_argument("--limit", type=int, default=20, help="Max results")

    # read
    read_p = subparsers.add_parser("read", help="Read a specific email by message_id")
    read_p.add_argument("message_id", help="Message ID to read")
    read_p.add_argument("--account", help="Account to read from")

    # send
    send_p = subparsers.add_parser("send", help="Send an email")
    send_p.add_argument("--account", help="Account to send from")
    send_p.add_argument("--to", required=True, nargs="+", help="Recipient email(s)")
    send_p.add_argument("--subject", required=True, help="Email subject")
    send_p.add_argument("--body", required=True, help="Email body text")
    send_p.add_argument("--html-body", help="Email body in HTML format")
    send_p.add_argument("--cc", nargs="+", help="CC email address(es)")
    send_p.add_argument("--bcc", nargs="+", help="BCC email address(es)")
    send_p.add_argument("--attach", nargs="+", help="Paths to attachments (files or folders)")
    send_p.add_argument(
        "--zip-as", help="Pack all attachments into a single zip file with this name"
    )

    # reply
    reply_p = subparsers.add_parser("reply", help="Reply to an email")
    reply_p.add_argument("message_id", help="Message ID to reply to")
    reply_p.add_argument("--account", help="Account to send from")
    reply_p.add_argument("--body", required=True, help="Email body text")
    reply_p.add_argument("--html-body", help="Email body in HTML format")
    reply_p.add_argument("--all", action="store_true", help="Reply to all (senders and CCs)")
    reply_p.add_argument("--attach", nargs="+", help="Paths to attachments (files or folders)")
    reply_p.add_argument(
        "--zip-as", help="Pack all attachments into a single zip file with this name"
    )

    # mark
    mark_p = subparsers.add_parser("mark", help="Mark email as read/starred")
    mark_p.add_argument("message_id", help="Message ID to mark")
    mark_p.add_argument("--read", type=int, choices=[0, 1], help="1 to mark read, 0 for unread")
    mark_p.add_argument("--starred", type=int, choices=[0, 1], help="1 to star, 0 to unstar")

    # move
    move_p = subparsers.add_parser("move", help="Move email to folder")
    move_p.add_argument("message_id", help="Message ID to move")
    move_p.add_argument("target_folder", help="Target folder name")

    # delete
    del_p = subparsers.add_parser("delete", help="Delete email")
    del_p.add_argument("message_id", help="Message ID to delete")

    # export
    exp_p = subparsers.add_parser("export", help="Export emails")
    exp_p.add_argument("--format", choices=["json", "csv"], default="json", help="Export format")
    exp_p.add_argument("--output", required=True, help="Output file path")

    # attachments
    att_p = subparsers.add_parser("attachments", help="List attachments with preview links")
    att_p.add_argument("--account", help="Account to list attachments from")
    att_p.add_argument("--limit", type=int, default=100, help="Max results")

    # summarize
    sum_p = subparsers.add_parser(
        "summarize", help="Generate a professional markdown summary of emails"
    )
    sum_p.add_argument("--task-id", help="Summarize emails from a specific fetch task ID")
    sum_p.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of recent emails to summarize if no task-id is provided",
    )

    # thread
    thread_p = subparsers.add_parser("thread", help="Show email thread timeline as a table")
    thread_p.add_argument("message_id", help="Seed message_id to build the thread")
    thread_p.add_argument("--account", help="Account to read from")

    # rebuild-index
    rebuild_p = subparsers.add_parser(
        "rebuild-index", help="Rebuild FTS5 and Vector search indices for existing emails"
    )
    rebuild_p.add_argument("--account", help="Account to rebuild indices for")

    # classify
    classify_p = subparsers.add_parser("classify", help="Classify emails by importance and category")
    classify_p.add_argument("message_id", nargs="?", help="Message ID to classify (optional, defaults to all)")
    classify_p.add_argument("--account", help="Account to classify emails from")
    classify_p.add_argument("--limit", type=int, default=100, help="Max emails to classify when batch mode")

    # reclassify
    reclassify_p = subparsers.add_parser("reclassify", help="Manually reclassify an email")
    reclassify_p.add_argument("message_id", help="Message ID to reclassify")
    reclassify_p.add_argument("--importance", choices=["critical", "high", "normal", "low"], help="New importance level")
    reclassify_p.add_argument("--category", choices=["work", "personal", "notification", "promo", "uncategorized"], help="New category")
    reclassify_p.add_argument("--account", help="Account the email belongs to")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    config = load_config()
    db = MailDatabase(config["DB_PATH"])

    if args.command == "fetch":
        cmd_fetch(args, config, db)
    elif args.command == "fetch-status":
        cmd_fetch_status(args, config, db)
    elif args.command == "search":
        cmd_search(args, config, db)
    elif args.command == "smart-search":
        cmd_smart_search(args, config, db)
    elif args.command == "read":
        cmd_read(args, config, db)
    elif args.command == "send":
        cmd_send(args, config, db)
    elif args.command == "reply":
        cmd_reply(args, config, db)
    elif args.command == "mark":
        cmd_mark(args, config, db)
    elif args.command == "move":
        cmd_move(args, config, db)
    elif args.command == "delete":
        cmd_delete(args, config, db)
    elif args.command == "export":
        cmd_export(args, config, db)
    elif args.command == "attachments":
        cmd_attachments(args, config, db)
    elif args.command == "summarize":
        cmd_summarize(args, config, db)
    elif args.command == "thread":
        cmd_thread(args, config, db)
    elif args.command == "rebuild-index":
        cmd_rebuild_index(args, config, db)
    elif args.command == "classify":
        cmd_classify(args, config, db)
    elif args.command == "reclassify":
        cmd_reclassify(args, config, db)


if __name__ == "__main__":
    main()
