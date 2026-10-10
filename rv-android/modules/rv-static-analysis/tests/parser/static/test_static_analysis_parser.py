"""Tests for the unified StaticAnalysisParser."""

import json
import os
import pathlib
import shutil
from unittest.mock import MagicMock

import pytest
from rv_android_core.constants import EXTENSION_PARSED_COPY, EXTENSION_STATIC_ANALYSIS
from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType
from rv_android_core.domain.window import Windows, WindowType
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_android_core.util.analysis_document import digest_of_file

import rv_static_analysis.parser.static.static_analysis_parser as parser_module
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

    def test_inv_ana_78_fragment_and_hosted_are_not_activities(
        self, parser, tmp_path
    ):
        """`FRAGMENT` and `HOSTED` windows keep their own type.

        An unmapped type falls back to `ACTIVITY`, which would count every
        `Host#Owner` window as one more activity of its host.
        """
        data = {
            "reachability": [
                {
                    "className": "com.example.MainActivity",
                    "componentType": "activity",
                    "isMain": True,
                    "methods": [],
                }
            ],
            "windows": [
                {
                    "name": "com.example.MainActivity",
                    "type": "ACTIVITY",
                    "id": 1,
                    "isMain": True,
                    "widgets": [],
                },
                {
                    "name": "com.example.MainActivity#com.example.ItemAdapter",
                    "type": "HOSTED",
                    "id": 2,
                    "isMain": False,
                    "widgets": [],
                },
                {
                    "name": "com.example.MainActivity#com.example.ListFragment",
                    "type": "FRAGMENT",
                    "id": 3,
                    "isMain": False,
                    "widgets": [],
                },
            ],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)
        result = parser.parse_file(path)
        types = {w.name: w.type for w in result.windows.windows}
        assert types == {
            "com.example.MainActivity": WindowType.ACTIVITY,
            "com.example.MainActivity#com.example.ItemAdapter": WindowType.HOSTED,
            "com.example.MainActivity#com.example.ListFragment": WindowType.FRAGMENT,
        }
        activities = [
            w for w in result.windows.windows if w.type == WindowType.ACTIVITY
        ]
        assert len(activities) == 1

    def test_inv_ana_78_type_mapping(self, parser):
        assert parser._map_window_type("HOSTED") is WindowType.HOSTED
        assert parser._map_window_type("FRAGMENT") is WindowType.FRAGMENT

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

    def test_dotted_name_is_stored_as_the_artefact_spells_it(self, parser, tmp_path):
        """A dot between two capitalized segments is a package boundary here.

        GATOR writes `SootClass.getName()`, so `com.example.Outer.Inner` names a
        class `Inner` in package `com.example.Outer` — not a nested class. The
        parser used to rewrite it to `Outer$Inner`, which matched nothing the
        weaver ever emitted; that is what INV-ANA-67 forbids.
        """
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
        assert "com.example.Outer.Inner" in result.classes.classes
        assert "com.example.Outer$Inner" not in result.classes.classes


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


def _members_before(document: dict, key: str) -> str:
    """Serialize the members of `document` that precede `key`, then open `key`.

    The text is what a producer killed while writing `key` leaves on disk: every
    earlier member in full, a separator, and the name of the member in progress.
    """
    keys = list(document)
    head = {name: document[name] for name in keys[: keys.index(key)]}
    opening = json.dumps(head)[:-1] + ", " if head else "{"
    return opening + json.dumps(key) + ": "


def _cut_inside_array(document: dict, key: str, index: int, chars: int) -> str:
    """Text cut `chars` characters into element `index` of the array member `key`."""
    items = document[key]
    written = "".join(json.dumps(item) + ", " for item in items[:index])
    return _members_before(document, key) + "[" + written + json.dumps(items[index])[:chars]


def _write_text(tmp_path, text, filename="truncated.json"):
    """Write raw text to a temp file and return its path."""
    path = os.path.join(str(tmp_path), filename)
    with open(path, "w") as f:
        f.write(text)
    return path


