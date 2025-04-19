"""Utilities for working with XML templates.

This module provides utility functions for working with XML templates,
including loading, parsing, and validation.
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set, Tuple
from xml.sax.saxutils import escape, unescape

from rvandroid.llm.constants import TemplateRole
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


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
    """Extract role content from a template XML.
    
    Args:
        root: Root element of the template XML.
        
    Returns:
        Dictionary mapping role names to content (string or dict with variable definitions).
    """
    roles = {}
    
    roles_elem = root.find("roles")
    if roles_elem is not None:
        # Map XML role tags to role constants
        role_mapping = {
            "s": TemplateRole.SYSTEM,
            "user": TemplateRole.USER,
            "assistant": TemplateRole.ASSISTANT
        }
        
        # Extract content for each role
        for xml_role, role_constant in role_mapping.items():
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
                    roles[role_constant] = variables
                    logger.debug(f"Role {xml_role} defines {len(variables['variable'])} variables for parent template")
                # Otherwise, get the direct content
                elif role_elem.text:
                    # Unescape CDATA content
                    roles[role_constant] = unescape(role_elem.text.strip())
                    logger.debug(f"Role {xml_role} has {len(roles[role_constant])} chars of direct content")
                # Check for CDATA content
                else:
                    for child in role_elem:
                        if child.tag == "![CDATA[":
                            roles[role_constant] = child.text
                            logger.debug(f"Role {xml_role} has {len(roles[role_constant])} chars of CDATA content")
                            break
    
    return roles


def create_template_xml_string(
    name: str,
    version: str,
    description: str,
    author: str,
    created: str,
    required_vars: List[str],
    optional_vars: List[str],
    system_content: Optional[str] = None,
    user_content: str = None,
    assistant_content: Optional[str] = None
) -> str:
    """Create an XML string for a template.
    
    Args:
        name: Template name.
        version: Template version.
        description: Template description.
        author: Template author.
        created: Creation date (YYYY-MM-DD).
        required_vars: List of required variables.
        optional_vars: List of optional variables.
        system_content: Content for system role (optional).
        user_content: Content for user role.
        assistant_content: Content for assistant role (optional).
        
    Returns:
        XML string for the template.
    """
    # Create XML string
    xml_parts = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<template name="{name}" version="{version}">',
        '  <metadata>',
        f'    <description>{description}</description>',
        f'    <created>{created}</created>',
        f'    <author>{author}</author>',
        '  </metadata>',
        '  <variables>'
    ]
    
    # Add required variables
    for var in required_vars:
        xml_parts.append(f'    <required>{var}</required>')
    
    # Add optional variables
    for var in optional_vars:
        xml_parts.append(f'    <optional>{var}</optional>')
    
    xml_parts.append('  </variables>')
    xml_parts.append('  <roles>')
    
    # Add roles with CDATA for content
    if system_content:
        xml_parts.append('    <s><![CDATA[')
        xml_parts.append(system_content)
        xml_parts.append('    ]]></s>')
    
    if user_content:
        xml_parts.append('    <user><![CDATA[')
        xml_parts.append(user_content)
        xml_parts.append('    ]]></user>')
    
    if assistant_content:
        xml_parts.append('    <assistant><![CDATA[')
        xml_parts.append(assistant_content)
        xml_parts.append('    ]]></assistant>')
    
    xml_parts.append('  </roles>')
    xml_parts.append('</template>')
    
    return '\n'.join(xml_parts)


def create_default_templates(output_dir: str) -> List[str]:
    """Create default XML templates in the specified directory.
    
    Args:
        output_dir: Directory to create templates in.
        
    Returns:
        List of paths to created template files.
    """
    os.makedirs(output_dir, exist_ok=True)
    created_files = []
    
    # Standard template
    standard_template_path = os.path.join(output_dir, "standard.xml")
    standard_template = create_template_xml_string(
        name="standard",
        version="1.0",
        description="Standard template for Android testing",
        author="RV-Android Team",
        created="2025-04-17",
        required_vars=["screen_elements"],
        optional_vars=["additional_guidelines", "ui_patterns", "monitored_operations"],
        system_content=(
            "You are an Android testing assistant. Your task is to help test the Android application by identifying UI elements and suggesting testing actions.\n\n"
            "The current screen contains the following UI elements:\n"
            "{screen_elements}\n\n"
            "{#if ui_patterns}I've identified the following UI patterns:\n"
            "{ui_patterns}\n\n"
            "{#endif}{#if monitored_operations}Pay attention to monitored operations:\n"
            "{monitored_operations.summary}\n\n"
            "{#endif}"
        ),
        user_content=(
            "Based on the current screen, suggest a single testing action that would help explore the application functionality and potentially trigger monitored operations.{#if additional_guidelines}\n\n"
            "{additional_guidelines}{#endif}"
        )
    )
    
    # Batch action template
    batch_template_path = os.path.join(output_dir, "batch_action.xml")
    batch_template = create_template_xml_string(
        name="batch_action",
        version="1.0",
        description="Template for generating batches of testing actions",
        author="RV-Android Team",
        created="2025-04-17",
        required_vars=["screen_elements"],
        optional_vars=["additional_guidelines", "ui_patterns", "monitored_operations", "testing_history"],
        system_content=(
            "You are an Android testing automation assistant. Your task is to generate a batch of specific testing actions based on the current application state.\n\n"
            "Current screen information:\n"
            "{screen_elements}\n\n"
            "{#if ui_patterns}UI patterns identified:\n"
            "{ui_patterns}\n\n"
            "{#endif}{#if monitored_operations}Monitored operations context:\n"
            "{monitored_operations.summary}\n\n"
            "{#endif}{#if testing_history}Testing history:\n"
            "{testing_history}\n\n"
            "{#endif}"
        ),
        user_content=(
            "Based on the current screen, generate a JSON array of 3-5 testing actions. Each action should have:\n"
            "- 'action_type': The type of action (tap, long_press, text_input, swipe, etc.)\n"
            "- 'target': Description of the UI element to interact with\n"
            "- 'resource_id' (optional): The resource ID of the target element\n"
            "- 'coordinates' (optional): Screen coordinates [x, y] if needed\n"
            "- 'input_value' (optional): For text inputs\n"
            "- 'description': Short description of the action purpose\n\n"
            "Format your response as a valid JSON array.\n"
            "{#if additional_guidelines}\n\n"
            "{additional_guidelines}{#endif}"
        )
    )
    
    # Write templates to files
    try:
        with open(standard_template_path, "w", encoding="utf-8") as f:
            f.write(standard_template)
        created_files.append(standard_template_path)
        logger.info(f"Created default template: {standard_template_path}")
    except Exception as e:
        logger.error(f"Error creating standard template: {e}", exc_info=True)
    
    try:
        with open(batch_template_path, "w", encoding="utf-8") as f:
            f.write(batch_template)
        created_files.append(batch_template_path)
        logger.info(f"Created default template: {batch_template_path}")
    except Exception as e:
        logger.error(f"Error creating batch action template: {e}", exc_info=True)
    
    return created_files