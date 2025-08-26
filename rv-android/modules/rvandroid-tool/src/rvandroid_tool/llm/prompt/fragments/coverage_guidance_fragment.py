"""UI element interaction guidance fragment for the prompt system.

This module defines a fragment for extracting and formatting UI element interaction
guidance to provide testing recommendations for LLM-driven action generation.
Distinct from system coverage (methods/activities/classes/MOP).

### Architectural Overview:
The CoverageGuidanceFragment serves as the interface between UI element tracking
systems and prompt generation, converting element interaction statistics and action
balance data into guidance that informs testing decisions.

### Core Responsibilities:
- **Element Analysis**: Processes UI element interaction data for testing insights
- **Action Balance**: Analyzes action type distribution to identify testing patterns
- **Priority Guidance**: Identifies untested UI elements for exploration
- **Balance Recommendations**: Provides guidance for UI element testing

### Distinction from System Coverage:
- **System Coverage**: Methods, activities, classes, MOP violations (via COVERAGE_UPDATED events)  
- **UI Element Coverage**: UI elements selected/tested by LLM (this fragment)

### Integration Architecture:
- Integrates with UICoverageTracker for element interaction data
- Uses rv-android-core error handling and logging infrastructure
- Supports both screen-specific and global coverage analysis
- Compatible with existing fragment and template systems

### Design Patterns:
- **Information Extraction**: Converts coverage data to LLM-compatible guidance
- **Analysis Framework**: Provides actionable recommendations for testing
- **Error Isolation**: Error handling to prevent prompt generation failures
- **Context Adaptation**: Guidance based on current testing state
"""

from typing import Any, Dict, Optional

from rv_android_core.constants import UI_COVERAGE_CONSTANTS
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVParsingError
from rv_llm.llm.constants import FragmentType, StateEntry
from rv_llm.llm.prompt.information.base_fragment import InformationFragment
from rvandroid_tool.core.memory.ui_coverage_tracker import UICoverageTracker


