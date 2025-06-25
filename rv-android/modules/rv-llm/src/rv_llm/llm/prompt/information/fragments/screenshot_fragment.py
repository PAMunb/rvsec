"""Screenshot information fragment for the prompt system.

This module defines a specialized fragment for processing and describing screenshots
from the application state, integrating visual analysis results with UI hierarchy
data to provide comprehensive visual context for LLM-driven testing systems.

### Architectural Overview:
The ScreenshotFragment serves as the interface between visual analysis systems
and prompt generation, processing screenshot paths and visual analysis results
to provide contextual image information and visual element annotations.

### Core Responsibilities:
- **Screenshot Validation**: Verifies screenshot file existence and accessibility
- **Visual Analysis Integration**: Processes error indicators and visual elements
- **UI Enhancement**: Annotates UI elements with visual analysis results
- **Image Context**: Provides screenshot metadata and visual insights

### Integration Architecture:
- Consumes screenshot paths and visual analysis results from state
- Integrates with rv-android-core error handling and logging infrastructure
- Supports visual element association from ScreenshotActionComplementor
- Maintains compatibility with different visual analysis backends

### Design Patterns:
- **Visual Data Processor**: Handles screenshot and visual analysis integration
- **Template Method**: Consistent processing pipeline with specialized validation
- **Error Isolation**: Comprehensive error handling to prevent prompt generation failures
- **Context Enrichment**: Enhances visual understanding through analysis results
"""

import os
from typing import Any, Dict, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.exceptions import RVParsingError
from rv_screen_parser.parser.screen.visitor.model import ScreenItem

from rv_llm.llm.constants import StateEntry
from rv_llm.llm.prompt.information.base_fragment import InformationFragment


