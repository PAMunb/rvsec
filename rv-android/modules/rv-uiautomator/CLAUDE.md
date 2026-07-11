# CLAUDE.md - rv-uiautomator

## Purpose
Shared UIAutomator components for Android device interaction across RV-Android testing tools — a unified interface for device operations, action execution, and state management, eliminating per-tool duplication. (Top-level `rv-android/CLAUDE.md` owns uv/pytest/env conventions and the ErrorHandler pattern.)

## Core components
| Component | File | Role |
|---|---|---|
| `UIAdapter` / `UIAutomator2Adapter` | `adapter/base.py`, `adapter/uiautomator2.py` | Abstract device API + uiautomator2 implementation |
| `UIAutomatorActionExecutor` | `executor/action_executor.py` | Translates `GeneratedAction` → device commands |
| `StateConverter` | `state/converter.py` | UIAutomator → DroidBot state format + screen hashing |
| `DeviceManager` | `utils/device_manager.py` | ADB device discovery/lifecycle |
| `ScreenshotManager` | `utils/screenshot_manager.py` | Screenshot capture, optimize, validate, cleanup |

**UIAdapter API**: `connect(device_id)`, `get_ui_state()` (XML hierarchy + activity + package), `click`/`long_click`, `swipe`, `input_text`, `press_back`/`press_home`, `take_screenshot`, `launch_app`/`stop_app`.

**ActionExecutor supported actions**: `CLICK`, `LONG_CLICK`, `TEXT_CHANGE` (optional click-to-focus), `SCROLL` (direction + distance), `BACK`, and custom coordinate actions (vision strategy).

**StateConverter mapping**: `xml` → `hierarchy` + `view_tree`, `current_activity` → `activity`, `current_package` → `package_name`. `compute_screen_hash(state)` produces a `SCREEN_HASH_LENGTH` (16)-char SHA-256 prefix for state identification.

**DeviceManager**: `get_available_devices()`, `verify_device_connection()`, `get_device_info()`, `restart_adb_server()`.

## Relationship to rv-screen-parser
`StateConverter` bridges the UIAutomator state format to DroidBot-compatible format so rv-screen-parser's existing parsers can consume UIAutomator captures without modification. This is the key architectural decision of the module: adapters stay framework-specific while parsing is reused across sources.

## Config constants (`constants.py`)
Most timing/retry/quality constants live in `constants.py`. Two are contract-relevant: `DEFAULT_DEVICE_ID` (`"emulator-5554"`) and `SCREEN_HASH_LENGTH` (16, tied to `compute_screen_hash`).

## Integration
Consumed by rv-agent (action execution, state capture) and rv-platform (device discovery/lifecycle) — see the top-level CLAUDE.md.
