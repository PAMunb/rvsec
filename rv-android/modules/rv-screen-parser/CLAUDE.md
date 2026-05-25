# CLAUDE.md - rv-screen-parser

## Purpose

The rv-screen-parser module provides Android UI parsing capabilities for the RV-Android framework. It parses screen state data from multiple sources (DroidBot, UIAutomator) into standardized `ScreenDescription` objects, enabling consistent UI element analysis and interaction across the framework. The module also includes screenshot analysis capabilities using computer vision (OpenCV) and OCR (Tesseract) for detecting UI elements not visible in the UI hierarchy.

## Architecture

The module is built around two main subsystems:

1. **UI Hierarchy Parsing**: Transforms XML/JSON screen state data into standardized models using the visitor pattern
2. **Screenshot Analysis**: Detects visual UI elements (buttons, text, errors, interactive elements) through image processing

### Key Components

#### Parser Subsystem

| Component | File | Description |
|-----------|------|-------------|
| `BaseScreenParser` | `parser/screen/base_parser.py` | Abstract base class implementing factory pattern for screen parsing |
| `UIAutomator2Parser` | `parser/screen/uiautomator/uiautomator_parser.py` | Parses UIAutomator2 XML hierarchy dumps |
| `DroidBotParser` | `parser/screen/droidbot/droidbot_parser.py` | Parses DroidBot JSON state data (view_tree format) |
| `ParserFactory` | `parser/screen/parser_factory.py` | Factory for dynamic parser instantiation by type |

#### Visitor Subsystem

| Component | File | Description |
|-----------|------|-------------|
| `AbstractScreenVisitor` | `parser/screen/visitor/abstract_visitor.py` | Abstract base implementing visitor pattern for UI traversal |
| `BasicTextVisitor` | `parser/screen/visitor/basic_visitor.py` | Compact descriptions optimized for LLM token efficiency (~69% reduction) |
| `DefaultTextVisitor` | `parser/screen/visitor/default_visitor.py` | Standard visitor with default features |
| `EnhancedTextVisitor` | `parser/screen/visitor/enhanced_visitor.py` | Comprehensive analysis with detailed coordinate information |
| `VisitorFactory` | `parser/screen/visitor/visitor_factory.py` | Factory for creating visitor instances by type |

#### Screenshot Analysis Subsystem

| Component | File | Description |
|-----------|------|-------------|
| `ScreenshotAnalyzer` | `screenshot/screenshot_analyzer.py` | Main orchestrator for visual analysis |
| `TextDetector` | `screenshot/detectors/text_detector.py` | OCR-based text extraction using Tesseract |
| `ButtonDetector` | `screenshot/detectors/button_detector.py` | Visual button detection using shape analysis |
| `ErrorDetector` | `screenshot/detectors/error_detector.py` | Detects error indicators (dialogs, icons, text) |
| `InteractiveElementDetector` | `screenshot/detectors/interactive_element_detector.py` | Detects game UI elements (joysticks, sliders, D-pads) |
| `ImagePreprocessor` | `screenshot/preprocessing/image_preprocessor.py` | Image preprocessing (grayscale, binary conversion) |

#### Data Models

| Model | File | Description |
|-------|------|-------------|
| `Node` | `parser/screen/visitor/model.py` | Hierarchical UI element with visitor pattern support |
| `ScreenItem` | `parser/screen/visitor/model.py` | UI element with description and available actions |
| `ItemAction` | `parser/screen/visitor/model.py` | Executable action with coordinates and MOP tracking |
| `ScreenDescription` | `parser/screen/visitor/model.py` | Complete screen state with all elements and actions |
| `ScreenshotAnalysisResult` | `screenshot/models.py` | Visual analysis results with detected elements |

## Directory Structure

