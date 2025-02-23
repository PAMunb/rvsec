# prompt_generator.py

from typing import Dict, List
from rvandroid.model.classes import Classes
from rvandroid.model.window import Windows
from rvandroid.model.wtg import WindowTransitionGraph
from rvandroid.parser.droidbot.state_parser import StateParser

class PromptGenerator:
    """
    Generates prompts for LLM using DroidBot state and static analysis information.
    """
    
    SYSTEM_PROMPT = """You are an Android UI testing assistant specialized in generating effective test actions.
Your role is to analyze the current application state and suggest targeted testing actions that will:
1. Effectively test the current window
2. Maximize code coverage
3. Exercise critical paths (important methods that were used in specifications)
4. Explore new application states when appropriate
5. Test complex UI interactions

Consider:
- Target methods that need coverage improvement
- Available widgets and their events
- Possible navigation paths to other windows
- Current window state and layout

For each suggested action, provide:
- Precise action type (click, long_click, scroll, set_text, key_event)
- Specific target (widget ID or coordinates)
- Any required parameters
- Brief rationale for the action

Provide a sequence of actions that will effectively test the application.
Format your response as a valid JSON array of actions."""
    
    def __init__(self, classes: Classes, windows: Windows, wtg: WindowTransitionGraph):
        self.state_parser = StateParser(classes, windows, wtg)
        self.classes = classes
        self.windows = windows
        self.wtg = wtg

    def generate_prompt(self, droidbot_state: Dict) -> Dict:
        """
        Generates system and user prompts from state data
        
        Args:
            droidbot_state: Current state from DroidBot
            
        Returns:
            Dictionary with system and user prompts
        """
        parsed_state = self.state_parser.parse_state(droidbot_state)
        
        user_prompt = self._generate_user_prompt(parsed_state)
        
        return {
            "system": self.SYSTEM_PROMPT,
            "user": user_prompt
        }
       
    def _generate_user_prompt(self, parsed_state: Dict) -> str:
        """Generates detailed user prompt from parsed state"""
        current_activity = parsed_state["activity"]
        views = parsed_state["views"]
        window_info = parsed_state["window_info"]
        
        prompt = f"""Current Activity: {current_activity}

UI State Analysis:
- Total UI Elements: {window_info['total_widgets']}
- Interactive Elements: {window_info['interactive_elements']}
- Elements with Static Analysis: {window_info['matched_widgets']}

Available Interactive Elements:
"""

        for view in views:
            prompt += self._format_view_info(view)
            
        prompt += "\nSuggest test actions that would be most effective for testing this screen."
        
        return prompt
        
    def _format_view_info(self, view: Dict) -> str:
        """Formats view information for prompt"""
        info = f"- {view['class'].split('.')[-1]}"
        
        if view["id"]:
            info += f" (id={view['id']})"
        if view["name"]:
            info += f" (name={view['name']})"            
        if view["text"]:
            info += f" text='{view['text']}'"
        if view["hint"]:
            info += f" hint='{view['hint']}'"
        if view["description"]:
            info += f" description='{view['description']}'"
            
        info += f"\n  Actions: {', '.join(view['possible_actions'])}"
        
        if "static_info" in view:
            static = view["static_info"]
            if static["registered_events"]:
                info += "\n  Registered events: "
                events = static["registered_events"]
                for event in events:
                    complement = ""
                    if event["directly_reaches_mop"]:
                        complement = ", IMPORTANT: directly reaches speacial method" 
                    elif event["reaches_mop"]:
                        complement = ", IMPORTANT: can reach speacial method" 
                    info += f"\n    - {event["type"]}{complement} "                
                
        return info + "\n"

    def _get_static_context(self, current_activity: str) -> str:
        """Extracts relevant static analysis information for the current activity."""
        if not self.classes or not current_activity:
            return "No static analysis data available."
            
        activity_class = self.classes.get_clazz(current_activity)
        if not activity_class:
            return "No static analysis data for current activity."
            
        reachable_methods = [m for m in activity_class.methods if m.reachable]
        critical_methods = [m for m in reachable_methods if m.reaches_mop]
        
        context = f"Activity contains {len(reachable_methods)} reachable methods\n"
        context += f"{len(critical_methods)} methods can reach security-critical operations\n"
        
        if self.wtg:
            transitions = [edge for edge in self.wtg.graph.edges(activity_class)]
            context += f"Can transition to {len(transitions)} other windows/activities\n"
            
        return context

    def _get_ui_description(self, widgets: List[Dict]) -> str:
        """Creates a description of the current UI elements."""
        if not widgets:
            return "No visible UI elements"
            
        description = f"Found {len(widgets)} interactive elements:\n"
        
        for widget in widgets:
            widget_id = widget.get('resource_id', 'unknown_id')
            widget_type = widget.get('class', 'unknown_type')
            widget_text = widget.get('text', '')
            clickable = widget.get('clickable', False)
            
            description += f"- {widget_type} (id={widget_id})"
            if widget_text:
                description += f" text='{widget_text}'"
            if clickable:
                description += " [clickable]"
            description += "\n"
            
        return description

    def _get_action_history(self, state: Dict) -> str:
        """Formats the recent action history."""
        history = state.get('action_history', [])
        if not history:
            return "No previous actions"
            
        return "\n".join(f"- {action}" for action in history[-5:])
    
    
     
#  prompt = f"""You are an Android UI testing assistant. Analyze the current state and suggest next actions.

# Current Activity: {current_activity}

# Static Analysis Context: .... execution context
# {static_context}

# Current UI State:
# {ui_description}

# Recent Actions:
# {action_history}

# Based on the above information, generate a sequence of test actions that will:
# 1. Effectively test the current window
# 2. Maximize coverage of target methods
# 3. Navigate to unexplored windows when appropriate

# Format your response as a JSON list of actions, where each action has:
# - "action_type": ("click", "long_click", "scroll", "set_text", "key_event")
# - "target": (widget id or coordinates)
# - "params": (additional parameters if needed)

# Consider:
# - Target methods that need coverage improvement
# - Available widgets and their events
# - Possible navigation paths to other windows
# - Current window state and layout

# Provide a sequence of actions that will effectively test the application.
# """
        # return prompt