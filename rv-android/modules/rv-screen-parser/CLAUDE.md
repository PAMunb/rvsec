# CLAUDE.md - rv-screen-parser

## Purpose
Android UI parsing for RV-Android (layer L3), built around two subsystems:
1. **UI hierarchy parsing** — transforms screen-state data into standardized `ScreenDescription` models via the visitor pattern. Accepts UIAutomator2 XML dumps and DroidBot JSON (`view_tree`) as inputs.
2. **Screenshot analysis** — detects visual UI elements not in the hierarchy (buttons, text, errors, interactive elements) via OpenCV + Tesseract OCR.

(Top-level `rv-android/CLAUDE.md` owns uv/pytest/env conventions and the Factory/Registry/ErrorHandler pattern summary.)

## Key components
Paths are under `src/rv_screen_parser/`.

| Component | File | Role |
|---|---|---|
| `BaseScreenParser` / `ParserFactory` | `parser/screen/base_parser.py`, `parser/screen/parser_factory.py` | Parser base (`parse_screen(state_data, static_data=None)`) + type-keyed factory |
| `UIAutomator2Parser` / `DroidBotParser` | `parser/screen/uiautomator/uiautomator_parser.py`, `parser/screen/droidbot/droidbot_parser.py` | Source-specific parsers |
| `AbstractScreenVisitor` + `VisitorFactory` | `parser/screen/visitor/abstract_visitor.py`, `visitor_factory.py` | Visitor base (MOP tracking, system-button filtering) + factory |
| `ScreenshotAnalyzer` + detectors | `screenshot/screenshot_analyzer.py`, `screenshot/detectors/*` | Orchestrator + `TextDetector`/`ButtonDetector`/`ErrorDetector`/`InteractiveElementDetector`, obtained through `get_*_detector()` accessors |
| `ImagePreprocessor`, `ScreenshotDataConverter`, `ScreenshotManager` | `screenshot/preprocessing/`, `screenshot/converters.py`, `screenshot/screenshot_manager.py` | Image preprocessing, result conversion, screenshot storage |
| Constants | `constants.py` | `ScreenParserType` (`uiautomator`, `droidbot`), `VisitorType` (`basic`, `default`, `detailed`), `ActionType`, `SystemActionType` |

## Entry points
```python
from rv_screen_parser.constants import ScreenParserType
from rv_screen_parser.parser.screen.parser_factory import ParserFactory

parser = ParserFactory.create(ScreenParserType.UIAUTOMATOR, visitor_class=None)  # None -> DefaultTextVisitor
screen = parser.parse_screen({"hierarchy": xml_string, "activity": ".MainActivity"}, static_data)
```
- `UIAutomator2Parser` reads `state_data["hierarchy"]` (XML string); `activity` is optional (extracted from the XML when absent).
- `DroidBotParser` reads `state_data["view_tree"]` (a dict); activity from `activity` or `foreground_activity`.
- `VisitorFactory.create(visitor_type, static_data, activity)` builds a visitor directly.
- Invalid state data raises `RVParsingError` (rv-android-core).

## Visitor types
`Node.accept(visitor)` dispatches to a per-widget-type handler (`visit_button`, `visit_edit_text`, `visit_checkbox`, `visit_spinner`, …), letting each visitor produce a different output format:
- `BasicTextVisitor` (`basic`) — compact descriptions optimized for LLM token efficiency (~69% reduction).
- `DefaultTextVisitor` (`default`) — standard output; base of rv-agent's `RVAgentVisitor`.
- `EnhancedTextVisitor` (`detailed`) — comprehensive analysis with detailed coordinates.

## Data models (`parser/screen/visitor/model.py`)
| Model | Description |
|---|---|
| `Node` | Hierarchical UI element; visitor-pattern entry point (`accept`) |
| `ScreenItem` / `ScreenDescription` | An element with its actions / the full screen state (all items + actions) |
| `ItemAction` | Executable action with coordinates, MOP flags, `widget_id`, `callback_signature`; `coords_for_matching` is the device-space identity rv-agent tracks |

(`ScreenshotAnalysisResult` in `screenshot/models.py` holds detected visual elements.)

## MOP (monitored-operations) tracking
`ItemAction` carries `reaches_target` and `directly_reaches_target` flags indicating whether executing the action reaches a monitored operation (and whether it does so directly). `AbstractScreenVisitor._update_action_mop_related_info` fills them: `find_matching_widget` matches the runtime node to a GATOR widget of the current window by resource ID, then by text; for the widget event whose type equals the action's `WidgetEventType`, the flags come from `static_info.classes.methods[event.signature]`, and `widget_id`/`callback_signature` are set. The action text gets a ` [DM]` (direct) or ` [M]` (transitive) suffix so an LLM sees it in the screen description. This linkage to rv-android-core's `StaticAnalysisData` is owned here; without static data every flag is False.

## Dependencies
- **Internal**: `rv-android-core` (`StaticAnalysisData`, `WidgetEventType`, `ErrorHandler`, `LoggingManager`, `BaseRepository`).
- **External**: `lxml`, `beautifulsoup4`, `uiautomator2`, `pytesseract` (needs the `tesseract` binary on the host), `opencv-python-headless`, `pillow`, `numpy`, `pydantic`.
- **Dependents**: rv-agent imports it (`ParserFactory`, models, `DefaultTextVisitor`, `ErrorDetector`). rv-uiautomator and rv-experiment declare it in `pyproject.toml` without importing it.

## Testing
```bash
# From rv-android root. -o "addopts=" is required: this pyproject sets addopts = "--cov=src".
uv run pytest modules/rv-screen-parser/tests --import-mode=importlib -o "addopts=" -q
uv run pytest modules/rv-screen-parser/tests/parser --import-mode=importlib -o "addopts=" -q
```
| Location | Content |
|---|---|
| `tests/parser/screen/{uiautomator,droidbot,visitor}/` | Parsers, edge cases, visitors, models, factories |
| `tests/analysis/`, `tests/screenshot/`, `tests/preprocessing/`, `tests/utils/` | Screenshot analyzer, converters, preprocessor, geometry |
| `tests/test_*.py` | Detector and visitor tests, real-dump parsing |
| `tests/images/`, `test_images/` | Screenshot fixtures; `test_images/NNN.uiautomator` + `NNN.png` dump pairs |
