#!/usr/bin/env python3
import argparse
import os
import sys
import json
import logging
import threading
import time
import uuid
import re
from datetime import datetime
from dotenv import load_dotenv

# Ensure the parent directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mail_manager.db import MailDatabase
from mail_manager.client import MailClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Task tracking for async fetch
TASKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mail_data', 'tasks')
os.makedirs(TASKS_DIR, exist_ok=True)

def load_config():
    """Load configuration from .env file"""
    # Look for .env in the parent directory of scripts
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv() # Try current directory
        
    config = {
        'STORAGE_ROOT': os.getenv('MAIL_STORAGE_ROOT', './mail_data'),
        'DB_PATH': os.getenv('MAIL_DB_PATH', './mail_data/mail_index.db'),
        'ATTACHMENT_PATH': os.getenv('MAIL_ATTACHMENT_PATH', './mail_data/attachments'),
        'ACCOUNTS': {}
    }
    
    # Parse accounts
    for key, value in os.environ.items():
        if key.startswith('MAIL_ACCOUNT_') and key.endswith('_EMAIL'):
            account_prefix = key[:-6] # Remove _EMAIL
            account_id = account_prefix.split('_')[-1]
            
            config['ACCOUNTS'][value] = {
                'EMAIL': value,
                'PASSWORD': os.getenv(f'{account_prefix}_PASSWORD'),
                'IMAP_SERVER': os.getenv(f'{account_prefix}_IMAP_SERVER'),
                'IMAP_PORT': os.getenv(f'{account_prefix}_IMAP_PORT', '993'),
                'SMTP_SERVER': os.getenv(f'{account_prefix}_SMTP_SERVER'),
                'SMTP_PORT': os.getenv(f'{account_prefix}_SMTP_PORT', '465'),
                'USE_SSL': os.getenv(f'{account_prefix}_USE_SSL', 'true'),
                'PREFIX': account_prefix
            }
            
    return config

def get_client(config, email_account=None):
    if not config['ACCOUNTS']:
        raise ValueError("No mail accounts configured in .env")
        
    if email_account and email_account in config['ACCOUNTS']:
        account_config = config['ACCOUNTS'][email_account]
    else:
        # Use the first account
        account_config = list(config['ACCOUNTS'].values())[0]
        
    return MailClient(account_config)

def _run_fetch_task(task_id, config, db_path, args):
    # Ensure this runs in a completely separate process to avoid thread killing issues
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
    def update_status(status, message="", data=None):
        info = {"status": status, "message": message, "updated_at": datetime.now().isoformat()}
        if data:
            info.update(data)
        with open(task_file, 'w') as f:
            json.dump(info, f)

    try:
        db = MailDatabase(db_path)
        client = get_client(config, args.account)
        update_status("running", f"Connecting and fetching emails for {client.email}...")
        
        # Ensure directories exist
        os.makedirs(config['ATTACHMENT_PATH'], exist_ok=True)
        os.makedirs(os.path.join(config['STORAGE_ROOT'], 'eml'), exist_ok=True)
        os.makedirs(os.path.join(config['STORAGE_ROOT'], 'json'), exist_ok=True)
        
        # Fetch from server
        emails = client.fetch_emails(
            folder=args.folder, 
            limit=args.limit, 
            days_back=args.days,
            unread_only=args.unread,
            db_check_func=db.exists
        )
        
        saved_count = 0
        fetched_ids = []
        for email_data in emails:
            # Save EML
            eml_filename = "".join([c for c in email_data['message_id'] if c.isalpha() or c.isdigit() or c in '-_.']).rstrip() + '.eml'
            eml_path = os.path.join(config['STORAGE_ROOT'], 'eml', eml_filename)
            with open(eml_path, 'wb') as f:
                f.write(bytes(email_data['raw_email']))
            email_data['local_path_eml'] = eml_path
            
            # Save attachments
            db_attachments = []
            if email_data['attachments']:
                att_dir = os.path.join(config['ATTACHMENT_PATH'], email_data['message_id'].replace('/', '_'))
                os.makedirs(att_dir, exist_ok=True)
                
                for att in email_data['attachments']:
                    if att.filename:
                        att_path = os.path.join(att_dir, att.filename)
                        with open(att_path, 'wb') as f:
                            f.write(att.payload)
                        db_attachments.append({
                            'filename': att.filename,
                            'content_type': att.content_type,
                            'size': att.size,
                            'local_path': att_path
                        })
            email_data['attachments'] = db_attachments
            
            # Save JSON
            json_filename = eml_filename.replace('.eml', '.json')
            json_path = os.path.join(config['STORAGE_ROOT'], 'json', json_filename)
            
            # Remove raw_email before saving JSON
            json_data = {k: v for k, v in email_data.items() if k not in ['raw_email', 'html_body']}
            # Convert datetime to string
            if 'date' in json_data and isinstance(json_data['date'], datetime):
                json_data['date'] = json_data['date'].isoformat()
                
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            email_data['local_path_json'] = json_path
            
            # Save to DB
            db.save_email(email_data)
            saved_count += 1
            fetched_ids.append(email_data['message_id'])
            
            # Update status periodically if many emails
            if saved_count % 10 == 0:
                update_status("running", f"Saved {saved_count} of {len(emails)} emails...", {"progress": saved_count, "total": len(emails)})
            
        update_status("completed", "Fetch completed successfully.", {"fetched_count": len(emails), "saved_count": saved_count, "fetched_ids": fetched_ids})
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        update_status("failed", str(e))

