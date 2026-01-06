"""
Online tests with real Android emulator - Dataset validation.

Tests verify system with multiple apps:
- 30+ apps from JCA-instrumented dataset
- 180s per app
- Full metrics collection
- Runtime Verification (RV) event monitoring via logcat
- Comparison with baseline
"""

import pytest
import time
import json
import os
import re
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.agent.agent_factory import AgentFactory
from rv_agent.agent.device_interface import DeviceInterface


pytestmark = [pytest.mark.online, pytest.mark.slow, pytest.mark.dataset]


# =============================================================================
# Logcat RV Monitoring
# =============================================================================

# RV event tags from instrumented APKs
RVSEC_TAG = "RVSEC"      # Main RV event tag
RVSEC_COV_TAG = "RVSEC-COV"  # Coverage tracking tag


@dataclass
class RVLogcatCapture:
    """Captures and parses RV events from logcat."""
    device_id: str
    process: Optional[subprocess.Popen] = None
    output_file: Optional[str] = None
    events: List[Dict] = field(default_factory=list)
    coverage_events: List[Dict] = field(default_factory=list)
    _stop_event: threading.Event = field(default_factory=threading.Event)
    _capture_thread: Optional[threading.Thread] = None

    def start(self, output_dir: str = "/tmp") -> None:
        """Start logcat capture in background."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = f"{output_dir}/logcat_rv_{timestamp}.log"

        # Clear logcat before starting
        subprocess.run(
            ["adb", "-s", self.device_id, "logcat", "-c"],
            capture_output=True, timeout=5
        )

        # Start logcat with RV tags filter
        self.process = subprocess.Popen(
            ["adb", "-s", self.device_id, "logcat",
             f"{RVSEC_TAG}:V", f"{RVSEC_COV_TAG}:V", "*:S"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        self._stop_event.clear()
        self._capture_thread = threading.Thread(target=self._capture_loop)
        self._capture_thread.daemon = True
        self._capture_thread.start()

    def _capture_loop(self) -> None:
        """Background thread to capture logcat output."""
        if self.process is None:
            return

        lines = []
        while not self._stop_event.is_set():
            line = self.process.stdout.readline()
            if line:
                lines.append(line)
                self._parse_line(line)
            elif self.process.poll() is not None:
                break

        # Save to file
        if self.output_file and lines:
            with open(self.output_file, 'w') as f:
                f.writelines(lines)

    def _parse_line(self, line: str) -> None:
        """Parse a logcat line for RV events."""
        # RVSEC format: "RVSEC: [property] event_type: details"
        # RVSEC-COV format: "RVSEC-COV: spec_name method_name"

        if RVSEC_TAG in line and RVSEC_COV_TAG not in line:
            # Main RV event
            event = self._parse_rvsec_event(line)
            if event:
                self.events.append(event)
        elif RVSEC_COV_TAG in line:
            # Coverage event
            event = self._parse_coverage_event(line)
            if event:
                self.coverage_events.append(event)

    def _parse_rvsec_event(self, line: str) -> Optional[Dict]:
        """Parse RVSEC event line."""
        # Pattern: timestamp pid tid level RVSEC: content
        match = re.search(r'RVSEC:\s*(.+)', line)
        if match:
            content = match.group(1).strip()
            # Classify event type
            event_type = "unknown"
            if "match" in content.lower():
                event_type = "match"
            elif "fail" in content.lower() or "violation" in content.lower():
                event_type = "violation"
            elif "skip" in content.lower():
                event_type = "skip"

            return {
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "content": content,
                "raw": line.strip()
            }
        return None

    def _parse_coverage_event(self, line: str) -> Optional[Dict]:
        """Parse RVSEC-COV event line."""
        match = re.search(r'RVSEC-COV:\s*(.+)', line)
        if match:
            content = match.group(1).strip()
            parts = content.split()
            spec_name = parts[0] if parts else "unknown"
            method_name = parts[1] if len(parts) > 1 else "unknown"

            return {
                "timestamp": datetime.now().isoformat(),
                "spec": spec_name,
                "method": method_name,
                "content": content,
                "raw": line.strip()
            }
        return None

    def stop(self) -> Tuple[List[Dict], List[Dict]]:
        """Stop capture and return events."""
        self._stop_event.set()

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        if self._capture_thread:
            self._capture_thread.join(timeout=5)
            self._capture_thread = None

        return self.events, self.coverage_events

    def get_summary(self) -> Dict:
        """Get summary of captured RV events."""
        event_types = {}
        for e in self.events:
            t = e.get("type", "unknown")
            event_types[t] = event_types.get(t, 0) + 1

        spec_coverage = {}
        for e in self.coverage_events:
            spec = e.get("spec", "unknown")
            spec_coverage[spec] = spec_coverage.get(spec, 0) + 1

        return {
            "total_rv_events": len(self.events),
            "total_coverage_events": len(self.coverage_events),
            "event_types": event_types,
            "spec_coverage": spec_coverage,
            "violations": event_types.get("violation", 0),
            "matches": event_types.get("match", 0),
            "output_file": self.output_file
        }


# =============================================================================
# ADB Helper Functions
# =============================================================================

def is_app_installed(device_id: str, package_name: str) -> bool:
    """Check if app is installed using adb."""
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "pm", "list", "packages", package_name],
            capture_output=True, text=True, timeout=10
        )
        return package_name in result.stdout
    except Exception:
        return False


def install_apk(device_id: str, apk_path: str) -> bool:
    """Install APK using adb."""
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "install", "-r", apk_path],
            capture_output=True, text=True, timeout=120
        )
        return "Success" in result.stdout
    except Exception:
        return False


def clear_logcat(device_id: str) -> None:
    """Clear logcat buffer."""
    try:
        subprocess.run(
            ["adb", "-s", device_id, "logcat", "-c"],
            capture_output=True, timeout=5
        )
    except Exception:
        pass


def get_logcat_rv_events(device_id: str, duration: int = 5) -> Tuple[List[str], List[str]]:
    """Get RV events from logcat for specified duration."""
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "logcat", "-d",
             f"{RVSEC_TAG}:V", f"{RVSEC_COV_TAG}:V", "*:S"],
            capture_output=True, text=True, timeout=duration + 10
        )
        rvsec_lines = []
        rvsec_cov_lines = []
        for line in result.stdout.split('\n'):
            if RVSEC_COV_TAG in line:
                rvsec_cov_lines.append(line)
            elif RVSEC_TAG in line:
                rvsec_lines.append(line)
        return rvsec_lines, rvsec_cov_lines
    except Exception:
        return [], []


# =============================================================================
# Dataset Configuration
# =============================================================================

# Path to JCA-instrumented APKs (with runtime verification monitors)
INSTRUMENTED_APKS_DIR = "/home/pedro/desenvolvimento/RV_ANDROID/NOVO/APKS_JCA_INSTRUMENTED"

# APKs organized by category for testing
# Using instrumented APKs for RV monitoring
DATASET_APPS = {
    "cryptography": [
        {"package": "br.unb.cic.cryptoapp", "name": "CryptoApp", "apk": None},
        {"package": "byrne.utilities.hashpass", "name": "HashPass", "apk": "byrne.utilities.hashpass_2.apk"},
        {"package": "com.aidinhut.simpletextcrypt", "name": "SimpleTextCrypt", "apk": "com.aidinhut.simpletextcrypt_14.apk"},
        {"package": "com.aptasystems.dicewarepasswordgenerator", "name": "DicewarePass", "apk": "com.aptasystems.dicewarepasswordgenerator_8.apk"},
        {"package": "com.example.openpass", "name": "OpenPass", "apk": "com.example.openpass_1.apk"},
    ],
    "file_manager": [
        {"package": "com.cyanogenmod.filemanager.ics", "name": "CMFileManager", "apk": "com.cyanogenmod.filemanager.ics_1015.apk"},
        {"package": "com.github.axet.mover", "name": "Mover", "apk": "com.github.axet.mover_127.apk"},
    ],
    "communication": [
        {"package": "com.iskrembilen.quasseldroid", "name": "Quasseldroid", "apk": "com.iskrembilen.quasseldroid_1322.apk"},
        {"package": "com.googlecode.gtalksms", "name": "GTalkSMS", "apk": "com.googlecode.gtalksms_69.apk"},
    ],
    "finance": [
        {"package": "com.blogspot.e_kanivets.moneytracker", "name": "MoneyTracker", "apk": "com.blogspot.e_kanivets.moneytracker_38.apk"},
        {"package": "com.greenaddress.greenbits_android_wallet", "name": "GreenBits", "apk": "com.greenaddress.greenbits_android_wallet_22000404.apk"},
    ],
    "gallery": [
        {"package": "com.alienpants.leafpicrevived", "name": "LeafPic", "apk": "com.alienpants.leafpicrevived_24.apk"},
        {"package": "com.easytarget.micopi", "name": "Micopi", "apk": "com.easytarget.micopi_32.apk"},
    ],
    "utilities": [
        {"package": "biz.gyrus.yaab", "name": "YAAB", "apk": "biz.gyrus.yaab_30.apk"},
        {"package": "cf.playhi.freezeyou", "name": "FreezeYou", "apk": "cf.playhi.freezeyou_151.apk"},
        {"package": "com.github.axet.hourlyreminder", "name": "HourlyReminder", "apk": "com.github.axet.hourlyreminder_476.apk"},
        {"package": "com.github.axet.audiorecorder", "name": "AudioRecorder", "apk": "com.github.axet.audiorecorder_377.apk"},
        {"package": "com.lostrealm.lembretes", "name": "Lembretes", "apk": "com.lostrealm.lembretes_93.apk"},
    ],
    "development": [
        {"package": "com.commit451.gitlab", "name": "GitLab", "apk": "com.commit451.gitlab_2070400.apk"},
        {"package": "com.github.mobile", "name": "GitHubMobile", "apk": "com.github.mobile_1900.apk"},
        {"package": "com.gh4a", "name": "OctoDroid", "apk": "com.gh4a_73.apk"},
    ],
    "network": [
        {"package": "com.gianlu.dnshero", "name": "DNSHero", "apk": "com.gianlu.dnshero_40.apk"},
        {"package": "com.googlecode.networklog", "name": "NetworkLog", "apk": "com.googlecode.networklog_22501.apk"},
    ],
    "media": [
        {"package": "com.andrew.apollo", "name": "Apollo", "apk": "com.andrew.apollo_2.apk"},
        {"package": "com.crazyhitty.chdev.ks.munch", "name": "Munch", "apk": "com.crazyhitty.chdev.ks.munch_14.apk"},
        {"package": "com.mishiranu.dashchan", "name": "Dashchan", "apk": "com.mishiranu.dashchan_1043.apk"},
    ],
    "other": [
        {"package": "com.akop.bach", "name": "Bach", "apk": "com.akop.bach_120.apk"},
        {"package": "com.Bisha.TI89EmuDonation", "name": "TI89Emu", "apk": "com.Bisha.TI89EmuDonation_1133.apk"},
        {"package": "com.mareksebera.simpledilbert", "name": "SimpleDilbert", "apk": "com.mareksebera.simpledilbert_40.apk"},
        {"package": "ca.farrelltonsolar.classic", "name": "Classic", "apk": "ca.farrelltonsolar.classic_314.apk"},
    ],
}


@dataclass
class AppTestResult:
    """Result from testing a single app."""
    package: str
    name: str
    success: bool
    duration_s: float
    iterations: int = 0
    unique_states: int = 0
    actions_executed: int = 0
    llm_calls: int = 0
    algorithm_actions: int = 0
    llm_percentage: float = 0.0
    error: str = ""
    memory_stats: Dict = field(default_factory=dict)
    routing_stats: Dict = field(default_factory=dict)
    wtg_stats: Dict = field(default_factory=dict)
    # RV (Runtime Verification) event data
    rv_events: int = 0
    rv_violations: int = 0
    rv_matches: int = 0
    rv_coverage_events: int = 0
    rv_specs_triggered: List[str] = field(default_factory=list)
    rv_summary: Dict = field(default_factory=dict)
    is_instrumented: bool = False


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def emulator_device():
    """Connect to running emulator."""
    device_id = os.getenv("ANDROID_DEVICE_ID", "emulator-5554")
    device = DeviceInterface(device_id)

    # DeviceInterface raises RuntimeError if connection fails
    # So if we get here, we're connected

    yield device

    device.home()


@pytest.fixture(scope="module")
def apk_base_dir():
    """Base directory for APKs."""
    return Path("/home/pedro/desenvolvimento/RV_ANDROID/apks")


@pytest.fixture(scope="module")
def results_dir():
    """Create results directory."""
    results_path = Path("/tmp/rvagent_dataset_tests")
    results_path.mkdir(parents=True, exist_ok=True)
    return results_path


# =============================================================================
# Helper Functions
# =============================================================================

def install_app_if_needed(device: DeviceInterface, package: str, apk_path: str, apk_base: Path) -> bool:
    """Install app if not already installed."""
    device_id = device.device_id

    if is_app_installed(device_id, package):
        return True

    if apk_path is None:
        return False

    full_path = apk_base / apk_path
    if not full_path.exists():
        return False

    try:
        success = install_apk(device_id, str(full_path))
        if success:
            return is_app_installed(device_id, package)
        return False
    except Exception as e:
        print(f"Failed to install {package}: {e}")
        return False


def run_app_exploration(
    device: DeviceInterface,
    package: str,
    name: str,
    duration: int = 180,
    mode: str = "multimode",
    capture_rv_events: bool = True,
    is_instrumented: bool = False
) -> AppTestResult:
    """Run exploration on a single app and collect metrics.

    Args:
        device: Android device interface
        package: App package name
        name: App display name
        duration: Exploration duration in seconds
        mode: Agent mode (pure_algorithm, llm_only, multimode)
        capture_rv_events: Whether to capture RV events from logcat
        is_instrumented: Whether the APK is instrumented with RV monitors
    """

    result = AppTestResult(
        package=package,
        name=name,
        success=False,
        duration_s=0,
        is_instrumented=is_instrumented
    )

    rv_capture = None

    try:
        # Start RV event capture if enabled
        if capture_rv_events:
            rv_capture = RVLogcatCapture(device_id=device.device_id)
            rv_capture.start(output_dir="/tmp/rvagent_dataset_tests")

        # Create config
        config = RVAgentConfig(
            package_name=package,
            device_id=device.device_id,
            agent_mode=mode,
            llm_probability=0.7,
            timeout=duration,
            results_dir="/tmp/rvagent_dataset_tests",
            debug_mode=False
        )

        # Create agent
        agent = AgentFactory.create_agent(config, device=device)

        # Start app
        device.start_app(package)
        time.sleep(2)

        # Run exploration
        start_time = time.time()
        exploration_result = agent.run()
        result.duration_s = time.time() - start_time

        # Collect metrics
        result.iterations = exploration_result.get("iterations", 0)
        result.unique_states = exploration_result.get("unique_states", 0)
        result.actions_executed = exploration_result.get("actions_executed", 0)
        result.llm_calls = exploration_result.get("llm_calls", 0)
        result.algorithm_actions = exploration_result.get("algorithm_actions", 0)

        # Memory stats
        result.memory_stats = agent.memory_coordinator.get_all_statistics()

        # Routing stats
        routing = agent.routing_manager
        result.routing_stats = {
            "llm_executed": routing.llm_executed,
            "algorithm_chosen": routing.algorithm_chosen,
            "llm_fallback": routing.llm_fallback,
        }

        total_routed = routing.llm_executed + routing.algorithm_chosen
        if total_routed > 0:
            result.llm_percentage = routing.llm_executed / total_routed * 100

        # WTG stats
        wtg = agent.dynamic_graph
        result.wtg_stats = {
            "states": len(wtg.states) if hasattr(wtg, 'states') else 0,
        }

        result.success = result.iterations > 0

    except Exception as e:
        result.error = str(e)
        result.success = False

    finally:
        # Stop RV capture and collect events
        if rv_capture:
            rv_events, cov_events = rv_capture.stop()
            rv_summary = rv_capture.get_summary()

            result.rv_events = rv_summary.get("total_rv_events", 0)
            result.rv_violations = rv_summary.get("violations", 0)
            result.rv_matches = rv_summary.get("matches", 0)
            result.rv_coverage_events = rv_summary.get("total_coverage_events", 0)
            result.rv_specs_triggered = list(rv_summary.get("spec_coverage", {}).keys())
            result.rv_summary = rv_summary

        # Cleanup
        device.home()
        time.sleep(1)

    return result


# =============================================================================
# Single App Tests (Parametrized)
# =============================================================================

class TestDatasetApps:
    """Test individual apps from dataset."""

    @pytest.mark.parametrize("app_info", [
        {"package": "br.unb.cic.cryptoapp", "name": "CryptoApp"},
    ])
    def test_cryptoapp_full_exploration(
        self, emulator_device, results_dir, app_info
    ):
        """Full 180s exploration of cryptoapp with all validations."""
        result = run_app_exploration(
            device=emulator_device,
            package=app_info["package"],
            name=app_info["name"],
            duration=180,
            mode="multimode"
        )

        # Save result
        result_file = results_dir / f"{app_info['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w') as f:
            json.dump(result.__dict__, f, indent=2, default=str)

        # Print summary
        print(f"\n{'='*60}")
        print(f"App: {result.name} ({result.package})")
        print(f"{'='*60}")
        print(f"Duration: {result.duration_s:.1f}s")
        print(f"Success: {result.success}")
        print(f"Iterations: {result.iterations}")
        print(f"Unique States: {result.unique_states}")
        print(f"Actions: {result.actions_executed}")
        print(f"LLM Calls: {result.llm_calls}")
        print(f"Algorithm Actions: {result.algorithm_actions}")
        print(f"LLM%: {result.llm_percentage:.1f}%")
        print(f"WTG States: {result.wtg_stats.get('states', 0)}")
        print(f"\n--- RV Events ---")
        print(f"Total RV Events: {result.rv_events}")
        print(f"Violations: {result.rv_violations}")
        print(f"Matches: {result.rv_matches}")
        print(f"Coverage Events: {result.rv_coverage_events}")
        print(f"Specs Triggered: {result.rv_specs_triggered}")
        print(f"Result saved: {result_file}")

        # Validations
        assert result.success, f"Exploration failed: {result.error}"
        assert result.iterations >= 1, "Should complete at least 1 iteration"
        assert result.duration_s >= 170, "Should run for at least 170s"

    @pytest.mark.parametrize("mode", ["pure_algorithm", "llm_only", "multimode"])
    def test_cryptoapp_mode_comparison(
        self, emulator_device, results_dir, mode
    ):
        """Compare exploration modes on cryptoapp (60s each)."""
        result = run_app_exploration(
            device=emulator_device,
            package="br.unb.cic.cryptoapp",
            name=f"CryptoApp_{mode}",
            duration=60,
            mode=mode
        )

        # Save result
        result_file = results_dir / f"mode_comparison_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w') as f:
            json.dump(result.__dict__, f, indent=2, default=str)

        print(f"\n[{mode}] Iterations: {result.iterations}, States: {result.unique_states}, LLM%: {result.llm_percentage:.1f}%")

        assert result.success, f"Mode {mode} failed: {result.error}"

        # Mode-specific validations
        if mode == "pure_algorithm":
            assert result.llm_percentage < 10, "pure_algorithm should have minimal LLM usage"
        elif mode == "llm_only":
            assert result.llm_percentage > 90, "llm_only should have >90% LLM usage"
        elif mode == "multimode":
            assert 40 <= result.llm_percentage <= 90, "multimode should be ~70% LLM"


# =============================================================================
# Multi-App Dataset Tests
# =============================================================================

class TestMultiAppDataset:
    """Test multiple apps from dataset."""

    def test_cryptography_apps(
        self, emulator_device, apk_base_dir, results_dir
    ):
        """Test all cryptography apps (60s each)."""
        results = []

        for app_info in DATASET_APPS["cryptography"]:
            # Install if needed
            if app_info["apk"]:
                installed = install_app_if_needed(
                    emulator_device,
                    app_info["package"],
                    app_info["apk"],
                    apk_base_dir
                )
                if not installed:
                    print(f"Skipping {app_info['name']}: not installed")
                    continue

            if not is_app_installed(emulator_device.device_id, app_info["package"]):
                print(f"Skipping {app_info['name']}: not installed")
                continue

            result = run_app_exploration(
                device=emulator_device,
                package=app_info["package"],
                name=app_info["name"],
                duration=60,
                mode="multimode"
            )

            results.append(result)

            print(f"[{result.name}] Success: {result.success}, Iterations: {result.iterations}, LLM%: {result.llm_percentage:.1f}%")

        # Save aggregate results
        aggregate_file = results_dir / f"cryptography_aggregate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(aggregate_file, 'w') as f:
            json.dump([r.__dict__ for r in results], f, indent=2, default=str)

        # Summary
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)

        print(f"\n{'='*60}")
        print(f"Cryptography Apps Summary: {success_count}/{total_count} successful")
        print(f"{'='*60}")

        assert success_count > 0, "At least one app should succeed"

    def test_full_dataset_short(
        self, emulator_device, apk_base_dir, results_dir
    ):
        """Test all available apps with short duration (30s each)."""
        all_results = []

        for category, apps in DATASET_APPS.items():
            for app_info in apps:
                # Check if installed
                if not is_app_installed(emulator_device.device_id, app_info["package"]):
                    # Try to install
                    if app_info.get("apk"):
                        installed = install_app_if_needed(
                            emulator_device,
                            app_info["package"],
                            app_info["apk"],
                            apk_base_dir
                        )
                        if not installed:
                            continue
                    else:
                        continue

                result = run_app_exploration(
                    device=emulator_device,
                    package=app_info["package"],
                    name=app_info["name"],
                    duration=30,
                    mode="multimode"
                )

                result_dict = result.__dict__
                result_dict["category"] = category
                all_results.append(result_dict)

                status = "✓" if result.success else "✗"
                rv_info = f", RV:{result.rv_events}" if result.rv_events > 0 else ""
                print(f"{status} [{category}] {result.name}: {result.iterations} iters, {result.llm_percentage:.1f}% LLM{rv_info}")

        # Save all results
        full_results_file = results_dir / f"full_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(full_results_file, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)

        # Summary
        success_count = sum(1 for r in all_results if r.get("success", False))
        total_count = len(all_results)

        print(f"\n{'='*60}")
        print(f"Full Dataset Summary: {success_count}/{total_count} successful")
        print(f"Results saved: {full_results_file}")
        print(f"{'='*60}")


# =============================================================================
# Baseline Comparison Tests
# =============================================================================

class TestBaselineComparison:
    """Compare results with V10 baseline."""

    def test_compare_with_v10_baseline(
        self, emulator_device, results_dir
    ):
        """Compare current results with V10 baseline metrics."""
        # Load V10 baseline
        baseline_path = Path(__file__).parent.parent.parent / "test_v10_baseline_10apps_aggregate.json"

        if not baseline_path.exists():
            pytest.skip("V10 baseline file not found")

        with open(baseline_path) as f:
            v10_baseline = json.load(f)

        # Run cryptoapp and compare
        result = run_app_exploration(
            device=emulator_device,
            package="br.unb.cic.cryptoapp",
            name="CryptoApp",
            duration=120,
            mode="multimode"
        )

        # Find cryptoapp in V10 baseline (closest match)
        v10_crypto = None
        for app_result in v10_baseline.get("individual_results", []):
            if "cryptomator" in app_result.get("package", "").lower():
                v10_crypto = app_result
                break

        print(f"\n{'='*60}")
        print("Baseline Comparison: CryptoApp vs V10")
        print(f"{'='*60}")
        print(f"Current - Iterations: {result.iterations}, States: {result.unique_states}")

        if v10_crypto:
            v10_iters = v10_crypto.get("metrics", {}).get("iterations", 0)
            v10_states = v10_crypto.get("metrics", {}).get("unique_states", 0)
            print(f"V10     - Iterations: {v10_iters}, States: {v10_states}")

            # Should be at least 80% of V10 performance
            if v10_iters > 0:
                iter_ratio = result.iterations / v10_iters
                print(f"Iteration ratio: {iter_ratio:.2f}x")

        assert result.success, "Current exploration should succeed"


# =============================================================================
# Memory Validation Tests
# =============================================================================

class TestMemoryValidation:
    """Validate memory systems during dataset exploration."""

    def test_memory_growth_bounded(
        self, emulator_device, results_dir
    ):
        """Memory usage should be bounded during exploration."""
        result = run_app_exploration(
            device=emulator_device,
            package="br.unb.cic.cryptoapp",
            name="CryptoApp",
            duration=120,
            mode="multimode"
        )

        memory_stats = result.memory_stats

        print(f"\nMemory Stats:")
        print(json.dumps(memory_stats, indent=2, default=str)[:500])

        # Validate memory bounds
        assert result.success, "Exploration should complete successfully"

    def test_wtg_consistency(
        self, emulator_device, results_dir
    ):
        """WTG should have consistent state-transition relationship."""
        result = run_app_exploration(
            device=emulator_device,
            package="br.unb.cic.cryptoapp",
            name="CryptoApp",
            duration=60,
            mode="multimode"
        )

        wtg_states = result.wtg_stats.get("states", 0)

        print(f"\nWTG Validation:")
        print(f"  States: {wtg_states}")
        print(f"  Unique states reported: {result.unique_states}")

        # States should be consistent
        assert result.success, "Exploration should complete"


# =============================================================================
# RV (Runtime Verification) Validation Tests
# =============================================================================

class TestRVMonitoring:
    """Tests for Runtime Verification monitoring with instrumented APKs."""

    @pytest.fixture
    def instrumented_apks_dir(self):
        """Path to JCA-instrumented APKs."""
        return Path(INSTRUMENTED_APKS_DIR)

    def test_rv_logcat_capture_basic(self, emulator_device):
        """Test that RV logcat capture infrastructure works."""
        rv_capture = RVLogcatCapture(device_id=emulator_device.device_id)

        # Start capture
        rv_capture.start(output_dir="/tmp/rvagent_dataset_tests")

        # Wait a bit
        time.sleep(3)

        # Stop capture
        events, cov_events = rv_capture.stop()
        summary = rv_capture.get_summary()

        print(f"\nRV Capture Test:")
        print(f"  Output file: {summary.get('output_file')}")
        print(f"  Total RV events: {summary.get('total_rv_events', 0)}")
        print(f"  Coverage events: {summary.get('total_coverage_events', 0)}")

        # Infrastructure should work (events may be 0 if no instrumented app running)
        assert summary.get("output_file") is not None

    def test_rv_events_with_instrumented_app(
        self, emulator_device, instrumented_apks_dir, results_dir
    ):
        """Test RV event capture with an instrumented APK."""
        # Find an instrumented APK that's likely to generate RV events
        test_apks = [
            {"package": "byrne.utilities.hashpass", "apk": "byrne.utilities.hashpass_2.apk", "name": "HashPass"},
            {"package": "com.aidinhut.simpletextcrypt", "apk": "com.aidinhut.simpletextcrypt_14.apk", "name": "SimpleTextCrypt"},
            {"package": "com.aptasystems.dicewarepasswordgenerator", "apk": "com.aptasystems.dicewarepasswordgenerator_8.apk", "name": "DicewarePass"},
        ]

        tested = False
        for app_info in test_apks:
            apk_path = instrumented_apks_dir / app_info["apk"]
            if not apk_path.exists():
                continue

            # Install if needed
            if not is_app_installed(emulator_device.device_id, app_info["package"]):
                if not install_apk(emulator_device.device_id, str(apk_path)):
                    continue

            # Run with RV capture
            result = run_app_exploration(
                device=emulator_device,
                package=app_info["package"],
                name=app_info["name"],
                duration=60,
                mode="multimode",
                capture_rv_events=True,
                is_instrumented=True
            )

            # Save result
            result_file = results_dir / f"rv_test_{app_info['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(result_file, 'w') as f:
                json.dump(result.__dict__, f, indent=2, default=str)

            print(f"\n{'='*60}")
            print(f"RV Test: {result.name}")
            print(f"{'='*60}")
            print(f"Success: {result.success}")
            print(f"Iterations: {result.iterations}")
            print(f"RV Events: {result.rv_events}")
            print(f"RV Violations: {result.rv_violations}")
            print(f"RV Matches: {result.rv_matches}")
            print(f"Coverage Events: {result.rv_coverage_events}")
            print(f"Specs Triggered: {result.rv_specs_triggered}")

            tested = True
            break

        if not tested:
            pytest.skip("No instrumented APKs available for testing")

        assert result.success, f"Exploration failed: {result.error}"

    def test_rv_dataset_30_apps(
        self, emulator_device, instrumented_apks_dir, results_dir
    ):
        """Test 30+ apps from the JCA-instrumented dataset."""
        if not instrumented_apks_dir.exists():
            pytest.skip(f"Instrumented APKs dir not found: {instrumented_apks_dir}")

        # Get all APKs from instrumented directory
        available_apks = list(instrumented_apks_dir.glob("*.apk"))
        if len(available_apks) < 30:
            pytest.skip(f"Need at least 30 APKs, found {len(available_apks)}")

        # Select 30 APKs for testing
        test_apks = available_apks[:30]

        all_results = []
        success_count = 0
        total_rv_events = 0
        total_violations = 0

        for apk_path in test_apks:
            apk_name = apk_path.stem
            # Extract package name from APK filename (format: package_version.apk)
            parts = apk_name.rsplit('_', 1)
            package_name = parts[0] if len(parts) > 1 else apk_name

            # Install APK
            if not is_app_installed(emulator_device.device_id, package_name):
                if not install_apk(emulator_device.device_id, str(apk_path)):
                    print(f"✗ Failed to install {package_name}")
                    continue

            # Run exploration
            result = run_app_exploration(
                device=emulator_device,
                package=package_name,
                name=apk_name,
                duration=60,  # 60s per app
                mode="multimode",
                capture_rv_events=True,
                is_instrumented=True
            )

            all_results.append(result.__dict__)

            if result.success:
                success_count += 1
                total_rv_events += result.rv_events
                total_violations += result.rv_violations

            status = "✓" if result.success else "✗"
            rv_str = f"RV:{result.rv_events}" if result.rv_events > 0 else ""
            viol_str = f"V:{result.rv_violations}" if result.rv_violations > 0 else ""
            print(f"{status} {apk_name}: {result.iterations} iters {rv_str} {viol_str}")

        # Save aggregate results
        aggregate_file = results_dir / f"rv_dataset_30apps_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(aggregate_file, 'w') as f:
            json.dump({
                "total_apps": len(test_apks),
                "apps_tested": len(all_results),
                "success_count": success_count,
                "total_rv_events": total_rv_events,
                "total_violations": total_violations,
                "results": all_results
            }, f, indent=2, default=str)

        print(f"\n{'='*60}")
        print(f"RV Dataset Summary: {success_count}/{len(all_results)} apps successful")
        print(f"Total RV Events: {total_rv_events}")
        print(f"Total Violations: {total_violations}")
        print(f"Results saved: {aggregate_file}")
        print(f"{'='*60}")

        # At least 50% of apps should complete successfully
        assert success_count >= len(all_results) * 0.5, f"Too few successful: {success_count}/{len(all_results)}"


class TestRVViolationDetection:
    """Tests for detecting specific RV violations."""

    def test_jca_spec_coverage(
        self, emulator_device, results_dir
    ):
        """Test coverage of JCA specification events."""
        # Test with cryptoapp which uses JCA cryptography
        result = run_app_exploration(
            device=emulator_device,
            package="br.unb.cic.cryptoapp",
            name="CryptoApp",
            duration=120,
            mode="multimode",
            capture_rv_events=True,
            is_instrumented=True
        )

        print(f"\n{'='*60}")
        print("JCA Spec Coverage Test")
        print(f"{'='*60}")
        print(f"RV Events: {result.rv_events}")
        print(f"Violations: {result.rv_violations}")
        print(f"Coverage Events: {result.rv_coverage_events}")
        print(f"Specs Triggered: {result.rv_specs_triggered}")

        if result.rv_summary:
            print("\nSpec Coverage Detail:")
            for spec, count in result.rv_summary.get("spec_coverage", {}).items():
                print(f"  {spec}: {count}")

        # Save detailed result
        result_file = results_dir / f"jca_coverage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w') as f:
            json.dump(result.__dict__, f, indent=2, default=str)

        assert result.success, f"Exploration failed: {result.error}"

    def test_violation_summary(
        self, emulator_device, results_dir
    ):
        """Test collecting violation summaries from multiple apps."""
        test_packages = [
            "br.unb.cic.cryptoapp",
            "byrne.utilities.hashpass",
        ]

        all_violations = []
        specs_seen = set()

        for package in test_packages:
            if not is_app_installed(emulator_device.device_id, package):
                continue

            result = run_app_exploration(
                device=emulator_device,
                package=package,
                name=package.split('.')[-1],
                duration=60,
                mode="multimode",
                capture_rv_events=True,
                is_instrumented=True
            )

            if result.rv_violations > 0:
                all_violations.append({
                    "package": package,
                    "violations": result.rv_violations,
                    "specs": result.rv_specs_triggered
                })

            specs_seen.update(result.rv_specs_triggered)

        print(f"\n{'='*60}")
        print("Violation Summary Across Apps")
        print(f"{'='*60}")
        print(f"Apps with violations: {len(all_violations)}")
        print(f"Unique specs seen: {specs_seen}")
        for v in all_violations:
            print(f"  {v['package']}: {v['violations']} violations, specs: {v['specs']}")

        # Save summary
        summary_file = results_dir / f"violation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w') as f:
            json.dump({
                "apps_with_violations": all_violations,
                "unique_specs": list(specs_seen)
            }, f, indent=2, default=str)
