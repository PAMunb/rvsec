"""
Unit tests for the experiment constants module.

This module ensures that all path generation functions in the
rv_experiment.constants module are working correctly.

### Test Strategy:
- Test each path generation function with sample inputs.
- Verify that the generated paths are correct and follow the expected structure.
- Ensure that the functions are pure and have no side effects.
"""

import os
import pytest
from rv_experiment import constants

class TestConstants:
    """
    Test suite for the constants and path generation functions.
    """

    def test_get_absolute_path(self):
        """
        Test that get_absolute_path returns the correct absolute path.
        """
        relative_path = "some/relative/path"
        expected_path = os.path.join(constants.WORKING_DIR, relative_path)
        assert constants.get_absolute_path(relative_path) == expected_path

    def test_get_experiment_dir(self):
        """
        Test that get_experiment_dir returns the correct experiment directory path.
        """
        results_dir = "results"
        experiment_id = "test_experiment"
        expected_path = os.path.join(results_dir, experiment_id)
        assert constants.get_experiment_dir(results_dir, experiment_id) == expected_path

    def test_get_apk_results_dir(self):
        """
        Test that get_apk_results_dir returns the correct APK-specific results directory.
        """
        results_dir = "results"
        experiment_id = "test_experiment"
        apk_name = "test_app.apk"
        expected_path = os.path.join(results_dir, experiment_id, apk_name)
        assert constants.get_apk_results_dir(results_dir, experiment_id, apk_name) == expected_path

    def test_get_static_analysis_source_path(self):
        """
        Test that get_static_analysis_source_path returns the correct path for static analysis files.
        """
        output_dir = "out"
        apk_name = "test_app"
        extension = ".gesda"
        expected_path = os.path.join(output_dir, constants.STATIC_ANALYSIS_DIR, f"{apk_name}{extension}")
        assert constants.get_static_analysis_source_path(output_dir, apk_name, extension) == expected_path

    def test_get_instrumented_apk_path(self):
        """
        Test that get_instrumented_apk_path returns the correct path for instrumented APKs.
        """
        output_dir = "out"
        apk_name = "test_app.apk"
        expected_path = os.path.join(output_dir, constants.INSTRUMENTED_APKS_DIR, apk_name)
        assert constants.get_instrumented_apk_path(output_dir, apk_name) == expected_path
