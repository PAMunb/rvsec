"""XML-based template repository for the prompt system.

This module defines the XMLTemplateRepository class for managing XML-based
prompt templates, including loading, retrieval, and message generation.
"""

import os
import re
from typing import Any, Dict, List, Optional, Set

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.constants import TemplateRole
from rvandroid.llm.data_structures import LLMMessage, LLMRole, LLMTextContent
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager

from .xml_template import XMLTemplate
from .xml_utils import (create_default_templates, extract_template_metadata,
                       extract_template_roles, extract_template_variables,
                       load_xml_file)


class XMLTemplateRepository:
    """Repository for managing XML-based prompt templates.
    
    Handles:
    - Loading templates from XML files
    - Creating default templates
    - Providing templates by name
    - Generating messages for LLM communication
    """
    
    def __init__(self, template_dir: Optional[str] = None, fragment_dir: Optional[str] = None):
        """Initialize the XML template repository.
        
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
            "llm.prompt.template.xml_repository",
            {CONTEXT_COMPONENT: "XMLTemplateRepository"}
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
        self.template_objects: Dict[str, XMLTemplate] = {}
        self.fragments: Dict[str, str] = {}
        
        # Load templates and fragments
        self._load_templates()
        self._load_fragments()
    
    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the repository with the given configuration.
        
        Args:
            config: The configuration to use.
        """
        self.logger.info("Configuring XMLTemplateRepository")
        
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
                    "component": "XMLTemplateRepository",
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
            # First pass: Load all template metadata and role content
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
                                "component": "XMLTemplateRepository",
                                "template_path": template_path
                            }
                        )
            
            # Second pass: Process templates in proper order - base templates first
            # Collect templates without parent first
            base_templates = [key for key, data in template_info.items() if not data["extends"]]
            
            # Process base templates first
            for template_key in base_templates:
                template_data = template_info[template_key]
                self._process_template(template_key, template_data)
            
            # Then process templates with parents
            for template_key, template_data in template_info.items():
                if template_data["extends"]:
                    self._process_template(template_key, template_data)
        except Exception as e:
            self.logger.error(f"Error loading templates from {directory}: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "XMLTemplateRepository",
                    "directory": directory
                }
            )
    
    def _process_template(self, template_key: str, template_data: Dict[str, Any]) -> None:
        """Process a template and create template objects.
        
        Args:
            template_key: The key for the template.
            template_data: The template data.
        """
        try:
            # Extract template details
            template_name = template_data["metadata"]["name"]
            roles = template_data["roles"]
            required_vars = set(template_data["required_variables"])
            parent_template = template_data["extends"]
            
            # Store template data
            self.templates[template_key] = template_data
            
            # Process roles
            for role, content in roles.items():
                object_key = f"{template_key}.{role}"
                
                # Check if content is a dict with variables for parent template
                if isinstance(content, dict) and "variable" in content:
                    self.logger.debug(f"Template {template_key} role {role} contains variables for parent template")
                    # This role defines variables for parent template, not direct content
                    # Store variables, but don't create a template object yet
                    continue
                
                # Create template object
                self.template_objects[object_key] = XMLTemplate(
                    content,
                    template_name,
                    role,
                    required_variables=required_vars,
                    fragment_repository=self.fragments
                )
            
            # If this template extends another, inherit roles that aren't defined
            if parent_template and parent_template in self.templates:
                parent_roles = self.templates[parent_template]["roles"]
                
                for role, content in parent_roles.items():
                    # For each role defined in the parent template
                    object_key = f"{template_key}.{role}"
                    parent_key = f"{parent_template}.{role}"
                    
                    if role in roles:
                        # If the child template also defines this role, check if it's variable definitions
                        if isinstance(roles[role], dict) and "variable" in roles[role]:
                            # Child template defines variables for this role that should be passed to parent template
                            variables_for_parent = {}
                            
                            # Extract variables from the role definition
                            var_entries = roles[role]["variable"]
                            for var_entry in var_entries:
                                # Check if var_entry is a dict (from the new extract_template_roles)
                                if isinstance(var_entry, dict) and "name" in var_entry and "text" in var_entry:
                                    var_name = var_entry["name"]
                                    var_content = var_entry["text"]
                                # Or if it's an XML element (old style)
                                elif hasattr(var_entry, "get") and hasattr(var_entry, "text"):
                                    var_name = var_entry.get("name")
                                    var_content = var_entry.text.strip() if var_entry.text else ""
                                else:
                                    # Skip if we can't extract name and content
                                    self.logger.warning(f"Skipping variable entry with unexpected format: {var_entry}")
                                    continue
                                
                                if var_name:
                                    variables_for_parent[var_name] = var_content
                                    self.logger.debug(f"Variable for parent: {var_name} = {var_content[:20]}...")
                            
                            # Get parent template
                            if parent_key in self.template_objects:
                                parent_template_obj = self.template_objects[parent_key]
                                parent_content = parent_template_obj.template_text
                                
                                # Create a template object with parent content and child variables
                                self.template_objects[object_key] = XMLTemplate(
                                    parent_content,
                                    template_name,
                                    role,
                                    required_variables=required_vars,
                                    fragment_repository=self.fragments
                                )
                                
                                # Store variables to be used during rendering
                                self.template_objects[object_key].variables_for_parent = variables_for_parent
                                self.logger.debug(f"Stored {len(variables_for_parent)} variables for parent template")
                    else:
                        # Role defined in parent but not in child
                        if parent_key in self.template_objects:
                            parent_content = self.template_objects[parent_key].template_text
                            
                            # Create template object with parent content
                            self.template_objects[object_key] = XMLTemplate(
                                parent_content,
                                template_name,
                                role,
                                required_variables=required_vars,
                                fragment_repository=self.fragments
                            )
            
            self.logger.debug(f"Processed template: {template_key}")
        except Exception as e:
            self.logger.error(f"Error processing template {template_key}: {e}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "XMLTemplateRepository",
                    "template_key": template_key
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
    
    def _load_fragments(self) -> None:
        """Load fragments from XML files in the fragment directory and its subdirectories.
        
        This method scans all XML files in the fragments directory and its subdirectories,
        loading fragments with comprehensive logging and error handling to aid debugging.
        """
        self.logger.info(f"Loading fragments from {self.fragment_dir}")
        
        try:
            # Check if the fragment directory exists
            if not os.path.exists(self.fragment_dir):
                self.logger.warning(f"Fragment directory does not exist: {self.fragment_dir}")
                self.logger.warning("Creating fragments directory...")
                os.makedirs(self.fragment_dir, exist_ok=True)
                
                # Create some default fragments for basic templates
                self._create_default_fragments()
                
            # Load all fragment directories with logging
            self.logger.info("Scanning fragment directories...")
            
            # Track directories for debugging
            found_dirs = []
            
            # Process the main fragment directory first
            if os.path.exists(self.fragment_dir):
                found_dirs.append(self.fragment_dir)
                self.logger.info(f"Processing main fragment directory: {self.fragment_dir}")
                self._load_fragments_from_directory(self.fragment_dir)
                
                # Then process subdirectories
                for subdir_name in os.listdir(self.fragment_dir):
                    subdir_path = os.path.join(self.fragment_dir, subdir_name)
                    if os.path.isdir(subdir_path):
                        found_dirs.append(subdir_path)
                        self.logger.info(f"Processing fragment subdirectory: {subdir_path}")
                        self._load_fragments_from_directory(subdir_path)
            
            # Log summary of loaded fragments
            self.logger.info(f"Loaded {len(self.fragments)} fragments from {len(found_dirs)} directories")
            self.logger.info(f"Fragment directories processed: {found_dirs}")
            
            # Debug: Log all loaded fragment names and their content lengths
            for fragment_name in sorted(self.fragments.keys()):
                content_length = len(self.fragments[fragment_name]) if self.fragments[fragment_name] else 0
                self.logger.debug(f"Loaded fragment: {fragment_name} (content length: {content_length} chars)")
            
            # Validate critical fragments
            self._validate_critical_fragments()
            
        except Exception as e:
            self.logger.error(f"Error loading fragments: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "XMLTemplateRepository",
                    "fragment_dir": self.fragment_dir
                }
            )
    
    def _create_default_fragments(self) -> None:
        """Create default fragments for essential functionality.
        
        This method is called when the fragment directory doesn't exist or is empty,
        ensuring that basic fragments are available for core templates.
        """
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

