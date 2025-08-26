"""
Simple MOP strategy implementation extending VisionStrategy.

This module implements the MOPVisionStrategy class, extending VisionStrategy with
minimal additions for monitored operations discovery using multimodal analysis.

### Architectural Decisions:
- **Simple Extension**: Extends VisionStrategy without complex modifications
- **Essential Functionality**: Only features that directly support LLM decision-making
- **Existing System Reuse**: Uses current context modes, templates, and fragments
- **No Over-Engineering**: Basic M/DM counting and priority guidance only
- **Performance Focused**: Minimal overhead over base VisionStrategy

### Role in the System:
- **MOP Prioritization**: Simple guidance on [M]/[DM] element priority
- **Action Sequencing**: Basic suggestions for monitored operations testing
- **Context Intelligence**: Minimal context analysis for strategic decisions
- **Template Integration**: Uses specialized mop_vision template

### Integration Points:
- **VisionStrategy**: Inherits all multimodal and coordinate action capabilities
- **Template System**: Uses mop_vision.xml template with existing inheritance
- **Fragment System**: Compatible with existing fragment registration
- **Event System**: Works with existing MOP error detection infrastructure
"""

from typing import Dict, Any, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.llm.constants import StateEntry, ContextMode, PromptStrategyType
from rvandroid_tool.llm.prompt.strategies.vision_strategy import VisionStrategy


