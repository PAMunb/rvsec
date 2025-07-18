"""Jinja2-based template for the prompt system.

This module defines the Jinja2Template class for processing templates
with Jinja2 templating engine, providing native template inheritance,
variable substitution, conditional sections, and fragment inclusion.
"""

import re
import time
from typing import Any, Dict, Optional, Set

import jinja2

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class Jinja2Template:
    """Jinja2-based template for generating prompt messages.

    ### Architectural Decisions:
    - Uses Jinja2's native inheritance system for template extension
    - Supports block-based content overriding for extensible templates
    - Provides comprehensive validation of required variables
    - Implements performance monitoring for template rendering
    - Uses consistent error handling with diagnostic information

    ### Key Components:
    - Native template inheritance through {% extends %} and {% block %}
    - Fragment inclusion with {% include %}
    - Performance monitoring for template rendering
    - Comprehensive validation and error reporting

    ### Integration Points:
    - Works with Jinja2TemplateRepository for template loading
    - Uses custom FragmentDictLoader for fragment access
    - Integrates with error handler for standardized error reporting
    - Receives rendered content from Jinja2's environment
    """

    def __init__(
            self,
            template_text: str,
            name: str,
            role: str,
            required_variables: Optional[Set[str]] = None,
            fragment_repository: Optional[Dict[str, str]] = None,
            jinja_env: Optional[jinja2.Environment] = None
    ):
        """Initialize a Jinja2-based template.

        Args:
            template_text: The template text with Jinja2 syntax.
            name: A unique identifier for the template.
            role: The role of this template (system, user, assistant).
            required_variables: Set of variable names that must be provided.
            fragment_repository: Dictionary of fragment name to fragment content.
            jinja_env: Optional custom Jinja2 environment to use.
        """
        self.template_text = template_text
        self.name = name
        self.role = role
        self.required_variables = required_variables or set()
        self.fragment_repository = fragment_repository or {}

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"rv_llm.llm.prompt.template.{name}.{role}",
            {CONTEXT_COMPONENT: f"Jinja2Template:{name}:{role}"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

        # Set up Jinja2 environment
        self.jinja_env = jinja_env or self._create_jinja_environment()

        # Compile the template
        try:
            # Jinja2 will handle the template inheritance automatically
            self.compiled_template = self.jinja_env.from_string(template_text)
            self.logger.debug(f"Successfully compiled template: {name}.{role}")
        except Exception as e:
            self.logger.error(f"Error compiling template: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": f"Jinja2Template:{name}",
                    "function": "__init__",
                    "template_role": role
                }
            )
            # Create a fallback template that displays the error
            error_template = f"ERROR COMPILING TEMPLATE: {str(e)}\n\nOriginal template:\n{template_text[:500]}..."
            self.compiled_template = self.jinja_env.from_string(error_template)

        # Extract all variables using Jinja2's parser
        self.all_variables = self._extract_all_variables()

    def _create_jinja_environment(self) -> jinja2.Environment:
        """Create a Jinja2 environment with custom settings.

        Returns:
            Configured Jinja2 Environment instance.
        """
        # Create a loader that can load fragments from the repository
        fragment_loader = FragmentDictLoader(self.fragment_repository)

        # Create environment with appropriate settings
        env = jinja2.Environment(
            loader=fragment_loader,
            undefined=jinja2.StrictUndefined,  # Raise errors for undefined variables
            trim_blocks=True,  # Remove first newline after a block
            lstrip_blocks=True,  # Strip tabs and spaces from the beginning of blocks
            keep_trailing_newline=True,  # Preserve trailing newlines
            extensions=['jinja2.ext.loopcontrols', 'jinja2.ext.do']  # Additional extensions
        )

        # Add custom filters
        env.filters['default_if_none'] = lambda value, default: default if value is None else value

        # Add custom tests
        env.tests['empty'] = lambda value: value is None or value == '' or value == [] or value == {}

        return env

    def _extract_all_variables(self) -> Set[str]:
        """Extract all variable names from the template using Jinja2's parser.

        Returns:
            A set of all variable names used in the template.
        """
        try:
            variables = set()

            # Parse the template to extract all variable references
            if hasattr(self.compiled_template, 'find_all'):
                # For newer Jinja2 versions that have direct access to AST
                from jinja2.nodes import Name
                for node in self.compiled_template.find_all(Name):
                    if node.ctx == 'load':
                        variables.add(node.name)
            else:
                # Fallback to regex-based extraction for older Jinja2 versions
                # Look for {{ variable }} patterns, excluding function calls and filters
                var_pattern = r'\{\{\s*([a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)*)\s*(?:\||\}\})'
                for match in re.finditer(var_pattern, self.template_text):
                    variables.add(match.group(1).split('|')[0].strip())

                # Also check for variables in {% if var %}, {% for item in items %}, etc.
                control_pattern = r'\{%\s*(?:if|elif|for).*?\b([a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)*)\b'
                for match in re.finditer(control_pattern, self.template_text):
                    variables.add(match.group(1))

            self.logger.debug(f"Extracted {len(variables)} variables from template: {sorted(list(variables))}")
            return variables
        except Exception as e:
            self.logger.error(f"Error extracting variables: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": f"Jinja2Template:{self.name}",
                    "function": "_extract_all_variables",
                    "template_role": self.role
                }
            )
            return set()

    def update_fragment_repository(self, fragment_repository: Dict[str, str]) -> None:
        """Update the fragment repository and recreate the Jinja environment.

        Args:
            fragment_repository: New dictionary of fragments.
        """
        if fragment_repository is not None:
            self.fragment_repository = fragment_repository
            # Recreate the Jinja environment with the new fragment repository
            self.jinja_env = self._create_jinja_environment()
            self.logger.debug(f"Updated fragment repository with {len(fragment_repository)} fragments")

    def render(self, data: Dict[str, Any], external_fragments: Optional[Dict[str, str]] = None) -> str:
        """Render the template with the given data using Jinja2.

        Args:
            data: A dictionary containing the values for template variables.
            external_fragments: Optional external fragment repository to use instead of
                               the internal fragment repository.

        Returns:
            The rendered template as a string.
        """
        try:
            # Log template rendering start
            start_time = self._get_timestamp()
            self.logger.debug(f"===== RENDERING TEMPLATE: {self.name}.{self.role} =====")
            self.logger.debug(f"Original template length: {len(self.template_text)} characters")
            self.logger.debug(f"Available variables: {sorted(list(data.keys()))}")

            # Update fragment repository if external one is provided
            if external_fragments is not None:
                prev_count = len(self.fragment_repository)
                self.update_fragment_repository(external_fragments)
                self.logger.debug(
                    f"Updated fragment repository: {prev_count} → {len(self.fragment_repository)} fragments")

            # Check for required variables
            missing_vars = self.required_variables - set(data.keys())
            if missing_vars:
                missing_list = ", ".join(missing_vars)
                self.logger.warning(f"Missing required variables: {missing_list}")
                # Add placeholders for missing variables to prevent errors
                for var in missing_vars:
                    data[var] = f"[MISSING_REQUIRED_VARIABLE:{var}]"

            # Add diagnostic information to data
            render_data = data.copy()
            render_data['_template_name'] = self.name
            render_data['_template_role'] = self.role

            # Render the template
            render_start = self._get_timestamp()
            result = self.compiled_template.render(**render_data)
            render_time = self._get_time_diff(render_start)

            # Log completion
            total_time = self._get_time_diff(start_time)
            self.logger.debug(
                f"===== TEMPLATE RENDERING COMPLETE =====\n"
                f"Template: {self.name}.{self.role}\n"
                f"Render time: {render_time}ms, Total time: {total_time}ms\n"
                f"Result length: {len(result)} characters"
            )

            return result
        except jinja2.exceptions.TemplateError as e:
            self.logger.error(f"Jinja2 template error: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": f"Jinja2Template:{self.name}",
                    "function": "render",
                    "template_role": self.role,
                    "variables": str(list(data.keys()) if data else "None")
                }
            )
            # Return error message in the result
            return f"TEMPLATE ERROR: {str(e)}\n\nOriginal template:\n{self.template_text[:500]}..."
        except Exception as e:
            self.logger.error(f"Unexpected error rendering template: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": f"Jinja2Template:{self.name}",
                    "function": "render",
                    "template_role": self.role
                }
            )
            # Return error message in the result
            return f"UNEXPECTED ERROR: {str(e)}\n\nOriginal template:\n{self.template_text[:500]}..."

    def _get_timestamp(self) -> float:
        """Get current timestamp for performance measurement."""
        return time.time() * 1000  # Convert to milliseconds

    def _get_time_diff(self, start_time: float) -> int:
        """Calculate time difference from start_time to now."""
        return int((time.time() * 1000) - start_time)


