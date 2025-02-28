# rvandroid/llm/prompt_strategy.py

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type, Union

from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.abstract_parser import AbstractScreenParser
from rvandroid.parser.parser_factory import ParserType


class PromptStrategy(ABC):
    """
    Abstract base class for prompt generation strategies.
    Different prompt strategies can be implemented for different models.
    """

    def __init__(self, 
                 static_data: Optional["StaticAnalysisData"] = None, 
                 parser: Union[ParserType, AbstractScreenParser, None] = None):
        """
        Initialize the prompt strategy.

        Args:
            static_data: Static analysis data (optional)
            parser: Either a ParserType enum value, an AbstractScreenParser instance, 
                    or None to use the default parser type
        """
        self.static_data = static_data
        
        # Handle the parser parameter
        if isinstance(parser, AbstractScreenParser):
            self.parser = parser
        elif isinstance(parser, ParserType) or parser is None:
            from rvandroid.parser.parser_factory import ParserFactory
            parser_type = ParserType.DROIDBOT if parser is None else parser
            self.parser = ParserFactory.create(parser_type)
        else:
            raise TypeError(f"parser must be a ParserType enum value or an AbstractScreenParser instance, got {type(parser)}")


    @abstractmethod
    def generate_system_prompt(self) -> str:
        """
        Generate the system prompt that defines the LLM's role and constraints.

        Returns:
            String containing the system prompt
        """
        pass

    @abstractmethod
    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """
        Generate the user prompt based on state.

        Args:
            state: Current application state

        Returns:
            User prompt
        """
        pass

    def generate_prompts(self, state: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate prompts from the current state.

        Args:
            state: Current state dictionary

        Returns:
            List of prompt messages in the format expected by the LLM
        """
        return [
            {"role": "system", "content": self.generate_system_prompt()},
            {"role": "user", "content": self.generate_user_prompt(state)}
        ]

    def _add_static_analysis_context(self, activity: str) -> str:
        """
        Add static analysis context for the current activity.

        Args:
            activity: Current activity name

        Returns:
            String containing static analysis context
        """
        context = "Static Analysis Context:\n"

        # Skip if no static data available
        if not self.static_data or not self.static_data.classes:
            return context + "No static analysis data available for this activity.\n\n"

        # Get information about the activity class
        activity_class = self.static_data.classes.get_clazz(activity)
        if not activity_class:
            return context + "No static analysis data available for this activity.\n\n"

        # Count methods with different properties
        reachable_methods = [m for m in activity_class.methods if m.reachable]
        critical_methods = [m for m in activity_class.methods if m.reaches_mop]
        direct_critical_methods = [m for m in activity_class.methods if m.directly_reaches_mop]

        # Add method statistics
        context += f"- Activity contains {len(reachable_methods)} reachable methods\n"
        context += f"- {len(critical_methods)} methods can reach special operations\n"
        context += f"- {len(direct_critical_methods)} methods directly call special operations\n"

        # Add window transition information
        if self.static_data.wtg:
            edges = [edge for edge in self.static_data.wtg.graph.edges()
                     if edge[0].name == activity_class.name]
            if edges:
                context += f"- Can transition to {len(edges)} other windows/activities\n"
                for edge in edges[:3]:  # Limit to 3 transitions for brevity
                    context += f"  - Can transition to {edge[1].name}\n"

                if len(edges) > 3:
                    context += f"  - Plus {len(edges) - 3} more transitions\n"

        return context + "\n"

    def _get_widget_static_info(self, activity: str, widget_id: str) -> str:
        """
        Get static analysis information for a specific widget.

        Args:
            activity: Activity name
            widget_id: Widget identifier

        Returns:
            String containing widget static analysis information
        """
        if not self.static_data or not self.static_data.windows:
            return ""

        window = self.static_data.windows.get_window(activity)
        if not window:
            return ""

        widget = window.get_widget_by_name(widget_id)
        if not widget:
            return ""

        # Gather information about widget events
        event_info = []
        for event in widget.events:
            if event.signature in self.static_data.classes.methods:
                method = self.static_data.classes.methods[event.signature]
                event_desc = f"{event.type.name}"
                if method.directly_reaches_mop:
                    event_desc += " (directly reaches critical methods)"
                elif method.reaches_mop:
                    event_desc += " (can reach critical methods)"
                event_info.append(event_desc)

        if not event_info:
            return ""

        return "Registered events: " + ", ".join(event_info)
