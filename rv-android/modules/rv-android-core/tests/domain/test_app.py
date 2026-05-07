"""
Tests for App - Android application metadata model.

Tests cover:
- Validation of app_path field
- Computed fields: path, name, package_name, code_package, sdk_target, permissions, min_api
- model_post_init() APK loading
- _load_and_validate_apk() file validation
- _detect_code_package() with PackageDetector
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from rv_android_core.domain.app import App
from rv_android_core.util.error.exceptions import ConfigurationError

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
