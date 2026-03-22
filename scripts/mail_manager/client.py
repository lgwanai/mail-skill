import os
import email
from email.message import EmailMessage
from email.policy import default
import smtplib
import imap_tools
from imap_tools import MailBox, A
import imaplib
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class MailClient:
    def __init__(self, account_config):
        self.config = account_config
        self.email = self.config.get('EMAIL')
        self.password = self.config.get('PASSWORD')
        
    def _get_mailbox(self):
        """Returns a connected MailBox instance"""
        imap_server = self.config.get('IMAP_SERVER')
        imap_port = int(self.config.get('IMAP_PORT', 993))
        
        # We assume SSL is used if port is 993 or use_ssl is true
        use_ssl = str(self.config.get('USE_SSL', 'true')).lower() == 'true' or imap_port == 993
        
        try:
            print(f"Connecting to {imap_server}:{imap_port} (is_netease={any(domain in imap_server.lower() for domain in ['163.com', '126.com', 'yeah.net'])}, use_ssl={use_ssl})")
            
            # Standard connection for all providers
            mailbox = MailBox(imap_server, port=imap_port)
            
            # Special handling for Netease (163/126/yeah) mail servers
            # They require an ID command before LOGIN to avoid "Unsafe Login" errors
            is_netease = any(domain in imap_server.lower() for domain in ['163.com', '126.com', 'yeah.net'])
            if is_netease:
                try:
                    mailbox.client._simple_command('ID', '("name" "PythonMailClient" "version" "1.0")')
                except Exception:
                    tag = mailbox.client._new_tag()
                    mailbox.client.send(f'{tag} ID ("name" "PythonMailClient" "version" "1.0")\r\n'.encode())
                    while True:
                        line = mailbox.client.readline()
                        if tag in line:
                            break
            
            # Now login
            mailbox.login(self.email, self.password)
            return mailbox
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Failed to connect to IMAP server {imap_server}: {e}")
            raise

    def fetch_emails(self, folder='INBOX', limit=50, days_back=None, unread_only=False, since_date=None, db_check_func=None):
        """
        Fetch emails from server.
        db_check_func: A function that takes a message_id and returns True if it exists in local DB.
        """
        results = []
        try:
            with self._get_mailbox() as mailbox:
                mailbox.folder.set(folder)
                
                # Build search criteria
                criteria = []
                if unread_only:
                    criteria.append(A(seen=False))
                if since_date:
                    criteria.append(A(date_gte=since_date))
                elif days_back:
                    from datetime import datetime, timedelta
                    d = (datetime.now() - timedelta(days=days_back)).date()
                    criteria.append(A(date_gte=d))
                    
                if not criteria:
                    search_criteria = A(all=True)
                else:
                    search_criteria = A(*criteria) if len(criteria) > 1 else criteria[0]
                
                # We iterate in reverse order to get newest first
                # imap_tools doesn't support reverse directly in fetch, we can use reverse=True
                for msg in mailbox.fetch(search_criteria, limit=limit, reverse=True, mark_seen=False):
                    # Usually msg.uid is what we want for IMAP operations, but message-id is better for global DB
                    # imap_tools uses headers for message-id
                    msg_id_header = msg.headers.get('message-id', ('',))[0] if isinstance(msg.headers.get('message-id'), tuple) else msg.headers.get('message-id', '')
                    global_msg_id = msg_id_header if msg_id_header else f"{self.email}-{folder}-{msg.uid}"
                    
                    if db_check_func and db_check_func(global_msg_id):
                        logger.debug(f"Message {global_msg_id} already exists locally, skipping.")
                        continue
                        
                    # Parse body text
                    body_text = msg.text or ''
                    if not body_text and msg.html:
                        soup = BeautifulSoup(msg.html, 'html.parser')
                        body_text = soup.get_text(separator='\n', strip=True)
                        
                    email_data = {
                        'message_id': global_msg_id,
                        'imap_uid': msg.uid, # Need this for IMAP operations like mark read/delete
                        'account': self.email,
                        'thread_id': msg.headers.get('thread-index', ('',))[0] if isinstance(msg.headers.get('thread-index'), tuple) else msg.headers.get('thread-index', ''),
                        'subject': msg.subject,
                        'sender': msg.from_,
                        'recipient': ', '.join(msg.to),
                        'cc': ', '.join(msg.cc),
                        'date': msg.date,
                        'body_text': body_text,
                        'html_body': msg.html,
                        'has_attachment': len(msg.attachments) > 0,
                        'is_read': 'SEEN' in [flag.upper() for flag in msg.flags],
                        'is_starred': 'FLAGGED' in [flag.upper() for flag in msg.flags],
                        'labels': msg.flags,
                        'folder': folder,
                        'raw_email': msg.obj, # email.message.Message object
                        'attachments': msg.attachments
                    }
                    results.append(email_data)
                    
            return results
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            raise

    def send_email(self, to, subject, body_text, html_body=None, cc=None, bcc=None, attachments=None):
        """Send an email via SMTP"""
        smtp_server = self.config.get('SMTP_SERVER')
        smtp_port = int(self.config.get('SMTP_PORT', 465))
        use_ssl = str(self.config.get('USE_SSL', 'true')).lower() == 'true' or smtp_port == 465
        
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.email
        msg['To'] = to
        if cc:
            msg['Cc'] = cc
        if bcc:
            msg['Bcc'] = bcc
            
        if html_body:
            msg.set_content(body_text)
            msg.add_alternative(html_body, subtype='html')
        else:
            msg.set_content(body_text)
            
        if attachments:
            for filepath in attachments:
                import mimetypes
                ctype, encoding = mimetypes.guess_type(filepath)
                if ctype is None or encoding is not None:
                    ctype = 'application/octet-stream'
                maintype, subtype = ctype.split('/', 1)
                
                with open(filepath, 'rb') as f:
                    msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=os.path.basename(filepath))
                    
        try:
            if use_ssl:
                with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                    server.login(self.email, self.password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(self.email, self.password)
                    server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise

    def mark_as_read(self, uids, folder='INBOX', is_read=True):
        """Mark emails as read/unread"""
        if not uids:
            return
        with self._get_mailbox() as mailbox:
            mailbox.folder.set(folder)
            mailbox.flag(uids, imap_tools.MailMessageFlags.SEEN, is_read)

    def mark_as_starred(self, uids, folder='INBOX', is_starred=True):
        """Mark emails as starred/unstarred"""
        if not uids:
            return
        with self._get_mailbox() as mailbox:
            mailbox.folder.set(folder)
            mailbox.flag(uids, imap_tools.MailMessageFlags.FLAGGED, is_starred)
            
    def create_folder(self, folder_name):
        """Create a new folder on the server"""
        try:
            with self._get_mailbox() as mailbox:
                if not mailbox.folder.exists(folder_name):
                    mailbox.folder.create(folder_name)
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to create folder {folder_name}: {e}")
            raise

    def move_emails(self, uids, destination_folder, source_folder='INBOX'):
        """Move emails to another folder"""
        if not uids:
            return
        
        # Try to create folder first, ignore if it already exists
        try:
            self.create_folder(destination_folder)
        except:
            pass
            
        with self._get_mailbox() as mailbox:
            mailbox.folder.set(source_folder)
            mailbox.move(uids, destination_folder)

    def delete_emails(self, uids, folder='INBOX'):
        """Delete emails (move to Trash usually, or permanently delete depending on server)"""
        if not uids:
            return
        with self._get_mailbox() as mailbox:
            mailbox.folder.set(folder)
            mailbox.delete(uids)
