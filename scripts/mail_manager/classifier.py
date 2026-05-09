"""
Email classification module for importance and category labeling.

Provides dataclasses for classification results and rules, and the EmailClassifier
class for rule-based email classification.
Uses from __future__ import annotations for Python 3.8 compatibility.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mail_manager.llm.client import LLMClient


@dataclass
class Classification:
    """
    Represents the classification result for an email.

    Attributes:
        importance: Email importance level (critical/high/normal/low)
        category: Email category (work/personal/notification/promo/uncategorized)
        confidence: Classification confidence score (0.0-1.0)
        matched_rules: List of rule names that matched this email
        manual_override: Whether this classification was manually set
    """

    importance: str  # "critical", "high", "normal", "low"
    category: str  # "work", "personal", "notification", "promo", "uncategorized"
    confidence: float  # 0.0 to 1.0
    matched_rules: list[str] = field(default_factory=list)
    manual_override: bool = False


@dataclass
class Rule:
    """
    Represents a classification rule.

    Rules are matched against emails to determine importance and category.
    Each rule has a type (sender/keyword/sender_pattern), patterns to match,
    and optional importance/category assignments with a confidence weight.

    Attributes:
        name: Descriptive name for the rule
        rule_type: Type of rule (sender/keyword/sender_pattern)
        patterns: List of patterns to match
        importance: Importance level to assign if matched
        category: Category to assign if matched
        weight: Confidence weight for this rule (1.0-2.0)
    """

    name: str
    rule_type: str  # "sender", "keyword", "sender_pattern"
    patterns: list[str]
    importance: str | None = None
    category: str | None = None
    weight: float = 1.0


@dataclass
class ClassificationResult:
    """
    Represents a classification result for batch operations.

    Used when classifying multiple emails to track processing time
    and individual results.

    Attributes:
        email_id: The message_id of the classified email
        classification: The classification result
        processing_time_ms: Time taken to classify in milliseconds
    """

    email_id: str
    classification: Classification
    processing_time_ms: float


class EmailClassifier:
    """
    Rule-based email classifier.

    Classifies emails using configurable rules for sender matching,
    keyword matching, and pattern-based classification.

    Attributes:
        rules: List of Rule objects to use for classification
    """

    def __init__(self, rules_path: str | None = None) -> None:
        """
        Initialize the email classifier.

        Args:
            rules_path: Path to YAML rules configuration file.
                        If None, uses default rules.
        """
        # Import here to avoid circular import with rules.py
        from scripts.mail_manager.rules import load_rules

        self.rules = load_rules(rules_path)

    def _match_rule(self, rule: Rule, email: dict) -> bool:
        """
        Check if a rule matches an email.

        Args:
            rule: The rule to check
            email: Email dict with sender, subject, body_text fields

        Returns:
            True if the rule matches, False otherwise
        """
        if rule.rule_type == "sender":
            return self._match_sender(rule, email)
        elif rule.rule_type == "sender_pattern":
            return self._match_sender_pattern(rule, email)
        elif rule.rule_type == "keyword":
            return self._match_keyword(rule, email)
        return False

    def _match_sender(self, rule: Rule, email: dict) -> bool:
        """
        Check if sender rule matches email.

        Performs case-insensitive substring matching on the sender field.

        Args:
            rule: Sender rule with patterns to match
            email: Email dict with sender field

        Returns:
            True if any pattern matches the sender
        """
        sender = (email.get("sender") or "").lower()
        for pattern in rule.patterns:
            if pattern.lower() in sender:
                return True
        return False

    def _match_sender_pattern(self, rule: Rule, email: dict) -> bool:
        """
        Check if sender pattern rule matches email using regex.

        Args:
            rule: Sender pattern rule with regex patterns
            email: Email dict with sender field

        Returns:
            True if any regex pattern matches the sender
        """
        sender = email.get("sender", "")
        for pattern in rule.patterns:
            if re.search(pattern, sender, re.IGNORECASE):
                return True
        return False

    def _match_keyword(self, rule: Rule, email: dict) -> bool:
        """
        Check if keyword rule matches email subject or body.

        Performs case-insensitive substring matching on subject and body.
        Only checks first 1000 characters of body for performance.

        Args:
            rule: Keyword rule with patterns to match
            email: Email dict with subject and body_text fields

        Returns:
            True if any pattern matches subject or body
        """
        subject = (email.get("subject") or "").lower()
        body = (email.get("body_text") or "").lower()[:1000]
        for pattern in rule.patterns:
            pattern_lower = pattern.lower()
            if pattern_lower in subject or pattern_lower in body:
                return True
        return False

    def classify(self, email: dict) -> Classification:
        """
        Classify an email using configured rules.

        Applies all rules to the email and aggregates results using
        weighted voting. Returns default classification if no rules match.

        Args:
            email: Email dict with sender, subject, body_text fields

        Returns:
            Classification with importance, category, confidence, and matched rules
        """
        matches: list[Rule] = []
        for rule in self.rules:
            if self._match_rule(rule, email):
                matches.append(rule)

        if not matches:
            return Classification(
                importance="normal",
                category="uncategorized",
                confidence=0.5,
                matched_rules=[],
            )

        # Weighted voting for importance and category
        importance_scores: dict[str, float] = defaultdict(float)
        category_scores: dict[str, float] = defaultdict(float)
        total_weight = 0.0

        for rule in matches:
            if rule.importance:
                importance_scores[rule.importance] += rule.weight
            if rule.category:
                category_scores[rule.category] += rule.weight
            total_weight += rule.weight

        # Select highest scoring importance and category
        importance = (
            max(importance_scores, key=importance_scores.get) if importance_scores else "normal"
        )
        category = (
            max(category_scores, key=category_scores.get) if category_scores else "uncategorized"
        )

        # Confidence: ratio of matched weight to total possible weight
        max_possible_weight = sum(r.weight for r in self.rules) or 1.0
        confidence = min(1.0, total_weight / max_possible_weight)

        return Classification(
            importance=importance,
            category=category,
            confidence=confidence,
            matched_rules=[r.name for r in matches],
        )

    def classify_batch(self, emails: list[dict]) -> list[Classification]:
        """
        Classify multiple emails.

        Args:
            emails: List of email dicts

        Returns:
            List of Classification objects
        """
        return [self.classify(email) for email in emails]


def classify_with_llm(llm_client: "LLMClient", email: dict) -> Classification:
    """Classify an email using LLM.

    Uses LLM to analyze email content and determine importance and category.
    This is used as a secondary classification for emails that don't match
    any rules, or for re-classifying emails classified as "normal".

    Args:
        llm_client: LLM client for making chat completion requests.
        email: Email dict with sender, subject, body_text fields.

    Returns:
        Classification with importance, category, confidence, and matched rules.

    Example:
        >>> from mail_manager.llm.client import LLMClient
        >>> llm = LLMClient()
        >>> email = {"sender": "boss@company.com", "subject": "Q3 Report", "body_text": "..."}
        >>> result = classify_with_llm(llm, email)
        >>> result.importance in ["critical", "high", "normal", "low"]
        True
    """
    from mail_manager.llm.prompts import EMAIL_CLASSIFICATION_PROMPT

    subject = email.get("subject", "")
    sender = email.get("sender", "")
    body = (email.get("body_text", "") or "")[:500]

    prompt = EMAIL_CLASSIFICATION_PROMPT.format(
        sender=sender.replace("{", "{{").replace("}", "}}"),
        subject=subject.replace("{", "{{").replace("}", "}}"),
        body=body.replace("{", "{{").replace("}", "}}"),
    )

    try:
        response = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )

        content = response.content.strip()

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)

        importance = result.get("importance", "normal")
        category = result.get("category", "uncategorized")

        valid_importance = ["critical", "high", "normal", "low"]
        valid_category = ["work", "personal", "notification", "promo"]

        if importance not in valid_importance:
            importance = "normal"
        if category not in valid_category:
            category = "uncategorized"

        return Classification(
            importance=importance,
            category=category,
            confidence=0.8,
            matched_rules=["llm_classification"],
        )
    except Exception:
        return Classification(
            importance="normal",
            category="uncategorized",
            confidence=0.5,
            matched_rules=[],
        )
