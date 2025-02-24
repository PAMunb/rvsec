# rvandroid/llm/prompt_strategy.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from rvandroid.model.static import StaticAnalysisData


class PromptStrategy(ABC):
    """
    Abstract base class for prompt generation strategies.
    """
    
    def __init__(self, static_data: StaticAnalysisData):
        """
        Initialize the strategy with static analysis data.
        
        Args:
            static_data: Static analysis data
        """
        self.static_data = static_data
    
    @abstractmethod
    def generate_system_prompt(self) -> str:
        """
        Generate the system prompt.
        
        Returns:
            System prompt
        """
        pass
    
    @abstractmethod
    def generate_user_prompt(self, state: Dict) -> str:
        """
        Generate the user prompt based on state.
        
        Args:
            state: Current application state
            
        Returns:
            User prompt
        """
        pass
    
    def generate_prompts(self, state: Dict) -> List[Dict[str, str]]:
        """
        Generate complete prompt messages.
        
        Args:
            state: Current application state
            
        Returns:
            List of message dictionaries
        """
        return [
            {"role": "system", "content": self.generate_system_prompt()},
            {"role": "user", "content": self.generate_user_prompt(state)}
        ]


class BasicPromptStrategy(PromptStrategy):
    """
    Basic prompt strategy similar to the original PromptGenerator.
    """
    
    def generate_system_prompt(self) -> str:
        """
        Generate a basic system prompt.
        """
        return """You are an Android UI testing expert. Your task is to analyze the current app state and suggest the most effective testing actions.

Focus on:
1. Maximizing code coverage by targeting untested UI elements
2. Exercising important methods that directly or indirectly reach security-critical operations
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
            
            # Format the item description
            prompt += f"- {item.base_description}\n"
            
            # Add actions with their IDs
            if item.actions:
                prompt += "  Available actions:\n"
                for action in item.actions:
                    reaches_mop_info = ""
                    if action.directly_reaches_mop:
                        reaches_mop_info = " [CRITICAL: Directly reaches security operation]"
                    elif action.reaches_mop:
                        reaches_mop_info = " [IMPORTANT: Can reach security operation]"
                    prompt += f"  - {action.text}{reaches_mop_info}\n"
            
            # Add static info if available
            static_info = self._get_widget_static_info(activity, widget_id)
            if static_info:
                prompt += f"  Static analysis: {static_info}\n"
                
        # Add action history if available
        if "action_history" in state:
            prompt += "\nRecent Actions:\n"
            history = state.get("action_history", [])
            for action in history[-5:]:  # Last 5 actions
                prompt += f"- {action}\n"
                
        # Add instructions for the LLM
        prompt += "\nSuggest 3-5 test actions that would be most effective for testing this screen, formatted as JSON according to the specified schema."
        
        return prompt
    
    def _add_static_analysis_context(self, activity: str) -> str:
        """
        Add static analysis context for the current activity.
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
        context += f"- {len(critical_methods)} methods can reach security-critical operations\n"
        context += f"- {len(direct_critical_methods)} methods directly call security-critical operations\n"
        
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


class LangchainPromptStrategy(PromptStrategy):
    """
    Specialized prompt strategy for Langchain models.
    Includes additional context and formatting suitable for Langchain.
    """
    
    def generate_system_prompt(self) -> str:
        """
        Generate system prompt for Langchain.
        """
        # Enhanced system prompt with more details about Android testing
        return """You are an advanced Android UI testing expert specialized in dynamic analysis. Your task is to analyze the current application state and suggest the most effective testing actions to maximize code coverage and security testing.

Focus on these priorities (in order of importance):
1. Security-critical operations - Prioritize actions that trigger methods marked as directly reaching security operations
2. Untested UI elements - Target elements that haven't been interacted with before
3. Complex interaction patterns - Test combinations of actions that might reveal edge cases
4. State exploration - Help visit all possible application states systematically

For each action, provide:
- action_type: One of [click, long_click, scroll, set_text, key_event]
- target: Widget identifier, resource ID, or coordinates
- params: Required parameters for the action (text for input fields, direction for scrolls, etc.)
- explanation: Brief justification for this action's selection

Your response must be a valid JSON array of actions following this exact schema:
[
  {
    "action_type": "click",
    "target": "widget_id_or_index",
    "params": {},
    "explanation": "Brief explanation"
  }
]

DO NOT include any text outside of the JSON array. Your output must be parseable as JSON."""
    
    def generate_user_prompt(self, state: Dict) -> str:
        """
        Generate enhanced user prompt with more context for Langchain models.
        """
        from rvandroid.parser.droidbot.droidbot_state_parser_novo import parse
        
        # Parse the state
        parsed_state = parse(state, self.static_data)
        activity = state.get("activity", "").replace("/", "")
        
        # Enhanced formatting for Langchain
        prompt = f"# Current Android App State Analysis\n\n"
        prompt += f"## Activity: {activity}\n\n"
        
        # Add detailed static analysis
        prompt += "## Static Analysis\n"
        prompt += self._add_static_analysis_context(activity)
        
        # Add UI hierarchy with more details
        prompt += "## UI Hierarchy\n"
        for item in parsed_state.items:
            view = item.view
            widget_id = view.get("resource_id", "").split("/")[-1] if view.get("resource_id") else "unknown"
            widget_class = view.get("class", "").split(".")[-1]
            widget_bounds = view.get("bounds", [[0, 0], [0, 0]])
            
            # Enhanced element description
            prompt += f"### Element: {widget_class} (ID: {widget_id})\n"
            prompt += f"- Description: {item.base_description}\n"
            prompt += f"- Bounds: {widget_bounds}\n"
            prompt += f"- Clickable: {view.get('clickable', False)}\n"
            prompt += f"- Enabled: {view.get('enabled', True)}\n"
            
            # Add actions
            if item.actions:
                prompt += "- Available actions:\n"
                for action in item.actions:
                    security_info = ""
                    if action.directly_reaches_mop:
                        security_info = " 🔴 [CRITICAL SECURITY OPERATION]"
                    elif action.reaches_mop:
                        security_info = " 🟠 [SECURITY IMPACT]"
                    prompt += f"  * {action.text}{security_info}\n"
            
            # Add static info
            static_info = self._get_widget_static_info(activity, widget_id)
            if static_info:
                prompt += f"- Static analysis: {static_info}\n"
        
        # Add action history with timestamps
        if "action_history" in state:
            prompt += "\n## Recent Actions\n"
            history = state.get("action_history", [])
            for i, action in enumerate(history[-5:]):
                prompt += f"{i+1}. {action}\n"
        
        # Clear instructions
        prompt += "\n## Task\n"
        prompt += "Analyze the current state and suggest 3-5 test actions that would be most effective for testing this screen.\n"
        prompt += "Return your suggestions as a valid JSON array following the required schema.\n"
        
        return prompt
    
    # Reuse the helper methods from BasicPromptStrategy
    _add_static_analysis_context = BasicPromptStrategy._add_static_analysis_context
    _get_widget_static_info = BasicPromptStrategy._get_widget_static_info