```
modules/rv-screen-parser/
├── src/rv_screen_parser/
│   ├── constants.py              # ScreenParserType, VisitorType, ActionType enums
│   ├── parser/
│   │   └── screen/
│   │       ├── base_parser.py    # Abstract base class for parsers
│   │       ├── parser_factory.py # Parser factory pattern
│   │       ├── droidbot/
│   │       │   └── droidbot_parser.py
│   │       ├── uiautomator/
│   │       │   └── uiautomator_parser.py
│   │       └── visitor/
│   │           ├── abstract_visitor.py
│   │           ├── basic_visitor.py
│   │           ├── default_visitor.py
│   │           ├── enhanced_visitor.py
│   │           ├── model.py      # Node, ScreenItem, ItemAction, ScreenDescription
│   │           └── visitor_factory.py
│   └── screenshot/
│       ├── models.py             # Pydantic models for visual analysis
│       ├── screenshot_analyzer.py
│       ├── screenshot_manager.py
│       ├── converters.py
│       ├── detectors/
│       │   ├── button_detector.py
│       │   ├── error_detector.py
│       │   ├── interactive_element_detector.py
│       │   └── text_detector.py
│       ├── preprocessing/
│       │   └── image_preprocessor.py
│       └── utils/
│           └── geometry_utils.py
└── tests/
    ├── parser/screen/
    │   ├── droidbot/
    │   ├── uiautomator/
    │   └── visitor/
    ├── analysis/screenshot/
    └── images/                   # Test screenshots
```

## Key Files

| File | Purpose |
|------|---------|
| `parser/screen/visitor/model.py` | Core data models (Node, ScreenItem, ItemAction, ScreenDescription) |
| `parser/screen/visitor/abstract_visitor.py` | Visitor pattern base with MOP tracking and system button filtering |
| `parser/screen/base_parser.py` | Parser base class with error handling and logging |
| `screenshot/screenshot_analyzer.py` | Visual analysis coordinator |
| `screenshot/models.py` | Pydantic models for screenshot analysis results |
| `constants.py` | Type constants (ScreenParserType, VisitorType, ActionType) |

## Dependencies

### Internal

- **rv-android-core**: Foundation infrastructure (domain models, error handling, logging, validation)
  - `StaticAnalysisData`: For MOP (Monitored Operations) tracking
  - `WidgetEventType`: Action type classification
  - `ErrorHandler`: Centralized error handling
  - `LoggingManager`: Standardized logging
  - `BaseValidatedModel`: Pydantic validation base

### External

```toml
# Core parsing
lxml = "^5.3.0"              # XML parsing
beautifulsoup4 = "^4.12.0"   # Alternative XML/HTML parsing
uiautomator2 = "^3.3.1"      # UIAutomator integration

# Screenshot analysis
pytesseract = "^0.3.0"       # OCR functionality
opencv-python = "^4.10.0"    # Computer vision and image processing
pillow = "^10.4.0"           # Image manipulation
numpy = "^2.1.0"             # Numerical operations
pydantic = "^2.9.0"          # Data validation
```

**System Dependencies (Ubuntu)**:
```bash
sudo apt-get install -y tesseract-ocr libtesseract-dev libopencv-dev python3-opencv
```

## Testing

```bash
cd modules/rv-screen-parser
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/ -v
```

### Test Organization

| Directory | Purpose |
|-----------|---------|
| `tests/parser/screen/droidbot/` | DroidBot parser tests |
| `tests/parser/screen/uiautomator/` | UIAutomator parser tests |
| `tests/parser/screen/visitor/` | Visitor implementation tests |
| `tests/analysis/screenshot/` | Screenshot analyzer tests |
| `tests/preprocessing/` | Image preprocessing tests |
| `tests/utils/` | Utility function tests |
| `tests/images/` | Test screenshot fixtures |
| `tests/test_default_visitor.py` | Default visitor tests |
| `tests/test_enhanced_visitor.py` | Enhanced visitor tests |
| `tests/test_error_detector.py` | Error detector tests |
| `tests/test_error_detector_integration.py` | Error detector integration tests |
| `tests/test_real_parsing.py` | Real parsing scenario tests |
| `tests/test_screenshot_manager.py` | Screenshot manager tests |

### Running Specific Tests

```bash
# Parser tests
uv run pytest tests/parser/ -v

# Visitor tests
uv run pytest tests/parser/screen/visitor/ -v

# Screenshot analysis tests
uv run pytest tests/analysis/screenshot/ -v

# With coverage
uv run pytest --cov=src --cov-report=html
```

