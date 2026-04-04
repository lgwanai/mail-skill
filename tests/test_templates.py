"""Tests for YAML-based reply templates with variable placeholders.

This module tests:
- Template dataclass with name, content, required_vars
- extract_variables function for finding {{var}} patterns
- load_template for reading YAML template files
- TemplateManager for listing, getting, and creating templates
- validate_variables for pre-send validation
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from scripts.mail_manager.templates import (
    Template,
    TemplateManager,
    extract_variables,
    load_template,
    substitute_variables,
    validate_variables,
)


class TestTemplateDataclass:
    """Tests for Template dataclass."""

    def test_template_holds_name_content_required_vars(self) -> None:
        """Template dataclass holds name, content, required_vars."""
        template = Template(
            name="Thank You",
            content="Hi {{sender_name}}, thank you for {{date}}.",
            required_vars=["sender_name", "date"],
        )
        assert template.name == "Thank You"
        assert template.content == "Hi {{sender_name}}, thank you for {{date}}."
        assert template.required_vars == ["sender_name", "date"]

    def test_template_required_vars_defaults_to_empty_list(self) -> None:
        """Template required_vars defaults to empty list if not provided."""
        template = Template(
            name="Simple",
            content="Hello!",
        )
        assert template.required_vars == []


class TestExtractVariables:
    """Tests for extract_variables function."""

    def test_extract_variables_finds_single_variable(self) -> None:
        """extract_variables finds single {{var}} pattern."""
        content = "Hello {{name}}, how are you?"
        result = extract_variables(content)
        assert result == ["name"]

    def test_extract_variables_returns_empty_list_for_no_variables(self) -> None:
        """extract_variables returns empty list when no variables found."""
        content = "Hello, this is a plain text with no variables."
        result = extract_variables(content)
        assert result == []

    def test_extract_variables_handles_multiple_variables(self) -> None:
        """extract_variables handles multiple variables."""
        content = "Hi {{sender_name}}, thank you for your email on {{date}} about {{subject}}."
        result = extract_variables(content)
        assert result == ["sender_name", "date", "subject"]

    def test_extract_variables_returns_unique_in_order(self) -> None:
        """extract_variables returns unique variables in order of appearance."""
        content = "{{name}} and {{name}} again, then {{date}} and {{date}}."
        result = extract_variables(content)
        assert result == ["name", "date"]

    def test_extract_variables_ignores_invalid_patterns(self) -> None:
        """extract_variables ignores invalid variable patterns."""
        content = "{{ valid }} {{invalid}} {{123invalid}} {{{triple}}}"
        result = extract_variables(content)
        # Only valid pattern: word characters only (no spaces)
        assert "valid" not in result  # Has spaces, not matched
        assert "invalid" in result  # Valid
        # 123invalid is valid (\w includes digits), triple is also valid
        assert result == ["invalid", "123invalid", "triple"]


class TestLoadTemplate:
    """Tests for load_template function."""

    def test_load_template_reads_yaml_and_returns_template(self, tmp_path: Path) -> None:
        """load_template reads YAML file and returns Template."""
        yaml_content = """name: "Thank You Reply"
content: |
  Hi {{sender_name}},
  Thank you for your email dated {{date}}.
  Best regards.
required_vars:
  - sender_name
  - date
"""
        template_file = tmp_path / "thank_you.yaml"
        template_file.write_text(yaml_content)

        template = load_template(str(template_file))
        assert template.name == "Thank You Reply"
        assert "{{sender_name}}" in template.content
        assert "{{date}}" in template.content
        assert template.required_vars == ["sender_name", "date"]

    def test_load_template_raises_filenotfound_for_missing_file(self) -> None:
        """load_template raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_template("/nonexistent/path/template.yaml")

    def test_load_template_raises_valueerror_for_invalid_yaml(self, tmp_path: Path) -> None:
        """load_template raises ValueError for invalid YAML."""
        template_file = tmp_path / "invalid.yaml"
        template_file.write_text("name: [unclosed\n  - list")

        with pytest.raises(ValueError, match="Invalid template"):
            load_template(str(template_file))

    def test_load_template_raises_valueerror_for_missing_name(self, tmp_path: Path) -> None:
        """load_template raises ValueError when 'name' field is missing."""
        yaml_content = """content: "Hello {{name}}" """
        template_file = tmp_path / "no_name.yaml"
        template_file.write_text(yaml_content)

        with pytest.raises(ValueError, match="'name' is required"):
            load_template(str(template_file))

    def test_load_template_raises_valueerror_for_missing_content(self, tmp_path: Path) -> None:
        """load_template raises ValueError when 'content' field is missing."""
        yaml_content = """name: "Test Template" """
        template_file = tmp_path / "no_content.yaml"
        template_file.write_text(yaml_content)

        with pytest.raises(ValueError, match="'content' is required"):
            load_template(str(template_file))

    def test_load_template_extracts_vars_if_required_vars_not_specified(self, tmp_path: Path) -> None:
        """load_template extracts variables if required_vars not specified."""
        yaml_content = """name: "Auto Extract"
content: "Hi {{sender_name}}, thanks for {{subject}}."
"""
        template_file = tmp_path / "auto_extract.yaml"
        template_file.write_text(yaml_content)

        template = load_template(str(template_file))
        assert template.required_vars == ["sender_name", "subject"]


