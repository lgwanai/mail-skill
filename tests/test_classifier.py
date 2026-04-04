"""
Test cases for email classification module.

This module contains test stubs for the EmailClassifier functionality.
Tests are marked as skip until implementation is complete.
"""

import os
import tempfile
import pytest

from scripts.mail_manager.classifier import Classification, Rule, ClassificationResult
from scripts.mail_manager.rules import load_rules, get_default_rules, DEFAULT_RULES_PATH


class TestClassificationDataclass:
    """Tests for Classification dataclass."""

    def test_classification_creation(self) -> None:
        """Test that Classification can be created with required fields."""
        classification = Classification(
            importance="high",
            category="work",
            confidence=0.85,
        )
        assert classification.importance == "high"
        assert classification.category == "work"
        assert classification.confidence == 0.85
        assert classification.matched_rules == []
        assert classification.manual_override is False

    def test_classification_with_matched_rules(self) -> None:
        """Test Classification with matched rules."""
        classification = Classification(
            importance="critical",
            category="work",
            confidence=0.95,
            matched_rules=["Critical Senders", "Urgent Keywords"],
        )
        assert len(classification.matched_rules) == 2
        assert "Critical Senders" in classification.matched_rules

    def test_classification_manual_override(self) -> None:
        """Test Classification with manual override flag."""
        classification = Classification(
            importance="low",
            category="promo",
            confidence=1.0,
            manual_override=True,
        )
        assert classification.manual_override is True


class TestRuleDataclass:
    """Tests for Rule dataclass."""

    def test_rule_creation(self) -> None:
        """Test that Rule can be created with required fields."""
        rule = Rule(
            name="Test Rule",
            rule_type="sender",
            patterns=["test@example.com"],
        )
        assert rule.name == "Test Rule"
        assert rule.rule_type == "sender"
        assert rule.patterns == ["test@example.com"]
        assert rule.weight == 1.0

    def test_rule_with_optional_fields(self) -> None:
        """Test Rule with optional importance and category."""
        rule = Rule(
            name="Test Rule",
            rule_type="keyword",
            patterns=["urgent", "important"],
            importance="high",
            category="work",
            weight=1.5,
        )
        assert rule.importance == "high"
        assert rule.category == "work"
        assert rule.weight == 1.5

    def test_rule_types(self) -> None:
        """Test different rule types."""
        sender_rule = Rule(name="Sender", rule_type="sender", patterns=["a@b.com"])
        keyword_rule = Rule(name="Keyword", rule_type="keyword", patterns=["urgent"])
        pattern_rule = Rule(name="Pattern", rule_type="sender_pattern", patterns=["@company\\.com$"])

        assert sender_rule.rule_type == "sender"
        assert keyword_rule.rule_type == "keyword"
        assert pattern_rule.rule_type == "sender_pattern"


class TestClassificationResultDataclass:
    """Tests for ClassificationResult dataclass."""

    @pytest.mark.skip(reason="Implementation pending")
    def test_classification_result_creation(self) -> None:
        """
        Test that ClassificationResult can be created.

        Should verify:
        - email_id is set correctly
        - classification is a Classification object
        - processing_time_ms is a float
        """
        pass


