"""
Parse unified static analysis JSON into domain objects.

Convert the JSON output produced by RvsecAnalysisClient (a GATOR Java client)
into StaticAnalysisData containing Classes, Windows, WindowTransitionGraph, and
Components. The JSON contains four sections written in priority order
(reachability, windows, transitions, components), and on timeout some sections
may be missing. The parser handles partial or truncated JSON gracefully by
returning empty domain objects for missing or corrupt sections.

All class names are normalized via SignatureNormalizer as a safety net for
inner class notation (Outer.Inner -> Outer$Inner), and classes are filtered
by code_package to exclude framework code.

### Architectural Decisions:

- Each section is parsed independently so a corrupt or missing section does
  not prevent recovery of the others (INV-ANA-06)
- Truncated JSON recovery via bracket completion handles timeout scenarios
  where the Java client flushed some sections but was killed mid-write
- SignatureNormalizer is applied defensively -- the GATOR client already
  writes $-notation, but the normalizer guards against future changes

### Role in the System:

- Called by StaticAnalyzer.get_static_data() to convert raw JSON into
  StaticAnalysisData domain objects for downstream consumers
- Module-level convenience functions (parse_file, read_static_analysis_files)
  provide a singleton-based API for direct use

### Key Features:

- Graceful degradation: missing or corrupt sections yield empty domain objects
- Truncated JSON recovery via bracket completion for timeout scenarios
- Class filtering by code_package to exclude framework/library classes
- Widget back-fill: widgets referenced in transitions but absent from windows
  are created on-the-fly

### Integration Points:

- Input: JSON files produced by RvsecAnalysisClient (GATOR)
- Output: StaticAnalysisData (Classes, Windows, WindowTransitionGraph, Components)
- Dependencies: rv-android-core domain models, SignatureNormalizer, LoggingManager
"""

import json
import os
import re

import rv_android_core.constants as constants
from rv_android_core.domain.classes import Classes, Method
from rv_android_core.domain.components import ComponentInfo, Components, IntentFilter
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import (
    Widget,
    WidgetEvent,
    WidgetEventType,
    WidgetType,
)
from rv_android_core.domain.window import Window, Windows, WindowType
from rv_android_core.domain.wtg import WindowTransition, WindowTransitionGraph
from rv_android_core.util.android.signature_normalizer import SignatureNormalizer
from rv_android_core.util.logging.manager import LoggingManager

# Event type mapping from Java analysis client output to domain enum
_EVENT_TYPE_MAP = {
    "click": WidgetEventType.CLICK,
    "long_click": WidgetEventType.LONG_CLICK,
    "scroll": WidgetEventType.SCROLL,
    "selection": WidgetEventType.SELECTION,
    "drag": WidgetEventType.DRAG,
    "touch": WidgetEventType.TOUCH,
    "focus": WidgetEventType.FOCUS,
    "key": WidgetEventType.KEY,
    "text_change": WidgetEventType.TEXT_CHANGE,
}


