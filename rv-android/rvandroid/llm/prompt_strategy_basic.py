

from rvandroid.llm.prompt_strategy import PromptStrategy
from typing import Dict, List
import json
import logging
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.droidbot.droidbot_state_parser_novo import parse


class BasicPromptStrategy(PromptStrategy):
    """
    Basic prompt strategy.
    """
    
    def __init__(self, static_data):
        super().__init__(static_data)
        self.logger = logging.getLogger(__name__)
    
    def generate_system_prompt(self) -> str:
        """
        Generate a basic system prompt.
        """
        return """You are an Android UI testing expert. Your task is to analyze the current app state and suggest the most effective testing actions.

Focus on:
1. Maximizing code coverage by targeting untested UI elements
2. Exercising important methods that directly or indirectly affect operations of interest, defined in formal specifications
3. Systematically exploring application states
4. Testing complex UI interactions and edge cases

For each action, provide:
- Action type (click, long_click, scroll, set_text, key_event)
- Target widget identifier or coordinates
- Parameters where needed (text input, scroll direction, etc.)
- Brief explanation of why you chose this action

Format your response as a valid JSON array of actions following this schema:
[
  {
    "action_type": "click",  
    "target": "widget_id_or_index",
    "params": {},  
    "explanation": "Brief explanation"
  },
  ...
]

Maintain awareness of the application state after each action. When suggesting a sequence of actions, ensure they build logically upon each other.

Before responding, carefully analyze the context to avoid suggesting conflicting actions. For example: when a screen has only 2 clickable buttons (each leading to a different activity), select only one button based on the current context and action history. On subsequent executions of the same screen, reference the previous selections to determine which alternative button to choose.

DO NOT include any additional text outside of the JSON array. Your response must be valid JSON that can be parsed directly."""
    
    def generate_user_prompt(self, state: Dict) -> str:
        """
        Generate a basic user prompt from the current application state.
        """
        from rvandroid.parser.droidbot.droidbot_state_parser_novo import parse
        
        # Parse the state to get a structured representation
        parsed_state = parse(state, self.static_data)
        
        # Extract activity name
        activity = state.get("activity", "").replace("/", "")
        
        # Begin building the prompt
        prompt = f"Current Activity: {activity}\n\n"
        
        # Add static analysis context if available
        prompt += self._add_static_analysis_context(activity)
        
        # Add UI state information
        prompt += "Current UI Elements:\n"
        for item in parsed_state.items:
            view = item.view
            widget_id = view.get("resource_id", "").split("/")[-1] if view.get("resource_id") else "unknown"
            widget_text = view.get("text", "")
            
            # Check if there's static analysis information for this widget
            static_info = self._get_widget_static_info(activity, widget_id)
            
            # Format the item description
            prompt += f"- {item.base_description}\n"
            
            # Add actions with their IDs
            if item.actions:
                prompt += "  Available actions:\n"
                for action in item.actions:
                    reaches_mop_info = ""
                    if action.directly_reaches_mop:
                        reaches_mop_info = " [CRITICAL: Directly reaches special operation]"
                    elif action.reaches_mop:
                        reaches_mop_info = " [IMPORTANT: Can reach special operation]"
                    prompt += f"  - {action.text}{reaches_mop_info}\n"
            
            # Add static info if available
            if static_info:
                prompt += f"  Static analysis: {static_info}\n"
                
        # Add action history if available
        if "action_history" in state:
            prompt += "\nRecent Actions:\n"
            history = state.get("action_history", [])
            for action in history[-5:]:  # Last 5 actions
                prompt += f"- {action}\n"
                
        # Add instructions for the LLM
        prompt += "\nSuggest test actions that would be most effective for testing this screen, formatted as JSON according to the specified schema."
        
        return prompt
    
    def _add_static_analysis_context(self, activity: str) -> str:
        """
        Add static analysis context for the current activity.
        
        Args:
            activity: Current activity name
            
        Returns:
            String containing static analysis context
        """
        context = "Static Analysis Context:\n"
        
        # Get information about the activity class
        activity_class = None
        if self.static_data and self.static_data.classes:
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
        self.logger.debug(f"Window for activity {activity}: {window}")
        if not window:
            return ""
            
        widget = window.get_widget_by_name(widget_id)
        self.logger.debug(f"Widget for widget_id {widget_id}: {widget}")
        if not widget:
            return ""
            
        # Gather information about widget events
        event_info = []
        for event in widget.events:
            if event.signature in self.static_data.classes.methods:
                self.logger.debug(f"Event [{event}] found in methods")
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
    