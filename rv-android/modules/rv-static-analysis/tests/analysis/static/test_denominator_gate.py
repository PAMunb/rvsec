"""The denominator gate: what it refuses, what it admits, and where it is wired.

Two layers, and both are needed. The bare-function tests pin the three refusals
and the one admission that matters (a genuinely tiny app). The wiring tests
exercise `StaticAnalyzer.analyze()` rather than the function — without them the
gate can be written, never called, and every other test here stays green.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.app import App
from rv_android_core.domain.classes import Classes
from rv_static_analysis.analysis.static.denominator_gate import (
    MIN_PARSED_RATIO,
    REFUSED_ARTIFACT_SUFFIX,
    DenominatorImplausibleError,
    check_denominator,
)
from rv_static_analysis.analysis.static.static_analysis import StaticAnalyzer
from rv_static_analysis.config import RVStaticAnalysisConfig


def _classes(n: int, prefix: str = "com.example.app") -> Classes:
    c = Classes()
    for i in range(n):
        c.add_clazz(f"{prefix}.C{i}", None, False)
    return c


@pytest.fixture
def mock_app():
    app = MagicMock(spec=App)
    app.name = "app"
    app.package_name = "com.example.app"
    app.code_package = "com.example.app"
    app.code_package_source = "manifest"
    app.path = "/path/to/app.apk"
    return app


@pytest.fixture
def output_dir():
    return "/tmp/test_output_gate"


@pytest.fixture
def mock_config():
    config = MagicMock(spec=RVStaticAnalysisConfig)
    config.output_dir = "/tmp/test_output_gate"
    config.analysis_timeout = 600
    return config


class TestCheckDenominator:
    def test_admits_a_healthy_denominator(self):
        check_denominator(_classes(762), 762, "br.com.colman.petals")

    def test_admits_a_genuinely_small_app(self):
        """18 parsed against 18 compiled is 1.0, not a small number.

        `com.tananaev.passportreader` is the case an absolute floor would have
        rejected. Note the compiled count is already net: ten of its classes are
        `.R` and `R$*`, which is why the raw ratio was 18/28 = 0.64 and the
        corrected one is 1.0. The gate divides; it does not subtract.
        """
        check_denominator(_classes(18), 18, "com.tananaev.passportreader")

    def test_refuses_the_degenerate_case(self):
        """1 of 762 — `br.com.colman.petals`, ratio 0.0013."""
        with pytest.raises(DenominatorImplausibleError) as exc:
            check_denominator(_classes(1), 762, "br.com.colman.petals")
        message = str(exc.value)
        assert "1" in message and "762" in message
        assert "br.com.colman.petals" in message

    def test_refuses_an_empty_denominator(self):
        with pytest.raises(DenominatorImplausibleError) as exc:
            check_denominator(Classes(), 535, "com.github.cvzi")
        assert "com.github.cvzi" in str(exc.value)

    def test_refuses_a_zero_universe_without_leaking_zerodivision(self):
        """0/0 is not a ratio — it is the state of 75 of the 162 corpus APKs.

        The named refusal has to come before the division, or the gate leaks a
        bare ZeroDivisionError that names neither the key nor the counts.
        """
        with pytest.raises(DenominatorImplausibleError) as exc:
            check_denominator(Classes(), 0, "com.example.app.debug")
        assert "com.example.app.debug" in str(exc.value)

    def test_the_boundary_is_the_documented_threshold(self):
        compiled = 1000
        check_denominator(_classes(int(compiled * MIN_PARSED_RATIO)), compiled, "k")
        with pytest.raises(DenominatorImplausibleError):
            check_denominator(
                _classes(int(compiled * MIN_PARSED_RATIO) - 1), compiled, "k"
            )


def _artefact(
    tmp_path, parsed_classes: int, class_defs_under_key, key="com.example.app"
):
    """A minimal artefact in the shape the producer writes (INV-ANA-66)."""
    path = tmp_path / "app.json"
    path.write_text(
        json.dumps(
            {
                "package": key,
                "mainActivity": f"{key}.MainActivity",
                "codePackage": key,
                "codePackageSource": "manifest",
                "class_defs_under_key": class_defs_under_key,
                "components": {},
                "reachability": [
                    {"className": f"{key}.C{i}", "componentType": "", "methods": []}
                    for i in range(parsed_classes)
                ],
                "windows": [],
                "transitions": [],
                "complete": True,
            }
        ),
        encoding="utf-8",
    )
    return str(path)


@pytest.fixture
def wired_analyzer(mock_app, mock_config, output_dir):
    with patch("os.makedirs"):
        return StaticAnalyzer(app=mock_app, config=mock_config, output_dir=output_dir)


class TestGateWiring:
    """The gate has to be reached from `analyze()`, not merely to exist."""

    @patch("rv_static_analysis.analysis.static.static_analysis.Command")
    def test_gate_raises_after_flip(self, mock_command, wired_analyzer, tmp_path):
        """A 762-class universe against 1 parsed class: the gate refuses.

        This is the fixture task 2.6 landed warn-only and task 3.7 flipped. The
        tolerance existed only while the run had no way to supply a key that
        resolves; the build-type suffix policy is that way, so the warning goes.
        The refusal is asserted on `_check_denominator` rather than on
        `analyze()`, because `analyze()` deliberately converts it — see the
        companion test below.
        """
        artefact = _artefact(tmp_path, parsed_classes=1, class_defs_under_key=762)
        wired_analyzer.analysis_file = artefact

        with pytest.raises(DenominatorImplausibleError) as exc:
            wired_analyzer._check_denominator()

        message = str(exc.value)
        assert "762" in message
        assert "com.example.app" in message

    @patch("rv_static_analysis.analysis.static.static_analysis.Command")
    def test_analyze_reports_the_refusal_as_a_failed_result(
        self, mock_command, wired_analyzer, tmp_path, caplog
    ):
        """The refusal fails this APK's analysis and no more.

        It travels through the same channel as an execution failure — a failed
        result carrying the message — because the `@ErrorHandler.handle_errors`
        decorator on `analyze()` would swallow a raise and return `None`, which
        is the silence the gate exists to end. The message still names all three
        numbers, so the operator knows which APK to re-run and why.
        """
        mock_command.return_value = MagicMock(
            invoke=MagicMock(return_value=MagicMock(exit_code=0))
        )
        artefact = _artefact(tmp_path, parsed_classes=1, class_defs_under_key=762)
        wired_analyzer.analysis_file = artefact

        with patch.object(wired_analyzer, "_run_analysis"):
            with caplog.at_level("ERROR"):
                result = wired_analyzer.analyze()

        assert result is not None, "a swallowed raise would return None"
        assert result.success is False
        assert len(result.errors) == 1
        assert "762" in result.errors[0]
        assert "com.example.app" in result.errors[0]

    @patch("rv_static_analysis.analysis.static.static_analysis.Command")
    def test_a_zero_universe_also_fails_the_analysis(
        self, mock_command, wired_analyzer, tmp_path
    ):
        """The state of 75 of the 162 corpus APKs under the literal manifest key,
        and the reason the gate could not raise before D2 landed."""
        mock_command.return_value = MagicMock(
            invoke=MagicMock(return_value=MagicMock(exit_code=0))
        )
        artefact = _artefact(tmp_path, parsed_classes=0, class_defs_under_key=0)
        wired_analyzer.analysis_file = artefact

        with patch.object(wired_analyzer, "_run_analysis"):
            result = wired_analyzer.analyze()

        assert result.success is False
        assert "class_defs_under_key=0" in result.errors[0]

    @patch("rv_static_analysis.analysis.static.static_analysis.Command")
    def test_gate_silent_on_a_healthy_artefact(
        self, mock_command, wired_analyzer, tmp_path
    ):
        artefact = _artefact(tmp_path, parsed_classes=707, class_defs_under_key=707)
        wired_analyzer.analysis_file = artefact

        with patch.object(wired_analyzer, "_run_analysis"):
            result = wired_analyzer.analyze()

        assert result.success is True
        assert result.errors == []

    @patch("rv_static_analysis.analysis.static.static_analysis.Command")
    def test_legacy_artefact_without_the_count_is_not_judged(
        self, mock_command, wired_analyzer, tmp_path
    ):
        """All 162 stored artefacts are in this state.

        The gate has no universe to divide by, and inventing one would be the
        silent measurement this change removes — so a degenerate-looking legacy
        artefact passes rather than aborting every resume in the campaign.
        """
        artefact = _artefact(tmp_path, parsed_classes=1, class_defs_under_key=-1)
        wired_analyzer.analysis_file = artefact

        with patch.object(wired_analyzer, "_run_analysis"):
            result = wired_analyzer.analyze()

        assert result.success is True
        assert result.errors == []


class TestRefusalReachesTheConsumers:
    """A refusal that leaves the artefact in place is a log line, not a gate.

    Everything downstream keys on the artefact's **presence**, never on the
    result object: `_report_missing_static_analysis` builds its list with
    `os.path.exists`, and `_resolve_static_data` locates the file by name. So
    the refusal has to change what is on disk, or INV-ANA-69's "the pipeline
    MUST NOT publish a coverage percentage for that APK" is not delivered.
    """

    @patch("rv_static_analysis.analysis.static.static_analysis.Command")
    def test_a_refused_artefact_is_moved_out_of_the_consumers_path(
        self, mock_command, wired_analyzer, tmp_path
    ):
        mock_command.return_value = MagicMock(
            invoke=MagicMock(return_value=MagicMock(exit_code=0))
        )
        artefact = _artefact(tmp_path, parsed_classes=1, class_defs_under_key=762)
        wired_analyzer.analysis_file = artefact

        with patch.object(wired_analyzer, "_run_analysis"):
            result = wired_analyzer.analyze()

        assert result.success is False
        assert not os.path.exists(artefact), (
            "left in place, the collapsed denominator is re-parsed by "
            "result_processor and published as a measured percentage"
        )
        assert os.path.exists(artefact + REFUSED_ARTIFACT_SUFFIX), (
            "renamed, not deleted: the recorded key and class_defs_under_key "
            "are what diagnose a stale jar or an unresolved key"
        )

    @patch("rv_static_analysis.analysis.static.static_analysis.Command")
    def test_an_admitted_artefact_stays_where_the_consumers_look(
        self, mock_command, wired_analyzer, tmp_path
    ):
        artefact = _artefact(tmp_path, parsed_classes=707, class_defs_under_key=707)
        wired_analyzer.analysis_file = artefact

        with patch.object(wired_analyzer, "_run_analysis"):
            result = wired_analyzer.analyze()

        assert result.success is True
        assert os.path.exists(artefact)
        assert not os.path.exists(artefact + REFUSED_ARTIFACT_SUFFIX)
