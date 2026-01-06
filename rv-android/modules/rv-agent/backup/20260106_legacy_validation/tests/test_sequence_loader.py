"""
Unit tests for SequenceLoader and related dataclasses.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from rv_agent.validation.sequence_loader import (
    ScreenData,
    AppSequence,
    SequenceLoader
)


# =============================================================================
# ScreenData Dataclass Tests
# =============================================================================

class TestScreenData:
    """Tests for ScreenData dataclass."""

    def test_screen_data_creation(self, tmp_path):
        """Test ScreenData creation with all fields."""
        screen = ScreenData(
            step=1,
            screenshot_path=tmp_path / "001.png",
            uiautomator_path=tmp_path / "001.uiautomator",
            state_path=tmp_path / "001.state",
            activity="com.example.MainActivity",
            package="com.example",
            screen_size=(1080, 1920)
        )

        assert screen.step == 1
        assert screen.activity == "com.example.MainActivity"
        assert screen.package == "com.example"
        assert screen.screen_size == (1080, 1920)

    def test_screen_data_str(self, tmp_path):
        """Test ScreenData string representation."""
        screen = ScreenData(
            step=5,
            screenshot_path=tmp_path / "005.png",
            uiautomator_path=tmp_path / "005.uiautomator",
            state_path=tmp_path / "005.state",
            activity="com.example.SettingsActivity",
            package="com.example",
            screen_size=(1080, 1920)
        )

        str_repr = str(screen)
        assert "step=5" in str_repr
        assert "activity=com.example.SettingsActivity" in str_repr


# =============================================================================
# AppSequence Dataclass Tests
# =============================================================================

class TestAppSequence:
    """Tests for AppSequence dataclass."""

    def test_app_sequence_creation(self, tmp_path):
        """Test AppSequence creation with screens."""
        screen = ScreenData(
            step=1,
            screenshot_path=tmp_path / "001.png",
            uiautomator_path=tmp_path / "001.uiautomator",
            state_path=tmp_path / "001.state",
            activity="MainActivity",
            package="com.example",
            screen_size=(1080, 1920)
        )

        sequence = AppSequence(
            app_name="test.apk",
            app_dir=tmp_path,
            package_name="com.example",
            screens=[screen]
        )

        assert sequence.app_name == "test.apk"
        assert sequence.package_name == "com.example"
        assert len(sequence) == 1
        assert sequence.apk_path is None
        assert sequence.reach_path is None

    def test_app_sequence_with_static_files(self, tmp_path):
        """Test AppSequence with all static analysis files."""
        sequence = AppSequence(
            app_name="test.apk",
            app_dir=tmp_path,
            package_name="com.example",
            screens=[],
            apk_path=tmp_path / "test.apk",
            reach_path=tmp_path / "test.reach",
            gesda_path=tmp_path / "test.gesda",
            wtg_path=tmp_path / "test.wtg",
            methods_path=tmp_path / "test.methods"
        )

        assert sequence.apk_path == tmp_path / "test.apk"
        assert sequence.reach_path == tmp_path / "test.reach"
        assert sequence.gesda_path == tmp_path / "test.gesda"

    def test_app_sequence_len(self, tmp_path):
        """Test AppSequence length method."""
        screens = [
            ScreenData(
                step=i,
                screenshot_path=tmp_path / f"{i:03d}.png",
                uiautomator_path=tmp_path / f"{i:03d}.uiautomator",
                state_path=tmp_path / f"{i:03d}.state",
                activity="Activity",
                package="com.example",
                screen_size=(1080, 1920)
            )
            for i in range(5)
        ]

        sequence = AppSequence(
            app_name="test.apk",
            app_dir=tmp_path,
            package_name="com.example",
            screens=screens
        )

        assert len(sequence) == 5

    def test_app_sequence_str(self, tmp_path):
        """Test AppSequence string representation."""
        screens = [
            ScreenData(
                step=i,
                screenshot_path=tmp_path / f"{i:03d}.png",
                uiautomator_path=tmp_path / f"{i:03d}.uiautomator",
                state_path=tmp_path / f"{i:03d}.state",
                activity="Activity",
                package="com.test.app",
                screen_size=(1080, 1920)
            )
            for i in range(3)
        ]

        sequence = AppSequence(
            app_name="myapp.apk",
            app_dir=tmp_path,
            package_name="com.test.app",
            screens=screens
        )

        str_repr = str(sequence)
        assert "myapp.apk" in str_repr
        assert "3 screens" in str_repr
        assert "com.test.app" in str_repr


# =============================================================================
# SequenceLoader Tests
# =============================================================================

class TestSequenceLoaderInit:
    """Tests for SequenceLoader initialization."""

    def test_init_with_valid_directory(self, tmp_path):
        """Test initialization with existing directory."""
        loader = SequenceLoader(tmp_path)
        assert loader.dataset_dir == tmp_path

    def test_init_with_nonexistent_directory(self, tmp_path):
        """Test initialization with non-existent directory raises error."""
        nonexistent = tmp_path / "does_not_exist"

        with pytest.raises(ValueError) as exc_info:
            SequenceLoader(nonexistent)

        assert "Dataset directory not found" in str(exc_info.value)

    def test_init_accepts_string_path(self, tmp_path):
        """Test initialization with string path."""
        loader = SequenceLoader(str(tmp_path))
        assert loader.dataset_dir == tmp_path


class TestSequenceLoaderListApps:
    """Tests for SequenceLoader.list_apps()."""

    def test_list_apps_empty_directory(self, tmp_path):
        """Test listing apps in empty directory."""
        loader = SequenceLoader(tmp_path)
        apps = loader.list_apps()
        assert apps == []

    def test_list_apps_with_subdirectories(self, tmp_path):
        """Test listing apps with subdirectories."""
        (tmp_path / "app1.apk").mkdir()
        (tmp_path / "app2.apk").mkdir()
        (tmp_path / "app3.apk").mkdir()

        loader = SequenceLoader(tmp_path)
        apps = loader.list_apps()

        assert len(apps) == 3
        assert "app1.apk" in apps
        assert "app2.apk" in apps
        assert "app3.apk" in apps

    def test_list_apps_ignores_files(self, tmp_path):
        """Test that list_apps ignores files (not directories)."""
        (tmp_path / "app1.apk").mkdir()
        (tmp_path / "readme.txt").touch()

        loader = SequenceLoader(tmp_path)
        apps = loader.list_apps()

        assert len(apps) == 1
        assert "app1.apk" in apps
        assert "readme.txt" not in apps

    def test_list_apps_returns_sorted(self, tmp_path):
        """Test that apps are returned sorted."""
        (tmp_path / "zebra.apk").mkdir()
        (tmp_path / "alpha.apk").mkdir()
        (tmp_path / "beta.apk").mkdir()

        loader = SequenceLoader(tmp_path)
        apps = loader.list_apps()

        assert apps == ["alpha.apk", "beta.apk", "zebra.apk"]


class TestSequenceLoaderLoadAppSequence:
    """Tests for SequenceLoader.load_app_sequence()."""

    def _create_app_structure(self, app_dir: Path, num_screens: int = 3):
        """Helper to create a valid app structure."""
        app_dir.mkdir(exist_ok=True)

        for i in range(1, num_screens + 1):
            step_str = f"{i:03d}"

            # Create screenshot
            (app_dir / f"{step_str}.png").touch()

            # Create UIAutomator dump
            (app_dir / f"{step_str}.uiautomator").write_text(
                '<hierarchy rotation="0"></hierarchy>'
            )

            # Create state file
            state_data = {
                "activity": f"com.example.Activity{i}",
                "view_tree": {"package": "com.example"},
                "screen_size": {"width": 1080, "height": 1920}
            }
            (app_dir / f"{step_str}.state").write_text(json.dumps(state_data))

        return app_dir

    def test_load_app_sequence_basic(self, tmp_path):
        """Test loading a basic app sequence."""
        app_dir = self._create_app_structure(tmp_path / "test.apk", num_screens=3)

        loader = SequenceLoader(tmp_path)
        sequence = loader.load_app_sequence("test.apk")

        assert sequence.app_name == "test.apk"
        assert sequence.package_name == "com.example"
        assert len(sequence.screens) == 3

    def test_load_app_sequence_screen_data(self, tmp_path):
        """Test that screen data is correctly populated."""
        app_dir = self._create_app_structure(tmp_path / "test.apk", num_screens=2)

        loader = SequenceLoader(tmp_path)
        sequence = loader.load_app_sequence("test.apk")

        screen = sequence.screens[0]
        assert screen.step == 1
        assert screen.activity == "com.example.Activity1"
        assert screen.package == "com.example"
        assert screen.screen_size == (1080, 1920)

    def test_load_app_sequence_with_static_files(self, tmp_path):
        """Test loading sequence with static analysis files."""
        app_dir = self._create_app_structure(tmp_path / "test.apk", num_screens=2)

        # Add static analysis files
        (app_dir / "test.apk").touch()
        (app_dir / "test.apk.reach").touch()
        (app_dir / "test.apk.gesda").touch()
        (app_dir / "test.apk.wtg").touch()
        (app_dir / "test.apk.methods").touch()

        loader = SequenceLoader(tmp_path)
        sequence = loader.load_app_sequence("test.apk")

        assert sequence.apk_path is not None
        assert sequence.reach_path is not None
        assert sequence.gesda_path is not None
        assert sequence.wtg_path is not None
        assert sequence.methods_path is not None

    def test_load_app_sequence_nonexistent_app(self, tmp_path):
        """Test loading non-existent app raises error."""
        loader = SequenceLoader(tmp_path)

        with pytest.raises(ValueError) as exc_info:
            loader.load_app_sequence("nonexistent.apk")

        assert "App directory not found" in str(exc_info.value)

    def test_load_app_sequence_no_screenshots(self, tmp_path):
        """Test loading app with no screenshots raises error."""
        app_dir = tmp_path / "empty.apk"
        app_dir.mkdir()

        loader = SequenceLoader(tmp_path)

        with pytest.raises(ValueError) as exc_info:
            loader.load_app_sequence("empty.apk")

        assert "No screenshots found" in str(exc_info.value)

    def test_load_app_sequence_missing_uiautomator(self, tmp_path):
        """Test that missing UIAutomator files are skipped."""
        app_dir = tmp_path / "test.apk"
        app_dir.mkdir()

        # Create screenshot but no UIAutomator
        (app_dir / "001.png").touch()
        state_data = {
            "activity": "Activity",
            "view_tree": {"package": "com.example"},
            "screen_size": {"width": 1080, "height": 1920}
        }
        (app_dir / "001.state").write_text(json.dumps(state_data))

        loader = SequenceLoader(tmp_path)

        with pytest.raises(ValueError) as exc_info:
            loader.load_app_sequence("test.apk")

        assert "No valid screens" in str(exc_info.value)

    def test_load_app_sequence_missing_state(self, tmp_path):
        """Test that missing state files are skipped."""
        app_dir = tmp_path / "test.apk"
        app_dir.mkdir()

        # Create screenshot and UIAutomator but no state
        (app_dir / "001.png").touch()
        (app_dir / "001.uiautomator").write_text("<hierarchy></hierarchy>")

        loader = SequenceLoader(tmp_path)

        with pytest.raises(ValueError) as exc_info:
            loader.load_app_sequence("test.apk")

        assert "No valid screens" in str(exc_info.value)

    def test_load_app_sequence_non_sequential_files(self, tmp_path):
        """Test that non-sequential files are skipped."""
        app_dir = self._create_app_structure(tmp_path / "test.apk", num_screens=2)

        # Add non-sequential file
        (app_dir / "background.png").touch()

        loader = SequenceLoader(tmp_path)
        sequence = loader.load_app_sequence("test.apk")

        # Should only have 2 screens (001, 002)
        assert len(sequence.screens) == 2

    def test_load_app_sequence_malformed_state(self, tmp_path):
        """Test handling of malformed state file."""
        app_dir = tmp_path / "test.apk"
        app_dir.mkdir()

        (app_dir / "001.png").touch()
        (app_dir / "001.uiautomator").write_text("<hierarchy></hierarchy>")
        (app_dir / "001.state").write_text("not valid json")

        loader = SequenceLoader(tmp_path)

        with pytest.raises(ValueError) as exc_info:
            loader.load_app_sequence("test.apk")

        assert "No valid screens" in str(exc_info.value)

    def test_load_app_sequence_default_screen_size(self, tmp_path):
        """Test default screen size when not specified in state."""
        app_dir = tmp_path / "test.apk"
        app_dir.mkdir()

        (app_dir / "001.png").touch()
        (app_dir / "001.uiautomator").write_text("<hierarchy></hierarchy>")

        # State without screen_size
        state_data = {
            "activity": "Activity",
            "view_tree": {"package": "com.example"}
        }
        (app_dir / "001.state").write_text(json.dumps(state_data))

        loader = SequenceLoader(tmp_path)
        sequence = loader.load_app_sequence("test.apk")

        # Should use default 1080x1920
        assert sequence.screens[0].screen_size == (1080, 1920)


class TestSequenceLoaderLoadAllSequences:
    """Tests for SequenceLoader.load_all_sequences()."""

    def _create_app_structure(self, app_dir: Path, num_screens: int = 2):
        """Helper to create a valid app structure."""
        app_dir.mkdir(exist_ok=True)

        for i in range(1, num_screens + 1):
            step_str = f"{i:03d}"
            (app_dir / f"{step_str}.png").touch()
            (app_dir / f"{step_str}.uiautomator").write_text("<hierarchy></hierarchy>")
            state_data = {
                "activity": f"Activity{i}",
                "view_tree": {"package": "com.example"},
                "screen_size": {"width": 1080, "height": 1920}
            }
            (app_dir / f"{step_str}.state").write_text(json.dumps(state_data))

    def test_load_all_sequences_multiple_apps(self, tmp_path):
        """Test loading all sequences from multiple apps."""
        self._create_app_structure(tmp_path / "app1.apk")
        self._create_app_structure(tmp_path / "app2.apk")
        self._create_app_structure(tmp_path / "app3.apk")

        loader = SequenceLoader(tmp_path)
        sequences = loader.load_all_sequences()

        assert len(sequences) == 3
        assert "app1.apk" in sequences
        assert "app2.apk" in sequences
        assert "app3.apk" in sequences

    def test_load_all_sequences_with_failure(self, tmp_path):
        """Test loading continues after one app fails."""
        self._create_app_structure(tmp_path / "good.apk")

        # Create broken app
        bad_dir = tmp_path / "bad.apk"
        bad_dir.mkdir()  # Empty directory - no screenshots

        loader = SequenceLoader(tmp_path)
        sequences = loader.load_all_sequences()

        # Should load the good one, skip the bad one
        assert len(sequences) == 1
        assert "good.apk" in sequences

    def test_load_all_sequences_empty_dataset(self, tmp_path):
        """Test loading from empty dataset."""
        loader = SequenceLoader(tmp_path)
        sequences = loader.load_all_sequences()

        assert sequences == {}
