# rvandroid/mcp/templates/template.py
"""Core template system for MCP."""

import logging
import re
from typing import Dict, Any, List, Optional, Union

from rvandroid.mcp.mcp_data_structures import MCPMessage, MCPRole, MCPTextContent, MCPImageContent


class TemplateFragment:
    """Reusable fragment of template content."""

    def __init__(self, name: str, content: Any, version: str = "1.0.0"):
        """Initialize a template fragment."""
        self.name = name
        self.content = content
        self.version = version
        self._validate_version(version)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _validate_version(self, version: str) -> None:
        """Validate semantic version format."""
        pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$'
        if not re.match(pattern, version):
            raise ValueError(f"Invalid semantic version: {version}")

    def render(self, variables: Dict[str, Any]) -> Any:
        """Render the fragment with the given variables."""
        if isinstance(self.content, str):
            return self._render_string(self.content, variables)
        elif isinstance(self.content, list):
            return [self._render_item(item, variables) for item in self.content]
        else:
            return self.content

    def _render_string(self, text: str, variables: Dict[str, Any]) -> str:
        """Render a string with variable substitution."""
        # Handle variable substitution
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            text = text.replace(placeholder, str(value))

        # Handle conditional sections
        text = self._process_conditionals(text, variables)

        return text

    def _render_item(self, item: Any, variables: Dict[str, Any]) -> Any:
        """Render a single content item."""
        if isinstance(item, str):
            return self._render_string(item, variables)
        elif isinstance(item, MCPTextContent):
            return MCPTextContent(text=self._render_string(item.text, variables))
        elif isinstance(item, MCPImageContent):
            return item  # Images typically don't need rendering
        elif isinstance(item, dict):
            return {k: self._render_item(v, variables) for k, v in item.items()}
        elif isinstance(item, list):
            return [self._render_item(i, variables) for i in item]
        else:
            return item

    def _process_conditionals(self, text: str, variables: Dict[str, Any]) -> str:
        """Process conditional sections in the text."""
        # Find all conditional blocks
        if_pattern = r'{#if\s+([^}]+)}(.*?){#endif}'

        def replace_if(match):
            condition = match.group(1).strip()
            content = match.group(2)

            # Evaluate the condition
            condition_met = False

            # Simple variable existence check
            if condition in variables:
                condition_met = bool(variables[condition])
            elif "==" in condition:
                # Equals comparison
                var_name, value = condition.split("==", 1)
                var_name = var_name.strip()
                value = value.strip()

                # Handle string literals
                if (value.startswith('"') and value.endswith('"')) or \
                        (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]

                # Compare values
                if var_name in variables:
                    condition_met = str(variables[var_name]) == value
            elif "!=" in condition:
                # Not equals comparison
                var_name, value = condition.split("!=", 1)
                var_name = var_name.strip()
                value = value.strip()

                # Handle string literals
                if (value.startswith('"') and value.endswith('"')) or \
                        (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]

                # Compare values
                if var_name in variables:
                    condition_met = str(variables[var_name]) != value

            return content if condition_met else ""

        # Replace all conditional blocks
        return re.sub(if_pattern, replace_if, text, flags=re.DOTALL)


