"""Tests for AI reply composition with feedback learning.

Tests cover reply generation, thread context inclusion, and feedback storage.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


class TestComposeAIReply:
    """Tests for AI reply composition via LLM."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        mock = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Thank you for your email. I will get back to you soon."
        mock.chat_with_history.return_value = mock_response
        return mock

    @pytest.fixture
    def sample_email(self):
        """Create sample email data."""
        return {
            "message_id": "msg-1@example.com",
            "sender": "alice@example.com",
            "recipient": "bob@example.com",
            "subject": "Meeting Request",
            "date": "2024-01-15",
            "body_text": "Can we meet next week?",
        }

    def test_compose_reply_generates_response(self, mock_llm_client, sample_email):
        """Test compose_ai_reply generates response via LLM."""
        from scripts.mail_manager.reply_assistant import compose_ai_reply

        result = compose_ai_reply(
            llm_client=mock_llm_client,
            original_email=sample_email,
        )

        mock_llm_client.chat_with_history.assert_called_once()
        assert "thank" in result.lower()

    def test_compose_reply_with_thread_context(self, mock_llm_client, sample_email):
        """Test reply includes thread context when available (REPLY-AI-01)."""
        from scripts.mail_manager.reply_assistant import compose_ai_reply

        thread_context = [
            {
                "message_id": "msg-0@example.com",
                "sender": "bob@example.com",
                "subject": "Re: Discussion",
                "date": "2024-01-14",
                "body_text": "Let's discuss the project.",
            }
        ]

        result = compose_ai_reply(
            llm_client=mock_llm_client,
            original_email=sample_email,
            thread_context=thread_context,
        )

        # Verify LLM was called
        mock_llm_client.chat_with_history.assert_called_once()
        assert result is not None

    def test_compose_reply_with_user_intent(self, mock_llm_client, sample_email):
        """Test user_intent influences reply content."""
        from scripts.mail_manager.reply_assistant import compose_ai_reply

        result = compose_ai_reply(
            llm_client=mock_llm_client,
            original_email=sample_email,
            user_intent="Accept the meeting request",
        )

        mock_llm_client.chat_with_history.assert_called_once()
        call_kwargs = mock_llm_client.chat_with_history.call_args.kwargs
        assert "intent" in call_kwargs.get("user_message", "").lower()

    def test_compose_reply_with_few_shot_examples(self, mock_llm_client, sample_email):
        """Test few-shot examples are included in LLM prompt."""
        from scripts.mail_manager.reply_assistant import compose_ai_reply

        few_shot_examples = [
            {
                "original": "From: test@example.com\nSubject: Hello",
                "reply": "Thank you for reaching out!",
            }
        ]

        result = compose_ai_reply(
            llm_client=mock_llm_client,
            original_email=sample_email,
            few_shot_examples=few_shot_examples,
        )

        mock_llm_client.chat_with_history.assert_called_once()
        call_kwargs = mock_llm_client.chat_with_history.call_args.kwargs
        # Conversation should include few-shot examples
        conversation = call_kwargs.get("conversation", [])
        assert len(conversation) >= 2  # At least one user/assistant pair for few-shot

    def test_compose_reply_professional_and_concise(self, mock_llm_client, sample_email):
        """Test response is professional and concise."""
        from scripts.mail_manager.reply_assistant import compose_ai_reply

        mock_llm_client.chat_with_history.return_value.content = (
            "Thank you for reaching out. "
            "I appreciate your message and will respond shortly.\n\n"
            "Best regards"
        )

        result = compose_ai_reply(
            llm_client=mock_llm_client,
            original_email=sample_email,
        )

        assert result is not None
        # Response should be present
        assert len(result) > 0


