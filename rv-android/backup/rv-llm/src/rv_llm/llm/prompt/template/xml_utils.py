"""Utilities for working with XML templates.

This module provides utility functions for working with XML templates,
including loading, parsing, and validation to support Jinja2's native inheritance.
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Set, Tuple
from xml.sax.saxutils import unescape

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

# Set up logging
logging_manager = LoggingManager.get_instance()
logger = logging_manager.get_logger(
    "rv_llm.llm.prompt.template.xml_utils",
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
