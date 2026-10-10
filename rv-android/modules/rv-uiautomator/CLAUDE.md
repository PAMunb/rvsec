# CLAUDE.md - rv-uiautomator

## Purpose
UIAutomator2 device-interaction components for RV-Android (layer L2): an abstract device API with a `uiautomator2` implementation, plus an action executor, a state-format converter and device/screenshot utilities. rv-agent's `DeviceInterface` is the only workspace consumer, and it uses only `UIAutomator2Adapter`. (Top-level `rv-android/CLAUDE.md` owns uv/pytest/env conventions and the ErrorHandler pattern.)

## Core components
Paths are under `src/rv_uiautomator/`. The package root exports `UIAdapter`, `UIAutomator2Adapter`, `UIAutomatorActionExecutor`, `StateConverter`.

| Component | File | Role |
|---|---|---|
| `UIAdapter` / `UIAutomator2Adapter` | `adapter/base.py`, `adapter/uiautomator2.py` | Abstract device API + `uiautomator2` implementation (`u2.connect(device_id)`) |
| `UIAutomatorActionExecutor` | `executor/action_executor.py` | Dispatches a duck-typed action (`action_type`, `text`, `coordinates`, optional `is_custom`) to `UIAdapter` calls |
| `StateConverter` | `state/converter.py` | UIAutomator state → DroidBot-style dict + screen hashing |
| `DeviceManager` | `utils/device_manager.py` | ADB device discovery/lifecycle |
| `ScreenshotManager` | `utils/screenshot_manager.py` | Screenshot path generation, JPEG optimization, validation, cleanup (distinct from rv-screen-parser's class of the same name) |

**UIAdapter API**: `connect(device_id)`, `get_ui_state(force_refresh=False)`, `click`/`long_click`, `swipe`, `input_text`, `press_back`/`press_home`, `take_screenshot`, `launch_app`/`stop_app`. There is no `press_keycode`.

**`get_ui_state()` keys**: `xml` (hierarchy dump), `current_activity`, `current_package`, `device_info`, `timestamp`. Every adapter method is wrapped in `ErrorHandler.handle_errors`; `get_ui_state` returns `{}` on failure.

**ActionExecutor supported actions**: `CLICK`, `LONG_CLICK`, `TEXT_CHANGE` (click-to-focus when coordinates exist), `SCROLL` (direction + distance), `BACK`, and custom coordinate actions (`is_custom`). Anything else logs a warning and returns False.

**StateConverter mapping**: `xml` → `hierarchy` + `view_tree`, `current_activity` → `activity`, `current_package` → `package_name`. `compute_screen_hash(state)` returns a `SCREEN_HASH_LENGTH` (16)-char SHA-256 prefix of the first 500 chars of the hierarchy, falling back to `package/activity`.

**DeviceManager**: `get_available_devices()`, `verify_device_connection()`, `get_device_info()`, `restart_adb_server()`.

## Usage
```python
from rv_uiautomator import UIAutomator2Adapter

adapter = UIAutomator2Adapter(device_id="emulator-5554")
adapter.connect("emulator-5554")
state = adapter.get_ui_state()          # {"xml": ..., "current_activity": ..., ...}
adapter.click(540, 960)
```
rv-agent passes `state["xml"]` and `state["current_activity"]` straight to rv-screen-parser's `UIAutomator2Parser` as `{"hierarchy": ..., "activity": ...}`; it does not use `StateConverter`. It also reads the raw `uiautomator2` device through `adapter.device` (e.g. `adapter.device.info` for display size).

## Config constants (`constants.py`)
Timing, retry and quality constants tuned for headless (SwiftShader) emulators: `WAIT_FOR_IDLE_TIMEOUT` (5.0 s, applied as `device.settings["wait_timeout"]` on connect), `ACTION_EXECUTION_DELAY` (0.3 s), `DEFAULT_SWIPE_DURATION` (0.25 s), `MAX_RETRY_ATTEMPTS` (3). Two are contract-relevant: `DEFAULT_DEVICE_ID` (`"emulator-5554"`) and `SCREEN_HASH_LENGTH` (16, tied to `compute_screen_hash`).

## Dependencies
- **Internal**: `rv-android-core` (`ErrorHandler`, `LoggingManager`, `WidgetEventType`), the only workspace dependency. Turning a dump into a `ScreenDescription` is left to the caller (rv-agent hands the XML to rv-screen-parser itself), so this module needs no parser.
- **External**: `uiautomator2`, `pillow`, `pydantic`.
- **Dependents**: rv-agent (`agent/device_interface.py`).

## Testing
```bash
# From rv-android root. -o "addopts=" is required: this pyproject sets addopts = "--cov=src".
uv run pytest modules/rv-uiautomator/tests --import-mode=importlib -o "addopts=" -q
```
`tests/test_adapter.py`, `tests/test_device_manager.py`, `tests/test_screenshot_manager.py` mock the device; no emulator is needed.