class TestLoadRules:
    """Tests for load_rules function."""

    def test_load_rules_default_path(self) -> None:
        """Test loading rules from default path."""
        # This test requires the default config file to exist
        if os.path.exists(DEFAULT_RULES_PATH):
            rules = load_rules()
            assert isinstance(rules, list)
            assert len(rules) > 0
            for rule in rules:
                assert isinstance(rule, Rule)
                assert rule.name
                assert rule.rule_type
                assert rule.patterns

    def test_load_rules_custom_path(self) -> None:
        """Test loading rules from custom path."""
        yaml_content = """
rules:
  - name: "Test Rule"
    type: keyword
    patterns:
      - "test"
    importance: high
    weight: 1.5
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            rules = load_rules(temp_path)
            assert len(rules) == 1
            assert rules[0].name == "Test Rule"
            assert rules[0].rule_type == "keyword"
            assert rules[0].importance == "high"
            assert rules[0].weight == 1.5
        finally:
            os.unlink(temp_path)

    def test_load_rules_fallback(self) -> None:
        """Test fallback to default rules when file not found."""
        rules = load_rules("/nonexistent/path/to/rules.yaml")
        # Should return default rules
        assert isinstance(rules, list)
        assert len(rules) > 0
        for rule in rules:
            assert isinstance(rule, Rule)

    def test_load_rules_invalid_yaml(self) -> None:
        """Test handling of invalid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid rules configuration"):
                load_rules(temp_path)
        finally:
            os.unlink(temp_path)

    def test_load_rules_empty_file(self) -> None:
        """Test handling of empty YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            rules = load_rules(temp_path)
            # Should return empty list or default rules
            assert isinstance(rules, list)
        finally:
            os.unlink(temp_path)


class TestGetDefaultRules:
    """Tests for get_default_rules function."""

    def test_get_default_rules_returns_list(self) -> None:
        """Test that get_default_rules returns a list."""
        rules = get_default_rules()
        assert isinstance(rules, list)
        assert len(rules) > 0

    def test_get_default_rules_structure(self) -> None:
        """Test structure of default rules."""
        rules = get_default_rules()
        for rule in rules:
            assert isinstance(rule, Rule)
            assert rule.name
            assert rule.rule_type in ("sender", "keyword", "sender_pattern")
            assert rule.patterns
            assert 0 < rule.weight <= 2.0

    def test_get_default_rules_has_critical_senders(self) -> None:
        """Test that default rules include critical sender patterns."""
        rules = get_default_rules()
        sender_rules = [r for r in rules if r.rule_type == "sender"]
        assert len(sender_rules) > 0

    def test_get_default_rules_has_urgent_keywords(self) -> None:
        """Test that default rules include urgent keyword patterns."""
        rules = get_default_rules()
        keyword_rules = [r for r in rules if r.rule_type == "keyword"]
        assert len(keyword_rules) > 0


class TestEmailClassifierMatch:
    """Tests for EmailClassifier rule matching methods."""

    def test_match_sender_exact(self) -> None:
        """Test exact sender match in sender rule."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(
            name="Test Sender",
            rule_type="sender",
            patterns=["boss@company.com"],
            importance="critical",
        )

        email_match = {"sender": "Boss <boss@company.com>", "subject": "Test", "body_text": ""}
        email_no_match = {"sender": "other@example.com", "subject": "Test", "body_text": ""}

        assert classifier._match_sender(rule, email_match) is True
        assert classifier._match_sender(rule, email_no_match) is False

    def test_match_sender_partial(self) -> None:
        """Test partial sender match (email address within sender string)."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(
            name="Company Senders",
            rule_type="sender",
            patterns=["@company.com"],
            importance="high",
        )

        email = {"sender": "John <john@company.com>", "subject": "Test", "body_text": ""}
        assert classifier._match_sender(rule, email) is True

    def test_match_sender_pattern(self) -> None:
        """Test regex pattern match on sender."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(
            name="Company Domain",
            rule_type="sender_pattern",
            patterns=[r"@company\.com$"],
            category="work",
        )

        email_match = {"sender": "user@company.com", "subject": "Test", "body_text": ""}
        email_no_match = {"sender": "user@company.org", "subject": "Test", "body_text": ""}

        assert classifier._match_sender_pattern(rule, email_match) is True
        assert classifier._match_sender_pattern(rule, email_no_match) is False

    def test_match_keyword_subject(self) -> None:
        """Test keyword match in email subject."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(
            name="Urgent Keywords",
            rule_type="keyword",
            patterns=["urgent", "important"],
            importance="critical",
        )

        email = {"sender": "test@test.com", "subject": "URGENT: Please read", "body_text": ""}
        assert classifier._match_keyword(rule, email) is True

    def test_match_keyword_body(self) -> None:
        """Test keyword match in email body."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(
            name="Verification Codes",
            rule_type="keyword",
            patterns=["验证码", "verification code"],
            category="notification",
        )

        email = {
            "sender": "system@test.com",
            "subject": "Your code",
            "body_text": "Your verification code is 123456",
        }
        assert classifier._match_keyword(rule, email) is True

    def test_match_keyword_case_insensitive(self) -> None:
        """Test that keyword matching is case-insensitive."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(
            name="Important Keywords",
            rule_type="keyword",
            patterns=["IMPORTANT", "Urgent"],
            importance="high",
        )

        email_lower = {"sender": "test@test.com", "subject": "important notice", "body_text": ""}
        email_upper = {"sender": "test@test.com", "subject": "URGENT ALERT", "body_text": ""}
        email_mixed = {"sender": "test@test.com", "subject": "ImPoRtAnT", "body_text": ""}

        assert classifier._match_keyword(rule, email_lower) is True
        assert classifier._match_keyword(rule, email_upper) is True
        assert classifier._match_keyword(rule, email_mixed) is True

    def test_match_multiple_rules(self) -> None:
        """Test that multiple rules can match the same email."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rules = [
            Rule(name="Sender Rule", rule_type="sender", patterns=["@company.com"]),
            Rule(name="Keyword Rule", rule_type="keyword", patterns=["urgent"]),
        ]

        email = {
            "sender": "boss@company.com",
            "subject": "URGENT meeting",
            "body_text": "",
        }

        matches = [r for r in rules if classifier._match_rule(r, email)]
        assert len(matches) == 2

    def test_match_no_match(self) -> None:
        """Test that no match returns False."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(
            name="No Match Rule",
            rule_type="keyword",
            patterns=["specificword123"],
        )

        email = {
            "sender": "test@test.com",
            "subject": "Random subject",
            "body_text": "Random body content",
        }

        assert classifier._match_keyword(rule, email) is False


class TestClassifySenderMatch:
    """Tests for sender-based classification."""

    def test_classify_exact_sender_match(self) -> None:
        """Test classification with exact sender match."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(
            name="Critical Sender",
            rule_type="sender",
            patterns=["boss@company.com"],
            importance="critical",
            category="work",
        )
        classifier.rules = [rule]

        email = {"sender": "Boss <boss@company.com>", "subject": "Test", "body_text": ""}
        result = classifier.classify(email)

        assert result.importance == "critical"
        assert result.category == "work"
        assert "Critical Sender" in result.matched_rules

    def test_classify_sender_pattern_match(self) -> None:
        """Test classification with sender pattern match."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(
            name="Company Domain",
            rule_type="sender_pattern",
            patterns=[r"@company\.com$"],
            category="work",
        )
        classifier.rules = [rule]

        email = {"sender": "user@company.com", "subject": "Test", "body_text": ""}
        result = classifier.classify(email)

        assert result.category == "work"
        assert "Company Domain" in result.matched_rules

    def test_classify_no_sender_match(self) -> None:
        """Test classification with no sender match returns default."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(
            name="Specific Sender",
            rule_type="sender",
            patterns=["specific@company.com"],
        )
        classifier.rules = [rule]

        email = {"sender": "other@example.com", "subject": "Test", "body_text": ""}
        result = classifier.classify(email)

        assert result.importance == "normal"
        assert result.category == "uncategorized"
        assert result.matched_rules == []


