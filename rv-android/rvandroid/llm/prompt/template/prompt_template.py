"""Prompt template module for the prompt system.

This module defines the PromptTemplate class, which is responsible for
rendering templates with variable substitution, conditional sections, and more.
"""

import re
from typing import Any, Callable, Dict, List, Optional, Set, Union

from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager

# TODO deprecated
class PromptTemplate:
    """Template for generating prompt messages with variable substitution.
    
    The PromptTemplate class provides a flexible way to define templates with
    variable substitution, conditional sections, and transformations.
    """
    
    # Regex patterns for parsing template syntax
    VARIABLE_PATTERN = r"\{([a-zA-Z0-9_\.]+)(?:\|([a-zA-Z0-9_]+))?\}"
    CONDITIONAL_START_PATTERN = r"\{#if ([a-zA-Z0-9_\.]+)\}"
    CONDITIONAL_END_PATTERN = r"\{#endif\}"
    ITERATION_START_PATTERN = r"\{#for ([a-zA-Z0-9_\.]+) as ([a-zA-Z0-9_]+)\}"
    ITERATION_END_PATTERN = r"\{#endfor\}"
    
    def __init__(
        self, 
        template_text: str,
        name: str,
        required_variables: Optional[List[str]] = None,
        transformers: Optional[Dict[str, Callable[[Any], str]]] = None
    ):
        """Initialize a prompt template.
        
        Args:
            template_text: The template text with variable placeholders.
            name: A name for the template.
            required_variables: A list of variable names that must be provided.
            transformers: A dictionary mapping transformer names to functions.
        """
        self.template_text = template_text
        self.name = name
        self.required_variables = set(required_variables or [])
        self.transformers = transformers or {}
        
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"llm.prompt.template.{name}",
            {CONTEXT_COMPONENT: f"PromptTemplate:{name}"}
        )
        
        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()
        
        # Parse the template to extract all variables
        self.all_variables = self._extract_all_variables()
    
    def _extract_all_variables(self) -> Set[str]:
        """Extract all variable names from the template.
        
        Returns:
            A set of all variable names used in the template.
        """
        variables = set()
        
        # Extract variables from placeholders
        for match in re.finditer(self.VARIABLE_PATTERN, self.template_text):
            variables.add(match.group(1))
        
        # Extract variables from conditional sections
        for match in re.finditer(self.CONDITIONAL_START_PATTERN, self.template_text):
            variables.add(match.group(1))
        
        # Extract variables from iteration sections
        for match in re.finditer(self.ITERATION_START_PATTERN, self.template_text):
            variables.add(match.group(1))
        
        return variables
    
    def _get_nested_value(self, data: Dict[str, Any], key_path: str) -> Any:
        """Get a value from nested dictionaries using dot notation.
        
        Args:
            data: The data dictionary.
            key_path: The key path in dot notation (e.g., "user.name").
            
        Returns:
            The value at the specified path, or None if not found.
        """
        if "." not in key_path:
            return data.get(key_path)
        
        parts = key_path.split(".")
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _apply_transformer(self, value: Any, transformer_name: str) -> str:
        """Apply a transformer to a value.
        
        Args:
            value: The value to transform.
            transformer_name: The name of the transformer to apply.
            
        Returns:
            The transformed value as a string.
        """
        transformer = self.transformers.get(transformer_name)
        
        if transformer is None:
            self.logger.warning(f"Transformer not found: {transformer_name}")
            return str(value) if value is not None else ""
        
        try:
            return transformer(value)
        except Exception as e:
            self.logger.error(f"Error applying transformer {transformer_name}: {e}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": f"PromptTemplate:{self.name}",
                    "transformer": transformer_name
                }
            )
            return str(value) if value is not None else ""
    
    def _render_variable(self, match: re.Match, data: Dict[str, Any]) -> str:
        """Render a variable placeholder.
        
        Args:
            match: The regex match object.
            data: The data dictionary.
            
        Returns:
            The rendered variable as a string.
        """
        variable_name = match.group(1)
        transformer_name = match.group(2) if len(match.groups()) > 1 else None
        
        value = self._get_nested_value(data, variable_name)
        
        if value is None:
            if variable_name in self.required_variables:
                self.logger.warning(f"Required variable not provided: {variable_name}")
            return ""
        
        if transformer_name:
            return self._apply_transformer(value, transformer_name)
        
        return str(value)
    
    def _process_conditional_section(
        self, 
        template: str, 
        data: Dict[str, Any]
    ) -> str:
        """Process conditional sections in the template.
        
        Args:
            template: The template text.
            data: The data dictionary.
            
        Returns:
            The processed template with conditional sections evaluated.
        """
        # Find all conditional sections
        pattern = f"{self.CONDITIONAL_START_PATTERN}(.*?){self.CONDITIONAL_END_PATTERN}"
        regex = re.compile(pattern, re.DOTALL)
        
        # Process each conditional section
        while True:
            match = regex.search(template)
            if not match:
                break
            
            condition_var = match.group(1)
            condition_content = match.group(2)
            
            # Evaluate the condition
            condition_value = self._get_nested_value(data, condition_var)
            
            # Replace the section with content or empty string
            if condition_value:
                template = template.replace(match.group(0), condition_content)
            else:
                template = template.replace(match.group(0), "")
        
        return template
    
    def _process_iteration_section(
        self, 
        template: str, 
        data: Dict[str, Any]
    ) -> str:
        """Process iteration sections in the template.
        
        Args:
            template: The template text.
            data: The data dictionary.
            
        Returns:
            The processed template with iteration sections expanded.
        """
        # Find all iteration sections
        pattern = f"{self.ITERATION_START_PATTERN}(.*?){self.ITERATION_END_PATTERN}"
        regex = re.compile(pattern, re.DOTALL)
        
        # Process each iteration section
        while True:
            match = regex.search(template)
            if not match:
                break
            
            collection_var = match.group(1)
            item_var = match.group(2)
            iteration_content = match.group(3)
            
            # Get the collection
            collection = self._get_nested_value(data, collection_var)
            
            if not collection or not isinstance(collection, (list, tuple, dict)):
                template = template.replace(match.group(0), "")
                continue
            
            # Generate the expanded content
            expanded_content = []
            
            if isinstance(collection, dict):
                items = collection.items()
            else:
                items = enumerate(collection)
            
            for key, item in items:
                # Create a copy of the data with the item variable
                item_data = data.copy()
                item_data[item_var] = item
                
                # Use item's index/key in case it's needed
                item_data[f"{item_var}_key"] = key
                
                # Render the iteration content with the item data
                rendered_content = self._substitute_variables(iteration_content, item_data)
                expanded_content.append(rendered_content)
            
            # Replace the section with the expanded content
            template = template.replace(match.group(0), "\n".join(expanded_content))
        
        return template
    
    def _substitute_variables(
        self, 
        template: str, 
        data: Dict[str, Any]
    ) -> str:
        """Substitute variables in the template.
        
        Args:
            template: The template text.
            data: The data dictionary.
            
        Returns:
            The template with variables substituted.
        """
        return re.sub(self.VARIABLE_PATTERN, lambda m: self._render_variable(m, data), template)
    
    def render(self, data: Dict[str, Any]) -> str:
        """Render the template with the given data.
        
        Args:
            data: A dictionary containing the values for template variables.
            
        Returns:
            The rendered template as a string.
        """
        try:
            # Check for required variables
            missing_vars = self.required_variables - set(data.keys())
            if missing_vars:
                missing_list = ", ".join(missing_vars)
                self.logger.warning(f"Missing required variables: {missing_list}")
            
            # Start with the original template
            result = self.template_text
            
            # Process conditional sections
            result = self._process_conditional_section(result, data)
            
            # Process iteration sections
            result = self._process_iteration_section(result, data)
            
            # Substitute variables
            result = self._substitute_variables(result, data)
            
            return result
        except Exception as e:
            self.logger.error(f"Error rendering template: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": f"PromptTemplate:{self.name}"
                }
            )
            return self.template_text  # Return the original template as fallback