class MOPVisionStrategy(VisionStrategy):
    """
    Simple multimodal strategy for monitored operations discovery.
    
    ### Architectural Decisions:
    - **Strategy Extension**: Inherits all VisionStrategy capabilities including multimodal 
      processing, coordinate actions, and context mode support
    - **Simple Intelligence**: Adds basic screen analysis and action sequencing logic
    - **Universal Compatibility**: Maintains compatibility with both STATELESS and RICH context modes
    - **Minimal Overhead**: Lightweight implementation without complex caching or analysis
    
    ### Role in the System:
    - **Simple Screen Analysis**: Basic detection of M/DM element counts and priorities
    - **Action Guidance**: Simple sequence suggestions based on MOP element availability
    - **Context Compatibility**: Works with existing STATELESS and RICH context modes
    - **Template Integration**: Uses specialized mop_vision template for prompt generation
    
    ### Key Features:
    - **M/DM Counting**: Simple counting of monitored operation elements on screen
    - **Priority Guidance**: Basic recommendations for LLM action selection
    - **Action Sequencing**: Simple suggestions for systematic MOP testing
    - **Template Variables**: Additional context variables for MOP-focused prompts
    
    ### Integration Points:
    - **VisionStrategy**: Base class for multimodal and coordinate action support
    - **Template System**: mop_vision.xml template extension with MOP-specific content
    - **Fragment System**: Compatible with existing fragment generation and registration
    - **Error Handling**: Uses existing ErrorHandler infrastructure with MOP-specific context
    """
    
    # Template configuration for MOP vision strategy
    DEFAULT_TEMPLATE = PromptStrategyType.MOP_VISION
    
    def __init__(self, 
                 name: str = PromptStrategyType.MOP_VISION, 
                 context_mode: str = ContextMode.STATELESS, 
                 **kwargs):
        """
        Initialize simple MOP strategy extending VisionStrategy.
        
        ### Initialization Strategy:
        Configures the strategy with the same context_mode support as VisionStrategy
        while adding monitored operations specific analysis capabilities.
        
        Args:
            name: Strategy identifier for registration and template selection
            context_mode: Context enrichment mode (STATELESS or RICH)
            **kwargs: Additional configuration parameters for base strategy
        """
        super().__init__(name, context_mode=context_mode, **kwargs)
        
        # Initialize logging infrastructure
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvandroid_tool.llm.prompt.strategies.mop_vision_strategy",
            {CONTEXT_COMPONENT: "MOPVisionStrategy"}
        )
        
        self.logger.info(f"Initialized MOP Vision Strategy with context_mode: {context_mode}")
        
        # DETAILED_LOG: MOP Vision Strategy initialization
        self.logger.info("DETAILED_LOG: ================== MOP VISION STRATEGY INITIALIZED ==================")
        self.logger.info(f"DETAILED_LOG: Strategy Name: {name}")
        self.logger.info(f"DETAILED_LOG: Context Mode: {context_mode}")
        self.logger.info(f"DETAILED_LOG: Template: {self.DEFAULT_TEMPLATE}")
        self.logger.info(f"DETAILED_LOG: Base Class: VisionStrategy")
        self.logger.info("DETAILED_LOG: ================== END MOP STRATEGY INIT ==================")
    
    @ErrorHandler.handle_errors(
        component="MOPVisionStrategy",
        phase="template_variable_building"
    )
    def _build_template_variables(self, 
                                 state: Dict[str, Any], 
                                 context: Dict[str, Any], 
                                 information: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build template variables with simple monitored operations intelligence.
        
        ### Variable Building Strategy:
        Extends VisionStrategy variable building with basic MOP context analysis including
        simple screen pattern detection and action sequence suggestions.
        
        Args:
            state: Current application state with UI and coverage information
            context: Testing context and configuration parameters
            information: Fragment-generated information for prompt construction
            
        Returns:
            Enhanced template variables with monitored operations intelligence
        """
        # Get base variables from VisionStrategy (includes multimodal processing and context_mode logic)
        # Inherits STATELESS/RICH context handling, coordinate actions, and screenshot integration
        variables = super()._build_template_variables(state, context, information)
        
        # Add monitored operations-specific intelligence for LLM guidance
        # Provides simple M/DM element counting and prioritization without complex analysis
        variables['mop_screen_context'] = self._analyze_screen_context(state)
        variables['mop_action_sequence'] = self._suggest_action_sequence(state)
        
        # RICH context mode uses existing VisionStrategy implementation
        
        return variables
    
    @ErrorHandler.handle_errors(
        component="MOPVisionStrategy",
        phase="screen_context_analysis",
        default_return=""
    )
    def _analyze_screen_context(self, state: Dict[str, Any]) -> str:
        """
        Simple screen context analysis - just count M/DM actions.
        
        ### Analysis Strategy:
        Provides basic guidance based on monitored operation element counts
        without complex pattern analysis or machine learning approaches.
        
        Args:
            state: Current application state containing screen information
            
        Returns:
            Basic context guidance for monitored operations discovery
        """
        screen_description = state.get(StateEntry.STRUCTURED_SCREEN)
        if not screen_description:
            return ""
        
        # Simple M/DM counting without complex analysis
        dm_count = 0
        m_count = 0
        
        if hasattr(screen_description, 'items'):
            for item in screen_description.items:
                if hasattr(item, 'actions'):
                    for action in item.actions:
                        if getattr(action, 'directly_reaches_mop', False):
                            dm_count += 1
                        elif getattr(action, 'reaches_mop', False):
                            m_count += 1
        
        # Simple priority guidance based on counts
        if dm_count >= 2:
            return "Focus on [DM] - multiple direct MOP actions available"
        elif dm_count >= 1:
            return "Focus on [DM] - direct MOP action available"
        elif m_count > 0:
            return "Explore [M] actions for indirect MOP access"
        else:
            return "Explore systematically for MOP actions"
    
    @ErrorHandler.handle_errors(
        component="MOPVisionStrategy",
        phase="action_sequence_suggestion",
        default_return=""
    )
    def _suggest_action_sequence(self, state: Dict[str, Any]) -> str:
        """
        Simple action sequence suggestions based on MOP priorities.
        
        ### Sequence Strategy:
        Provides basic action ordering recommendations based on monitored
        operation element availability without complex planning algorithms.
        
        Args:
            state: Current application state with screen information
            
        Returns:
            Basic sequence guidance for monitored operations testing
        """
        screen_description = state.get(StateEntry.STRUCTURED_SCREEN)
        if not screen_description:
            return ""
        
        # Count [DM] and [M] actions for simple guidance
        dm_count = 0
        m_count = 0
        
        if hasattr(screen_description, 'items'):
            for item in screen_description.items:
                if hasattr(item, 'actions'):
                    for action in item.actions:
                        if getattr(action, 'directly_reaches_mop', False):
                            dm_count += 1
                        elif getattr(action, 'reaches_mop', False):
                            m_count += 1
        
        # Simple priority-based suggestions
        suggestions = []
        
        if dm_count > 0:
            suggestions.append(f"1. Test [DM] actions first ({dm_count} available)")
        
        if m_count > 0:
            suggestions.append(f"2. Explore [M] actions ({m_count} available)")
            
        if not suggestions:
            suggestions.append("Explore screen systematically to discover MOP actions")
        
        return " | ".join(suggestions)