class TestClassifyKeywordMatch:
    """Tests for keyword-based classification."""

    def test_classify_keyword_in_subject(self) -> None:
        """Test classification with keyword in subject."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(
            name="Urgent Keywords",
            rule_type="keyword",
            patterns=["urgent"],
            importance="critical",
        )
        classifier.rules = [rule]

        email = {"sender": "test@test.com", "subject": "URGENT action needed", "body_text": ""}
        result = classifier.classify(email)

        assert result.importance == "critical"
        assert "Urgent Keywords" in result.matched_rules

    def test_classify_keyword_in_body(self) -> None:
        """Test classification with keyword in body."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(
            name="Financial Keywords",
            rule_type="keyword",
            patterns=["invoice", "payment"],
            importance="high",
            category="work",
        )
        classifier.rules = [rule]

        email = {
            "sender": "billing@vendor.com",
            "subject": "Your order",
            "body_text": "Please find attached invoice for your payment.",
        }
        result = classifier.classify(email)

        assert result.importance == "high"
        assert result.category == "work"

    def test_classify_multiple_keywords(self) -> None:
        """Test classification with multiple matching keywords."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rules = [
            Rule(name="Urgent", rule_type="keyword", patterns=["urgent"], importance="critical", weight=1.5),
            Rule(name="Important", rule_type="keyword", patterns=["important"], importance="high", weight=1.0),
        ]
        classifier.rules = rules

        email = {
            "sender": "test@test.com",
            "subject": "Urgent and important meeting",
            "body_text": "",
        }
        result = classifier.classify(email)

        # Higher weight rule should win
        assert result.importance == "critical"
        assert len(result.matched_rules) == 2

    def test_classify_chinese_keywords(self) -> None:
        """Test classification with Chinese keywords."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(
            name="Chinese Urgent",
            rule_type="keyword",
            patterns=["紧急", "重要"],
            importance="critical",
        )
        classifier.rules = [rule]

        email = {
            "sender": "test@test.com",
            "subject": "紧急通知",
            "body_text": "",
        }
        result = classifier.classify(email)

        assert result.importance == "critical"
        assert "Chinese Urgent" in result.matched_rules


