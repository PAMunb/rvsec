# tests/analysis/coverage/test_tracker.py
import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.domain.classes import Classes, Clazz, Method
from rvandroid.parser.log.logcat_parser import parse_logcat_line


class TestCoverageTracker:
    @pytest.fixture
    def mock_static_data(self):
        """Create mock static analysis data matching the logcat structure."""
        classes = Classes()

        # Create mock classes matching logcat content
        main_activity_class = classes.add_clazz(
            "br.unb.cic.cryptoapp.MainActivity",
            is_activity=True,
            is_main_activity=True
        )

        crypto_activity_class = classes.add_clazz(
            "br.unb.cic.cryptoapp.generated.CryptographyActivity",
            is_activity=True,
            is_main_activity=False
        )

        # Add methods matching logcat entries
        methods = [
            Method(
                class_name="br.unb.cic.cryptoapp.MainActivity",
                name="onCreate",
                params=["android.os.Bundle"],
                signature="br.unb.cic.cryptoapp.MainActivity: void onCreate(android.os.Bundle)",
                reachable=True,
                reaches_mop=False,
                directly_reaches_mop=False
            ),
            Method(
                class_name="br.unb.cic.cryptoapp.generated.CryptographyActivity",
                name="executeSecretKeyOperation",
                params=[],
                signature="br.unb.cic.cryptoapp.generated.CryptographyActivity: void executeSecretKeyOperation()",
                reachable=True,
                reaches_mop=True,
                directly_reaches_mop=True
            )
        ]

        for method in methods:
            classes.add_method(method)

        return StaticAnalysisData(
            classes=classes,
            windows=None,
            wtg=None
        )

    @pytest.fixture
    def sample_logcat_file(self, tmp_path):
        """Create a sample logcat file for testing."""
        logcat_content = """
03-24 19:36:38.394  4110  4110 V RVSEC-COV: <br.unb.cic.cryptoapp.MainActivity: void onCreate(android.os.Bundle)>
03-24 19:37:25.398  4110  4110 V RVSEC   : SecretKeySpecSpec,br.unb.cic.cryptoapp.generated.CryptographyActivity,CryptographyActivity,executeSecretKeyOperation,Unknown Source:1,UnsatisfiedConstraint,Using either an invalid algorithm or keyMaterial.length is not randomized.
03-24 19:37:25.400  4110  4110 V RVSEC   : SecretKeySpecSpec,br.unb.cic.cryptoapp.generated.CryptographyActivity,CryptographyActivity,executeSecretKeyOperation,Unknown Source:1,InvalidSequenceOfMethodCalls,unknown
"""
        logcat_path = tmp_path / "sample.logcat"
        logcat_path.write_text(logcat_content)
        return str(logcat_path)

    @patch('rvandroid.analysis.coverage.tracker.EventBus')
    def test_parse_real_logcat_entries(self, mock_event_bus, sample_logcat_file):
        """Test parsing real logcat entries."""
        with open(sample_logcat_file, 'r') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if line:
                error_log, coverage_log = parse_logcat_line(line)

                if 'RVSEC-COV' in line:
                    assert coverage_log is not None
                    assert coverage_log.clazz is not None
                    assert coverage_log.method is not None
                elif 'RVSEC' in line and 'COV' not in line:
                    assert error_log is not None
                    assert error_log.class_full_name is not None
                    assert error_log.method is not None

    @patch('rvandroid.analysis.coverage.tracker.EventBus')
    def test_process_real_logcat_file(self, mock_event_bus, mock_static_data, sample_logcat_file):
        """Test processing a real logcat file."""
        from rvandroid.analysis.coverage.tracker import CoverageTracker

        mock_bus_instance = MagicMock()
        mock_event_bus.get_instance.return_value = mock_bus_instance

        tracker = CoverageTracker(sample_logcat_file, mock_static_data)

        # Simulate tracking
        with open(sample_logcat_file, 'r') as f:
            lines = f.readlines()

        # Process all lines
        tracker.process_lines(lines)

        # Check tracking results
        assert tracker.total_method_calls > 0
        assert tracker.total_errors > 0

        # Verify metrics have been updated
        metrics = tracker.get_coverage_metrics()
        assert metrics is not None
        assert 'method_coverage' in metrics

    def test_get_detailed_metrics(self, mock_static_data, sample_logcat_file):
        """Test retrieving detailed coverage metrics."""
        from rvandroid.analysis.coverage.tracker import CoverageTracker

        tracker = CoverageTracker(sample_logcat_file, mock_static_data)

        # Process lines manually
        with open(sample_logcat_file, 'r') as f:
            lines = f.readlines()

        tracker.process_lines(lines)

        # Get detailed metrics from the underlying repository
        detailed_metrics = tracker.repository.get_underlying_repository().to_dict()

        # Verify structure of detailed metrics
        assert 'metrics' in detailed_metrics
        assert 'classes' in detailed_metrics
        assert 'errors' in detailed_metrics
