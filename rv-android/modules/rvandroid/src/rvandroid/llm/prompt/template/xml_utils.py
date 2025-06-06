"""Utilities for working with XML templates.

This module provides utility functions for working with XML templates,
including loading, parsing, and validation to support Jinja2's native inheritance.
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set, Tuple
from xml.sax.saxutils import unescape

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

# Set up logging
logging_manager = LoggingManager.get_instance()
logger = logging_manager.get_logger(
    "llm.prompt.template.xml_utils",
    {CONTEXT_COMPONENT: "XMLUtils"}
)

# Set up error handling
error_handler = ErrorHandler.get_instance()


def load_xml_file(file_path: str) -> Optional[ET.Element]:
    """Load and parse an XML file, preserving CDATA sections.

    Args:
        file_path: Path to the XML file.

    Returns:
        Root element of the parsed XML document, or None if loading failed.
    """
    try:
        # Read the file as text first to preserve CDATA sections
        with open(file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        # Replace CDATA sections with a custom tag to preserve them
        # This workaround is needed because ElementTree doesn't properly handle CDATA
        cdata_pattern = r'<!\[CDATA\[(.*?)\]\]>'

        def replace_cdata(match):
            cdata_content = match.group(1)
            # Create a special element with the CDATA content
            return f'<![CDATA[{cdata_content}]]>'

        # Process the XML content
        modified_xml = re.sub(cdata_pattern, replace_cdata, xml_content, flags=re.DOTALL)

        # Parse the modified XML
        root = ET.fromstring(modified_xml)
        return root
    except ET.ParseError as e:
        logger.error(f"Error parsing XML file {file_path}: {e}", exc_info=True)
        error_handler.handle_error(
            e,
            context={
                "component": "XMLUtils",
                "function": "load_xml_file",
                "file_path": file_path
            }
        )
        return None
    except FileNotFoundError as e:
        logger.error(f"XML file not found: {file_path}", exc_info=True)
        error_handler.handle_error(
            e,
            context={
                "component": "XMLUtils",
                "function": "load_xml_file",
                "file_path": file_path
            }
        )
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading XML file {file_path}: {e}", exc_info=True)
        error_handler.handle_error(
            e,
            context={
                "component": "XMLUtils",
                "function": "load_xml_file",
                "file_path": file_path
            }
        )
        return None


def extract_template_metadata(root: ET.Element) -> Dict[str, str]:
    """Extract metadata from a template XML.

    Args:
        root: Root element of the template XML.

    Returns:
        Dictionary of metadata values.
    """
    metadata = {}

    # Extract template attributes
    metadata["name"] = root.get("name", "unknown")
    metadata["version"] = root.get("version", "1.0")
    metadata["extends"] = root.get("extends", "")  # Extract parent template name

    # Extract metadata elements
    metadata_elem = root.find("metadata")
    if metadata_elem is not None:
        for child in metadata_elem:
            metadata[child.tag] = child.text or ""

    return metadata


def extract_template_variables(root: ET.Element) -> Tuple[Set[str], Set[str]]:
    """Extract required and optional variables from a template XML.

    Args:
        root: Root element of the template XML.

    Returns:
        Tuple of (required_variables, optional_variables) as sets.
    """
    required_vars = set()
    optional_vars = set()

    variables_elem = root.find("variables")
    if variables_elem is not None:
        # Extract required variables
        for var_elem in variables_elem.findall("required"):
            if var_elem.text:
                required_vars.add(var_elem.text.strip())

        # Extract optional variables
        for var_elem in variables_elem.findall("optional"):
            if var_elem.text:
                optional_vars.add(var_elem.text.strip())

    return required_vars, optional_vars


def extract_template_roles(root: ET.Element) -> Dict[str, any]:
    """Extract role content from a template XML, handling Jinja2 native inheritance.

    Args:
        root: Root element of the template XML.

    Returns:
        Dictionary mapping role names to content (string or dict with variable definitions).
    """
    roles = {}

    roles_elem = root.find("roles")
    if roles_elem is not None:
        # Map XML role tags to roles
        role_mapping = {
            "system": "system",
            "s": "system",  # Shorthand for system
            "user": "user",
            "assistant": "assistant"
        }

        # Extract content for each role
        for xml_role, role in role_mapping.items():
            role_elem = roles_elem.find(xml_role)

            if role_elem is not None:
                # Try to find variable sections first (for roles that define variables for parent templates)
                variable_elements = role_elem.findall("variable")

                # If this role defines variables for a parent template
                if variable_elements:
                    logger.debug(f"Found {len(variable_elements)} variable definitions in {xml_role} role")
                    variables = {"variable": []}

                    for var_elem in variable_elements:
                        var_name = var_elem.get("name")
                        var_content = ""

                        # Get text content
                        if var_elem.text:
                            var_content += var_elem.text.strip()

                        # Extract from CDATA if present
                        for child in var_elem:
                            if child.tag == "![CDATA[":
                                var_content = child.text
                                break

                        if var_name:
                            var_entry = {
                                "name": var_name,
                                "text": var_content
                            }
                            variables["variable"].append(var_entry)
                            logger.debug(f"Added variable '{var_name}' with {len(var_content)} chars of content")

                    # Store variables dict for this role
                    roles[role] = variables
                    logger.debug(f"Role {xml_role} defines {len(variables['variable'])} variables for parent template")
                # Otherwise, get the direct content
                elif role_elem.text:
                    # Unescape CDATA content
                    roles[role] = unescape(role_elem.text.strip())
                    logger.debug(f"Role {xml_role} has {len(roles[role])} chars of direct content")
                # Check for CDATA content
                else:
                    for child in role_elem:
                        if child.tag == "![CDATA[":
                            roles[role] = child.text
                            logger.debug(f"Role {xml_role} has {len(roles[role])} chars of CDATA content")
                            break

    return roles


def create_default_templates(output_dir: str) -> List[str]:
    """Create default XML templates in the specified directory.

    Args:
        output_dir: Directory to create templates in.

    Returns:
        List of paths to created template files.
    """
    os.makedirs(output_dir, exist_ok=True)
    created_files = []

    # Create system_base.xml template
    system_base_path = os.path.join(output_dir, "system_base.xml")
    system_base = create_template_xml_string(
        name="system_base",
        version="1.0",
        description="Base system template for Android testing",
        author="RV-Android Team",
        created="2023-05-04",
        required_vars=["strategy_specific_instructions", "response_format_instructions"],
        optional_vars=["additional_guidelines", "action_history", "memory_insights", "transition_guidance"],
        system_content="""{% block system_intro %}
{% include "system_intro" %}
{% endblock %}

