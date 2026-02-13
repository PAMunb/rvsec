# CLAUDE.md - rv-uiautomator

This file provides guidance to Claude Code when working with the rv-uiautomator module.

## Module Overview

rv-uiautomator provides shared UIAutomator components for Android device interaction across RV-Android testing tools. It eliminates code duplication by providing a unified interface for device operations, action execution, and state management.

## Architecture

### Directory Structure

```
rv-uiautomator/
├── src/rv_uiautomator/
│   ├── __init__.py           # Public API exports
│   ├── constants.py          # Configuration constants
│   ├── adapter/              # Device interaction adapters
│   │   ├── base.py           # UIAdapter abstract interface
│   │   └── uiautomator2.py   # UIAutomator2 implementation
│   ├── executor/             # Action execution
│   │   └── action_executor.py # Translates actions to device commands
│   ├── state/                # State format conversion
│   │   └── converter.py      # UIAutomator to DroidBot format conversion
│   └── utils/                # Utility components
│       ├── device_manager.py # ADB device management
│       └── screenshot_manager.py # Screenshot capture and processing
└── tests/
    └── test_adapter.py       # Unit tests
```

### Core Components

#### UIAdapter (Abstract Interface)
- **Location**: `adapter/base.py`
- **Purpose**: Defines standard interface for UI operations across different automation frameworks
- **Key Methods**:
  - `connect(device_id)` - Establish device connection
  - `get_ui_state()` - Capture current UI state (XML hierarchy, activity, package)
  - `click(x, y)`, `long_click(x, y, duration)` - Touch interactions
  - `swipe(x1, y1, x2, y2, duration)` - Gesture support
  - `input_text(text)` - Text input at focused element
  - `press_back()`, `press_home()` - System button presses
  - `take_screenshot()` - Screenshot capture
  - `launch_app(package)`, `stop_app(package)` - Application lifecycle

#### UIAutomator2Adapter
- **Location**: `adapter/uiautomator2.py`
- **Purpose**: Concrete implementation using UIAutomator2 library
- **Features**:
  - Uses `uiautomator2` Python library for device communication
  - Implements all UIAdapter methods with proper error handling
  - Uses ErrorHandler decorator for consistent error management

#### UIAutomatorActionExecutor
- **Location**: `executor/action_executor.py`
- **Purpose**: Translates GeneratedAction objects into device commands
- **Supported Actions**:
  - `CLICK` - Click at coordinates
  - `LONG_CLICK` - Long click with configurable duration
  - `TEXT_CHANGE` - Text input with optional click to focus
  - `SCROLL` - Swipe with direction (up/down/left/right) and distance
  - `BACK` - System back button
  - Custom coordinate actions (from vision strategy)

#### StateConverter
- **Location**: `state/converter.py`
- **Purpose**: Converts UIAutomator state format to DroidBot-compatible format
- **Mapping**:
  - `xml` -> `hierarchy` and `view_tree`
  - `current_activity` -> `activity`
  - `current_package` -> `package_name`
- **Additional Features**:
  - `compute_screen_hash()` - Generates hash for state identification

#### DeviceManager
- **Location**: `utils/device_manager.py`
- **Purpose**: ADB-based device discovery and management
- **Features**:
  - `get_available_devices()` - List connected devices
  - `verify_device_connection()` - Check device responsiveness
  - `get_device_info()` - Retrieve device properties (model, Android version, resolution)
  - `restart_adb_server()` - Recovery from connection issues

#### ScreenshotManager
- **Location**: `utils/screenshot_manager.py`
- **Purpose**: Screenshot capture, processing, and storage management
- **Features**:
  - `generate_screenshot_path()` - Unique timestamped paths
  - `optimize_screenshot()` - Image compression and format conversion
  - `validate_screenshot()` - Verify image integrity
  - `cleanup_old_screenshots()` - Disk space management

## Dependencies

- **rv-android-core**: Foundation infrastructure (ErrorHandler, LoggingManager)
- **rv-screen-parser**: UI parsing capabilities
- **uiautomator2**: UIAutomator2 Python bindings
- **pillow**: Image processing for screenshots

## Configuration Constants

