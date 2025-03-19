import json
import os
import platform
import socket
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import psutil


@dataclass
class SystemInfo:
    """System information data class."""
    os_name: str = ""
    os_version: str = ""
    python_version: str = ""
    cpu_count: int = 0
    total_memory_gb: float = 0.0
    available_memory_gb: float = 0.0
    disk_space_gb: float = 0.0
    hostname: str = ""

    @staticmethod
    def collect():
        """Collect system information."""
        info = SystemInfo()
        info.os_name = platform.system()
        info.os_version = platform.version()
        info.python_version = platform.python_version()
        info.cpu_count = os.cpu_count() or 0

        # Memory info
        mem_info = psutil.virtual_memory()
        info.total_memory_gb = mem_info.total / (1024 ** 3)
        info.available_memory_gb = mem_info.available / (1024 ** 3)

        # Disk info
        disk_info = psutil.disk_usage('/')
        info.disk_space_gb = disk_info.free / (1024 ** 3)

        # Hostname
        info.hostname = socket.gethostname()

        return info


@dataclass
class AndroidToolInfo:
    """Information about Android tools."""
    adb_version: str = ""
    sdk_version: str = ""
    emulator_version: str = ""

    @staticmethod
    def collect():
        """Collect Android tool information."""
        info = AndroidToolInfo()

        # ADB version
        try:
            process = subprocess.run(['adb', 'version'], capture_output=True, text=True)
            if process.returncode == 0:
                info.adb_version = process.stdout.strip()
        except:
            info.adb_version = "Unknown (command failed)"

        # SDK version
        android_home = os.environ.get('ANDROID_HOME', '')
        if android_home:
            info.sdk_version = f"SDK path: {android_home}"
        else:
            info.sdk_version = "SDK not found in environment"

        # Emulator version
        try:
            process = subprocess.run(['emulator', '-version'], capture_output=True, text=True)
            if process.returncode == 0:
                info.emulator_version = process.stdout.strip()
        except:
            info.emulator_version = "Unknown (command failed)"

        return info


