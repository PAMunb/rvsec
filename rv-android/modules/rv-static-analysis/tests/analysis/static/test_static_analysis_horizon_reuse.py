"""A stored analysis document answers a run only under its own horizon (INV-ANA-102).

`StaticAnalyzer._execute_command` reads the distance horizon a stored
`<apk_name>.json` records (`distMax`, 10 when absent, INV-ANA-99) from the top of
the document, before the scope-key check of INV-ANA-70. A document of another
horizon, or one whose top cannot be read, is removed with a warning and the
analysis runs again. The output mode is not compared.

GATOR is never started: `Command` is patched, and where a test needs the
analysis to run, the patched invocation writes the document a real run would.
The documents are laid out as GATOR writes them, without whitespace.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.app import App
from rv_static_analysis.analysis.static.static_analysis import StaticAnalyzer
from rv_static_analysis.config import DEFAULT_DIST_MAX, RVStaticAnalysisConfig

KEY = "com.example.test"
COMMAND = "rv_static_analysis.analysis.static.static_analysis.Command"


def _document(dist_max: int | None = None, *, compact: bool = False) -> dict:
    """A small document in GATOR's member order, `distMax` only when given."""
    document = {
        "package": KEY,
        "mainActivity": f"{KEY}.Main",
        "codePackage": KEY,
        "codePackageSource": "manifest",
        "class_defs_under_key": 1,
    }
    if dist_max is not None:
        document["distMax"] = dist_max
    if compact:
        document["distancePairs"] = {"weighedMax": 3, "k": 3}
    document["distanceTargets"] = [
        {"signature": f"<{KEY}.Crypto: void encrypt()>", "kind": "direct"}
    ]
    document["components"] = {}
    document["reachability"] = [
        {
            "className": f"{KEY}.Main",
            "componentType": "activity",
            "isMain": True,
            "methods": [
                {
                    "name": "onClick",
                    "signature": f"<{KEY}.Main: void onClick()>",
                    "reachable": True,
                    "reachesTarget": True,
                    "directlyReachesTarget": False,
                    "targetDistances": [[0, 2]],
                }
            ],
        }
    ]
    document["windows"] = [
        {"id": 1, "name": f"{KEY}.Main", "type": "ACTIVITY", "widgets": []}
    ]
    document["transitions"] = [
        {
            "sourceId": 1,
            "targetId": 1,
            "events": [{"widgetId": 7, "eventType": "click"}],
        },
        {
            "sourceId": 1,
            "targetId": 1,
            "events": [{"widgetId": 8, "eventType": "click"}],
        },
    ]
    document["complete"] = True
    return document


def _text(document: dict) -> str:
    return json.dumps(document, separators=(",", ":"))


def _analyzer(tmp_path: Path, dist_max: int | None = None, **config) -> StaticAnalyzer:
    app = MagicMock(spec=App)
    app.name = "app.apk"
    app.package_name = KEY
    app.code_package = KEY
    app.code_package_source = "manifest"
    app.path = str(tmp_path / "app.apk")
    configuration = RVStaticAnalysisConfig(
        validate_on_init=False,
        rvsec_root=str(tmp_path),
        gator_dir=str(tmp_path / "gator"),
        analysis_client_jar=str(tmp_path / "gator" / "client.jar"),
        mop_dir=str(tmp_path / "mop"),
        output_dir=str(tmp_path),
        dist_max=dist_max,
        **config,
    )
    return StaticAnalyzer(app=app, config=configuration, output_dir=str(tmp_path))


def _run(analyzer: StaticAnalyzer, regenerated: str | None = None) -> MagicMock:
    """Run the analysis with GATOR patched out; return the patched `Command`.

    When the analysis runs, the patched invocation writes `regenerated` where
    GATOR would write the document.
    """
    with patch(COMMAND) as command:

        def _write(*_args, **_kwargs):
            Path(analyzer.analysis_file).write_text(regenerated, encoding="utf-8")
            return MagicMock(code=0, stderr=b"")

        command.return_value.invoke.side_effect = _write
        analyzer._run_analysis()
    return command