Current Activity: {activity}

Screen Elements:
{ui_elements}"""
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
    
    def _validate_critical_fragments(self) -> None:
        """Validate that all critical fragments required by core templates are available.
        
        Logs warnings for any missing critical fragments that might cause template rendering issues.
        """
        # List of fragments that are considered critical for core functionality
        critical_fragments = [
            "system_intro",
            "system_guidelines",
            "standard_instructions",
            "standard_format",
            "standard_guidelines",
            "user_base"
        ]
        
        missing_fragments = []
        
        for fragment_name in critical_fragments:
            # Try multiple ways of accessing the fragment
            found = False
            
            # Try direct name
            if fragment_name in self.fragments:
                found = True
            else:
                # Try with variations
                possible_variations = [
                    fragment_name, 
                    f"fragments/{fragment_name}", 
                    fragment_name.split('/')[-1]
                ]
                
                for variation in possible_variations:
                    if variation in self.fragments:
                        found = True
                        break
            
            if not found:
                missing_fragments.append(fragment_name)
        
        if missing_fragments:
            self.logger.warning(f"Missing critical fragments: {missing_fragments}")
            self.logger.warning("These fragments are required for core templates to render correctly.")
        else:
            self.logger.info("All critical fragments are available.")
    
    def _ensure_critical_fragments(self) -> None:
        """Ensure that all critical fragments required by core templates are available.
        
        This method validates and if needed, manually injects critical fragments directly
        into the fragment repository to ensure templates render correctly, even if the
        actual fragment files are missing or not loaded correctly.
        """
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

Current Activity: {activity}

Screen Elements:
{ui_elements}"""
        }
        
        # Check each critical fragment
        for fragment_name, default_content in critical_fragments.items():
            # Check if fragment exists (direct or with variations)
            found = False
            
            # Direct check
            if fragment_name in self.fragments:
                found = True
                content = self.fragments[fragment_name]
                content_len = len(content) if content else 0
                self.logger.debug(f"Critical fragment '{fragment_name}' already exists ({content_len} chars)")
            else:
                # Try variations
                possible_variations = [
                    fragment_name, 
                    f"fragments/{fragment_name}", 
                    fragment_name.split('/')[-1]
                ]
                
                for variation in possible_variations:
                    if variation in self.fragments:
                        found = True
                        # Ensure the fragment is also registered under its canonical name
                        content = self.fragments[variation]
                        self.fragments[fragment_name] = content
                        self.logger.info(f"Mapped critical fragment from '{variation}' to canonical name '{fragment_name}'")
                        break
            
            # If still not found, inject the default
            if not found:
                self.logger.warning(f"Critical fragment '{fragment_name}' not found - injecting default content")
                self.fragments[fragment_name] = default_content
        
        # Validate again to ensure success
        missing_after_fix = []
        for fragment_name in critical_fragments.keys():
            if fragment_name not in self.fragments:
                missing_after_fix.append(fragment_name)
        
        if missing_after_fix:
            self.logger.error(f"Failed to ensure critical fragments: {missing_after_fix}")
        else:
            self.logger.info("All critical fragments are now available")
    
    def _load_fragments_from_directory(self, directory: str) -> None:
        """Load fragments from XML files in the specified directory.
        
        This method scans all XML files in the directory, loading any that contain
        fragment definitions and registering them in the repository under multiple
        lookup keys to maximize findability.
        
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
                            fragment_content = cdata_matches[0]
                        elif root.text:
                            fragment_content = root.text
                        
                        # Store the fragment in multiple ways to support various reference formats
                        if fragment_content:
                            # Get path information for naming
                            rel_path = os.path.relpath(directory, self.fragment_dir)
                            subdir_name = os.path.basename(directory)
                            base_filename = os.path.basename(fragment_path).replace(".xml", "")
                            
                            # Clean names to better handle spaces
                            fragment_name_clean = fragment_name.strip()
                            base_filename_clean = base_filename.strip()
                            
                            # Normalize whitespace for additional keys
                            fragment_name_norm = re.sub(r'\s+', '_', fragment_name_clean)
                            base_filename_norm = re.sub(r'\s+', '_', base_filename_clean)
                            
                            # Track all keys we register for this fragment
                            fragment_keys = []
                            
                            # 1. Basic registration: register under all basic name variants
                            # These are the most common ways fragments are looked up
                            basic_keys = [
                                # Basic name variations - standard and clean variants
                                fragment_name_clean,                       # Original name from file or XML (cleaned)
                                fragment_name_norm,                        # Original name with normalized whitespace
                                base_filename_clean,                       # Filename without path and extension (cleaned)
                                base_filename_norm,                        # Filename with normalized whitespace
                                
                                # Path-based references (with subdirectory)
                                f"{subdir_name}/{fragment_name_clean}",    # subdir/name format
                                f"{subdir_name}/{base_filename_clean}",    # subdir/filename format
                                f"{subdir_name}/{fragment_name_norm}",     # subdir/name_norm format
                                f"{subdir_name}/{base_filename_norm}",     # subdir/filename_norm format
                            ]
                            
                            # Special case: if XML name is different from filename
                            if xml_fragment_name and xml_fragment_name != base_filename_clean:
                                xml_name_clean = xml_fragment_name.strip()
                                xml_name_norm = re.sub(r'\s+', '_', xml_name_clean)
                                
                                basic_keys.append(xml_name_clean)                      # XML name attribute (cleaned)
                                basic_keys.append(xml_name_norm)                       # XML name with normalized whitespace
                                basic_keys.append(f"{subdir_name}/{xml_name_clean}")  # subdir/xml_name format
                                basic_keys.append(f"{subdir_name}/{xml_name_norm}")   # subdir/xml_name_norm format
                            
                            # Also add all lowercase variants for case-insensitive matching
                            lowercase_keys = [key.lower() for key in basic_keys.copy()]
                            basic_keys.extend(lowercase_keys)
                            
                            # 2. Advanced path variations
                            # Handle paths that might be used in different reference styles
                            advanced_keys = []
                            
                            # Absolute and relative paths from fragment directory
                            if rel_path != "." and rel_path != subdir_name:
                                advanced_keys.append(f"{rel_path}/{fragment_name_clean}")
                                advanced_keys.append(f"{rel_path}/{base_filename_clean}")
                                advanced_keys.append(f"{rel_path}/{fragment_name_norm}")
                                advanced_keys.append(f"{rel_path}/{base_filename_norm}")
                            
                            # 3. Prefix/suffix analysis for common patterns
                            # Register fragments with common prefixes/suffixes with and without those prefixes
                            common_prefixes = ["standard_", "system_", "batch_", "user_", "ui_patterns_"]
                            common_suffixes = ["_format", "_instructions", "_guidelines", "_base", "_fragment", "_template"]
                            
                            pattern_keys = []
                            
                            # Also register key variants where underscores are replaced with spaces
                            for prefix in common_prefixes:
                                prefix_space = prefix.replace('_', ' ').strip()
                                if fragment_name_clean.startswith(prefix) or fragment_name_clean.startswith(prefix_space):
                                    use_prefix = prefix if fragment_name_clean.startswith(prefix) else prefix_space
                                    base_name = fragment_name_clean[len(use_prefix):].strip()
                                    pattern_keys.append(base_name)  # Register without prefix
                                    pattern_keys.append(re.sub(r'\s+', '_', base_name))  # Normalized variant
                                
                                # Also check for prefix in the normalized version
                                if fragment_name_norm.startswith(prefix):
                                    base_name = fragment_name_norm[len(prefix):]
                                    pattern_keys.append(base_name)  # Register without prefix
                            
                            # Check for common suffixes
                            for suffix in common_suffixes:
                                suffix_space = suffix.replace('_', ' ').strip()
                                if fragment_name_clean.endswith(suffix) or fragment_name_clean.endswith(suffix_space):
                                    use_suffix = suffix if fragment_name_clean.endswith(suffix) else suffix_space
                                    base_name = fragment_name_clean[:-len(use_suffix)].strip()
                                    pattern_keys.append(base_name)  # Register without suffix
                                    pattern_keys.append(re.sub(r'\s+', '_', base_name))  # Normalized variant
                                    
                                    # Also register with path style (e.g., 'standard/guidelines' for 'standard_guidelines')
                                    if '_' in base_name:
                                        parts = base_name.split('_', 1)
                                        if len(parts) == 2 and parts[0] and parts[1]:
                                            pattern_keys.append(f"{parts[0]}/{parts[1]}")
                                
                                # Also check for suffix in normalized version
                                if fragment_name_norm.endswith(suffix):
                                    base_name = fragment_name_norm[:-len(suffix)]
                                    pattern_keys.append(base_name)  # Register without suffix
                            
                            # Special cases for UI patterns - always register both with and without folder prefix
                            if subdir_name == "ui_patterns":
                                pattern_keys.append(fragment_name_clean)  # Without path
                                pattern_keys.append(fragment_name_norm)   # Without path, normalized
                                pattern_keys.append(f"ui_patterns/{fragment_name_clean}")  # With path
                                pattern_keys.append(f"ui_patterns/{fragment_name_norm}")   # With path, normalized
                                # Also register with underscore format
                                pattern_keys.append(f"ui_patterns_{fragment_name_clean}")  # With underscore
                                pattern_keys.append(f"ui_patterns_{fragment_name_norm}")   # With underscore, normalized
                            
                            # 4. Special cases for common fragment naming patterns
                            if fragment_name_clean in ["instructions", "guidelines", "format", "summary"]:
                                # These common fragment names might be referenced with prefixes
                                category_prefixes = ["standard_", "batch_", "system_", "user_"]
                                for prefix in category_prefixes:
                                    pattern_keys.append(f"{prefix}{fragment_name_clean}")
                            
                            # Combine all key variations and remove duplicates
                            all_keys = basic_keys + advanced_keys + pattern_keys
                            unique_keys = set()
                            
                            # Deduplicate while preserving case variants (useful for better debug logging)
                            for key in all_keys:
                                key_lower = key.lower()
                                if key_lower not in [k.lower() for k in unique_keys]:
                                    unique_keys.add(key)
                            
                            # Register fragment under all generated keys
                            for key in unique_keys:
                                self.fragments[key] = fragment_content
                                fragment_keys.append(key)
                                
                                # Only log specific keys to avoid excessive logging
                                if len(fragment_keys) <= 10 or key == fragment_name_clean:
                                    self.logger.debug(f"Registered fragment '{fragment_name_clean}' with key: {key}")
                            
                            # Provide a detailed summary for debugging
                            self.logger.info(
                                f"Fragment '{fragment_name_clean}' registered with {len(fragment_keys)} access keys"
                            )
                            if len(fragment_keys) <= 20:
                                self.logger.debug(f"Keys for '{fragment_name_clean}': {sorted(fragment_keys)}")
                            else:
                                self.logger.debug(f"First 20 keys for '{fragment_name_clean}': {sorted(fragment_keys)[:20]}...")
                        else:
                            self.logger.warning(f"No content found in fragment: {fragment_path}")
                    except Exception as e:
                        self.logger.error(f"Error loading fragment {fragment_path}: {e}")
                        self.error_handler.handle_error(
                            e,
                            context={
                                "component": "XMLTemplateRepository",
                                "fragment_path": fragment_path
                            }
                        )
        except Exception as e:
            self.logger.error(f"Error loading fragments from {directory}: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "XMLTemplateRepository",
                    "directory": directory
                }
            )
    
    def get_fragment(self, name: str) -> Optional[str]:
        """Get a fragment by name.
        
        Args:
            name: The name of the fragment. May include a category prefix.
            
        Returns:
            The fragment content, or None if not found.
        """
        return self.fragments.get(name)
    
    def get_template_object(self, name: str, role: str) -> Optional[XMLTemplate]:
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
        
        This method prepares the template, adds necessary variables if missing, 
        ensures proper fragment registration, and renders the template
        into a list of messages. It focuses on using fragment includes rather than
        hardcoding content.
        
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
            
            # Log loaded fragments before rendering
            fragment_count = len(self.fragments)
            self.logger.debug(f"Fragment repository has {fragment_count} fragments registered")
            
            # Add all known equivalent fragment names - a more aggressive approach to ensure
            # that all possible variations of the fragment names are available
            fragments_to_ensure = [
                # Basic fragments
                "user_base", "system_intro", "system_guidelines", "standard_guidelines", 
                "standard_format", "standard_instructions",
                # Batch-specific fragments
                "batch_instructions", "batch_format", "batch_guidelines",
                "batch_ui_pattern_detection", "batch_critical_task"
            ]
            
            # Fix all missing fragments - ensure they're available under all common variations
            for fragment_name in fragments_to_ensure:
                # First check if it exists directly
                if fragment_name in self.fragments:
                    content_len = len(self.fragments[fragment_name])
                    self.logger.debug(f"Fragment '{fragment_name}' is available ({content_len} chars)")
                    # We found it directly, now register all variations
                    fragment_content = self.fragments[fragment_name]
                    
                    # Register common variations explicitly
                    variations = []
                    base_name = fragment_name.split('/')[-1] if '/' in fragment_name else fragment_name
                    
                    # Add common variations
                    variations.extend([
                        base_name,                   # Base name without path
                        f"fragments/{base_name}",    # With fragments/ prefix
                        f"{base_name}_fragment",     # With _fragment suffix
                    ])
                    
                    # Special case for user_base
                    if base_name == "user_base":
                        variations.extend(["user", "base", "user/base"])
                    
                    # Register all variations
                    for variation in variations:
                        if variation != fragment_name and variation not in self.fragments:
                            self.fragments[variation] = fragment_content
                            self.logger.debug(f"Registered alias '{variation}' → '{fragment_name}'")
                else:
                    # Try to find it through other entries
                    self.logger.warning(f"Critical fragment '{fragment_name}' not found directly")
                    alternatives = []
                    for key in self.fragments.keys():
                        # Try multiple matching techniques
                        if (fragment_name in key or 
                            fragment_name.replace('_', '/') in key or
                            key.endswith(fragment_name) or
                            fragment_name.lower() == key.lower()):
                            alternatives.append(key)
                    
                    if alternatives:
                        self.logger.debug(f"Found {len(alternatives)} alternatives for '{fragment_name}': {alternatives[:3]}")
                        # Choose first alternative and register under the canonical name
                        chosen_alt = alternatives[0]
                        self.fragments[fragment_name] = self.fragments[chosen_alt]
                        self.logger.info(f"Auto-registered '{fragment_name}' using '{chosen_alt}'")
            
            # Prepare variables with defaults if needed
            processed_variables = self._prepare_variables(variables, template)
            
            messages = []
            
            # Create messages for each role in the template
            for role, content in template["roles"].items():
                template_obj = self.get_template_object(template_name, role)
                
                if template_obj:
                    try:
                        # Update the template's fragment repository directly with our latest fragments
                        # This is a more aggressive approach, but ensures fragments are found
                        template_obj.fragment_repository = self.fragments.copy()
                        self.logger.debug(f"Updated template {template_name}.{role} with complete fragment repository")
                        
                        # Preprocess the template text to handle includes
                        original_template_text = template_obj.template_text
                        
                        # Check if the template text contains include directives that need preprocessing
                        if "{#include" in original_template_text:
                            self.logger.debug(f"Template {template_name}.{role} contains direct include directives")
                            
                            # Preprocess includes in the template text using the current fragment repository
                            preprocessed_text = template_obj._process_includes(original_template_text)
                            
                            if preprocessed_text != original_template_text:
                                self.logger.debug(f"Preprocessed template includes for {template_name}.{role}")
                                # Update the template text with processed includes
                                template_obj.template_text = preprocessed_text
                        
                        # Process parent template variables
                        if hasattr(template_obj, 'variables_for_parent') and template_obj.variables_for_parent:
                            # Process variables_for_parent to expand any fragment includes
                            parent_vars = {}
                            for var_name, var_value in template_obj.variables_for_parent.items():
                                if "{#include" in var_value:
                                    # Process includes in variable values
                                    expanded_value = template_obj._process_includes(var_value)
                                    parent_vars[var_name] = expanded_value
                                    self.logger.debug(f"Expanded fragment includes in variable '{var_name}'")
                                else:
                                    parent_vars[var_name] = var_value
                            
                            # Add parent variables to processed_variables
                            self.logger.debug(f"Adding {len(parent_vars)} parent variables to template variables")
                            processed_variables.update(parent_vars)
                        
                        # Render the template - we already updated its fragment repository
                        # but pass external_fragments as well for maximum compatibility
                        self.logger.debug(f"Rendering template {template_name} for role: {role}")
                        rendered_content = template_obj.render(processed_variables, external_fragments=self.fragments)
                        
                        # Restore original template text to avoid side effects
                        if "{#include" in original_template_text:
                            template_obj.template_text = original_template_text
                        
                        # Check for unresolved includes
                        if "FRAGMENT_NOT_FOUND" in rendered_content:
                            self.logger.warning(f"Template {template_name}.{role} has unresolved fragment includes")
                            # Extract names of unresolved fragments 
                            unresolved = re.findall(r'FRAGMENT_NOT_FOUND:([^}]+)', rendered_content)
                            self.logger.warning(f"Unresolved fragments: {unresolved}")
                            
                            # Try one last desperate measure for each unresolved fragment
                            if unresolved:
                                for unresolved_name in unresolved:
                                    clean_name = unresolved_name.strip()
                                    # Try one more time with a more aggressive search
                                    for key, content in self.fragments.items():
                                        # Look for any key that contains this fragment name
                                        if clean_name.lower() in key.lower():
                                            # Register it directly with the expected name
                                            self.fragments[clean_name] = content
                                            self.logger.debug(f"Last-chance registration: '{clean_name}' using '{key}'")
                                            # Update the template's fragments too
                                            template_obj.fragment_repository[clean_name] = content
                                            break
                                
                                # Try rendering again with the newly registered fragments
                                self.logger.debug(f"Attempting second render for {template_name}.{role}")
                                rendered_content = template_obj.render(processed_variables, external_fragments=self.fragments)
                        
                        # Log content length for debugging
                        content_length = len(rendered_content) if rendered_content else 0
                        self.logger.debug(f"Rendered content length: {content_length} chars")
                        
                        # Add to messages list
                        messages.append({
                            "role": role,
                            "content": rendered_content
                        })
                    except Exception as role_error:
                        self.logger.error(f"Error rendering template {template_name}.{role}: {role_error}", exc_info=True)
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
                # Debug: check if the actual content has guidelines
                has_guidelines = any("IMPORTANT RULES" in msg.get("content", "") for msg in messages)
                self.logger.debug(f"Messages contain guidelines section: {has_guidelines}")
            
            return messages
        except Exception as e:
            self.logger.error(f"Error creating messages from template {template_name}: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "XMLTemplateRepository",
                    "template_name": template_name,
                    "variables": str(list(variables.keys()) if variables else "None")
                }
            )
            return []
    
    def _prepare_variables(self, variables: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare variables with defaults if needed.
        
        This method keeps the original variables but adds missing required variables
        with sensible defaults where possible, all without embedding content directly.
        
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
        
        # Handle specific known template variables that might be referenced by fragments
        # Note: We're not embedding content, just ensuring variables exist to help fragment lookups
        
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
    
    def create_mcp_messages(
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
            
            mcp_messages = []
            for msg in dict_messages:
                role_value = msg["role"]
                content_text = msg["content"]
                
                # Convert role string to LLMRole enum
                role = LLMRole(role_value)
                
                # Create LLMMessage object
                mcp_message = LLMMessage(
                    role=role,
                    content=[LLMTextContent(text=content_text)]
                )
                mcp_messages.append(mcp_message)
            
            return mcp_messages
        except Exception as e:
            self.logger.error(f"Error creating MCP messages from template {template_name}: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "XMLTemplateRepository",
                    "template_name": template_name
                }
            )
            return []