# RV-Screen-Parser Module

Comprehensive Android screen parsing framework with multi-source support, visitor pattern architecture, and integrated screenshot analysis capabilities for advanced UI testing and analysis.

## Overview

The RV-Screen-Parser module provides a complete framework for parsing Android screen state data and analyzing screenshots within the RV-Android ecosystem. It transforms diverse input formats (DroidBot JSON, UIAutomator XML) into standardized ScreenDescription objects while providing advanced screenshot analysis capabilities through Pydantic v2 models for visual element detection and UI hierarchy enhancement.

### Key Features

- **Multi-Source Parsing**: Support for DroidBot JSON and UIAutomator2 XML formats with extensible architecture
- **Screenshot Analysis**: Comprehensive visual analysis system with error detection, button recognition, and interactive element identification
- **Visitor Pattern**: Flexible element processing strategies with multiple visitor implementations for different analysis needs
- **Pydantic v2 Integration**: Type-safe data models with validation for screenshot analysis results and UI element representation
- **Standardized Output**: Unified ScreenDescription objects with consistent structure across all parsing sources
- **Visual Element Detection**: Advanced computer vision capabilities for detecting UI elements not present in hierarchy
- **Error Indicator Analysis**: Specialized detection of visual error indicators with form field association
- **Architecture Integration**: Built on rv-android-core infrastructure with ErrorHandler decorators and LoggingManager

## Architecture

### Core Components

```
rv-screen-parser/
   src/rv_screen_parser/
      parser/
          screen/
              base_parser.py          # Base class with full infrastructure integration
              droidbot/              # DroidBot-specific parsing
                 droidbot_parser.py
              uiautomator/           # UIAutomator2-specific parsing  
                 uiautomator_parser.py
              visitor/               # Visitor pattern implementation
                 abstract_visitor.py
                 basic_visitor.py
                 default_visitor.py
                 enhanced_visitor.py
                 model.py           # ScreenDescription and UI element models
                 visitor_factory.py
              parser_factory.py      # Factory pattern for parser instantiation
      screenshot/                    # Screenshot analysis system
              screenshot_analyzer.py  # Main analysis engine
              models.py              # Pydantic v2 models for visual elements
              detectors/             # Specialized detection algorithms
                 error_detector.py   # Error indicator detection
                 button_detector.py  # Visual button detection
                 text_detector.py    # OCR text detection
                 interactive_element_detector.py
              preprocessing/         # Image preprocessing utilities
                 image_preprocessor.py
              utils/                 # Geometric and utility functions
                 geometry_utils.py
              converters.py          # Format conversion utilities
              screenshot_manager.py  # Screenshot file management
   tests/                            # Comprehensive test suite with screenshot analysis
```

### Architectural Principles

- **Modular Design**: Separation between screen parsing and screenshot analysis with clear interfaces
- **Pydantic v2 Integration**: Type-safe data models with comprehensive validation for all analysis results
- **Infrastructure Integration**: Full rv-android-core ErrorHandler decorators and LoggingManager integration
- **Factory Pattern**: Parser and detector creation through factory pattern with configuration support
- **Visitor Pattern**: Flexible element processing through multiple visitor strategies
- **Computer Vision Pipeline**: Modular detection system with specialized algorithms for different element types
- **Error Handling**: Comprehensive error isolation and recovery for robust analysis operations

### Integration Points

- **rv-android-core**: Uses BaseScreenParser infrastructure, ErrorHandler decorators, LoggingManager, and domain models
- **rv-agent**: Consumes parsed screen data for LLM-driven testing and exploration
- **rv-experiment**: Provides screen parsing and analysis components for experiment orchestration
- **Testing Tools Integration**: Supports parsing of screen data from various testing tools for unified analysis
- **Factory Pattern**: Dynamic parser and detector selection through factory systems
- **Visitor Pattern**: Flexible UI element processing strategies
- **Visual Analysis Pipeline**: Screenshot analysis integration with UI hierarchy processing

## Installation