{% block strategy_specific_instructions %}
{{ strategy_specific_instructions }}
{% endblock %}

{% block response_format_instructions %}
{{ response_format_instructions }}
{% endblock %}

{% block system_guidelines %}
{% include "system_guidelines" %}
{% endblock %}

{% if additional_guidelines %}
{% block additional_guidelines %}
{{ additional_guidelines }}
{% endblock %}
{% endif %}"""
    )

    # Create standard_modular.xml template
    standard_modular_path = os.path.join(output_dir, "standard_modular.xml")
    standard_modular = create_template_xml_string(
        name="standard_modular",
        version="1.0",
        description="Standard template for Android testing (modular version)",
        author="RV-Android Team",
        created="2023-05-04",
        extends="system_base",
        required_vars=["ui_elements"],
        optional_vars=["additional_guidelines", "ui_patterns", "monitored_operations"],
        system_content="""{% block strategy_specific_instructions %}
{% include "standard_instructions" %}
{% endblock %}

{% block response_format_instructions %}
{% include "standard_format" %}
{% endblock %}

{% block additional_guidelines %}
{% include "standard_guidelines" %}
{% endblock %}""",
        user_content="""I'm testing an Android application and need your guidance on the next action to take.

Current Activity: {{ activity }}

Screen Elements:
{{ ui_elements }}

