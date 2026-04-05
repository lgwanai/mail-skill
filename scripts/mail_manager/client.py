from __future__ import annotations

import os
import smtplib
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from typing import TYPE_CHECKING, Any, Callable

import imap_tools
from bs4 import BeautifulSoup
from imap_tools import A

if TYPE_CHECKING:
    from imap_tools import MailBox

logger = __import__("logging").getLogger(__name__)


class MailClient:
    """Client for IMAP and SMTP email operations."""

    def __init__(self, account_config: dict[str, Any]) -> None:
        self.config = account_config
        self.email: str | None = self.config.get("EMAIL")
        self.password: str | None = self.config.get("PASSWORD")

    def _get_mailbox(self) -> MailBox:
        """Returns a connected MailBox instance."""
        imap_server = self.config.get("IMAP_SERVER")
        imap_port = int(self.config.get("IMAP_PORT", 993))

        # We assume SSL is used if port is 993 or use_ssl is true
        use_ssl = str(self.config.get("USE_SSL", "true")).lower() == "true" or imap_port == 993

        try:
            print(
                f"Connecting to {imap_server}:{imap_port} (is_netease={any(domain in str(imap_server).lower() for domain in ['163.com', '126.com', 'yeah.net'])}, use_ssl={use_ssl})"
            )

            # Standard connection for all providers
            mailbox = imap_tools.MailBox(str(imap_server), port=imap_port)

            # Special handling for Netease (163/126/yeah) mail servers
            # They require an ID command before LOGIN to avoid "Unsafe Login" errors
            is_netease = any(
                domain in str(imap_server).lower() for domain in ["163.com", "126.com", "yeah.net"]
            )
            if is_netease:
                try:
                    mailbox.client._simple_command(
                        "ID", '("name" "PythonMailClient" "version" "1.0")'
                    )  # type: ignore[attr-defined]
                except Exception:
                    tag = mailbox.client._new_tag()  # type: ignore[attr-defined]
                    mailbox.client.send(
                        f'{tag} ID ("name" "PythonMailClient" "version" "1.0")\r\n'.encode()
                    )  # type: ignore[attr-defined]
                    while True:
                        line = mailbox.client.readline()  # type: ignore[attr-defined]
                        if tag in line:
                            break

            # Now login
            mailbox.login(str(self.email), str(self.password))
            return mailbox

        except Exception as e:
            import traceback

            traceback.print_exc()
            logger.error(f"Failed to connect to IMAP server {imap_server}: {e}")
            raise

    def fetch_emails(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        days_back: int | None = None,
        unread_only: bool = False,
        since_date: date | None = None,
        db_check_func: Callable[[str], bool] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch emails from server.

        Args:
            folder: Folder name(s), comma-separated, or 'ALL' for all folders.
            limit: Maximum number of emails to fetch per folder.
            days_back: Number of days back to fetch emails from.
            unread_only: Only fetch unread emails.
            since_date: Fetch emails from this date onwards.
            db_check_func: A function that takes a message_id and returns True if it exists in local DB.

        Returns:
            List of email data dictionaries.
        """
        results: list[dict[str, Any]] = []
        try:
            with self._get_mailbox() as mailbox:
                folders_to_fetch: list[str] = []
                if folder.upper() == "ALL":
                    folders_to_fetch = [f.name for f in mailbox.folder.list()]
                else:
                    folders_to_fetch = [f.strip() for f in folder.split(",")]

                for current_folder in folders_to_fetch:
                    try:
                        mailbox.folder.set(current_folder)
                    except Exception as e:
                        logger.warning(f"Could not set folder {current_folder}: {e}")
                        continue

                    # Build search criteria
                    criteria: list[Any] = []
                    if unread_only:
                        criteria.append(A(seen=False))
                    if since_date:
                        criteria.append(A(date_gte=since_date))
                    elif days_back:
                        d = (datetime.now() - timedelta(days=days_back)).date()
                        criteria.append(A(date_gte=d))

                    if not criteria:
                        search_criteria = A(all=True)
                    else:
                        search_criteria = A(*criteria) if len(criteria) > 1 else criteria[0]

                    # We iterate in reverse order to get newest first
                    # imap_tools doesn't support reverse directly in fetch, we can use reverse=True
                    for msg in mailbox.fetch(
                        search_criteria, limit=limit, reverse=True, mark_seen=False
                    ):
                        # Usually msg.uid is what we want for IMAP operations, but message-id is better for global DB
                        # imap_tools uses headers for message-id
                        msg_id_header = (
                            msg.headers.get("message-id", ("",))[0]
                            if isinstance(msg.headers.get("message-id"), tuple)
                            else msg.headers.get("message-id", "")
                        )
                        in_reply_to_header = (
                            msg.headers.get("in-reply-to", ("",))[0]
                            if isinstance(msg.headers.get("in-reply-to"), tuple)
                            else msg.headers.get("in-reply-to", "")
                        )
                        references_header = (
                            msg.headers.get("references", ("",))[0]
                            if isinstance(msg.headers.get("references"), tuple)
                            else msg.headers.get("references", "")
                        )
                        import re

                        refs: list[str] = []
                        if references_header:
                            refs = re.findall(r"<([^>]+)>", str(references_header))
                            if not refs:
                                refs = [
                                    x.strip() for x in str(references_header).split() if x.strip()
                                ]
                        in_reply_to_norm = ""
                        if in_reply_to_header:
                            m = str(in_reply_to_header).strip()
                            if m.startswith("<") and m.endswith(">"):
                                m = m[1:-1]
                            in_reply_to_norm = m
                        global_msg_id = (
                            str(msg_id_header)
                            if msg_id_header
                            else f"{self.email}-{current_folder}-{msg.uid}"
                        )

                        if db_check_func and db_check_func(global_msg_id):
                            logger.debug(
                                f"Message {global_msg_id} already exists locally, skipping."
                            )
                            continue

                        # Parse body text
                        body_text = msg.text or ""
                        if not body_text and msg.html:
                            soup = BeautifulSoup(msg.html, "html.parser")
                            body_text = soup.get_text(separator="\n", strip=True)

                        email_data: dict[str, Any] = {
                            "message_id": global_msg_id,
                            "imap_uid": msg.uid,  # Need this for IMAP operations like mark read/delete
                            "account": self.email,
                            "thread_id": msg.headers.get("thread-index", ("",))[0]
                            if isinstance(msg.headers.get("thread-index"), tuple)
                            else msg.headers.get("thread-index", ""),
                            "in_reply_to": in_reply_to_norm,
                            "references": ",".join(refs) if refs else "",
                            "subject": msg.subject,
                            "sender": msg.from_,
                            "recipient": ", ".join(msg.to),
                            "cc": ", ".join(msg.cc),
                            "date": msg.date,
                            "body_text": body_text,
                            "html_body": msg.html,
                            "has_attachment": len(msg.attachments) > 0,
                            "is_read": "SEEN" in [flag.upper() for flag in msg.flags],
                            "is_starred": "FLAGGED" in [flag.upper() for flag in msg.flags],
                            "labels": msg.flags,
                            "folder": current_folder,
                            "raw_email": msg.obj,  # email.message.Message object
                            "attachments": msg.attachments,
                        }
                        results.append(email_data)

            return results
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            raise

    def send_email(
        self,
        to: str | list[str],
        subject: str,
        body_text: str,
        html_body: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        attachments: list[str] | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
    ) -> bool:
        """
        Send an email via SMTP.

        Args:
            to: Recipient email address(es).
            subject: Email subject.
            body_text: Plain text body.
            html_body: Optional HTML body.
            cc: Optional CC recipient(s).
            bcc: Optional BCC recipient(s).
            attachments: Optional list of file paths to attach.
            in_reply_to: Optional message-id this email replies to.
            references: Optional references header for threading.

        Returns:
            True if email was sent successfully.
        """
        smtp_server = self.config.get("SMTP_SERVER")
        smtp_port = int(self.config.get("SMTP_PORT", 465))
        use_ssl = str(self.config.get("USE_SSL", "true")).lower() == "true" or smtp_port == 465

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.email

        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references

        # Handle multiple recipients
        if isinstance(to, list):
            msg["To"] = ", ".join(to)
        else:
            msg["To"] = to

        if cc:
            if isinstance(cc, list):
                msg["Cc"] = ", ".join(cc)
            else:
                msg["Cc"] = cc

        if bcc:
            if isinstance(bcc, list):
                msg["Bcc"] = ", ".join(bcc)
            else:
                msg["Bcc"] = bcc

        if html_body:
            msg.set_content(body_text)
            msg.add_alternative(html_body, subtype="html")
        else:
            msg.set_content(body_text)

        if attachments:
            for filepath in attachments:
                import mimetypes

                ctype, encoding = mimetypes.guess_type(filepath)
                if ctype is None or encoding is not None:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)

                with open(filepath, "rb") as f:
                    msg.add_attachment(
                        f.read(),
                        maintype=maintype,
                        subtype=subtype,
                        filename=os.path.basename(filepath),
                    )

        try:
            if use_ssl:
                with smtplib.SMTP_SSL(str(smtp_server), smtp_port) as server:
                    server.login(str(self.email), str(self.password))
                    server.send_message(msg)
            else:
                with smtplib.SMTP(str(smtp_server), smtp_port) as server:
                    server.starttls()
                    server.login(str(self.email), str(self.password))
                    server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise

    def mark_as_read(self, uids: list[str], folder: str = "INBOX", is_read: bool = True) -> None:
        """
        Mark emails as read/unread.

        Args:
            uids: List of IMAP UIDs to mark.
            folder: Folder containing the emails.
            is_read: True to mark as read, False to mark as unread.
        """
        if not uids:
            return
        with self._get_mailbox() as mailbox:
            mailbox.folder.set(folder)
            mailbox.flag(uids, imap_tools.MailMessageFlags.SEEN, is_read)  # type: ignore[attr-defined]

    def mark_as_starred(
        self, uids: list[str], folder: str = "INBOX", is_starred: bool = True
    ) -> None:
        """
        Mark emails as starred/unstarred.

        Args:
            uids: List of IMAP UIDs to mark.
            folder: Folder containing the emails.
            is_starred: True to star, False to unstar.
        """
        if not uids:
            return
        with self._get_mailbox() as mailbox:
            mailbox.folder.set(folder)
            mailbox.flag(uids, imap_tools.MailMessageFlags.FLAGGED, is_starred)  # type: ignore[attr-defined]

    def create_folder(self, folder_name: str) -> bool:
        """
        Create a new folder on the server.

        Args:
            folder_name: Name of the folder to create.

        Returns:
            True if folder was created, False if it already exists.
        """
        try:
            with self._get_mailbox() as mailbox:
                if not mailbox.folder.exists(folder_name):
                    mailbox.folder.create(folder_name)
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to create folder {folder_name}: {e}")
            raise

    def move_emails(
        self, uids: list[str], destination_folder: str, source_folder: str = "INBOX"
    ) -> None:
        """
        Move emails to another folder.

        Args:
            uids: List of IMAP UIDs to move.
            destination_folder: Target folder name.
            source_folder: Source folder name.
        """
        if not uids:
            return

        # Try to create folder first, ignore if it already exists
        try:
            self.create_folder(destination_folder)
        except Exception:
            pass

        with self._get_mailbox() as mailbox:
            mailbox.folder.set(source_folder)
            mailbox.move(uids, destination_folder)

    def delete_emails(self, uids: list[str], folder: str = "INBOX") -> None:
        """
        Delete emails (move to Trash usually, or permanently delete depending on server).

        Args:
            uids: List of IMAP UIDs to delete.
            folder: Folder containing the emails.
        """
        if not uids:
            return
        with self._get_mailbox() as mailbox:
            mailbox.folder.set(folder)
            mailbox.delete(uids)