class ScreenshotFragment(InformationFragment):
    """Fragment for processing and describing screenshots.
    
    ### Architectural Role:
    This fragment serves as the bridge between visual analysis systems and
    prompt generation, ensuring reliable integration of screenshot information
    and visual analysis results for comprehensive visual context.
    
    ### Processing Strategy:
    - Validates screenshot file existence and accessibility
    - Processes visual analysis results including error indicators
    - Enhances UI elements with visual annotations and confidence data
    - Provides structured visual context for LLM decision making
    
    ### Integration Points:
    - Consumes screenshot paths from application state management
    - Integrates with visual analysis results from ScreenshotActionComplementor
    - Supports model capabilities context for image-enabled models
    - Delivers visual context for template-based prompt generation
    """

    def __init__(
            self,
            name: str = "screenshot",
            priority: int = 600,
            include_image: bool = True
    ):
        """Initialize the screenshot fragment with comprehensive infrastructure.
        
        Sets up the complete fragment processing pipeline including error handling,
        logging, and visual analysis integration systems for robust screenshot processing.
        
        Args:
            name: The name of the fragment (default: "screenshot").
            priority: The priority of the fragment (default: 600).
            include_image: Whether to include the actual image (default: True).
        """
        super().__init__(name, priority)
        
        # Initialize logging infrastructure
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.prompt.screenshot_fragment",
            {CONTEXT_COMPONENT: "ScreenshotFragment"}
        )
        
        # Initialize error handling
        self.error_handler = ErrorHandler.get_instance()
        
        # Configuration for screenshot processing
        self.include_image = include_image
        
        self.logger.debug("Initialized ScreenshotFragment for visual analysis integration")

    @ErrorHandler.handle_errors(component="ScreenshotFragment", phase="generation", reraise=True)
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate screenshot information with visual analysis integration.
        
        Processes screenshot paths and visual analysis results to generate comprehensive
        visual context information for LLM prompt integration. Implements validation
        and error handling for reliable visual data processing.
        
        Args:
            state: The current application state containing screenshot and visual data
            context: Additional context information for processing customization
            
        Returns:
            A dictionary containing screenshot information and visual analysis results
            
        Raises:
            RVParsingError: If state validation fails or contains invalid data
        """
        if not state:
            raise RVParsingError(
                "State dictionary is empty or None",
                parser_type="ScreenshotFragment"
            )

        # Validate screenshot path
        screenshot_path = state.get(StateEntry.SCREENSHOT_PATH)
        if not screenshot_path:
            self.logger.debug("No screenshot path found in state")
            return {}
            
        if not isinstance(screenshot_path, str) or not screenshot_path.strip():
            self.logger.warning(f"Invalid screenshot path format: {screenshot_path}")
            return {}

        if not os.path.exists(screenshot_path):
            self.logger.warning(f"Screenshot file not found: {screenshot_path}")
            return {}

        result = {
            "screenshot_path": screenshot_path,
            "file_exists": True
        }

        # Process visual analysis results if available
        if StateEntry.SCREENSHOT_INFO in state:
            screenshot_info = state[StateEntry.SCREENSHOT_INFO]
            
            if isinstance(screenshot_info, dict):
                self.logger.debug("Processing visual analysis results")
                
                # Process error indicators with enhanced annotations
                error_indicators = screenshot_info.get("error_indicators", [])
                if isinstance(error_indicators, list):
                    high_confidence_errors = 0
                    for error_indicator in error_indicators:
                        if isinstance(error_indicator, dict):
                            confidence = error_indicator.get("confidence", 0)
                            
                            # Enhanced error annotation for high-confidence errors
                            if confidence >= 0.8 and "associated_item" in error_indicator:
                                associated_item = error_indicator["associated_item"]
                                
                                if isinstance(associated_item, ScreenItem):
                                    # Add error annotation to UI element description
                                    if not associated_item.base_description.endswith(" [ERR]"):
                                        associated_item.base_description += " [ERR]"
                                    high_confidence_errors += 1
                                    self.logger.debug(
                                        f"Annotated UI element with error indicator (confidence: {confidence})"
                                    )
                    
                    result["error_indicators_count"] = len(error_indicators)
                    result["high_confidence_errors"] = high_confidence_errors
                
                # Process visual buttons information
                visual_buttons = screenshot_info.get("visual_buttons", [])
                if isinstance(visual_buttons, list):
                    result["visual_buttons_count"] = len(visual_buttons)
                
                # Process analysis metrics
                metrics = screenshot_info.get("metrics", {})
                if isinstance(metrics, dict):
                    result["analysis_metrics"] = metrics
                    
            else:
                self.logger.warning(f"Invalid screenshot_info format: {type(screenshot_info)}")

        # Add file metadata
        try:
            file_stat = os.stat(screenshot_path)
            result["file_size"] = file_stat.st_size
        except OSError as e:
            self.logger.warning(f"Could not get file stats for {screenshot_path}: {e}")

        self.logger.debug(
            f"Generated screenshot information from {screenshot_path} with "
            f"{result.get('error_indicators_count', 0)} error indicators and "
            f"{result.get('visual_buttons_count', 0)} visual buttons"
        )
        return result

    @ErrorHandler.handle_errors(component="ScreenshotFragment", phase="inclusion_check")
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if screenshot information should be included in prompt generation.
        
        Validates state content and model capabilities to ensure screenshot information
        is available and suitable for prompt inclusion. Implements comprehensive validation
        to prevent invalid or inaccessible image data from being included.
        
        Args:
            state: The current application state to validate
            context: Additional context information including model capabilities
            
        Returns:
            True if valid screenshot information is available and supported, False otherwise
        """
        if not state:
            self.logger.debug("Screenshot not included: empty state")
            return False
            
        # Check model capabilities for image support
        if context and "model_capabilities" in context:
            capabilities = context.get("model_capabilities", {})
            if isinstance(capabilities, dict) and not capabilities.get("supports_images", True):
                self.logger.debug("Screenshot not included: model does not support images")
                return False

        # Validate screenshot path
        screenshot_path = state.get(StateEntry.SCREENSHOT_PATH)
        if not screenshot_path:
            self.logger.debug("Screenshot not included: no screenshot path in state")
            return False
            
        if not isinstance(screenshot_path, str) or not screenshot_path.strip():
            self.logger.debug(f"Screenshot not included: invalid path format {type(screenshot_path)}")
            return False

        # Verify file existence and accessibility
        if not os.path.exists(screenshot_path):
            self.logger.debug(f"Screenshot not included: file not found at {screenshot_path}")
            return False
            
        # Check file accessibility
        try:
            if not os.access(screenshot_path, os.R_OK):
                self.logger.debug(f"Screenshot not included: file not readable at {screenshot_path}")
                return False
        except OSError as e:
            self.logger.debug(f"Screenshot not included: access check failed for {screenshot_path}: {e}")
            return False

        # Additional validation for visual analysis context
        has_visual_analysis = StateEntry.SCREENSHOT_INFO in state
        if has_visual_analysis:
            self.logger.debug(f"Including screenshot with visual analysis: {screenshot_path}")
        else:
            self.logger.debug(f"Including screenshot without visual analysis: {screenshot_path}")
            
        return True