def cmd_fetch(args, config, db):
    if args.limit > 100 and not args.confirm:
        print(json.dumps({
            "status": "requires_confirmation",
            "message": f"You requested to fetch {args.limit} emails. This may take a long time. Please run the command again with --confirm to proceed."
        }))
        return

    task_id = str(uuid.uuid4())
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
    
    # Initialize task file
    with open(task_file, 'w') as f:
        json.dump({"status": "starting", "message": "Initializing fetch task...", "updated_at": datetime.now().isoformat()}, f)
    
    # Use multiprocessing to ensure it runs even if parent exits
    import multiprocessing
    p = multiprocessing.Process(target=_run_fetch_task, args=(task_id, config, config['DB_PATH'], args))
    p.start()
    
    # Return immediately to the LLM
    print(json.dumps({
        "status": "started",
        "task_id": task_id,
        "message": "Fetch task started in the background. Use the 'fetch-status' command to check progress."
    }))

def cmd_fetch_status(args, config, db):
    task_file = os.path.join(TASKS_DIR, f"{args.task_id}.json")
    if not os.path.exists(task_file):
        print(json.dumps({"status": "error", "message": "Task not found"}))
        return
        
    with open(task_file, 'r') as f:
        data = json.load(f)
        
    print(json.dumps(data, indent=2))

def cmd_search(args, config, db):
    results = db.search_emails(
        query=args.query,
        account=args.account,
        folder=args.folder,
        sender=args.sender,
        subject=args.subject,
        is_read=args.is_read,
        has_attachment=args.has_attachment,
        limit=args.limit
    )
    
    # Format output
    output = []
    for r in results:
        # Convert datetime to string if needed
        output.append({
            'message_id': r['message_id'],
            'subject': r['subject'],
            'sender': r['sender'],
            'date': r['date'],
            'folder': r['folder'],
            'is_read': r['is_read'],
            'snippet': r['body_text'][:100] + '...' if r['body_text'] and len(r['body_text']) > 100 else r['body_text']
        })
        
    print(json.dumps({"status": "success", "count": len(results), "results": output}, ensure_ascii=False, indent=2))

def cmd_read(args, config, db):
    email = db.get_email(args.message_id)
    if not email:
        print(json.dumps({"status": "error", "message": "Email not found locally"}))
        return
        
    print(json.dumps({"status": "success", "email": email}, ensure_ascii=False, indent=2))

def cmd_send(args, config, db):
    client = get_client(config, args.account)
    try:
        # Replace literal "\n" strings with actual newline characters
        # This handles cases where AI passes "Line 1\nLine 2" as a single string argument
        body_text = args.body.replace('\\n', '\n')
        
        client.send_email(
            to=args.to,
            subject=args.subject,
            body_text=body_text,
            cc=args.cc,
            attachments=args.attach
        )
        print(json.dumps({"status": "success", "message": "Email sent"}))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

