"""
Classification rules loader module.

Provides functions to load classification rules from YAML configuration files.
Uses from __future__ import annotations for Python 3.8 compatibility.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from scripts.mail_manager.classifier import Rule

logger = logging.getLogger(__name__)

# Default path for classification rules configuration
DEFAULT_RULES_PATH = "config/classification_rules.yaml"


def load_rules(path: str | None = None) -> list[Rule]:
    """
    Load classification rules from a YAML configuration file.

    The YAML file should have the following structure:
    ```yaml
    rules:
      - name: "Rule Name"
        type: sender  # or keyword, sender_pattern
        patterns:
          - "pattern1"
          - "pattern2"
        importance: high  # optional: critical/high/normal/low
        category: work    # optional: work/personal/notification/promo
        weight: 1.5       # optional: confidence weight (1.0-2.0)
    ```

    Args:
        path: Path to the YAML rules file. If None, uses DEFAULT_RULES_PATH.

    Returns:
        List of Rule objects loaded from the configuration file.
        Falls back to default rules if file not found.
    """
    if path is None:
        path = DEFAULT_RULES_PATH

    try:
        with open(path) as f:
            data = yaml.safe_load(f)

        if not data or "rules" not in data:
            logger.warning(f"No rules found in {path}, using defaults")
            return get_default_rules()

        rules_data = data.get("rules", [])
        rules = []
        for rule_dict in rules_data:
            rule = Rule(
                name=rule_dict.get("name", "Unnamed Rule"),
                rule_type=rule_dict.get("type", "keyword"),
                patterns=rule_dict.get("patterns", []),
                importance=rule_dict.get("importance"),
                category=rule_dict.get("category"),
                weight=rule_dict.get("weight", 1.0),
            )
            rules.append(rule)

        logger.info(f"Loaded {len(rules)} rules from {path}")
        return rules

    except FileNotFoundError:
        logger.warning(f"Rules file not found: {path}, using defaults")
        return get_default_rules()
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in rules file: {e}")
        raise ValueError(f"Invalid rules configuration: {e}") from e


def get_default_rules() -> list[Rule]:
    """
    Get default classification rules.

    These are hardcoded fallback rules used when no configuration file
    is available. They cover common classification patterns:

    - Critical senders (management emails)
    - Urgent keywords (紧急, urgent, 重要, important, asap)
    - Verification codes (验证码, verification code, 安全码)
    - Promotional keywords (促销, 优惠, unsubscribe, 退订)
    - Work domain patterns (@company.com style patterns)

    Returns:
        List of default Rule objects.
    """
    return [
        # Critical importance - immediate attention
        Rule(
            name="Critical Senders - Management",
            rule_type="sender",
            patterns=[
                "boss@company.com",
                "ceo@company.com",
                "hr@company.com",
                "cfo@company.com",
                "cto@company.com",
            ],
            importance="critical",
            category="work",
            weight=2.0,
        ),
        Rule(
            name="Urgent Keywords",
            rule_type="keyword",
            patterns=[
                "紧急",
                "urgent",
                "重要",
                "important",
                "asap",
                "ASAP",
                "立即",
                "马上",
            ],
            importance="critical",
            weight=1.5,
        ),
        # High importance - prompt attention
        Rule(
            name="Verification Codes",
            rule_type="keyword",
            patterns=[
                "验证码",
                "verification code",
                "安全码",
                "activation code",
                "确认码",
                "动态密码",
            ],
            category="notification",
            importance="high",
            weight=2.0,
        ),
        Rule(
            name="Action Required Keywords",
            rule_type="keyword",
            patterns=[
                "请回复",
                "请确认",
                "请查收",
                "action required",
                "please reply",
                "确认收到",
            ],
            importance="high",
            weight=1.5,
        ),
        Rule(
            name="Financial Keywords",
            rule_type="keyword",
            patterns=[
                "账单",
                "invoice",
                "付款",
                "payment",
                "收据",
                "receipt",
                "合同",
                "contract",
            ],
            importance="high",
            category="work",
            weight=1.5,
        ),
        # Work category
        Rule(
            name="Work Domain Senders",
            rule_type="sender_pattern",
            patterns=[
                "@company\\.com$",
                "@internal\\.company\\.com$",
                "@corp\\.com$",
                "@office\\.com$",
            ],
            category="work",
            importance="normal",
            weight=1.0,
        ),
        # Personal category
        Rule(
            name="Personal Email Domains",
            rule_type="sender_pattern",
            patterns=[
                "@qq\\.com$",
                "@163\\.com$",
                "@126\\.com$",
                "@gmail\\.com$",
                "@outlook\\.com$",
                "@hotmail\\.com$",
                "@yahoo\\.com$",
                "@icloud\\.com$",
            ],
            category="personal",
            weight=0.8,
        ),
        # Promo category
        Rule(
            name="Promotional Keywords",
            rule_type="keyword",
            patterns=[
                "促销",
                "优惠",
                "折扣",
                "discount",
                "sale",
                "特价",
                "限时",
                "limited time",
            ],
            category="promo",
            importance="low",
            weight=1.2,
        ),
        Rule(
            name="Newsletter Indicators",
            rule_type="keyword",
            patterns=[
                "unsubscribe",
                "退订",
                "取消订阅",
                "newsletter",
                "周刊",
                "订阅",
            ],
            category="promo",
            importance="low",
            weight=1.3,
        ),
        # Notification category
        Rule(
            name="Notification Keywords",
            rule_type="keyword",
            patterns=[
                "通知",
                "notification",
                "提醒",
                "reminder",
                "系统消息",
                "自动回复",
                "auto-reply",
            ],
            category="notification",
            importance="normal",
            weight=1.0,
        ),
    ]