Defined in `constants.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `DEFAULT_CONNECTION_TIMEOUT` | 30 | Device connection timeout (seconds) |
| `DEFAULT_DEVICE_ID` | "emulator-5554" | Default emulator device |
| `ACTION_EXECUTION_DELAY` | 0.5 | Delay after action execution (seconds) |
| `TEXT_INPUT_DELAY` | 0.3 | Delay for text input (seconds) |
| `STATE_STABILIZATION_DELAY` | 1.0 | Wait for UI stabilization (seconds) |
| `SCREENSHOT_QUALITY` | 90 | JPEG compression quality |
| `MAX_RETRY_ATTEMPTS` | 3 | Retry attempts for failed operations |
| `SCREEN_HASH_LENGTH` | 16 | Characters in screen hash |

## Usage Examples

### Basic Device Interaction

```python
from rv_uiautomator import UIAutomator2Adapter

# Initialize and connect
adapter = UIAutomator2Adapter(device_id="emulator-5554")
adapter.connect("emulator-5554")

# Get UI state
state = adapter.get_ui_state()
print(f"Current activity: {state['current_activity']}")

# Perform actions
adapter.click(540, 1200)
adapter.input_text("Hello World")
adapter.press_back()

# Take screenshot
screenshot_path = adapter.take_screenshot()
```

### Action Execution

```python
from rv_uiautomator import UIAutomator2Adapter, UIAutomatorActionExecutor

adapter = UIAutomator2Adapter()
adapter.connect("emulator-5554")

executor = UIAutomatorActionExecutor()

# Execute a generated action (from LLM or algorithm)
success = executor.execute(action, adapter)
```

### State Conversion

```python
from rv_uiautomator import StateConverter

converter = StateConverter()

# Convert UIAutomator state to DroidBot format
ui_state = adapter.get_ui_state()
droidbot_state = converter.uiautomator_to_droidbot(ui_state)

# Compute screen hash for state identification
screen_hash = converter.compute_screen_hash(droidbot_state)
```

### Device Management

```python
from rv_uiautomator.utils import DeviceManager

manager = DeviceManager()

# Discover available devices
devices = manager.get_available_devices()

# Get device info
info = manager.get_device_info("emulator-5554")
print(f"Android version: {info.get('android_version')}")

# Verify connection
if manager.verify_device_connection("emulator-5554"):
    print("Device is responsive")
```

## Integration Points

### With rv-agent

The rv-agent module uses rv-uiautomator for:
- Device action execution via UIAutomatorActionExecutor
- UI state capture via UIAutomator2Adapter
- State format conversion for compatibility with parsers

### With rv-platform

The rv-platform coordinates device interaction through:
- DeviceManager for device discovery and lifecycle
- UIAdapter for consistent device operations across tools

## Development Commands

```bash
# Run tests
cd modules/rv-uiautomator
PYTHONPATH=../rv-android-core/src:../rv-screen-parser/src:src poetry run pytest tests/ -v

# Test with coverage
poetry run pytest tests/ --cov=src --cov-report=html

# Install module
cd modules && ./install.sh rv-uiautomator
```

## Error Handling

All components use the ErrorHandler decorator from rv-android-core:

```python
@ErrorHandler.handle_errors(
    component="UIAutomator2Adapter",
    phase="click_action"
)
def click(self, x: int, y: int) -> bool:
    # Implementation
```

This provides:
- Consistent error logging with component/phase context
- Automatic exception handling
- Optional default return values on failure

## Architectural Decisions

1. **Abstract UIAdapter Interface**: Enables framework-agnostic testing strategies and potential support for alternative automation frameworks

2. **State Format Conversion**: StateConverter bridges UIAutomator and DroidBot formats, allowing reuse of existing parsers without modification

3. **Separation of Concerns**:
   - Adapters handle device communication
   - Executor handles action translation
   - Managers handle resource lifecycle

4. **Error Handling**: All operations use ErrorHandler decorators for consistent error management

## Future Evolution Notes

- StateConverter is a temporary solution; future versions should implement a proper DeviceState model with typed attributes
- Additional UIAdapter implementations may be added for different automation frameworks


## Development Notes

This module is part of the RV-Android Poetry workspace. All modules are installed in **editable mode** via the root `pyproject.toml`.

**Key points:**
- Run `poetry install` from the project root to install all modules
- Source code changes are reflected immediately (no reinstall needed)
- Only reinstall if `pyproject.toml` dependencies change

```bash
# From project root
poetry install          # Install/update all modules
poetry install --sync   # Also remove unused packages
```