## Common Tasks

### Parse UIAutomator XML

```python
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.constants import ScreenParserType

# Create parser
parser = ParserFactory.create(ScreenParserType.UIAUTOMATOR)

# Parse XML string
xml_data = "<hierarchy>...</hierarchy>"
screen_desc = parser.parse(xml_data, activity="com.example.MainActivity")

# Access elements
for item in screen_desc.items:
    print(f"{item.description}")
    for action in item.actions:
        print(f"  - {action.text} at {action.get_execution_coordinates()}")
```

### Parse DroidBot State

```python
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.constants import ScreenParserType

parser = ParserFactory.create(ScreenParserType.DROIDBOT)

state_data = {
    "activity": "com.example.MainActivity",
    "view_tree": { ... }  # DroidBot view tree structure
}

screen_desc = parser.parse_screen(state_data)
```

### Use Different Visitor Types

```python
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.parser.screen.visitor.visitor_factory import VisitorFactory
from rv_screen_parser.constants import ScreenParserType, VisitorType

# Get visitor class for compact LLM-optimized output
visitor_class = VisitorFactory.get_visitor_class(VisitorType.BASIC)

# Create parser with specific visitor
parser = ParserFactory.create(ScreenParserType.UIAUTOMATOR, visitor_class=visitor_class)
```

### Analyze Screenshot

```python
from rv_screen_parser.screenshot.screenshot_analyzer import ScreenshotAnalyzer

analyzer = ScreenshotAnalyzer()
result = analyzer.analyze("/path/to/screenshot.png")

# Access detected elements
for text in result.texts:
    print(f"Text: {text.text} at ({text.bbox.center_x}, {text.bbox.center_y})")

for button in result.buttons:
    print(f"Button: {button.text or 'unnamed'} confidence={button.confidence}")

for error in result.error_indicators:
    print(f"Error: {error.error_type} - {error.text}")
```

### Access Action Coordinates

```python
# Get action by ID
action = screen_desc.get_action_by_id(5)

# Get execution coordinates (for clicking)
coords = action.get_execution_coordinates()  # Returns (x, y) tuple

# Get action signature for tracking
signature = action.coords_for_matching  # Returns ((x, y), action_type)

# Get all actions of a specific type
click_actions = screen_desc.get_actions_by_type("click")
text_actions = screen_desc.get_actions_by_type("set_text")
```

### Check MOP (Monitored Operations) Tracking

```python
# Actions track whether they reach monitored operations
for item in screen_desc.items:
    for action in item.actions:
        if action.reaches_target:
            print(f"Action {action.id} reaches monitored operations")
        if action.directly_reaches_target:
            print(f"Action {action.id} DIRECTLY reaches monitored operations")
        if action.widget_id:
            print(f"  Widget ID: {action.widget_id}")
```

## Design Patterns

### Visitor Pattern

The module uses the visitor pattern for flexible UI tree traversal:

1. `Node.accept(visitor)` dispatches to appropriate visitor method based on element type
2. Specialized handlers for each widget type (Button, EditText, CheckBox, etc.)
3. Allows different visitors to produce different output formats (basic, default, enhanced)

### Factory Pattern

Both parsers and visitors use factory patterns:

- `ParserFactory.create(parser_type)` - Creates appropriate parser instance
- `VisitorFactory.create(visitor_type)` - Creates appropriate visitor instance
- Registry pattern allows dynamic registration of new implementations

### Component Architecture (Screenshot Analysis)

Screenshot analysis uses dependency injection with specialized detector components:

- `TextDetector` - OCR-based text extraction
- `ButtonDetector` - Shape-based button detection
- `ErrorDetector` - Error indicator detection (visual + textual)
- `InteractiveElementDetector` - Game UI element detection


## Development Notes

This module is part of the RV-Android uv workspace. All modules are installed in **editable mode** via the root `pyproject.toml`.

**Key points:**
- Run `uv sync` from the project root to install all modules
- Source code changes are reflected immediately (no reinstall needed)
- Only reinstall if `pyproject.toml` dependencies change

```bash
# From project root
uv sync             # Install/update all modules (also removes unused packages)
```

