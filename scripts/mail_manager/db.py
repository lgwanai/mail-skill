import sqlite3
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MailDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        os.makedirs(os.path.dirname(self.db_path) or '.', exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT UNIQUE,
                    account TEXT,
                    thread_id TEXT,
                    subject TEXT,
                    sender TEXT,
                    recipient TEXT,
                    cc TEXT,
                    date DATETIME,
                    body_text TEXT,
                    has_attachment BOOLEAN,
                    is_read BOOLEAN,
                    is_starred BOOLEAN,
                    labels TEXT,
                    folder TEXT,
                    local_path_eml TEXT,
                    local_path_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT,
                    filename TEXT,
                    content_type TEXT,
                    size INTEGER,
                    local_path TEXT,
                    FOREIGN KEY (message_id) REFERENCES emails (message_id)
                )
            ''')
            
            # Indexes for fast search
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_id ON emails(message_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_account ON emails(account)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON emails(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sender ON emails(sender)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_subject ON emails(subject)')
            conn.commit()

    def exists(self, message_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM emails WHERE message_id = ?', (message_id,))
            return cursor.fetchone() is not None

    def save_email(self, email_data):
        """Save or update email in the database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Convert list of labels to JSON string
            labels = json.dumps(email_data.get('labels', []))
            
            cursor.execute('''
                INSERT INTO emails (
                    message_id, account, thread_id, subject, sender, recipient, cc, 
                    date, body_text, has_attachment, is_read, is_starred, labels, folder, 
                    local_path_eml, local_path_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    is_read=excluded.is_read,
                    is_starred=excluded.is_starred,
                    labels=excluded.labels,
                    folder=excluded.folder
            ''', (
                email_data.get('message_id'),
                email_data.get('account'),
                email_data.get('thread_id'),
                email_data.get('subject', ''),
                email_data.get('sender', ''),
                email_data.get('recipient', ''),
                email_data.get('cc', ''),
                email_data.get('date'),
                email_data.get('body_text', ''),
                email_data.get('has_attachment', False),
                email_data.get('is_read', False),
                email_data.get('is_starred', False),
                labels,
                email_data.get('folder', 'INBOX'),
                email_data.get('local_path_eml'),
                email_data.get('local_path_json')
            ))
            
            # Save attachments
            if 'attachments' in email_data and email_data['attachments']:
                # Clear existing attachments for this message to avoid duplicates on update
                cursor.execute('DELETE FROM attachments WHERE message_id = ?', (email_data.get('message_id'),))
                
                for att in email_data['attachments']:
                    cursor.execute('''
                        INSERT INTO attachments (message_id, filename, content_type, size, local_path)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        email_data.get('message_id'),
                        att.get('filename'),
                        att.get('content_type'),
                        att.get('size', 0),
                        att.get('local_path')
                    ))
            
            conn.commit()
            
    def search_emails(self, query=None, account=None, folder=None, sender=None, 
                      subject=None, date_from=None, date_to=None, has_attachment=None,
                      is_read=None, limit=100, offset=0):
        """Search emails based on criteria"""
        sql = "SELECT * FROM emails WHERE 1=1"
        params = []
        
        if account:
            sql += " AND account = ?"
            params.append(account)
            
        if folder:
            sql += " AND folder = ?"
            params.append(folder)
            
        if sender:
            sql += " AND sender LIKE ?"
            params.append(f"%{sender}%")
            
        if subject:
            sql += " AND subject LIKE ?"
            params.append(f"%{subject}%")
            
        if date_from:
            sql += " AND date >= ?"
            params.append(date_from)
            
        if date_to:
            sql += " AND date <= ?"
            params.append(date_to)
            
        if has_attachment is not None:
            sql += " AND has_attachment = ?"
            params.append(has_attachment)
            
        if is_read is not None:
            sql += " AND is_read = ?"
            params.append(is_read)
            
        if query:
            sql += " AND (subject LIKE ? OR body_text LIKE ? OR sender LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
            
        sql += " ORDER BY date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                email_dict = dict(row)
                email_dict['labels'] = json.loads(email_dict['labels']) if email_dict['labels'] else []
                
                # Fetch attachments
                cursor.execute('SELECT * FROM attachments WHERE message_id = ?', (email_dict['message_id'],))
                att_rows = cursor.fetchall()
                email_dict['attachments'] = [dict(att) for att in att_rows]
                
                result.append(email_dict)
                
            return result

    def get_email(self, message_id):
        """Get a single email by message_id"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM emails WHERE message_id = ?', (message_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            email_dict = dict(row)
            email_dict['labels'] = json.loads(email_dict['labels']) if email_dict['labels'] else []
            
            cursor.execute('SELECT * FROM attachments WHERE message_id = ?', (message_id,))
            att_rows = cursor.fetchall()
            email_dict['attachments'] = [dict(att) for att in att_rows]
            
            return email_dict

    def update_flags(self, message_id, is_read=None, is_starred=None, labels=None, folder=None):
        """Update flags or folder of an email"""
        updates = []
        params = []
        
        if is_read is not None:
            updates.append("is_read = ?")
            params.append(is_read)
            
        if is_starred is not None:
            updates.append("is_starred = ?")
            params.append(is_starred)
            
        if labels is not None:
            updates.append("labels = ?")
            params.append(json.dumps(labels))
            
        if folder is not None:
            updates.append("folder = ?")
            params.append(folder)
            
        if not updates:
            return
            
        sql = f"UPDATE emails SET {', '.join(updates)} WHERE message_id = ?"
        params.append(message_id)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()

    def delete_email(self, message_id):
        """Delete an email from database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM attachments WHERE message_id = ?', (message_id,))
            cursor.execute('DELETE FROM emails WHERE message_id = ?', (message_id,))
            conn.commit()