def _regenerations(caplog) -> list[str]:
    """The warnings `_execute_command` logs when it discards a stored document."""
    return [
        r.getMessage()
        for r in caplog.records
        if r.levelname == "WARNING" and r.getMessage().startswith("Regenerating")
    ]


# --- Scenario: a stored document of another horizon is regenerated ---


@pytest.mark.parametrize("requested", [10, None], ids=["dist-max-10", "no-horizon"])
def test_another_horizon_is_regenerated(tmp_path, caplog, requested):
    analyzer = _analyzer(tmp_path, dist_max=requested)
    Path(analyzer.analysis_file).write_text(_text(_document(15)), encoding="utf-8")
    fresh = _text(_document(requested))

    command = _run(analyzer, regenerated=fresh)

    command.return_value.invoke.assert_called_once()
    assert Path(analyzer.analysis_file).read_text(encoding="utf-8") == fresh
    (warning,) = _regenerations(caplog)
    assert analyzer.analysis_file in warning
    assert "horizon 15" in warning
    assert f"horizon {DEFAULT_DIST_MAX}" in warning


# --- Scenario: a stored document without the member counts as 10 ---


def test_absent_member_is_regenerated_under_another_horizon(tmp_path, caplog):
    analyzer = _analyzer(tmp_path, dist_max=12)
    Path(analyzer.analysis_file).write_text(_text(_document()), encoding="utf-8")

    command = _run(analyzer, regenerated=_text(_document(12)))

    command.return_value.invoke.assert_called_once()
    (warning,) = _regenerations(caplog)
    assert "horizon 10" in warning
    assert "horizon 12" in warning


@pytest.mark.parametrize("requested", [None, 10], ids=["no-horizon", "dist-max-10"])
def test_absent_member_is_reused_under_the_default_horizon(tmp_path, requested):
    analyzer = _analyzer(tmp_path, dist_max=requested)
    stored = _text(_document())
    Path(analyzer.analysis_file).write_text(stored, encoding="utf-8")

    command = _run(analyzer)

    command.return_value.invoke.assert_not_called()
    assert Path(analyzer.analysis_file).read_text(encoding="utf-8") == stored


# --- Scenario: the same horizon is reused without reading the whole document ---


def test_same_horizon_is_reused(tmp_path, caplog):
    analyzer = _analyzer(tmp_path, dist_max=15)
    stored = _text(_document(15))
    Path(analyzer.analysis_file).write_text(stored, encoding="utf-8")

    command = _run(analyzer)

    command.return_value.invoke.assert_not_called()
    assert Path(analyzer.analysis_file).read_text(encoding="utf-8") == stored
    assert _regenerations(caplog) == []


def test_horizon_check_stops_at_the_member_after_dist_max(tmp_path):
    """Bytes that are not JSON right after the member that follows `distMax`
    do not reach the check: it has its answer before them."""
    analyzer = _analyzer(tmp_path, dist_max=15)
    text = _text(_document(15))
    cut = text.index(',"components"')
    Path(analyzer.analysis_file).write_text(text[:cut] + ",@@@ not json", "utf-8")

    assert analyzer._recorded_dist_max(analyzer.analysis_file) == 15


def test_tail_after_distance_targets_that_is_not_json_is_still_reused(tmp_path):
    """The horizon check reads no further than the member after `distMax`, and
    the scope-key check recovers the members read in full (INV-ANA-81), so the
    document is reused."""
    analyzer = _analyzer(tmp_path, dist_max=15)
    text = _text(_document(15))
    stored = text[: text.index(',"components"')] + ",@@@ not json"
    Path(analyzer.analysis_file).write_text(stored, encoding="utf-8")

    command = _run(analyzer)

    command.return_value.invoke.assert_not_called()
    assert Path(analyzer.analysis_file).read_text(encoding="utf-8") == stored


# --- Scenario: the output mode is not compared ---


def test_compact_document_is_reused_under_full_output(tmp_path):
    analyzer = _analyzer(tmp_path, full_output=True)
    stored = _text(_document(compact=True))
    Path(analyzer.analysis_file).write_text(stored, encoding="utf-8")

    command = _run(analyzer)

    command.return_value.invoke.assert_not_called()
    assert Path(analyzer.analysis_file).read_text(encoding="utf-8") == stored