def _load_fixture(path=CRYPTOAPP_FIXTURE) -> dict:
    with open(path) as f:
        return json.load(f)


def _model_snapshot(data: StaticAnalysisData) -> dict:
    """Everything a consumer can read from a model, in a comparable form.

    Pydantic equality is not enough here: `Method` and `Widget` override `__eq__`
    to compare one identifying field, so two models differing in a reachability
    flag or a widget's text would compare equal. The dump compares every field;
    the graph edges and each transition's `target_reaches_target` (computed from
    a private index the dump leaves out) are added beside it.
    """
    snapshot = data.model_dump(mode="json")
    snapshot["wtg"]["window_ids"] = sorted(snapshot["wtg"]["window_ids"])
    snapshot["wtg_edges"] = sorted(
        (
            source,
            target,
            [
                (
                    event.widget_id,
                    event.event_type.name,
                    event.method,
                    event.target_window_class,
                    event.target_reaches_target,
                )
                for event in attributes["events"]
            ],
        )
        for source, target, attributes in data.wtg.graph.edges(data=True)
    )
    return snapshot


class TestTruncatedJSON:
    """Recovery of a document cut by a producer killed mid-write (INV-ANA-81).

    Every top-level member read in full is kept; the member being written when
    the input ended, and everything after it, are dropped; `complete` is False
    unless the `complete` member itself was read.

    Outcomes against the bracket repair this recovery supersedes, which closed
    the root object at the last `]` of the text:

    - The two cases this class held before keep their outcome.
      `test_truncated_after_reachability` cuts inside `windows` of a document
      whose last `]` closes `reachability`, so the repair recovered
      `reachability` too — the test only asserted that nothing crashed, and now
      pins the recovered sections. `test_completely_invalid_json` is an empty
      model under both.
    - A cut inside the 12th element of `transitions`, inside `windows`, or
      inside the `components` object returned an empty model under the repair:
      the last `]` closed a nested list (an `events`, `widgets` or
      `intentFilters` array), so the repaired text was still invalid and every
      section was lost. The sections written before the cut are now kept.
    - A document missing only its closing `}` was repaired at the `]` of
      `transitions`, which dropped the `complete: true` written after it, so it
      read as incomplete. The `complete` member was read in full, so `complete`
      is now True.
    - A cut inside the first `reachability` entry is an empty model for
      `classes`, `windows` and `wtg` under both; the members written before
      `reachability` (here `components`) are now kept.
    - A JSON array at the root (`test_non_object_root`) parsed under
      `json.loads` and then raised `AttributeError` from `parse_file`, because
      the scalar reads call `.get` on the list. The streaming read rejects a
      non-object root as not a document, so the result is the empty model.
    """

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
        # Cut 30 characters after the start of the windows member.
        reach_end = content.find('"windows"')
        path = _write_text(tmp_path, content[: reach_end + 30])

        result = parser.parse_file(path)

        assert list(result.classes.classes) == ["com.example.Main"]
        assert len(result.classes.methods) == 1
        assert len(result.windows.windows) == 0
        assert result.complete is False

    def test_cut_inside_twelfth_transition_keeps_earlier_sections(
        self, parser, tmp_path
    ):
        """The spec scenario: `reachability` and `windows` written in full, the
        file ends inside the 12th element of `transitions`."""
        document = _load_fixture()
        path = _write_text(
            tmp_path, _cut_inside_array(document, "transitions", 11, 60)
        )

        # The reference is the complete document without the sections the cut
        # lost: parsing `transitions` back-fills widgets into `windows`, so the
        # windows of the whole document carry widgets the windows section alone
        # does not.
        written = {
            k: v for k, v in document.items() if k not in ("transitions", "complete")
        }
        whole = parser.parse_file(_write_json(tmp_path, written, "written.json"))

        result = parser.parse_file(path)

        recovered = _model_snapshot(result)
        expected = _model_snapshot(whole)
        assert recovered["classes"] == expected["classes"]
        assert recovered["windows"] == expected["windows"]
        assert recovered["components"] == expected["components"]
        assert len(result.wtg.transitions) == 0
        assert result.complete is False

    def test_cut_inside_windows_keeps_reachability(self, parser, tmp_path):
        """The last `]` of this text closes a `widgets` list, not a section."""
        document = _load_fixture()
        path = _write_text(tmp_path, _cut_inside_array(document, "windows", 1, 100))

        result = parser.parse_file(path)

        assert len(result.classes.classes) == 16
        assert len(result.classes.methods) == 106
        assert len(result.windows.windows) == 0
        assert len(result.wtg.transitions) == 0
        assert result.complete is False

    def test_cut_inside_components_object(self, parser, tmp_path):
        """A section that is an object, cut inside one of its nested arrays."""
        document = _load_fixture()
        text = _members_before(document, "components") + json.dumps(
            document["components"]
        )[:300]
        path = _write_text(tmp_path, text)

        result = parser.parse_file(path)

        # Only the scalar members before `components` were complete.
        assert result.class_defs_under_key == 16
        assert len(result.components.activities) == 0
        assert len(result.classes.classes) == 0
        assert result.complete is False

    def test_cut_inside_first_reachability_entry(self, parser, tmp_path):
        """The spec scenario: no complete top-level array of the model's
        sections yields empty classes, windows and wtg."""
        document = _load_fixture()
        path = _write_text(
            tmp_path, _cut_inside_array(document, "reachability", 0, 200)
        )

        result = parser.parse_file(path)

        assert len(result.classes.classes) == 0
        assert len(result.windows.windows) == 0
        assert len(result.wtg.transitions) == 0
        assert result.complete is False
        # `components` precedes `reachability` in the fixture, so it was complete.
        assert len(result.components.activities) == 4

    def test_missing_final_brace_keeps_complete(self, parser, tmp_path):
        """Every member, `complete` included, was read in full; only the root's
        closing brace is missing."""
        with open(CRYPTOAPP_FIXTURE) as f:
            text = f.read().rstrip()
        assert text.endswith("}")
        path = _write_text(tmp_path, text[:-1])

        result = parser.parse_file(path)

        assert _model_snapshot(result) == _model_snapshot(
            parser.parse_file(CRYPTOAPP_FIXTURE)
        )
        assert result.complete is True

    def test_recovery_goes_through_recover_truncated_json(
        self, parser, tmp_path
    ):
        """INV-ANA-81 keeps the entry point's name; the recovery is logged."""
        document = _load_fixture()
        path = _write_text(
            tmp_path, _cut_inside_array(document, "transitions", 11, 60)
        )
        parser.logger = MagicMock()
        recover = MagicMock(wraps=parser._recover_truncated_json)
        parser._recover_truncated_json = recover

        parser.parse_file(path)

        recover.assert_called_once()
        warnings = " ".join(str(c) for c in parser.logger.warning.call_args_list)
        assert path in warnings
        infos = " ".join(str(c) for c in parser.logger.info.call_args_list)
        # package, mainActivity, codePackage, codePackageSource,
        # class_defs_under_key, components, reachability, windows; the dropped
        # distanceTargets is not counted.
        assert "kept 8 " in infos

    def test_completely_invalid_json(self, parser, tmp_path):
        """Completely invalid JSON returns empty data."""
        path = _write_text(tmp_path, "this is not json at all", "invalid.json")

        result = parser.parse_file(path)
        assert isinstance(result, StaticAnalysisData)
        assert len(result.classes.classes) == 0
        assert len(result.windows.windows) == 0
        assert len(result.wtg.transitions) == 0

    def test_empty_file(self, parser, tmp_path):
        """A file with no bytes is not a document: empty model, no exception."""
        path = _write_text(tmp_path, "", "empty.json")

        result = parser.parse_file(path)

        assert len(result.classes.classes) == 0
        assert result.complete is False

    def test_non_object_root(self, parser, tmp_path):
        """A JSON array at the root is not an analysis document."""
        path = _write_text(tmp_path, "[1, 2, 3]", "array.json")

        result = parser.parse_file(path)

        assert len(result.classes.classes) == 0
        assert result.complete is False


