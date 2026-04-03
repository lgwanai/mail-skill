from __future__ import annotations

import sqlite3
import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

class MailDatabase:
    """Manages email storage in SQLite and ChromaDB for vector search."""

    def __init__(self, db_path: str) -> None:
        """Initialize the database with the given path.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._init_db()
        self._chroma_client: Optional[Any] = None
        self._collection: Optional[Any] = None

    def _get_chroma_collection(self) -> Any:
        if self._collection is None:
            chroma_dir = os.path.join(os.path.dirname(self.db_path), 'chroma_db')
            os.makedirs(chroma_dir, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(path=chroma_dir)
            
            # Use environment variables to configure embedding function if available
            api_key = os.getenv('OPENAI_API_KEY')
            api_base = os.getenv('OPENAI_API_BASE')
            if api_key:
                # Some OpenAI compatible endpoints (like siliconflow) might need adjusting the path
                # Standard OpenAI path is /v1/embeddings, but chromadb appends /embeddings automatically
                # So we should be careful with OPENAI_API_BASE
                if api_base and api_base.endswith('/embeddings'):
                    api_base = api_base[:-11] # Remove /embeddings so chromadb can append it
                
                ef = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=api_key,
                    api_base=api_base,
                    model_name=os.getenv('EMBEDDING_MODEL_NAME', 'text-embedding-3-small')
                )
            else:
                # Default to local model, allow override via EMBEDDING_MODEL_NAME
                local_model = os.getenv('EMBEDDING_MODEL_NAME', 'all-MiniLM-L6-v2')
                if local_model == 'all-MiniLM-L6-v2':
                    ef = embedding_functions.DefaultEmbeddingFunction()
                else:
                    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=local_model)
                
            self._collection = self._chroma_client.get_or_create_collection(
                name="emails",
                embedding_function=ef
            )
        return self._collection

    def _get_connection(self) -> sqlite3.Connection:
        """Get a SQLite connection with row factory.

        Returns:
            sqlite3.Connection: A connection with Row factory enabled.
        """
        os.makedirs(os.path.dirname(self.db_path) or '.', exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database schema including tables, indexes, and FTS."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT UNIQUE,
                    imap_uid TEXT,
                    account TEXT,
                    thread_id TEXT,
                    in_reply_to TEXT,
                "references" TEXT,
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
            
            # Migration: add columns if they don't exist
            cursor.execute("PRAGMA table_info(emails)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'imap_uid' not in columns:
                cursor.execute("ALTER TABLE emails ADD COLUMN imap_uid TEXT")
            if 'in_reply_to' not in columns:
                cursor.execute("ALTER TABLE emails ADD COLUMN in_reply_to TEXT")
            if '"references"' not in columns and 'references' not in columns:
                cursor.execute('ALTER TABLE emails ADD COLUMN "references" TEXT')

            
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
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_in_reply_to ON emails(in_reply_to)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_references ON emails("references")')
            
            # Create FTS5 virtual table for full-text search
            try:
                cursor.execute('''
                    CREATE VIRTUAL TABLE IF NOT EXISTS emails_fts USING fts5(
                        subject, body_text, sender, recipient, cc,
                        content='emails', content_rowid='id'
                    )
                ''')
                # Triggers to keep FTS in sync
                cursor.execute('''
                    CREATE TRIGGER IF NOT EXISTS emails_ai AFTER INSERT ON emails BEGIN
                        INSERT INTO emails_fts(rowid, subject, body_text, sender, recipient, cc)
                        VALUES (new.id, new.subject, new.body_text, new.sender, new.recipient, new.cc);
                    END;
                ''')
                cursor.execute('''
                    CREATE TRIGGER IF NOT EXISTS emails_au AFTER UPDATE ON emails BEGIN
                        UPDATE emails_fts SET subject=new.subject, body_text=new.body_text, sender=new.sender, recipient=new.recipient, cc=new.cc
                        WHERE rowid=new.id;
                    END;
                ''')
                cursor.execute('''
                    CREATE TRIGGER IF NOT EXISTS emails_ad AFTER DELETE ON emails BEGIN
                        DELETE FROM emails_fts WHERE rowid=old.id;
                    END;
                ''')
            except sqlite3.OperationalError:
                pass
                
            # Auto-rebuild FTS5 if it's empty but emails exist
            try:
                cursor.execute("SELECT count(*) FROM emails_fts")
                fts_count = cursor.fetchone()[0]
                if fts_count == 0:
                    cursor.execute("SELECT count(*) FROM emails")
                    email_count = cursor.fetchone()[0]
                    if email_count > 0:
                        logger.info("FTS5 index is empty. Rebuilding...")
                        cursor.execute("INSERT INTO emails_fts(emails_fts) VALUES('rebuild')")
            except Exception as e:
                logger.warning(f"Failed to check or rebuild FTS5 index: {e}")
                
            conn.commit()

    def exists(self, message_id: str) -> bool:
        """Check if an email with the given message_id exists.

        Args:
            message_id: The email message ID to check.

        Returns:
            bool: True if email exists, False otherwise.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM emails WHERE message_id = ?', (message_id,))
            return cursor.fetchone() is not None

    def save_email(self, email_data: dict) -> None:
        """Save or update email in the database.

        Args:
            email_data: Dictionary containing email data.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Convert list of labels to JSON string
            labels = json.dumps(email_data.get('labels', []))
            
            cursor.execute('''
                INSERT INTO emails (
                    message_id, imap_uid, account, thread_id, in_reply_to, "references", subject, sender, recipient, cc, 
                    date, body_text, has_attachment, is_read, is_starred, labels, folder, 
                    local_path_eml, local_path_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    imap_uid=excluded.imap_uid,
                    in_reply_to=excluded.in_reply_to,
                    "references"=excluded."references",
                    is_read=excluded.is_read,
                    is_starred=excluded.is_starred,
                    labels=excluded.labels,
                    folder=excluded.folder
            ''', (
                email_data.get('message_id'),
                email_data.get('imap_uid'),
                email_data.get('account'),
                email_data.get('thread_id'),
                email_data.get('in_reply_to'),
                email_data.get('references'),
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

            # Save to ChromaDB for vector search
            try:
                collection = self._get_chroma_collection()
                doc_text = f"Subject: {email_data.get('subject', '')}\nFrom: {email_data.get('sender', '')}\nDate: {email_data.get('date', '')}\n\n{email_data.get('body_text', '')}"
                
                # Truncate text if too long to avoid token limits
                if len(doc_text) > 8000:
                    doc_text = doc_text[:8000]
                    
                metadata = {
                    "subject": email_data.get('subject', '') or '',
                    "sender": email_data.get('sender', '') or '',
                    "date": str(email_data.get('date', ''))
                }
                
                collection.upsert(
                    ids=[email_data.get('message_id')],
                    documents=[doc_text],
                    metadatas=[metadata]
                )
            except Exception as e:
                logger.warning(f"Failed to save email to ChromaDB: {e}")

    def search_fts(self, query: str, limit: int = 100, offset: int = 0) -> list[dict]:
        """Full-text search for emails using FTS5 or LIKE fallback.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.
            offset: Number of results to skip.

        Returns:
            list[dict]: List of matching email dictionaries.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = []
            
            # 1. Try FTS5 first (fast for English/exact matches)
            try:
                # Safely escape quotes for FTS5 syntax
                safe_query = query.replace('"', '""')
                # For exact phrase match and preventing operator syntax errors (e.g. from hyphens)
                match_query = f'"{safe_query}"'
                
                cursor.execute('''
                    SELECT e.* FROM emails_fts f
                    JOIN emails e ON e.id = f.rowid
                    WHERE emails_fts MATCH ?
                    ORDER BY e.date DESC LIMIT ? OFFSET ?
                ''', (match_query, limit, offset))
                rows = cursor.fetchall()
            except Exception as e:
                logger.warning(f"FTS5 search failed or syntax error: {e}")
                
            # 2. Fallback to LIKE search (crucial for Chinese/CJK characters and partial word matches)
            if not rows:
                logger.info("FTS returned no results, falling back to LIKE search...")
                cursor.execute('''
                    SELECT * FROM emails 
                    WHERE subject LIKE ? OR body_text LIKE ? OR sender LIKE ?
                    ORDER BY date DESC LIMIT ? OFFSET ?
                ''', (f'%{query}%', f'%{query}%', f'%{query}%', limit, offset))
                rows = cursor.fetchall()

            result = []
            for row in rows:
                email_dict = dict(row)
                email_dict['labels'] = json.loads(email_dict['labels']) if email_dict['labels'] else []
                cursor.execute('SELECT * FROM attachments WHERE message_id = ?', (email_dict['message_id'],))
                att_rows = cursor.fetchall()
                email_dict['attachments'] = [dict(att) for att in att_rows]
                result.append(email_dict)
            return result

    def search_vector(self, query: str, limit: int = 10) -> list[dict]:
        """Search emails using vector similarity.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.

        Returns:
            list[dict]: List of matching email dictionaries.
        """
        try:
            collection = self._get_chroma_collection()
            results = collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            if not results or not results['ids'] or not results['ids'][0]:
                return []
                
            message_ids = results['ids'][0]
            
            # Fetch full email data from SQLite
            emails = []
            for msg_id in message_ids:
                email = self.get_email(msg_id)
                if email:
                    emails.append(email)
            return emails
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def _get_reranker(self) -> Any:
        """Get or create the reranker model.

        Returns:
            CrossEncoder: The reranker model instance.
        """
        if not hasattr(self, '_reranker'):
            from sentence_transformers import CrossEncoder
            reranker_model_name = os.getenv('RERANKER_MODEL_NAME', 'BAAI/bge-reranker-base')
            # Initialize CrossEncoder (will be downloaded on first run if not cached)
            self._reranker = CrossEncoder(reranker_model_name)
        return self._reranker

    def search_hybrid(self, query: str, limit: int = 10) -> list[dict]:
        """Hybrid search combining FTS and Vector search, with Reranking.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.

        Returns:
            list[dict]: List of matching email dictionaries sorted by relevance.
        """
        # 1. Fetch candidates
        fts_results = self.search_fts(query, limit=limit*2)
        vec_results = self.search_vector(query, limit=limit*2)
        
        # 2. Merge and deduplicate
        merged_results = {}
        for r in fts_results:
            merged_results[r['message_id']] = r
        for r in vec_results:
            merged_results[r['message_id']] = r
            
        if not merged_results:
            return []
            
        emails = list(merged_results.values())
        
        # 3. Rerank
        try:
            reranker = self._get_reranker()
            pairs = []
            for email in emails:
                doc_text = f"Subject: {email.get('subject', '')}\nFrom: {email.get('sender', '')}\n\n{email.get('body_text', '')}"
                if len(doc_text) > 2000:
                    doc_text = doc_text[:2000]
                pairs.append([query, doc_text])
                
            scores = reranker.predict(pairs)
            
            for i, email in enumerate(emails):
                email['_rerank_score'] = float(scores[i])
                
            # Sort by score descending
            emails.sort(key=lambda x: x.get('_rerank_score', 0), reverse=True)
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            
        return emails[:limit]

    def get_thread_timeline(self, seed_message_id: str, limit: int = 100) -> list[dict]:
        """Get all emails in a thread starting from a seed message.

        Args:
            seed_message_id: The message ID to start from.
            limit: Maximum number of emails to return.

        Returns:
            list[dict]: List of emails in the thread, sorted by date.
        """
        def norm(mid: Optional[str]) -> str:
            if not mid:
                return ''
            m = mid.strip()
            if m.startswith('<') and m.endswith('>'):
                m = m[1:-1]
            return m.strip()
        seed_norm = norm(seed_message_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM emails WHERE message_id = ? OR message_id = ?', (seed_message_id, seed_norm))
            base_row = cursor.fetchone()
            if not base_row:
                return []
            base = dict(base_row)
            ids = set([norm(base['message_id'])])
            timeline = [base]
            visited = set([base['message_id']])
            while True:
                found_new = False
                q_marks = ','.join(['?'] * len(ids)) if ids else '?'
                params = list(ids) if ids else [seed_norm]
                cursor.execute(f'''
                    SELECT * FROM emails 
                    WHERE in_reply_to IN ({q_marks})
                       OR "references" LIKE '%' || ? || '%'
                    ORDER BY date ASC
                    LIMIT ?
                ''', (*params, seed_norm, limit))
                rows = cursor.fetchall()
                for r in rows:
                    em = dict(r)
                    if em['message_id'] in visited:
                        continue
                    timeline.append(em)
                    visited.add(em['message_id'])
                    ids.add(norm(em.get('message_id')))
                    found_new = True
                if not found_new or len(timeline) >= limit:
                    break
            timeline.sort(key=lambda x: x.get('date') or '')
            for i in range(len(timeline)):
                cursor.execute('SELECT * FROM attachments WHERE message_id = ?', (timeline[i]['message_id'],))
                att_rows = cursor.fetchall()
                timeline[i]['attachments'] = [dict(att) for att in att_rows]
            return timeline

    def search_emails(
        self,
        query: Optional[str] = None,
        account: Optional[str] = None,
        folder: Optional[str] = None,
        sender: Optional[str] = None,
        subject: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        has_attachment: Optional[bool] = None,
        is_read: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict]:
        """Search emails based on criteria.

        Args:
            query: Full-text search query.
            account: Filter by account email.
            folder: Filter by folder name.
            sender: Filter by sender email (partial match).
            subject: Filter by subject (partial match).
            date_from: Filter by start date.
            date_to: Filter by end date.
            has_attachment: Filter by attachment presence.
            is_read: Filter by read status.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            list[dict]: List of matching email dictionaries.
        """
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

    def get_email(self, message_id: str) -> Optional[dict]:
        """Get a single email by message_id.

        Args:
            message_id: The email message ID.

        Returns:
            Optional[dict]: Email dictionary or None if not found.
        """
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

    def update_flags(
        self,
        message_id: str,
        is_read: Optional[bool] = None,
        is_starred: Optional[bool] = None,
        labels: Optional[list] = None,
        folder: Optional[str] = None
    ) -> None:
        """Update flags or folder of an email.

        Args:
            message_id: The email message ID.
            is_read: New read status, if updating.
            is_starred: New starred status, if updating.
            labels: New list of labels, if updating.
            folder: New folder name, if updating.
        """
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

    def delete_email(self, message_id: str) -> None:
        """Delete an email from database.

        Args:
            message_id: The email message ID to delete.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM attachments WHERE message_id = ?', (message_id,))
            cursor.execute('DELETE FROM emails WHERE message_id = ?', (message_id,))
            conn.commit()
            
        try:
            collection = self._get_chroma_collection()
            collection.delete(ids=[message_id])
        except Exception as e:
            logger.warning(f"Failed to delete email from ChromaDB: {e}")
