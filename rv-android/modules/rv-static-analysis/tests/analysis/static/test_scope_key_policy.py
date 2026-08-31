"""The scope key a run decides on travels intact to GATOR, to the artefact, and back.

These are integration tests in the sense that matters here: each one crosses a
seam the change repairs, and each seam is a place where the key was previously
answered twice or not recorded at all. They assert, in order: what the run tells
GATOR, what it deliberately does not tell the ajc instrumenter, what the
artefact carries back, what a stored artefact is allowed to answer for, and that
the new run policy is documented where the drift check looks.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from rv_android_core.domain.app import App
from rv_static_analysis.__main__ import _discard_cached_artifact
from rv_static_analysis.analysis.static.static_analysis import StaticAnalyzer
from rv_static_analysis.config import RVStaticAnalysisConfig
from rv_static_analysis.parser.static.static_analysis_parser import (
    StaticAnalysisParser,
)

DECLARED = "br.com.colman.petals.debug"
NEUTRALIZED = "br.com.colman.petals"

# Two tests below read repo-level files (another module's CLAUDE.md, a script in
# scripts/). Anchoring them on this file rather than on the process cwd is what
# lets the module be tested from its own directory as well as from the repo root
# — `/rv-test-run rv-static-analysis` does the former, `ci.yml` the latter.
REPO_ROOT = Path(__file__).resolve().parents[5]


def _app(package: str, **policy) -> App:
    """An App whose loaded APK declares `package`, without touching disk."""
    app = App(app_path="/tmp/petals.apk", validate_on_init=False, **policy)
    apk = MagicMock()
    apk.get_package.return_value = package
    app._apk_instance = apk
    return app


def _artifact(path, *, code_package, class_defs_under_key, classes=("A", "B")):
    """A minimal GATOR artefact recording a scope key and its compiled universe."""
    payload = {
        "package": DECLARED,
        "codePackage": code_package,
        "codePackageSource": "manifest-neutralized",
        "class_defs_under_key": class_defs_under_key,
        "mainActivity": f"{code_package}.MainActivity",
        "reachability": [
            {
                "className": f"{code_package}.{name}",
                "methods": [
                    {
                        "name": "run",
                        "signature": f"<{code_package}.{name}: void run()>",
                        "reachable": True,
                        "reachesTarget": False,
                        "directlyReachesTarget": False,
                    }
                ],
            }
            for name in classes
        ],
        "windows": [],
        "transitions": [],
        "components": {},
        "complete": True,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class TestPolicyReachesTheGatorArgv:
    """The key the run decided on is the key GATOR is told to filter by."""

    def test_neutralized_key_and_its_origin_are_emitted(self):
        config = RVStaticAnalysisConfig(
            gator_dir="/fake/gator",
            analysis_client_jar="/fake/gator/rvsec-analysis-client.jar",
            android_jar="/fake/android.jar",
            mop_dir="/fake/mop",
            validate_on_init=False,
        )
        app = _app(DECLARED, strip_build_type_suffix=True)

        argv = config.get_tool_command(
            "analysis",
            app.path,
            "/tmp/out/petals.apk.json",
            code_package=app.code_package,
            code_package_source=app.code_package_source,
        )

        assert f"codePackage={NEUTRALIZED}" in argv
        assert "codePackageSource=manifest-neutralized" in argv
        # The declared id is what the device installs, and it must not be what
        # GATOR scopes by — that pairing is the whole defect.
        assert f"codePackage={DECLARED}" not in argv

    def test_default_policy_still_emits_the_declared_id(self):
        config = RVStaticAnalysisConfig(
            gator_dir="/fake/gator",
            analysis_client_jar="/fake/gator/rvsec-analysis-client.jar",
            android_jar="/fake/android.jar",
            mop_dir="/fake/mop",
            validate_on_init=False,
        )
        app = _app(DECLARED)

        argv = config.get_tool_command(
            "analysis",
            app.path,
            "/tmp/out/petals.apk.json",
            code_package=app.code_package,
            code_package_source=app.code_package_source,
        )

        assert f"codePackage={DECLARED}" in argv
        assert "codePackageSource=manifest" in argv


class TestPolicyDoesNotReachAjc:
    """INV-EXP-36: the instrumenter receives the DECLARED applicationId.

    The exclusion is deliberate and asymmetric. Feeding the neutralized key to
    ajc would activate the anti-quarantine guard that is inert today precisely
    in the suffixed apps — a change on the instrumentation path, not the
    analysis path, and out of scope for this change. So the pipeline
    deliberately holds two answers for `code_package`, by consumer.
    """

    def test_ajc_constructs_apps_without_the_neutralization_policy(self):
        import rv_instrumentation_ajc.ajc_instrumentation as ajc

        source = Path(ajc.__file__).read_text(encoding="utf-8")

        assert "package_detector=self.config.package_detector" in source
        assert "strip_build_type_suffix" not in source

    def test_the_asymmetry_the_exclusion_does_not_cover_is_recorded(self):
        """ajc is excluded from this policy and NOT from `package_detector`, so
        the guard activation cited as the reason already happens under
        `--package-detector`. The divergence is recorded, not repaired."""
        claude_md = REPO_ROOT / "modules/rv-instrumentation-ajc/CLAUDE.md"
        text = claude_md.read_text(encoding="utf-8")

        assert "INV-EXP-36" in text
        assert "strip_build_type_suffix" in text


class TestArtifactRecordsTheKey:
    """The artefact carries what produced it, so a later reader need not guess."""

    def test_parser_reads_back_key_origin_and_compiled_universe(self, tmp_path):
        path = _artifact(
            tmp_path / "petals.apk.json",
            code_package=NEUTRALIZED,
            class_defs_under_key=762,
        )

        data = StaticAnalysisParser().parse_file(str(path))

        assert data.code_package == NEUTRALIZED
        assert data.code_package_source == "manifest-neutralized"
        assert data.class_defs_under_key == 762
        # The artefact still carries `package` — the manifest package, whatever
        # key filtered the file — and the parser deliberately does not surface
        # it: a member that can never stand in for the effective key must not be
        # reachable as one (INV-ANA-58).
        assert json.loads(path.read_text())["package"] == DECLARED
        assert not hasattr(data, "package")

    def test_a_legacy_artefact_supplies_none_rather_than_the_manifest(self, tmp_path):
        path = tmp_path / "legacy.apk.json"
        path.write_text(
            json.dumps(
                {
                    "package": DECLARED,
                    "mainActivity": "M",
                    "reachability": [],
                    "windows": [],
                    "transitions": [],
                    "components": {},
                    "complete": True,
                }
            ),
            encoding="utf-8",
        )

        data = StaticAnalysisParser().parse_file(str(path))

        assert data.code_package is None
        assert data.code_package_source is None
        assert data.class_defs_under_key is None


class TestArtifactReusedOnlyUnderItsOwnKey:
    """INV-ANA-70: existence is no longer enough to make a cache hit."""

    @staticmethod
    def _analyzer(tmp_path, app):
        config = MagicMock(spec=RVStaticAnalysisConfig)
        config.output_dir = str(tmp_path)
        config.analysis_timeout = 600
        config.get_tool_command.return_value = ["/bin/true"]
        return StaticAnalyzer(app=app, config=config, output_dir=str(tmp_path))

    def test_a_key_mismatched_artefact_is_not_reused(self, tmp_path, caplog):
        """The stored artefact was produced under the declared id; this run
        scopes by the neutralized one. Reusing it would publish a denominator
        built from one key against coverage measured under another."""
        app = _app(DECLARED, strip_build_type_suffix=True)
        analyzer = self._analyzer(tmp_path, app)
        _artifact(
            tmp_path / "petals.apk.json",
            code_package=DECLARED,
            class_defs_under_key=1,
        )

        with patch(
            "rv_static_analysis.analysis.static.static_analysis.Command"
        ) as command:
            command.return_value.invoke.return_value = MagicMock(code=0, stderr=b"")

            # GATOR is mocked, so it writes nothing; put the artefact back the
            # way a real run would, before the post-condition check.
            def _reinstate(*_args, **_kwargs):
                _artifact(
                    tmp_path / "petals.apk.json",
                    code_package=NEUTRALIZED,
                    class_defs_under_key=762,
                )
                return MagicMock(code=0, stderr=b"")

            command.return_value.invoke.side_effect = _reinstate
            analyzer._run_analysis()

        command.return_value.invoke.assert_called_once()
        reparsed = StaticAnalysisParser().parse_file(analyzer.analysis_file)
        assert reparsed.code_package == NEUTRALIZED

    def test_an_artefact_under_the_same_key_is_still_a_cache_hit(self, tmp_path):
        """The key comparison adds a condition to reuse, never a new way of
        reusing: the existing cache-hit path is unchanged."""
        app = _app(NEUTRALIZED)
        analyzer = self._analyzer(tmp_path, app)
        _artifact(
            tmp_path / "petals.apk.json",
            code_package=NEUTRALIZED,
            class_defs_under_key=2,
        )

        with patch(
            "rv_static_analysis.analysis.static.static_analysis.Command"
        ) as command:
            analyzer._run_analysis()

        command.return_value.invoke.assert_not_called()

    def test_force_discards_an_artefact_the_cache_would_have_answered_with(
        self, tmp_path
    ):
        """The deliberate invalidation, as against the automatic one.

        The key comparison fires only when the keys disagree, so it cannot help
        an operator re-measuring the *same* key against a rebuilt jar — which is
        exactly what this change's own acceptance runs do. `--force` is the only
        way to say "measure again"; without it the second leg of an A/B in one
        directory is answered from the first leg's artefact.
        """
        app = _app(NEUTRALIZED)
        analyzer = self._analyzer(tmp_path, app)
        _artifact(
            tmp_path / "petals.apk.json",
            code_package=NEUTRALIZED,
            class_defs_under_key=762,
        )

        _discard_cached_artifact(analyzer, force=False)
        assert Path(analyzer.analysis_file).is_file()

        _discard_cached_artifact(analyzer, force=True)
        assert not Path(analyzer.analysis_file).exists()

        with patch(
            "rv_static_analysis.analysis.static.static_analysis.Command"
        ) as command:
            # GATOR is mocked and writes nothing; stand in for the artefact a
            # real re-run would produce, so the post-condition under test is the
            # re-invocation and not the absence of output.
            def _write(*_args, **_kwargs):
                _artifact(
                    tmp_path / "petals.apk.json",
                    code_package=NEUTRALIZED,
                    class_defs_under_key=762,
                )
                return MagicMock(code=0, stderr=b"")

            command.return_value.invoke.side_effect = _write
            analyzer._run_analysis()

        command.return_value.invoke.assert_called_once()

    def test_a_legacy_artefact_recording_no_key_is_still_a_cache_hit(self, tmp_path):
        """All 162 artefacts of the article corpus record no key. Refusing them
        would make every resume re-run GATOR — hours per APK — to recover a key
        the file was never asked to carry."""
        app = _app(DECLARED, strip_build_type_suffix=True)
        analyzer = self._analyzer(tmp_path, app)
        path = tmp_path / "petals.apk.json"
        path.write_text(
            json.dumps(
                {
                    "package": DECLARED,
                    "mainActivity": "M",
                    "reachability": [],
                    "windows": [],
                    "transitions": [],
                    "components": {},
                    "complete": True,
                }
            ),
            encoding="utf-8",
        )

        with patch(
            "rv_static_analysis.analysis.static.static_analysis.Command"
        ) as command:
            analyzer._run_analysis()

        command.return_value.invoke.assert_not_called()


class TestEnvironmentVariableDrift:
    """The new run policy is documented where the drift check looks for it."""

    def test_check_env_vars_drift_reports_no_violation(self):
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts/check_env_vars_drift.py")],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert "clean" in result.stdout