class TestClassifyAggregation:
    """Tests for rule aggregation in classification."""

    def test_classify_aggregation_multiple_rules(self) -> None:
        """Test aggregation when multiple rules match."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rules = [
            Rule(name="Sender", rule_type="sender", patterns=["@company.com"], importance="high", weight=1.0),
            Rule(name="Keyword", rule_type="keyword", patterns=["urgent"], importance="critical", weight=2.0),
        ]
        classifier.rules = rules

        email = {
            "sender": "boss@company.com",
            "subject": "URGENT meeting",
            "body_text": "",
        }
        result = classifier.classify(email)

        assert len(result.matched_rules) == 2
        # Higher weight (2.0) for critical wins over high (1.0)
        assert result.importance == "critical"

    def test_classify_conflicting_rules(self) -> None:
        """Test handling of conflicting rule matches."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rules = [
            Rule(name="Rule A", rule_type="keyword", patterns=["test"], importance="low", weight=1.0),
            Rule(name="Rule B", rule_type="keyword", patterns=["test"], importance="critical", weight=2.0),
        ]
        classifier.rules = rules

        email = {"sender": "test@test.com", "subject": "test", "body_text": ""}
        result = classifier.classify(email)

        # Higher weight rule wins
        assert result.importance == "critical"

    def test_classify_no_matching_rules(self) -> None:
        """Test classification when no rules match."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rules = [
            Rule(name="No Match", rule_type="keyword", patterns=["specificword123"]),
        ]
        classifier.rules = rules

        email = {
            "sender": "random@example.com",
            "subject": "Random subject",
            "body_text": "Random body content",
        }
        result = classifier.classify(email)

        assert result.importance == "normal"
        assert result.category == "uncategorized"
        assert result.confidence == 0.5
        assert result.matched_rules == []


class TestClassifyConfidence:
    """Tests for confidence calculation."""

    def test_confidence_single_match(self) -> None:
        """Test confidence with single rule match."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rules = [
            Rule(name="Rule A", rule_type="keyword", patterns=["test"], importance="high", weight=1.0),
            Rule(name="Rule B", rule_type="keyword", patterns=["other"], importance="low", weight=1.0),
        ]
        classifier.rules = rules

        email = {"sender": "test@test.com", "subject": "test", "body_text": ""}
        result = classifier.classify(email)

        # Single match with weight 1.0 out of total weight 2.0 = 0.5
        assert result.confidence == 0.5
        assert 0.0 <= result.confidence <= 1.0

    def test_confidence_multiple_matches(self) -> None:
        """Test confidence with multiple rule matches."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rules = [
            Rule(name="Rule A", rule_type="keyword", patterns=["test"], importance="high", weight=1.0),
            Rule(name="Rule B", rule_type="keyword", patterns=["subject"], importance="low", weight=1.0),
        ]
        classifier.rules = rules

        email = {"sender": "test@test.com", "subject": "test subject", "body_text": ""}
        result = classifier.classify(email)

        # Both match: 2.0 out of 2.0 total = 1.0
        assert result.confidence == 1.0

    def test_confidence_high_weight_rule(self) -> None:
        """Test confidence contribution of high-weight rules."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rules = [
            Rule(name="High Weight", rule_type="keyword", patterns=["test"], importance="critical", weight=2.0),
            Rule(name="Low Weight", rule_type="keyword", patterns=["other"], importance="low", weight=0.5),
        ]
        classifier.rules = rules

        email = {"sender": "test@test.com", "subject": "test", "body_text": ""}
        result = classifier.classify(email)

        # Single high weight match: 2.0 out of 2.5 total = 0.8
        assert result.confidence == 0.8


