"""
Tests for App - Android application metadata model.

Tests cover:
- Validation of app_path field
- Computed fields: path, name, package_name, code_package, code_package_source,
  sdk_target, permissions, min_api
- model_post_init() APK loading
- _load_and_validate_apk() file validation
- the package policy: declared package by default, PackageDetector on request
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import rv_android_core.domain.app as app_module
from rv_android_core.domain.app import App
from rv_android_core.util.android.package_detector import PackageDetectionResult


def _app_with_manifest_package(package: str, **kwargs) -> App:
    """Build an App whose loaded APK declares `package`, without touching disk."""
    app = App(app_path="/tmp/test.apk", validate_on_init=False, **kwargs)
    apk = MagicMock()
    apk.get_package.return_value = package
    app._apk_instance = apk
    return app


# ---------------------------------------------------------------------------
# Tests: Validation
# ---------------------------------------------------------------------------


class TestAppValidation:
    """Test App validation."""

    def test_empty_path_raises(self):
        """Test that empty path raises validation error."""
        with pytest.raises(Exception):  # Pydantic ValidationError or ConfigurationError
            App(app_path="")

    def test_whitespace_only_path_raises(self):
        """Test that whitespace-only path raises validation error."""
        with pytest.raises(Exception):
            App(app_path="   ")

    def test_none_path_raises(self):
        """Test that None path raises validation error."""
        with pytest.raises(Exception):
            App(app_path=None)


# ---------------------------------------------------------------------------
# Tests: Computed fields (without APK loading)
# ---------------------------------------------------------------------------


class TestComputedFields:
    """Test computed fields without APK loading."""

    def test_path_returns_absolute(self):
        """Test that path returns absolute path."""
        app = App(app_path="/tmp/test.apk", validate_on_init=False)
        assert app.path.startswith("/")
        assert "test.apk" in app.path

    def test_name_returns_basename(self):
        """Test that name returns APK filename."""
        app = App(app_path="/some/dir/my_app.apk", validate_on_init=False)
        assert app.name == "my_app.apk"


# ---------------------------------------------------------------------------
# Tests: Field validator
# ---------------------------------------------------------------------------


class TestFieldValidator:
    """Test app_path field validator."""

    def test_validator_strips_whitespace(self):
        """Test that validator strips whitespace."""
        app = App(app_path="  /path/to/app.apk  ", validate_on_init=False)
        assert app.app_path == "/path/to/app.apk"

    def test_validator_rejects_empty_string(self):
        """Test that validator rejects empty string."""
        with pytest.raises(Exception):
            App(app_path="", validate_on_init=False)


# ---------------------------------------------------------------------------
# Tests: model_post_init()
# ---------------------------------------------------------------------------


class TestModelPostInit:
    """Test model_post_init() APK loading."""

    def test_post_init_skips_apk_when_validate_false(self):
        """Test that post_init skips APK loading when validate_on_init=False."""
        app = App(app_path="/tmp/test.apk", validate_on_init=False)
        assert app._apk_instance is None


# ---------------------------------------------------------------------------
# Tests: package policy (INV-CORE-18, INV-CORE-55)
# ---------------------------------------------------------------------------


class TestCodePackagePolicy:
    """Which package scopes app-owned classes, and where that answer came from.

    The Godot case is the one that motivates the detector: the manifest declares
    `ir.hsn6.trans` while every implementation class lives under
    `org.godotengine.godot`. The suffix case is the one that motivates the
    default: `org.fossify.calendar_20.apk` declares `org.fossify.calendar.debug`,
    and stripping `.debug` is a rule about a corpus, not about the APK.
    """

    GODOT_MANIFEST = "ir.hsn6.trans"
    GODOT_CODE = "org.godotengine.godot"

    def _detector_returning(self, manifest: str, code: str) -> MagicMock:
        """A PackageDetector class mock whose instance elects `code`."""
        detector_cls = MagicMock()
        detector_cls.return_value.detect_package.return_value = PackageDetectionResult(
            manifest_package=manifest,
            code_package=code,
            confidence="high",
            detection_method="game_engine",
            game_engine="godot",
        )
        return detector_cls

    def test_code_package_defaults_to_manifest(self):
        """Without a stated preference, code_package is the declared package."""
        app = _app_with_manifest_package(self.GODOT_MANIFEST)

        assert app.package_name == self.GODOT_MANIFEST
        assert app.code_package == self.GODOT_MANIFEST
        assert app.code_package_source == "manifest"

    def test_detector_not_invoked_by_default(self):
        """The default path never pays for component enumeration."""
        app = _app_with_manifest_package(self.GODOT_MANIFEST)

        with patch("rv_android_core.domain.app.PackageDetector") as detector_cls:
            assert app.code_package == self.GODOT_MANIFEST

        detector_cls.assert_not_called()

    def test_code_package_uses_detector_when_enabled(self):
        """With the flag, the election replaces the declared package."""
        app = _app_with_manifest_package(self.GODOT_MANIFEST, package_detector=True)
        detector_cls = self._detector_returning(self.GODOT_MANIFEST, self.GODOT_CODE)

        with patch("rv_android_core.domain.app.PackageDetector", detector_cls):
            assert app.code_package == self.GODOT_CODE

        assert app.package_name == self.GODOT_MANIFEST
        detector_cls.return_value.detect_package.assert_called_once_with(
            app._apk_instance
        )

    def test_detector_mismatch_is_logged_at_info(self, caplog):
        """A mismatch between declared and elected package is reported once."""
        app = _app_with_manifest_package(self.GODOT_MANIFEST, package_detector=True)
        detector_cls = self._detector_returning(self.GODOT_MANIFEST, self.GODOT_CODE)

        with caplog.at_level("INFO", logger="rv_android_core.domain.app"):
            with patch("rv_android_core.domain.app.PackageDetector", detector_cls):
                assert app.code_package == self.GODOT_CODE

        assert "Package mismatch detected" in caplog.text
        assert self.GODOT_CODE in caplog.text

    def test_code_package_source_matches_mechanism(self):
        """Provenance names the mechanism that produced the value."""
        default_app = _app_with_manifest_package(self.GODOT_MANIFEST)
        detector_app = _app_with_manifest_package(
            self.GODOT_MANIFEST, package_detector=True
        )
        detector_cls = self._detector_returning(self.GODOT_MANIFEST, self.GODOT_CODE)

        assert default_app.code_package_source == "manifest"
        assert default_app.code_package == default_app.package_name

        with patch("rv_android_core.domain.app.PackageDetector", detector_cls):
            assert detector_app.code_package == self.GODOT_CODE
        assert detector_app.code_package_source == "detector"

    def test_declared_package_is_returned_verbatim(self):
        """No build-type segment is stripped: normalization belongs to the corpus."""
        app = _app_with_manifest_package("org.fossify.calendar.debug")

        assert app.code_package == "org.fossify.calendar.debug"
        assert app.code_package_source == "manifest"

    def test_strip_build_type_suffix_defaults_to_off(self):
        """The manifest verbatim stays the rule; neutralization is a run policy."""
        app = App("/tmp/test.apk", validate_on_init=False)

        assert app.strip_build_type_suffix is False

    def test_neutralization_applies_when_the_policy_is_on(self):
        app = _app_with_manifest_package(
            "org.fossify.calendar.debug", strip_build_type_suffix=True
        )

        assert app.package_name == "org.fossify.calendar.debug"
        assert app.code_package == "org.fossify.calendar"
        assert app.code_package_source == "manifest-neutralized"

    def test_stacked_suffix_reaches_the_App_through_one_rule(self):
        app = _app_with_manifest_package(
            "com.example.app.qa.debug", strip_build_type_suffix=True
        )

        assert app.code_package == "com.example.app"
        assert app.code_package_source == "manifest-neutralized"

    def test_source_reports_manifest_when_the_policy_removed_nothing(self):
        """The value names what produced the key, not what was requested — a
        reader asking why a key looks the way it does is asking about the former.
        """
        app = _app_with_manifest_package(
            "de.grobox.liberario", strip_build_type_suffix=True
        )

        assert app.code_package == "de.grobox.liberario"
        assert app.code_package_source == "manifest"

    def test_package_name_is_unaffected_by_the_policy(self):
        """Device operations install and launch the declared id, whatever key the
        study scopes classes by."""
        app = _app_with_manifest_package(
            "br.com.colman.petals.debug", strip_build_type_suffix=True
        )

        assert app.package_name == "br.com.colman.petals.debug"
        assert app.code_package == "br.com.colman.petals"

    def test_detector_wins_over_neutralization(self):
        """Both policies on is not a conflict to resolve here: the detector
        answers from the compiled classes themselves, which is strictly more
        evidence than a denylist over the declared id."""
        app = _app_with_manifest_package(
            self.GODOT_MANIFEST, package_detector=True, strip_build_type_suffix=True
        )
        detector_cls = self._detector_returning(self.GODOT_MANIFEST, self.GODOT_CODE)

        with patch("rv_android_core.domain.app.PackageDetector", detector_cls):
            assert app.code_package == self.GODOT_CODE
        assert app.code_package_source == "detector"

    def test_package_detector_defaults_to_false(self):
        """Constructing App positionally keeps the manifest policy."""
        app = App("/tmp/test.apk", validate_on_init=False)

        assert app.package_detector is False
        assert app.code_package_source == "manifest"

    def test_domain_model_reads_no_environment(self):
        """INV-CORE-55: the value arrives as a constructor argument, never from os.environ."""
        source = Path(app_module.__file__).read_text(encoding="utf-8")

        assert "os.environ" not in source
        assert "os.getenv" not in source