class DSPyPromptStrategy(PromptStrategy):
    """
    Specialized prompt strategy for DSPy models.
    Uses a more structured approach suitable for DSPy's programming model.
    """
    
    def generate_system_prompt(self) -> str:
        """
        Generate system prompt for DSPy.
        """
        return """You are an Android UI testing AI assistant. Your role is to analyze application states and generate optimal testing actions.

Your output must follow this JSON format exactly:
[{"action_type": "...", "target": "...", "params": {...}, "explanation": "..."}]

Valid action types: click, long_click, scroll, set_text, key_event

Focus on these testing objectives:
- Find security vulnerabilities by targeting critical operations
- Maximize test coverage across the application
- Exercise complex UI paths and edge cases
- Ensure all UI elements are properly tested"""
    
    def generate_user_prompt(self, state: Dict) -> str:
        """
        Generate user prompt for DSPy with additional structure.
        """
        from rvandroid.parser.droidbot.droidbot_state_parser_novo import parse
        
        # Parse the state
        parsed_state = parse(state, self.static_data)
        activity = state.get("activity", "").replace("/", "")
        
        # Structure the prompt with clear sections
        sections = []
        
        # Section 1: Activity information
        sections.append(f"ACTIVITY: {activity}")
        
        # Section 2: Static analysis
        static_section = ["STATIC ANALYSIS:"]
        static_section.append(self._add_static_analysis_context(activity).strip())
        sections.append("\n".join(static_section))
        
        # Section 3: UI elements
        ui_section = ["UI ELEMENTS:"]
        for item in parsed_state.items:
            view = item.view
            widget_id = view.get("resource_id", "").split("/")[-1] if view.get("resource_id") else "unknown"
            
            element_info = [f"ELEMENT: {item.base_description}"]
            
            # Add actions
            if item.actions:
                action_info = []
                for action in item.actions:
                    security_tag = ""
                    if action.directly_reaches_mop:
                        security_tag = "[CRITICAL]"
                    elif action.reaches_mop:
                        security_tag = "[IMPORTANT]"
                    action_info.append(f"- {action.text} {security_tag}")
                
                if action_info:
                    element_info.append("ACTIONS:\n" + "\n".join(action_info))
            
            # Add static info
            static_info = self._get_widget_static_info(activity, widget_id)
            if static_info:
                element_info.append(f"STATIC INFO: {static_info}")
            
            ui_section.append("\n".join(element_info))
        
        sections.append("\n\n".join(ui_section))
        
        # Section 4: Action history
        if "action_history" in state:
            history_section = ["RECENT ACTIONS:"]
            history = state.get("action_history", [])
            for action in history[-5:]:
                history_section.append(f"- {action}")
            sections.append("\n".join(history_section))
        
        # Section 5: Task instruction
        sections.append("TASK: Generate 3-5 test actions in JSON format. Focus on security-critical operations and unexplored UI elements.")
        
        return "\n\n".join(sections)
    
    # Reuse the helper methods from BasicPromptStrategy
    _add_static_analysis_context = BasicPromptStrategy._add_static_analysis_context
    _get_widget_static_info = BasicPromptStrategy._get_widget_static_info


class PromptStrategyFactory:
    """
    Factory for creating prompt strategies.
    """
    
    _STRATEGIES = {
        "basic": BasicPromptStrategy,
        "langchain": LangchainPromptStrategy,
        "dspy": DSPyPromptStrategy
    }
    
    @staticmethod
    def create(strategy_type: str, static_data: StaticAnalysisData) -> PromptStrategy:
        """
        Create a prompt strategy.
        
        Args:
            strategy_type: Type of prompt strategy ('basic', 'langchain', 'dspy')
            static_data: Static analysis data
            
        Returns:
            PromptStrategy instance
        """
        if strategy_type not in PromptStrategyFactory._STRATEGIES:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        strategy_class = PromptStrategyFactory._STRATEGIES[strategy_type]
        return strategy_class(static_data)
    
    @staticmethod
    def register_strategy(name: str, strategy_class: Any) -> None:
        """
        Register a new prompt strategy.
        
        Args:
            name: Name of the strategy
            strategy_class: Strategy class
        """
        PromptStrategyFactory._STRATEGIES[name] = strategy_class