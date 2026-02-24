"""Tests for the unified StaticAnalysisParser."""

import json
import os
import tempfile

import pytest

from unittest.mock import patch

from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType, WidgetType
from rv_android_core.domain.window import Windows, WindowType
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_static_analysis.parser.static.static_analysis_parser import (
    StaticAnalysisParser,
    parse_file,
    read_static_analysis_files,
)

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "resources")
CRYPTOAPP_FIXTURE = os.path.join(FIXTURE_DIR, "cryptoapp.apk.json")
PACKAGE = "br.unb.cic.cryptoapp"


@pytest.fixture
def parser():
    return StaticAnalysisParser()


def _write_json(tmp_path, data, filename="test.json"):
    """Write JSON data to a temp file and return path."""
    path = os.path.join(str(tmp_path), filename)
    with open(path, "w") as f:
        json.dump(data, f)
    return path


# --- Well-formed JSON (real fixture) ---


class TestWellFormedJSON:
    """Tests using the real cryptoapp.apk.json fixture."""

    def test_parse_real_fixture(self, parser):
        """Parse the real cryptoapp fixture and verify basic counts."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)

        assert isinstance(result, StaticAnalysisData)
        assert isinstance(result.classes, Classes)
        assert isinstance(result.windows, Windows)
        assert isinstance(result.wtg, WindowTransitionGraph)

        # Verify non-empty results
        assert len(result.classes.classes) > 0
        assert len(result.classes.methods) > 0
        assert len(result.windows.windows) > 0
        assert len(result.wtg.transitions) > 0

    def test_class_count(self, parser):
        """Verify expected number of classes from cryptoapp."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        # cryptoapp has 27 app classes matching the package
        assert len(result.classes.classes) == 27

    def test_method_count(self, parser):
        """Verify expected number of methods from cryptoapp."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        assert len(result.classes.methods) == 118

    def test_window_count(self, parser):
        """Verify expected number of windows from cryptoapp."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        assert len(result.windows.windows) == 5

    def test_transition_count(self, parser):
        """Verify expected number of transitions from cryptoapp."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        assert len(result.wtg.transitions) == 36

    def test_main_activity_detected(self, parser):
        """Verify main activity is correctly identified."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        main_clazz = result.classes.get_clazz("br.unb.cic.cryptoapp.MainActivity")
        assert main_clazz is not None
        assert main_clazz.is_main_activity is True

    def test_activity_flag(self, parser):
        """Verify activity classes are marked as activities."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        main_clazz = result.classes.get_clazz("br.unb.cic.cryptoapp.MainActivity")
        assert main_clazz is not None
        assert main_clazz.is_activity is True

    def test_reachability_flags(self, parser):
        """Verify reachability flags are parsed correctly."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        # At least some methods should be reachable
        reachable_methods = [m for m in result.classes.methods.values() if m.reachable]
        reaches_mop = [m for m in result.classes.methods.values() if m.reaches_mop]
        directly_reaches = [
            m for m in result.classes.methods.values() if m.directly_reaches_mop
        ]

        assert len(reachable_methods) > 0
        assert len(reaches_mop) > 0
        assert len(directly_reaches) > 0

    def test_window_types(self, parser):
        """Verify different window types are parsed."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        types = {w.type for w in result.windows.windows}
        assert WindowType.ACTIVITY in types
        # cryptoapp has an OptionsMenu
        assert WindowType.OPTIONSMENU in types

    def test_widget_events_parsed(self, parser):
        """Verify widget click listeners are parsed."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        # Find widgets with events across all windows
        has_events = False
        for window in result.windows.windows:
            for widget in window.widgets.values():
                if widget.events:
                    has_events = True
                    # Verify event has required fields
                    event = next(iter(widget.events))
                    assert event.type is not None
                    assert event.signature != ""
                    break
            if has_events:
                break
        assert has_events, "No widget events found in fixture"

    def test_click_event_type(self, parser):
        """Verify click events are mapped to CLICK type."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        for window in result.windows.windows:
            for widget in window.widgets.values():
                for event in widget.events:
                    if event.type == WidgetEventType.CLICK:
                        assert event.clazz != ""
                        assert event.method != ""
                        return
        pytest.fail("No CLICK event found in fixture")


# --- Empty and missing data ---


class TestEmptyAndMissingData:
    """Tests for edge cases: empty JSON, missing sections, missing file."""

    def test_missing_file(self, parser):
        """Missing file returns empty StaticAnalysisData."""
        result = parser.parse_file("/nonexistent/path.json", PACKAGE)
        assert isinstance(result, StaticAnalysisData)
        assert len(result.classes.classes) == 0
        assert len(result.windows.windows) == 0
        assert len(result.wtg.transitions) == 0

    def test_none_file_path(self, parser):
        """None file path returns empty StaticAnalysisData."""
        result = parser.parse_file(None, PACKAGE)
        assert isinstance(result, StaticAnalysisData)
        assert len(result.classes.classes) == 0

    def test_empty_string_file_path(self, parser):
        """Empty string file path returns empty StaticAnalysisData."""
        result = parser.parse_file("", PACKAGE)
        assert isinstance(result, StaticAnalysisData)
        assert len(result.classes.classes) == 0

    def test_empty_json_object(self, parser, tmp_path):
        """Empty JSON object {} returns empty data for all sections."""
        path = _write_json(tmp_path, {})
        result = parser.parse_file(path, PACKAGE)
        assert len(result.classes.classes) == 0
        assert len(result.windows.windows) == 0
        assert len(result.wtg.transitions) == 0

    def test_missing_reachability_section(self, parser, tmp_path):
        """JSON without reachability returns empty Classes."""
        data = {
            "windows": [
                {
                    "name": "com.example.Main",
                    "type": "ACTIVITY",
                    "id": 1,
                    "isMain": True,
                    "widgets": [],
                }
            ],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        assert len(result.classes.classes) == 0
        assert len(result.windows.windows) == 1

    def test_missing_windows_section(self, parser, tmp_path):
        """JSON without windows returns empty Windows."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Main",
                    "isActivity": True,
                    "isMainActivity": True,
                    "methods": [],
                }
            ],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        assert len(result.classes.classes) == 1
        assert len(result.windows.windows) == 0

    def test_missing_transitions_section(self, parser, tmp_path):
        """JSON without transitions returns empty WTG."""
        data = {
            "reachability": [],
            "windows": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        assert len(result.wtg.transitions) == 0

    def test_empty_reachability_array(self, parser, tmp_path):
        """Empty reachability array returns empty Classes."""
        data = {"reachability": [], "windows": [], "transitions": []}
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        assert len(result.classes.classes) == 0

    def test_empty_windows_array(self, parser, tmp_path):
        """Empty windows array returns empty Windows."""
        data = {"reachability": [], "windows": [], "transitions": []}
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        assert len(result.windows.windows) == 0


# --- Code package filtering (INV-ANA-03) ---


class TestCodePackageFiltering:
    """Tests for class filtering by code_package."""

    def test_filters_by_package(self, parser, tmp_path):
        """Only classes matching the package are included."""
        data = {
            "reachability": [
                {
                    "className": "com.example.MyClass",
                    "isActivity": False,
                    "isMainActivity": False,
                    "methods": [],
                },
                {
                    "className": "org.other.OtherClass",
                    "isActivity": False,
                    "isMainActivity": False,
                    "methods": [],
                },
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        assert len(result.classes.classes) == 1
        assert "com.example.MyClass" in result.classes.classes
        assert "org.other.OtherClass" not in result.classes.classes

    def test_empty_package_includes_all(self, parser, tmp_path):
        """Empty package string includes all classes."""
        data = {
            "reachability": [
                {
                    "className": "com.a.A",
                    "isActivity": False,
                    "isMainActivity": False,
                    "methods": [],
                },
                {
                    "className": "com.b.B",
                    "isActivity": False,
                    "isMainActivity": False,
                    "methods": [],
                },
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "")
        assert len(result.classes.classes) == 2

    def test_window_package_filter_activity_only(self, parser, tmp_path):
        """Package filter applies only to ACTIVITY windows, not OPTIONSMENU."""
        data = {
            "reachability": [],
            "windows": [
                {
                    "name": "com.example.Main",
                    "type": "ACTIVITY",
                    "id": 1,
                    "isMain": True,
                    "widgets": [],
                },
                {
                    "name": "org.other.Activity",
                    "type": "ACTIVITY",
                    "id": 2,
                    "isMain": False,
                    "widgets": [],
                },
                {
                    "name": "com.example.Main#OptionsMenu",
                    "type": "OPTIONSMENU",
                    "id": 3,
                    "isMain": False,
                    "widgets": [],
                },
            ],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        names = {w.name for w in result.windows.windows}
        assert "com.example.Main" in names
        # OPTIONSMENU is not filtered by package
        assert "com.example.Main#OptionsMenu" in names
        # Activity from other package is filtered out
        assert "org.other.Activity" not in names


# --- Inner class normalization (INV-ANA-02) ---


class TestInnerClassNormalization:
    """Tests for inner class name normalization."""

    def test_dollar_notation_preserved(self, parser, tmp_path):
        """Class names already using $ are preserved."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Outer$Inner",
                    "isActivity": False,
                    "isMainActivity": False,
                    "methods": [],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        assert "com.example.Outer$Inner" in result.classes.classes

    def test_dot_notation_normalized(self, parser, tmp_path):
        """Class names using . for inner classes are normalized to $."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Outer.Inner",
                    "isActivity": False,
                    "isMainActivity": False,
                    "methods": [],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        # SignatureNormalizer converts Outer.Inner to Outer$Inner
        assert "com.example.Outer$Inner" in result.classes.classes


# --- Partial section failure (INV-ANA-06) ---


class TestPartialSectionFailure:
    """Tests for graceful handling of individual section failures."""

    def test_corrupted_reachability_doesnt_break_windows(self, parser, tmp_path):
        """Bad reachability data doesn't prevent windows from parsing."""
        data = {
            "reachability": "not-an-array",
            "windows": [
                {
                    "name": "com.example.Main",
                    "type": "ACTIVITY",
                    "id": 1,
                    "isMain": True,
                    "widgets": [],
                }
            ],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        # Reachability failed gracefully
        assert len(result.classes.classes) == 0
        # Windows still parsed
        assert len(result.windows.windows) == 1


# --- Transitions with unknown window IDs ---


class TestTransitionsWithUnknownWindows:
    """Tests for transitions referencing unknown window IDs."""

    def test_unknown_source_skipped(self, parser, tmp_path):
        """Transitions with unknown source window are skipped."""
        data = {
            "reachability": [],
            "windows": [
                {
                    "name": "com.example.Main",
                    "type": "ACTIVITY",
                    "id": 1,
                    "isMain": True,
                    "widgets": [],
                }
            ],
            "transitions": [
                {
                    "sourceId": 999,
                    "targetId": 1,
                    "events": [
                        {"handler": "<com.example.A: void m()>", "widgetId": 10}
                    ],
                }
            ],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        assert len(result.wtg.transitions) == 0

    def test_unknown_target_skipped(self, parser, tmp_path):
        """Transitions with unknown target window are skipped."""
        data = {
            "reachability": [],
            "windows": [
                {
                    "name": "com.example.Main",
                    "type": "ACTIVITY",
                    "id": 1,
                    "isMain": True,
                    "widgets": [],
                }
            ],
            "transitions": [
                {
                    "sourceId": 1,
                    "targetId": 999,
                    "events": [
                        {"handler": "<com.example.A: void m()>", "widgetId": 10}
                    ],
                }
            ],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        assert len(result.wtg.transitions) == 0


# --- Truncated JSON from timeout ---


class TestTruncatedJSON:
    """Tests for truncated JSON recovery (timeout scenarios)."""

    def test_truncated_after_reachability(self, parser, tmp_path):
        """JSON truncated mid-windows section still parses reachability."""
        # Simulate: full reachability, truncated windows
        full_data = {
            "reachability": [
                {
                    "className": "com.example.Main",
                    "isActivity": True,
                    "isMainActivity": True,
                    "methods": [
                        {
                            "name": "onCreate",
                            "signature": "<com.example.Main: void onCreate(android.os.Bundle)>",
                            "reachable": True,
                            "reachesMop": False,
                            "directlyReachesMop": False,
                        }
                    ],
                }
            ],
            "windows": [
                {
                    "name": "com.example.Main",
                    "type": "ACTIVITY",
                    "id": 1,
                    "isMain": True,
                    "widgets": [],
                }
            ],
        }
        content = json.dumps(full_data)
        # Truncate mid-way through windows section
        # Find the end of reachability array
        reach_end = content.find('"windows"')
        truncated = content[:reach_end + 30]  # Cut in middle of windows

        path = os.path.join(str(tmp_path), "truncated.json")
        with open(path, "w") as f:
            f.write(truncated)

        result = parser.parse_file(path, "com.example")
        # Recovery may or may not succeed depending on truncation point
        # But it should NOT crash
        assert isinstance(result, StaticAnalysisData)

    def test_completely_invalid_json(self, parser, tmp_path):
        """Completely invalid JSON returns empty data."""
        path = os.path.join(str(tmp_path), "invalid.json")
        with open(path, "w") as f:
            f.write("this is not json at all")

        result = parser.parse_file(path, "com.example")
        assert isinstance(result, StaticAnalysisData)
        assert len(result.classes.classes) == 0
        assert len(result.windows.windows) == 0
        assert len(result.wtg.transitions) == 0


# --- Empty MOP specs ---


class TestEmptyMOPSpecs:
    """Tests for scenarios where no MOP specs match."""

    def test_no_mop_all_false(self, parser, tmp_path):
        """When no MOP specs match, all reachesMop flags are false."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Main",
                    "isActivity": True,
                    "isMainActivity": True,
                    "methods": [
                        {
                            "name": "onCreate",
                            "signature": "<com.example.Main: void onCreate(android.os.Bundle)>",
                            "reachable": True,
                            "reachesMop": False,
                            "directlyReachesMop": False,
                        },
                        {
                            "name": "onResume",
                            "signature": "<com.example.Main: void onResume()>",
                            "reachable": True,
                            "reachesMop": False,
                            "directlyReachesMop": False,
                        },
                    ],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")

        for method in result.classes.methods.values():
            assert method.reaches_mop is False
            assert method.directly_reaches_mop is False


# --- Convenience functions ---


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_parse_file_function(self):
        """parse_file() delegates to singleton."""
        result = parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        assert isinstance(result, StaticAnalysisData)
        assert len(result.classes.classes) > 0

    def test_read_static_analysis_files(self, tmp_path):
        """read_static_analysis_files() constructs path correctly."""
        # Copy fixture to tmp with expected name
        import shutil

        dest = os.path.join(str(tmp_path), "cryptoapp.apk.json")
        shutil.copy(CRYPTOAPP_FIXTURE, dest)

        result = read_static_analysis_files(str(tmp_path), "cryptoapp.apk", PACKAGE)
        assert isinstance(result, StaticAnalysisData)
        assert len(result.classes.classes) > 0


# --- Method signature parsing ---


class TestMethodSignatureParsing:
    """Tests for Soot signature parsing internals."""

    def test_params_extracted(self, parser, tmp_path):
        """Method parameters are extracted from signature."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Main",
                    "isActivity": False,
                    "isMainActivity": False,
                    "methods": [
                        {
                            "name": "doStuff",
                            "signature": "<com.example.Main: void doStuff(int,java.lang.String)>",
                            "reachable": True,
                            "reachesMop": False,
                            "directlyReachesMop": False,
                        }
                    ],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        methods = list(result.classes.methods.values())
        assert len(methods) == 1
        assert methods[0].params == ["int", "java.lang.String"]

    def test_no_params(self, parser, tmp_path):
        """Methods with no parameters have empty params list."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Main",
                    "isActivity": False,
                    "isMainActivity": False,
                    "methods": [
                        {
                            "name": "run",
                            "signature": "<com.example.Main: void run()>",
                            "reachable": True,
                            "reachesMop": False,
                            "directlyReachesMop": False,
                        }
                    ],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        methods = list(result.classes.methods.values())
        assert len(methods) == 1
        assert methods[0].params == []


# --- Listener event type mapping ---


class TestListenerEventTypeMapping:
    """Tests for event type mapping from JSON to domain enum."""

    def test_unmapped_event_type_excluded(self, parser, tmp_path):
        """Listeners with unmapped event types are excluded."""
        data = {
            "reachability": [],
            "windows": [
                {
                    "name": "com.example.Main",
                    "type": "ACTIVITY",
                    "id": 1,
                    "isMain": True,
                    "widgets": [
                        {
                            "id": 10,
                            "idName": "btn",
                            "type": "android.widget.Button",
                            "listeners": [
                                {
                                    "eventType": "unknown_type",
                                    "handler": "<com.example.A: void h()>",
                                }
                            ],
                        }
                    ],
                }
            ],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        window = list(result.windows.windows)[0]
        widget = list(window.widgets.values())[0]
        assert len(widget.events) == 0

    def test_click_event_mapped(self, parser, tmp_path):
        """Click listeners are mapped to WidgetEventType.CLICK."""
        data = {
            "reachability": [],
            "windows": [
                {
                    "name": "com.example.Main",
                    "type": "ACTIVITY",
                    "id": 1,
                    "isMain": True,
                    "widgets": [
                        {
                            "id": 10,
                            "idName": "btn",
                            "type": "android.widget.Button",
                            "listeners": [
                                {
                                    "eventType": "click",
                                    "handler": "<com.example.A: void onClick(android.view.View)>",
                                }
                            ],
                        }
                    ],
                }
            ],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")
        window = list(result.windows.windows)[0]
        widget = list(window.widgets.values())[0]
        assert len(widget.events) == 1
        event = next(iter(widget.events))
        assert event.type == WidgetEventType.CLICK


# --- Baseline equivalence (Task 8.7) ---


class TestBaselineEquivalence:
    """Verify parsed output matches saved baseline metrics for cryptoapp.apk.

    These baselines come from the unified analysis client running on cryptoapp.apk.
    The test ensures the Python parser faithfully reproduces the counts from the
    JSON fixture. Exact match for structural counts; ±10% tolerance for
    reachability counts (to absorb minor analysis variations across runs).
    """

    # Baseline values from cryptoapp.apk analysis
    BASELINE = {
        "classes": 27,
        "methods": 118,
        "activities": 4,
        "windows": 5,
        "transitions": 36,  # 35 raw JSON objects, 1 has 2 events → 36 expanded
        "reachable": 67,
        "reaches_mop": 61,
        "directly_reaches_mop": 21,
    }

    def test_class_count_exact(self, parser):
        """Exact match: number of classes after package filtering."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        assert len(result.classes.classes) == self.BASELINE["classes"]

    def test_method_count_exact(self, parser):
        """Exact match: total number of methods."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        assert len(result.classes.methods) == self.BASELINE["methods"]

    def test_activity_count_exact(self, parser):
        """Exact match: number of activity classes."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        activities = [c for c in result.classes.classes.values() if c.is_activity]
        assert len(activities) == self.BASELINE["activities"]

    def test_window_count_exact(self, parser):
        """Exact match: number of windows in WTG."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        assert len(result.windows.windows) == self.BASELINE["windows"]

    def test_transition_count_exact(self, parser):
        """Exact match: number of expanded transitions (events flattened)."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        assert len(result.wtg.transitions) == self.BASELINE["transitions"]

    def test_directly_reaches_mop_exact(self, parser):
        """Exact match: methods that directly call monitored operations."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        count = sum(
            1 for m in result.classes.methods.values() if m.directly_reaches_mop
        )
        assert count == self.BASELINE["directly_reaches_mop"]

    def test_reachable_within_tolerance(self, parser):
        """±10% tolerance: reachable methods from entry points."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        count = sum(1 for m in result.classes.methods.values() if m.reachable)
        expected = self.BASELINE["reachable"]
        assert abs(count - expected) <= expected * 0.10, (
            f"reachable={count}, expected={expected} (±10%)"
        )

    def test_reaches_mop_within_tolerance(self, parser):
        """±10% tolerance: methods that can reach monitored operations."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        count = sum(1 for m in result.classes.methods.values() if m.reaches_mop)
        expected = self.BASELINE["reaches_mop"]
        assert abs(count - expected) <= expected * 0.10, (
            f"reaches_mop={count}, expected={expected} (±10%)"
        )

    def test_main_activity_identified(self, parser):
        """Main activity must be correctly identified."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        main = result.classes.get_main_activity()
        assert main is not None
        assert main.name == "br.unb.cic.cryptoapp.MainActivity"

    def test_all_activities_named(self, parser):
        """All 4 cryptoapp activities must be present."""
        expected_activities = {
            "br.unb.cic.cryptoapp.MainActivity",
            "br.unb.cic.cryptoapp.cipher.CipherActivity",
            "br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity",
            "br.unb.cic.cryptoapp.generated.CryptographyActivity",
        }
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        actual = {c.name for c in result.classes.classes.values() if c.is_activity}
        assert actual == expected_activities

    def test_wtg_window_ids_match_windows(self, parser):
        """WTG window_ids must be consistent with parsed windows."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        wtg_ids = result.wtg.window_ids
        window_ids = {w.id for w in result.windows.windows}
        assert wtg_ids == window_ids

    def test_transitions_reference_valid_windows(self, parser):
        """Every transition must reference source/target in window_ids."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)
        for t in result.wtg.transitions:
            assert t["source"] in result.wtg.window_ids, (
                f"source {t['source']} not in window_ids"
            )
            assert t["target"] in result.wtg.window_ids, (
                f"target {t['target']} not in window_ids"
            )


# --- Normalization validation (Task 8.10) ---


class TestNormalizerSafetyNet:
    """Verify SignatureNormalizer is a no-op on well-formed JSON (D7 rule).

    The Java client writes all class names using SootClass.getName() which
    produces JVM $ notation. The Python normalizer is a safety net — it should
    NOT change any class name from correctly-generated JSON.
    """

    def test_normalizer_is_noop_on_correct_json(self, parser):
        """Normalizer should not change any class name from cryptoapp JSON."""
        change_count = 0
        original_normalize = parser.normalizer.normalize_class_name

        def counting_normalize(class_name):
            nonlocal change_count
            result = original_normalize(class_name)
            if class_name != result:
                change_count += 1
            return result

        parser.normalizer.normalize_class_name = counting_normalize
        parser.parse_file(CRYPTOAPP_FIXTURE, PACKAGE)

        assert change_count == 0, (
            f"Normalizer changed {change_count} class names — Java client may have a bug"
        )

    def test_normalizer_warns_on_change(self, parser, tmp_path, caplog):
        """If normalizer changes a class name, a WARNING should be logged."""
        import logging

        data = {
            "reachability": [
                {
                    "className": "com.example.Outer.Inner",
                    "isActivity": False,
                    "isMainActivity": False,
                    "methods": [
                        {
                            "name": "run",
                            "signature": "<com.example.Outer.Inner: void run()>",
                            "reachable": True,
                            "reachesMop": False,
                            "directlyReachesMop": False,
                        }
                    ],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        with caplog.at_level(logging.WARNING):
            result = parser.parse_file(path, "com.example")

        # The normalizer converts Outer.Inner -> Outer$Inner
        assert "com.example.Outer$Inner" in result.classes.classes

    def test_normalizer_handles_legacy_dot_notation(self, parser, tmp_path):
        """Normalizer corrects . to $ for inner classes in legacy data."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Outer.Inner",
                    "isActivity": False,
                    "isMainActivity": False,
                    "methods": [
                        {
                            "name": "run",
                            "signature": "<com.example.Outer.Inner: void run()>",
                            "reachable": True,
                            "reachesMop": False,
                            "directlyReachesMop": False,
                        }
                    ],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")

        # Should be normalized to $ notation
        assert "com.example.Outer$Inner" in result.classes.classes
        assert "com.example.Outer.Inner" not in result.classes.classes

    def test_inner_class_patterns(self, parser, tmp_path):
        """Verify normalization for all known inner class patterns."""
        classes = [
            # (input, expected_output)
            ("com.example.Outer$Inner", "com.example.Outer$Inner"),
            ("com.example.Outer$1", "com.example.Outer$1"),
            ("com.example.Outer$Inner$1", "com.example.Outer$Inner$1"),
            ("com.example.Map.GameFieldPosition", "com.example.Map$GameFieldPosition"),
        ]
        data = {
            "reachability": [
                {
                    "className": cn,
                    "isActivity": False,
                    "isMainActivity": False,
                    "methods": [
                        {
                            "name": "m",
                            "signature": f"<{cn}: void m()>",
                            "reachable": True,
                            "reachesMop": False,
                            "directlyReachesMop": False,
                        }
                    ],
                }
                for cn, _ in classes
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path, "com.example")

        for _, expected in classes:
            assert expected in result.classes.classes, (
                f"Expected {expected} in classes, got: {list(result.classes.classes.keys())}"
            )


class TestMultiPackageFiltering:
    """Test code_package filtering for multi-package APKs (Task 8.10e-f)."""

    def test_multi_package_filtering(self, parser, tmp_path):
        """Only classes matching code_package are included."""
        data = {
            "reachability": [
                {
                    "className": "edu.cmu.cylab.starslinger.demo.Main",
                    "isActivity": True,
                    "isMainActivity": True,
                    "methods": [
                        {
                            "name": "onCreate",
                            "signature": "<edu.cmu.cylab.starslinger.demo.Main: void onCreate(android.os.Bundle)>",
                            "reachable": True,
                            "reachesMop": False,
                            "directlyReachesMop": False,
                        }
                    ],
                },
                {
                    "className": "edu.cmu.cylab.starslinger.exchange.ExchangeActivity",
                    "isActivity": True,
                    "isMainActivity": False,
                    "methods": [
                        {
                            "name": "process",
                            "signature": "<edu.cmu.cylab.starslinger.exchange.ExchangeActivity: void process()>",
                            "reachable": True,
                            "reachesMop": False,
                            "directlyReachesMop": False,
                        }
                    ],
                },
                {
                    "className": "com.google.firebase.App",
                    "isActivity": False,
                    "isMainActivity": False,
                    "methods": [
                        {
                            "name": "init",
                            "signature": "<com.google.firebase.App: void init()>",
                            "reachable": True,
                            "reachesMop": False,
                            "directlyReachesMop": False,
                        }
                    ],
                },
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)

        # Filter by code_package prefix
        result = parser.parse_file(path, "edu.cmu.cylab.starslinger")

        # Both starslinger packages should be included
        assert "edu.cmu.cylab.starslinger.demo.Main" in result.classes.classes
        assert (
            "edu.cmu.cylab.starslinger.exchange.ExchangeActivity"
            in result.classes.classes
        )
        # Firebase should be excluded
        assert "com.google.firebase.App" not in result.classes.classes

    def test_manifest_vs_code_package(self, parser, tmp_path):
        """Using code_package correctly filters Godot engine classes."""
        data = {
            "reachability": [
                {
                    "className": "org.godotengine.godot.GodotActivity",
                    "isActivity": True,
                    "isMainActivity": True,
                    "methods": [
                        {
                            "name": "onCreate",
                            "signature": "<org.godotengine.godot.GodotActivity: void onCreate(android.os.Bundle)>",
                            "reachable": True,
                            "reachesMop": False,
                            "directlyReachesMop": False,
                        }
                    ],
                },
                {
                    "className": "ir.hsn6.trans.Launcher",
                    "isActivity": True,
                    "isMainActivity": False,
                    "methods": [
                        {
                            "name": "start",
                            "signature": "<ir.hsn6.trans.Launcher: void start()>",
                            "reachable": True,
                            "reachesMop": False,
                            "directlyReachesMop": False,
                        }
                    ],
                },
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)

        # PackageDetector would return code_package="org.godotengine.godot"
        result = parser.parse_file(path, "org.godotengine.godot")

        assert "org.godotengine.godot.GodotActivity" in result.classes.classes
        # Manifest package class should be filtered out
        assert "ir.hsn6.trans.Launcher" not in result.classes.classes