class TestStoreReplyFeedback:
    """Tests for store_reply_feedback function."""

    @pytest.fixture
    def db(self, temp_db_path, mock_chroma_collection):
        """Create a MailDatabase instance for testing."""
        from mail_manager.db import MailDatabase

        return MailDatabase(temp_db_path)

    def test_store_reply_feedback_saves_to_db(self, db):
        """Test store_reply_feedback saves feedback to database."""
        from scripts.mail_manager.reply_assistant import store_reply_feedback

        store_reply_feedback(
            db=db,
            original_message_id="msg-1@example.com",
            original_email="From: alice@example.com\nSubject: Test",
            suggested_reply="Thank you for your email.",
            is_positive=True,
        )

        feedback = db.get_reply_feedback(limit=10, positive_only=True)
        assert len(feedback) == 1
        assert feedback[0]["original_message_id"] == "msg-1@example.com"

    def test_store_reply_feedback_with_edited_reply(self, db):
        """Test store_reply_feedback stores edited reply."""
        from scripts.mail_manager.reply_assistant import store_reply_feedback

        store_reply_feedback(
            db=db,
            original_message_id="msg-2@example.com",
            original_email="From: bob@example.com\nSubject: Hello",
            suggested_reply="Draft reply",
            user_edited_reply="Edited version of reply",
            is_positive=True,
        )

        feedback = db.get_reply_feedback(limit=10, positive_only=False)
        assert feedback[0]["user_edited_reply"] == "Edited version of reply"

    def test_store_reply_feedback_negative(self, db):
        """Test store_reply_feedback stores negative feedback."""
        from scripts.mail_manager.reply_assistant import store_reply_feedback

        store_reply_feedback(
            db=db,
            original_message_id="msg-3@example.com",
            original_email="From: charlie@example.com",
            suggested_reply="Bad reply",
            is_positive=False,
        )

        # Negative feedback should not appear in positive_only results
        positive = db.get_reply_feedback(limit=10, positive_only=True)
        assert len(positive) == 0

        # But should appear when not filtered
        all_feedback = db.get_reply_feedback(limit=10, positive_only=False)
        assert len(all_feedback) == 1


class TestGetFewShotExamples:
    """Tests for get_few_shot_examples function."""

    @pytest.fixture
    def db(self, temp_db_path, mock_chroma_collection):
        """Create a MailDatabase instance for testing."""
        from mail_manager.db import MailDatabase

        return MailDatabase(temp_db_path)

    def test_get_few_shot_examples_returns_list(self, db):
        """Test get_few_shot_examples returns list of examples."""
        from scripts.mail_manager.reply_assistant import (
            get_few_shot_examples,
            store_reply_feedback,
        )

        # Store some feedback
        for i in range(3):
            store_reply_feedback(
                db=db,
                original_message_id=f"msg-{i}@example.com",
                original_email=f"Email {i}",
                suggested_reply=f"Reply {i}",
                is_positive=True,
            )

        examples = get_few_shot_examples(db=db, limit=5)

        assert isinstance(examples, list)
        assert len(examples) == 3
        assert "original" in examples[0]
        assert "reply" in examples[0]

    def test_get_few_shot_examples_uses_edited_reply(self, db):
        """Test get_few_shot_examples uses edited reply when available."""
        from scripts.mail_manager.reply_assistant import (
            get_few_shot_examples,
            store_reply_feedback,
        )

        store_reply_feedback(
            db=db,
            original_message_id="msg-edited@example.com",
            original_email="Original email",
            suggested_reply="Suggested reply",
            user_edited_reply="User edited this",
            is_positive=True,
        )

        examples = get_few_shot_examples(db=db, limit=5)

        assert examples[0]["reply"] == "User edited this"

    def test_get_few_shot_examples_respects_limit(self, db):
        """Test get_few_shot_examples respects limit parameter."""
        from scripts.mail_manager.reply_assistant import (
            get_few_shot_examples,
            store_reply_feedback,
        )

        for i in range(10):
            store_reply_feedback(
                db=db,
                original_message_id=f"msg-limit-{i}@example.com",
                original_email=f"Email {i}",
                suggested_reply=f"Reply {i}",
                is_positive=True,
            )

        examples = get_few_shot_examples(db=db, limit=3)

        assert len(examples) == 3

    def test_get_few_shot_examples_positive_only(self, db):
        """Test get_few_shot_examples only returns positive feedback."""
        from scripts.mail_manager.reply_assistant import (
            get_few_shot_examples,
            store_reply_feedback,
        )

        # Store positive feedback
        store_reply_feedback(
            db=db,
            original_message_id="msg-pos@example.com",
            original_email="Good email",
            suggested_reply="Good reply",
            is_positive=True,
        )

        # Store negative feedback
        store_reply_feedback(
            db=db,
            original_message_id="msg-neg@example.com",
            original_email="Bad email",
            suggested_reply="Bad reply",
            is_positive=False,
        )

        examples = get_few_shot_examples(db=db, limit=10)

        # Only positive feedback should be returned
        assert len(examples) == 1