# --- Scenario: a document whose first members cannot be read is regenerated ---


@pytest.mark.parametrize(
    "stored",
    ["", "\x00\x01 not json", '{"package":"com.example.test",@@@'],
    ids=["empty", "not-json", "not-json-inside-the-scope-block"],
)
def test_unreadable_top_is_regenerated(tmp_path, caplog, stored):
    analyzer = _analyzer(tmp_path)
    Path(analyzer.analysis_file).write_text(stored, encoding="utf-8")
    fresh = _text(_document())

    command = _run(analyzer, regenerated=fresh)

    command.return_value.invoke.assert_called_once()
    assert Path(analyzer.analysis_file).read_text(encoding="utf-8") == fresh
    (warning,) = _regenerations(caplog)
    assert analyzer.analysis_file in warning
    assert "cannot be read" in warning


def test_document_that_cannot_be_opened_is_regenerated(tmp_path, caplog):
    # A document gone between the existence check and the read has no readable
    # top: it is regenerated, not a crash of the reuse check.
    analyzer = _analyzer(tmp_path)
    fresh = _text(_document())

    with patch(
        "rv_static_analysis.analysis.static.static_analysis.os.path.isfile",
        return_value=True,
    ):
        command = _run(analyzer, regenerated=fresh)

    command.return_value.invoke.assert_called_once()
    assert Path(analyzer.analysis_file).read_text(encoding="utf-8") == fresh
    (warning,) = _regenerations(caplog)
    assert "cannot be read" in warning


# --- Scenario: a truncated document keeps its horizon readable ---


def test_document_truncated_inside_transitions_keeps_its_horizon(tmp_path, caplog):
    analyzer = _analyzer(tmp_path, dist_max=15)
    text = _text(_document(15))
    second_edge = text.index('{"sourceId"', text.index('"transitions"') + 20)
    stored = text[: second_edge + len('{"sourceId":1,')]
    Path(analyzer.analysis_file).write_text(stored, encoding="utf-8")

    assert analyzer._recorded_dist_max(analyzer.analysis_file) == 15

    command = _run(analyzer)

    command.return_value.invoke.assert_not_called()
    assert _regenerations(caplog) == []


# --- The member's value and the order of the two checks ---


@pytest.mark.parametrize(
    "value",
    ['"15"', "true", "0", "-3", "15.0", "null", "{}", "[15]"],
)
def test_dist_max_that_is_not_an_integer_of_at_least_one_is_unreadable(tmp_path, value):
    analyzer = _analyzer(tmp_path)
    text = _text(_document(15)).replace('"distMax":15', f'"distMax":{value}')
    Path(analyzer.analysis_file).write_text(text, encoding="utf-8")

    assert analyzer._recorded_dist_max(analyzer.analysis_file) is None


def test_object_less_root_is_unreadable(tmp_path):
    analyzer = _analyzer(tmp_path)
    Path(analyzer.analysis_file).write_text("[1,2]", encoding="utf-8")

    assert analyzer._recorded_dist_max(analyzer.analysis_file) is None


def test_scope_key_check_runs_only_when_the_horizons_agree(tmp_path):
    """The scope-key check parses the whole document; a horizon mismatch is
    decided from the top alone, so the parse does not run."""
    mismatched = _analyzer(tmp_path / "mismatch", dist_max=12)
    Path(mismatched.analysis_file).write_text(_text(_document()), encoding="utf-8")
    agreeing = _analyzer(tmp_path / "agree", dist_max=12)
    Path(agreeing.analysis_file).write_text(_text(_document(12)), encoding="utf-8")

    with patch.object(
        StaticAnalyzer, "_disagreeing_recorded_key", return_value=None
    ) as key_check:
        _run(mismatched, regenerated=_text(_document(12)))
        key_check.assert_not_called()

        _run(agreeing)
        key_check.assert_called_once_with(agreeing.analysis_file)
