"""
Shared pytest fixtures for mail-skill tests.

These fixtures mock external dependencies (IMAP, SMTP, ChromaDB) to ensure
tests run fast and isolated without requiring real network connections.
"""

import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_imap_mailbox():
    """
    Mock imap_tools.MailBox for unit testing.

    Mocks the MailBox class at the library boundary, allowing tests to
    simulate IMAP operations without real network connections.

    Yields:
        MagicMock: A mock MailBox instance that can be configured for test scenarios.
    """
    with patch('imap_tools.MailBox') as mock_class:
        mailbox_instance = MagicMock()
        mock_class.return_value.__enter__ = MagicMock(return_value=mailbox_instance)
        mock_class.return_value.__exit__ = MagicMock(return_value=False)
        # Mock login method
        mailbox_instance.login = MagicMock()
        # Mock folder operations
        mailbox_instance.folder = MagicMock()
        mailbox_instance.folder.set = MagicMock()
        mailbox_instance.folder.list = MagicMock(return_value=[])
        mailbox_instance.folder.exists = MagicMock(return_value=False)
        mailbox_instance.folder.create = MagicMock()
        # Mock fetch
        mailbox_instance.fetch = MagicMock(return_value=[])
        # Mock flag operations
        mailbox_instance.flag = MagicMock()
        # Mock move and delete
        mailbox_instance.move = MagicMock()
        mailbox_instance.delete = MagicMock()
        # Mock client for Netease special handling
        mailbox_instance.client = MagicMock()
        mailbox_instance.client._simple_command = MagicMock()
        mailbox_instance.client._new_tag = MagicMock(return_value='A001')
        mailbox_instance.client.send = MagicMock()
        mailbox_instance.client.readline = MagicMock(return_value=b'A001 OK\r\n')
        yield mailbox_instance


@pytest.fixture
def mock_smtp():
    """
    Mock smtplib.SMTP_SSL and smtplib.SMTP for unit testing.

    Mocks SMTP connections to test email sending without real network calls.

    Yields:
        MagicMock: A mock SMTP server instance.
    """
    with patch('smtplib.SMTP_SSL') as mock_ssl_class:
        server_instance = MagicMock()
        mock_ssl_class.return_value.__enter__ = MagicMock(return_value=server_instance)
        mock_ssl_class.return_value.__exit__ = MagicMock(return_value=False)
        server_instance.login = MagicMock()
        server_instance.send_message = MagicMock()
        yield server_instance


@pytest.fixture
def mock_smtp_starttls():
    """
    Mock smtplib.SMTP with STARTTLS for unit testing.

    For servers that use SMTP with STARTTLS instead of SMTP_SSL.

    Yields:
        MagicMock: A mock SMTP server instance with starttls support.
    """
    with patch('smtplib.SMTP') as mock_smtp_class:
        server_instance = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=server_instance)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)
        server_instance.starttls = MagicMock()
        server_instance.login = MagicMock()
        server_instance.send_message = MagicMock()
        yield server_instance


