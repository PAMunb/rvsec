"""System coverage information fragment for the prompt system.

This module defines a fragment for extracting and formatting system coverage
information (methods, activities, classes, MOP violations) to provide testing
context for LLM-driven action generation. This is distinct from UI element
coverage tracking.

### Architectural Overview:
The SystemCoverageFragment serves as the interface between system coverage
tracking (rv-coverage) and prompt generation, converting coverage metrics and
MOP violation data into formatted context for all testing strategies.

### Core Responsibilities:
- **System Metrics**: Processes method, activity, and class coverage percentages
- **MOP Violations**: Formats MOP error information for LLM context
- **Coverage Context**: Provides coverage progression information
- **Universal Access**: Ensures all strategies have access to system coverage data

### Integration Architecture:
- Integrates with rv-coverage system via COVERAGE_UPDATED events
- Uses rv-android-core error handling and logging infrastructure
- Provides coverage context for all prompt strategies (single, batch, vision)
- Compatible with both stateless and rich context modes

### Distinction from UI Element Coverage:
- **System Coverage**: Methods, activities, classes, MOP violations (this fragment)
- **UI Element Coverage**: UI elements selected/tested by LLM (CoverageGuidanceFragment)
"""

from typing import Any, Dict, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVParsingError
from rv_llm.llm.constants import FragmentType, StateEntry
from rv_llm.llm.prompt.information.base_fragment import InformationFragment


class SystemCoverageFragment(InformationFragment):
    """Fragment for extracting and formatting system coverage information.

    ### Architectural Role:
    This fragment serves as the interface between system coverage tracking
    and prompt generation, converting coverage metrics and MOP violation data
    into formatted context for LLM testing decisions.

    ### Processing Strategy:
    - Analyzes system coverage metrics from rv-coverage events
    - Formats MOP violation information for testing context
    - Provides coverage progression data for strategy decisions
    - Ensures consistent coverage data across all strategies

    ### Integration Points:
    - Consumes coverage metrics from COVERAGE_UPDATED events
    - Integrates with rv-android-core error handling and logging systems
    - Provides coverage data for all prompt strategies uniformly
    - Delivers formatted coverage context for template generation
    """

    def __init__(self, name: str = "system_coverage", priority: int = 95):
        """Initialize the system coverage fragment with infrastructure.

        Sets up the fragment processing pipeline for system coverage data
        extraction and formatting for LLM context generation.

        Args:
            name: The name of the fragment (default: "system_coverage")
            priority: The priority of the fragment (default: 95 - high priority for context)
        """
        super().__init__(name, priority)

        self.logger.logger.name = "rvsmart_tool.llm.prompt.system_coverage_fragment"

        self.logger.debug("Initialized SystemCoverageFragment for coverage context")

    @ErrorHandler.handle_errors(component="SystemCoverageFragment", phase="generation", reraise=True)
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Generate system coverage information for testing context.

        Analyzes system coverage metrics and MOP violation data to generate
        formatted context information for LLM testing decisions across all
        strategies.

        Args:
            state: The current application state containing coverage information
            context: Additional context information for formatting

        Returns:
            A formatted string containing system coverage context
            
        Raises:
            RVParsingError: If state validation fails or contains invalid data
        """
        if not state:
            raise RVParsingError(
                "State dictionary is empty or None",
                parser_type="SystemCoverageFragment"
            )

        coverage_parts = []

        # Process system coverage metrics
        coverage_info = self._generate_coverage_metrics(state)
        if coverage_info:
            coverage_parts.append(coverage_info)

        # Process MOP violation information
        mop_info = self._generate_mop_violations(state)
        if mop_info:
            coverage_parts.append(mop_info)

        # Generate final coverage output
        if coverage_parts:
            final_coverage = "\n".join(coverage_parts)
            self.logger.debug(f"Generated system coverage with {len(coverage_parts)} sections")
            return final_coverage
        else:
            self.logger.debug("No system coverage information available")
            return ""

    @ErrorHandler.handle_errors(
        component="SystemCoverageFragment", 
        phase="metrics_processing",
        default_return=""
    )
    def _generate_coverage_metrics(self, state: Dict[str, Any]) -> str:
        """Generate system coverage metrics information.

        Processes coverage metrics from rv-coverage system to provide
        testing context about method, activity, and class coverage.

        Args:
            state: The current application state

        Returns:
            Formatted coverage metrics string or empty string if no data
        """
        coverage_metrics = state.get(StateEntry.COVERAGE_METRICS)
        if not coverage_metrics:
            return ""

        try:
            method_coverage = coverage_metrics.get("method_coverage", 0.0)
            activity_coverage = coverage_metrics.get("activity_coverage", 0.0)
            mop_coverage = coverage_metrics.get("mop_method_coverage", 0.0)
            unique_errors = coverage_metrics.get("unique_errors", 0)

            coverage_line = (f"COVERAGE: Methods {method_coverage:.1f}% | "
                           f"Activities {activity_coverage:.1f}% | "
                           f"MOP {mop_coverage:.1f}%")
            
            if unique_errors > 0:
                coverage_line += f" | **MOP Violations: {unique_errors}**"

            return coverage_line

        except Exception as e:
            self.logger.warning(f"Error formatting coverage metrics: {e}")
            return ""

    @ErrorHandler.handle_errors(
        component="SystemCoverageFragment", 
        phase="mop_violations_processing",
        default_return=""
    )
    def _generate_mop_violations(self, state: Dict[str, Any]) -> str:
        """Generate MOP violation information for testing context.

        Processes recent MOP violations to provide specific testing context
        about security and API monitoring violations.

        Args:
            state: The current application state

        Returns:
            Formatted MOP violations string or empty string if no violations
        """
        mop_errors = state.get(StateEntry.MOP_RECENT_ERRORS)
        if not mop_errors:
            return ""

        try:
            violation_lines = ["**RECENT MOP VIOLATIONS:**"]
            
            for error in mop_errors:
                if isinstance(error, dict):
                    spec = error.get("spec", "unknown")
                    class_name = error.get("class_full_name", "unknown")
                    method = error.get("method", "unknown")
                    message = error.get("message", "")
                    
                    violation_lines.append(f"- {spec}: {class_name}.{method} - {message}")
                else:
                    # Handle string or other formats
                    violation_lines.append(f"- {str(error)}")

            return "\n".join(violation_lines)

        except Exception as e:
            self.logger.warning(f"Error formatting MOP violations: {e}")
            return ""

    @ErrorHandler.handle_errors(component="SystemCoverageFragment", phase="inclusion_check")
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if system coverage information should be included in prompt generation.

        Validates state content to ensure meaningful coverage data is available for
        prompt inclusion. Includes coverage data when available to provide context
        for all testing strategies.

        Args:
            state: The current application state to validate
            context: Additional context information for inclusion decisions

        Returns:
            True if system coverage information is available, False otherwise
        """
        if not state:
            self.logger.debug("System coverage not included: empty state")
            return False

        # Check for coverage metrics
        if StateEntry.COVERAGE_METRICS in state:
            coverage_metrics = state[StateEntry.COVERAGE_METRICS]
            if coverage_metrics and isinstance(coverage_metrics, dict):
                self.logger.debug("Including system coverage metrics")
                return True

        # Check for MOP violations
        if StateEntry.MOP_RECENT_ERRORS in state:
            mop_errors = state[StateEntry.MOP_RECENT_ERRORS]
            if mop_errors:
                self.logger.debug("Including MOP violation information")
                return True

        # No system coverage information found
        self.logger.debug("No system coverage information found for inclusion")
        return False