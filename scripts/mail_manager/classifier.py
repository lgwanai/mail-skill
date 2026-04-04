"""
Email classification module for importance and category labeling.

Provides dataclasses for classification results and rules.
Uses from __future__ import annotations for Python 3.8 compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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