def cmd_mark(args, config, db):
    email = db.get_email(args.message_id)
    if not email:
        print(json.dumps({"status": "error", "message": "Email not found locally"}))
        return
        
    client = get_client(config, email['account'])
    
    try:
        if args.read is not None:
            is_read = bool(args.read)
            client.mark_as_read(email['imap_uid'], email['folder'], is_read)
            db.update_flags(args.message_id, is_read=is_read)
            
        if args.starred is not None:
            is_starred = bool(args.starred)
            client.mark_as_starred(email['imap_uid'], email['folder'], is_starred)
            db.update_flags(args.message_id, is_starred=is_starred)
            
        print(json.dumps({"status": "success", "message": "Flags updated"}))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

def cmd_move(args, config, db):
    email = db.get_email(args.message_id)
    if not email:
        print(json.dumps({"status": "error", "message": "Email not found locally"}))
        return
        
    client = get_client(config, email['account'])
    
    try:
        client.move_emails(email['imap_uid'], args.target_folder, email['folder'])
        db.update_flags(args.message_id, folder=args.target_folder)
        print(json.dumps({"status": "success", "message": f"Moved to {args.target_folder}"}))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

def cmd_delete(args, config, db):
    email = db.get_email(args.message_id)
    if not email:
        print(json.dumps({"status": "error", "message": "Email not found locally"}))
        return
        
    client = get_client(config, email['account'])
    
    try:
        client.delete_emails(email['imap_uid'], email['folder'])
        db.delete_email(args.message_id)
        print(json.dumps({"status": "success", "message": "Email deleted"}))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

def cmd_export(args, config, db):
    results = db.search_emails(limit=10000) # Get all
    if args.format == 'json':
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    elif args.format == 'csv':
        import csv
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            if not results:
                return
            writer = csv.DictWriter(f, fieldnames=['message_id', 'account', 'subject', 'sender', 'recipient', 'date', 'folder', 'is_read'])
            writer.writeheader()
            for r in results:
                writer.writerow({
                    'message_id': r['message_id'],
                    'account': r['account'],
                    'subject': r['subject'],
                    'sender': r['sender'],
                    'recipient': r['recipient'],
                    'date': r['date'],
                    'folder': r['folder'],
                    'is_read': r['is_read']
                })
    print(json.dumps({"status": "success", "message": f"Exported {len(results)} emails to {args.output}"}))

def cmd_summarize(args, config, db):
    # If a task ID is provided, load its fetched IDs to summarize only those
    fetched_ids = []
    if args.task_id:
        task_file = os.path.join(TASKS_DIR, f"{args.task_id}.json")
        if os.path.exists(task_file):
            with open(task_file, 'r') as f:
                data = json.load(f)
                fetched_ids = data.get("fetched_ids", [])
    
    if fetched_ids:
        emails = [db.get_email(msg_id) for msg_id in fetched_ids if db.get_email(msg_id)]
    else:
        # Fallback to recent emails if no task ID or it had no ids
        emails = db.search_emails(limit=args.limit)

    if not emails:
        print("未找到需要总结的邮件。")
        return

    # Categorize emails
    important_emails = []
    verification_emails = []
    action_required_emails = []
    other_emails = []
    
    important_keywords = ['重要', '紧急', 'urgent', 'important', '通知', '账单', '合同', '面试', 'offer']
    verification_keywords = ['验证码', 'activation code', 'verify', 'code', '安全码']
    action_keywords = ['回复', '确认', '请查收', '跟进', 'action required', 'please reply']

    for email in emails:
        subject = email.get('subject', '').lower()
        body = email.get('body_text', '').lower()
        snippet = body[:150].replace('\n', ' ').replace('\r', '') + '...' if body else ''
        
        email_info = {
            'id': email.get('message_id'),
            'subject': email.get('subject', '无主题'),
            'sender': email.get('sender', '未知发件人'),
            'date': email.get('date', '')[:10] if email.get('date') else '',
            'snippet': snippet
        }

        is_categorized = False
        
        # 1. Check for verification codes
        if any(kw in subject or kw in body[:500] for kw in verification_keywords):
            # Try to extract the code using a simple regex (4-6 digits)
            code_match = re.search(r'\b\d{4,6}\b', body[:500])
            if code_match:
                email_info['code'] = code_match.group()
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
        "---"
    ]
    
    if verification_emails:
        report.append("### 🔑 验证码与登录凭证")
        for e in verification_emails:
            code_str = f" **[提取码: {e.get('code')}]**" if 'code' in e else ""
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
        for e in other_emails[:5]: # Only show top 5 others to avoid clutter
            report.append(f"- {e['sender']}: {e['subject']}")
        if len(other_emails) > 5:
            report.append(f"- *(还有 {len(other_emails) - 5} 封常规邮件未展示)*")
            
    report.append("\n*提示: 您可以通过 `read <message_id>` 查看上述任一邮件的完整内容。*")
    
    print("\n".join(report))