# --- Streaming read equals the json.loads read (INV-ANA-80) ---


def _equivalence_documents() -> list[str]:
    """The fixtures plus every baseline the manifest pins, without duplicates.

    Baseline paths in the manifest are relative to the rv-android root.
    """
    rv_android_root = pathlib.Path(__file__).resolve().parents[5]
    manifest = pathlib.Path(FIXTURE_DIR) / "baselines" / "MANIFEST.json"
    with open(manifest) as f:
        entries = json.load(f)["entries"]
    paths = [CRYPTOAPP_FIXTURE, os.path.join(FIXTURE_DIR, "app.notesr_59.apk.json")]
    paths += [str(rv_android_root / entry["baseline_json"]) for entry in entries]
    unique: dict[str, str] = {}
    for path in paths:
        unique.setdefault(os.path.realpath(path), path)
    return list(unique.values())


class TestStreamingEquivalence:
    """The streaming read builds the same model as `json.loads` of the file.

    The reference is built the way the parser read documents before it
    streamed them: the whole text through `json.loads`, then the parser's own
    section methods and scalar reads. Any difference is a difference in the
    dict the section parsers receive, which is what the streaming read must not
    change beyond the two distance members no section parser reads.
    """

    @staticmethod
    def _reference_model(parser, path) -> StaticAnalysisData:
        with open(path, encoding="utf-8") as f:
            data = json.loads(f.read())
        classes = parser._parse_classes(data)
        windows = parser._parse_windows(data, classes)
        index = {
            name: any(m.reaches_target for m in clazz.methods)
            for name, clazz in classes.classes.items()
        }
        wtg = parser._parse_transitions(data, windows, index)
        recorded_defs = data.get("class_defs_under_key")
        return StaticAnalysisData(
            classes,
            windows,
            wtg,
            components=parser._parse_components(data),
            complete=bool(data.get("complete", False)),
            code_package=data.get("codePackage") or None,
            code_package_source=data.get("codePackageSource") or None,
            class_defs_under_key=(
                recorded_defs
                if isinstance(recorded_defs, int) and recorded_defs >= 0
                else None
            ),
        )

    @pytest.mark.parametrize(
        "path", _equivalence_documents(), ids=lambda p: os.path.basename(p)
    )
    def test_model_equals_json_loads_model(self, parser, path):
        streamed = parser.parse_file(path)
        reference = self._reference_model(parser, path)

        assert _model_snapshot(streamed) == _model_snapshot(reference)
        assert len(streamed.classes.methods) > 0

    def test_distance_members_are_not_built(self, parser):
        """cryptoapp carries `distanceTargets` and 38 `targetDistances` lists; the
        dict handed to the section parsers holds neither."""
        with open(CRYPTOAPP_FIXTURE) as f:
            raw = json.load(f)
        assert "distanceTargets" in raw
        assert (
            sum(
                "targetDistances" in m
                for c in raw["reachability"]
                for m in c["methods"]
            )
            == 38
        )

        data, truncated = parser._load_json(CRYPTOAPP_FIXTURE)

        assert truncated is False
        assert "distanceTargets" not in data
        assert not any(
            "targetDistances" in m for c in data["reachability"] for m in c["methods"]
        )