class TestClassifyBatch:
    """Tests for batch classification."""

    def test_classify_batch(self) -> None:
        """Test batch classification of multiple emails."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rules = [
            Rule(name="Urgent", rule_type="keyword", patterns=["urgent"], importance="critical"),
            Rule(name="Normal", rule_type="keyword", patterns=["normal"], importance="normal"),
        ]
        classifier.rules = rules

        emails = [
            {"sender": "test@test.com", "subject": "URGENT", "body_text": ""},
            {"sender": "test@test.com", "subject": "Normal email", "body_text": ""},
            {"sender": "test@test.com", "subject": "Random", "body_text": ""},
        ]

        results = classifier.classify_batch(emails)

        assert len(results) == 3
        assert results[0].importance == "critical"
        assert results[1].importance == "normal"
        assert results[2].importance == "normal"  # Default
        assert results[2].category == "uncategorized"

    def test_classify_real_email(self) -> None:
        """Integration test with realistic email."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        # Use default rules
        classifier.rules = get_default_rules()

        email = {
            "sender": "boss@company.com",
            "subject": "紧急会议通知",
            "body_text": "请确认参加",
        }
        result = classifier.classify(email)

        # Should match urgent keywords
        assert result.importance in ("critical", "high")
        assert len(result.matched_rules) > 0


class TestManualReclassify:
    """Tests for manual reclassification."""

    def test_manual_reclassify_updates_classification(self) -> None:
        """Test that manual reclassification updates the email."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(name="Auto", rule_type="keyword", patterns=["test"], importance="low")
        classifier.rules = [rule]

        email = {"sender": "test@test.com", "subject": "test", "body_text": ""}

        # Get automatic classification
        auto_result = classifier.classify(email)
        assert auto_result.importance == "low"

        # Manual override
        manual_result = Classification(
            importance="critical",
            category="work",
            confidence=1.0,
            matched_rules=["Manual Override"],
            manual_override=True,
        )
        assert manual_result.manual_override is True
        assert manual_result.importance == "critical"

    def test_manual_reclassify_overrides_automatic(self) -> None:
        """Test that manual classification overrides automatic."""
        manual_result = Classification(
            importance="low",
            category="promo",
            confidence=1.0,
            matched_rules=[],
            manual_override=True,
        )

        # Manual classification should have certainty
        assert manual_result.confidence == 1.0
        assert manual_result.manual_override is True

    def test_manual_reclassify_resets_override(self) -> None:
        """Test resetting manual override to automatic."""
        from scripts.mail_manager.classifier import EmailClassifier

        classifier = EmailClassifier()
        rule = Rule(name="Test", rule_type="keyword", patterns=["urgent"], importance="critical")
        classifier.rules = [rule]

        email = {"sender": "test@test.com", "subject": "urgent", "body_text": ""}

        # Re-run automatic classification
        result = classifier.classify(email)
        assert result.manual_override is False
        assert result.importance == "critical"
