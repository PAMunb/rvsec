"""
Test qwen3-vl with Real APKs - 10 Apps x 2min

Descobre automaticamente APKs disponíveis e testa 10 deles
para comparar com baseline e detectar se problemas persistem.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

APK_BASE_DIR = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
TIMEOUT_PER_APP = 120  # 2 minutes per app
MAX_APPS = 10


# ============================================================================
# APK DISCOVERY
# ============================================================================

def discover_apks() -> List[Dict]:
    """Auto-discover available APKs"""
    logger.info("🔍 Discovering available APKs...")

    apks = []
    for apk_dir in sorted(APK_BASE_DIR.glob("*.apk")):
        if not apk_dir.is_dir():
            continue

        # Extract package name (directory name without version)
        dir_name = apk_dir.name
        package = dir_name.rsplit('_', 1)[0]  # Remove version suffix

        # Find APK file inside directory
        apk_files = list(apk_dir.glob("*.apk"))
        if not apk_files:
            continue

        apk_path = apk_files[0]

        apks.append({
            "name": package.split('.')[-1],  # Short name
            "package": package,
            "apk_path": str(apk_path),
            "dir": str(apk_dir)
        })

    logger.info(f"✅ Found {len(apks)} APKs")
    return apks


# ============================================================================
# DEVICE MANAGEMENT
# ============================================================================

def get_connected_device() -> Optional[str]:
    """Get first connected Android device"""
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            check=True
        )

        lines = result.stdout.strip().split('\n')[1:]
        for line in lines:
            if '\tdevice' in line:
                device_id = line.split('\t')[0]
                logger.info(f"✅ Found device: {device_id}")
                return device_id

        logger.error("❌ No device connected")
        return None

    except Exception as e:
        logger.error(f"❌ Error detecting device: {e}")
        return None


def install_apk(device_id: str, apk_path: str) -> bool:
    """Install APK on device"""
    try:
        logger.info(f"📦 Installing {Path(apk_path).name}...")
        result = subprocess.run(
            ["adb", "-s", device_id, "install", "-r", apk_path],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0 or "Success" in result.stdout:
            logger.info(f"✅ APK installed")
            return True
        else:
            logger.error(f"❌ Installation failed: {result.stdout}")
            return False

    except Exception as e:
        logger.error(f"❌ Installation error: {e}")
        return False


def uninstall_app(device_id: str, package: str):
    """Uninstall app from device"""
    try:
        logger.info(f"🗑️  Uninstalling {package}...")
        subprocess.run(
            ["adb", "-s", device_id, "uninstall", package],
            capture_output=True,
            timeout=30
        )
        logger.info("✅ App uninstalled")
    except Exception as e:
        logger.warning(f"⚠️  Uninstall warning: {e}")


# ============================================================================
# TEST EXECUTION
# ============================================================================

def run_rvagent_test(device_id: str, app_config: Dict, timeout: int) -> Dict:
    """
    Run RVAgent test on single app with qwen3-vl
    """
    sys.path.insert(0, str(Path(__file__).parent / "src"))

    from rv_agent.core.rv_agent import RVAgent
    from rv_agent.core.device_interface import DeviceInterface
    from rv_agent.config.agent_config import RVAgentConfig

    logger.info(f"\n{'='*80}")
    logger.info(f"🧪 TESTING: {app_config['name'].upper()}")
    logger.info(f"{'='*80}")
    logger.info(f"   Package: {app_config['package']}")
    logger.info(f"   Timeout: {timeout}s")
    logger.info(f"   Model: qwen3-vl:4b")

    start_time = time.time()

    try:
        # Create device interface (connects automatically)
        device = DeviceInterface(device_id)

        # Create config with qwen3-vl model
        config = RVAgentConfig(
            package_name=app_config['package'],
            device_id=device_id,
            strategy="dfs",
            timeout=timeout,
            max_iterations=200,
            llm_model="qwen3-vl:4b"  # Use qwen3-vl instead of default qwen2.5vl
        )

        # Create RVAgent with config and device
        agent = RVAgent(config, static_data=None, device=device)

        # Run exploration
        logger.info(f"🚀 Starting exploration...")
        results = agent.run()

        execution_time = time.time() - start_time

        # agent.run() returns results dict with metrics
        metrics = results.copy()
        metrics.update({
            "app_name": app_config['name'],
            "package": app_config['package'],
            "model": "qwen3-vl:4b",
            "timeout_requested": timeout,
            "actual_execution_time_s": execution_time,
        })

        logger.info(f"\n📊 Results:")
        logger.info(f"   Iterations: {metrics['iterations']}")
        logger.info(f"   Unique States: {metrics['unique_states']}")
        logger.info(f"   Transitions: {metrics['total_transitions']}")
        logger.info(f"   Loop: {'YES ❌' if metrics['potential_loop'] else 'NO ✅'}")

        return metrics

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return {
            "app_name": app_config['name'],
            "package": app_config['package'],
            "status": "failed",
            "error": str(e),
            "execution_time_s": time.time() - start_time,
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run 10-app test with qwen3-vl"""

    print("\n" + "="*80)
    print("  QWEN3-VL REAL TEST: 10 APPS x 2 MINUTES")
    print("="*80)
    print(f"\n📍 APK Directory: {APK_BASE_DIR}")
    print(f"⏱️  Timeout per app: {TIMEOUT_PER_APP}s")
    print(f"🤖 Model: qwen3-vl:4b + LangGraph ToolNode")
    print(f"📊 Total time: ~{MAX_APPS * TIMEOUT_PER_APP / 60:.0f} minutes")

    # Discover APKs
    all_apks = discover_apks()
    if not all_apks:
        logger.error("❌ No APKs found!")
        return

    # Select first 10
    apps_to_test = all_apks[:MAX_APPS]
    logger.info(f"\n✅ Selected {len(apps_to_test)} apps for testing")

    # Detect device
    device_id = get_connected_device()
    if not device_id:
        logger.error("❌ No device found!")
        return

    # Run tests
    results = []
    for i, app in enumerate(apps_to_test, 1):
        logger.info(f"\n{'🔵'*40}")
        logger.info(f"  APP {i}/{len(apps_to_test)}: {app['name'].upper()}")
        logger.info(f"{'🔵'*40}")

        # Install
        if not install_apk(device_id, app['apk_path']):
            logger.error(f"❌ Skipping - installation failed")
            continue

        # Test
        result = run_rvagent_test(device_id, app, TIMEOUT_PER_APP)
        results.append(result)

        # Uninstall
        uninstall_app(device_id, app['package'])

        # Save intermediate results
        output_file = Path("qwen3vl_10apps_results.json")
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"💾 Results saved: {output_file}")

    # Summary
    print("\n" + "="*80)
    print("  SUMMARY")
    print("="*80)

    completed = [r for r in results if r['status'] == 'completed']
    failed = [r for r in results if r['status'] == 'failed']

    print(f"\n📊 Statistics:")
    print(f"   ✅ Completed: {len(completed)}/{len(results)}")
    print(f"   ❌ Failed: {len(failed)}/{len(results)}")

    if completed:
        avg_its = sum(r['iterations'] for r in completed) / len(completed)
        avg_states = sum(r['unique_states'] for r in completed) / len(completed)
        avg_trans = sum(r['total_transitions'] for r in completed) / len(completed)
        loops = sum(1 for r in completed if r.get('potential_loop', False))

        print(f"\n📈 Averages:")
        print(f"   Iterations: {avg_its:.1f}")
        print(f"   Unique States: {avg_states:.1f}")
        print(f"   Transitions: {avg_trans:.1f}")
        print(f"   Apps with loops: {loops}/{len(completed)}")

        print(f"\n📋 Per-App:")
        for r in completed:
            loop = "🔴" if r.get('potential_loop', False) else "✅"
            print(f"   {r['app_name']:20s}: {r['iterations']:3d} its, "
                  f"{r['unique_states']:3d} states, "
                  f"{r['total_transitions']:3d} trans  {loop}")

    # Comparison
    print("\n" + "="*80)
    print("  COMPARISON: Qwen2.5-Coder vs qwen3-vl")
    print("="*80)
    print("\nBaseline (Qwen2.5-Coder, CryptoApp, 120s):")
    print("   Iterations: 22")
    print("   Unique States: 0  ❌")
    print("   Transitions: 0  ❌")
    print("   Loop: YES  ❌")

    if completed:
        print(f"\nQwen3-VL Average ({len(completed)} apps, 120s):")
        print(f"   Iterations: {avg_its:.1f}")
        print(f"   Unique States: {avg_states:.1f}")
        print(f"   Transitions: {avg_trans:.1f}")
        print(f"   Loops: {loops}/{len(completed)}")

        if avg_states > 0:
            print("\n✅ IMPROVEMENT! Qwen3-VL discovers unique states!")
        else:
            print("\n❌ SAME PROBLEM! Loops persist")

    print("\n" + "="*80)
    print(f"💾 Full results: qwen3vl_10apps_results.json")
    print("="*80)


if __name__ == "__main__":
    main()