class MCPPromptTemplate:
    """Template for generating MCP messages."""

    def __init__(self,
                 name: str,
                 template_data: Dict[str, Any],
                 version: str = "1.0.0",
                 parent: Optional['MCPPromptTemplate'] = None):
        """Initialize prompt template."""
        self.name = name
        self.template_data = template_data
        self.version = version
        self.parent = parent
        self.required_vars = template_data.get("required_vars", [])
        self.fragments = {}
        self._validate_version(version)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _validate_version(self, version: str) -> None:
        """Validate semantic version format."""
        pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$'
        if not re.match(pattern, version):
            raise ValueError(f"Invalid semantic version: {version}")

    def add_fragment(self, name: str, fragment: TemplateFragment) -> None:
        """Add a fragment to the template."""
        self.fragments[name] = fragment

    def render(self, variables: Dict[str, Any]) -> List[MCPMessage]:
        """Render the template into MCP messages."""
        self._validate_variables(variables)

        # Process inheritance
        base_messages = []
        if self.parent:
            base_messages = self.parent.render(variables)

        # Process template sections
        message_templates = self.template_data.get("messages", [])
        messages = self._process_messages(message_templates, variables)

        # Merge with base messages as appropriate
        return self._merge_messages(base_messages, messages)

    def _validate_variables(self, variables: Dict[str, Any]) -> None:
        """Validate that all required variables are present."""
        missing = [var for var in self.required_vars if var not in variables]
        if missing:
            raise ValueError(f"Missing required variables: {', '.join(missing)}")

    def _process_messages(self,
                          message_templates: List[Dict[str, Any]],
                          variables: Dict[str, Any]) -> List[MCPMessage]:
        """Process message templates into MCP messages."""
        messages = []

        for template in message_templates:
            # Check for conditional rendering
            if "condition" in template:
                condition = template["condition"]
                if not self._evaluate_condition(condition, variables):
                    continue

            role_str = template.get("role", "user")
            try:
                role = MCPRole(role_str)
            except ValueError:
                self.logger.warning(f"Invalid role: {role_str}, defaulting to USER")
                role = MCPRole.USER

            name = template.get("name")
            if name and isinstance(name, str):
                name = self._render_text(name, variables)

            # Process content
            raw_content = template.get("content", [])
            content = []

            if isinstance(raw_content, str):
                # Single text content
                rendered_text = self._render_text(raw_content, variables)
                content = [MCPTextContent(text=rendered_text)]
            elif isinstance(raw_content, list):
                # Multiple content items
                for item in raw_content:
                    if isinstance(item, dict):
                        content_item = self._process_content_item(item, variables)
                        if content_item:
                            content.append(content_item)
                    elif isinstance(item, str):
                        rendered_text = self._render_text(item, variables)
                        content.append(MCPTextContent(text=rendered_text))

            # Create message
            message = MCPMessage(
                role=role,
                content=content,
                name=name
            )

            messages.append(message)

        return messages

    def _process_content_item(self,
                              item: Dict[str, Any],
                              variables: Dict[str, Any]) -> Optional[Union[MCPTextContent, MCPImageContent]]:
        """Process a single content item."""
        item_type = item.get("type", "text")

        if item_type == "text":
            text = item.get("text", "")
            rendered_text = self._render_text(text, variables)
            return MCPTextContent(text=rendered_text)
        elif item_type == "image":
            url = item.get("url", "")
            detail = item.get("detail", "auto")
            rendered_url = self._render_text(url, variables)
            return MCPImageContent(url=rendered_url, detail=detail)
        elif item_type == "fragment":
            # Include a named fragment
            fragment_name = item.get("name", "")
            if not fragment_name:
                self.logger.warning("Fragment reference without name")
                return None

            if fragment_name not in self.fragments:
                self.logger.warning(f"Fragment not found: {fragment_name}")
                return None

            fragment = self.fragments[fragment_name]
            rendered_content = fragment.render(variables)

            # Handle different fragment return types
            if isinstance(rendered_content, str):
                return MCPTextContent(text=rendered_content)
            elif isinstance(rendered_content, MCPTextContent) or isinstance(rendered_content, MCPImageContent):
                return rendered_content
            elif isinstance(rendered_content, list):
                # For lists, return the first item as a fallback
                if rendered_content and (
                        isinstance(rendered_content[0], MCPTextContent) or
                        isinstance(rendered_content[0], MCPImageContent)
                ):
                    return rendered_content[0]

            return None
        else:
            self.logger.warning(f"Unknown content type: {item_type}")
            return None

    def _render_text(self, text: str, variables: Dict[str, Any]) -> str:
        """Render text with variable substitution and conditional processing."""
        # Replace variables
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            if isinstance(value, (str, int, float, bool)):
                text = text.replace(placeholder, str(value))

        # Process fragment inclusions
        include_pattern = r'{#include\s+([^}]+)}'

        def replace_include(match):
            fragment_name = match.group(1).strip()

            if fragment_name not in self.fragments:
                self.logger.warning(f"Fragment not found: {fragment_name}")
                return f"[Fragment {fragment_name} not found]"

            fragment = self.fragments[fragment_name]
            rendered_content = fragment.render(variables)

            if isinstance(rendered_content, str):
                return rendered_content
            elif isinstance(rendered_content, MCPTextContent):
                return rendered_content.text
            elif isinstance(rendered_content, list):
                # For lists, join all text content
                text_parts = []
                for item in rendered_content:
                    if isinstance(item, MCPTextContent):
                        text_parts.append(item.text)
                    elif isinstance(item, str):
                        text_parts.append(item)
                return "\n".join(text_parts)
            else:
                return "[Fragment could not be rendered]"

        # Replace all fragment inclusions
        text = re.sub(include_pattern, replace_include, text)

        # Process conditional sections
        if_pattern = r'{#if\s+([^}]+)}(.*?){#endif}'

        def replace_if(match):
            condition = match.group(1).strip()
            content = match.group(2)

            if self._evaluate_condition(condition, variables):
                return content
            else:
                return ""

        # Replace all conditional blocks
        text = re.sub(if_pattern, replace_if, text, flags=re.DOTALL)

        return text

    def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """Evaluate a condition for conditional rendering."""
        # Simple variable existence/truthiness check
        if condition in variables:
            return bool(variables[condition])

        # Equals comparison
        if "==" in condition:
            var_name, value = condition.split("==", 1)
            var_name = var_name.strip()
            value = value.strip()

            # Handle string literals
            if (value.startswith('"') and value.endswith('"')) or \
                    (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]

            # Compare values
            if var_name in variables:
                return str(variables[var_name]) == value

        # Not equals comparison
        if "!=" in condition:
            var_name, value = condition.split("!=", 1)
            var_name = var_name.strip()
            value = value.strip()

            # Handle string literals
            if (value.startswith('"') and value.endswith('"')) or \
                    (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]

            # Compare values
            if var_name in variables:
                return str(variables[var_name]) != value

        return False

    def _merge_messages(self,
                        base: List[MCPMessage],
                        new: List[MCPMessage]) -> List[MCPMessage]:
        """Merge base messages with new messages."""
        # Default implementation: append new messages to base
        merged = base.copy()
        merged.extend(new)
        return merged

    def derive(self,
               name: str,
               modifications: Dict[str, Any] = None,
               version_increment: str = "minor") -> 'MCPPromptTemplate':
        """Create a derived template."""
        # Calculate new version
        major, minor, patch = map(int, self.version.split('.'))

        if version_increment == "major":
            new_version = f"{major + 1}.0.0"
        elif version_increment == "minor":
            new_version = f"{major}.{minor + 1}.0"
        else:  # patch
            new_version = f"{major}.{minor}.{patch + 1}"

        # Create a copy of template data
        new_data = self.template_data.copy()

        # Apply modifications
        if modifications:
            for key, value in modifications.items():
                if key in new_data:
                    if isinstance(new_data[key], dict) and isinstance(value, dict):
                        # Merge dictionaries
                        new_data[key].update(value)
                    elif isinstance(new_data[key], list) and isinstance(value, list):
                        # Replace list
                        new_data[key] = value
                    else:
                        # Replace value
                        new_data[key] = value
                else:
                    # Add new key
                    new_data[key] = value

        # Create new template
        derived = MCPPromptTemplate(
            name=name,
            template_data=new_data,
            version=new_version,
            parent=self
        )

        # Copy fragments
        for fragment_name, fragment in self.fragments.items():
            derived.add_fragment(fragment_name, fragment)

        return derived
   