```bash
# From the modules directory
cd rv-screen-parser
uv sync
```

## Usage

### Basic Parser Usage

```python
from rv_screen_parser.parser.screen.droidbot.droidbot_parser import DroidBotParser
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser

# DroidBot parsing
droidbot_parser = DroidBotParser()
screen_data = droidbot_parser.parse_screen(droidbot_state_data)

# UIAutomator2 parsing
uiautomator_parser = UIAutomator2Parser()
screen_data = uiautomator_parser.parse_screen(xml_hierarchy_data)
```

### Screenshot Analysis Usage

```python
from rv_screen_parser.screenshot.screenshot_analyzer import ScreenshotAnalyzer

# Analyze screenshot for visual elements
analyzer = ScreenshotAnalyzer(image_path="/path/to/screenshot.png")
analysis_result = analyzer.extract_information()

# Access typed Pydantic models
error_indicators = analysis_result["error_indicators"]  # List[ErrorIndicator]
visual_buttons = analysis_result["buttons"]            # List[DetectedButton]
text_elements = analysis_result["texts"]               # List[DetectedText]
interactive_elements = analysis_result["interactive_elements"]  # List[InteractiveElement]
```

### Factory Pattern Usage

```python
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.constants import ScreenParserType

# Register default parsers
ParserFactory.register_default_parsers()

# Create parser dynamically
parser = ParserFactory.create(ScreenParserType.DROIDBOT)
screen_data = parser.parse_screen(state_data)
```

### Custom Visitor Usage

```python
from rv_screen_parser.parser.screen.visitor.enhanced_visitor import EnhancedTextVisitor

# Use custom visitor for specialized processing
parser = DroidBotParser(visitor_class=EnhancedTextVisitor)
screen_data = parser.parse_screen(state_data, static_analysis_data)
```

### Integrated Analysis Usage

```python
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.constants import ScreenParserType
from rv_screen_parser.screenshot.screenshot_analyzer import ScreenshotAnalyzer

# Complete UI analysis with both hierarchy and visual data
parser = ParserFactory.create(ScreenParserType.DROIDBOT)
screen_description = parser.parse_screen(state_data, static_data)

# Enhance with screenshot analysis
analyzer = ScreenshotAnalyzer(image_path=screenshot_path)
visual_analysis = analyzer.extract_information()

# Combined analysis provides complete UI understanding
enhanced_context = {
    "hierarchy": screen_description,
    "visual_elements": visual_analysis
}
```

## Supported Input Formats

### Screen Hierarchy Parsing

#### DroidBot Format
- **Input**: JSON state data from DroidBot monitoring
- **Features**: Activity extraction, view tree parsing, stack information processing
- **Specializations**: Handles DroidBot-specific hierarchy and activity naming conventions

#### UIAutomator2 Format
- **Input**: XML hierarchy dumps from UIAutomator2
- **Features**: Complete XML tree parsing, attribute normalization, coordinate processing
- **Specializations**: System navigation filtering, performance-optimized XML processing

### Screenshot Analysis

#### Image Formats
- **Supported**: PNG, JPEG, BMP, TIFF
- **Features**: Multi-format image loading with automatic preprocessing
- **Optimization**: Memory-efficient processing for large screenshots

#### Visual Element Detection
- **Error Indicators**: Color-based, icon-based, text-based, and dialog error detection
- **Button Detection**: Shape analysis, text recognition, and confidence scoring
- **Text Elements**: OCR integration with confidence metrics and positioning
- **Interactive Elements**: Game UI detection including joysticks, sliders, and D-pads

## Design Patterns

### Visitor Pattern for UI Processing

The module implements a visitor pattern for flexible UI element processing:

#### Available Visitors

- **AbstractScreenVisitor**: Base visitor interface with infrastructure integration
- **BasicTextVisitor**: Simple text-based element processing
- **DefaultTextVisitor**: Standard visitor with element handling and action generation
- **EnhancedTextVisitor**: Visitor with static analysis integration and enhanced features

