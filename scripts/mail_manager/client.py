from __future__ import annotations

import email.utils
import logging
import os
import poplib
import re
import smtplib
import time
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from typing import TYPE_CHECKING, Any, Callable

import imap_tools
from bs4 import BeautifulSoup
from imap_tools import A

if TYPE_CHECKING:
    from imap_tools import MailBox

logger = logging.getLogger(__name__)


class MailClientError(Exception):
    """Raised when mail client operations fail."""


class POP3NotSupportedError(MailClientError):
    """Raised when an operation is not supported for POP3 protocol."""


class MissingCredentialsError(MailClientError):
    """Raised when required credentials are missing."""


class MailClient:
    """Client for IMAP/POP3 and SMTP email operations."""

    def __init__(self, account_config: dict[str, Any]) -> None:
        self.config = account_config
        self.email: str | None = self.config.get("EMAIL")
        self.password: str | None = self.config.get("PASSWORD")
        self.protocol: str = str(self.config.get("PROTOCOL", "imap")).lower()

        if self.protocol not in ("imap", "pop3"):
            raise MailClientError(
                f"Invalid protocol '{self.protocol}'. Must be 'imap' or 'pop3'."
            )

        if not self.email:
            raise MissingCredentialsError(
                "EMAIL is required in account configuration."
            )

        if not self.password:
            raise MissingCredentialsError(
                "PASSWORD is required in account configuration."
            )

    # -----------------------------------------------------------------
    # IMAP CONNECTION
    # -----------------------------------------------------------------
    def _get_mailbox(self) -> MailBox:
        imap_server = self.config.get("IMAP_SERVER")
        if not imap_server:
            raise MissingCredentialsError("IMAP_SERVER is required for IMAP protocol.")

        mailbox = None
        try:
            imap_port = int(self.config.get("IMAP_PORT", 993))
        except (ValueError, TypeError):
            imap_port = 993

        try:
            logger.info(f"Connecting to IMAP server {imap_server}:{imap_port}")

            mailbox = imap_tools.MailBox(str(imap_server), port=imap_port, timeout=30)

            is_netease = any(
                domain in str(imap_server).lower()
                for domain in ["163.com", "126.com", "yeah.net"]
            )
            if is_netease:
                self._send_netease_id(mailbox)

            mailbox.login(str(self.email), str(self.password))
            return mailbox

        except Exception as e:
            if mailbox is not None:
                try:
                    mailbox.logout()
                except Exception:
                    pass
            logger.error(f"Failed to connect to IMAP server {imap_server}: {e}")
            raise MailClientError(f"IMAP connection failed: {e}") from e

    @staticmethod
    def _send_netease_id(mailbox: MailBox) -> None:
        try:
            mailbox.client._simple_command(
                "ID", '("name" "PythonMailClient" "version" "1.0")'
            )  # type: ignore[attr-defined]
        except Exception:
            logger.debug("Netease ID via _simple_command failed, trying fallback")
            try:
                tag = mailbox.client._new_tag()  # type: ignore[attr-defined]
                if isinstance(tag, bytes):
                    tag_str = tag.decode()
                else:
                    tag_str = str(tag)
                mailbox.client.send(
                    f'{tag_str} ID ("name" "PythonMailClient" "version" "1.0")\r\n'.encode()
                )  # type: ignore[attr-defined]
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    line = mailbox.client.readline()  # type: ignore[attr-defined]
                    if tag_str.encode() in line:
                        return
                logger.warning("Netease ID command timed out, proceeding anyway.")
            except Exception:
                logger.warning("Netease ID fallback also failed, proceeding anyway.")

    # -----------------------------------------------------------------
    # POP3 CONNECTION
    # -----------------------------------------------------------------
    def _get_pop3_connection(self) -> poplib.POP3_SSL | poplib.POP3:
        pop3_server = self.config.get("POP3_SERVER")
        if not pop3_server:
            raise MissingCredentialsError("POP3_SERVER is required for POP3 protocol.")

        try:
            pop3_port = int(self.config.get("POP3_PORT", 995))
        except (ValueError, TypeError):
            pop3_port = 995
        use_ssl = str(self.config.get("USE_SSL", "true")).lower() == "true"

        try:
            logger.info(f"Connecting to POP3 server {pop3_server}:{pop3_port}")
            if use_ssl:
                conn = poplib.POP3_SSL(str(pop3_server), pop3_port, timeout=30)
            else:
                conn = poplib.POP3(str(pop3_server), pop3_port, timeout=30)

            conn.user(str(self.email))
            conn.pass_(str(self.password))
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to POP3 server {pop3_server}: {e}")
            raise MailClientError(f"POP3 connection failed: {e}") from e

    # -----------------------------------------------------------------
    # POP3 FETCH
    # -----------------------------------------------------------------
    def _fetch_emails_pop3(
        self,
        limit: int = 50,
        days_back: int | None = None,
        since_date: date | None = None,
        db_check_func: Callable[[str], bool] | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        conn = None
        try:
            conn = self._get_pop3_connection()
            num_messages = len(conn.list()[1])
            logger.info(f"Found {num_messages} messages in POP3 mailbox")

            if since_date:
                cutoff = datetime.combine(since_date, datetime.min.time(), tzinfo=timezone.utc)
            elif days_back is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
            else:
                cutoff = None

            messages_to_fetch = min(num_messages, limit)
            start_idx = num_messages - messages_to_fetch + 1

            for i in range(start_idx, num_messages + 1):
                try:
                    raw_lines = conn.retr(i)[1]
                    raw_email = b"\r\n".join(raw_lines)
                    msg = email.message_from_bytes(raw_email)

                    msg_id = msg.get("Message-ID", f"{self.email}-pop3-{i}").strip()
                    if msg_id.startswith("<") and msg_id.endswith(">"):
                        msg_id = msg_id[1:-1]

                    if db_check_func and db_check_func(msg_id):
                        continue

                    if cutoff is not None:
                        date_str = msg.get("Date", "")
                        if date_str:
                            parsed_date = self._parse_email_date(date_str)
                            if parsed_date is not None and parsed_date < cutoff:
                                continue

                    parsed_date = self._parse_email_date(msg.get("Date", ""))

                    body_text, html_body = self._extract_body(msg)

                    attachments = self._extract_attachments(msg)

                    in_reply_to = _normalize_message_id(msg.get("In-Reply-To", ""))

                    refs = re.findall(r"<([^>]+)>", msg.get("References", ""))

                    email_data: dict[str, Any] = {
                        "message_id": msg_id,
                        "imap_uid": str(i),
                        "account": self.email,
                        "thread_id": msg.get("Thread-Index", ""),
                        "in_reply_to": in_reply_to,
                        "references": ",".join(refs) if refs else "",
                        "subject": msg.get("Subject", ""),
                        "sender": msg.get("From", ""),
                        "recipient": msg.get("To", ""),
                        "cc": msg.get("Cc", ""),
                        "date": parsed_date or datetime.now(),
                        "body_text": body_text,
                        "html_body": html_body,
                        "has_attachment": len(attachments) > 0,
                        "is_read": True,
                        "is_starred": False,
                        "labels": [],
                        "folder": "INBOX",
                        "raw_email": raw_email,
                        "attachments": attachments,
                    }
                    results.append(email_data)

                except Exception as e:
                    logger.warning(f"Failed to fetch POP3 message {i}: {e}")
                    continue

            return results
        finally:
            if conn:
                try:
                    conn.quit()
                except Exception:
                    pass

    # -----------------------------------------------------------------
    # FETCH EMAILS (unified entry point)
    # -----------------------------------------------------------------
    def fetch_emails(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        days_back: int | None = None,
        unread_only: bool = False,
        since_date: date | None = None,
        db_check_func: Callable[[str], bool] | None = None,
    ) -> list[dict[str, Any]]:
        if self.protocol == "pop3":
            if unread_only:
                logger.warning("POP3 does not support unread_only filter.")
            if folder.upper() not in ("INBOX", "ALL"):
                logger.warning("POP3 only supports INBOX folder.")
            return self._fetch_emails_pop3(
                limit=limit,
                days_back=days_back,
                since_date=since_date,
                db_check_func=db_check_func,
            )

        results: list[dict[str, Any]] = []
        try:
            with self._get_mailbox() as mailbox:
                folders_to_fetch: list[str] = self._resolve_folders(mailbox, folder)

                for current_folder in folders_to_fetch:
                    try:
                        mailbox.folder.set(current_folder)
                    except Exception as e:
                        logger.warning(f"Could not set folder {current_folder}: {e}")
                        continue

                    criteria = self._build_imap_criteria(
                        unread_only=unread_only,
                        since_date=since_date,
                        days_back=days_back,
                    )

                    for msg in mailbox.fetch(
                        criteria, limit=limit, reverse=True, mark_seen=False
                    ):
                        try:
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

                            refs: list[str] = []
                            if references_header:
                                refs = re.findall(r"<([^>]+)>", str(references_header))
                                if not refs:
                                    refs = [
                                        x.strip()
                                        for x in str(references_header).split()
                                        if x.strip()
                                    ]

                            in_reply_to_norm = _normalize_message_id(
                                str(in_reply_to_header)
                            )

                            global_msg_id = _normalize_message_id(
                                str(msg_id_header) if msg_id_header
                                else f"{self.email}-{current_folder}-{msg.uid}"
                            )

                            if db_check_func and db_check_func(global_msg_id):
                                continue

                            body_text = msg.text or ""
                            if not body_text and msg.html:
                                soup = BeautifulSoup(msg.html, "html.parser")
                                body_text = soup.get_text(separator="\n", strip=True)

                            email_data: dict[str, Any] = {
                                "message_id": global_msg_id,
                                "imap_uid": msg.uid,
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
                                "is_starred": "FLAGGED"
                                in [flag.upper() for flag in msg.flags],
                                "labels": msg.flags,
                                "folder": current_folder,
                                "raw_email": msg.obj,
                                "attachments": msg.attachments,
                            }
                            results.append(email_data)
                        except MailClientError:
                            raise
                        except Exception as e:
                            logger.warning(f"Failed to process IMAP message: {e}")
                            continue

            return results
        except MailClientError:
            raise
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            raise MailClientError(str(e)) from e

    # -----------------------------------------------------------------
    # SEND EMAIL
    # -----------------------------------------------------------------
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
        smtp_server = self.config.get("SMTP_SERVER")
        if not smtp_server:
            raise MissingCredentialsError("SMTP_SERVER is required for sending emails.")
        try:
            smtp_port = int(self.config.get("SMTP_PORT", 465))
        except (ValueError, TypeError):
            smtp_port = 465
        use_ssl = (
            str(self.config.get("USE_SSL", "true")).lower() == "true" or smtp_port == 465
        )

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = str(self.email)

        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references

        if isinstance(to, list):
            msg["To"] = ", ".join(to)
        else:
            msg["To"] = to

        if cc:
            msg["Cc"] = ", ".join(cc) if isinstance(cc, list) else cc
        if bcc:
            msg["Bcc"] = ", ".join(bcc) if isinstance(bcc, list) else bcc

        if html_body:
            msg.add_alternative(body_text, subtype="plain")
            msg.add_alternative(html_body, subtype="html")
        else:
            msg.set_content(body_text)

        if attachments:
            for filepath in attachments:
                _attach_file(msg, filepath)

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
            raise MailClientError(str(e)) from e

    # -----------------------------------------------------------------
    # IMAP SERVER OPERATIONS
    # -----------------------------------------------------------------
    def _require_imap(self, operation: str) -> None:
        if self.protocol == "pop3":
            raise POP3NotSupportedError(
                f"'{operation}' is not supported with POP3 protocol."
            )

    def mark_as_read(
        self, uids: list[str], folder: str = "INBOX", is_read: bool = True
    ) -> None:
        self._require_imap("mark_as_read")
        if not uids:
            return
        with self._get_mailbox() as mailbox:
            mailbox.folder.set(folder)
            mailbox.flag(uids, imap_tools.MailMessageFlags.SEEN, is_read)  # type: ignore[attr-defined]

    def mark_as_starred(
        self, uids: list[str], folder: str = "INBOX", is_starred: bool = True
    ) -> None:
        self._require_imap("mark_as_starred")
        if not uids:
            return
        with self._get_mailbox() as mailbox:
            mailbox.folder.set(folder)
            mailbox.flag(uids, imap_tools.MailMessageFlags.FLAGGED, is_starred)  # type: ignore[attr-defined]

    def create_folder(self, folder_name: str) -> bool:
        self._require_imap("create_folder")
        try:
            with self._get_mailbox() as mailbox:
                if not mailbox.folder.exists(folder_name):
                    mailbox.folder.create(folder_name)
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to create folder {folder_name}: {e}")
            raise MailClientError(str(e)) from e

    def move_emails(
        self, uids: list[str], destination_folder: str, source_folder: str = "INBOX"
    ) -> None:
        self._require_imap("move_emails")
        if not uids:
            return
        try:
            self.create_folder(destination_folder)
        except Exception as e:
            logger.error(f"Failed to create destination folder: {e}")
            raise

        with self._get_mailbox() as mailbox:
            mailbox.folder.set(source_folder)
            mailbox.move(uids, destination_folder)

    def delete_emails(self, uids: list[str], folder: str = "INBOX") -> None:
        self._require_imap("delete_emails")
        if not uids:
            return
        with self._get_mailbox() as mailbox:
            mailbox.folder.set(folder)
            mailbox.delete(uids)

    # -----------------------------------------------------------------
    # HELPERS
    # -----------------------------------------------------------------
    @staticmethod
    def _resolve_folders(mailbox: Any, folder: str) -> list[str]:
        if folder.upper() == "ALL":
            return [
                f.name
                for f in mailbox.folder.list()
                if not f.name.startswith("[Gmail]")
            ]
        return [f.strip() for f in folder.split(",")]

    @staticmethod
    def _build_imap_criteria(
        unread_only: bool = False,
        since_date: date | None = None,
        days_back: int | None = None,
    ) -> Any:
        criteria: list[Any] = []
        if unread_only:
            criteria.append(A(seen=False))
        if since_date:
            criteria.append(A(date_gte=since_date))
        elif days_back is not None:
            d = (datetime.now() - timedelta(days=days_back)).date()
            criteria.append(A(date_gte=d))
        if not criteria:
            return A(all=True)
        return A(*criteria) if len(criteria) > 1 else criteria[0]

    @staticmethod
    def _parse_email_date(date_str: str) -> datetime | None:
        try:
            parsed = email.utils.parsedate_to_datetime(date_str)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except Exception:
            return None

    @staticmethod
    def _extract_body(msg: Any) -> tuple[str, str]:
        body_text = ""
        html_body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" and not body_text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = _safe_decode(payload, part.get_content_charset())
                elif content_type == "text/html" and not html_body:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_body = _safe_decode(payload, part.get_content_charset())
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body_text = _safe_decode(payload, msg.get_content_charset())

        if not body_text and html_body:
            soup = BeautifulSoup(html_body, "html.parser")
            body_text = soup.get_text(separator="\n", strip=True)
        return body_text, html_body

    @staticmethod
    def _extract_attachments(msg: Any) -> list[dict[str, str]]:
        attachments = []
        for part in msg.walk():
            disposition = str(part.get_content_disposition()).lower()
            if disposition == "attachment":
                filename = part.get_filename()
                if filename:
                    attachments.append({
                        "filename": filename,
                        "content_type": part.get_content_type(),
                    })
        return attachments


# -----------------------------------------------------------------
# MODULE-LEVEL HELPERS
# -----------------------------------------------------------------
def _normalize_message_id(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1]
    return value


def _safe_decode(payload: bytes, charset: str | None) -> str:
    if charset:
        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            pass
    return payload.decode("utf-8", errors="replace")


def _attach_file(msg: EmailMessage, filepath: str) -> None:
    import mimetypes

    ctype, _ = mimetypes.guess_type(filepath)
    if ctype is None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)

    try:
        with open(filepath, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(filepath),
            )
    except (OSError, IOError) as e:
        raise MailClientError(f"Cannot read attachment '{filepath}': {e}") from e
