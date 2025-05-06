"""Jinja2-based template repository for the prompt system.

This module defines the Jinja2TemplateRepository class for managing XML-based
prompt templates that use Jinja2 for rendering, including loading, retrieval,
and message generation.
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set, Tuple

import jinja2

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.data_structures import LLMMessage, LLMRole, LLMTextContent
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager

from .jinja_template import Jinja2Template, FragmentDictLoader
from .xml_utils import (create_default_templates, extract_template_metadata,
                        extract_template_roles, extract_template_variables,
                        load_xml_file)


class Jinja2TemplateRepository:
    """Repository for managing Jinja2-based XML prompt templates.
    
    This repository:
    - Loads templates from XML files with Jinja2 syntax inside CDATA sections
    - Creates default templates if none exist
    - Provides templates by name
    - Generates messages for LLM communication
    - Handles template inheritance via Jinja2's extends/block system
    
    The XML structure is preserved for metadata, variables, and roles, while
    the content uses Jinja2 for powerful templating capabilities.
    """

    def __init__(self, template_dir: Optional[str] = None, fragment_dir: Optional[str] = None):
        """Initialize the Jinja2 template repository.
        
        Args:
            template_dir: The directory containing template XML files.
                If not provided, defaults to the "templates" directory
                in the same directory as this file.
            fragment_dir: The directory containing fragment XML files.
                If not provided, defaults to the "fragments" directory
                in the same directory as this file.
        """
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.prompt.template.jinja_repository",
            {CONTEXT_COMPONENT: "Jinja2TemplateRepository"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

        # Set template directory
        self.template_dir = template_dir or os.path.join(
            os.path.dirname(__file__), "templates")

        # Set fragment directory
        self.fragment_dir = fragment_dir or os.path.join(
            os.path.dirname(__file__), "fragments")

        # Ensure directories exist
        os.makedirs(self.template_dir, exist_ok=True)
        os.makedirs(self.fragment_dir, exist_ok=True)

        # Initialize template and fragment caches
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.template_objects: Dict[str, Jinja2Template] = {}
        self.fragments: Dict[str, str] = {}
        
        # Create Jinja2 environment
        self.jinja_env = self._create_jinja_environment()

        # Load templates and fragments
        self._load_templates()
        self._load_fragments()

    def _create_jinja_environment(self) -> jinja2.Environment:
        """Create a Jinja2 environment with custom settings.
        
        Returns:
            Configured Jinja2 Environment instance.
        """
        # Create a loader that can load fragments from the repository
        fragment_loader = FragmentDictLoader(self.fragments)
        
        # Create environment with appropriate settings
        env = jinja2.Environment(
            loader=fragment_loader,
            undefined=jinja2.StrictUndefined,  # Raise errors for undefined variables
            trim_blocks=True,                  # Remove first newline after a block
            lstrip_blocks=True,                # Strip tabs and spaces from the beginning of blocks
            keep_trailing_newline=True,        # Preserve trailing newlines
            extensions=['jinja2.ext.loopcontrols', 'jinja2.ext.do']  # Additional extensions
        )
        
        # Add custom filters
        env.filters['default_if_none'] = lambda value, default: default if value is None else value
        
        # Add custom tests
        env.tests['empty'] = lambda value: value is None or value == '' or value == [] or value == {}
        
        return env

    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the repository with the given configuration.
        
        Args:
            config: The configuration to use.
        """
        self.logger.info("Configuring Jinja2TemplateRepository")

        # Check if custom template directory is specified
        if hasattr(config, 'llm_config') and hasattr(config.llm_config, 'template_dir'):
            custom_template_dir = config.llm_config.template_dir
            if custom_template_dir:
                self.logger.info(f"Custom template directory specified: {custom_template_dir}")
                self.template_dir = custom_template_dir
                self._load_templates()

        # Check if custom fragment directory is specified
        if hasattr(config, 'llm_config') and hasattr(config.llm_config, 'fragment_dir'):
            custom_fragment_dir = config.llm_config.fragment_dir
            if custom_fragment_dir:
                self.logger.info(f"Custom fragment directory specified: {custom_fragment_dir}")
                self.fragment_dir = custom_fragment_dir
                self._load_fragments()

        # Ensure critical fragments are available
        self._ensure_critical_fragments()
        
        # Recreate Jinja environment after configuration changes
        self.jinja_env = self._create_jinja_environment()

    def _load_templates(self) -> None:
        """Load templates from XML files in the template directory and RVDroid directory."""
        self.logger.info(f"Loading templates from {self.template_dir}")

        try:
            # If the directory doesn't exist or is empty, create default templates
            if not os.path.exists(self.template_dir) or not os.listdir(self.template_dir):
                self.logger.warning("Template directory empty or not found, creating default templates")
                create_default_templates(self.template_dir)

            # Define directories to load templates from
            template_dirs = [self.template_dir]

            # Add RVDroid template directory if it exists
            rvdroid_template_dir = os.path.join(self.template_dir, "rvdroid")
            if os.path.exists(rvdroid_template_dir):
                template_dirs.append(rvdroid_template_dir)
                self.logger.info(f"Found RVDroid template directory: {rvdroid_template_dir}")

            # Load templates from all directories
            for template_dir in template_dirs:
                self._load_templates_from_directory(template_dir)

            self.logger.info(f"Loaded {len(self.templates)} templates in total")
        except Exception as e:
            self.logger.error(f"Error loading templates: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "Jinja2TemplateRepository",
                    "template_dir": self.template_dir
                }
            )

    def _load_templates_from_directory(self, directory: str) -> None:
        """Load templates from XML files in the specified directory.
        
        Args:
            directory: The directory containing template XML files.
        """
        self.logger.debug(f"Loading templates from directory: {directory}")

        try:
            # Process all template files
            template_info = {}

            for filename in os.listdir(directory):
                if filename.endswith(".xml"):
                    template_path = os.path.join(directory, filename)
                    template_name = filename.replace(".xml", "")

                    # Determine category based on directory
                    if directory.endswith("rvdroid"):
                        # For templates in the rvdroid directory, use the "rvdroid:" prefix
                        template_key = f"rvdroid:{template_name}"
                    else:
                        template_key = template_name

                    try:
                        # Load the XML file
                        root = load_xml_file(template_path)
                        if root is None:
                            self.logger.error(f"Failed to load template: {template_path}")
                            continue

                        # Extract metadata
                        metadata = extract_template_metadata(root)

                        # Extract variables
                        required_vars, optional_vars = extract_template_variables(root)

                        # Extract role content
                        roles = extract_template_roles(root)

                        # Store template data
                        template_data = {
                            "metadata": metadata,
                            "required_variables": list(required_vars),
                            "optional_variables": list(optional_vars),
                            "roles": roles,
                            "path": template_path,
                            "extends": metadata.get("extends", "")
                        }

                        template_info[template_key] = template_data
                    except Exception as e:
                        self.logger.error(f"Error loading template {template_key}: {e}")
                        self.error_handler.handle_error(
                            e,
                            context={
                                "component": "Jinja2TemplateRepository",
                                "template_path": template_path
                            }
                        )
            
            # After loading all templates, store them and create template objects
            for template_key, template_data in template_info.items():
                try:
                    # Store the template data
                    self.templates[template_key] = template_data
                    
                    # Process each role into a template object
                    self._create_template_objects(template_key, template_data)
                    
                    self.logger.debug(f"Processed template: {template_key}")
                except Exception as e:
                    self.logger.error(f"Error processing template {template_key}: {e}")
                    self.error_handler.handle_error(
                        e,
                        context={
                            "component": "Jinja2TemplateRepository",
                            "template_key": template_key
                        }
                    )
        except Exception as e:
            self.logger.error(f"Error loading templates from {directory}: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "Jinja2TemplateRepository",
                    "directory": directory
                }
            )

    def _create_template_objects(self, template_key: str, template_data: Dict[str, Any]) -> None:
        """Create Jinja2Template objects for each role in the template.
        
        Args:
            template_key: The key for the template.
            template_data: The template data.
        """
        template_name = template_data["metadata"]["name"]
        roles = template_data["roles"]
        required_vars = set(template_data["required_variables"])
        
        # Create template objects for each role
        for role, content in roles.items():
            object_key = f"{template_key}.{role}"
            
            # Skip empty or variable-only roles
            if not content or (isinstance(content, dict) and "variable" in content):
                continue
                
            # Create Jinja2Template object
            template_obj = Jinja2Template(
                content,
                template_name,
                role,
                required_variables=required_vars,
                fragment_repository=self.fragments,
                jinja_env=self.jinja_env
            )
            
            # Store the template object
            self.template_objects[object_key] = template_obj
            self.logger.debug(f"Created template object for {object_key}")

    def _load_fragments(self) -> None:
        """Load fragments from XML files in the fragment directory and its subdirectories."""
        self.logger.info(f"Loading fragments from {self.fragment_dir}")

        try:
            # Check if the fragment directory exists
            if not os.path.exists(self.fragment_dir):
                self.logger.warning(f"Fragment directory does not exist: {self.fragment_dir}")
                self.logger.warning("Creating fragments directory...")
                os.makedirs(self.fragment_dir, exist_ok=True)

                # Create some default fragments for basic templates
                self._create_default_fragments()

            # Process the main fragment directory first
            if os.path.exists(self.fragment_dir):
                self.logger.info(f"Processing main fragment directory: {self.fragment_dir}")
                self._load_fragments_from_directory(self.fragment_dir)

                # Then process subdirectories
                for subdir_name in os.listdir(self.fragment_dir):
                    subdir_path = os.path.join(self.fragment_dir, subdir_name)
                    if os.path.isdir(subdir_path):
                        self.logger.info(f"Processing fragment subdirectory: {subdir_path}")
                        self._load_fragments_from_directory(subdir_path)

            # Log summary of loaded fragments
            self.logger.info(f"Loaded {len(self.fragments)} fragments")
            
            # Validate critical fragments
            self._ensure_critical_fragments()
            
            # Update Jinja environment with loaded fragments
            self.jinja_env = self._create_jinja_environment()

        except Exception as e:
            self.logger.error(f"Error loading fragments: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "Jinja2TemplateRepository",
                    "fragment_dir": self.fragment_dir
                }
            )

    def _create_default_fragments(self) -> None:
        """Create default fragments for essential functionality."""
        self.logger.info("Creating default fragments for basic functionality")

        # Ensure ui_patterns directory exists
        ui_patterns_dir = os.path.join(self.fragment_dir, "ui_patterns")
        os.makedirs(ui_patterns_dir, exist_ok=True)

        # Define essential fragments and their content
        default_fragments = {
            # Basic system fragments
            "system_intro": """You are an Android testing assistant. Your task is to help test Android applications by recommending the best actions to take based on the current screen state.""",
            "system_guidelines": """GENERAL GUIDELINES:
- Focus on thorough exploration of the application
- Target actions that are most likely to trigger interesting behavior
- Pay attention to input validation and edge cases
- Attempt to reach all parts of the application""",

            # Standard prompt fragments
            "standard_instructions": """Your task is to analyze the current state of an Android application and recommend the single most effective action to take next for testing purposes.""",
            "standard_format": """RESPONSE FORMAT:
Your response must be a valid JSON object with the following structure:
{
  "action": {
    "type": "ACTION_TYPE",  // e.g., "CLICK", "SET_TEXT", "LONG_CLICK"
    "target": "element description or action_id",
    "value": "text to enter" // only for SET_TEXT actions
  },
  "explanation": "Brief explanation of why this action was chosen"
}""",
            "standard_guidelines": """IMPORTANT RULES:
1. SEQUENCE MATTERS - actions must be in a logical order (e.g., fill all form fields BEFORE submitting)
2. FORM FILLING - when you see a form, ALWAYS fill out all required fields before clicking submit/next buttons
3. NEVER include a BACK action unless absolutely necessary (only when no other actions are possible)
4. Prioritize exploring new functionality over revisiting previous screens
5. For text inputs, provide appropriate values based on the field type (emails, passwords, etc.)
6. Choose the single most effective action for thorough testing""",

            # Batch action fragments
            "batch_instructions": """Your task is to analyze the current state of an Android application and recommend a BATCH of effective actions to execute in sequence.""",
            "batch_format": """RESPONSE FORMAT:
Your response must be a valid JSON object with the following structure:
{
  "actions": [
    {
      "type": "ACTION_TYPE",  // e.g., "CLICK", "SET_TEXT", "LONG_CLICK"
      "target": "element description or action_id",
      "value": "text to enter" // only for SET_TEXT actions
    },
    // Additional actions...
  ],
  "explanation": "Brief explanation of this action sequence"
}""",

            # User fragments
            "user_base": """I'm testing an Android application and need your guidance on the next action to take.

Current Activity: {{ activity }}

Screen Elements:
{{ ui_elements }}"""
        }

        # Write default fragments to files
        for fragment_name, content in default_fragments.items():
            fragment_path = os.path.join(self.fragment_dir, f"{fragment_name}.xml")

            try:
                with open(fragment_path, 'w', encoding='utf-8') as f:
                    f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<fragment name="{fragment_name}">
  <![CDATA[
{content}
  ]]>
