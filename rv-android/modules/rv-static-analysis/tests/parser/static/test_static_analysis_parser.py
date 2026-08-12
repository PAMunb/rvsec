"""Tests for the unified StaticAnalysisParser."""

import json
import os

import pytest
from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType
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
        result = parser.parse_file(CRYPTOAPP_FIXTURE)

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
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        # 16 app classes after gh57 R$*/BuildConfig filter. The earlier 27
        # came from including generated resource classes, which inflated the
        # coverage denominator. See baselines/MANIFEST.json for the canonical
        # cryptoapp metrics ledger.
        assert len(result.classes.classes) == 16

    def test_method_count(self, parser):
        """Verify expected number of methods from cryptoapp."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        # 106 methods under the post-gh57 R$*/BuildConfig filter.
        assert len(result.classes.methods) == 106

    def test_window_count(self, parser):
        """Verify expected number of windows from cryptoapp."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        assert len(result.windows.windows) == 5

    def test_transition_count(self, parser):
        """Verify expected number of transitions from cryptoapp."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        assert len(result.wtg.transitions) == 36

    def test_main_activity_detected(self, parser):
        """Verify main activity is correctly identified."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        main_clazz = result.classes.get_clazz("br.unb.cic.cryptoapp.MainActivity")
        assert main_clazz is not None
        assert main_clazz.is_main is True

    def test_activity_flag(self, parser):
        """Verify activity classes are marked as activities."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        main_clazz = result.classes.get_clazz("br.unb.cic.cryptoapp.MainActivity")
        assert main_clazz is not None
        assert main_clazz.component_type == "activity"

    def test_parse_service_component_type(self, parser, tmp_path):
        """Test parsing a reachability entry with componentType=service."""
        data = {
            "reachability": [
                {
                    "className": "br.unb.cic.cryptoapp.MyService",
                    "componentType": "service",
                    "isMain": False,
                    "methods": [
                        {
                            "name": "onStartCommand",
                            "signature": "<br.unb.cic.cryptoapp.MyService: int onStartCommand(android.content.Intent,int,int)>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        }
                    ],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        service_clazz = result.classes.get_clazz("br.unb.cic.cryptoapp.MyService")
        assert service_clazz is not None
        assert service_clazz.component_type == "service"
        assert service_clazz.is_main is False
        assert len(service_clazz.methods) == 1

    def test_reachability_flags(self, parser):
        """Verify reachability flags are parsed correctly."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        # At least some methods should be reachable
        reachable_methods = [m for m in result.classes.methods.values() if m.reachable]
        reaches_target = [
            m for m in result.classes.methods.values() if m.reaches_target
        ]
        directly_reaches = [
            m for m in result.classes.methods.values() if m.directly_reaches_target
        ]

        assert len(reachable_methods) > 0
        assert len(reaches_target) > 0
        assert len(directly_reaches) > 0

    def test_window_types(self, parser):
        """Verify different window types are parsed."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        types = {w.type for w in result.windows.windows}
        assert WindowType.ACTIVITY in types
        # cryptoapp has an OptionsMenu
        assert WindowType.OPTIONSMENU in types

    def test_widget_events_parsed(self, parser):
        """Verify widget click listeners are parsed."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
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

    def test_parses_v2_widget_xml_attributes_with_nulls(self, parser, tmp_path):
        """gh57 Group 3: prompt/spinnerMode/contentDescription/tooltipText fields.

        Verify the parser propagates the four new XML attribute fields (None
        when absent in the JSON, literal string when present) into the Widget
        Pydantic model.
        """
        import json

        fixture = {
            "reachability": [
                {
                    "className": "com.example.X",
                    "componentType": "activity",
                    "isMain": True,
                    "methods": [],
                }
            ],
            "windows": [
                {
                    "id": 1,
                    "name": "com.example.X",
                    "type": "ACTIVITY",
                    "isMain": True,
                    "widgets": [
                        {
                            "id": 100,
                            "idName": "spinner_a",
                            "type": "android.widget.Spinner",
                            "text": "",
                            "hint": "",
                            "inputType": "",
                            "entries": [],
                            "prompt": "Pick a color",
                            "spinnerMode": "dialog",
                            "contentDescription": None,
                            "tooltipText": None,
                            "listeners": [],
                        },
                        {
                            "id": 101,
                            "idName": "btn_save",
                            "type": "android.widget.Button",
                            "text": "Save",
                            "hint": "",
                            "inputType": "",
                            "entries": [],
                            "prompt": None,
                            "spinnerMode": None,
                            "contentDescription": "Save button",
                            "tooltipText": "Save the form",
                            "listeners": [],
                        },
                    ],
                }
            ],
            "transitions": [],
        }
        fixture_path = tmp_path / "v2.json"
        fixture_path.write_text(json.dumps(fixture))

        result = parser.parse_file(str(fixture_path))
        window = next(iter(result.windows.windows))
        by_name = {w.name: w for w in window.widgets.values()}

        assert by_name["spinner_a"].prompt == "Pick a color"
        assert by_name["spinner_a"].spinner_mode == "dialog"
        assert by_name["spinner_a"].content_description is None
        assert by_name["spinner_a"].tooltip_text is None
        assert by_name["btn_save"].prompt is None
        assert by_name["btn_save"].spinner_mode is None
        assert by_name["btn_save"].content_description == "Save button"
        assert by_name["btn_save"].tooltip_text == "Save the form"

    def test_click_event_type(self, parser):
        """Verify click events are mapped to CLICK type."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
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
        result = parser.parse_file("/nonexistent/path.json")
        assert isinstance(result, StaticAnalysisData)
        assert len(result.classes.classes) == 0
        assert len(result.windows.windows) == 0
        assert len(result.wtg.transitions) == 0

    def test_none_file_path(self, parser):
        """None file path returns empty StaticAnalysisData."""
        result = parser.parse_file(None)
        assert isinstance(result, StaticAnalysisData)
        assert len(result.classes.classes) == 0

    def test_empty_string_file_path(self, parser):
        """Empty string file path returns empty StaticAnalysisData."""
        result = parser.parse_file("")
        assert isinstance(result, StaticAnalysisData)
        assert len(result.classes.classes) == 0

    def test_empty_json_object(self, parser, tmp_path):
        """Empty JSON object {} returns empty data for all sections."""
        path = _write_json(tmp_path, {})
        result = parser.parse_file(path)
        assert len(result.classes.classes) == 0
        assert len(result.windows.windows) == 0
        assert len(result.wtg.transitions) == 0

    def test_missing_reachability_section(self, parser, tmp_path):
        """JSON without reachability returns empty Classes and no activities.

        With no reachability there is nothing that can answer whether an
        ACTIVITY belongs to the application (INV-ANA-60), so none is admitted.
        The artefact reads as degenerate rather than as an application with
        activities and no methods: coverage then reports a zero denominator on
        both axes instead of a plausible-looking cov_act over framework classes.
        Other window types still enter, so the section itself is not lost.
        """
        data = {
            "windows": [
                {
                    "name": "com.example.Main",
                    "type": "ACTIVITY",
                    "id": 1,
                    "isMain": True,
                    "widgets": [],
                },
                {
                    "name": "com.example.Main#Dialog",
                    "type": "DIALOG",
                    "id": 2,
                    "isMain": False,
                    "widgets": [],
                },
            ],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        assert len(result.classes.classes) == 0
        names = {w.name for w in result.windows.windows}
        assert "com.example.Main" not in names
        assert "com.example.Main#Dialog" in names

    def test_missing_windows_section(self, parser, tmp_path):
        """JSON without windows returns empty Windows."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Main",
                    "componentType": "activity",
                    "isMain": True,
                    "methods": [],
                }
            ],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        assert len(result.classes.classes) == 1
        assert len(result.windows.windows) == 0

    def test_missing_transitions_section(self, parser, tmp_path):
        """JSON without transitions returns empty WTG."""
        data = {
            "reachability": [],
            "windows": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        assert len(result.wtg.transitions) == 0

    def test_empty_reachability_array(self, parser, tmp_path):
        """Empty reachability array returns empty Classes."""
        data = {"reachability": [], "windows": [], "transitions": []}
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        assert len(result.classes.classes) == 0

    def test_empty_windows_array(self, parser, tmp_path):
        """Empty windows array returns empty Windows."""
        data = {"reachability": [], "windows": [], "transitions": []}
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        assert len(result.windows.windows) == 0


# --- The artefact defines its own scope (INV-ANA-59, INV-ANA-60, INV-ANA-61) ---


class TestArtefactDefinesItsOwnScope:
    """The parser loads an artefact at the scope its producer gave it."""

    def test_inv_ana_59_reachability_loaded_whole(self, parser, tmp_path):
        """Every reachability entry is loaded, whatever its namespace.

        GATOR removed the out-of-scope classes before writing the file, so a
        second opinion here could only subtract. An artefact that legitimately
        spans namespaces — an app whose implementation lives under a library's
        package — keeps both.
        """
        data = {
            "reachability": [
                {
                    "className": "com.example.MyClass",
                    "componentType": None,
                    "isMain": False,
                    "methods": [],
                },
                {
                    "className": "org.other.OtherClass",
                    "componentType": None,
                    "isMain": False,
                    "methods": [],
                },
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        assert len(result.classes.classes) == 2
        assert "com.example.MyClass" in result.classes.classes
        assert "org.other.OtherClass" in result.classes.classes

    def test_gh102_applicationid_suffix_full_denominator(self, parser, tmp_path):
        """A build-suffixed applicationId no longer empties the universe.

        The artefact's `package` member is the applicationId as GATOR read it
        (`io.keepalive.android.debug`), which is strictly longer than the
        namespace its own classes live in and contains none of them. This is
        the shape that drove 75 of the 162 Estudo 03 applications to a zero
        denominator while their logcats were full of executed methods.
        """
        data = {
            "package": "io.keepalive.android.debug",
            "reachability": [
                {
                    "className": "io.keepalive.android.MainActivity",
                    "componentType": "activity",
                    "isMain": True,
                    "methods": [
                        {
                            "name": "onCreate",
                            "signature": "<io.keepalive.android.MainActivity: void onCreate(android.os.Bundle)>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        }
                    ],
                },
                {
                    "className": "io.keepalive.android.SettingsActivity",
                    "componentType": "activity",
                    "isMain": False,
                    "methods": [
                        {
                            "name": "onResume",
                            "signature": "<io.keepalive.android.SettingsActivity: void onResume()>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        }
                    ],
                },
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        assert len(result.classes.classes) == 2
        assert len(result.classes.methods) == 2

    def test_inv_ana_60_framework_activity_excluded(self, parser, tmp_path):
        """An ACTIVITY absent from reachability is not the app's to cover.

        GATOR scopes `reachability` but not `windows`, so library and
        framework activities show up in the latter. Admitting them would
        dilute `cov_act` with activities the application does not own.
        """
        data = {
            "reachability": [
                {
                    "className": "com.example.Main",
                    "componentType": "activity",
                    "isMain": True,
                    "methods": [],
                }
            ],
            "windows": [
                {
                    "name": "com.example.Main",
                    "type": "ACTIVITY",
                    "id": 1,
                    "isMain": True,
                    "widgets": [],
                },
                {
                    "name": "androidx.compose.ui.tooling.PreviewActivity",
                    "type": "ACTIVITY",
                    "id": 2,
                    "isMain": False,
                    "widgets": [],
                },
            ],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        names = {w.name for w in result.windows.windows}
        assert "com.example.Main" in names
        assert "androidx.compose.ui.tooling.PreviewActivity" not in names

    def test_inv_ana_60_non_activity_admitted(self, parser, tmp_path):
        """Non-ACTIVITY windows enter regardless of reachability.

        A dialog or an options menu can be a system-provided overlay raised by
        application code, so ownership is not the question being asked of it.
        """
        data = {
            "reachability": [
                {
                    "className": "com.example.Main",
                    "componentType": "activity",
                    "isMain": True,
                    "methods": [],
                }
            ],
            "windows": [
                {
                    "name": "android.app.AlertDialog",
                    "type": "DIALOG",
                    "id": 1,
                    "isMain": False,
                    "widgets": [],
                },
                {
                    "name": "com.example.Main#OptionsMenu",
                    "type": "OPTIONSMENU",
                    "id": 2,
                    "isMain": False,
                    "widgets": [],
                },
            ],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        names = {w.name for w in result.windows.windows}
        assert "android.app.AlertDialog" in names
        assert "com.example.Main#OptionsMenu" in names

    def test_inv_ana_61_no_package_parameter(self):
        """The consumption path carries no key, at either entry point.

        Removing the parameter rather than ignoring it is what makes a stale
        call site fail loudly instead of silently re-scoping a denominator.
        """
        import inspect

        for fn in (
            StaticAnalysisParser.parse_file,
            StaticAnalysisParser.read_static_analysis_files,
            parse_file,
            read_static_analysis_files,
        ):
            params = set(inspect.signature(fn).parameters)
            assert "package" not in params
            assert "code_package" not in params


# --- Inner class normalization (INV-ANA-02) ---


class TestInnerClassNormalization:
    """Tests for inner class name normalization."""

    def test_dollar_notation_preserved(self, parser, tmp_path):
        """Class names already using $ are preserved."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Outer$Inner",
                    "componentType": None,
                    "isMain": False,
                    "methods": [],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        assert "com.example.Outer$Inner" in result.classes.classes

    def test_dot_notation_normalized(self, parser, tmp_path):
        """Class names using . for inner classes are normalized to $."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Outer.Inner",
                    "componentType": None,
                    "isMain": False,
                    "methods": [],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        # SignatureNormalizer converts Outer.Inner to Outer$Inner
        assert "com.example.Outer$Inner" in result.classes.classes


# --- Partial section failure (INV-ANA-06) ---


class TestPartialSectionFailure:
    """Tests for graceful handling of individual section failures."""

    def test_corrupted_reachability_doesnt_break_windows(self, parser, tmp_path):
        """Bad reachability degrades on its own, and takes activities with it.

        The windows section is still parsed (INV-ANA-06): a corrupt
        reachability does not raise out of the parse, and window types that
        need no ownership test still enter. ACTIVITY windows do need one, and
        the only thing that can answer it is the reachability the artefact
        failed to deliver (INV-ANA-60), so they are excluded rather than
        admitted on trust.
        """
        data = {
            "reachability": "not-an-array",
            "windows": [
                {
                    "name": "com.example.Main",
                    "type": "ACTIVITY",
                    "id": 1,
                    "isMain": True,
                    "widgets": [],
                },
                {
                    "name": "com.example.Main#OptionsMenu",
                    "type": "OPTIONSMENU",
                    "id": 2,
                    "isMain": False,
                    "widgets": [],
                },
            ],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        # Reachability failed gracefully
        assert len(result.classes.classes) == 0
        # The windows section itself survived the corrupt sibling section
        names = {w.name for w in result.windows.windows}
        assert "com.example.Main#OptionsMenu" in names
        assert "com.example.Main" not in names


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
        result = parser.parse_file(path)
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
        result = parser.parse_file(path)
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
                    "componentType": "activity",
                    "isMain": True,
                    "methods": [
                        {
                            "name": "onCreate",
                            "signature": "<com.example.Main: void onCreate(android.os.Bundle)>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
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
        truncated = content[: reach_end + 30]  # Cut in middle of windows

        path = os.path.join(str(tmp_path), "truncated.json")
        with open(path, "w") as f:
            f.write(truncated)

        result = parser.parse_file(path)
        # Recovery may or may not succeed depending on truncation point
        # But it should NOT crash
        assert isinstance(result, StaticAnalysisData)

    def test_completely_invalid_json(self, parser, tmp_path):
        """Completely invalid JSON returns empty data."""
        path = os.path.join(str(tmp_path), "invalid.json")
        with open(path, "w") as f:
            f.write("this is not json at all")

        result = parser.parse_file(path)
        assert isinstance(result, StaticAnalysisData)
        assert len(result.classes.classes) == 0
        assert len(result.windows.windows) == 0
        assert len(result.wtg.transitions) == 0


# --- Empty MOP specs ---


class TestEmptyMOPSpecs:
    """Tests for scenarios where no MOP specs match."""

    def test_no_mop_all_false(self, parser, tmp_path):
        """When no MOP specs match, all reachesTarget flags are false."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Main",
                    "componentType": "activity",
                    "isMain": True,
                    "methods": [
                        {
                            "name": "onCreate",
                            "signature": "<com.example.Main: void onCreate(android.os.Bundle)>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        },
                        {
                            "name": "onResume",
                            "signature": "<com.example.Main: void onResume()>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        },
                    ],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)

        for method in result.classes.methods.values():
            assert method.reaches_target is False
            assert method.directly_reaches_target is False


# --- Convenience functions ---


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_parse_file_function(self):
        """parse_file() delegates to singleton."""
        result = parse_file(CRYPTOAPP_FIXTURE)
        assert isinstance(result, StaticAnalysisData)
        assert len(result.classes.classes) > 0

    def test_read_static_analysis_files(self, tmp_path):
        """read_static_analysis_files() constructs path correctly."""
        # Copy fixture to tmp with expected name
        import shutil

        dest = os.path.join(str(tmp_path), "cryptoapp.apk.json")
        shutil.copy(CRYPTOAPP_FIXTURE, dest)

        result = read_static_analysis_files(str(tmp_path), "cryptoapp.apk")
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
                    "componentType": None,
                    "isMain": False,
                    "methods": [
                        {
                            "name": "doStuff",
                            "signature": "<com.example.Main: void doStuff(int,java.lang.String)>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        }
                    ],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        methods = list(result.classes.methods.values())
        assert len(methods) == 1
        assert methods[0].params == ["int", "java.lang.String"]

    def test_no_params(self, parser, tmp_path):
        """Methods with no parameters have empty params list."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Main",
                    "componentType": None,
                    "isMain": False,
                    "methods": [
                        {
                            "name": "run",
                            "signature": "<com.example.Main: void run()>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        }
                    ],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        methods = list(result.classes.methods.values())
        assert len(methods) == 1
        assert methods[0].params == []


# --- Listener event type mapping ---


class TestListenerEventTypeMapping:
    """Tests for event type mapping from JSON to domain enum."""

    def test_unmapped_event_type_excluded(self, parser, tmp_path):
        """Listeners with unmapped event types are excluded."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Main",
                    "componentType": "activity",
                    "isMain": True,
                    "methods": [],
                }
            ],
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
        result = parser.parse_file(path)
        window = list(result.windows.windows)[0]
        widget = list(window.widgets.values())[0]
        assert len(widget.events) == 0

    def test_click_event_mapped(self, parser, tmp_path):
        """Click listeners are mapped to WidgetEventType.CLICK."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Main",
                    "componentType": "activity",
                    "isMain": True,
                    "methods": [],
                }
            ],
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
        result = parser.parse_file(path)
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

    # Baseline values for the current cryptoapp.apk analysis. Regenerated
    # 2026-05-26 against the post-gh60 jar (spark default per gh51 D5 + gh57
    # schema with components + ADR-6 complete sentinel + C1f reachesTarget
    # key naming). Source-of-truth ledger lives at
    # `modules/rv-static-analysis/tests/resources/baselines/MANIFEST.json`
    # — keep these constants in sync with the `expected_metrics` of the
    # `cryptoapp` entry there.
    #
    # Drop from the gh45/cha-era baseline (27/118/67/61) to the gh51-spark
    # baseline (16/106/55/32) is the intended precision improvement of the
    # cha→spark switch; the historical drop in `classes` to 16 reflects the
    # R$*/BuildConfig filtering also landed during gh57. See
    # openspec/changes/gh60-targets-core/design.md §D12.
    BASELINE = {
        "classes": 16,
        "methods": 106,
        "activities": 4,
        "windows": 5,
        "transitions": 36,  # 35 raw JSON objects, 1 has 2 events → 36 expanded
        "reachable": 55,
        "reaches_target": 32,
        "directly_reaches_target": 21,
    }

    def test_class_count_exact(self, parser):
        """Exact match: number of classes after package filtering."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        assert len(result.classes.classes) == self.BASELINE["classes"]

    def test_method_count_exact(self, parser):
        """Exact match: total number of methods."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        assert len(result.classes.methods) == self.BASELINE["methods"]

    def test_activity_count_exact(self, parser):
        """Exact match: number of activity classes."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        activities = [
            c for c in result.classes.classes.values() if c.component_type == "activity"
        ]
        assert len(activities) == self.BASELINE["activities"]

    def test_window_count_exact(self, parser):
        """Exact match: number of windows in WTG."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        assert len(result.windows.windows) == self.BASELINE["windows"]

    def test_transition_count_exact(self, parser):
        """Exact match: number of expanded transitions (events flattened)."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        assert len(result.wtg.transitions) == self.BASELINE["transitions"]

    def test_directly_reaches_target_exact(self, parser):
        """Exact match: methods that directly call monitored operations."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        count = sum(
            1 for m in result.classes.methods.values() if m.directly_reaches_target
        )
        assert count == self.BASELINE["directly_reaches_target"]

    def test_reachable_within_tolerance(self, parser):
        """±10% tolerance: reachable methods from entry points."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        count = sum(1 for m in result.classes.methods.values() if m.reachable)
        expected = self.BASELINE["reachable"]
        assert (
            abs(count - expected) <= expected * 0.10
        ), f"reachable={count}, expected={expected} (±10%)"

    def test_reaches_target_within_tolerance(self, parser):
        """±10% tolerance: methods that can reach monitored operations."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        count = sum(1 for m in result.classes.methods.values() if m.reaches_target)
        expected = self.BASELINE["reaches_target"]
        assert (
            abs(count - expected) <= expected * 0.10
        ), f"reaches_target={count}, expected={expected} (±10%)"

    def test_main_activity_identified(self, parser):
        """Main activity must be correctly identified."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
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
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        actual = {
            c.name
            for c in result.classes.classes.values()
            if c.component_type == "activity"
        }
        assert actual == expected_activities

    def test_wtg_window_ids_match_windows(self, parser):
        """WTG window_ids must be consistent with parsed windows."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        wtg_ids = result.wtg.window_ids
        window_ids = {w.id for w in result.windows.windows}
        assert wtg_ids == window_ids

    def test_transitions_reference_valid_windows(self, parser):
        """Every transition must reference source/target in window_ids."""
        result = parser.parse_file(CRYPTOAPP_FIXTURE)
        for t in result.wtg.transitions:
            assert (
                t["source"] in result.wtg.window_ids
            ), f"source {t['source']} not in window_ids"
            assert (
                t["target"] in result.wtg.window_ids
            ), f"target {t['target']} not in window_ids"


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
        parser.parse_file(CRYPTOAPP_FIXTURE)

        assert (
            change_count == 0
        ), f"Normalizer changed {change_count} class names — Java client may have a bug"

    def test_normalizer_warns_on_change(self, parser, tmp_path, caplog):
        """If normalizer changes a class name, a WARNING should be logged."""
        import logging

        data = {
            "reachability": [
                {
                    "className": "com.example.Outer.Inner",
                    "componentType": None,
                    "isMain": False,
                    "methods": [
                        {
                            "name": "run",
                            "signature": "<com.example.Outer.Inner: void run()>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        }
                    ],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        with caplog.at_level(logging.WARNING):
            result = parser.parse_file(path)

        # The normalizer converts Outer.Inner -> Outer$Inner
        assert "com.example.Outer$Inner" in result.classes.classes

    def test_normalizer_handles_legacy_dot_notation(self, parser, tmp_path):
        """Normalizer corrects . to $ for inner classes in legacy data."""
        data = {
            "reachability": [
                {
                    "className": "com.example.Outer.Inner",
                    "componentType": None,
                    "isMain": False,
                    "methods": [
                        {
                            "name": "run",
                            "signature": "<com.example.Outer.Inner: void run()>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        }
                    ],
                }
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)

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
                    "componentType": None,
                    "isMain": False,
                    "methods": [
                        {
                            "name": "m",
                            "signature": f"<{cn}: void m()>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        }
                    ],
                }
                for cn, _ in classes
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)

        for _, expected in classes:
            assert (
                expected in result.classes.classes
            ), f"Expected {expected} in classes, got: {list(result.classes.classes.keys())}"


class TestMultiPackageArtefacts:
    """Artefacts whose classes span more than one namespace.

    These are the cases that used to motivate a key on this side, and they are
    exactly the cases a key gets wrong. The producer already decided what
    belongs; whatever it wrote is the application.
    """

    def test_multi_namespace_artefact_loaded_whole(self, parser, tmp_path):
        """Every namespace GATOR kept is loaded, including a library's."""
        data = {
            "reachability": [
                {
                    "className": "edu.cmu.cylab.starslinger.demo.Main",
                    "componentType": "activity",
                    "isMain": True,
                    "methods": [
                        {
                            "name": "onCreate",
                            "signature": "<edu.cmu.cylab.starslinger.demo.Main: void onCreate(android.os.Bundle)>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        }
                    ],
                },
                {
                    "className": "edu.cmu.cylab.starslinger.exchange.ExchangeActivity",
                    "componentType": "activity",
                    "isMain": False,
                    "methods": [
                        {
                            "name": "process",
                            "signature": "<edu.cmu.cylab.starslinger.exchange.ExchangeActivity: void process()>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        }
                    ],
                },
                {
                    "className": "com.google.firebase.App",
                    "componentType": None,
                    "isMain": False,
                    "methods": [
                        {
                            "name": "init",
                            "signature": "<com.google.firebase.App: void init()>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        }
                    ],
                },
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)

        result = parser.parse_file(path)

        assert "edu.cmu.cylab.starslinger.demo.Main" in result.classes.classes
        assert (
            "edu.cmu.cylab.starslinger.exchange.ExchangeActivity"
            in result.classes.classes
        )
        # A GATOR that kept com.google.firebase.App decided it is in scope for
        # this analysis. Second-guessing that here is what INV-ANA-59 forbids.
        assert "com.google.firebase.App" in result.classes.classes

    def test_implementation_namespace_differs_from_applicationid(
        self, parser, tmp_path
    ):
        """A Godot game keeps both its launcher and the engine classes.

        Manifest `ir.hsn6.trans`, implementation `org.godotengine.godot`: no
        single key admits both, which is why the key had to go rather than get
        better. The artefact answers it — GATOR wrote both, so both count.
        """
        data = {
            "reachability": [
                {
                    "className": "org.godotengine.godot.GodotActivity",
                    "componentType": "activity",
                    "isMain": True,
                    "methods": [
                        {
                            "name": "onCreate",
                            "signature": "<org.godotengine.godot.GodotActivity: void onCreate(android.os.Bundle)>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        }
                    ],
                },
                {
                    "className": "ir.hsn6.trans.Launcher",
                    "componentType": "activity",
                    "isMain": False,
                    "methods": [
                        {
                            "name": "start",
                            "signature": "<ir.hsn6.trans.Launcher: void start()>",
                            "reachable": True,
                            "reachesTarget": False,
                            "directlyReachesTarget": False,
                        }
                    ],
                },
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)

        result = parser.parse_file(path)

        assert "org.godotengine.godot.GodotActivity" in result.classes.classes
        assert "ir.hsn6.trans.Launcher" in result.classes.classes


# --- Components parsing ---


class TestComponentsParsing:
    """Tests for components{} section parsing."""

    def test_parse_activities_with_intent_filters(self, parser, tmp_path):
        json_data = {
            "reachability": [],
            "windows": [],
            "transitions": [],
            "components": {
                "activities": [
                    {
                        "className": "com.example.MainActivity",
                        "isMain": True,
                        "intentFilters": [
                            {
                                "actions": ["android.intent.action.MAIN"],
                                "categories": ["android.intent.category.LAUNCHER"],
                            }
                        ],
                        "exported": True,
                        "reachesTarget": False,
                        "targetMethods": [],
                    }
                ],
                "receivers": [],
                "services": [],
                "providers": [],
            },
        }
        path = _write_json(tmp_path, json_data)
        result = parser.parse_file(str(path))
        assert len(result.components.activities) == 1
        activity = result.components.activities[0]
        assert activity.class_name == "com.example.MainActivity"
        assert activity.is_main is True
        assert activity.exported is True
        assert len(activity.intent_filters) == 1
        assert activity.intent_filters[0].actions == ["android.intent.action.MAIN"]
        assert activity.intent_filters[0].categories == [
            "android.intent.category.LAUNCHER"
        ]

    def test_parse_providers_with_authorities(self, parser, tmp_path):
        json_data = {
            "reachability": [],
            "windows": [],
            "transitions": [],
            "components": {
                "activities": [],
                "receivers": [],
                "services": [],
                "providers": [
                    {
                        "className": "com.example.DataProvider",
                        "isMain": False,
                        "authorities": "com.example.data",
                        "exported": False,
                        "reachesTarget": True,
                        "targetMethods": ["<com.example.DataProvider: Cursor query()>"],
                    }
                ],
            },
        }
        path = _write_json(tmp_path, json_data)
        result = parser.parse_file(str(path))
        assert len(result.components.providers) == 1
        provider = result.components.providers[0]
        assert provider.class_name == "com.example.DataProvider"
        assert provider.component_type == "provider"
        assert provider.is_main is False
        assert provider.authorities == "com.example.data"
        assert provider.reaches_target is True
        assert len(provider.target_methods) == 1
        assert provider.intent_filters == []

    def test_parse_all_component_types(self, parser, tmp_path):
        json_data = {
            "reachability": [],
            "windows": [],
            "transitions": [],
            "components": {
                "activities": [
                    {
                        "className": "com.example.Act",
                        "isMain": True,
                        "intentFilters": [],
                        "exported": True,
                        "reachesTarget": False,
                        "targetMethods": [],
                    }
                ],
                "receivers": [
                    {
                        "className": "com.example.Recv",
                        "isMain": False,
                        "intentFilters": [],
                        "exported": True,
                        "reachesTarget": False,
                        "targetMethods": [],
                    }
                ],
                "services": [
                    {
                        "className": "com.example.Svc",
                        "isMain": False,
                        "intentFilters": [],
                        "exported": False,
                        "reachesTarget": True,
                        "targetMethods": ["sig"],
                    }
                ],
                "providers": [
                    {
                        "className": "com.example.Prov",
                        "authorities": "auth",
                        "exported": False,
                        "reachesTarget": False,
                        "targetMethods": [],
                    }
                ],
            },
        }
        path = _write_json(tmp_path, json_data)
        result = parser.parse_file(str(path))
        assert len(result.components.activities) == 1
        assert len(result.components.receivers) == 1
        assert len(result.components.services) == 1
        assert len(result.components.providers) == 1
        assert result.components.services[0].reaches_target is True

    def test_missing_components_section(self, parser, tmp_path):
        json_data = {"reachability": [], "windows": [], "transitions": []}
        path = _write_json(tmp_path, json_data)
        result = parser.parse_file(str(path))
        assert len(result.components.get_all()) == 0

    def test_empty_components_section(self, parser, tmp_path):
        json_data = {
            "reachability": [],
            "windows": [],
            "transitions": [],
            "components": {},
        }
        path = _write_json(tmp_path, json_data)
        result = parser.parse_file(str(path))
        assert len(result.components.get_all()) == 0

    def test_malformed_components_section(self, parser, tmp_path):
        json_data = {
            "reachability": [],
            "windows": [],
            "transitions": [],
            "components": "not_an_object",
        }
        path = _write_json(tmp_path, json_data)
        result = parser.parse_file(str(path))
        assert len(result.components.get_all()) == 0

    def test_target_methods_parsed(self, parser, tmp_path):
        json_data = {
            "reachability": [],
            "windows": [],
            "transitions": [],
            "components": {
                "activities": [],
                "receivers": [
                    {
                        "className": "com.example.Recv",
                        "isMain": False,
                        "intentFilters": [
                            {
                                "actions": ["android.intent.action.BOOT_COMPLETED"],
                                "categories": [],
                            }
                        ],
                        "exported": True,
                        "reachesTarget": True,
                        "targetMethods": [
                            "<com.example.Recv: void onReceive(Context,Intent)>"
                        ],
                    }
                ],
                "services": [],
                "providers": [],
            },
        }
        path = _write_json(tmp_path, json_data)
        result = parser.parse_file(str(path))
        recv = result.components.receivers[0]
        assert recv.reaches_target is True
        assert recv.target_methods == [
            "<com.example.Recv: void onReceive(Context,Intent)>"
        ]
        assert recv.exported is True

    def test_exported_flag(self, parser, tmp_path):
        json_data = {
            "reachability": [],
            "windows": [],
            "transitions": [],
            "components": {
                "activities": [],
                "receivers": [],
                "services": [
                    {
                        "className": "com.example.Svc1",
                        "isMain": False,
                        "intentFilters": [],
                        "exported": True,
                        "reachesTarget": False,
                        "targetMethods": [],
                    },
                    {
                        "className": "com.example.Svc2",
                        "isMain": False,
                        "intentFilters": [],
                        "exported": False,
                        "reachesTarget": False,
                        "targetMethods": [],
                    },
                ],
                "providers": [],
            },
        }
        path = _write_json(tmp_path, json_data)
        result = parser.parse_file(str(path))
        exported = result.components.get_exported_components()
        assert len(exported) == 1
        assert exported[0].class_name == "com.example.Svc1"


class TestComponentsD15Enrichment:
    """D15 (2026-05-29) — intent-filter data block + permission fields.

    Validates the manual-trigger surface aperv consumes: deep-link
    schemes/hosts/paths/mimeTypes per intent filter, plus per-component
    permission and provider-specific read/write permissions. Includes
    pre-D15 back-compat round-trips so an older JSON without the new
    keys parses into ComponentInfo with empty/None defaults.
    """

    def test_intent_filter_data_block_roundtrip(self, parser, tmp_path):
        """Full data block in JSON -> populated IntentFilter."""
        json_data = {
            "package": "com.example",
            "mainActivity": "com.example.Main",
            "reachability": [],
            "windows": [],
            "transitions": [],
            "complete": True,
            "components": {
                "activities": [
                    {
                        "className": "com.example.Main",
                        "isMain": True,
                        "intentFilters": [
                            {
                                "actions": ["android.intent.action.VIEW"],
                                "categories": ["android.intent.category.BROWSABLE"],
                                "data": {
                                    "schemes": ["myapp", "https"],
                                    "hosts": ["example.com"],
                                    "ports": [443],
                                    "paths": ["/exact"],
                                    "pathPrefixes": ["/api/"],
                                    "pathPatterns": ["/items/.*"],
                                    "mimeTypes": ["image/*"],
                                },
                            }
                        ],
                        "exported": True,
                        "permission": None,
                        "reachesTarget": False,
                        "targetMethods": [],
                    }
                ],
                "receivers": [],
                "services": [],
                "providers": [],
            },
        }
        path = _write_json(tmp_path, json_data)
        result = parser.parse_file(str(path))
        f = result.components.activities[0].intent_filters[0]
        assert f.data_schemes == ["myapp", "https"]
        assert f.data_hosts == ["example.com"]
        assert f.data_ports == [443]
        assert f.data_paths == ["/exact"]
        assert f.data_path_prefixes == ["/api/"]
        assert f.data_path_patterns == ["/items/.*"]
        assert f.data_mime_types == ["image/*"]

    def test_intent_filter_pre_d15_back_compat(self, parser, tmp_path):
        """Pre-D15 JSON (no 'data' key) -> IntentFilter has empty defaults."""
        json_data = {
            "package": "com.example",
            "mainActivity": "com.example.Main",
            "reachability": [],
            "windows": [],
            "transitions": [],
            "complete": True,
            "components": {
                "activities": [
                    {
                        "className": "com.example.Main",
                        "isMain": True,
                        "intentFilters": [
                            {
                                "actions": ["android.intent.action.MAIN"],
                                "categories": ["android.intent.category.LAUNCHER"],
                            }
                        ],
                        "exported": True,
                        "reachesTarget": False,
                        "targetMethods": [],
                    }
                ],
                "receivers": [],
                "services": [],
                "providers": [],
            },
        }
        path = _write_json(tmp_path, json_data)
        result = parser.parse_file(str(path))
        f = result.components.activities[0].intent_filters[0]
        assert f.actions == ["android.intent.action.MAIN"]
        assert f.data_schemes == []
        assert f.data_hosts == []
        assert f.data_mime_types == []

    def test_component_permission_some_none(self, parser, tmp_path):
        """activities with permission=string and permission=null both parse."""
        json_data = {
            "package": "com.example",
            "mainActivity": "",
            "reachability": [],
            "windows": [],
            "transitions": [],
            "complete": True,
            "components": {
                "activities": [
                    {
                        "className": "com.example.A",
                        "isMain": False,
                        "intentFilters": [],
                        "exported": True,
                        "permission": "android.permission.READ_CONTACTS",
                        "reachesTarget": False,
                        "targetMethods": [],
                    },
                    {
                        "className": "com.example.B",
                        "isMain": False,
                        "intentFilters": [],
                        "exported": True,
                        "permission": None,
                        "reachesTarget": False,
                        "targetMethods": [],
                    },
                ],
                "receivers": [],
                "services": [],
                "providers": [],
            },
        }
        path = _write_json(tmp_path, json_data)
        result = parser.parse_file(str(path))
        a, b = result.components.activities
        assert a.permission == "android.permission.READ_CONTACTS"
        assert b.permission is None

    def test_provider_separate_permissions(self, parser, tmp_path):
        """Provider with readPermission/writePermission distinct."""
        json_data = {
            "package": "com.example",
            "mainActivity": "",
            "reachability": [],
            "windows": [],
            "transitions": [],
            "complete": True,
            "components": {
                "activities": [],
                "receivers": [],
                "services": [],
                "providers": [
                    {
                        "className": "com.example.P",
                        "isMain": False,
                        "authorities": "com.example.p",
                        "exported": True,
                        "permission": "com.example.BASE_PERM",
                        "readPermission": "com.example.READ_PERM",
                        "writePermission": "com.example.WRITE_PERM",
                        "reachesTarget": False,
                        "targetMethods": [],
                    }
                ],
            },
        }
        path = _write_json(tmp_path, json_data)
        result = parser.parse_file(str(path))
        p = result.components.providers[0]
        assert p.permission == "com.example.BASE_PERM"
        assert p.read_permission == "com.example.READ_PERM"
        assert p.write_permission == "com.example.WRITE_PERM"

    def test_provider_pre_d15_back_compat(self, parser, tmp_path):
        """Pre-D15 provider (no permission keys) -> None defaults preserved."""
        json_data = {
            "package": "com.example",
            "mainActivity": "",
            "reachability": [],
            "windows": [],
            "transitions": [],
            "complete": True,
            "components": {
                "activities": [],
                "receivers": [],
                "services": [],
                "providers": [
                    {
                        "className": "com.example.P",
                        "isMain": False,
                        "authorities": "com.example.p",
                        "exported": True,
                        "reachesTarget": False,
                        "targetMethods": [],
                    }
                ],
            },
        }
        path = _write_json(tmp_path, json_data)
        result = parser.parse_file(str(path))
        p = result.components.providers[0]
        assert p.permission is None
        assert p.read_permission is None
        assert p.write_permission is None
