# tests/analysis/coverage/test_analyzer.py
from unittest.mock import MagicMock, patch

import pytest

from rvandroid.domain.classes import Classes, Method
from rvandroid.domain.log import RvCoverageLog, RvErrorLog
from rvandroid.domain.static import StaticAnalysisData


class TestCoverageAnalyzer:
    @pytest.fixture
    def mock_static_data(self):
        """Create mock static analysis data matching real-world logcat structure."""
        classes = Classes()

        # Create classes matching the logcat
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
            ),
            Method(
                class_name="br.unb.cic.cryptoapp.generated.CryptographyActivity",
                name="encryptWithSecretKey",
                params=["java.lang.String", "java.lang.String"],
                signature="br.unb.cic.cryptoapp.generated.CryptographyActivity: byte[] encryptWithSecretKey(java.lang.String,java.lang.String)",
                reachable=True,
                reaches_mop=True,
                directly_reaches_mop=False
            )
        ]

        for method in methods:
            classes.add_method(method)

        return StaticAnalysisData(
            classes=classes,
            windows=None,
            wtg=None
        )

    @patch('rvandroid.analysis.coverage.tracker.EventBus')
    def test_initialization_with_static_data(self, mock_event_bus, mock_static_data):
        """Test analyzer initialization with realistic static data."""
        from rvandroid.analysis.coverage.analyzer import CoverageAnalyzer

        mock_event_bus.get_instance.return_value = MagicMock()

        analyzer = CoverageAnalyzer(static_data=mock_static_data)

        # Verify repository contents
        assert len(analyzer.repository.classes) == 2
        assert "br.unb.cic.cryptoapp.MainActivity" in analyzer.repository.classes
        assert "br.unb.cic.cryptoapp.generated.CryptographyActivity" in analyzer.repository.classes

    @patch('rvandroid.analysis.coverage.tracker.EventBus')
    def test_add_method_call(self, mock_event_bus, mock_static_data):
        """Test adding a method call to the repository with realistic data."""
        from rvandroid.analysis.coverage.analyzer import CoverageAnalyzer

        mock_event_bus.get_instance.return_value = MagicMock()

        analyzer = CoverageAnalyzer(static_data=mock_static_data)

        coverage_log = RvCoverageLog(
            clazz="br.unb.cic.cryptoapp.generated.CryptographyActivity",
            method="executeSecretKeyOperation",
            params="",
            signature="br.unb.cic.cryptoapp.generated.CryptographyActivity: void executeSecretKeyOperation()"
        )

        analyzer.add_method_call(coverage_log)

        # Verify method call tracking
        class_data = analyzer.repository.classes["br.unb.cic.cryptoapp.generated.CryptographyActivity"]
        method_found = any(
            method.signature == "br.unb.cic.cryptoapp.generated.CryptographyActivity: void executeSecretKeyOperation()"
            and method.called
            for method in class_data.methods.values()
        )
        assert method_found

    @patch('rvandroid.analysis.coverage.tracker.EventBus')
    def test_add_error(self, mock_event_bus, mock_static_data):
        """Test adding an error to the repository with realistic data."""
        from rvandroid.analysis.coverage.analyzer import CoverageAnalyzer

        mock_event_bus.get_instance.return_value = MagicMock()

        analyzer = CoverageAnalyzer(static_data=mock_static_data)

        error_log = RvErrorLog(
            spec="SecretKeySpecSpec",
            error_type="UnsatisfiedConstraint",
            class_full_name="br.unb.cic.cryptoapp.generated.CryptographyActivity",
            method="executeSecretKeyOperation",
            source="Unknown Source:1",
            message="Using either an invalid algorithm or keyMaterial.length is not randomized."
        )

        analyzer.add_error(error_log)

        # Verify error tracking
        assert len(analyzer.repository.errors) == 1
        assert error_log in analyzer.repository.errors

    @patch('rvandroid.analysis.coverage.tracker.EventBus')
    def test_get_coverage_metrics(self, mock_event_bus, mock_static_data):
        """Test getting coverage metrics with realistic method calls and errors."""
        from rvandroid.analysis.coverage.analyzer import CoverageAnalyzer

        mock_event_bus.get_instance.return_value = MagicMock()

        analyzer = CoverageAnalyzer(static_data=mock_static_data)

        # Add method calls
        method_calls = [
            RvCoverageLog(
                clazz="br.unb.cic.cryptoapp.MainActivity",
                method="onCreate",
                params="android.os.Bundle",
                signature="br.unb.cic.cryptoapp.MainActivity: void onCreate(android.os.Bundle)"
            ),
            RvCoverageLog(
                clazz="br.unb.cic.cryptoapp.generated.CryptographyActivity",
                method="executeSecretKeyOperation",
                params="",
                signature="br.unb.cic.cryptoapp.generated.CryptographyActivity: void executeSecretKeyOperation()"
            )
        ]

        # Add errors
        errors = [
            RvErrorLog(
                spec="SecretKeySpecSpec",
                error_type="UnsatisfiedConstraint",
                class_full_name="br.unb.cic.cryptoapp.generated.CryptographyActivity",
                method="executeSecretKeyOperation",
                source="Unknown Source:1",
                message="Using either an invalid algorithm or keyMaterial.length is not randomized."
            )
        ]

        # Process method calls and errors
        for call in method_calls:
            analyzer.add_method_call(call)

        for error in errors:
            analyzer.add_error(error)

        # Get coverage metrics
        metrics = analyzer.get_coverage_metrics()

        # Verify metrics structure and values
        assert "method_coverage" in metrics
        assert "activities_coverage" in metrics
        assert "methods_jca_reachable_coverage" in metrics
        assert "total_errors" in metrics
        assert "total_method_calls" in metrics

        # Verify metric values make sense
        assert metrics["total_method_calls"] > 0
        assert metrics["total_errors"] > 0
        assert 0 <= metrics["method_coverage"] <= 100