class TestTemplateManager:
    """Tests for TemplateManager class."""

    def test_list_templates_returns_yaml_files(self, tmp_path: Path) -> None:
        """TemplateManager.list_templates returns all .yaml files in directory."""
        # Create template files
        (tmp_path / "template1.yaml").write_text("name: T1\ncontent: C1")
        (tmp_path / "template2.yaml").write_text("name: T2\ncontent: C2")
        (tmp_path / "not_template.txt").write_text("ignore me")

        manager = TemplateManager(str(tmp_path))
        templates = manager.list_templates()
        assert sorted(templates) == ["template1", "template2"]

    def test_list_templates_returns_empty_for_empty_directory(self, tmp_path: Path) -> None:
        """TemplateManager.list_templates returns empty list for empty directory."""
        manager = TemplateManager(str(tmp_path))
        assert manager.list_templates() == []

    def test_get_template_loads_by_name(self, tmp_path: Path) -> None:
        """TemplateManager.get_template loads specific template by name."""
        yaml_content = """name: "My Template"
content: "Hello {{name}}"
"""
        (tmp_path / "my_template.yaml").write_text(yaml_content)

        manager = TemplateManager(str(tmp_path))
        template = manager.get_template("my_template")
        assert template.name == "My Template"
        assert template.content == "Hello {{name}}"

    def test_get_template_raises_for_nonexistent(self, tmp_path: Path) -> None:
        """TemplateManager.get_template raises FileNotFoundError for missing template."""
        manager = TemplateManager(str(tmp_path))
        with pytest.raises(FileNotFoundError):
            manager.get_template("nonexistent")

    def test_create_template_saves_to_yaml(self, tmp_path: Path) -> None:
        """TemplateManager.create_template saves new template to YAML file."""
        manager = TemplateManager(str(tmp_path))
        template = manager.create_template(
            name="New Template",
            content="Hi {{name}}",
            required_vars=["name"],
        )

        assert template.name == "New Template"
        assert template.content == "Hi {{name}}"

        # Verify file was created
        template_file = tmp_path / "new_template.yaml"
        assert template_file.exists()

        # Verify it can be loaded back
        loaded = manager.get_template("new_template")
        assert loaded.name == "New Template"

    def test_create_template_with_auto_extracted_vars(self, tmp_path: Path) -> None:
        """TemplateManager.create_template auto-extracts variables if not specified."""
        manager = TemplateManager(str(tmp_path))
        template = manager.create_template(
            name="Auto Vars",
            content="Hi {{name}}, see you on {{date}}",
        )

        assert "name" in template.required_vars
        assert "date" in template.required_vars

    def test_validate_variables_returns_missing(self, tmp_path: Path) -> None:
        """TemplateManager.validate_variables returns list of missing required vars."""
        (tmp_path / "test.yaml").write_text(
            "name: Test\ncontent: 'Hi {{a}} {{b}}'\nrequired_vars: [a, b]"
        )
        manager = TemplateManager(str(tmp_path))
        template = manager.get_template("test")

        # Missing 'b'
        missing = manager.validate_variables(template, {"a": "value"})
        assert missing == ["b"]

    def test_validate_variables_returns_empty_when_all_present(self, tmp_path: Path) -> None:
        """TemplateManager.validate_variables returns empty list when all vars present."""
        (tmp_path / "test.yaml").write_text(
            "name: Test\ncontent: 'Hi {{a}} {{b}}'\nrequired_vars: [a, b]"
        )
        manager = TemplateManager(str(tmp_path))
        template = manager.get_template("test")

        missing = manager.validate_variables(template, {"a": "val1", "b": "val2"})
        assert missing == []


class TestValidateVariablesFunction:
    """Tests for validate_variables standalone function."""

    def test_validate_variables_returns_true_when_all_present(self) -> None:
        """validate_variables returns (True, []) when all required vars present."""
        template = Template(
            name="Test",
            content="Hi {{name}}",
            required_vars=["name"],
        )
        is_valid, missing = validate_variables(template, {"name": "John"})
        assert is_valid is True
        assert missing == []

    def test_validate_variables_returns_false_when_missing(self) -> None:
        """validate_variables returns (False, missing_list) when vars missing."""
        template = Template(
            name="Test",
            content="Hi {{name}} on {{date}}",
            required_vars=["name", "date"],
        )
        is_valid, missing = validate_variables(template, {"name": "John"})
        assert is_valid is False
        assert missing == ["date"]

    def test_validate_variables_returns_multiple_missing(self) -> None:
        """validate_variables returns all missing variables."""
        template = Template(
            name="Test",
            content="Hi {{a}} {{b}} {{c}}",
            required_vars=["a", "b", "c"],
        )
        is_valid, missing = validate_variables(template, {"b": "value"})
        assert is_valid is False
        assert sorted(missing) == ["a", "c"]


class TestSubstituteVariables:
    """Tests for substitute_variables function."""

    def test_substitute_variables_replaces_placeholders(self) -> None:
        """substitute_variables replaces {{var}} with values from dict."""
        template = Template(
            name="Test",
            content="Hi {{name}}, see you on {{date}}.",
            required_vars=["name", "date"],
        )
        result = substitute_variables(template, {"name": "John", "date": "2024-01-15"})
        assert result == "Hi John, see you on 2024-01-15."

    def test_substitute_variables_raises_on_missing_required(self) -> None:
        """substitute_variables raises ValueError if required variable missing."""
        template = Template(
            name="Test",
            content="Hi {{name}}",
            required_vars=["name"],
        )
        with pytest.raises(ValueError, match="Missing required variable"):
            substitute_variables(template, {})

    def test_substitute_variables_handles_extra_vars(self) -> None:
        """substitute_variables ignores extra variables not in template."""
        template = Template(
            name="Test",
            content="Hi {{name}}",
            required_vars=["name"],
        )
        result = substitute_variables(
            template, {"name": "John", "extra": "ignored"}
        )
        assert result == "Hi John"
