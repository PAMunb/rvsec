# CLAUDE.md - rv-screen-parser

## Purpose
Android UI parsing for RV-Android, built around two subsystems:
1. **UI hierarchy parsing** — transforms screen-state data into standardized `ScreenDescription` models via the visitor pattern. Accepts UIAutomator2 XML dumps and DroidBot JSON (`view_tree`) as inputs.
2. **Screenshot analysis** — detects visual UI elements not in the hierarchy (buttons, text, errors, game controls) via OpenCV + Tesseract OCR.

(Top-level `rv-android/CLAUDE.md` owns uv/pytest/env conventions and the Factory/Registry/ErrorHandler pattern summary.)

## Key components
| Component | File | Role |
|---|---|---|
| `BaseScreenParser` / `ParserFactory` | `parser/screen/base_parser.py`, `parser_factory.py` | Parser base + type-keyed factory |
| `UIAutomator2Parser` / `DroidBotParser` | `parser/screen/{uiautomator,droidbot}/…` | Source-specific parsers |
| `AbstractScreenVisitor` + `VisitorFactory` | `parser/screen/visitor/…` | Visitor base (MOP tracking, system-button filtering) + factory |
| `ScreenshotAnalyzer` + detectors | `screenshot/screenshot_analyzer.py`, `screenshot/detectors/*` | Orchestrator + Text/Button/Error/InteractiveElement detectors (DI) |

## Visitor types
`Node.accept(visitor)` dispatches to a per-widget-type handler (Button, EditText, CheckBox, …), letting each visitor produce a different output format:
- `BasicTextVisitor` — compact descriptions optimized for LLM token efficiency (~69% reduction).
- `DefaultTextVisitor` — standard output.
- `EnhancedTextVisitor` — comprehensive analysis with detailed coordinates.

## Data models (`parser/screen/visitor/model.py`)
| Model | Description |
|---|---|
| `Node` | Hierarchical UI element; visitor-pattern entry point (`accept`) |
| `ScreenItem` / `ScreenDescription` | An element with its actions / the full screen state (all items + actions) |
| `ItemAction` | Executable action with coordinates and MOP-tracking flags |

(`ScreenshotAnalysisResult` in `screenshot/models.py` holds detected visual elements.)

## MOP (monitored-operations) tracking
`ItemAction` carries `reaches_target` and `directly_reaches_target` flags indicating whether executing the action reaches a monitored operation (and whether it does so directly). These are populated from rv-android-core's `StaticAnalysisData` (plus `WidgetEventType` for action classification, `widget_id` for correlation), letting downstream exploration prioritize actions that exercise monitored operations. This linkage to `StaticAnalysisData` is owned here.