{% if additional_guidelines %}
GUIDELINES:
{{ additional_guidelines }}
{% endif %}"""
    )

    # Create batch_action_modular.xml template
    batch_modular_path = os.path.join(output_dir, "batch_action_modular.xml")
    batch_modular = create_template_xml_string(
        name="batch_action_modular",
        version="1.0",
        description="Template for generating batches of testing actions (modular version)",
        author="RV-Android Team",
        created="2023-05-04",
        extends="system_base",
        required_vars=["ui_elements"],
        optional_vars=["additional_guidelines", "ui_patterns", "monitored_operations", "testing_history"],
        system_content="""{% block strategy_specific_instructions %}
{% include "batch_instructions" %}
{% endblock %}

{% block response_format_instructions %}
{% include "batch_format" %}
{% endblock %}

{% block additional_guidelines %}
{% include "batch_guidelines" %}
{% endblock %}""",
        user_content="""{% include "user_base" %}

{% if ui_patterns %}
UI PATTERNS DETECTED:
{{ ui_patterns }}
{% endif %}

{% if detected_pattern == "form" %}{% include "ui_patterns/form_pattern" %}{% endif %}
{% if detected_pattern == "list" %}{% include "ui_patterns/list_pattern" %}{% endif %}

{% if workflow_guidance is defined and workflow_guidance %}
{{ workflow_guidance }}
{% endif %}

CRITICAL TASK: Analyze the current UI, identify the primary UI pattern present, and generate a batch of related actions that efficiently test this pattern.

{% if additional_guidelines is defined and additional_guidelines %}
{{ additional_guidelines }}
{% endif %}"""
    )

    # Write templates to files
    try:
        with open(system_base_path, "w", encoding="utf-8") as f:
            f.write(system_base)
        created_files.append(system_base_path)
        logger.info(f"Created default template: {system_base_path}")
    except Exception as e:
        logger.error(f"Error creating system_base template: {e}", exc_info=True)

    try:
        with open(standard_modular_path, "w", encoding="utf-8") as f:
            f.write(standard_modular)
        created_files.append(standard_modular_path)
        logger.info(f"Created default template: {standard_modular_path}")
    except Exception as e:
        logger.error(f"Error creating standard_modular template: {e}", exc_info=True)

    try:
        with open(batch_modular_path, "w", encoding="utf-8") as f:
            f.write(batch_modular)
        created_files.append(batch_modular_path)
        logger.info(f"Created default template: {batch_modular_path}")
    except Exception as e:
        logger.error(f"Error creating batch_action_modular template: {e}", exc_info=True)

    return created_files


def validate_template(root: ET.Element) -> List[str]:
    """Validate a template XML for correctness.

    Args:
        root: Root element of the template XML.

    Returns:
        List of validation errors, empty if template is valid.
    """
    errors = []

    # Check template attributes
    if not root.get("name"):
        errors.append("Template is missing 'name' attribute")

    if not root.get("version"):
        errors.append("Template is missing 'version' attribute")

    # Check for required sections
    if root.find("metadata") is None:
        errors.append("Template is missing 'metadata' section")

    if root.find("roles") is None:
        errors.append("Template is missing 'roles' section")

    # Check roles
    roles_section = root.find("roles")
    if roles_section is not None:
        if (
                roles_section.find("system") is None and
                roles_section.find("s") is None and
                roles_section.find("user") is None
        ):
            errors.append("Template must have at least a 'system' or 'user' role")

    # Check extends attribute
    extends = root.get("extends")
    if extends:
        # Check for Jinja2 extends directive in content
        system_elem = roles_section.find("system") if roles_section else None
        if system_elem is not None and system_elem.text:
            content = system_elem.text
            if not re.search(r'{%\s*extends\s+["\']', content):
                errors.append("System role in extending template should include {% extends %} directive")

    return errors
