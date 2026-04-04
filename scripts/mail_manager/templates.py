"""
Email template management module.

Provides template loading, validation, and variable substitution
for email reply templates. Uses from __future__ import annotations
for Python 3.8 compatibility.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Template:
    """Represents an email template with variable placeholders."""

    name: str
    content: str
    required_vars: list[str] = field(default_factory=list)
    optional_vars: dict[str, str] = field(default_factory=dict)


def extract_variables(content: str) -> list[str]:
    """
    Extract variable names from template content.

    Finds all {{variable}} patterns and returns unique variable names
    in order of first appearance.

    Args:
        content: Template content string with {{var}} placeholders

    Returns:
        List of unique variable names in order of appearance
    """
    # Match {{variable}} where variable is word characters only
    pattern = r'\{\{(\w+)\}\}'
    matches = re.findall(pattern, content)
    # Return unique in order of appearance
    seen: set[str] = set()
    result: list[str] = []
    for var in matches:
        if var not in seen:
            seen.add(var)
            result.append(var)
    return result


def load_template(path: str) -> Template:
    """
    Load a template from a YAML file.

    The YAML file should have the following structure:
    ```yaml
    name: "Thank You Reply"
    content: |
      Hi {{sender_name}},
      Thank you for your email dated {{date}}.
      Best regards.
    required_vars:
      - sender_name
      - date  # optional
    ```

    Args:
        path: Path to the YAML template file

    Returns:
        Template object loaded from the file

    Raises:
        FileNotFoundError: If the template file does not exist
        ValueError: If the YAML is invalid or required fields are missing
    """
    template_path = Path(path)
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {path}")

    try:
        with open(template_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid template YAML: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("Invalid template: root must be a mapping")

    if "name" not in data:
        raise ValueError("Invalid template: 'name' is required")
    if "content" not in data:
        raise ValueError("Invalid template: 'content' is required")

    name = data["name"]
    content = data["content"]

    # Extract required_vars from content if not specified
    required_vars = data.get("required_vars")
    if required_vars is None:
        required_vars = extract_variables(content)
    elif not isinstance(required_vars, list):
        required_vars = []

    return Template(
        name=name,
        content=content,
        required_vars=list(required_vars),
        optional_vars=data.get("optional_vars", {}),
    )


def validate_variables(template: Template, variables: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate that all required variables are provided.

    Args:
        template: Template to validate against
        variables: Dictionary of variable values

    Returns:
        Tuple of (is_valid, missing_vars) where missing_vars contains
        the list of missing required variable names
    """
    missing = []
    for var in template.required_vars:
        if var not in variables:
            missing.append(var)
    return (len(missing) == 0, missing)


def substitute_variables(template: Template, variables: dict[str, Any]) -> str:
    """
    Substitute variables in template content.

    Args:
        template: Template with variable placeholders
        variables: Dictionary of variable values

    Returns:
        Template content with variables substituted

    Raises:
        ValueError: If any required variable is missing
    """
    is_valid, missing = validate_variables(template, variables)
    if not is_valid:
        raise ValueError(f"Missing required variable(s): {', '.join(missing)}")

    result = template.content
    for var, value in variables.items():
        result = result.replace(f"{{{{{var}}}}}", str(value))
    return result


class TemplateManager:
    """
    Manages email templates stored as YAML files.

    Provides functionality for loading, listing, creating, and validating
    email templates stored as YAML files in a directory.
    """

    def __init__(self, templates_dir: str) -> None:
        """
        Initialize TemplateManager.

        Args:
            templates_dir: Directory containing template YAML files
        """
        self.templates_dir = Path(templates_dir)

    def list_templates(self) -> list[str]:
        """
        List all available template names.

        Returns:
            List of template names (without .yaml extension)
        """
        if not self.templates_dir.exists():
            return []
        templates = []
        for f in self.templates_dir.glob("*.yaml"):
            templates.append(f.stem)
        return sorted(templates)

    def get_template(self, name: str) -> Template:
        """
        Load a template by name.

        Args:
            name: Template name (without .yaml extension)

        Returns:
            Template object

        Raises:
            FileNotFoundError: If template file does not exist
            ValueError: If template YAML is invalid
        """
        template_path = self.templates_dir / f"{name}.yaml"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {name}")
        return load_template(str(template_path))

    def create_template(
        self,
        name: str,
        content: str,
        required_vars: list[str] | None = None,
    ) -> Template:
        """
        Create a new template and save to YAML file.

        Args:
            name: Template name
            content: Template content with {{var}} placeholders
            required_vars: List of required variable names (auto-extracted if None)

        Returns:
            Created Template object
        """
        # Create directory if needed
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Extract variables if not specified
        if required_vars is None:
            required_vars = extract_variables(content)

        # Create template object
        template = Template(
            name=name,
            content=content,
            required_vars=required_vars,
        )

        # Save to YAML file
        template_path = self.templates_dir / f"{self._sanitize_name(name)}.yaml"
        data = {
            "name": name,
            "content": content,
            "required_vars": required_vars,
        }
        with open(template_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"Created template: {name}")
        return template

    def validate_variables(self, template: Template, variables: dict[str, Any]) -> list[str]:
        """
        Validate that all required variables are provided.

        Args:
            template: Template to validate against
            variables: Dictionary of variable values

        Returns:
            List of missing required variable names (empty if all present)
        """
        _, missing = validate_variables(template, variables)
        return missing

    def _sanitize_name(self, name: str) -> str:
        """Sanitize template name for use as filename."""
        # Replace spaces and special chars with underscore
        sanitized = re.sub(r'[^\w\-]', '_', name.lower())
        return sanitized