@dataclass
class DiagnosticReport:
    """Full diagnostic report."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    system_info: SystemInfo = field(default_factory=SystemInfo.collect)
    android_info: AndroidToolInfo = field(default_factory=AndroidToolInfo.collect)
    environment_vars: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    components_status: Dict[str, bool] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "system_info": {
                "os_name": self.system_info.os_name,
                "os_version": self.system_info.os_version,
                "python_version": self.system_info.python_version,
                "cpu_count": self.system_info.cpu_count,
                "total_memory_gb": self.system_info.total_memory_gb,
                "available_memory_gb": self.system_info.available_memory_gb,
                "disk_space_gb": self.system_info.disk_space_gb,
                "hostname": self.system_info.hostname
            },
            "android_info": {
                "adb_version": self.android_info.adb_version,
                "sdk_version": self.android_info.sdk_version,
                "emulator_version": self.android_info.emulator_version
            },
            "environment_vars": self.environment_vars,
            "metrics": self.metrics,
            "components_status": self.components_status,
            "errors": self.errors
        }

    def to_json(self, indent=2):
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save_to_file(self, file_path):
        """Save report to a file."""
        with open(file_path, 'w') as f:
            f.write(self.to_json())


class DiagnosticTool:
    """
    Diagnostic tool for rv-android.
    Collects system information, checks component health, and generates reports.
    """

    def __init__(self):
        """Initialize the diagnostic tool."""
        from rvandroid.util.logging_manager import LoggingManager
        self.logger = LoggingManager.get_instance().get_logger('diagnostics')

    def collect_environment_vars(self) -> Dict[str, str]:
        """
        Collect relevant environment variables.

        Returns:
            Dictionary of environment variables
        """
        # List of environment variables we're interested in
        env_vars = [
            "ANDROID_HOME",
            "JAVA_HOME",
            "PATH",
            "RV_MEMORY_FILE",
            "RV_REPETITIONS",
            "RV_TIMEOUTS",
            "RV_TOOLS",
            "RV_SKIP_MONITORS",
            "RV_SKIP_INSTRUMENT",
            "RV_SKIP_STATIC_ANALYSIS",
            "RV_SKIP_EXPERIMENT",
            "RV_NO_WINDOW",
            "RV_DELAY",
            "RV_DEBUG",
            "RV_JCA_SPEC",
            "RV_RT_JAR",
            "RV_RVANDROID_URL"
        ]

        # Collect environment variables
        collected_vars = {}
        for var in env_vars:
            value = os.environ.get(var)
            if value is not None:
                collected_vars[var] = value

        return collected_vars

    def check_android_emulator(self) -> Tuple[bool, Optional[str]]:
        """
        Check if Android emulator is running.

        Returns:
            Tuple of (is_running, error_message)
        """
        try:
            process = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            if process.returncode != 0:
                return False, f"adb command failed: {process.stderr}"

            output = process.stdout
            if 'emulator-' in output:
                return True, None
            else:
                return False, "No emulator device found"
        except Exception as e:
            return False, f"Error checking emulator: {str(e)}"

    def check_components(self) -> Dict[str, bool]:
        """
        Check status of various components.

        Returns:
            Dictionary mapping component names to status (True if OK)
        """
        components = {}

        # Check if adb is available
        try:
            process = subprocess.run(['adb', 'version'], capture_output=True)
            components['adb'] = process.returncode == 0
        except:
            components['adb'] = False

        # Check if emulator is available
        try:
            process = subprocess.run(['emulator', '-list-avds'], capture_output=True)
            components['emulator'] = process.returncode == 0
        except:
            components['emulator'] = False

        # Check if javamop is available (assuming JAVAMOP_HOME is set)
        try:
            javamop_bin = os.path.join(os.environ.get('JAVAMOP_HOME', ''), 'bin', 'javamop')
            if os.path.exists(javamop_bin):
                components['javamop'] = True
            else:
                components['javamop'] = False
        except:
            components['javamop'] = False

        # Check if rv-monitor is available (assuming RV_MONITOR_HOME is set)
        try:
            rv_monitor_bin = os.path.join(os.environ.get('RV_MONITOR_HOME', ''), 'bin', 'rv-monitor')
            if os.path.exists(rv_monitor_bin):
                components['rv_monitor'] = True
            else:
                components['rv_monitor'] = False
        except:
            components['rv_monitor'] = False

        return components

    def collect_performance_metrics(self) -> Dict[str, Any]:
        """
        Collect performance metrics from the performance monitor.

        Returns:
            Dictionary of metrics
        """
        from rvandroid.util.performance_monitor import PerformanceMonitor
        performance_monitor = PerformanceMonitor.get_instance()

        metrics = {}

        # Group metrics by name
        metric_names = set(m.name for m in performance_monitor.metrics)
        for name in metric_names:
            metrics[name] = performance_monitor.get_metrics_stats(name)

        return metrics

    def generate_report(self) -> DiagnosticReport:
        """
        Generate a complete diagnostic report.

        Returns:
            DiagnosticReport instance
        """
        self.logger.info("Generating diagnostic report")

        # Create report
        report = DiagnosticReport()

        # Collect environment variables
        report.environment_vars = self.collect_environment_vars()

        # Check components
        report.components_status = self.check_components()

        # Collect performance metrics
        try:
            report.metrics = self.collect_performance_metrics()
        except Exception as e:
            self.logger.error(f"Error collecting performance metrics: {e}")
            report.errors.append({
                "component": "performance_metrics",
                "error": str(e)
            })

        # Check emulator status
        emulator_running, error = self.check_android_emulator()
        report.components_status['emulator_running'] = emulator_running
        if not emulator_running and error:
            report.errors.append({
                "component": "emulator",
                "error": error
            })

        self.logger.info("Diagnostic report generated")
        return report