@pytest.fixture
def temp_db_path():
    """
    Create a temporary SQLite database file for testing.

    Yields the path to a temporary database file that is automatically
    cleaned up after the test completes.

    Yields:
        str: Path to a temporary database file.
    """
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def temp_db_dir():
    """
    Create a temporary directory for database files including ChromaDB.

    Yields:
        str: Path to a temporary directory.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_chroma_collection():
    """
    Mock ChromaDB collection for vector search tests.

    Mocks the chromadb.PersistentClient and its collection to avoid
    loading real embedding models during tests.

    Yields:
        MagicMock: A mock ChromaDB collection instance.
    """
    with patch('chromadb.PersistentClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        # Mock collection methods
        mock_collection.upsert = MagicMock()
        mock_collection.query = MagicMock(return_value={
            'ids': [[]],
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]]
        })
        mock_collection.delete = MagicMock()

        yield mock_collection


@pytest.fixture
def sample_email_data():
    """
    Sample email data for tests.

    Returns a dict with sample email data matching the EmailData structure
    used by MailClient and MailDatabase.

    Returns:
        dict: Sample email data with all required fields.
    """
    return {
        'message_id': 'test-msg-123@example.com',
        'imap_uid': '12345',
        'account': 'test@example.com',
        'thread_id': '',
        'in_reply_to': '',
        'references': '',
        'subject': 'Test Subject',
        'sender': 'sender@example.com',
        'recipient': 'recipient@example.com',
        'cc': '',
        'date': datetime(2024, 1, 15, 10, 30, 0),
        'body_text': 'This is a test email body.',
        'html_body': '<p>This is a test email body.</p>',
        'has_attachment': False,
        'is_read': False,
        'is_starred': False,
        'labels': [],
        'folder': 'INBOX',
        'attachments': []
    }


@pytest.fixture
def sample_email_data_with_attachment():
    """
    Sample email data with attachment for tests.

    Returns:
        dict: Sample email data including an attachment.
    """
    return {
        'message_id': 'test-msg-456@example.com',
        'imap_uid': '67890',
        'account': 'test@example.com',
        'thread_id': '',
        'in_reply_to': '',
        'references': '',
        'subject': 'Test Email with Attachment',
        'sender': 'sender@example.com',
        'recipient': 'recipient@example.com',
        'cc': '',
        'date': datetime(2024, 1, 16, 14, 0, 0),
        'body_text': 'Please see the attached file.',
        'html_body': '<p>Please see the attached file.</p>',
        'has_attachment': True,
        'is_read': True,
        'is_starred': False,
        'labels': ['SEEN'],
        'folder': 'INBOX',
        'attachments': [{
            'filename': 'document.pdf',
            'content_type': 'application/pdf',
            'size': 1024,
            'local_path': None
        }]
    }


@pytest.fixture
def test_config():
    """
    Test email configuration.

    Returns a dict with test email configuration for MailClient initialization.

    Returns:
        dict: Test configuration with EMAIL, PASSWORD, server settings, etc.
    """
    return {
        'EMAIL': 'test@example.com',
        'PASSWORD': 'test_password',
        'IMAP_SERVER': 'imap.example.com',
        'IMAP_PORT': '993',
        'SMTP_SERVER': 'smtp.example.com',
        'SMTP_PORT': '465',
        'USE_SSL': 'true'
    }


@pytest.fixture
def mock_imap_message():
    """
    Create a mock IMAP message for testing fetch_emails.

    Returns a MagicMock that behaves like an imap_tools MailMessage.

    Returns:
        MagicMock: A mock message object.
    """
    msg = MagicMock()
    msg.uid = '12345'
    msg.subject = 'Test Subject'
    msg.from_ = 'sender@example.com'
    msg.to = ['recipient@example.com']
    msg.cc = []
    msg.date = datetime(2024, 1, 15, 10, 30, 0)
    msg.text = 'This is a test email body.'
    msg.html = '<p>This is a test email body.</p>'
    msg.attachments = []
    msg.flags = []
    msg.headers = {
        'message-id': ('test-msg-123@example.com',),
        'in-reply-to': ('',),
        'references': ('',),
        'thread-index': ('',)
    }
    msg.obj = MagicMock()  # email.message.Message mock
    return msg


@pytest.fixture
def mock_imap_message_list(mock_imap_message):
    """
    Create a list of mock IMAP messages for testing.

    Args:
        mock_imap_message: A single mock message fixture.

    Returns:
        list: A list of mock message objects.
    """
    # Create multiple messages with different content
    messages = []
    for i in range(3):
        msg = MagicMock()
        msg.uid = str(10000 + i)
        msg.subject = f'Test Subject {i + 1}'
        msg.from_ = f'sender{i}@example.com'
        msg.to = ['recipient@example.com']
        msg.cc = []
        msg.date = datetime(2024, 1, 15 + i, 10, 30, 0)
        msg.text = f'This is test email body {i + 1}.'
        msg.html = f'<p>This is test email body {i + 1}.</p>'
        msg.attachments = []
        msg.flags = []
        msg.headers = {
            'message-id': (f'test-msg-{i + 1}@example.com',),
            'in-reply-to': ('',),
            'references': ('',)
        }
        msg.obj = MagicMock()
        messages.append(msg)
    return messages
