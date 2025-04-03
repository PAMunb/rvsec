"""
Prompt Strategy Module

Provides a hierarchy of strategies for generating prompts for LLMs.
This module follows a strategy pattern with a standard interface and
specialized implementations for different prompt generation approaches.

This is the core component of the LLM-driven testing system, as the
quality of prompts directly impacts the quality of generated actions.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Set, Tuple
import re
import os

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserType, ParserFactory
from rvandroid.llm.prompt.prompt_template import PromptTemplate, PromptLibrary
from rvandroid.util.diagnostics import log_wrapper


class PromptStrategy(ABC):
    """
    Abstract base class for prompt generation strategies.
    Defines the interface for all prompt generation strategies.

    ### Architectural Decisions:
    - Follows the Strategy Pattern for prompt generation
    - Provides a common interface for all strategies
    - Enables dynamic strategy selection based on configuration
    - Supports different parser types for screen parsing
    - Integrates with static analysis data for enhanced context

    ### Role in the System:
    - Core component of the LLM-driven testing system
    - Translates application state into effective prompts
    - Coordinates with parsers and static analysis
    - Provides extensibility for custom prompt generation approaches
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
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Handle the parser parameter
        if isinstance(parser, AbstractScreenParser):
            self.parser = parser
        elif isinstance(parser, ParserType) or parser is None:
            parser_type = ParserType.DROIDBOT if parser is None else parser
            self.parser = ParserFactory.create(parser_type)
        else:
            raise TypeError(
                f"parser must be a ParserType enum value or an AbstractScreenParser instance, got {type(parser)}")

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
        context += f"- {len(critical_methods)} methods can reach operations of interest\n"
        context += f"- {len(direct_critical_methods)} methods directly call operations of interest\n"

        # Add window transition information
        if self.static_data and self.static_data.wtg:
            edges = []
            try:
                for edge in self.static_data.wtg.graph.edges():
                    # Safely check edge source
                    try:
                        source = edge[0]
                        source_name = source.name if hasattr(source, 'name') else source
                        
                        # Check if this edge is from our activity
                        if hasattr(activity_class, 'name'):
                            if source_name == activity_class.name:
                                edges.append(edge)
                    except Exception as e:
                        self.logger.debug(f"Error processing edge source: {e}")
                        continue
                        
                if edges:
                    context += f"- Can transition to {len(edges)} other windows/activities\n"
                    
                    # Safely process transition targets
                    for edge in edges[:3]:  # Limit to 3 transitions for brevity
                        try:
                            target = edge[1]
                            target_name = target.name if hasattr(target, 'name') else str(target)
                            context += f"  - Can transition to {target_name}\n"
                        except Exception as e:
                            self.logger.debug(f"Error processing edge target: {e}")

                    if len(edges) > 3:
                        context += f"  - Plus {len(edges) - 3} more transitions\n"
            except Exception as e:
                self.logger.warning(f"Error processing window transitions: {e}")
                context += "- Window transition information unavailable\n"

        return context + "\n"

    def _get_detailed_static_analysis_context(self, activity: str) -> str:
        """
        Add detailed static analysis context including method information.

        Args:
            activity: Current activity name

        Returns:
            String containing detailed static analysis context
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
        context += f"- {len(critical_methods)} methods can reach operations of interest\n"
        context += f"- {len(direct_critical_methods)} methods directly call operations of interest\n"

        # List some critical methods if available
        if direct_critical_methods:
            context += "\nDirect critical methods (sample):\n"
            for method in direct_critical_methods[:3]:  # Limit to 3 for brevity
                context += f"  - {method.name}\n"
            
            if len(direct_critical_methods) > 3:
                context += f"  - Plus {len(direct_critical_methods) - 3} more critical methods\n"

        # Add window transition information with event details
        if self.static_data and self.static_data.wtg:
            edges = []
            try:
                # Safely get edges with data
                for edge in self.static_data.wtg.graph.edges(data=True):
                    # Safely check edge source
                    try:
                        source = edge[0]
                        source_name = source.name if hasattr(source, 'name') else source
                        
                        # Check if this edge is from our activity
                        if hasattr(activity_class, 'name'):
                            if source_name == activity_class.name:
                                edges.append(edge)
                    except Exception as e:
                        self.logger.debug(f"Error processing edge source in detailed view: {e}")
                        continue
                
                if edges:
                    context += f"\nWindow transitions:\n"
                    for edge in edges[:5]:  # Limit to 5 transitions for brevity
                        try:
                            # Safely get target name
                            target = edge[1]
                            target_name = target.name if hasattr(target, 'name') else str(target)
                            
                            # Safely get events
                            events = []
                            if len(edge) > 2:  # Check if we have edge data
                                events = edge[2].get('events', [])
                            
                            context += f"  - Can transition to {target_name} via:\n"
                            
                            # Process events safely
                            for event in events[:2]:  # Limit events per transition
                                try:
                                    event_type_name = event.type.name if hasattr(event, 'type') and hasattr(event.type, 'name') else "unknown event"
                                    context += f"    * {event_type_name}"
                                    
                                    if hasattr(event, 'widget_id') and event.widget_id:
                                        context += f" on widget {event.widget_id}"
                                    context += "\n"
                                except Exception as e:
                                    self.logger.debug(f"Error processing event: {e}")
                                    context += "    * unknown event\n"
                        except Exception as e:
                            self.logger.debug(f"Error processing edge in detailed view: {e}")
                            continue
                    
                    if len(edges) > 5:
                        context += f"  - Plus {len(edges) - 5} more possible transitions\n"
            except Exception as e:
                self.logger.warning(f"Error processing detailed window transitions: {e}")
                context += "\nWindow transition information unavailable\n"

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
                    event_desc += " (directly reaches operations of interest)"
                elif method.reaches_mop:
                    event_desc += " (can reach operations of interest)"
                event_info.append(event_desc)

        if not event_info:
            return ""

        return "Registered events: " + ", ".join(event_info)
    
    def _get_screenshot_analysis(self, state: Dict[str, Any]) -> str:
        """
        Get screenshot analysis information if available.
        
        Args:
            state: Current application state
            
        Returns:
            String containing screenshot analysis information
        """
        screenshot_data = state.get("screenshot_analysis", {})
        if not screenshot_data:
            return ""
            
        analysis = "Visual Analysis:\n"
        
        # Add text information
        texts = screenshot_data.get("texts", [])
        if texts:
            high_confidence_texts = [t for t in texts if t.get("confidence", 0) > 70]
            if high_confidence_texts:
                analysis += f"- Detected {len(high_confidence_texts)} text elements\n"
                
                # List some examples
                for text in high_confidence_texts[:3]:
                    text_content = text.get("text", "")
                    if text_content:
                        analysis += f"  * \"{text_content}\"\n"
        
        # Add error indicators
        errors = screenshot_data.get("error_indicators", [])
        if errors:
            analysis += f"- Detected {len(errors)} potential error indicators\n"
        
        # Add button information
        buttons = screenshot_data.get("buttons", [])
        if buttons:
            analysis += f"- Detected {len(buttons)} potential button shapes\n"
            
        return analysis if analysis != "Visual Analysis:\n" else ""
    
    def _get_transition_guidance(self, state: Dict[str, Any]) -> str:
        """
        Get transition guidance from state if available.
        
        Args:
            state: Current application state
            
        Returns:
            String containing transition guidance
        """
        guidance = state.get("transition_guidance", {})
        if not guidance:
            return ""
            
        output = "Navigation Guidance:\n"
        
        # Add current activity visit information
        visit_count = guidance.get("visit_count", 0)
        output += f"- Current screen has been visited {visit_count} time(s)\n"
        
        # Add suggested targets if available
        suggested = guidance.get("suggested_targets", [])
        if suggested:
            output += "- Suggested exploration targets:\n"
            for target in suggested[:3]:
                output += f"  * {target.get('name', 'Unknown')} ({target.get('visits', 0)} visits)\n"
                
        # Add unexplored elements information
        unexplored = guidance.get("unexplored_elements", [])
        if unexplored:
            output += f"- {len(unexplored)} UI elements on this screen have not yet been tested\n"
            
        return output
    
    def _infer_input_type(self, view: Dict, widget_id: str) -> str:
        """
        Infer the input type for a text field based on properties and static analysis.

        Args:
            view: View data dictionary
            widget_id: Widget identifier

        Returns:
            Inferred input type as string
        """
        # Try to find widget in static data
        widget = None
        if self.static_data and self.static_data.windows:
            activity = self.parser.get_activity_name({})  # Get current activity
            window = self.static_data.windows.get_window(activity)
            if window:
                widget = window.get_widget_by_name(widget_id)

        # Use widget input_type if available
        if widget and hasattr(widget, 'input_type') and widget.input_type:
            return widget.input_type

        # Otherwise infer from view properties
        input_type = view.get("input_type", 0)
        hint = view.get("hint", "")
        text = view.get("text", "")
        resource_id = view.get("resource_id", "")

        # Check common patterns in properties
        lower_id = resource_id.lower() if resource_id else ""
        lower_hint = hint.lower() if hint else ""
        lower_text = text.lower() if text else ""

        if "password" in lower_id or "password" in lower_hint or view.get("is_password", False):
            return "password"
        elif "email" in lower_id or "email" in lower_hint or "email" in lower_text:
            return "email address"
        elif "phone" in lower_id or "phone" in lower_hint:
            return "phone number"
        elif "search" in lower_id or "search" in lower_hint:
            return "search query"
        elif "username" in lower_id or "username" in lower_hint or "user" in lower_id:
            return "username"
        elif "url" in lower_id or "website" in lower_hint:
            return "URL"

        # Default
        return "text"