</fragment>""")
                self.logger.info(f"Created default fragment: {fragment_name}")
            except Exception as e:
                self.logger.error(f"Error creating default fragment {fragment_name}: {e}")

        # Create UI pattern fragments
        ui_patterns = {
            "form_pattern": """FORM HANDLING GUIDANCE:
- Identify all required input fields before submission
- Fill fields with valid data appropriate to their type
- For login forms, use test credentials
- Check for validation messages after submission""",

            "list_pattern": """LIST HANDLING GUIDANCE:
- Explore both scrolling up and down
- Try selecting items at different positions
- Check for interactive elements within list items
- Try to reach the end of the list if possible"""
        }

        # Write UI pattern fragments
        for pattern_name, content in ui_patterns.items():
            pattern_path = os.path.join(ui_patterns_dir, f"{pattern_name}.xml")

            try:
                with open(pattern_path, 'w', encoding='utf-8') as f:
                    f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<fragment name="{pattern_name}">
  <![CDATA[
{content}
  ]]>
</fragment>""")
                self.logger.info(f"Created UI pattern fragment: {pattern_name}")
            except Exception as e:
                self.logger.error(f"Error creating UI pattern fragment {pattern_name}: {e}")

    def _ensure_critical_fragments(self) -> None:
        """Ensure that all critical fragments required by core templates are available."""
        self.logger.info("Ensuring critical fragments are available")

        # Define the critical fragments and their default contents
        critical_fragments = {
            "system_intro": "You are an Android testing assistant. Your task is to help test Android applications by recommending the best actions to take based on the current screen state.",

            "system_guidelines": """GENERAL GUIDELINES:
- Focus on thorough exploration of the application
- Target actions that are most likely to trigger interesting behavior
- Pay attention to input validation and edge cases
- Attempt to reach all parts of the application""",

            "standard_instructions": """Your task is to analyze the current state of an Android application and recommend the single most effective action to take next for testing purposes.""",

            "standard_format": """RESPONSE FORMAT:
Your response must be a valid JSON object with the following structure:
{
  "action": {
    "type": "ACTION_TYPE",  // e.g., "CLICK", "SET_TEXT", "LONG_CLICK"
    "target": "element description or action_id",
    "value": "text to enter" // only for SET_TEXT actions
  },
  "explanation": "Brief explanation of why this action was chosen"
}""",

            "standard_guidelines": """IMPORTANT RULES:
1. SEQUENCE MATTERS - actions must be in a logical order (e.g., fill all form fields BEFORE submitting)
2. FORM FILLING - when you see a form, ALWAYS fill out all required fields before clicking submit/next buttons
3. NEVER include a BACK action unless absolutely necessary (only when no other actions are possible)
4. Prioritize exploring new functionality over revisiting previous screens
5. For text inputs, provide appropriate values based on the field type (emails, passwords, etc.)
6. Choose the single most effective action for thorough testing""",

            "user_base": """I'm testing an Android application and need your guidance on the next action to take.

Current Activity: {{ activity }}

Screen Elements:
{{ ui_elements }}"""
        }

        # Check each critical fragment
        for fragment_name, default_content in critical_fragments.items():
            # Check if fragment exists
            if fragment_name not in self.fragments:
                # Try with common prefixes
                prefixed_names = [f"fragments/{fragment_name}", f"ui_patterns/{fragment_name}"]
                found = False
                
                for prefixed_name in prefixed_names:
                    if prefixed_name in self.fragments:
                        # Found with prefix, register under canonical name too
                        self.fragments[fragment_name] = self.fragments[prefixed_name]
                        found = True
                        break
                
                # If still not found, inject default content
                if not found:
                    self.logger.warning(f"Critical fragment '{fragment_name}' not found - injecting default content")
                    self.fragments[fragment_name] = default_content

    def _load_fragments_from_directory(self, directory: str) -> None:
        """Load fragments from XML files in the specified directory.
        
        Args:
            directory: The directory containing fragment XML files.
        """
        self.logger.info(f"Loading fragments from directory: {directory}")

        try:
            # Load all XML fragment files
            for filename in os.listdir(directory):
                if filename.endswith(".xml"):
                    fragment_path = os.path.join(directory, filename)
                    fragment_name = filename.replace(".xml", "")

                    try:
                        # Load the XML file
                        root = load_xml_file(fragment_path)
                        if root is None:
                            self.logger.error(f"Failed to load fragment: {fragment_path}")
                            continue

                        # Check if this is a fragment (not a template)
                        if root.tag != "fragment":
                            continue

                        # Get the fragment name from the XML if available
                        xml_fragment_name = root.get("name")
                        if xml_fragment_name:
                            fragment_name = xml_fragment_name

                        # Try to extract CDATA content
                        fragment_content = ""
                        # First get the XML as string
                        with open(fragment_path, 'r', encoding='utf-8') as f:
                            xml_content = f.read()

                        # Use regex to extract CDATA content
                        cdata_pattern = r'<!\[CDATA\[(.*?)\]\]>'
                        cdata_matches = re.findall(cdata_pattern, xml_content, re.DOTALL)

                        if cdata_matches:
                            fragment_content = cdata_matches[0].strip()
                        elif root.text:
                            fragment_content = root.text.strip()

                        # Store fragment - simplified approach focused on clarity
                        if fragment_content:
                            # 1. Store with direct name
                            self.fragments[fragment_name] = fragment_content
                            
                            # 2. Store with subdirectory prefix if in a subdirectory
                            subdir_name = os.path.basename(directory)
                            if subdir_name != os.path.basename(self.fragment_dir):
                                prefixed_name = f"{subdir_name}/{fragment_name}"
                                self.fragments[prefixed_name] = fragment_content
                                self.logger.debug(f"Registered fragment with prefix: {prefixed_name}")
                            
                            self.logger.debug(f"Loaded fragment: {fragment_name}")
                        else:
                            self.logger.warning(f"No content found in fragment: {fragment_path}")
                    except Exception as e:
                        self.logger.error(f"Error loading fragment {fragment_path}: {e}")
                        self.error_handler.handle_error(
                            e,
                            context={
                                "component": "Jinja2TemplateRepository",
                                "fragment_path": fragment_path
                            }
                        )
        except Exception as e:
            self.logger.error(f"Error loading fragments from {directory}: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "Jinja2TemplateRepository",
                    "directory": directory
                }
            )

    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a template by name.
        
        Args:
            name: The name of the template. May include a category prefix
                 (e.g., "rvdroid:exploration").
            
        Returns:
            The template dictionary, or None if not found.
        """
        # First, try exact name match
        template = self.templates.get(name)

        # If not found and name has a prefix, try without prefix
        if template is None and ":" in name:
            base_name = name.split(":", 1)[1]
            template = self.templates.get(base_name)

            # If still not found, try with different category prefixes
            if template is None:
                for template_key in self.templates:
                    if template_key.endswith(f":{base_name}"):
                        template = self.templates.get(template_key)
                        break

        self.logger.debug(f"Retrieved template: {name} -> {template is not None}")

        return template

    def get_fragment(self, name: str) -> Optional[str]:
        """Get a fragment by name.
        
        Args:
            name: The name of the fragment. May include a category prefix.
            
        Returns:
            The fragment content, or None if not found.
        """
        return self.fragments.get(name)

    def get_template_object(self, name: str, role: str) -> Optional[Jinja2Template]:
        """Get a template object by name and role.
        
        Args:
            name: The name of the template. May include a category prefix.
            role: The role (system, user, assistant).
            
        Returns:
            The template object, or None if not found.
        """
        # First, try exact key match
        template_key = f"{name}.{role}"
        template_obj = self.template_objects.get(template_key)

        # If not found and name has a prefix, try without prefix
        if template_obj is None and ":" in name:
            base_name = name.split(":", 1)[1]
            base_key = f"{base_name}.{role}"
            template_obj = self.template_objects.get(base_key)

            # If still not found, try with different category prefixes
            if template_obj is None:
                for obj_key in self.template_objects:
                    if obj_key.endswith(f":{base_name}.{role}"):
                        template_obj = self.template_objects.get(obj_key)
                        break

        return template_obj

    def create_messages(
            self,
            template_name: str,
            variables: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Create a list of messages using the specified template.
        
        Args:
            template_name: The name of the template to use.
            variables: Variables to substitute in the template.
            
        Returns:
            A list of message dictionaries with role and content.
        """
        try:
            self.logger.info(f"Creating messages from template: {template_name}")

            # Get the template
            template = self.get_template(template_name)

            if not template:
                self.logger.error(f"Template not found: {template_name}")
                self.logger.info(f"Available templates: {sorted(list(self.templates.keys()))}")
                return []

            # Prepare variables
            processed_variables = self._prepare_variables(variables, template)

            messages = []

            # Create messages for each role in the template
            for role, content in template["roles"].items():
                template_obj = self.get_template_object(template_name, role)

                if template_obj:
                    try:
                        # Update template with latest fragments
                        template_obj.update_fragment_repository(self.fragments)
                        
                        # Render the template
                        self.logger.debug(f"Rendering template {template_name} for role: {role}")
                        rendered_content = template_obj.render(processed_variables, external_fragments=self.fragments)

                        # Add to messages list
                        messages.append({
                            "role": role,
                            "content": rendered_content
                        })
                    except Exception as role_error:
                        self.logger.error(f"Error rendering template {template_name}.{role}: {role_error}",
                                          exc_info=True)
                        # Try to include a simplified version as fallback
                        messages.append({
                            "role": role,
                            "content": f"Error rendering template. Raw template content: {content[:100]}..."
                        })

            # Verify messages were created
            if not messages:
                self.logger.warning(f"No messages were created from template: {template_name}")
            else:
                self.logger.info(f"Created {len(messages)} messages from template: {template_name}")

            return messages
        except Exception as e:
            self.logger.error(f"Error creating messages from template {template_name}: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "Jinja2TemplateRepository",
                    "template_name": template_name,
                    "variables": str(list(variables.keys()) if variables else "None")
                }
            )
            return []

    def _prepare_variables(self, variables: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare variables with defaults if needed.
        
        Args:
            variables: The variables provided by the caller.
            template: The template definition.
            
        Returns:
            A prepared variables dictionary with defaults for missing values.
        """
        # Start with a copy to avoid modifying the original
        processed = variables.copy() if variables else {}

        # Get required variables from template
        required_vars = template.get("required_variables", [])

        # Get template name
        template_name = template.get("metadata", {}).get("name", "unknown")

        # For additional_guidelines, create a reference to the fragment rather than embedding content
        if "additional_guidelines" not in processed:
            # Enable the additional_guidelines conditional section, but let the template 
            # access its content via fragment includes
            processed["additional_guidelines"] = True
            self.logger.debug(f"Enabled additional_guidelines section in template {template_name}")

        # For screen_description, ensure we have at least a placeholder if needed
        if "screen_description" not in processed and "ui_elements" not in processed:
            if "ui_elements" in required_vars:
                processed["ui_elements"] = "No UI elements information available."
                self.logger.debug(f"Added placeholder for required ui_elements in template {template_name}")

        return processed

    def create_llm_messages(
            self,
            template_name: str,
            variables: Dict[str, Any]
    ) -> List[LLMMessage]:
        """Create a list of LLMMessage objects using the specified template.
        
        Args:
            template_name: The name of the template to use.
            variables: Variables to substitute in the template.
            
        Returns:
            A list of LLMMessage objects.
        """
        try:
            dict_messages = self.create_messages(template_name, variables)

            if not dict_messages:
                return []

            llm_messages = []
            for msg in dict_messages:
                role_value = msg["role"]
                content_text = msg["content"]

                # Convert role string to LLMRole enum
                role = LLMRole(role_value)

                # Create LLMMessage object
                llm_message = LLMMessage(
                    role=role,
                    content=[LLMTextContent(text=content_text)]
                )
                llm_messages.append(llm_message)

            return llm_messages
        except Exception as e:
            self.logger.error(f"Error creating LLM messages from template {template_name}: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "Jinja2TemplateRepository",
                    "template_name": template_name
                }
            )
            return []