#### Creating Custom Visitors

```python
from rv_screen_parser.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, Node

class CustomVisitor(AbstractScreenVisitor):
    def __init__(self, static_info, activity):
        super().__init__(static_info, activity)
        # Custom initialization
    
    def visit_node(self, node: Node) -> None:
        # Custom node processing logic
        pass
    
    def get_screen_description(self) -> ScreenDescription:
        # Return processed screen description
        return self.screen_description
```

### Pydantic v2 Data Models

The screenshot analysis system uses strongly-typed Pydantic models:

#### Core Models

```python
from rv_screen_parser.screenshot.models import (
    ErrorIndicator, DetectedButton, DetectedText, InteractiveElement,
    ScreenshotAnalysisResult, DetectionMethod, ErrorType
)

# Type-safe error indicator with validation
error = ErrorIndicator(
    x=100, y=150, width=200, height=30,
    detection_method=DetectionMethod.COLOR,
    confidence=0.85,
    error_type=ErrorType.VALIDATION_ERROR,
    text="Field is required"
)

# Visual button with geometric properties
button = DetectedButton(
    x=50, y=200, width=120, height=40,
    confidence=0.92,
    detection_method=DetectionMethod.SHAPE,
    text="Submit"
)
```

## Integration with RV-Android Core

The module is fully integrated with the RV-Android core infrastructure:

### Error Handling
```python
# Automatic error handling through ErrorHandler
try:
    screen_data = parser.parse_screen(invalid_data)
except Exception as e:
    # Errors are automatically logged and handled by ErrorHandler
    pass
```

### Logging
```python
# Standardized logging through LoggingManager
parser = DroidBotParser()
# Logging context automatically set with component information
parser.logger.info("Processing DroidBot state data")
```

### Static Analysis Integration
```python
from rv_android_core.domain.static import StaticAnalysisData

# Enhanced parsing with static analysis context
static_data = StaticAnalysisData(...)
screen_data = parser.parse_screen(state_data, static_data)
```

## Testing

The module includes a comprehensive test suite covering all functionality:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run specific test categories
uv run pytest tests/parser/screen/droidbot/
uv run pytest tests/parser/screen/uiautomator/
uv run pytest tests/parser/screen/visitor/
uv run pytest tests/analysis/screenshot/
```

### Test Coverage

- **Parser Implementations**: Complete coverage of DroidBot and UIAutomator2 parsers
- **Visitor Pattern**: All visitor implementations and factory functionality
- **Screenshot Analysis**: Comprehensive testing of visual element detection algorithms
- **Pydantic Models**: Validation testing for all data models and edge cases
- **Integration Testing**: Cross-component integration and factory pattern testing
- **Edge Cases**: Malformed data, missing elements, error conditions, invalid images
- **Performance Testing**: Memory efficiency and processing speed validation

## Performance Characteristics

### Screen Parsing Performance
- **Memory Efficient**: Optimized for processing large UI hierarchies with minimal memory footprint
- **Fast Processing**: Streamlined parsing algorithms for real-time monitoring applications
- **Scalable Architecture**: Handles complex nested UI structures efficiently
- **Thread Safe**: Safe for concurrent usage in multi-threaded environments

### Screenshot Analysis Performance
- **Optimized Computer Vision**: Efficient image processing with configurable quality vs speed trade-offs
- **Memory Management**: Intelligent image preprocessing to handle large screenshots
- **Parallel Processing**: Multi-threaded detection algorithms for improved performance
- **Caching Support**: Intelligent caching of analysis results for repeated operations

## Dependencies

### Runtime Dependencies
- `rv-android-core`: Core framework components (ErrorHandler, LoggingManager, domain models)
- `pydantic`: Type-safe data models with validation (v2)
- `opencv-python`: Computer vision operations for screenshot analysis
- `numpy`: Numerical operations for image processing
- `pillow`: Image loading and manipulation
- `pytesseract`: OCR capabilities for text detection
- `lxml`: High-performance XML processing for UIAutomator2 parsing
- `beautifulsoup4`: Alternative HTML/XML parsing support

### Development Dependencies
- `pytest`: Testing framework
- `pytest-cov`: Coverage reporting
- `pytest-mock`: Mocking utilities for testing

## Configuration

The module uses the standardized RV-Android configuration approach:

```python
# Parsers automatically inherit logging and error handling configuration
# from rv-android-core LoggingManager and ErrorHandler instances