# --- Parsed copy beside the source (INV-ANA-82, -83) ---


class TestParsedCopyCache:
    """`read_static_analysis_files` reuses `<apk>.static.json` keyed by the
    source's digest, and writes it only from a source read in full."""

    APK = "cryptoapp.apk"

    @pytest.fixture
    def results_dir(self, tmp_path):
        shutil.copy(CRYPTOAPP_FIXTURE, tmp_path / (self.APK + EXTENSION_STATIC_ANALYSIS))
        return tmp_path

    def _source(self, results_dir) -> pathlib.Path:
        return results_dir / (self.APK + EXTENSION_STATIC_ANALYSIS)

    def _copy(self, results_dir) -> pathlib.Path:
        return results_dir / (self.APK + EXTENSION_PARSED_COPY)

    def _load_copy(self, results_dir) -> dict:
        with open(self._copy(results_dir)) as f:
            return json.load(f)

    def test_miss_writes_the_copy(self, parser, results_dir):
        result = parser.read_static_analysis_files(str(results_dir), self.APK)

        copy = self._load_copy(results_dir)
        assert copy["source"] == {
            "digest": digest_of_file(str(self._source(results_dir))),
            "generator": "rv-static-analysis/1",
        }
        assert "distanceTargets" not in copy
        assert not any(
            "targetDistances" in m for c in copy["reachability"] for m in c["methods"]
        )
        assert _model_snapshot(result) == _model_snapshot(
            parser.parse_file(CRYPTOAPP_FIXTURE)
        )
        # Nothing but the copy is left beside the source.
        assert sorted(p.name for p in results_dir.iterdir()) == sorted(
            [self._source(results_dir).name, self._copy(results_dir).name]
        )

    def test_hit_reads_the_copy_and_not_the_source(
        self, parser, results_dir, monkeypatch
    ):
        """The spec scenario: the second read of an unchanged source parses the
        copy and reads the source only to digest it."""
        first = parser.read_static_analysis_files(str(results_dir), self.APK)

        def no_stream(*_args, **_kwargs):
            raise AssertionError("the source was streamed on a cache hit")

        monkeypatch.setattr(parser_module, "read_analysis_document", no_stream)
        second = parser.read_static_analysis_files(str(results_dir), self.APK)

        assert _model_snapshot(second) == _model_snapshot(first)

    def test_hit_answers_from_the_copy_contents(self, parser, results_dir):
        """A copy whose digest matches is believed: its contents, not the
        source's, make the model."""
        parser.read_static_analysis_files(str(results_dir), self.APK)
        copy = self._load_copy(results_dir)
        copy["reachability"] = copy["reachability"][:1]
        self._copy(results_dir).write_text(json.dumps(copy))

        result = parser.read_static_analysis_files(str(results_dir), self.APK)

        assert len(result.classes.classes) == 1

    def test_stale_digest_regenerates_the_copy(self, parser, results_dir):
        """The spec scenario: the source changed under the same name."""
        parser.read_static_analysis_files(str(results_dir), self.APK)
        old_digest = self._load_copy(results_dir)["source"]["digest"]

        document = _load_fixture()
        document["reachability"] = document["reachability"][:2]
        self._source(results_dir).write_text(json.dumps(document))
        new_digest = digest_of_file(str(self._source(results_dir)))

        result = parser.read_static_analysis_files(str(results_dir), self.APK)

        assert new_digest != old_digest
        assert self._load_copy(results_dir)["source"]["digest"] == new_digest
        assert len(result.classes.classes) == 2

    @pytest.mark.parametrize(
        "contents",
        ["{not json", "", "[]", '{"reachability": []}', '{"source": "sha256:x"}'],
        ids=["unparseable", "empty", "array", "no-source", "source-not-object"],
    )
    def test_unusable_copy_is_a_miss_and_is_rewritten(
        self, parser, results_dir, contents
    ):
        self._copy(results_dir).write_text(contents)

        result = parser.read_static_analysis_files(str(results_dir), self.APK)

        assert len(result.classes.classes) == 16
        assert self._load_copy(results_dir)["source"]["digest"] == digest_of_file(
            str(self._source(results_dir))
        )

    def test_truncated_source_is_not_cached(self, parser, results_dir):
        """The spec scenario: the recovered model is returned and no copy is
        written, so a later complete document is not shadowed by a recovery."""
        document = _load_fixture()
        self._source(results_dir).write_text(
            _cut_inside_array(document, "transitions", 11, 60)
        )

        result = parser.read_static_analysis_files(str(results_dir), self.APK)

        assert len(result.classes.classes) == 16
        assert len(result.wtg.transitions) == 0
        assert result.complete is False
        assert not self._copy(results_dir).exists()

    def test_missing_source_yields_empty_model_and_no_copy(self, parser, tmp_path):
        result = parser.read_static_analysis_files(str(tmp_path), self.APK)

        assert len(result.classes.classes) == 0
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.skipif(
        hasattr(os, "geteuid") and os.geteuid() == 0,
        reason="root writes into a read-only directory",
    )
    def test_unwritable_directory_returns_the_model(self, parser, results_dir):
        """The spec scenario: the temporary file cannot be created."""
        parser.logger = MagicMock()
        results_dir.chmod(0o555)
        try:
            result = parser.read_static_analysis_files(str(results_dir), self.APK)
            names = sorted(p.name for p in results_dir.iterdir())
        finally:
            results_dir.chmod(0o755)

        assert len(result.classes.classes) == 16
        assert names == [self._source(results_dir).name]
        warnings = " ".join(str(c) for c in parser.logger.warning.call_args_list)
        assert str(self._copy(results_dir)) in warnings

    def test_failed_rename_leaves_no_partial_file(
        self, parser, results_dir, monkeypatch
    ):
        """A failure after the temporary file was written removes it."""
        parser.logger = MagicMock()

        def failing_replace(*_args, **_kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(parser_module.os, "replace", failing_replace)
        result = parser.read_static_analysis_files(str(results_dir), self.APK)

        assert len(result.classes.classes) == 16
        assert [p.name for p in results_dir.iterdir()] == [
            self._source(results_dir).name
        ]
        warnings = " ".join(str(c) for c in parser.logger.warning.call_args_list)
        assert str(self._copy(results_dir)) in warnings

    def test_parse_file_keeps_no_cache(self, parser, results_dir):
        """`parse_file` is the producer side's explicit-path read."""
        parser.parse_file(str(self._source(results_dir)))

        assert not self._copy(results_dir).exists()


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

    # Baseline values for the current cryptoapp.apk analysis. Source-of-truth
    # ledger lives at
    # `modules/rv-static-analysis/tests/resources/baselines/MANIFEST.json`
    # — keep these constants in sync with the `expected_metrics` of the
    # `cryptoapp` entry there.
    #
    # Drop from the gh45/cha-era baseline (27/118/67/61) to the gh51-spark
    # baseline (16/106/55/32) is the intended precision improvement of the
    # cha→spark switch; the historical drop in `classes` to 16 reflects the
    # R$*/BuildConfig filtering also landed during gh57. See
    # openspec/changes/gh60-targets-core/design.md §D12.
    #
    # The two target axes moved again in gh69 (`2a0f5280`), which regenerated
    # the fixture. Both movements are gains in what the matcher can resolve,
    # not drift, and each is attributed to one cause:
    #   - `new` → `<init>` (gh69 D9): Soot names every constructor `<init>`,
    #     so no pointcut written as `Owner.new(..)` had ever resolved a call
    #     site. reaches_target 32→33 (`CryptoUtils.createSecretKeyFromBytes`),
    #     directly_reaches_target 21→23 (plus
    #     `CryptographyActivity.executeSecretKeyOperation`).
    #   - implicit `java.lang` seeding (gh69 phase 5.6): `RandomStringPassword.mop`
    #     names the owner `String` without importing it. The direct axis stays
    #     at 23 — this APK has no call site of the woven signatures — while
    #     reaches_target goes 33→37: the default constructors of MainActivity,
    #     CipherActivity, CryptographyActivity and MessageDigestActivity reach
    #     `String.valueOf(Object)` through the framework call graph.
    BASELINE = {
        "classes": 16,
        "methods": 106,
        "activities": 4,
        "windows": 5,
        "transitions": 36,  # 35 raw JSON objects, 1 has 2 events → 36 expanded
        "reachable": 55,
        "reaches_target": 37,
        "directly_reaches_target": 23,
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


# --- No transformation on the consumption path (INV-ANA-67) ---


class TestArtifactSpellingPreserved:
    """Every identifier reaches a consumer exactly as the artefact spells it.

    The class this replaces asserted that a normalizer was a *no-op* on
    well-formed GATOR output, which was true and beside the point: the
    transformation had no correct case in this pipeline and one wrong case that
    fired on 465 classes across 7 of the 162 corpus artefacts. What is worth
    pinning now is the absence of the transformation, not its harmlessness.
    """

    def test_parser_stores_artifact_spelling(self, parser):
        """No class name from the cryptoapp fixture differs from its own file."""
        on_disk = {
            entry["className"]
            for entry in json.loads(
                pathlib.Path(CRYPTOAPP_FIXTURE).read_text(encoding="utf-8")
            )["reachability"]
        }

        parsed = set(parser.parse_file(CRYPTOAPP_FIXTURE).classes.classes.keys())

        assert parsed == on_disk

    def test_capitalized_package_segment(self, parser, tmp_path):
        """The corpus shape that motivated the removal.

        `com.hwloc.lstopo.ZoomView.ZoomView` is a class `ZoomView` in package
        `com.hwloc.lstopo.ZoomView` — two capitalized segments and no nesting.
        Its 1080 `RVSEC-COV` events name it with the dot; rewriting the static
        side to `ZoomView$ZoomView` matched none of them and published 0.00%.
        """
        dotted = "com.hwloc.lstopo.ZoomView.ZoomView"
        data = {
            "reachability": [
                {
                    "className": dotted,
                    "componentType": None,
                    "isMain": False,
                    "methods": [
                        {
                            "name": "onDraw",
                            "signature": f"<{dotted}: void onDraw()>",
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

        assert dotted in result.classes.classes
        assert "$" not in "".join(result.classes.classes)
        # The signature was always stored verbatim; the point is that the class
        # name now agrees with it, which it did not while the rewrite fired.
        method = next(iter(result.classes.classes[dotted].methods))
        assert method.signature == f"<{dotted}: void onDraw()>"
        assert method.class_name == dotted

    def test_genuine_nesting_survives_untouched(self, parser, tmp_path):
        """`$` in the artefact is real nesting and must be kept as written."""
        names = [
            "com.example.Outer$Inner",
            "com.example.Outer$1",
            "com.example.Outer$Inner$1",
        ]
        data = {
            "reachability": [
                {
                    "className": cn,
                    "componentType": None,
                    "isMain": False,
                    "methods": [],
                }
                for cn in names
            ],
            "windows": [],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)

        result = parser.parse_file(path)

        assert set(result.classes.classes) == set(names)

    def test_window_names_are_not_rewritten_either(self, parser, tmp_path):
        """Both call sites went together, and this is why.

        INV-ANA-60 admits an ACTIVITY window when its class is present in
        `reachability`. Removing only the class-side rewrite would leave window
        names dollar-separated against dotted classes, silently changing which
        activities are admitted — so the membership test is asserted here, not
        just the spelling.
        """
        dotted = "com.hwloc.lstopo.ZoomView.ZoomView"
        data = {
            "reachability": [
                {
                    "className": dotted,
                    "componentType": None,
                    "isMain": False,
                    "methods": [],
                }
            ],
            "windows": [{"id": 1, "name": dotted, "type": "ACTIVITY", "widgets": []}],
            "transitions": [],
        }
        path = _write_json(tmp_path, data)

        result = parser.parse_file(path)

        assert [w.name for w in result.windows.windows] == [dotted]


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
