# RV-UIAutomator

Shared UIAutomator components for Android device interaction across RV-Android testing tools.

## Overview

RV-UIAutomator provides a unified interface for interacting with Android devices through the UIAutomator2 framework. It handles device connection, UI state capture, action execution, and screenshot management. Multiple RV-Android modules (rv-agent, rv-platform) depend on this module to interact with emulators and physical devices without duplicating device communication logic.

## Installation

```bash
# Install all rv-android modules (from project root)
uv sync
```

This module is part of the RV-Android uv workspace. All modules are installed in editable mode — source changes are reflected immediately.

**Prerequisites**: ADB must be installed and available on `PATH` (included with Android SDK).

## Quick Start

```python
from rv_uiautomator import UIAutomator2Adapter, UIAutomatorActionExecutor

# Connect to a device
adapter = UIAutomator2Adapter(device_id="emulator-5554")
adapter.connect("emulator-5554")

# Capture UI state
state = adapter.get_ui_state()
print(f"Activity: {state['current_activity']}")
print(f"Package: {state['current_package']}")

# Perform actions
adapter.click(540, 1200)
adapter.input_text("Hello World")
adapter.press_back()

# Take a screenshot
screenshot_path = adapter.take_screenshot()
```

## Features

- **Device Interaction**: Click, long click, swipe, text input, and system button presses via UIAutomator2
- **UI State Capture**: Retrieve current activity, package, and XML UI hierarchy from the device
- **Action Execution**: Translate `GeneratedAction` objects into device commands (click, scroll, text change, back)
- **State Format Conversion**: Convert UIAutomator state format to DroidBot-compatible format for parser compatibility
- **Device Management**: Discover connected devices, verify connections, and retrieve device properties via ADB
- **Screenshot Management**: Capture, validate, optimize, and clean up screenshots

## Configuration

### Constants

Key constants defined in `rv_uiautomator/constants.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `DEFAULT_DEVICE_ID` | `"emulator-5554"` | Default device identifier |
| `DEFAULT_CONNECTION_TIMEOUT` | `30` | Connection timeout in seconds |
| `ACTION_EXECUTION_DELAY` | `0.3` | Delay after each action (seconds) |
| `DEFAULT_SWIPE_DURATION` | `0.25` | Swipe gesture duration (seconds) |
| `WAIT_FOR_IDLE_TIMEOUT` | `5.0` | UIAutomator2 idle wait timeout (seconds) |
| `SCREENSHOT_QUALITY` | `90` | JPEG compression quality for optimization |
| `MAX_RETRY_ATTEMPTS` | `3` | Retry attempts for failed operations |

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANDROID_HOME` | Android SDK path (provides ADB) | Yes |

## Usage Examples

### Device Discovery and Connection

```python
from rv_uiautomator.utils import DeviceManager

manager = DeviceManager()

# List all connected devices
devices = manager.get_available_devices()
# ['emulator-5554', 'emulator-5556']

# Get device details
info = manager.get_device_info("emulator-5554")
# {'model': 'sdk_gphone64_x86_64', 'android_version': '14', 'api_level': '34', 'resolution': '1080x2400'}

# Verify a device is responsive
if manager.verify_device_connection("emulator-5554"):
    print("Device ready")
```

### Executing Generated Actions

```python
from rv_uiautomator import UIAutomator2Adapter, UIAutomatorActionExecutor

adapter = UIAutomator2Adapter()
adapter.connect("emulator-5554")

executor = UIAutomatorActionExecutor()

# Execute a GeneratedAction from LLM or algorithm
# Supports: CLICK, LONG_CLICK, TEXT_CHANGE, SCROLL, BACK
success = executor.execute(action, adapter)
```

### State Format Conversion

```python
from rv_uiautomator import UIAutomator2Adapter, StateConverter

adapter = UIAutomator2Adapter()
adapter.connect("emulator-5554")

converter = StateConverter()

# Capture state in UIAutomator format
ui_state = adapter.get_ui_state()

# Convert to DroidBot format for use with existing parsers
droidbot_state = converter.uiautomator_to_droidbot(ui_state)

# Compute a hash for state identification
screen_hash = converter.compute_screen_hash(droidbot_state)
```

### Screenshot Management

```python
from rv_uiautomator.utils import ScreenshotManager

manager = ScreenshotManager(screenshot_dir="./screenshots")

# Generate a unique path
path = manager.generate_screenshot_path(prefix="test_screen")

# Validate a screenshot
if manager.validate_screenshot(path):
    # Optimize for storage
    manager.optimize_screenshot(path, quality=85)

# Clean up screenshots older than 12 hours
removed = manager.cleanup_old_screenshots(max_age_hours=12)
```

### Application Lifecycle

```python
from rv_uiautomator import UIAutomator2Adapter

adapter = UIAutomator2Adapter()
adapter.connect("emulator-5554")

# Launch an app
adapter.launch_app("com.example.myapp")

# ... interact with the app ...

# Stop the app
adapter.stop_app("com.example.myapp")
```

## API Reference

### Core Components (exported from `rv_uiautomator`)

| Class | Description |
|-------|-------------|
| `UIAdapter` | Abstract interface defining all device interaction methods |
| `UIAutomator2Adapter` | Concrete implementation using the `uiautomator2` library |
| `UIAutomatorActionExecutor` | Translates `GeneratedAction` objects into device commands |
| `StateConverter` | Converts UIAutomator state format to DroidBot-compatible format |

### Utility Components (from `rv_uiautomator.utils`)

| Class | Description |
|-------|-------------|
| `DeviceManager` | ADB-based device discovery, verification, and info retrieval |
| `ScreenshotManager` | Screenshot path generation, validation, optimization, and cleanup |

## Dependencies

### Internal (rv-android)

| Module | Purpose |
|--------|---------|
| `rv-android-core` | ErrorHandler, LoggingManager, domain models (`WidgetEventType`) |
| `rv-screen-parser` | UI parsing capabilities |

### External

| Package | Purpose |
|---------|---------|
| `uiautomator2` | UIAutomator2 Python bindings for device communication |
| `pillow` | Image processing for screenshot optimization and validation |
| `pydantic` | Data validation for conversion metrics |

## Documentation

| Document | Purpose |
|----------|---------|
| [CLAUDE.md](./CLAUDE.md) | Development reference with architecture details |

## Testing

```bash
# From project root
uv run pytest modules/rv-uiautomator/tests/ -v

# With coverage
uv run pytest modules/rv-uiautomator/tests/ --cov=modules/rv-uiautomator/src --cov-report=html
```

## License

Part of the rv-android project.