# Custom visitor configuration
visitor_config = {
    'filter_system_ui': True,
    'extract_coordinates': True,
    'normalize_attributes': True
}

# Screenshot analysis configuration
analysis_config = {
    'enable_error_detection': True,
    'enable_button_detection': True,
    'enable_text_detection': True,
    'enable_interactive_detection': True,
    'confidence_threshold': 0.7,
    'preprocessing_enabled': True
}

# Initialize with configuration
analyzer = ScreenshotAnalyzer(
    image_path="screenshot.png",
    config=analysis_config
)
```

## Extension Points

### Adding New Parser Types

1. **Implement BaseScreenParser**:
```python
class NewFormatParser(BaseScreenParser[ScreenDescription]):
    def __init__(self, visitor_class=None):
        super().__init__("new_format", visitor_class)
    
    def _parse_implementation(self, state_data, static_data, activity):
        # Implementation specific logic
        pass
```

2. **Register with Factory**:
```python
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.constants import ScreenParserType

# Register new parser type
ParserFactory.register_parser_type("new_format", NewFormatParser)
```

### Adding New Detection Algorithms

1. **Implement Detection Algorithm**:
```python
from rv_screen_parser.screenshot.models import BaseValidatedModel
from typing import List, Dict, Any

class CustomDetector:
    def detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        # Custom detection logic
        detected_elements = []
        # Process image and populate detected_elements
        return detected_elements
```

2. **Integrate with ScreenshotAnalyzer**:
```python
from rv_screen_parser.screenshot.screenshot_analyzer import ScreenshotAnalyzer

class EnhancedScreenshotAnalyzer(ScreenshotAnalyzer):
    def __init__(self, image_path: str):
        super().__init__(image_path)
        self.custom_detector = CustomDetector()
    
    def extract_information(self) -> Dict[str, Any]:
        result = super().extract_information()
        result["custom_elements"] = self.custom_detector.detect(self.image)
        return result
```

### Adding New Pydantic Models

1. **Create Type-Safe Model**:
```python
from rv_screen_parser.screenshot.models import BaseValidatedModel
from pydantic import Field
from typing import Optional

class CustomElement(BaseValidatedModel):
    x: int = Field(..., ge=0, description="Element X coordinate")
    y: int = Field(..., ge=0, description="Element Y coordinate")
    width: int = Field(..., gt=0, description="Element width")
    height: int = Field(..., gt=0, description="Element height")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    custom_property: Optional[str] = Field(None, description="Custom element property")
```

### Adding New Visitor Types

1. **Implement AbstractScreenVisitor**:
```python
class SpecializedVisitor(AbstractScreenVisitor):
    # Implementation with enhanced capabilities
    pass
```

2. **Register with VisitorFactory**:
```python
from rv_screen_parser.parser.screen.visitor.visitor_factory import VisitorFactory

VisitorFactory.register_visitor_type("specialized", SpecializedVisitor)
```

## Contributing

### Development Guidelines

1. **Architecture Compliance**: Follow established patterns from ExecutionManager, TaskExecutor
2. **Error Handling**: Use ErrorHandler for all error management
3. **Logging**: Use LoggingManager with appropriate context
4. **Documentation**: Include detailed architectural comments in English
5. **Testing**: Maintain 100% test coverage for new functionality

### Code Style

- **Language**: All code and comments in English
- **Type Annotations**: Comprehensive type hints required
- **Documentation**: Follow established architectural comment patterns
- **Error Handling**: Use centralized ErrorHandler infrastructure

## License

This module is part of the RV-Android project and follows the same licensing terms.