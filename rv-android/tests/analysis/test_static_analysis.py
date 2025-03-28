# tests/analysis/test_static_analysis.py
import os
from unittest.mock import MagicMock, patch

import pytest

from rvandroid.analysis.static_analysis import (
    run_static_analysis,
    run_gesda,
    run_gator,
    run_reachability,
    StaticAnalysisException
)
from rvandroid.app import App


class TestStaticAnalysis:
    @pytest.fixture
    def mock_app(self):
        """Create a mock App instance for testing."""
        mock_app = MagicMock(spec=App)
        mock_app.name = "test_app"
        mock_app.path = "/path/to/test_app.apk"
        return mock_app

    def test_run_gesda(self, mock_app, tmp_path):
        """Test GESDA static analysis execution."""
        # Prepare temp output file
        gesda_file = str(tmp_path / "gesda_output.txt")

        # Use real paths from the actual implementation
        with patch('rvandroid.analysis.static_analysis.LIB_DIR', '/some/lib/path'), \
                patch('rvandroid.analysis.static_analysis.ANDROID_PLATFORMS_DIR', '/android/platforms'), \
                patch('rvandroid.analysis.static_analysis.RT_JAR', '/path/to/rt.jar'), \
                patch('rvandroid.analysis.static_analysis.Command') as mock_command_class:
            # Mock successful command execution
            mock_command_instance = MagicMock()
            mock_command_instance.invoke.return_value = MagicMock(code=0)
            mock_command_class.return_value = mock_command_instance

            # Run GESDA analysis
            run_gesda(mock_app, gesda_file)

            # Verify command was created with correct arguments
            mock_command_class.assert_called_once()
            args = mock_command_class.call_args[0][1]

            # Check key arguments
            assert "-jar" in args
            assert "/some/lib/path/gesda/rvsec-gesda.jar" in args
            assert mock_app.path in args
            assert gesda_file in args

    def test_run_gator(self, mock_app, tmp_path):
        """Test GATOR static analysis execution."""
        # Prepare temp output file
        gator_file = str(tmp_path / "gator_output.txt")

        # Use real paths from the actual implementation
        with patch('rvandroid.analysis.static_analysis.LIB_DIR', '/some/lib/path'), \
                patch('rvandroid.analysis.static_analysis.Command') as mock_command_class:
            # Mock successful command execution
            mock_command_instance = MagicMock()
            mock_command_instance.invoke.return_value = MagicMock(code=0)
            mock_command_class.return_value = mock_command_instance

            # Run GATOR analysis
            run_gator(mock_app, gator_file)

            # Verify command was created with correct arguments
            mock_command_class.assert_called_once()
            args = mock_command_class.call_args[0][1]

            # Check key arguments
            assert "/some/lib/path/gator/gator" in args
            assert mock_app.path in args
            assert gator_file in args
            assert "RvsecWtgClient" in args

    def test_run_reachability(self, mock_app, tmp_path):
        """Test Reachability static analysis execution."""
        # Prepare temp output file and MOP directory
        reach_file = str(tmp_path / "reach_output.txt")
        mop_dir = str(tmp_path / "mop")
        os.makedirs(mop_dir)

        # Use real paths from the actual implementation
        with patch('rvandroid.analysis.static_analysis.LIB_DIR', '/some/lib/path'), \
                patch('rvandroid.analysis.static_analysis.ANDROID_PLATFORMS_DIR', '/android/platforms'), \
                patch('rvandroid.analysis.static_analysis.RT_JAR', '/path/to/rt.jar'), \
                patch('rvandroid.analysis.static_analysis.Command') as mock_command_class:
            # Mock successful command execution
            mock_command_instance = MagicMock()
            mock_command_instance.invoke.return_value = MagicMock(code=0)
            mock_command_class.return_value = mock_command_instance

            # Run Reachability analysis
            run_reachability(mock_app, reach_file, mop_dir)

            # Verify command was created with correct arguments
            mock_command_class.assert_called_once()
            args = mock_command_class.call_args[0][1]

            # Check key arguments
            assert "-jar" in args
            assert "/some/lib/path/reach/rvsec-reach.jar" in args
            assert mock_app.path in args
            assert reach_file in args
            assert mop_dir in args

    def test_run_static_analysis(self, mock_app, tmp_path):
        """Test complete static analysis workflow."""
        # Prepare temp output files
        gesda_file = str(tmp_path / "gesda_output.txt")
        gator_file = str(tmp_path / "gator_output.txt")
        reach_file = str(tmp_path / "reach_output.txt")

        # Mock the individual analysis methods
        with patch('rvandroid.analysis.static_analysis.run_gesda') as mock_run_gesda, \
                patch('rvandroid.analysis.static_analysis.run_gator') as mock_run_gator, \
                patch('rvandroid.analysis.static_analysis.run_reachability') as mock_run_reachability, \
                patch('rvandroid.analysis.static_analysis.MOP_DIR', '/mock/mop/dir'):
            # Run static analysis
            run_static_analysis(mock_app, gesda_file, gator_file, reach_file)

            # Verify each analysis method was called with correct arguments
            mock_run_gesda.assert_called_once_with(mock_app, gesda_file)
            mock_run_gator.assert_called_once_with(mock_app, gator_file)
            mock_run_reachability.assert_called_once_with(
                mock_app,
                reach_file,
                '/mock/mop/dir',
                gesda_file
            )

    def test_static_analysis_skipped_if_output_exists(self, mock_app, tmp_path):
        """Test that analysis is skipped if output file already exists."""
        # Prepare temp output files
        gesda_file = str(tmp_path / "gesda_output.txt")
        gator_file = str(tmp_path / "gator_output.txt")
        reach_file = str(tmp_path / "reach_output.txt")

        # Create existing output files
        for file in [gesda_file, gator_file, reach_file]:
            with open(file, 'w') as f:
                f.write("Existing analysis")

        # Patch logging to avoid console output during test
        with patch('rvandroid.analysis.static_analysis.logging'), \
                patch('rvandroid.analysis.static_analysis.MOP_DIR', '/mock/mop/dir'):
            # Run static analysis
            run_static_analysis(mock_app, gesda_file, gator_file, reach_file)

    def test_run_static_analysis_command_failure(self, mock_app, tmp_path):
        """Test static analysis failure handling."""
        # Prepare temp output files
        gesda_file = str(tmp_path / "gesda_output.txt")
        gator_file = str(tmp_path / "gator_output.txt")
        reach_file = str(tmp_path / "reach_output.txt")

        # Use real paths from the actual implementation
        with patch('rvandroid.analysis.static_analysis.LIB_DIR', '/some/lib/path'), \
                patch('rvandroid.analysis.static_analysis.ANDROID_PLATFORMS_DIR', '/android/platforms'), \
                patch('rvandroid.analysis.static_analysis.RT_JAR', '/path/to/rt.jar'), \
                patch('rvandroid.analysis.static_analysis.MOP_DIR', '/mock/mop/dir'), \
                patch('rvandroid.analysis.static_analysis.Command') as mock_command_class:
            # Mock failed command execution
            mock_command_instance = MagicMock()
            mock_command_instance.invoke.return_value = MagicMock(code=1, stderr="Test error")
            mock_command_class.return_value = mock_command_instance

            # Expect StaticAnalysisException
            with pytest.raises(StaticAnalysisException, match="Error while executing"):
                run_static_analysis(mock_app, gesda_file, gator_file, reach_file)