class FragmentDictLoader(jinja2.BaseLoader):
    """Custom Jinja2 loader that loads templates from a dictionary.

    ### Architectural Decisions:
    - Implements a dictionary-based template loader for Jinja2
    - Handles both direct and namespace-based fragment lookups
    - Provides robust missing fragment handling
    - Supports dynamic fragment repository updates

    ### Key Components:
    - Namespace resolution for fragments in different categories
    - Case-insensitive matching as fallback
    - Detailed logging for fragment loading
    - Diagnostics for missing fragments
    """

    def __init__(self, fragments_dict: Dict[str, str]):
        """Initialize the loader with a dictionary of fragments.

        Args:
            fragments_dict: Dictionary mapping fragment names to content.
        """
        self.fragments = fragments_dict
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.prompt.template.jinja_template.FragmentDictLoader",
            {CONTEXT_COMPONENT: "FragmentDictLoader"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

    def get_source(self, environment: jinja2.Environment, template: str) -> tuple:
        """Get the source of a template.

        Args:
            environment: The Jinja2 environment.
            template: The name of the template to load.

        Returns:
            Tuple of (source, filename, uptodate_func)

        Raises:
            jinja2.exceptions.TemplateNotFound: If the template is not found.
        """
        # Clean template name
        clean_template = template.strip()

        # Check direct match first (most common case)
        if clean_template in self.fragments:
            self.logger.debug(f"Found fragment '{clean_template}' with direct match")
            return self.fragments[clean_template], None, lambda: True

        # Try with common namespace prefixes if not found directly
        namespaces = ["fragments/", "ui_patterns/"]
        for prefix in namespaces:
            prefixed_name = f"{prefix}{clean_template}"
            if prefixed_name in self.fragments:
                self.logger.debug(f"Found fragment '{clean_template}' with prefix '{prefix}'")
                return self.fragments[prefixed_name], None, lambda: True

        # Try case-insensitive match as last resort
        for key in self.fragments:
            if key.lower() == clean_template.lower():
                self.logger.debug(f"Found fragment '{clean_template}' with case-insensitive match to '{key}'")
                return self.fragments[key], None, lambda: True

        # Not found after all attempts
        self.logger.warning(f"Fragment not found: '{clean_template}'")

        # Only log all available fragments if there aren't too many
        fragments_list = sorted(list(self.fragments.keys()))
        if len(fragments_list) < 50:
            self.logger.debug(f"Available fragments: {fragments_list}")
        else:
            self.logger.debug(f"Available fragments (first 20): {fragments_list[:20]}...")

        # Proper exception handling
        raise jinja2.exceptions.TemplateNotFound(clean_template)
