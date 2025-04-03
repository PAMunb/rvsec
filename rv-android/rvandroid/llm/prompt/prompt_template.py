# rvandroid/llm/prompt/prompt_template.py
"""
Module for template-based prompt generation.
Provides a flexible, composable approach to generate prompts for LLMs.

This module implements a robust template management system that supports:
- Variable substitution with type handling
- Template inheritance and composition
- Conditional sections
- Template versioning
- Fragment reuse and partial rendering
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional, Set, Union


class TemplateFragment:
    """
    Represents a reusable fragment of a template that can be included in other templates.
    Enables composition and reuse of template components.
    """

    def __init__(self, name: str, content: str, version: str = "1.0"):
        """
        Initialize a template fragment.

        Args:
            name: Unique identifier for the fragment
            content: The template content
            version: Version identifier for the fragment
        """
        self.name = name
        self.content = content
        self.version = version

    def render(self, variables: Dict[str, Any] = None) -> str:
        """
        Render the fragment with the provided variables.

        Args:
            variables: Dictionary of variable names and values

        Returns:
            Rendered fragment string
        """
        if not variables:
            return self.content

        result = self.content
        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(var_value))

        return result


class PromptTemplate:
    """
    Represents a template for generating prompts with variable content.
    Uses a composition-based approach for flexibility with advanced features:
    - Variable transformers
    - Required variable validation
    - Template inheritance
    - Conditional sections
    - Fragment composition
    """

    def __init__(self, 
                 template_text: str, 
                 name: str = "",
                 version: str = "1.0",
                 required_variables: List[str] = None,
                 parent: Optional['PromptTemplate'] = None,
                 metadata: Dict[str, Any] = None):
        """
        Initialize a prompt template.

        Args:
            template_text: The template text with placeholders
            name: Template name/identifier
            version: Template version
            required_variables: List of variable names required for this template
            parent: Parent template for inheritance
            metadata: Additional metadata about the template
        """
        self.template_text = template_text
        self.name = name
        self.version = version
        self.required_variables = required_variables or []
        self.parent = parent
        self.metadata = metadata or {}
        self.transformers: Dict[str, Callable] = {}
        self.fragments: Dict[str, TemplateFragment] = {}
        
        # Track rendered variables for evaluation
        self.last_rendered_variables: Set[str] = set()
        self.last_render_time: Optional[datetime] = None

    def add_transformer(self, variable: str, transform_func: Callable) -> 'PromptTemplate':
        """
        Add a transformation function for a variable.

        Args:
            variable: Variable name to transform
            transform_func: Function to transform the variable value

        Returns:
            Self for method chaining
        """
        self.transformers[variable] = transform_func
        return self

    def add_fragment(self, name: str, fragment: Union[TemplateFragment, str]) -> 'PromptTemplate':
        """
        Add a reusable fragment to this template.

        Args:
            name: Fragment identifier
            fragment: TemplateFragment instance or string content

        Returns:
            Self for method chaining
        """
        if isinstance(fragment, str):
            fragment = TemplateFragment(name, fragment)
        
        self.fragments[name] = fragment
        return self

    def derive(self, template_text: str = "", name: str = "", version: str = "") -> 'PromptTemplate':
        """
        Create a derived template that inherits from this one.

        Args:
            template_text: New template text (overrides parent)
            name: New template name (defaults to parent name + "_derived")
            version: New version (defaults to parent version + ".1")

        Returns:
            New PromptTemplate inheriting from this one
        """
        new_name = name or f"{self.name}_derived"
        new_version = version or f"{self.version}.1"
        new_text = template_text or self.template_text
        
        derived = PromptTemplate(
            template_text=new_text,
            name=new_name,
            version=new_version,
            required_variables=self.required_variables.copy(),
            parent=self,
            metadata={**self.metadata, "derived_from": self.name}
        )
        
        # Copy transformers
        for var, transformer in self.transformers.items():
            derived.transformers[var] = transformer
            
        # Copy fragments
        for name, fragment in self.fragments.items():
            derived.fragments[name] = fragment
            
        return derived

    def render(self, variables: Dict[str, Any]) -> str:
        """
        Render the template with the provided variables.

        Args:
            variables: Dictionary of variable names and values

        Returns:
            Rendered template string

        Raises:
            ValueError: If a required variable is missing
        """
        # Track render time
        self.last_render_time = datetime.now()
        self.last_rendered_variables = set()
        
        # Check for required variables
        missing = [var for var in self.required_variables if var not in variables]
        if missing:
            raise ValueError(f"Missing required variables: {', '.join(missing)}")

        # Apply transformers to variables
        processed_vars = {}
        for var_name, var_value in variables.items():
            if var_name in self.transformers:
                processed_vars[var_name] = self.transformers[var_name](var_value)
            else:
                processed_vars[var_name] = var_value
            
            # Track rendered variables
            self.last_rendered_variables.add(var_name)

        # Process conditional sections
        template = self._process_conditionals(self.template_text, processed_vars)
        
        # Process fragment inclusions
        template = self._process_fragment_inclusions(template, processed_vars)

        # Perform template substitution
        result = template
        for var_name, var_value in processed_vars.items():
            placeholder = f"{{{var_name}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(var_value))

        return result
    
    def render_with_parent(self, variables: Dict[str, Any], inherit_mode: str = "override") -> str:
        """
        Render template with parent inheritance.

        Args:
            variables: Dictionary of variable names and values
            inherit_mode: How to combine with parent ("override", "append", or "prepend")

        Returns:
            Rendered template string with parent content included
        """
        if not self.parent:
            return self.render(variables)
            
        # Render parent template
        parent_content = self.parent.render(variables)
        
        # Render this template
        this_content = self.render(variables)
        
        # Combine according to inherit mode
        if inherit_mode == "append":
            return f"{this_content}\n\n{parent_content}"
        elif inherit_mode == "prepend":
            return f"{parent_content}\n\n{this_content}"
        else:  # override
            return this_content
    
    def render_fragment(self, fragment_name: str, variables: Dict[str, Any] = None) -> str:
        """
        Render a specific fragment from this template.

        Args:
            fragment_name: Name of the fragment to render
            variables: Dictionary of variable names and values

        Returns:
            Rendered fragment string

        Raises:
            ValueError: If fragment doesn't exist
        """
        variables = variables or {}
        
        if fragment_name not in self.fragments:
            # Check parent template
            if self.parent and hasattr(self.parent, 'fragments') and fragment_name in self.parent.fragments:
                return self.parent.render_fragment(fragment_name, variables)
            raise ValueError(f"Fragment '{fragment_name}' not found")
            
        return self.fragments[fragment_name].render(variables)
    
    def _process_conditionals(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Process conditional sections in the template.

        Args:
            template: Template text to process
            variables: Dictionary of variables

        Returns:
            Processed template with conditionals evaluated
        """
        # Handle #if conditions
        pattern = r'\{#if\s+([^}]+?)\}(.*?)\{#endif\}'
        
        def replace_conditional(match):
            condition = match.group(1).strip()
            content = match.group(2)
            
            # Evaluate the condition
            if self._evaluate_condition(condition, variables):
                return content
            else:
                return ""
                
        # Process conditionals (using regex with DOTALL to match across lines)
        result = re.sub(pattern, replace_conditional, template, flags=re.DOTALL)
        
        # Process #if-else blocks
        pattern_else = r'\{#if\s+([^}]+?)\}(.*?)\{#else\}(.*?)\{#endif\}'
        
        def replace_conditional_else(match):
            condition = match.group(1).strip()
            if_content = match.group(2)
            else_content = match.group(3)
            
            if self._evaluate_condition(condition, variables):
                return if_content
            else:
                return else_content
                
        result = re.sub(pattern_else, replace_conditional_else, result, flags=re.DOTALL)
        
        return result
    
    def _process_fragment_inclusions(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Process fragment inclusions in the template.

        Args:
            template: Template text to process
            variables: Dictionary of variables

        Returns:
            Processed template with fragments included
        """
        # Handle fragment inclusions
        pattern = r'\{#include\s+([^}]+?)\}'
        
        def replace_inclusion(match):
            fragment_name = match.group(1).strip()
            
            try:
                return self.render_fragment(fragment_name, variables)
            except ValueError:
                return f"[Fragment '{fragment_name}' not found]"
                
        # Process inclusions
        return re.sub(pattern, replace_inclusion, template)
    
    def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """
        Evaluate a condition for conditional sections.

        Args:
            condition: Condition string to evaluate
            variables: Dictionary of variables

        Returns:
            True if condition is satisfied, False otherwise
        """
        try:
            if "=" in condition and not "==" in condition:
                # Simple equality check
                parts = condition.split("=", 1)
                var_name = parts[0].strip()
                value = parts[1].strip()
                
                # If value is quoted, remove quotes
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                    
                if var_name in variables:
                    return str(variables[var_name]) == value
                return False
                
            elif "!=" in condition:
                # Inequality check
                parts = condition.split("!=", 1)
                var_name = parts[0].strip()
                value = parts[1].strip()
                
                # If value is quoted, remove quotes
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                    
                if var_name in variables:
                    return str(variables[var_name]) != value
                return True  # Variable not defined is not equal
                
            elif condition.startswith("exists "):
                # Check if variable exists
                var_name = condition[7:].strip()
                return var_name in variables
                
            elif condition.startswith("!"):
                # Negation
                var_name = condition[1:].strip()
                # Return True if variable doesn't exist or is falsy
                if var_name not in variables:
                    return True
                    
                value = variables[var_name]
                if isinstance(value, bool):
                    return not value
                elif isinstance(value, (int, float)):
                    return value == 0
                elif isinstance(value, str):
                    return not value or value.lower() in ('false', 'no', '0')
                elif value is None:
                    return True
                return False
                
            else:
                # Simple boolean check
                var_name = condition.strip()
                if var_name not in variables:
                    return False
                    
                value = variables[var_name]
                if isinstance(value, bool):
                    return value
                elif isinstance(value, (int, float)):
                    return value != 0
                elif isinstance(value, str):
                    return value.lower() not in ('false', 'no', '0', '')
                elif value is None:
                    return False
                return bool(value)
                
        except Exception as e:
            print(f"Error evaluating condition '{condition}': {e}")
            return False
            
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert template to dictionary for serialization.

        Returns:
            Dictionary representation of the template
        """
        return {
            "name": self.name,
            "version": self.version,
            "template_text": self.template_text,
            "required_variables": self.required_variables,
            "metadata": self.metadata,
            "parent": self.parent.name if self.parent else None,
            "fragments": {name: {"name": f.name, "content": f.content, "version": f.version} 
                          for name, f in self.fragments.items()}
        }
        
    def save_to_file(self, file_path: str) -> bool:
        """
        Save template to a file.

        Args:
            file_path: Path to save the template

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Convert to dictionary and save as JSON
            template_dict = self.to_dict()
            with open(file_path, 'w') as f:
                json.dump(template_dict, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving template: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'PromptTemplate':
        """
        Load a template from a file.

        Args:
            file_path: Path to load the template from

        Returns:
            Loaded PromptTemplate instance

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file contains invalid template data
        """
        try:
            with open(file_path, 'r') as f:
                template_dict = json.load(f)
                
            # Create template instance
            template = cls(
                template_text=template_dict.get("template_text", ""),
                name=template_dict.get("name", ""),
                version=template_dict.get("version", "1.0"),
                required_variables=template_dict.get("required_variables", []),
                metadata=template_dict.get("metadata", {})
            )
            
            # Add fragments
            for name, fragment_dict in template_dict.get("fragments", {}).items():
                fragment = TemplateFragment(
                    name=fragment_dict.get("name", name),
                    content=fragment_dict.get("content", ""),
                    version=fragment_dict.get("version", "1.0")
                )
                template.add_fragment(name, fragment)
                
            return template
        except Exception as e:
            raise ValueError(f"Error loading template from {file_path}: {e}")


class PromptLibrary:
    """
    A centralized repository of reusable prompt templates for different scenarios.
    Provides standard templates that can be customized by derived classes.
    
    Features:
    - Template categorization
    - Versioning for tracking changes
    - Template validation
    - Support for specialized templates for different UI scenarios
    """
    
    # Class-level storage for templates
    _templates: Dict[str, PromptTemplate] = {}
    _categories: Dict[str, List[str]] = {
        "system": [],
        "user": [],
        "form": [],
        "list": [],
        "navigation": [],
        "formats": [],
        "guidelines": []
    }
    
    @classmethod
    def register_template(cls, template: PromptTemplate, category: str = "uncategorized") -> None:
        """
        Register a template in the library.
        
        Args:
            template: Template to register
            category: Category to place the template in
        """
        cls._templates[template.name] = template
        
        # Add to category
        if category not in cls._categories:
            cls._categories[category] = []
            
        if template.name not in cls._categories[category]:
            cls._categories[category].append(template.name)
    
    @classmethod
    def get_template(cls, name: str) -> Optional[PromptTemplate]:
        """
        Get a template by name.
        
        Args:
            name: Template name
            
        Returns:
            PromptTemplate instance or None if not found
        """
        return cls._templates.get(name)
    
    @classmethod
    def list_templates(cls, category: str = None) -> List[str]:
        """
        List available templates.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            List of template names
        """
        if category:
            return cls._categories.get(category, [])
        return list(cls._templates.keys())
        
    @classmethod
    def get_categories(cls) -> List[str]:
        """
        Get available categories.
        
        Returns:
            List of category names
        """
        return list(cls._categories.keys())
    
    @classmethod
    def validate_template(cls, template: PromptTemplate) -> List[str]:
        """
        Validate a template for common issues.
        
        Args:
            template: Template to validate
            
        Returns:
            List of validation error/warning messages
        """
        errors = []
        
        # Check for empty template
        if not template.template_text:
            errors.append("Template text is empty")
            
        # Check for unclosed conditional blocks
        if "{#if" in template.template_text and not "{#endif}" in template.template_text:
            errors.append("Unclosed conditional block (missing {#endif})")
            
        # Check for undefined fragments
        pattern = r'\{#include\s+([^}]+?)\}'
        for match in re.finditer(pattern, template.template_text):
            fragment_name = match.group(1).strip()
            if fragment_name not in template.fragments:
                errors.append(f"Referenced fragment '{fragment_name}' is not defined")
                
        # Check for required variables
        pattern = r'\{([^#][^}]+?)\}'
        for match in re.finditer(pattern, template.template_text):
            var_name = match.group(1).strip()
            if var_name not in template.required_variables:
                errors.append(f"Variable '{var_name}' is used but not listed in required_variables")
                
        return errors

    @staticmethod
    def system_base_template() -> PromptTemplate:
        """
        Basic system prompt template that defines the LLM's role.

        Returns:
            PromptTemplate for system prompt
        """
        template = """You are an Android UI testing expert. Your task is to analyze the current app state and suggest the MOST EFFECTIVE NEXT ACTIONS to take for testing the application thoroughly.

Focus on:
1. {exploration_goal}
2. Maximizing code coverage by targeting untested UI elements
3. Prioritizing testing of methods of interest that directly or indirectly affect operations defined in formal specifications
4. Testing complete workflows from start to finish

{response_format}

{#include dropdown_guidelines}

{#include form_guidelines}

{#if additional_guidelines}{additional_guidelines}{#endif}

DO NOT include any additional text outside of the JSON array. Your response must be valid JSON that can be parsed directly."""

        tmpl = PromptTemplate(
            template,
            name="system_base",
            version="2.0",
            required_variables=["exploration_goal", "response_format"],
            metadata={"description": "Base system prompt for Android testing"}
        )
        
        # Add standard fragments
        tmpl.add_fragment("dropdown_guidelines", PromptLibrary.dropdown_guidelines())
        tmpl.add_fragment("form_guidelines", PromptLibrary.form_guidelines())
        
        # Register in library
        PromptLibrary.register_template(tmpl, "system")
        
        return tmpl

    @staticmethod
    def user_base_template() -> PromptTemplate:
        """
        Basic user prompt template.

        Returns:
            PromptTemplate for user prompt
        """
        template = """Current Activity: {activity}

{#if static_context}{static_context}{#endif}

Current UI Elements and Available Actions:
{ui_elements}

{#if action_history}{action_history}{#endif}

{#if summary}{summary}{#else}SUMMARY: You are testing the {activity} screen. Analyze the UI elements and suggest appropriate testing actions.{#endif}"""

        tmpl = PromptTemplate(
            template,
            name="user_base",
            version="2.0",
            required_variables=["activity", "ui_elements"],
            metadata={"description": "Base user prompt for Android testing"}
        )
        
        # Register in library
        PromptLibrary.register_template(tmpl, "user")
        
        return tmpl

    @staticmethod
    def single_action_format() -> str:
        """
        Format instructions for single action responses.

        Returns:
            Formatting instruction string
        """
        return """Your response MUST follow this schema - a JSON array with EXACTLY ONE object inside:
[
  {
    "action_id": "5",  
    "params": {},  
    "explanation": "Detailed explanation of why this action was chosen as the next step"
  }
]

YOUR RESPONSE MUST CONTAIN EXACTLY ONE ACTION. DO NOT SUGGEST MULTIPLE ACTIONS OR A SEQUENCE OF ACTIONS."""

    @staticmethod
    def multi_action_format() -> str:
        """
        Format instructions for multiple action responses.

        Returns:
            Formatting instruction string
        """
        return """Your response must be a valid JSON array of actions following this schema:
[
  {
    "action_id": "5",  
    "params": {},  
    "explanation": "Detailed explanation of why this action was chosen"
  },
  {
    "action_id": "8",  
    "params": {"text": "example@email.com"},  
    "explanation": "Detailed explanation for this action"
  }
]"""

    @staticmethod
    def dropdown_guidelines() -> str:
        """
        Guidelines for dropdown interaction.

        Returns:
            Dropdown interaction guidelines
        """
        return """DROPDOWN INTERACTION RULES:
1. For dropdown spinners, you MUST first CLICK the dropdown to open it before scrolling
2. The correct sequence is: CLICK dropdown → THEN scroll to find option → THEN click to select"""

    @staticmethod
    def form_guidelines() -> str:
        """
        Guidelines for form testing.

        Returns:
            Form testing guidelines
        """
        return """FORM TESTING WORKFLOW:
1. ALWAYS fill forms in a SEQUENTIAL, LOGICAL ORDER before submitting them
2. For forms with dropdowns/spinners, first click and select from dropdown, then fill other fields, then click action buttons
3. For forms with input fields and buttons, fill ALL required inputs first, THEN click the action/submit button
4. When a form appears to be completely filled, CLICK THE ACTION BUTTON to complete the workflow
5. COMPLETE WORKFLOWS - After filling all required inputs, proceed to action buttons to test the functionality"""
        
    @staticmethod
    def advanced_guidelines() -> str:
        """
        Advanced guidelines for testing.
        
        Returns:
            Advanced testing guidelines
        """
        return """ADVANCED TESTING STRATEGIES:
1. EXPLORE THOROUGHLY - Balance breadth (visiting many screens) and depth (complete workflows)
2. VARY INPUTS - Test both valid and invalid input values to find edge cases
3. CONTEXT AWARENESS - Pay attention to critical operations indicated in static analysis
4. ERROR RECOVERY - When encountering errors, try to proceed or navigate to recover
5. STATE AWARENESS - Avoid repeated testing of the same UI elements/paths
6. DELIBERATE NAVIGATION - Systematically explore app hierarchies from main screens
7. TARGET COVERAGE - Focus on visiting unvisited screens when app is well-explored"""
    
    @staticmethod
    def create_specialized(name: str, template_text: str, parent_name: str = None) -> PromptTemplate:
        """
        Create a specialized template from the library.
        
        Args:
            name: New template name
            template_text: Template text
            parent_name: Name of parent template (optional)
            
        Returns:
            New PromptTemplate instance
        """
        parent = None
        if parent_name and parent_name in PromptLibrary._templates:
            parent = PromptLibrary._templates[parent_name]
            
        template = PromptTemplate(
            template_text=template_text,
            name=name,
            version="1.0",
            parent=parent
        )
        
        # Inherit required variables from parent
        if parent:
            template.required_variables = parent.required_variables.copy()
            template.metadata = {**parent.metadata, "derived_from": parent_name}
            
            # Inherit fragments
            for fragment_name, fragment in parent.fragments.items():
                template.add_fragment(fragment_name, fragment)
                
        # Register in library
        PromptLibrary.register_template(template)
        
        return template
    
    # Initialize standard templates
    @classmethod
    def initialize_templates(cls):
        """Initialize standard templates in the library."""
        # Create format templates
        single_action_format = PromptTemplate(
            template_text=cls.single_action_format(),
            name="single_action_format",
            version="1.0",
            metadata={"description": "Format for single action responses"}
        )
        cls.register_template(single_action_format, "formats")
        
        multi_action_format = PromptTemplate(
            template_text=cls.multi_action_format(),
            name="multi_action_format",
            version="1.0",
            metadata={"description": "Format for multiple action responses"}
        )
        cls.register_template(multi_action_format, "formats")
        
        # Create guideline templates
        dropdown_guidelines = PromptTemplate(
            template_text=cls.dropdown_guidelines(),
            name="dropdown_guidelines",
            version="1.0",
            metadata={"description": "Guidelines for dropdown interaction"}
        )
        cls.register_template(dropdown_guidelines, "guidelines")
        
        form_guidelines = PromptTemplate(
            template_text=cls.form_guidelines(),
            name="form_guidelines",
            version="1.0",
            metadata={"description": "Guidelines for form testing"}
        )
        cls.register_template(form_guidelines, "guidelines")
        
        advanced_guidelines = PromptTemplate(
            template_text=cls.advanced_guidelines(),
            name="advanced_guidelines",
            version="1.0",
            metadata={"description": "Advanced testing guidelines"}
        )
        cls.register_template(advanced_guidelines, "guidelines")
        
        # Initialize base templates (these will add themselves to the library)
        cls.system_base_template()
        cls.user_base_template()


# Initialize the template library
PromptLibrary.initialize_templates()
   