class StaticAnalysisParser:
    """
    Parses the unified static analysis JSON into StaticAnalysisData.

    The JSON is produced by RvsecAnalysisClient (a GATOR client) and contains
    three sections written in priority order: reachability, windows, transitions.
    On timeout, some sections may be missing — the parser handles partial JSON
    gracefully by returning empty domain objects for missing/corrupt sections
    (INV-ANA-06).

    SignatureNormalizer is applied to all class names as a safety net (INV-ANA-02),
    though the Java client already writes $-notation via SootClass.getName().
    Classes are filtered by code_package (INV-ANA-03).
    """

    def __init__(self):
        """Initialize parser with logging and signature normalization.

        State:
            self.normalizer: SignatureNormalizer for inner class notation
                (Outer.Inner -> Outer$Inner). Applied to all class names.
        """
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_static_analysis.parser.static.static_analysis_parser"
        )
        self.normalizer = SignatureNormalizer()

    def parse_file(self, file_path: str, package: str) -> StaticAnalysisData:
        """
        Parse a unified analysis JSON file into StaticAnalysisData.

        Args:
            file_path: Path to the .json analysis output file
            package: Application code_package for class filtering (INV-ANA-03)

        Returns:
            StaticAnalysisData with parsed Classes, Windows, WindowTransitionGraph, and Components.
            On any failure, returns data with empty objects for the failed sections.
        """
        if not file_path or not os.path.isfile(file_path):
            self.logger.warning(f"Analysis file not found: {file_path}")
            return StaticAnalysisData(Classes(), Windows(), WindowTransitionGraph())

        self.logger.info(f"Parsing analysis file: {file_path}")

        data = self._load_json(file_path)
        if data is None:
            return StaticAnalysisData(Classes(), Windows(), WindowTransitionGraph())

        # Step 1: Parse each section independently so a corrupt section does not
        # prevent recovery of the others (graceful degradation, INV-ANA-06).
        # Order matters: windows need classes (to mark main activity), and
        # transitions need windows (for source/target lookup and widget back-fill).
        classes = self._parse_classes(data, package)
        windows = self._parse_windows(data, package, classes)
        wtg = self._parse_transitions(data, windows)
        components = self._parse_components(data)

        self.logger.info(
            f"Parsed: {len(classes.classes)} classes, "
            f"{len(classes.methods)} methods, "
            f"{len(windows.windows)} windows, "
            f"{len(wtg.transitions)} transitions, "
            f"{sum(len(v) for v in [components.activities, components.receivers, components.services, components.providers])} components"
        )
        return StaticAnalysisData(classes, windows, wtg, components=components)

    def read_static_analysis_files(
        self, results_dir: str, apk: str, package: str
    ) -> StaticAnalysisData:
        """
        Parse the analysis JSON for an APK from a results directory.

        Construct the file path as ``results_dir/apk.json`` and delegate
        to parse_file.

        Args:
            results_dir: Directory containing analysis result files.
            apk: APK filename including extension (e.g., "cryptoapp.apk").
                The JSON extension is appended automatically.
            package: Application code_package for class filtering (INV-ANA-03).

        Returns:
            StaticAnalysisData with parsed Classes, Windows, and
            WindowTransitionGraph.
        """
        file_path = os.path.join(results_dir, apk + constants.EXTENSION_STATIC_ANALYSIS)
        return self.parse_file(file_path, package)

    def _load_json(self, file_path: str) -> dict | None:
        """Load and parse JSON, with bracket-recovery for truncated files from timeout.

        Args:
            file_path: Path to the analysis JSON file.

        Returns:
            Parsed dictionary, or None if the file cannot be read or recovered.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return json.loads(content)
        except json.JSONDecodeError:
            self.logger.warning(
                f"JSON parse error in {file_path}, attempting truncated file recovery"
            )
            return self._recover_truncated_json(content)
        except Exception as e:
            self.logger.error(f"Failed to read analysis file {file_path}: {e}")
            return None

    def _recover_truncated_json(self, content: str) -> dict | None:
        """Recover truncated JSON by closing at the last complete array bracket.

        Args:
            content: Raw file content that failed json.loads().

        Returns:
            Parsed dictionary from the recovered content, or None if
            recovery fails (no ']' found or still invalid after fix).
        """
        # The GATOR client writes sections sequentially and flushes between each.
        # On timeout, the file is truncated mid-array (e.g., the transitions array
        # is half-written). We find the last complete ']' and close the root object
        # with '}', discarding the partial entry. This preserves all fully-flushed
        # sections even when the process was killed mid-write.
        last_bracket = content.rfind("]")
        if last_bracket == -1:
            self.logger.error("Cannot recover truncated JSON: no ']' found")
            return None

        truncated = content[: last_bracket + 1] + "}"
        try:
            data = json.loads(truncated)
            self.logger.info("Recovered truncated JSON successfully")
            return data
        except json.JSONDecodeError:
            self.logger.error("Cannot recover truncated JSON after bracket fix")
            return None

    def _parse_classes(self, data: dict, package: str) -> Classes:
        """Parse the reachability section into Classes domain object.

        Each entry in data["reachability"] is a class with methods and
        reachability flags. Class names are normalized (INV-ANA-02) and
        filtered by code_package (INV-ANA-03).

        Args:
            data: Parsed JSON dictionary from the analysis file.
            package: Application code_package for class filtering.

        Returns:
            Classes populated with class and method entries, or empty
            Classes on missing data or parse error.
        """
        try:
            reachability = data.get("reachability", [])
            if not reachability:
                self.logger.debug("No reachability data in analysis JSON")
                return Classes()

            classes = Classes()

            for cls_data in reachability:
                class_name = cls_data.get("className", "")
                # Normalize inner class notation: Outer.Inner -> Outer$Inner.
                # GATOR already outputs $-notation via SootClass.getName(), but
                # the normalizer guards against future upstream changes.
                normalized = self.normalizer.normalize_class_name(class_name)

                # Filter by code_package prefix to exclude Android framework and
                # third-party library classes. Uses substring match (not startswith)
                # because code_package may differ from the manifest package in apps
                # that use a library namespace (e.g., Godot games).
                if package and package not in normalized:
                    continue

                component_type = cls_data.get("componentType", None)
                is_main = cls_data.get("isMain", False)
                classes.add_clazz(normalized, component_type, is_main)

                for m_data in cls_data.get("methods", []):
                    signature = m_data.get("signature", "")
                    method_name = m_data.get("name", "")

                    # Extract parameter types from Soot signature format:
                    # "<class: retType name(p1,p2)>" -- we need the params list
                    # to build the Method domain object for coverage matching.
                    params = self._extract_params(signature)

                    method = Method(
                        class_name=normalized,
                        name=method_name,
                        params=params,
                        signature=signature,
                        reachable=m_data.get("reachable", False),
                        reaches_mop=m_data.get("reachesMop", False),
                        directly_reaches_mop=m_data.get("directlyReachesMop", False),
                    )
                    classes.add_method(method)

            return classes

        except Exception as e:
            self.logger.error(f"Error parsing reachability section: {e}")
            return Classes()

    def _parse_windows(self, data: dict, package: str, classes: Classes) -> Windows:
        """Parse the windows section into Windows domain object.

        Each entry in data["windows"] is a window with widgets and listeners.
        Window names are normalized and filtered by code_package. Only
        ACTIVITY-type windows are filtered; DIALOG, OPTIONSMENU, and other
        types are included regardless of package.

        Args:
            data: Parsed JSON dictionary from the analysis file.
            package: Application code_package for ACTIVITY filtering.
            classes: Previously parsed Classes, used to mark main activity.

        Returns:
            Windows populated with window and widget entries, or empty
            Windows on missing data or parse error.
        """
        try:
            windows_data = data.get("windows", [])
            if not windows_data:
                self.logger.debug("No windows data in analysis JSON")
                return Windows()

            windows = Windows()

            for w_data in windows_data:
                window_name = w_data.get("name", "")
                normalized_name = self.normalizer.normalize_class_name(window_name)

                # Only ACTIVITY windows are filtered by code_package. DIALOGs,
                # OPTIONSMENUs, and other window types are kept regardless of package
                # because they can be system-provided overlays triggered by app code.
                w_type_str = w_data.get("type", "ACTIVITY")
                if (
                    w_type_str == "ACTIVITY"
                    and package
                    and package not in normalized_name
                ):
                    continue

                # Map window type
                window_type = self._map_window_type(w_type_str)

                window_id = str(w_data.get("id", ""))
                is_main = w_data.get("isMain", False)

                window = Window(
                    name=normalized_name,
                    id=window_id,
                    type=window_type,
                    activity=(
                        normalized_name if window_type == WindowType.ACTIVITY else ""
                    ),
                    class_name=normalized_name,
                )

                # Parse widgets
                for wgt_data in w_data.get("widgets", []):
                    widget = self._parse_widget(wgt_data, normalized_name)
                    if widget:
                        window.add_widget(widget)

                windows.add_window(window)

                # Mark main activity in classes
                if is_main:
                    clazz = classes.get_clazz(normalized_name)
                    if clazz:
                        clazz.is_main = True

            return windows

        except Exception as e:
            self.logger.error(f"Error parsing windows section: {e}")
            return Windows()

    def _parse_widget(self, wgt_data: dict, window_name: str) -> Widget | None:
        """Parse a single widget entry from the windows section.

        Args:
            wgt_data: Widget JSON object with id, idName, type, text,
                hint, inputType, entries, and listeners.
            window_name: Normalized window name for error context.

        Returns:
            Widget with parsed events, or None on parse error.
        """
        try:
            widget_id = str(wgt_data.get("id", ""))
            id_name = wgt_data.get("idName", "")
            widget_class = wgt_data.get("type", "")
            widget_type = WidgetType.from_class_name(widget_class)

            widget = Widget(
                id=widget_id,
                name=id_name,
                type=widget_type,
                text=wgt_data.get("text", ""),
                hint=wgt_data.get("hint", ""),
                input_type=wgt_data.get("inputType", ""),
                class_name=widget_class,
                entries=wgt_data.get("entries", []),
                # gh57 Group 3: XML widget attributes — None when absent
                prompt=wgt_data.get("prompt"),
                spinner_mode=wgt_data.get("spinnerMode"),
                content_description=wgt_data.get("contentDescription"),
                tooltip_text=wgt_data.get("tooltipText"),
            )

            # Parse listeners into WidgetEvents
            for listener in wgt_data.get("listeners", []):
                event = self._parse_listener(listener, window_name)
                if event:
                    widget.add_event(event)

            return widget

        except Exception as e:
            self.logger.debug(f"Error parsing widget in {window_name}: {e}")
            return None

    def _parse_listener(self, listener: dict, window_name: str) -> WidgetEvent | None:
        """Parse a listener entry into a WidgetEvent.

        Unmapped event types (e.g., OTHER) are excluded because they
        have no actionable UI interaction in the testing tools.

        Args:
            listener: Listener JSON object with eventType and handler.
            window_name: Normalized window name for error context.

        Returns:
            WidgetEvent with type, class, method, and signature, or
            None if the event type is unmapped or handler is missing.
        """
        event_type_str = listener.get("eventType", "")
        event_type = _EVENT_TYPE_MAP.get(event_type_str)

        # Exclude unmapped event types (OTHER MUST be excluded)
        if event_type is None:
            return None

        handler = listener.get("handler", "")
        if not handler:
            return None

        # Extract class and method from Soot signature: <class: retType method(params)>
        clazz, method_name = self._extract_class_method(handler)

        return WidgetEvent(
            type=event_type,
            clazz=clazz,
            method=method_name,
            signature=handler,
        )

    def _parse_transitions(self, data: dict, windows: Windows) -> WindowTransitionGraph:
        """Parse the transitions section into WindowTransitionGraph.

        Each transition links source and target windows by ID and carries
        event metadata (widget, handler). Widgets referenced in transitions
        but absent from the source window are created on-the-fly and added
        to both the window and the global widget index.

        Args:
            data: Parsed JSON dictionary from the analysis file.
            windows: Previously parsed Windows, used for window lookup
                and widget back-fill.

        Returns:
            WindowTransitionGraph with parsed transitions, or empty
            graph on missing data or parse error.
        """
        try:
            transitions_data = data.get("transitions", [])
            if not transitions_data:
                self.logger.debug("No transitions data in analysis JSON")
                return WindowTransitionGraph()

            wtg = WindowTransitionGraph()

            for t_data in transitions_data:
                source_id = str(t_data.get("sourceId", ""))
                target_id = str(t_data.get("targetId", ""))

                source_window = windows.get_window_by_id(source_id)
                target_window = windows.get_window_by_id(target_id)

                if not source_window or not target_window:
                    self.logger.debug(
                        f"Transition references unknown window: "
                        f"source={source_id} target={target_id}"
                    )
                    continue

                events = []
                for evt_data in t_data.get("events", []):
                    handler = evt_data.get("handler", "")
                    widget_id = str(evt_data.get("widgetId", ""))
                    widget_class = evt_data.get("widgetClass", "")
                    widget_name = evt_data.get("widgetName", "")

                    # Widget back-fill: GATOR may reference widgets in transitions
                    # that were not listed in the window's widget array (e.g., widgets
                    # created dynamically in code). Create them on-the-fly and register
                    # in both the window and the global widget index so downstream
                    # consumers (rv-agent's TransitionManager) can look them up.
                    if widget_id and not source_window.get_widget(widget_id):
                        widget_type = WidgetType.from_class_name(widget_class)
                        widget = Widget(
                            id=widget_id,
                            name=widget_name,
                            type=widget_type,
                            class_name=widget_class,
                        )
                        source_window.add_widget(widget)
                        windows.widgets[widget_id] = widget

                    # GATOR JSON uses "type" for transition events but "eventType" for
                    # widget listeners -- inconsistent naming from the Java client.
                    # Default to CLICK because most transitions are click-triggered.
                    event_type_str = evt_data.get("type", "click")
                    event_type = _EVENT_TYPE_MAP.get(
                        event_type_str, WidgetEventType.CLICK
                    )

                    transition_event = WindowTransition(
                        widget_id=widget_id,
                        event_type=event_type,
                        method=handler,
                    )
                    events.append(transition_event)

                if events:
                    wtg.add_transition(source_window, target_window, events)

            return wtg

        except Exception as e:
            self.logger.error(f"Error parsing transitions section: {e}")
            return WindowTransitionGraph()

    def _parse_intent_filters(self, filters_data: list) -> list[IntentFilter]:
        """Parse intent filter entries into IntentFilter objects.

        Args:
            filters_data: List of filter dictionaries with actions and categories.

        Returns:
            List of IntentFilter domain objects.
        """
        result = []
        for f in filters_data:
            result.append(
                IntentFilter(
                    actions=f.get("actions", []),
                    categories=f.get("categories", []),
                )
            )
        return result

    def _parse_component_list(
        self, entries: list, component_type: str
    ) -> list[ComponentInfo]:
        """Parse component entries (activities, receivers, services) with intentFilters.

        Args:
            entries: List of component dictionaries from the JSON.
            component_type: Type label ("activity", "receiver", "service").

        Returns:
            List of ComponentInfo domain objects with parsed intent filters.
        """
        result = []
        for entry in entries:
            result.append(
                ComponentInfo(
                    class_name=entry.get("className", ""),
                    component_type=component_type,
                    is_main=entry.get("isMain", False),
                    intent_filters=self._parse_intent_filters(
                        entry.get("intentFilters", [])
                    ),
                    exported=entry.get("exported", False),
                    reaches_mop=entry.get("reachesMop", False),
                    mop_methods=entry.get("mopMethods", []),
                )
            )
        return result

    def _parse_provider_list(self, entries: list) -> list[ComponentInfo]:
        """Parse provider entries with authorities instead of intentFilters.

        Args:
            entries: List of provider dictionaries from the JSON.

        Returns:
            List of ComponentInfo domain objects with authorities field.
        """
        result = []
        for entry in entries:
            result.append(
                ComponentInfo(
                    class_name=entry.get("className", ""),
                    component_type="provider",
                    is_main=False,  # Providers are never the main component
                    authorities=entry.get("authorities"),
                    exported=entry.get("exported", False),
                    reaches_mop=entry.get("reachesMop", False),
                    mop_methods=entry.get("mopMethods", []),
                )
            )
        return result

    def _parse_components(self, data: dict) -> Components:
        """Parse the components section into Components domain object.

        Each component type has its own array in the JSON. Activities, receivers,
        and services share the same shape (with intentFilters). Providers use
        authorities instead of intentFilters.

        Args:
            data: Parsed JSON dictionary from the analysis file.

        Returns:
            Components populated with activities, receivers, services, and
            providers, or empty Components on missing data or parse error.
        """
        try:
            components_data = data.get("components")
            if not components_data:
                return Components()

            return Components(
                activities=self._parse_component_list(
                    components_data.get("activities", []), "activity"
                ),
                receivers=self._parse_component_list(
                    components_data.get("receivers", []), "receiver"
                ),
                services=self._parse_component_list(
                    components_data.get("services", []), "service"
                ),
                providers=self._parse_provider_list(
                    components_data.get("providers", [])
                ),
            )
        except Exception as e:
            self.logger.error(f"Error parsing components section: {e}")
            return Components()

    def _map_window_type(self, type_str: str) -> WindowType:
        """Map analysis JSON window type string to WindowType enum.

        Args:
            type_str: Window type from JSON (e.g., "ACTIVITY", "DIALOG").

        Returns:
            Corresponding WindowType enum value, defaulting to ACTIVITY.
        """
        mapping = {
            "ACTIVITY": WindowType.ACTIVITY,
            "DIALOG": WindowType.DIALOG,
            "OPTIONSMENU": WindowType.OPTIONSMENU,
            "CONTEXTMENU": WindowType.CONTEXTMENU,
            "FRAGMENT": WindowType.FRAGMENT,
        }
        return mapping.get(type_str, WindowType.ACTIVITY)

    def _extract_params(self, signature: str) -> list[str]:
        """Extract parameter types from a Soot method signature.

        Args:
            signature: Soot signature like ``<class: retType name(p1,p2)>``.

        Returns:
            List of parameter type strings, or empty list if none found.
        """
        match = re.search(r"\(([^)]*)\)", signature)
        if match:
            params_str = match.group(1).strip()
            if params_str:
                return [p.strip() for p in params_str.split(",")]
        return []

    def _extract_class_method(self, signature: str) -> tuple[str, str]:
        """Extract class name and method name from a Soot signature.

        Args:
            signature: Soot signature like ``<class: retType method(params)>``.

        Returns:
            Tuple of (class_name, method_name), or ("", "") if not parseable.
        """
        match = re.match(r"<([^:]+):\s+\S+\s+(\w+)\(", signature)
        if match:
            return match.group(1), match.group(2)
        return "", ""


# Singleton instance for convenience
_instance = StaticAnalysisParser()


def parse_file(file_path: str, package: str) -> StaticAnalysisData:
    """Parse a unified analysis JSON file using the module singleton.

    Args:
        file_path: Path to the .json analysis output file.
        package: Application code_package for class filtering.

    Returns:
        StaticAnalysisData with parsed domain objects.
    """
    return _instance.parse_file(file_path, package)


def read_static_analysis_files(
    results_dir: str, apk: str, package: str
) -> StaticAnalysisData:
    """Parse analysis JSON for an APK from a results directory using the module singleton.

    Args:
        results_dir: Directory containing analysis result files.
        apk: APK filename including extension (e.g., "cryptoapp.apk").
        package: Application code_package for class filtering.

    Returns:
        StaticAnalysisData with parsed domain objects.
    """
    return _instance.read_static_analysis_files(results_dir, apk, package)
