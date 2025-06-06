# rvandroid/rvdroid/llm/directives/directive_parser.py
"""
Directive parser for RVDroid LLM integration.

This module provides functionality to parse structured directives from LLM
responses, validate them, and convert them into actionable directives.
"""

import json
import re
from typing import Dict, Any, List

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class DirectiveParser:
    """
    Parses and validates directives from LLM responses.

    ### Architectural Decisions:
    - Separates directive parsing from LLM interaction logic
    - Uses regex and structured parsing for robustness
    - Implements validation and sanitization for safety
    - Provides translation to internal configuration

    ### Role in the System:
    - Extracts actionable directives from LLM responses
    - Validates directives for safety and feasibility
    - Translates LLM guidance into concrete testing actions
    - Monitors directive effectiveness
    """

    def __init__(self):
        """Initialize the directive parser."""
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.llm.directives.parser",
            {CONTEXT_COMPONENT: "DirectiveParser"}
        )

        # Initialize directive tracking
        self.directive_stats: Dict[str, Dict[str, Any]] = {}

        self.logger.info("Initialized directive parser")

    def parse_directives(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse directives from an LLM response.

        Args:
            response: LLM response text

        Returns:
            List of parsed directives
        """
        directives = []

        # Try multiple parsing strategies

        # Strategy 1: Look for JSON blocks
        json_directives = self._parse_json_directives(response)
        if json_directives:
            directives.extend(json_directives)

        # Strategy 2: Look for formatted directive sections
        section_directives = self._parse_directive_sections(response)
        if section_directives:
            directives.extend(section_directives)

        # Strategy 3: Look for inline directives
        inline_directives = self._parse_inline_directives(response)
        if inline_directives:
            directives.extend(inline_directives)

        # Validate and normalize all directives
        valid_directives = []
        for directive in directives:
            if self._validate_directive(directive):
                normalized = self._normalize_directive(directive)
                valid_directives.append(normalized)

                # Track directive for stats
                directive_type = normalized.get("type", "unknown")
                if directive_type not in self.directive_stats:
                    self.directive_stats[directive_type] = {
                        "count": 0,
                        "success_count": 0,
                        "fail_count": 0
                    }
                self.directive_stats[directive_type]["count"] += 1

        self.logger.info(f"Parsed {len(valid_directives)} valid directives from response")
        return valid_directives

    def parse_suggestions(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse suggestions from an LLM response.

        Args:
            response: LLM response text

        Returns:
            List of parsed suggestions
        """
        suggestions = []

        # Look for suggestions in the response
        suggestion_pattern = r"(?:^|\n)(?:[\d\-\*•]+\s*|\bSuggestion\s*\d*\s*:?\s*)(.+?)(?=\n[\d\-\*•]+\s*|\bSuggestion\s*\d*\s*:|\n\n|$)"
        matches = re.finditer(suggestion_pattern, response, re.MULTILINE | re.IGNORECASE)

        for match in matches:
            suggestion_text = match.group(1).strip()
            if suggestion_text:
                suggestion = {
                    "text": suggestion_text,
                    "priority": self._detect_priority(suggestion_text)
                }
                suggestions.append(suggestion)

        # If no suggestions found with pattern, split by newlines and look for keyword indicators
        if not suggestions:
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line and any(
                        keyword in line.lower() for keyword in ["try", "should", "recommend", "focus on", "test"]):
                    suggestion = {
                        "text": line,
                        "priority": self._detect_priority(line)
                    }
                    suggestions.append(suggestion)

        return suggestions

    def parse_strategy(self, response: str) -> Dict[str, Any]:
        """
        Parse strategy recommendations from an LLM response.

        Args:
            response: LLM response text

        Returns:
            Strategy dictionary
        """
        # Default strategy
        strategy = {
            "strategy": "random",
            "rationale": "Default strategy",
            "duration": 300  # 5 minutes in seconds
        }

        # Try to extract strategy name
        strategy_pattern = r"(?:strategy|approach|recommend|suggest)\s*:?\s*([\w-]+)"
        match = re.search(strategy_pattern, response, re.IGNORECASE)
        if match:
            strategy_name = match.group(1).lower()

            # Map to known strategy names
            strategy_mapping = {
                "random": "random",
                "systematic": "systematic",
                "greedy": "greedy",
                "model": "model-based",
                "model-based": "model-based",
                "modelbased": "model-based",
                "monitored": "monitored-operations-focused",
                "monitored-operations": "monitored-operations-focused", 
                "monitoredoperations": "monitored-operations-focused",
                "mop": "monitored-operations-focused"
            }

            if strategy_name in strategy_mapping:
                strategy["strategy"] = strategy_mapping[strategy_name]

        # Try to extract duration
        duration_pattern = r"(?:duration|for|period|time)\s*:?\s*(\d+)\s*(?:min|minutes|seconds|sec|s)?"
        match = re.search(duration_pattern, response, re.IGNORECASE)
        if match:
            try:
                duration = int(match.group(1))
                # Assume it's in minutes if it's a small number
                if duration < 60:
                    duration *= 60  # Convert to seconds
                strategy["duration"] = duration
            except ValueError:
                pass

        # Extract rationale (everything after "rationale:" or first meaningful paragraph)
        rationale_pattern = r"(?:rationale|reason|explanation)\s*:?\s*(.+?)(?=\n\n|$)"
        match = re.search(rationale_pattern, response, re.IGNORECASE | re.DOTALL)
        if match:
            strategy["rationale"] = match.group(1).strip()
        else:
            # Use first paragraph as rationale
            paragraphs = [p.strip() for p in response.split('\n\n')]
            for paragraph in paragraphs:
                if len(paragraph) > 20:  # Reasonably sized paragraph
                    strategy["rationale"] = paragraph
                    break

        return strategy

    def parse_monitored_operations_interpretation(self, response: str) -> Dict[str, Any]:
        """
        Parse monitored operations interpretation from an LLM response.

        Args:
            response: LLM response text

        Returns:
            Monitored operations interpretation dictionary
        """
        interpretation = {
            "risk_level": "unknown",
            "recommendations": []
        }

        # Try to extract risk level
        risk_pattern = r"(?:risk level|interest level|priority level|risk|interest|vulnerability)\s*:?\s*(low|medium|high|critical)"
        match = re.search(risk_pattern, response, re.IGNORECASE)
        if match:
            interpretation["risk_level"] = match.group(1).lower()

        # Extract recommendations
        recommendations = []

        # Look for recommendation sections
        recommendation_pattern = r"(?:^|\n)(?:[\d\-\*•]+\s*|\bRecommendation\s*\d*\s*:?\s*)(.+?)(?=\n[\d\-\*•]+\s*|\bRecommendation\s*\d*\s*:|\n\n|$)"
        matches = re.finditer(recommendation_pattern, response, re.MULTILINE | re.IGNORECASE)

        for match in matches:
            text = match.group(1).strip()
            if text:
                recommendations.append({
                    "text": text,
                    "priority": self._detect_priority(text)
                })

        # If no recommendations found with pattern, try bullet points and numbered lists
        if not recommendations:
            bullet_pattern = r"(?:^|\n)[\d\-\*•]+\s*(.+?)(?=\n[\d\-\*•]+\s*|\n\n|$)"
            matches = re.finditer(bullet_pattern, response, re.MULTILINE)

            for match in matches:
                text = match.group(1).strip()
                if text:
                    recommendations.append({
                        "text": text,
                        "priority": self._detect_priority(text)
                    })

        interpretation["recommendations"] = recommendations

        return interpretation

    def update_directive_effectiveness(self, directive: Dict[str, Any], success: bool) -> None:
        """
        Update effectiveness stats for a directive.

        Args:
            directive: Directive that was applied
            success: Whether the directive was successful
        """
        directive_type = directive.get("type", "unknown")

        if directive_type in self.directive_stats:
            if success:
                self.directive_stats[directive_type]["success_count"] += 1
            else:
                self.directive_stats[directive_type]["fail_count"] += 1

    def _parse_json_directives(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse JSON-formatted directives from response.

        This method extracts structured directives from LLM responses using
        multiple parsing strategies, prioritizing well-formatted JSON code blocks
        and falling back to pattern matching for less structured formats.

        Args:
            response: LLM response text

        Returns:
            List of directives parsed from JSON
        """
        directives = []

        # Look for JSON blocks within code blocks (preferred format)
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        code_blocks = re.findall(code_block_pattern, response)
        
        for block in code_blocks:
            try:
                # Clean up the block content
                json_str = block.strip()
                
                # Attempt to parse as JSON
                if json_str.startswith('['):
                    json_data = json.loads(json_str)
                    if isinstance(json_data, list):
                        for item in json_data:
                            if isinstance(item, dict):
                                directives.append(item)
                elif json_str.startswith('{'):
                    json_data = json.loads(json_str)
                    if isinstance(json_data, dict):
                        directives.append(json_data)
                        
                # If we successfully parsed directives, don't look for more patterns
                if directives:
                    self.logger.info(f"Successfully parsed JSON directives from code block: {len(directives)} found")
                    return directives
                    
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse code block as JSON: {e}")

        # If code blocks didn't yield results, look for standalone JSON patterns
        json_pattern = r'{(?:[^{}]|{[^{}]*})*}'
        matches = re.finditer(json_pattern, response)

        for match in matches:
            json_str = match.group(0).strip()
            try:
                json_data = json.loads(json_str)
                if isinstance(json_data, dict):
                    directives.append(json_data)
            except json.JSONDecodeError:
                pass
                
        # Look for JSON arrays not in code blocks as a last resort
        array_pattern = r'\[\s*{.*?}\s*(?:,\s*{.*?}\s*)*\]'
        matches = re.finditer(array_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                array_str = match.group(0)
                json_data = json.loads(array_str)
                if isinstance(json_data, list):
                    for item in json_data:
                        if isinstance(item, dict):
                            directives.append(item)
            except json.JSONDecodeError:
                pass

        if directives:
            self.logger.info(f"Successfully parsed JSON directives: {len(directives)} found")
        else:
            self.logger.warning("No JSON directives found in response")
            
        return directives

    def _parse_directive_sections(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse directive sections from response.

        Args:
            response: LLM response text

        Returns:
            List of directives parsed from sections
        """
        directives = []

        # Look for directive sections
        section_pattern = r'(?:^|\n)# Directive\s*(\d*):\s*(.*?)(?=\n# Directive|$)'
        matches = re.finditer(section_pattern, response, re.MULTILINE | re.IGNORECASE | re.DOTALL)

        for match in matches:
            directive_index = match.group(1) or ""
            directive_content = match.group(2).strip()

            # Try to extract directive properties
            directive = {"type": "unknown"}

            # Look for type
            type_match = re.search(r'Type:\s*(\w+)', directive_content, re.IGNORECASE)
            if type_match:
                directive["type"] = type_match.group(1).lower()

            # Look for target
            target_match = re.search(r'Target:\s*(\w+)', directive_content, re.IGNORECASE)
            if target_match:
                directive["target"] = target_match.group(1).lower()

            # Look for priority
            priority_match = re.search(r'Priority:\s*(\w+)', directive_content, re.IGNORECASE)
            if priority_match:
                directive["priority"] = priority_match.group(1).lower()

            # Look for duration
            duration_match = re.search(r'Duration:\s*(\d+)', directive_content, re.IGNORECASE)
            if duration_match:
                try:
                    directive["duration"] = int(duration_match.group(1))
                except ValueError:
                    pass

            # Add description from remaining content
            description = directive_content
            for pattern in [r'Type:\s*\w+', r'Target:\s*\w+', r'Priority:\s*\w+', r'Duration:\s*\d+']:
                description = re.sub(pattern, '', description, flags=re.IGNORECASE)

            description = description.strip()
            if description:
                directive["description"] = description

            directives.append(directive)

        return directives

    def _parse_inline_directives(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse inline directives from response text.

        Args:
            response: LLM response text

        Returns:
            List of directives parsed from inline text
        """
        directives = []

        # Look for common directive patterns
        patterns = [
            # Explore pattern
            r'(?:should|recommend|explore|focus on)\s*(exploring|testing|checking|examining)\s*(?:the\s*)?([\w\s-]+)',
            # Strategy pattern
            r'(?:use|adopt|switch to|follow)\s*(?:a\s*)?([\w-]+)\s*(?:strategy|approach)',
            # Focus pattern
            r'(?:focus|concentrate|prioritize)\s*(?:on\s*)?([\w\s-]+)'
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)

            for match in matches:
                if pattern.startswith('(?:should|recommend|explore'):
                    directive = {
                        "type": "explore",
                        "target": match.group(2).strip().lower(),
                        "priority": "medium"
                    }
                elif pattern.startswith('(?:use|adopt|switch'):
                    strategy_name = match.group(1).strip().lower()
                    directive = {
                        "type": "strategy",
                        "name": strategy_name,
                        "duration": 300  # Default 5 minutes
                    }
                elif pattern.startswith('(?:focus|concentrate'):
                    directive = {
                        "type": "focus",
                        "target": match.group(1).strip().lower(),
                        "priority": "high"
                    }
                else:
                    continue

                directives.append(directive)

        return directives

    def _detect_priority(self, text: str) -> str:
        """
        Detect priority level from text.

        Args:
            text: Text to analyze

        Returns:
            Priority level (high, medium, low)
        """
        # Look for explicit priority indicators
        if re.search(r'\b(critical|urgent|highest|vital|essential)\b', text, re.IGNORECASE):
            return "high"
        elif re.search(r'\b(important|significant|should|recommend)\b', text, re.IGNORECASE):
            return "medium"
        elif re.search(r'\b(consider|optional|suggest|might|could|low)\b', text, re.IGNORECASE):
            return "low"

        # Default to medium priority
        return "medium"

    def _validate_directive(self, directive: Dict[str, Any]) -> bool:
        """
        Validate a directive for required fields and valid values.

        Args:
            directive: Directive to validate

        Returns:
            True if valid, False otherwise
        """
        # Check for required type field
        if "type" not in directive:
            return False

        directive_type = directive.get("type", "").lower()

        # Validate based on directive type
        if directive_type == "explore":
            # Explore directive needs a target
            if "target" not in directive:
                return False

        elif directive_type == "strategy":
            # Strategy directive needs a name
            if "name" not in directive:
                return False

            # Check if strategy name is valid
            valid_strategies = ["random", "systematic", "greedy", "model-based", "monitored-operations-focused"]
            if directive["name"].lower() not in valid_strategies:
                # Try to map to valid strategy
                directive["name"] = self._map_to_valid_strategy(directive["name"])
                if not directive["name"]:
                    return False

        elif directive_type == "focus":
            # Focus directive needs a target
            if "target" not in directive:
                return False

        elif directive_type == "action":
            # Action directive needs action_type and target
            if "action_type" not in directive or "target" not in directive:
                return False

            # Check if action type is valid
            valid_actions = ["click", "scroll", "text_input", "back", "long_click"]
            if directive["action_type"].lower() not in valid_actions:
                return False

        else:
            # Unknown directive type
            return False

        return True

    def _normalize_directive(self, directive: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize directive fields and values.

        Args:
            directive: Directive to normalize

        Returns:
            Normalized directive
        """
        normalized = directive.copy()

        # Normalize type
        if "type" in normalized:
            normalized["type"] = normalized["type"].lower()

        # Normalize priority if present
        if "priority" in normalized:
            priority = normalized["priority"].lower()
            if priority not in ["high", "medium", "low"]:
                # Map to standard priority
                if priority in ["critical", "urgent", "highest"]:
                    normalized["priority"] = "high"
                elif priority in ["normal", "default"]:
                    normalized["priority"] = "medium"
                else:
                    normalized["priority"] = "medium"  # Default

        # Normalize strategy name if present
        if normalized.get("type") == "strategy" and "name" in normalized:
            normalized["name"] = self._map_to_valid_strategy(normalized["name"])

        # Normalize action_type if present
        if "action_type" in normalized:
            normalized["action_type"] = normalized["action_type"].lower()

        return normalized

    def _map_to_valid_strategy(self, strategy_name: str) -> str:
        """
        Map a strategy name to a valid strategy.

        Args:
            strategy_name: Strategy name to map

        Returns:
            Mapped strategy name
        """
        strategy_name = strategy_name.lower()

        # Direct mappings
        mapping = {
            "random": "random",
            "systematic": "systematic",
            "greedy": "greedy",
            "modelbased": "model-based",
            "model-based": "model-based",
            "model": "model-based",
            "monitored": "monitored-operations-focused",
            "monitored-operations": "monitored-operations-focused",
            "monitored-operations-focused": "monitored-operations-focused",
            "monitoredoperations": "monitored-operations-focused",
            "mop": "monitored-operations-focused",
            "mop-focused": "monitored-operations-focused",
            "exploration": "random",
            "exploit": "greedy",
            "balanced": "model-based"
        }

        if strategy_name in mapping:
            return mapping[strategy_name]

        # Fuzzy matching
        for valid, mapped in mapping.items():
            if valid in strategy_name:
                return mapped

        # Default to random if no match
        return "random"
