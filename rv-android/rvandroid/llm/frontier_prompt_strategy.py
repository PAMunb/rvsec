# rvandroid/llm/frontier_prompt_strategy.py
from typing import Dict, List
from rvandroid.llm.prompt_strategy import PromptStrategy
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.droidbot.droidbot_state_parser import parse

class FrontierPromptStrategy(PromptStrategy):
    """
    Base prompt strategy for frontier models like Claude, GPT, Gemini, etc.
    These models typically have better understanding of complex instructions
    and can handle more nuanced prompts.
    """
    
    def generate_system_prompt(self) -> str:
        """
        Generate system prompt optimized for frontier models.
        """
        return """You are an expert Android application tester. Your task is to analyze the current app state and suggest the most effective testing actions to maximize code coverage and find potential issues.

Focus on these objectives, in order of priority:
1. Exercise security-critical code paths that directly interact with sensitive operations
2. Explore previously untested UI elements and app features
3. Test complex interaction patterns and edge cases
4. Systematically explore all application states

For each suggested action, provide:
- action_type: The type of action (click, long_click, scroll, set_text, key_event)
- target: The widget ID, resource ID, or coordinates to act upon
- params: Any additional parameters required for the action
- explanation: A brief justification for why this action was selected

Your response must be a valid JSON array of action objects. Each object should follow this schema:
{
  "action_type": "click",
  "target": "widget_id_or_index",
  "params": {},
  "explanation": "Brief explanation"
}

Do not include any text outside of the JSON array. Return exactly 3-5 suggested actions that would be most effective for testing the current screen.
"""
    
    def generate_user_prompt(self, state: Dict) -> str:
        """
        Generate user prompt with detailed context for frontier models.
        """
        # Parse the state
        parsed_state = parse(state, self.static_data)
        activity = state.get("activity", "").replace("/", "")
        
        # Build a comprehensive prompt with clear sections
        sections = []
        
        # Current activity
        sections.append(f"# Current Activity: {activity}")
        
        # Static analysis context
        sections.append("# Static Analysis")
        sections.append(self._add_static_analysis_context(activity))
        
        # UI Elements with rich information
        sections.append("# UI Elements")
        for item in parsed_state.items:
            view = item.view
            widget_id = view.get("resource_id", "").split("/")[-1] if view.get("resource_id") else "unknown"
            widget_class = view.get("class", "").split(".")[-1] if view.get("class") else "unknown"
            widget_text = view.get("text", "")
            widget_bounds = view.get("bounds", [[0, 0], [0, 0]])
            widget_clickable = view.get("clickable", False)
            widget_enabled = view.get("enabled", True)
            
            # Build detailed element description
            element_info = [
                f"## Element: {widget_class} (ID: {widget_id})",
                f"- Description: {item.base_description}",
                f"- Bounds: {widget_bounds}",
                f"- Properties: {'Clickable' if widget_clickable else 'Not clickable'}, {'Enabled' if widget_enabled else 'Disabled'}"
            ]
            
            if widget_text:
                element_info.append(f"- Text: \"{widget_text}\"")
            
            # Add actions with security annotations
            if item.actions:
                action_info = ["- Available actions:"]
                for action in item.actions:
                    security_tag = ""
                    if action.directly_reaches_mop:
                        security_tag = " [CRITICAL: Directly reaches security operation]"
                    elif action.reaches_mop:
                        security_tag = " [IMPORTANT: Can reach security operation]"
                    action_info.append(f"  * {action.text}{security_tag}")
                element_info.append("\n".join(action_info))
            
            # Add static info
            static_info = self._get_widget_static_info(activity, widget_id)
            if static_info:
                element_info.append(f"- Static analysis: {static_info}")
            
            sections.append("\n".join(element_info))
        
        # Action history with context
        if "action_history" in state and state["action_history"]:
            sections.append("# Recent Actions")
            history = state.get("action_history", [])
            recent_actions = history[-5:] if len(history) > 5 else history
            for i, action in enumerate(recent_actions):
                sections.append(f"{i+1}. {action}")
        
        # Testing objective reminder
        sections.append("# Task")
        sections.append(
            "Based on the above information, provide 3-5 test actions that would be most effective "
            "for testing this screen. Focus on exercising security-critical code paths and testing "
            "unexplored functionality. Return your response as a valid JSON array."
        )
        
        return "\n\n".join(sections)
    
    def _add_static_analysis_context(self, activity: str) -> str:
        """
        Add detailed static analysis context for the current activity.
        """
        # Get information about the activity class
        activity_class = None
        if self.static_data and self.static_data.classes:
            activity_class = self.static_data.classes.get_clazz(activity)
        
        if not activity_class:
            return "No static analysis data available for this activity."
            
        # Build comprehensive static analysis
        context = []
        
        # Method statistics
        reachable_methods = [m for m in activity_class.methods if m.reachable]
        critical_methods = [m for m in activity_class.methods if m.reaches_mop]
        direct_critical_methods = [m for m in activity_class.methods if m.directly_reaches_mop]
        
        context.append(f"- Activity contains {len(activity_class.methods)} methods, of which {len(reachable_methods)} are reachable")
        context.append(f"- {len(critical_methods)} methods can reach security-critical operations")
        context.append(f"- {len(direct_critical_methods)} methods directly call security-critical operations")
        
        # TODO terminar .............
        # List some of the critical methods if available
        if direct_critical_methods:
            method_sampl