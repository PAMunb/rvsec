"""
Test qwen3-vl with ToolNode on Multiple Apps

Real-world test to see if loop problems persist or new issues emerge
when using qwen3-vl:4b with native ToolNode.

Test Plan:
- 10 different apps
- 120s timeout each
- Collect metrics: iterations, unique_states, transitions, loops
- Compare with baseline (Qwen2.5-Coder results)
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# APP CONFIGURATION
# ============================================================================

APPS_TO_TEST = [
    {
        "name": "cryptoapp",
        "apk_path": "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/cryptoapp.apk",
        "package": "br.unb.cic.cryptoapp",
        "expected_features": ["MESSAGE DIGEST", "CIPHER", "GENERATED"],
    },
    {
        "name": "calculator",
        "apk_path": "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/calculator.apk/calculator.apk",
        "package": "com.example.calculator",
        "expected_features": ["numbers", "operators", "equals"],
    },
    {
        "name": "notepad",
        "apk_path": "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/notepad.apk/notepad.apk",
        "package": "com.example.notepad",
        "expected_features": ["new note", "save", "list"],
    },
    {
        "name": "todo",
        "apk_path": "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/todo.apk/todo.apk",
        "package": "com.example.todo",
        "expected_features": ["add task", "complete", "delete"],
    },
    {
        "name": "weather",
        "apk_path": "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/weather.apk/weather.apk",
        "package": "com.example.weather",
        "expected_features": ["search city", "forecast", "settings"],
    },
    {
        "name": "contacts",
        "apk_path": "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/contacts.apk/contacts.apk",
        "package": "com.example.contacts",
        "expected_features": ["add contact", "call", "message"],
    },
    {
        "name": "gallery",
        "apk_path": "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/gallery.apk/gallery.apk",
        "package": "com.example.gallery",
        "expected_features": ["view photos", "slideshow", "share"],
    },
    {
        "name": "music",
        "apk_path": "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/music.apk/music.apk",
        "package": "com.example.music",
        "expected_features": ["play", "pause", "playlist"],
    },
    {
        "name": "settings",
        "apk_path": "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/settings.apk/settings.apk",
        "package": "com.android.settings",
        "expected_features": ["wifi", "bluetooth", "display"],
    },
    {
        "name": "browser",
        "apk_path": "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/browser.apk/browser.apk",
        "package": "com.android.browser",
        "expected_features": ["url bar", "bookmarks", "tabs"],
    },
]

TIMEOUT_PER_APP = 120  # seconds


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

        lines = result.stdout.strip().split('\n')[1:]  # Skip header
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
        logger.info(f"Installing {Path(apk_path).name}...")
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
        logger.info(f"Uninstalling {package}...")
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
    Run RVAgent test on single app

    Uses current rv_agent.py with qwen3-vl + ToolNode
    """
    from rv_agent.core.rv_agent import RVAgent
    from rv_agent.device_interface import DeviceInterface
    from rv_android_core.domain.static import StaticAnalysisData

    logger.info(f"\n{'='*80}")
    logger.info(f"🧪 TESTING: {app_config['name'].upper()}")
    logger.info(f"{'='*80}")
    logger.info(f"   Package: {app_config['package']}")
    logger.info(f"   Timeout: {timeout}s")
    logger.info(f"   Model: qwen3-vl:4b")
    logger.info(f"   Framework: LangGraph + ToolNode")

    start_time = time.time()

    try:
        # Create device interface
        device = DeviceInterface(device_id)
        device.connect()

        # Create RVAgent with qwen3-vl
        agent = RVAgent(
            device=device,
            package_name=app_config['package'],
            static_analysis=StaticAnalysisData(
                package_name=app_config['package'],
                activities=[],
                intents=[],
                permissions=[]
            ),
            strategy_name="dfs",
            model_name="qwen3-vl:4b",  # Use validated vision model
            temperature=0.0,
        )

        # Run exploration
        logger.info(f"\n🚀 Starting exploration...")
        agent.run(timeout=timeout)

        execution_time = time.time() - start_time

        # Collect metrics
        metrics = {
            "app_name": app_config['name'],
            "package": app_config['package'],
            "status": "completed",
            "model": "qwen3-vl:4b",
            "timeout_requested": timeout,
            "execution_time_s": execution_time,
            "iterations": len(agent.memory.long_term.states),
            "unique_states": len(agent.memory.long_term.state_hashes),
            "total_transitions": len(agent.memory.long_term.transitions),
            "actions_executed": len(agent.memory.long_term.executed_actions),
        }

        # Detect loops
        if metrics['iterations'] > 0:
            # Simple loop detection: many iterations with few unique states
            loop_ratio = metrics['iterations'] / max(metrics['unique_states'], 1)
            metrics['potential_loop'] = loop_ratio > 5.0
            metrics['loop_ratio'] = loop_ratio
        else:
            metrics['potential_loop'] = False
            metrics['loop_ratio'] = 0.0

        logger.info(f"\n📊 Test Results:")
        logger.info(f"   Iterations: {metrics['iterations']}")
        logger.info(f"   Unique States: {metrics['unique_states']}")
        logger.info(f"   Transitions: {metrics['total_transitions']}")
        logger.info(f"   Actions: {metrics['actions_executed']}")
        logger.info(f"   Loop Detected: {metrics['potential_loop']}")

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
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run multi-app test with qwen3-vl"""

    print("\n" + "="*80)
    print("  QWEN3-VL MULTI-APP REAL DEVICE TEST")
    print("="*80)
    print(f"\nModel: qwen3-vl:4b")
    print(f"Framework: LangGraph + ToolNode")
    print(f"Apps: {len(APPS_TO_TEST)}")
    print(f"Timeout per app: {TIMEOUT_PER_APP}s")
    print(f"Total estimated time: {len(APPS_TO_TEST) * TIMEOUT_PER_APP / 60:.1f} minutes")

    # Detect device
    device_id = get_connected_device()
    if not device_id:
        logger.error("❌ No device found. Please connect an emulator or device.")
        return

    # Filter apps that exist
    available_apps = []
    for app in APPS_TO_TEST:
        if Path(app['apk_path']).exists():
            available_apps.append(app)
            logger.info(f"✅ Found APK: {app['name']}")
        else:
            logger.warning(f"⚠️  APK not found: {app['name']} - {app['apk_path']}")

    if not available_apps:
        logger.error("❌ No APKs found. Please check paths.")
        return

    logger.info(f"\n📱 Testing {len(available_apps)} apps...")

    # Run tests
    results = []
    for i, app in enumerate(available_apps, 1):
        logger.info(f"\n{'🔵'*40}")
        logger.info(f"  TEST {i}/{len(available_apps)}: {app['name'].upper()}")
        logger.info(f"{'🔵'*40}")

        # Install app
        if not install_apk(device_id, app['apk_path']):
            logger.error(f"❌ Skipping {app['name']} - installation failed")
            continue

        # Run test
        result = run_rvagent_test(device_id, app, TIMEOUT_PER_APP)
        results.append(result)

        # Uninstall app
        uninstall_app(device_id, app['package'])

        # Save intermediate results
        output_file = Path("qwen3vl_multiapp_results.json")
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"\n💾 Results saved to: {output_file}")

    # Generate summary
    print("\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)

    completed = [r for r in results if r['status'] == 'completed']
    failed = [r for r in results if r['status'] == 'failed']

    print(f"\n📊 Overall Statistics:")
    print(f"   Total apps tested: {len(results)}")
    print(f"   ✅ Completed: {len(completed)}")
    print(f"   ❌ Failed: {len(failed)}")

    if completed:
        avg_iterations = sum(r['iterations'] for r in completed) / len(completed)
        avg_unique_states = sum(r['unique_states'] for r in completed) / len(completed)
        avg_transitions = sum(r['total_transitions'] for r in completed) / len(completed)
        loops_detected = sum(1 for r in completed if r.get('potential_loop', False))

        print(f"\n📈 Average Metrics:")
        print(f"   Iterations: {avg_iterations:.1f}")
        print(f"   Unique States: {avg_unique_states:.1f}")
        print(f"   Transitions: {avg_transitions:.1f}")
        print(f"   Apps with loops: {loops_detected}/{len(completed)}")

        print(f"\n📋 Per-App Results:")
        for r in completed:
            loop_marker = "🔴 LOOP" if r.get('potential_loop', False) else "✅ OK"
            print(f"   {r['app_name']:15s}: {r['iterations']:3d} its, "
                  f"{r['unique_states']:3d} states, "
                  f"{r['total_transitions']:3d} trans  {loop_marker}")

    print("\n" + "="*80)
    print("  TEST COMPLETE")
    print("="*80)
    print(f"\n💾 Full results: qwen3vl_multiapp_results.json")

    # Compare with baseline
    print("\n" + "="*80)
    print("  COMPARISON WITH BASELINE (Qwen2.5-Coder)")
    print("="*80)
    print("\nBaseline CryptoApp (120s):")
    print("   Iterations: 22")
    print("   Unique States: 0  ❌")
    print("   Transitions: 0  ❌")
    print("   Loop: YES  ❌")

    if completed:
        crypto_result = next((r for r in completed if r['app_name'] == 'cryptoapp'), None)
        if crypto_result:
            print("\nQwen3-VL CryptoApp (120s):")
            print(f"   Iterations: {crypto_result['iterations']}")
            print(f"   Unique States: {crypto_result['unique_states']}")
            print(f"   Transitions: {crypto_result['total_transitions']}")
            loop_status = "YES ❌" if crypto_result.get('potential_loop', False) else "NO ✅"
            print(f"   Loop: {loop_status}")

            if crypto_result['unique_states'] > 0:
                print("\n✅ IMPROVEMENT! Qwen3-VL discovered unique states!")
            else:
                print("\n❌ SAME PROBLEM! Loop persists with qwen3-vl")


if __name__ == "__main__":
    main()
