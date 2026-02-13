
import os
import xml.etree.ElementTree as ET
from unittest.mock import patch, mock_open

import pytest

from rv_llm.llm.prompt.template.xml_utils import (
    load_xml_file,
    extract_template_metadata,
    extract_template_variables,
    extract_template_roles,
)


@pytest.fixture
def mock_xml_content():
    """Provides a sample XML content for testing."""
    return """
    <template name="test_template" version="1.1" extends="base_template">
        <metadata>
            <author>Test Author</author>
            <description>A test template.</description>
        </metadata>
        <variables>
            <required>req_var1</required>
            <required>req_var2</required>
            <optional>opt_var1</optional>
        </variables>
        <roles>
            <system><![CDATA[System message with {{ req_var1 }}]]></system>
            <user>User message with {{ opt_var1 }}</user>
        </roles>
    </template>
    """


@pytest.fixture
def mock_xml_with_role_vars():
    """Provides XML content where roles define variables for a parent template."""
    return """
    <template name="child_template" extends="parent_template">
        <roles>
            <system>
                <variable name="parent_var1"><![CDATA[Content for parent_var1]]></variable>
            </system>
        </roles>
    </template>
    """


class TestLoadXmlFile:
    """Tests for the load_xml_file function."""

    def test_load_xml_file_success(self, mock_xml_content):
        """Test successful loading and parsing of an XML file."""
        with patch("builtins.open", mock_open(read_data=mock_xml_content)) as mock_file:
            root = load_xml_file("dummy/path.xml")
            assert root is not None
            assert root.tag == "template"
            mock_file.assert_called_once_with("dummy/path.xml", "r", encoding="utf-8")

    def test_load_xml_file_not_found(self):
        """Test that a FileNotFoundError is handled correctly."""
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = FileNotFoundError
            root = load_xml_file("nonexistent/path.xml")
            assert root is None

    def test_load_xml_file_parse_error(self):
        """Test that an XML parse error is handled correctly."""
        invalid_xml = "<template><unclosed>" 
        with patch("builtins.open", mock_open(read_data=invalid_xml)):
            root = load_xml_file("invalid.xml")
            assert root is None


class TestExtractTemplateMetadata:
    """Tests for the extract_template_metadata function."""

    def test_extract_metadata(self, mock_xml_content):
        """Test extraction of metadata from a parsed XML root."""
        root = ET.fromstring(mock_xml_content)
        metadata = extract_template_metadata(root)
        assert metadata["name"] == "test_template"
        assert metadata["version"] == "1.1"
        assert metadata["extends"] == "base_template"
        assert metadata["author"] == "Test Author"
        assert metadata["description"] == "A test template."


class TestExtractTemplateVariables:
    """Tests for the extract_template_variables function."""

    def test_extract_variables(self, mock_xml_content):
        """Test extraction of required and optional variables."""
        root = ET.fromstring(mock_xml_content)
        required, optional = extract_template_variables(root)
        assert required == {"req_var1", "req_var2"}
        assert optional == {"opt_var1"}


class TestExtractTemplateRoles:
    """Tests for the extract_template_roles function."""

    def test_extract_roles_with_cdata(self, mock_xml_content):
        """Test extraction of role content, including CDATA."""
        root = ET.fromstring(mock_xml_content)
        roles = extract_template_roles(root)
        assert "system" in roles
        assert roles["system"] == "System message with {{ req_var1 }}"
        assert "user" in roles
        assert roles["user"] == "User message with {{ opt_var1 }}"

    def test_extract_roles_with_variables(self, mock_xml_with_role_vars):
        """Test extraction of roles that define variables for a parent template."""
        root = ET.fromstring(mock_xml_with_role_vars)
        roles = extract_template_roles(root)
        assert "system" in roles
        assert isinstance(roles["system"], dict)
        assert "variable" in roles["system"]
        variables = roles["system"]["variable"]
        assert len(variables) == 1
        assert variables[0]["name"] == "parent_var1"
        assert variables[0]["text"] == "Content for parent_var1"
