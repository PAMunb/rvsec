# rvandroid/llm/prompt/flow_based_batch_action_strategy.py
"""
Flow-Based Batch Action Strategy Implementation

Specializes the prompt strategy to generate multiple related actions as a batch,
focusing on completing UI flows efficiently. This strategy identifies UI patterns
and generates sequences of actions that logically belong together.
"""

import logging
import os
from typing import Dict, Any, Optional, Union, List

from rvandroid.llm.prompt.composable_prompt_strategy import ComposablePromptStrategy
from rvandroid.llm.prompt.prompt_template import PromptTemplate, PromptLibrary
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserType
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription
from rvandroid.test_framework.batch_metrics import BatchMetricsCollector
from rvandroid.config.component_configurator import ComponentConfigurator


class FlowBasedBatchActionStrategy(ComposablePromptStrategy):
    """
    A composable strategy specialized for generating batches of related actions.
    
    This strategy identifies UI patterns (forms, lists, tabs, etc.) and generates
    appropriate sequences of actions to efficiently interact with these patterns.
    
    ### Key Capabilities:
    - Detects common UI patterns in the current screen
    - Generates batches of logically related actions for efficient testing
    - Maintains context awareness for interrupted flows
    - Tracks batch execution metrics for analysis
    - Supports pattern-specific batch generation logic
    
    ### Usage:
    This strategy should be used when you want to optimize testing efficiency by
    executing related actions as a batch, especially for form filling, list traversal,
    and similar UI patterns that benefit from batch processing.
    """
    
    # Override process_response to capture pattern information from LLM response
    def process_response(self, response_text: str) -> Dict[str, Any]:
        """
        Process the raw LLM response to extract batch actions and pattern information.
        
        Args:
            response_text: Raw text response from LLM
            
        Returns:
            Processed response with actions and metadata
        """
        import json

        # Store the raw response for pattern info extraction
        self._last_llm_response = response_text
        
        try:
            # Parse JSON response
            response_data = json.loads(response_text)

            # Extract and store pattern information
            if response_data and "pattern_type" in response_data:
                pattern_type = response_data["pattern_type"]
                self.current_pattern_type = pattern_type
                self._last_pattern_info = {
                    "type": pattern_type,
                    "confidence": 0.9  # High confidence for explicit pattern detection
                }
                self.logger.info(f"LLM detected UI pattern: {pattern_type}")
            
            return response_data
            
        except Exception as e:
            self.logger.error(f"Error processing LLM response: {e}")
            # Return empty response in case of error
            return {"pattern_type": "unknown", "actions": [], "batch_explanation": "Failed to parse response"}

    def __init__(self,
                 static_data: Optional[StaticAnalysisData] = None,
                 parser: Union[ParserType, AbstractScreenParser, None] = None):
        """
        Initialize the flow-based batch action strategy.

        Args:
            static_data: Static analysis data (optional)
            parser: Parser type or instance
        """
        super().__init__(static_data, parser, single_action_mode=False)

        self.logger = logging.getLogger(__name__)
        # Override templates with batch-specific ones
        self.system_template = self._create_batch_action_system_template()
        self.user_template = self._create_batch_action_user_template()
        
        # Initialize batch metrics collector
        self.batch_metrics = BatchMetricsCollector()
        
        # State tracking for batch operations
        self.current_batch = []
        self.current_pattern_type = "unknown"
        self.batch_start_time = None
        self._last_pattern_info = None

    def _create_batch_action_system_template(self) -> PromptTemplate:
        """
        Create a system template specialized for batch action mode.

        Returns:
            PromptTemplate for system prompt
        """
        template = """You are an Android UI testing expert. Your task is to analyze the current app state and suggest a BATCH OF RELATED ACTIONS to efficiently test the current UI flow.

Focus on:
1. Identifying UI patterns (forms, lists, tabs, dialogs, etc.) and generating appropriate action sequences
2. Completing logical workflows by batching related actions that naturally belong together
3. Maximizing code coverage through efficient batch execution
4. Prioritizing testing of methods of interest that directly or indirectly affect monitored operations

IMPORTANT: You should identify a specific UI pattern and generate a batch of related actions to efficiently interact with it.

For a FORM pattern, include actions to:
- Enter text in all text fields
- Select options in dropdowns/spinners
- Toggle checkboxes/switches appropriately
- Click the submit/save button

For a LIST pattern, include actions to:
- Scroll through the list
- Select specific items
- Perform operations on list items
- Navigate between list sections

For a TAB pattern, include actions to:
- Navigate through each tab
- Interact with content on each tab
- Test tab switching behavior

For a DIALOG pattern, include actions to:
- Interact with dialog elements
- Test both positive and negative dialog paths
- Ensure proper dialog dismissal

Your response MUST follow this schema - a JSON object with the following structure:
{
  "pattern_type": "form|list|tabs|dialog|navigation|custom",
  "actions": [
    {
      "action_id": "5",  
      "params": {},  
      "explanation": "Why this action is included in the batch"
    },
    {
      "action_id": "8",
      "params": {},
      "explanation": "Why this action logically follows the previous one"
    }
    // Additional related actions...
  ],
  "batch_explanation": "Overall explanation of why these actions form a logical batch"
}

{additional_guidelines}

DO NOT include any additional text outside of the JSON object. Your response must be valid JSON that can be parsed directly."""

        return PromptTemplate(
            template,
            required_variables=["additional_guidelines"]
        )

    def _create_batch_action_user_template(self) -> PromptTemplate:
        """
        Create a user template specialized for batch action mode.

        Returns:
            PromptTemplate for user prompt
        """
        template = """Current Activity: {activity}

{static_context}

UI PATTERN DETECTION:
I need you to identify the primary UI pattern present on this screen. Common patterns include:
- FORM: Multiple input fields with a submit button
- LIST: Scrollable lists of items
- TABS: Multiple tabs that can be switched between
- DIALOG: Modal dialog requiring user input
- NAVIGATION: Screen with primary navigation elements
- CUSTOM: Other specialized UI patterns

{transition_guidance}

Current UI Elements and Available Actions:
{ui_elements}

{action_history}

{workflow_guidance}

BATCH ACTION INSTRUCTIONS:
Based on the identified UI pattern, generate a batch of 2-10 logically related actions that efficiently test this pattern.
Group related actions that naturally belong in a sequence, focusing on completing a specific task or testing a specific aspect of the application.

{critical_instruction}"""

        return PromptTemplate(
            template,
            required_variables=[
                "activity", "ui_elements", "static_context", "transition_guidance",
                "action_history", "workflow_guidance", "critical_instruction"
            ]
        )

    def get_additional_guidelines(self) -> str:
        """
        Get additional guidelines specific to batch action generation.

        Returns:
            String containing additional guidelines
        """
        return """
BATCH GENERATION GUIDELINES:
- Include 2-10 actions in your batch (more for complex patterns, fewer for simple ones)
- Ensure actions flow logically from one to the next
- Focus on completing a cohesive task or interaction sequence
- Make sure all actions in the batch are currently available on the screen
- For form patterns, follow a natural sequence (fill fields from top to bottom, then submit)
- For list patterns, test both scrolling and item selection
- For tab patterns, visit multiple tabs and interact with content on each
- Avoid including unrelated actions that don't fit the identified pattern

IMPORTANT: If you can't identify a clear UI pattern or there aren't enough related actions,
still generate a batch but note this in your explanation and use a smaller batch size."""

    def generate_system_prompt(self) -> str:
        """
        Generate the system prompt for batch action generation.

        Returns:
            Formatted system prompt string
        """
        return self.system_template.render({
            "additional_guidelines": self.get_additional_guidelines()
        })

    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """
        Generate the user prompt for batch action generation.

        Args:
            state: Current application state

        Returns:
            Formatted user prompt string
        """
        # Get activity name with error handling
        try:
            activity = self.parser.get_activity_name(state)
        except (ValueError, AttributeError):
            activity = state.get("package_name", "unknown.package") + ".UnknownActivity"
            self.logger.warning(f"Using fallback activity name: {activity}")
        
        # Get screen description
        screen_description = None
        try:
            if "screen_description" in state and isinstance(state["screen_description"], ScreenDescription):
                screen_description = state["screen_description"]
            elif hasattr(self, '_last_screen_description') and self._last_screen_description:
                screen_description = self._last_screen_description
            else:
                # Try to parse as a fallback
                screen_description = self.process_screen(state)
        except Exception as e:
            self.logger.error(f"Error getting screen description: {e}")
            # Continue with screen_description = None
        
        # Format screen information - handle the case when screen_description is None
        try:
            if screen_description:
                ui_elements = self._format_ui_elements(screen_description, state)
            else:
                ui_elements = "No UI elements could be extracted from the current screen."
        except Exception as e:
            self.logger.error(f"Error formatting UI elements: {e}")
            ui_elements = "Error occurred while formatting UI elements. Please check the screen state."
            
        static_context = self._generate_static_context(activity)
        transition_guidance = self._generate_transition_guidance(state.get("transition_guidance", {}))
        action_history = self._generate_action_history(state.get("action_history", []))
        workflow_guidance = self._generate_workflow_guidance(state.get("workflow_guidance", {}))
        critical_instruction = self._generate_critical_instruction(state)
        
        return self.user_template.render({
            "activity": activity,
            "ui_elements": ui_elements,
            "static_context": static_context,
            "transition_guidance": transition_guidance,
            "action_history": action_history,
            "workflow_guidance": workflow_guidance,
            "critical_instruction": critical_instruction
        })

    def _generate_transition_guidance(self, guidance: Dict[str, Any]) -> str:
        """
        Generate transition guidance with pattern detection hints.

        Args:
            guidance: Transition guidance data

        Returns:
            Formatted transition guidance string
        """
        # Implement full method rather than relying on super()
        if not guidance:
            guidance_text = "TRANSITION GUIDANCE: This is your first interaction with this screen."
        else:
            # Based on _get_transition_guidance from PromptStrategy
            guidance_text = "TRANSITION GUIDANCE:\n"
            
            # Add current activity visit information
            visit_count = guidance.get("visit_count", 0)
            guidance_text += f"- Current screen has been visited {visit_count} time(s)\n"
            
            # Add suggested targets if available
            suggested = guidance.get("suggested_targets", [])
            if suggested:
                guidance_text += "- Suggested exploration targets:\n"
                for target in suggested[:3]:
                    guidance_text += f"  * {target.get('name', 'Unknown')} ({target.get('visits', 0)} visits)\n"
                    
            # Add unexplored elements information
            unexplored = guidance.get("unexplored_elements", [])
            if unexplored:
                guidance_text += f"- {len(unexplored)} UI elements on this screen have not yet been tested\n"
        
        # Add pattern-specific guidance
        guidance_text += "\nPattern Detection Hints:\n"
        
        # Check for form patterns
        input_fields = guidance.get('input_fields', 0)
        if input_fields > 1:
            guidance_text += f"- Detected {input_fields} input fields - consider using FORM pattern\n"
        
        # Check for list patterns
        list_items = guidance.get('list_items', 0)
        if list_items > 3:
            guidance_text += f"- Detected {list_items} list items - consider using LIST pattern\n"
        
        # Check for tab patterns
        tabs = guidance.get('tabs', 0)
        if tabs > 1:
            guidance_text += f"- Detected {tabs} tabs - consider using TABS pattern\n"
        
        # Check for dialog patterns
        if guidance.get('is_dialog', False):
            guidance_text += "- Detected dialog elements - consider using DIALOG pattern\n"
        
        # Check for navigation patterns
        nav_elements = guidance.get('navigation_elements', 0)
        if nav_elements > 2:
            guidance_text += f"- Detected {nav_elements} navigation elements - consider using NAVIGATION pattern\n"
        
        return guidance_text
        
    def _generate_static_context(self, activity: str) -> str:
        """
        Generate static analysis context for the current activity.
        
        Args:
            activity: Current activity name
            
        Returns:
            Formatted static context string
        """
        if self.detailed_static_analysis:
            return self._get_detailed_static_analysis_context(activity)
        else:
            return self._add_static_analysis_context(activity)
            
    def _generate_action_history(self, action_history: List[Any]) -> str:
        """
        Generate formatted action history.
        
        Args:
            action_history: List of previous actions
            
        Returns:
            Formatted action history string
        """
        if not action_history:
            return "ACTION HISTORY: No previous actions have been taken."
            
        history_text = "ACTION HISTORY:\n"
        
        # Handle only the last 10 actions for brevity
        recent_actions = action_history[-10:] if len(action_history) > 10 else action_history
        
        for i, action in enumerate(recent_actions):
            # Handle different action formats
            if isinstance(action, dict):
                # Dictionary format
                action_id = action.get("action_id", "unknown")
                description = action.get("description", "Unknown action")
                result = action.get("result", "Unknown result")
            elif isinstance(action, str):
                # String format
                action_id = "unknown"
                description = action
                result = "executed"
            else:
                # Other formats
                action_id = "unknown"
                description = str(action)
                result = "executed"
            
            history_text += f"{i+1}. Action {action_id}: {description} -> {result}\n"
            
        if len(action_history) > 10:
            history_text += f"[Plus {len(action_history) - 10} earlier actions not shown]\n"
            
        return history_text
        
    def _generate_workflow_guidance(self, workflow: Any) -> str:
        """
        Generate workflow-specific guidance.
        
        Args:
            workflow: Workflow guidance data (dictionary or other)
            
        Returns:
            Formatted workflow guidance string
        """
        # Handle non-dictionary or empty workflows
        if not workflow or not isinstance(workflow, dict):
            return "WORKFLOW GUIDANCE: Identify the most logical sequence of related actions to execute as a batch."
            
        guidance_text = "WORKFLOW GUIDANCE:\n"
        
        # Add specialized guidance based on detected UI pattern
        pattern = workflow.get("pattern", "")
        if pattern == "form":
            guidance_text += "{#include form_guidance}\n"
        elif pattern == "list":
            guidance_text += "{#include list_guidance}\n"
        elif pattern == "tabs":
            guidance_text += "Focus on visiting each tab and interacting with content on each tab.\n"
        elif pattern == "dialog":
            guidance_text += "Focus on testing both positive and negative dialog paths.\n"
        
        # Add explicit goals if available
        goals = workflow.get("goals", [])
        if isinstance(goals, list):
            if goals:
                guidance_text += "\nSuggested testing goals:\n"
                for goal in goals:
                    guidance_text += f"- {goal}\n"
        elif isinstance(goals, str):
            guidance_text += f"\nSuggested testing goal: {goals}\n"
                
        return guidance_text

    def _generate_critical_instruction(self, state: Any) -> str:
        """
        Generate critical instruction for batch action mode.

        Args:
            state: Current application state

        Returns:
            Critical instruction string
        """
        instruction = """CRITICAL TASK: Analyze the current UI, identify the primary UI pattern present, and generate a batch of related actions that efficiently test this pattern.

Your response must include:
1. The identified pattern type
2. A sequence of 2-10 related actions with their IDs
3. An explanation for each action and the overall batch logic

RESPOND WITH VALID JSON ONLY containing the pattern_type, actions array, and batch_explanation."""
        
        # Add context about partial batch execution if we have an interrupted batch
        if isinstance(state, dict) and state.get("interrupted_batch"):
            instruction += "\n\nNOTE: The previous batch was interrupted. Consider continuing the incomplete workflow or starting a new one depending on the current screen state."
        
        return instruction

    def process_batch_metrics(self, batch_data: Dict[str, Any]) -> None:
        """
        Process metrics for a completed batch execution.

        Args:
            batch_data: Data about the executed batch
        """
        # Record batch execution metrics
        self.batch_metrics.record_batch_execution(batch_data)
        
        # Save metrics to file if output directory is available
        if hasattr(self, 'output_dir') and self.output_dir:
            metrics_file = os.path.join(self.output_dir, "batch_metrics.json")
            self.batch_metrics.save_to_file(metrics_file)
            self.logger.info(f"Saved batch metrics to {metrics_file}")

    def get_batch_metrics(self) -> Dict[str, Any]:
        """
        Get current batch metrics.

        Returns:
            Dictionary of calculated batch metrics
        """
        return self.batch_metrics.calculate_metrics()
        
    def get_last_pattern_info(self) -> Dict[str, Any]:
        """
        Get information about the most recently detected UI pattern.
        
        Returns:
            Dictionary with pattern type and confidence information
        """
        # If we have explicit pattern info stored, return it
        if hasattr(self, '_last_pattern_info') and self._last_pattern_info:
            return self._last_pattern_info
            
        # Try to extract from the last LLM response
        if hasattr(self, '_last_llm_response') and self._last_llm_response:
            try:
                # Try to parse JSON if it's a string
                if isinstance(self._last_llm_response, str):
                    import json
                    response_data = json.loads(self._last_llm_response)
                else:
                    response_data = self._last_llm_response
                    
                if "pattern_type" in response_data:
                    pattern_type = response_data["pattern_type"]
                    # Store for future use
                    self._last_pattern_info = {
                        "type": pattern_type,
                        "confidence": 0.9  # Default high confidence for LLM-detected patterns
                    }
                    return self._last_pattern_info
            except Exception as e:
                self.logger.error(f"Error extracting pattern info from LLM response: {e}")
                
        # Use current_pattern_type as fallback
        if hasattr(self, 'current_pattern_type') and self.current_pattern_type != "unknown":
            return {
                "type": self.current_pattern_type,
                "confidence": 0.7  # Lower confidence for fallback mechanism
            }
            
        # Return None if no pattern info available
        return None
        
    def _format_ui_elements(self, screen_description: ScreenDescription, state: Any) -> str:
        """
        Format UI elements for batch action prompt display.
        This implementation provides additional batch-oriented information
        compared to the base class implementation.

        Args:
            screen_description: Parsed screen description
            state: Current application state

        Returns:
            Formatted UI elements string
        """
        try:
            # Ensure screen_description has items
            if not screen_description or not hasattr(screen_description, 'items') or not screen_description.items:
                return "No UI elements detected in the current state."
                
            lines = []
            
            # Get activity from state with fallback
            if isinstance(state, dict):
                activity = state.get("activity", "")
            else:
                activity = ""
            
            # Get UI pattern indicators
            form_element_count = 0
            list_element_count = 0
            button_count = 0
            
            # Process each item
            for item in screen_description.items:
                try:
                    view = item.view
                    widget_id = view.get("resource_id", "").split("/")[-1] if view.get("resource_id") else "unknown"
                    
                    # Count UI pattern indicators
                    if "EditText" in item.base_description or "text field" in item.base_description.lower():
                        form_element_count += 1
                    if "List" in item.base_description or "RecyclerView" in item.base_description:
                        list_element_count += 1
                    if "Button" in item.base_description:
                        button_count += 1
                    
                    # Format the item description with more batch-oriented information
                    lines.append(f"- {item.base_description}")
                    
                    # Add actions with their IDs
                    if item.actions:
                        lines.append("  Available actions:")
                        for action in item.actions:
                            # Add importance indicators
                            importance_tag = ""
                            if hasattr(action, 'directly_reaches_mop') and action.directly_reaches_mop:
                                importance_tag = " [CRITICAL: Directly reaches operation of interest]"
                            elif hasattr(action, 'reaches_mop') and action.reaches_mop:
                                importance_tag = " [IMPORTANT: Can reach operation of interest]"
                            
                            # Create detailed action description
                            action_desc = f"  - {action.text} (action_id: \"{action.id}\"){importance_tag}"
                            lines.append(action_desc)
                    
                    # Add guidance for parameterized actions
                    if item.actions and any(a.text.startswith("SET_TEXT") for a in item.actions):
                        # Get input hints or description
                        hint = ""
                        if "hint" in view and view["hint"]:
                            hint = f" (hint: {view['hint']})"
                        elif "content_description" in view and view["content_description"]:
                            hint = f" (description: {view['content_description']})"
                        elif "text" in view and view["text"]:
                            hint = f" (current text: {view['text']})"
                        
                        # Infer input type using base class method if available
                        if hasattr(self, '_infer_input_type'):
                            input_type = self._infer_input_type(view, widget_id)
                            if input_type:
                                lines.append(f"  Input type appears to be: {input_type}{hint}")
                        else:
                            lines.append(f"  Input field{hint}")
                    
                except Exception as e:
                    self.logger.warning(f"Error formatting UI element: {e}")
                    lines.append(f"- Error processing element: {str(e)}")
            
            # Add UI pattern summary for batch action guidance
            pattern_summary = []
            if form_element_count > 0 and button_count > 0:
                pattern_summary.append(f"Form pattern detected: {form_element_count} input fields and {button_count} buttons")
            if list_element_count > 0:
                pattern_summary.append(f"List pattern detected: {list_element_count} list/recycler elements")
            
            if pattern_summary:
                lines.insert(0, "UI PATTERN SUMMARY:")
                for pattern in pattern_summary:
                    lines.insert(1, f"- {pattern}")
                lines.insert(len(pattern_summary) + 1, "")  # Add blank line after summary
            
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"Error in custom _format_ui_elements: {e}", exc_info=True)
            # Fallback to a simple implementation if our custom one fails
            return "UI Elements (error occurred during formatting):\n" + "\n".join([
                f"- {item.base_description}" for item in screen_description.items
            ]) if screen_description and hasattr(screen_description, 'items') else "No UI elements available."