def main():
    parser = argparse.ArgumentParser(description="Mail Manager CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # fetch
    fetch_p = subparsers.add_parser("fetch", help="Fetch emails from server asynchronously")
    fetch_p.add_argument("--account", help="Email account to use")
    fetch_p.add_argument("--folder", default="INBOX", help="Folder to fetch from")
    fetch_p.add_argument("--limit", type=int, default=50, help="Max emails to fetch")
    fetch_p.add_argument("--days", type=int, default=7, help="Fetch emails from last N days")
    fetch_p.add_argument("--unread", action="store_true", help="Fetch only unread emails")
    fetch_p.add_argument("--confirm", action="store_true", help="Confirm fetching more than 100 emails")
    
    # fetch-status
    fetch_status_p = subparsers.add_parser("fetch-status", help="Check status of an async fetch task")
    fetch_status_p.add_argument("task_id", help="Task ID returned by the fetch command")
    
    # search
    search_p = subparsers.add_parser("search", help="Search local emails")
    search_p.add_argument("--query", help="Text to search in subject/body/sender")
    search_p.add_argument("--account", help="Filter by account")
    search_p.add_argument("--folder", help="Filter by folder")
    search_p.add_argument("--sender", help="Filter by sender")
    search_p.add_argument("--subject", help="Filter by subject")
    search_p.add_argument("--is-read", type=int, choices=[0, 1], help="1 for read, 0 for unread")
    search_p.add_argument("--has-attachment", type=int, choices=[0, 1], help="1 for has attachment")
    search_p.add_argument("--limit", type=int, default=20, help="Max results")
    
    # read
    read_p = subparsers.add_parser("read", help="Read a specific email by message_id")
    read_p.add_argument("message_id", help="Message ID to read")
    
    # send
    send_p = subparsers.add_parser("send", help="Send an email")
    send_p.add_argument("--account", help="Account to send from")
    send_p.add_argument("--to", required=True, help="Recipient email")
    send_p.add_argument("--subject", required=True, help="Email subject")
    send_p.add_argument("--body", required=True, help="Email body text")
    send_p.add_argument("--cc", help="CC email addresses")
    send_p.add_argument("--attach", nargs="+", help="Paths to attachments")
    
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
    
    # summarize
    sum_p = subparsers.add_parser("summarize", help="Generate a professional markdown summary of emails")
    sum_p.add_argument("--task-id", help="Summarize emails from a specific fetch task ID")
    sum_p.add_argument("--limit", type=int, default=10, help="Number of recent emails to summarize if no task-id is provided")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    config = load_config()
    db = MailDatabase(config['DB_PATH'])
    
    if args.command == "fetch":
        cmd_fetch(args, config, db)
    elif args.command == "fetch-status":
        cmd_fetch_status(args, config, db)
    elif args.command == "search":
        cmd_search(args, config, db)
    elif args.command == "read":
        cmd_read(args, config, db)
    elif args.command == "send":
        cmd_send(args, config, db)
    elif args.command == "mark":
        cmd_mark(args, config, db)
    elif args.command == "move":
        cmd_move(args, config, db)
    elif args.command == "delete":
        cmd_delete(args, config, db)
    elif args.command == "export":
        cmd_export(args, config, db)
    elif args.command == "summarize":
        cmd_summarize(args, config, db)

if __name__ == "__main__":
    main()
