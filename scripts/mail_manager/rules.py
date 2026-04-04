"""
Classification rules loader module.

Provides functions to load classification rules from YAML configuration files.
Uses from __future__ import annotations for Python 3.8 compatibility.
"""

from __future__ import annotations

from scripts.mail_manager.classifier import Rule

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
        Currently returns empty list (stub implementation).

    TODO: Implement YAML file loading and parsing.
    """
    # Stub implementation - returns empty list
    # Will be implemented in subsequent plans
    return []


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
        Currently returns empty list (stub implementation).

    TODO: Implement default rules based on RESEARCH.md patterns.
    """
    # Stub implementation - returns empty list
    # Will be implemented in subsequent plans
    return []
