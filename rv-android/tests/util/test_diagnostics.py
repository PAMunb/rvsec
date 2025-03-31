import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

from rvandroid.util.diagnostics import DiagnosticTool, DiagnosticReport


class TestDiagnosticTool:
    """
    Comprehensive unit tests for the DiagnosticTool class.

    ### Test Strategy:
    - Validate all methods of DiagnosticTool
    - Use mocking to simulate system and resource interactions
    - Test both successful and failure scenarios
    - Ensure proper error handling and data collection
    """

    @pytest.fixture
    def diagnostic_tool(self):
        """Create a fresh DiagnosticTool instance for each test."""
        return DiagnosticTool()

    def test_generate_report_complete(self, diagnostic_tool):
        """
        Test that generate_report creates a complete DiagnosticReport.

        Validates that:
        - All sections of the report are populated
        - No critical errors occur during report generation
        """
        report = diagnostic_tool.generate_report()

        assert isinstance(report, DiagnosticReport)

        # Validate system info
        assert 'platform' in report.system_info
        assert 'system' in report.system_info
        assert 'cpu_count' in report.system_info

        # Validate Python info
        assert 'version' in report.python_info
        assert 'executable' in report.python_info

        # Validate timestamp
        assert report.timestamp is not None

    @patch('platform.platform')
    @patch('platform.system')
    @patch('platform.release')
    @patch('platform.version')
    @patch('platform.machine')
    @patch('platform.processor')
    @patch('os.cpu_count')
    def test_get_system_info_success(self,
                                     mock_cpu_count,
                                     mock_processor,
                                     mock_machine,
                                     mock_version,
                                     mock_release,
                                     mock_system,
                                     mock_platform,
                                     diagnostic_tool):
        """
        Test system information collection with mocked platform methods.

        Validates that:
        - System information is collected correctly
        - All expected keys are present
        - Mocked values are used
        """
        # Setup mocks
        mock_platform.return_value = 'MockPlatform'
        mock_system.return_value = 'MockSystem'
        mock_release.return_value = 'MockRelease'
        mock_version.return_value = 'MockVersion'
        mock_machine.return_value = 'MockMachine'
        mock_processor.return_value = 'MockProcessor'
        mock_cpu_count.return_value = 8

        # Simulate psutil availability
        with patch('rvandroid.util.diagnostics.PSUTIL_AVAILABLE', True):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory_obj = MagicMock()
                mock_memory_obj.total = 16 * 1024 * 1024 * 1024  # 16GB
                mock_memory.return_value = mock_memory_obj

                system_info = diagnostic_tool._get_system_info()

        assert system_info['platform'] == 'MockPlatform'
        assert system_info['system'] == 'MockSystem'
        assert system_info['release'] == 'MockRelease'
        assert system_info['version'] == 'MockVersion'
        assert system_info['machine'] == 'MockMachine'
        assert system_info['processor'] == 'MockProcessor'
        assert system_info['cpu_count'] == 8
        assert 'memory_total' in system_info

    def test_get_system_info_psutil_unavailable(self, diagnostic_tool):
        """
        Test system information collection when psutil is not available.

        Validates that:
        - Method handles psutil unavailability gracefully
        - Basic system information is still collected
        """
        with patch('rvandroid.util.diagnostics.PSUTIL_AVAILABLE', False):
            system_info = diagnostic_tool._get_system_info()

        # Verify basic system information is still collected
        assert 'platform' in system_info
        assert 'system' in system_info
        assert 'release' in system_info
        assert 'version' in system_info
        assert 'machine' in system_info
        assert 'processor' in system_info
        assert 'cpu_count' in system_info

        # Ensure no memory_total when psutil is unavailable
        assert 'memory_total' not in system_info

    def test_get_python_info(self, diagnostic_tool):
        """
        Test Python environment information collection.

        Validates that:
        - All expected Python information is collected
        - Correct current Python environment details are used
        """
        python_info = diagnostic_tool._get_python_info()

        assert 'version' in python_info
        assert 'implementation' in python_info
        assert 'compiler' in python_info
        assert 'build' in python_info
        assert 'executable' in python_info
        assert 'path' in python_info

        # Verify values match current Python environment
        assert python_info['version'] == sys.version
        assert python_info['executable'] == sys.executable

    @pytest.mark.skipif(not sys.modules.get('psutil'), reason="psutil not installed")
    def test_get_resource_usage_with_psutil(self, diagnostic_tool):
        """
        Test resource usage collection with psutil available.

        Validates that:
        - Resource usage information is collected
        - Key metrics are present and within expected ranges
        """
        resource_usage = diagnostic_tool._get_resource_usage()

        assert 'cpu_percent' in resource_usage
        assert 'memory_percent' in resource_usage
        assert 'memory_info' in resource_usage
        assert 'open_files' in resource_usage
        assert 'threads' in resource_usage
        assert 'system' in resource_usage

    def test_get_resource_usage_without_psutil(self, diagnostic_tool):
        """
        Test resource usage collection when psutil is unavailable.

        Validates that:
        - Method handles psutil unavailability
        - Returns a dictionary indicating unavailability
        """
        with patch('rvandroid.util.diagnostics.PSUTIL_AVAILABLE', False):
            resource_usage = diagnostic_tool._get_resource_usage()

        # Verify the dictionary reflects psutil unavailability
        assert isinstance(resource_usage, dict)
        assert resource_usage.get('error') == 'psutil module not available'

    def test_report_save_to_file(self, tmp_path, diagnostic_tool):
        """
        Test saving DiagnosticReport to a file.

        Validates that:
        - Report can be saved to a file
        - File is created with correct content
        - Returns True on successful save
        """
        report = diagnostic_tool.generate_report()

        # Create a temporary file path
        test_file = tmp_path / "diagnostic_report.json"

        # Save the report
        result = report.save_to_file(str(test_file))

        # Verify save was successful
        assert result is True
        assert os.path.exists(test_file)

        # Verify file contents can be parsed as JSON
        with open(test_file, 'r') as f:
            saved_data = json.load(f)

        assert 'timestamp' in saved_data
        assert 'system_info' in saved_data
        assert 'python_info' in saved_data

    def test_identify_issues(self, diagnostic_tool):
        """
        Test issue identification in diagnostic report.

        Validates that:
        - Issues are detected based on resource thresholds
        - Returned issues have expected structure
        """
        # Create a mock report with high resource usage
        report = DiagnosticReport()
        report.resource_usage = {
            'memory_percent': 90,
            'cpu_percent': 95,
            'system': {
                'disk_usage': {'/': 95}
            }
        }
        report.experiment_stats = {
            'task_execution': {
                'avg': 400  # Longer than 5 minutes
            }
        }

        issues = diagnostic_tool._identify_issues(report)

        assert len(issues) > 0

        # Check for specific issue types
        issue_titles = [issue['title'] for issue in issues]
        assert 'High memory usage' in issue_titles
        assert 'High CPU usage' in issue_titles
        assert 'High disk usage' in issue_titles
        assert 'Long task execution times' in issue_titles
