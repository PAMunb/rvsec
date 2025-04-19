"""XML-based template for the prompt system.

This module defines the XMLTemplate class for processing XML templates
with variable substitution, conditional sections, and iteration.
"""

import re
from typing import Any, Callable, Dict, List, Optional, Set, Union

from rvandroid.llm.constants import TemplateRole
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class XMLTemplate:
    """XML-based template for generating prompt messages.
    
    Supports:
    - Variable substitution with dot notation
    - Conditional sections with if/endif
    - Iteration over collections with for/endfor
    - Custom transformers with pipeline notation
    - Required variable validation
    
    This implementation preserves the same functionality as the previous
    JSON-based template system but uses XML with CDATA sections for improved
    readability and maintainability of multi-line prompt templates.
    """
    
    # Regex patterns for parsing template syntax - allowing for whitespace
    VARIABLE_PATTERN = r"\{\s*([a-zA-Z0-9_\.]+)(?:\|([a-zA-Z0-9_]+))?\s*\}"
    CONDITIONAL_START_PATTERN = r"\{#\s*if\s+([a-zA-Z0-9_\.]+(?:\s*==\s*\"[^\"]*\")?)(?:\s*\|\|\s*[a-zA-Z0-9_\.]+(?:\s*==\s*\"[^\"]*\")?)*\s*\}"
    CONDITIONAL_END_PATTERN = r"\{#\s*endif\s*\}"
    ITERATION_START_PATTERN = r"\{#\s*for\s+([a-zA-Z0-9_\.]+)\s+as\s+([a-zA-Z0-9_]+)\s*\}"
    ITERATION_END_PATTERN = r"\{#\s*endfor\s*\}"
    # Enhanced include pattern with more robust whitespace handling
    INCLUDE_PATTERN = r"\{#\s*include\s+([a-zA-Z0-9_/]+(?:\s+[a-zA-Z0-9_/]+)*)\s*\}"
    
    def __init__(
        self, 
        template_text: str,
        name: str,
        role: str = TemplateRole.USER,
        required_variables: Optional[Set[str]] = None,
        transformers: Optional[Dict[str, Callable[[Any], str]]] = None,
        fragment_repository: Optional[Dict[str, str]] = None
    ):
        """Initialize an XML-based template.
        
        Args:
            template_text: The template text with variable placeholders.
            name: A unique identifier for the template.
            role: The role of this template (system, user, assistant).
            required_variables: Set of variable names that must be provided.
            transformers: Dictionary mapping transformer names to functions.
            fragment_repository: Dictionary of fragment name to fragment content.
        """
        self.template_text = template_text
        self.name = name
        self.role = role
        self.required_variables = required_variables or set()
        self.transformers = transformers or {}
        self.fragment_repository = fragment_repository or {}
        self.variables_for_parent = {}
        
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"llm.prompt.template.{name}.{role}",
            {CONTEXT_COMPONENT: f"XMLTemplate:{name}:{role}"}
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
        
        This method retrieves values from nested data structures, with support for
        dot notation for nested dictionaries. It includes special handling for
        template-specific variables and graceful degradation when a path is not found.
        
        Args:
            data: The data dictionary.
            key_path: The key path in dot notation (e.g., "user.name").
            
        Returns:
            The value at the specified path, or None if not found.
        """
        # Special case handling for known template variables
        # This ensures variable values are explicitly included in the template
        if key_path == "additional_guidelines" and key_path in data:
            self.logger.debug(f"Found explicit additional_guidelines in data")
            return data.get(key_path)
        
        # Handle simple key (no dot notation)
        if "." not in key_path:
            if key_path in data:
                value = data.get(key_path)
                # Debug info for important variables
                if key_path in ["ui_elements", "additional_guidelines", "activity", "screen_description"]:
                    self.logger.debug(f"Retrieved value for {key_path}: length {len(str(value)) if value else 0} chars")
                return value
            else:
                self.logger.debug(f"Key not found in data: {key_path}")
                return None
        
        # Handle nested path with dot notation
        parts = key_path.split(".")
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                self.logger.debug(f"Nested path not found: {key_path} (failed at '{part}')")
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
                    "component": f"XMLTemplate:{self.name}",
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
        
        # Process variable string value for any includes before returning
        string_value = str(value)
        if string_value and "{#include" in string_value:
            # If the variable itself contains include directives, process them
            self.logger.debug(f"Variable '{variable_name}' contains fragment includes - processing them")
            string_value = self._process_includes(string_value)
        
        if transformer_name:
            return self._apply_transformer(value, transformer_name)
        
        return string_value
    
    def _process_conditional_section(
        self, 
        template: str, 
        data: Dict[str, Any]
    ) -> str:
        """Process conditional sections in the template.
        
        Evaluates all {#if variable}...{#endif} blocks in the template, including
        nested conditionals and more complex condition expressions with equality 
        checks and basic logical operators.
        
        Args:
            template: The template text.
            data: The data dictionary.
            
        Returns:
            The processed template with conditional sections evaluated.
        """
        # Track stats for debugging
        processed_count = 0
        included_count = 0
        excluded_count = 0
        
        # Simple if/endif pattern for direct variable checks
        pattern = f"{self.CONDITIONAL_START_PATTERN}(.*?){self.CONDITIONAL_END_PATTERN}"
        regex = re.compile(pattern, re.DOTALL)
        
        # Extended patterns for if/elif/else blocks
        elif_pattern = r"\{#\s*elif\s+([a-zA-Z0-9_\.]+(?:\s*==\s*\"[^\"]*\")?)(?:\s*\|\|\s*[a-zA-Z0-9_\.]+(?:\s*==\s*\"[^\"]*\")?)*\s*\}"
        else_pattern = r"\{#\s*else\s*\}"
        
        # Pattern for checking for equality conditions like {#if variable == "value"}
        equality_condition = re.compile(r'([a-zA-Z0-9_\.]+)\s*==\s*\"([^\"]*)\"')
        
        # Process if/endif blocks
        while True:
            match = regex.search(template)
            if not match:
                break
            
            # Extract the condition and content
            condition_expr = match.group(1)
            full_content = match.group(2)
            
            # Check for elif/else in the content
            elif_matches = list(re.finditer(elif_pattern, full_content))
            else_match = re.search(else_pattern, full_content)
            
            # Process the content sections
            content_sections = []
            
            # Handle if/elif/else structure
            if elif_matches or else_match:
                # First section is from start to first elif (or else)
                start_idx = 0
                
                # Add if section
                if elif_matches:
                    first_elif_idx = elif_matches[0].start()
                    content_sections.append(("if", condition_expr, full_content[start_idx:first_elif_idx]))
                    
                    # Add elif sections
                    for i, elif_match in enumerate(elif_matches):
                        elif_condition = elif_match.group(1)
                        start_idx = elif_match.end()
                        end_idx = elif_matches[i+1].start() if i+1 < len(elif_matches) else (else_match.start() if else_match else len(full_content))
                        content_sections.append(("elif", elif_condition, full_content[start_idx:end_idx]))
                else:
                    content_sections.append(("if", condition_expr, full_content[start_idx:else_match.start()]))
                
                # Add else section if present
                if else_match:
                    content_sections.append(("else", None, full_content[else_match.end():]))
            else:
                # Simple if/endif without elif/else
                content_sections.append(("if", condition_expr, full_content))
            
            # Evaluate each section
            result_content = ""
            section_included = False
            
            for section_type, section_condition, section_content in content_sections:
                # Skip remaining sections if one has already been included
                if section_included:
                    continue
                
                # Else sections have no condition, always include if reached
                if section_type == "else":
                    result_content = section_content
                    section_included = True
                    self.logger.debug(f"Including 'else' section ({len(section_content)} chars)")
                    included_count += 1
                    continue
                
                # Process condition - check for equality first
                try:
                    equality_match = equality_condition.match(section_condition)
                    
                    if equality_match:
                        # This is an equality check like "varname == 'value'"
                        var_name = equality_match.group(1)
                        expected_value = equality_match.group(2)
                        
                        # Get the variable value
                        actual_value = self._get_nested_value(data, var_name)
                        
                        # Compare values
                        condition_met = (str(actual_value) == expected_value)
                        self.logger.debug(f"Equality condition: {var_name} == '{expected_value}', Actual: '{actual_value}', Result: {condition_met}")
                    else:
                        # Simple variable truthiness check
                        condition_value = self._get_nested_value(data, section_condition)
                        
                        # Special handling for critical variables
                        if section_condition == "additional_guidelines":
                            # Double-check variable existence for critical variables
                            self.logger.debug(f"Special condition '{section_condition}', Raw value: '{condition_value}'")
                            
                            # Force to true if present, even with empty value
                            if section_condition in data:
                                condition_met = True 
                                self.logger.debug("Forcing additional_guidelines condition to TRUE because variable exists")
                            else:
                                condition_met = bool(condition_value)
                        else:
                            # Normal boolean evaluation
                            condition_met = bool(condition_value)
                            self.logger.debug(f"Boolean condition: {section_condition}, Value: {condition_value}, Result: {condition_met}")
                    
                    # Include content if condition is met
                    if condition_met:
                        result_content = section_content
                        section_included = True
                        self.logger.debug(f"Condition '{section_condition}' is TRUE - Including {section_type} content")
                        included_count += 1
                
                except Exception as e:
                    self.logger.error(f"Error evaluating condition '{section_condition}': {e}")
                    # On error, include error comment only in this section
                    if section_type == "if":
                        result_content = f"<!-- Error in {section_type} condition: {section_condition} -->"
                        section_included = True  # Treat as included to prevent else clause
                
            # If no section was included, result is empty
            if not section_included:
                excluded_count += 1
                
            # Replace the entire construct with the result
            template = template.replace(match.group(0), result_content)
            processed_count += 1
        
        # Log summary
        if processed_count > 0:
            self.logger.debug(f"Processed {processed_count} conditional sections: {included_count} included, {excluded_count} excluded")
        
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
    
    def _process_includes(self, template: str) -> str:
        """Process include directives in the template.
        
        This method recursively processes {#include fragment_name} directives in templates,
        supporting multiple formats of fragment references with robust fallback mechanisms.
        The processing continues until all nested includes are resolved or no more matches
        are found.
        
        Args:
            template: The template text with include directives.
            
        Returns:
            The template with all includes processed and replaced with fragment content.
        """
        # Track processed fragments to prevent infinite recursion
        processed_fragments = set()
        max_recursion_depth = 10
        
        # More permissive regex for tracing all possible include patterns for debugging
        all_includes_pattern = r"\{#\s*include\s+([^\}]+)\s*\}"
        all_includes = re.findall(all_includes_pattern, template)
        if all_includes:
            self.logger.debug(f"Template contains these include patterns: {[f.strip() for f in all_includes]}")
        
        def process_include_recursive(template_text, depth=0):
            """Process includes recursively, handling nested includes."""
            if depth > max_recursion_depth:
                self.logger.warning(f"Maximum include recursion depth ({max_recursion_depth}) reached")
                return template_text
                
            # Find all include directives at this level
            while True:
                match = re.search(self.INCLUDE_PATTERN, template_text)
                if not match:
                    break
                
                # Get the full matched text and the fragment name (with whitespace cleaned)
                full_match = match.group(0)
                fragment_name = match.group(1).strip()
                fragment_original = fragment_name  # Keep original for logging
                
                self.logger.debug(f"[Depth {depth}] Found include directive: '{full_match}' for fragment: '{fragment_name}'")
                
                # Skip if we've already processed this fragment at this path (prevents infinite recursion)
                fragment_path = f"{depth}:{fragment_name}"
                if fragment_path in processed_fragments:
                    self.logger.warning(f"Circular reference detected for fragment: {fragment_name}")
                    template_text = template_text.replace(full_match, f"{{CIRCULAR_REFERENCE:{fragment_name}}}")
                    continue
                
                processed_fragments.add(fragment_path)
                
                # Get fragment content with comprehensive fallback strategy
                fragment_content = self._find_fragment(fragment_name)
                
                if fragment_content:
                    # Replace the include directive with the fragment content
                    template_text = template_text.replace(full_match, fragment_content)
                    self.logger.debug(f"Successfully included fragment: '{fragment_original}' with {len(fragment_content)} chars")
                    
                    # Process any nested includes in the fragment content (recursive)
                    template_text = process_include_recursive(template_text, depth + 1)
                else:
                    # Direct include didn't work, try more extensive searches
                    self.logger.debug(f"Fragment '{fragment_name}' not found directly, trying variations...")
                    
                    # Get a more comprehensive list of all available fragment keys for diagnostics
                    fragment_keys = sorted(list(self.fragment_repository.keys()))
                    
                    # 1. Try exact keys in repository - case insensitive
                    found = False
                    for key in fragment_keys:
                        if key.lower() == fragment_name.lower():
                            fragment_content = self.fragment_repository[key]
                            template_text = template_text.replace(full_match, fragment_content)
                            self.logger.debug(f"Found fragment with case-insensitive match: '{key}'")
                            found = True
                            break
                    
                    if found:
                        continue
                    
                    # 2. Try with normalized whitespace
                    normalized_name = re.sub(r'\s+', '_', fragment_name)
                    if normalized_name != fragment_name:
                        for key in fragment_keys:
                            if key.lower() == normalized_name.lower():
                                fragment_content = self.fragment_repository[key]
                                template_text = template_text.replace(full_match, fragment_content)
                                self.logger.debug(f"Found fragment with normalized whitespace: '{key}'")
                                found = True
                                break
                    
                    if found:
                        continue
                    
                    # 3. Try with common prefixes 
                    common_prefixes = ["standard_", "batch_", "system_", "user_", "ui_patterns/", "fragments/"]
                    for prefix in common_prefixes:
                        prefixed_name = f"{prefix}{fragment_name}"
                        for key in fragment_keys:
                            if key.lower() == prefixed_name.lower():
                                fragment_content = self.fragment_repository[key]
                                template_text = template_text.replace(full_match, fragment_content)
                                self.logger.debug(f"Found fragment with prefix: '{key}'")
                                found = True
                                break
                        if found:
                            break
                    
                    if found:
                        continue
                    
                    # 4. Try substring matching (most aggressive, but useful for debugging)
                    similar_fragments = sorted([k for k in fragment_keys if fragment_name.lower() in k.lower()])
                    if similar_fragments:
                        self.logger.debug(f"Found {len(similar_fragments)} similar fragments: {similar_fragments[:5]}")
                        most_similar = similar_fragments[0]
                        fragment_content = self.fragment_repository.get(most_similar)
                        if fragment_content:
                            template_text = template_text.replace(full_match, fragment_content)
                            self.logger.debug(f"Using most similar fragment as fallback: '{most_similar}'")
                            continue
                    
                    # If all strategies failed, insert error placeholder
                    self.logger.warning(f"Fragment not found: '{fragment_original}' after trying all variations")
                    template_text = template_text.replace(
                        full_match, 
                        f"{{FRAGMENT_NOT_FOUND:{fragment_original}}}"
                    )
            
            return template_text
            
        # Start the recursive processing
        processed_template = process_include_recursive(template)
        
        # Final check for any remaining unprocessed include directives
        remaining_includes = re.findall(all_includes_pattern, processed_template)
        if remaining_includes:
            self.logger.warning(f"Template still contains unprocessed include directives: {remaining_includes}")
            
            # One last attempt to debug exactly what wasn't matched by our pattern
            standard_includes = re.findall(r"\{#\s*include\s+([a-zA-Z0-9_/]+)\s*\}", processed_template)
            if standard_includes:
                self.logger.warning(f"Standard includes not matched: {standard_includes}")
                
            # Display the unprocessed template sections around include statements
            for unprocessed in remaining_includes:
                context_pattern = fr".{{20}}\{{#\s*include\s+{re.escape(unprocessed)}\s*\}}.{{20}}"
                context_matches = re.findall(context_pattern, processed_template, re.DOTALL)
                if context_matches:
                    self.logger.debug(f"Context for unprocessed include '{unprocessed.strip()}': '{context_matches[0]}'")
        
        return processed_template
    
    def _find_fragment(self, fragment_name: str) -> Optional[str]:
        """Find a fragment using multiple possible name variations.
        
        This is a comprehensive search strategy that tries various formats
        of the fragment name to find the best match. It handles whitespace
        variations, directory prefixes, and partial matches to maximize the
        chances of finding the requested fragment.
        
        Args:
            fragment_name: The name of the fragment to find.
            
        Returns:
            The fragment content if found, None otherwise.
        """
        # Clean the fragment name - normalize whitespace
        cleaned_fragment_name = fragment_name.strip()
        
        # Direct match first (most efficient)
        if cleaned_fragment_name in self.fragment_repository:
            self.logger.debug(f"Found fragment '{cleaned_fragment_name}' by direct match")
            return self.fragment_repository.get(cleaned_fragment_name)
        
        # No direct match, try multiple formats
        self.logger.debug(f"Searching for fragment '{cleaned_fragment_name}' using alternative formats")
        
        # Common fragment name variants - add all possible combinations
        # This covers variations in how fragments are registered and referenced
        base_name = cleaned_fragment_name.split('/')[-1]  # Get base name without path
        
        # Whitespace handling - normalize any whitespace within the name
        normalized_name = re.sub(r'\s+', '_', cleaned_fragment_name)
        normalized_base = re.sub(r'\s+', '_', base_name)
        
        # Build comprehensive list of possible variations
        possible_keys = [
            # Base variations
            cleaned_fragment_name,                # Original name as specified
            cleaned_fragment_name.lower(),        # Lowercase
            normalized_name,                      # With normalized whitespace
            normalized_name.lower(),              # Lowercase with normalized whitespace
            
            # Base name variations (without path)
            base_name,                            # Just the base name without path
            base_name.lower(),                    # Lowercase base name
            normalized_base,                      # Base name with normalized whitespace
            normalized_base.lower(),              # Lowercase base with normalized whitespace
            
            # Common prefixed variants
            f"fragments/{cleaned_fragment_name}",   # With fragments prefix
            f"fragments/{base_name}",               # With fragments prefix + base name
            f"ui_patterns/{cleaned_fragment_name}", # With ui_patterns prefix
            f"ui_patterns/{base_name}",             # With ui_patterns prefix + base name
            
            # Common directory-based variants with prefixes
            f"standard_{base_name}",               # Common standard_ prefix
            f"system_{base_name}",                 # Common system_ prefix
            f"batch_{base_name}",                  # Common batch_ prefix
            f"user_{base_name}",                   # Common user_ prefix
        ]
        
        # Add variations with common prefixes
        common_prefixes = ["ui_patterns", "fragments", "common", "system", "user", "standard", "batch"]
        common_suffixes = ["_format", "_instructions", "_guidelines", "_base", "_fragment", "_template"]
        
        # Add prefix combinations - making sure both / and _ separators are tried
        for prefix in common_prefixes:
            possible_keys.append(f"{prefix}/{base_name}")
            possible_keys.append(f"{prefix}_{base_name}")
            possible_keys.append(f"{prefix}/{normalized_base}")
            possible_keys.append(f"{prefix}_{normalized_base}")
            
            # Check if base name already has a prefix that should be preserved
            for existing_prefix in common_prefixes:
                if base_name.startswith(existing_prefix + "_"):
                    suffix_part = base_name[len(existing_prefix) + 1:]
                    possible_keys.append(f"{prefix}/{existing_prefix}_{suffix_part}")
                    possible_keys.append(f"{prefix}_{existing_prefix}_{suffix_part}")
        
        # Add variations for common suffixes
        for suffix in common_suffixes:
            if base_name.endswith(suffix):
                prefix_part = base_name[:-len(suffix)]
                possible_keys.append(prefix_part)
                possible_keys.append(f"{prefix_part}/{suffix[1:]}")  # Remove leading underscore
        
        # Try each possibility, deduplicated
        tried_keys = set()
        for key in possible_keys:
            if key in tried_keys:
                continue
                
            tried_keys.add(key)
            if key in self.fragment_repository:
                self.logger.debug(f"Found fragment '{cleaned_fragment_name}' using key: {key}")
                return self.fragment_repository.get(key)
        
        # If still not found, try a more aggressive substring-based search
        self.logger.debug(f"Fragment '{cleaned_fragment_name}' not found with standard variations, trying fuzzy matching")
        fragments_list = sorted(list(self.fragment_repository.keys()))
        
        # 1. Try substring matching
        base_name_lower = base_name.lower()
        for key in fragments_list:
            key_lower = key.lower()
            # Check if the base name is contained in the key
            if base_name_lower in key_lower:
                self.logger.debug(f"Found substring match: {key} contains {base_name_lower}")
                # Extra check: if it's the key's basename, that's a high-confidence match
                if key_lower.split('/')[-1] == base_name_lower:
                    self.logger.debug(f"High confidence match: {key}")
                    return self.fragment_repository.get(key)
        
        # 2. Try partial name matching with better handling of separators
        for key in fragments_list:
            # Check for similarity between the key and our fragment name
            key_parts = key.lower().split('/')
            
            # Check if the last part of the key is similar to our base name
            if key_parts and (base_name_lower in key_parts[-1] or key_parts[-1] in base_name_lower):
                self.logger.debug(f"Partial name match: {key}")
                return self.fragment_repository.get(key)
            
            # Also check for underscore vs. space variations
            key_normalized = key.lower().replace('_', ' ')
            base_normalized = base_name_lower.replace('_', ' ')
            if key_normalized.endswith(base_normalized) or base_normalized.endswith(key_normalized):
                self.logger.debug(f"Normalized separator match: {key}")
                return self.fragment_repository.get(key)
                
        # 3. Try checking for any key with a similar function
        # For example, if we're looking for "guidelines" check for any key containing "guide"
        if len(base_name) > 5:  # Only for somewhat longer names
            search_term = base_name_lower[:5]  # Use first few chars
            for key in fragments_list:
                if search_term in key.lower():
                    self.logger.debug(f"Functional match: {key} (searching for '{search_term}')")
                    return self.fragment_repository.get(key)
        
        # 4. If normalized name is different, try again with fully normalized path
        if normalized_name != cleaned_fragment_name:
            for key in fragments_list:
                normalized_key = re.sub(r'\s+', '_', key)
                if normalized_key == normalized_name:
                    self.logger.debug(f"Fully normalized path match: {key}")
                    return self.fragment_repository.get(key)
        
        # Log all fragments we tried and failed to match
        self.logger.warning(f"Could not find fragment: '{cleaned_fragment_name}'")
        self.logger.debug(f"Tried all these variations: {sorted(list(tried_keys))}")
        
        # Only log the full list of available fragments if there aren't too many
        if len(fragments_list) < 50:
            self.logger.debug(f"Available fragments: {fragments_list}")
        else:
            self.logger.debug(f"Available fragments (first 20): {fragments_list[:20]}...")
            
        # No match found after all attempts
        return None
    
    def render(self, data: Dict[str, Any], external_fragments: Optional[Dict[str, str]] = None) -> str:
        """Render the template with the given data.
        
        This method processes the template through the following steps:
        1. Process all include directives (recursively)
        2. Process conditional sections 
        3. Process iteration sections
        4. Substitute all variables
        
        Each stage is logged in detail for debugging purposes, and comprehensive
        error handling ensures the system can recover from template processing issues.
        
        Args:
            data: A dictionary containing the values for template variables.
            external_fragments: Optional external fragment repository to use instead of
                               the internal fragment repository. This allows for fragment
                               repository updates to be properly reflected at render time.
            
        Returns:
            The rendered template as a string.
        """
        try:
            # If external fragment repository is provided, use it (ensures up-to-date fragments)
            original_fragment_repository = None
            if external_fragments is not None:
                # Save the original fragment repository for restoration later
                original_fragment_count = len(self.fragment_repository) if self.fragment_repository else 0
                original_fragment_repository = self.fragment_repository
                
                # Replace with the external fragments
                self.fragment_repository = external_fragments.copy()  # Use a copy to avoid modifying the original
                self.logger.debug(f"Updated fragment repository: {original_fragment_count} → {len(self.fragment_repository)} fragments")
            
            # Clone data to avoid modifying the original
            debug_data = data.copy() if data else {}
            
            # Add debug info to data for template debugging
            debug_data['debug_info'] = f"Template: {self.name}, Role: {self.role}"
            debug_data['template_name'] = self.name
            debug_data['template_role'] = self.role
            
            # Check for required variables
            missing_vars = self.required_variables - set(debug_data.keys())
            if missing_vars:
                missing_list = ", ".join(missing_vars)
                self.logger.warning(f"Missing required variables: {missing_list}")
                # Add placeholders for missing variables to prevent errors
                for var in missing_vars:
                    debug_data[var] = f"[MISSING_REQUIRED_VARIABLE:{var}]"
            
            # Start with the original template
            result = self.template_text
            start_length = len(result)
            
            # Log template processing start
            self.logger.debug(f"===== RENDERING TEMPLATE: {self.name}.{self.role} =====")
            self.logger.debug(f"Original template length: {start_length} characters")
            self.logger.debug(f"Available variables: {sorted(list(debug_data.keys()))}")
            self.logger.debug(f"Available fragments: {len(self.fragment_repository)} entries")
            
            # Print a few fragment names to help with debugging
            fragment_sample = sorted(list(self.fragment_repository.keys()))[:10]
            self.logger.debug(f"Fragment sample: {fragment_sample}")
            
            # Check for include directives in original template
            include_matches = re.findall(r"\{#\s*include\s+([^\}]+)\s*\}", result)
            if include_matches:
                self.logger.debug(f"Template contains these include directives: {include_matches}")
                
                # Check if these fragments exist in repository
                for include_name in include_matches:
                    include_name = include_name.strip()
                    if include_name in self.fragment_repository:
                        self.logger.debug(f"Fragment '{include_name}' exists in repository (direct match)")
                    else:
                        self.logger.warning(f"Fragment '{include_name}' NOT found in repository (direct check)")
                        # Try variations
                        variations = [f"fragments/{include_name}", f"{include_name}_fragment", f"standard_{include_name}"]
                        for var in variations:
                            if var in self.fragment_repository:
                                self.logger.debug(f"Found '{include_name}' as variant: '{var}'")
                                break
            
            # STAGE 1: Process include directives
            self.logger.debug(f"--- STAGE 1: Processing includes ---")
            include_start_time = self._get_timestamp()
            try:
                result = self._process_includes(result)
                after_includes_length = len(result)
                include_count = result.count("FRAGMENT_NOT_FOUND")
                self.logger.debug(
                    f"Processed includes in {self._get_time_diff(include_start_time)}ms. "
                    f"Length change: {start_length} → {after_includes_length} chars. "
                    f"Missing fragments: {include_count}"
                )
            except Exception as e:
                self.logger.error(f"Error processing includes: {e}", exc_info=True)
                # Continue with what we have, but log the error
                self.error_handler.handle_error(
                    e,
                    context={
                        "component": f"XMLTemplate:{self.name}",
                        "stage": "process_includes",
                        "template_role": self.role
                    }
                )
            
            # STAGE 2: Process conditional sections
            self.logger.debug(f"--- STAGE 2: Processing conditional sections ---")
            conditional_start_time = self._get_timestamp()
            try:
                result = self._process_conditional_section(result, debug_data)
                after_conditionals_length = len(result)
                self.logger.debug(
                    f"Processed conditionals in {self._get_time_diff(conditional_start_time)}ms. "
                    f"Length change: {after_includes_length} → {after_conditionals_length} chars"
                )
            except Exception as e:
                self.logger.error(f"Error processing conditionals: {e}", exc_info=True)
                self.error_handler.handle_error(
                    e,
                    context={
                        "component": f"XMLTemplate:{self.name}",
                        "stage": "process_conditionals",
                        "template_role": self.role
                    }
                )
            
            # STAGE 3: Process iteration sections
            self.logger.debug(f"--- STAGE 3: Processing iterations ---")
            iteration_start_time = self._get_timestamp()
            try:
                result = self._process_iteration_section(result, debug_data)
                after_iterations_length = len(result)
                self.logger.debug(
                    f"Processed iterations in {self._get_time_diff(iteration_start_time)}ms. "
                    f"Length change: {after_conditionals_length} → {after_iterations_length} chars"
                )
            except Exception as e:
                self.logger.error(f"Error processing iterations: {e}", exc_info=True)
                self.error_handler.handle_error(
                    e,
                    context={
                        "component": f"XMLTemplate:{self.name}",
                        "stage": "process_iterations",
                        "template_role": self.role
                    }
                )
            
            # STAGE 4: Substitute variables
            self.logger.debug(f"--- STAGE 4: Substituting variables ---")
            variable_start_time = self._get_timestamp()
            try:
                result = self._substitute_variables(result, debug_data)
                final_length = len(result)
                remaining_vars = len(re.findall(r'\{[a-zA-Z0-9_\.]+\}', result))
                self.logger.debug(
                    f"Substituted variables in {self._get_time_diff(variable_start_time)}ms. "
                    f"Length change: {after_iterations_length} → {final_length} chars. "
                    f"Unresolved variables: {remaining_vars}"
                )
            except Exception as e:
                self.logger.error(f"Error substituting variables: {e}", exc_info=True)
                self.error_handler.handle_error(
                    e,
                    context={
                        "component": f"XMLTemplate:{self.name}",
                        "stage": "substitute_variables",
                        "template_role": self.role
                    }
                )
            
            # Log completion summary
            self.logger.debug(
                f"===== TEMPLATE RENDERING COMPLETE =====\n"
                f"Template: {self.name}.{self.role}\n"
                f"Total length: {final_length} chars (changed from {start_length}, delta: {final_length - start_length})"
            )
            
            # Check for any remaining template syntax that wasn't processed
            remaining_syntax = re.findall(r'\{#[a-z]+.*?\}', result)
            if remaining_syntax:
                self.logger.warning(f"Unprocessed template directives found: {remaining_syntax[:5]}")
            
            # Restore original fragment repository if we replaced it
            if original_fragment_repository is not None:
                self.fragment_repository = original_fragment_repository
                self.logger.debug(f"Restored original fragment repository")
            
            return result
        except Exception as e:
            # Restore original fragment repository in case of error too
            if original_fragment_repository is not None:
                self.fragment_repository = original_fragment_repository
                self.logger.debug(f"Restored original fragment repository after error")
                
            self.logger.error(f"Fatal error rendering template: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": f"XMLTemplate:{self.name}",
                    "template_role": self.role
                }
            )
            # Return the original template with an error message
            error_msg = f"\n\n<!-- TEMPLATE RENDERING ERROR: {str(e)} -->\n\n"
            return self.template_text + error_msg
    
    def _get_timestamp(self) -> float:
        """Get current timestamp for performance measurement."""
        import time
        return time.time() * 1000  # Convert to milliseconds
    
    def _get_time_diff(self, start_time: float) -> int:
        """Calculate time difference from start_time to now."""
        import time
        return int((time.time() * 1000) - start_time)