class CoverageGuidanceFragment(InformationFragment):
    """Fragment for extracting and formatting UI coverage guidance information.

    ### Architectural Role:
    This fragment serves as the interface between UI coverage tracking systems and
    prompt generation, converting coverage statistics into guidance for LLM testing
    decisions.

    ### Processing Strategy:
    - Analyzes element coverage statistics for exploration guidance
    - Evaluates action type distribution to identify testing patterns
    - Provides priority recommendations for untested elements
    - Generates testing strategies for coverage

    ### Integration Points:
    - Consumes coverage data from UICoverageTracker instances
    - Integrates with rv-android-core error handling and logging systems
    - Supports screen-specific and global coverage analysis modes
    - Delivers formatted guidance for template-based prompt generation
    """

    def __init__(self, ui_coverage_tracker: Optional[UICoverageTracker] = None, 
                 name: str = "coverage_guidance", priority: int = 90):
        """Initialize the coverage guidance fragment with tracking infrastructure.

        Sets up the fragment processing pipeline including UI coverage tracking
        integration, error handling, and logging systems for coverage guidance
        generation.

        Args:
            ui_coverage_tracker: The UICoverageTracker instance for data access
            name: The name of the fragment (default: "coverage_guidance")
            priority: The priority of the fragment (default: 90)
        """
        super().__init__(name, priority)

        self.ui_coverage_tracker = ui_coverage_tracker
        self.logger.logger.name = "rvandroid_tool.llm.prompt.coverage_guidance_fragment"

        # Configuration for guidance generation using constants
        self.min_actions_for_balance_analysis = UI_COVERAGE_CONSTANTS.MIN_ACTIONS_FOR_BALANCE_ANALYSIS
        self.untested_priority_threshold = UI_COVERAGE_CONSTANTS.UNTESTED_PRIORITY_THRESHOLD

        self.logger.debug("Initialized CoverageGuidanceFragment for testing guidance")

    @ErrorHandler.handle_errors(component="CoverageGuidanceFragment", phase="generation", reraise=True)
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Generate coverage guidance information for testing strategy.

        Analyzes UI coverage data and action balance statistics to generate
        recommendations for LLM testing decisions. Implements validation and error
        handling for reliable guidance generation.

        Args:
            state: The current application state containing UI and coverage information
            context: Additional context information for guidance customization

        Returns:
            A formatted string containing strategic testing guidance
            
        Raises:
            RVParsingError: If state validation fails or coverage tracker unavailable
        """
        if not state:
            raise RVParsingError(
                "State dictionary is empty or None",
                parser_type="CoverageGuidanceFragment"
            )

        if not self.ui_coverage_tracker:
            return self._generate_basic_guidance()

        guidance_parts = []

        # Get screen hash for context-specific analysis
        screen_hash = self.ui_coverage_tracker.compute_screen_hash(state)
        
        # Generate element coverage guidance
        coverage_guidance = self._generate_coverage_guidance(screen_hash)
        if coverage_guidance:
            guidance_parts.append(coverage_guidance)

        # Generate action balance guidance
        balance_guidance = self._generate_action_balance_guidance()
        if balance_guidance:
            guidance_parts.append(balance_guidance)

        # Generate priority guidance for systematic exploration
        priority_guidance = self._generate_priority_guidance(screen_hash)
        if priority_guidance:
            guidance_parts.append(priority_guidance)

        # Generate final guidance output
        if guidance_parts:
            final_guidance = " | ".join(guidance_parts)
            self.logger.debug(f"Generated coverage guidance with {len(guidance_parts)} recommendations")
            return final_guidance
        else:
            self.logger.debug("No specific coverage guidance generated")
            return self._generate_basic_guidance()

    @ErrorHandler.handle_errors(
        component="CoverageGuidanceFragment", 
        phase="coverage_analysis",
        default_return=""
    )
    def _generate_coverage_guidance(self, screen_hash: Optional[str]) -> str:
        """Generate element coverage guidance for systematic exploration.

        Analyzes element coverage statistics to provide strategic recommendations
        for systematic testing progress and element prioritization.

        Args:
            screen_hash: Screen identifier for context-specific analysis

        Returns:
            Coverage guidance string or empty string if no guidance available
        """
        if not screen_hash:
            return ""

        # Get UI element interaction statistics for current screen
        stats = self.ui_coverage_tracker.get_ui_element_stats(screen_hash)

        if stats.total_elements == 0:
            return ""

        # Generate UI element interaction status summary
        coverage_summary = (f"UI Elements: {stats.tested_elements}/{stats.total_elements} "
                          f"tested ({stats.coverage_percentage:.0f}%)")

        # Add priority recommendations based on coverage status
        if stats.untested_elements == 0:
            return f"{coverage_summary} - {UI_COVERAGE_CONSTANTS.GUIDANCE_ALL_TESTED}"
        elif stats.untested_elements <= 3:
            return f"{coverage_summary} - {UI_COVERAGE_CONSTANTS.GUIDANCE_COMPLETE_REMAINING} {stats.untested_elements} [UNTESTED] elements"
        elif stats.untested_elements >= self.untested_priority_threshold:
            return f"{coverage_summary} - {UI_COVERAGE_CONSTANTS.GUIDANCE_SYSTEMATIC_EXPLORATION}"
        else:
            return coverage_summary

    @ErrorHandler.handle_errors(
        component="CoverageGuidanceFragment", 
        phase="balance_analysis",
        default_return=""
    )
    def _generate_action_balance_guidance(self) -> str:
        """Generate action type balance recommendations for comprehensive testing.

        Analyzes action type distribution to identify testing bias and provide
        recommendations for more balanced and comprehensive testing coverage.

        Returns:
            Action balance guidance string or empty string if insufficient data
        """
        # Get balance guidance from tracker
        balance_guidance = self.ui_coverage_tracker.get_action_balance_guidance()
        
        # Filter out basic/default messages when no specific guidance needed
        if UI_COVERAGE_CONSTANTS.GUIDANCE_GOOD_BALANCE in balance_guidance:
            return ""
        elif UI_COVERAGE_CONSTANTS.GUIDANCE_VARY_ACTIONS in balance_guidance:
            # Only show generic advice if we have minimal actions
            total_actions = sum(self.ui_coverage_tracker.action_type_counts.values())
            if total_actions < self.min_actions_for_balance_analysis:
                return balance_guidance
            else:
                return ""  # Don't show generic advice with sufficient data

        # Return specific guidance recommendations
        return balance_guidance

    @ErrorHandler.handle_errors(
        component="CoverageGuidanceFragment", 
        phase="priority_analysis",
        default_return=""
    )
    def _generate_priority_guidance(self, screen_hash: Optional[str]) -> str:
        """Generate priority guidance for systematic element exploration.

        Identifies high-priority elements and testing strategies based on
        current screen context and element coverage analysis.

        Args:
            screen_hash: Screen identifier for context-specific analysis

        Returns:
            Priority guidance string or empty string if no priorities identified
        """
        if not screen_hash:
            return ""

        # Get untested elements for prioritization
        untested_elements = self.ui_coverage_tracker.get_untested_elements(screen_hash)
        
        if not untested_elements:
            return ""

        untested_count = len(untested_elements)
        
        # Generate priority recommendations based on untested element count
        if untested_count == 1:
            return "Priority: 1 [UNTESTED] element available"
        elif untested_count <= 3:
            return f"Priority: {untested_count} [UNTESTED] elements available"
        elif untested_count >= self.untested_priority_threshold:
            return f"Priority: {untested_count} [UNTESTED] elements - systematic exploration recommended"
        else:
            return f"Priority: {untested_count} [UNTESTED] elements available"

    @ErrorHandler.handle_errors(
        component="CoverageGuidanceFragment", 
        phase="basic_guidance_generation",
        default_return="Systematic Exploration: Test all visible UI elements comprehensively"
    )
    def _generate_basic_guidance(self) -> str:
        """Generate basic guidance when coverage tracker is unavailable.

        Provides fundamental systematic testing recommendations when detailed
        coverage tracking is not available or functional.

        Returns:
            Basic systematic testing guidance string
        """
        return ("Exploration: Test all visible UI elements | "
                f"Action Balance: {UI_COVERAGE_CONSTANTS.GUIDANCE_VARY_ACTIONS} | "
                "Priority: Focus on [M] and [DM] elements during exploration")

    @ErrorHandler.handle_errors(component="CoverageGuidanceFragment", phase="inclusion_check")
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if coverage guidance information should be included in prompt generation.

        Validates state content and coverage tracker availability to ensure meaningful
        guidance data can be generated for prompt inclusion. Always includes guidance
        to provide testing recommendations.

        Args:
            state: The current application state to validate
            context: Additional context information for inclusion decisions

        Returns:
            True if guidance should be included (default: always include for testing)
        """
        if not state:
            self.logger.debug("Coverage guidance not included: empty state")
            return False

        # Check context preference for coverage guidance
        if context and context.get("coverage_guidance_enabled") is False:
            self.logger.debug("Coverage guidance disabled by context configuration")
            return False

        # Always include guidance for testing support
        self.logger.debug("Including coverage guidance for testing")
        return True