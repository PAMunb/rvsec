"""
Real Emulator Test - CryptoApp with V9 Agent.

Tests V9 agent controlling real Android emulator:
- Auto-detect running emulator
- Install APK via ADB
- Run RVAgent with configurable timeout
- Collect detailed metrics
- Compare with offline validation
"""

import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('test_real_emulator.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.rv_agent import RVAgent
from rv_agent.core.device_interface import DeviceInterface


# APK paths
APK_DIR = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
APK_CONFIGS = {
    "cryptoapp": {
        "apk_file": "cryptoapp.apk/cryptoapp.apk",
        "package_name": "br.unb.cic.cryptoapp"
    },
    "simplenotes": {
        "apk_file": "com.rafapps.simplenotes_7.apk",
        "package_name": "com.rafapps.simplenotes"
    }
}


def get_running_emulator() -> str:
    """
    Detect running emulator via adb devices.

    Returns:
        Device ID of running emulator (e.g., "emulator-5554")

    Raises:
        RuntimeError: If no emulator is running
    """
    logger.info("Detecting running emulator...")

    try:
        result = subprocess.run(
            ['adb', 'devices'],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse output for emulator-XXXX
        for line in result.stdout.split('\n'):
            if line.startswith('emulator-') and 'device' in line:
                device_id = line.split()[0]
                logger.info(f"✅ Found emulator: {device_id}")
                return device_id

        raise RuntimeError("No emulator found running")

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ADB command failed: {e}")
    except FileNotFoundError:
        raise RuntimeError("ADB not found in PATH. Install Android SDK Platform Tools.")


def install_apk(device_id: str, apk_path: Path) -> bool:
    """
    Install APK on emulator.

    Args:
        device_id: Emulator device ID
        apk_path: Path to APK file

    Returns:
        True if installed successfully
    """
    if not apk_path.exists():
        logger.error(f"APK not found: {apk_path}")
        return False

    logger.info(f"Installing {apk_path.name} on {device_id}...")

    try:
        result = subprocess.run(
            ['adb', '-s', device_id, 'install', '-r', str(apk_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            logger.info("✅ APK installed successfully")
            return True
        else:
            logger.warning(f"Install output: {result.stdout}")
            logger.warning(f"Install error: {result.stderr}")
            # Sometimes install "fails" but actually succeeds (already installed)
            if "Success" in result.stdout or "already installed" in result.stderr.lower():
                logger.info("✅ APK already installed (using existing)")
                return True
            return False

    except subprocess.TimeoutExpired:
        logger.error("APK installation timed out (60s)")
        return False
    except Exception as e:
        logger.error(f"Failed to install APK: {e}")
        return False


def run_agent_test(
    device_id: str,
    package_name: str,
    timeout: int = 120,
    static_data: Optional[Dict] = None
) -> Dict:
    """
    Run RVAgent on real device.

    Args:
        device_id: Emulator device ID
        package_name: App package name
        timeout: Execution timeout in seconds
        static_data: Optional static analysis data

    Returns:
        Results dictionary with metrics
    """
    logger.info("="*80)
    logger.info(f"🔬 REAL DEVICE TEST")
    logger.info("="*80)
    logger.info(f"   Device: {device_id}")
    logger.info(f"   Package: {package_name}")
    logger.info(f"   Timeout: {timeout}s")
    logger.info("")

    # Create config
    # ⚠️ CRITICAL: TIMEOUT IS THE ONLY CONTROL MECHANISM
    # max_iterations is IGNORED - execution stops ONLY when timeout is reached
    # Setting to 200 just to satisfy Pydantic validation (field requirement)
    # THE TIMEOUT PARAMETER CONTROLS EVERYTHING - NOT max_iterations!
    config = RVAgentConfig(
        package_name=package_name,
        device_id=device_id,
        strategy="dfs",  # Not used yet, but required in config
        timeout=timeout,  # ← THIS CONTROLS EXECUTION TIME (e.g., 120 seconds)
        max_iterations=200  # ← IGNORED! Just satisfies Pydantic. TIMEOUT controls execution!
    )

    # Create device interface (real device)
    logger.info("Connecting to device...")
    device = DeviceInterface(device_id)

    # Create agent
    logger.info("Creating RVAgent with V9 prompts...")
    agent = RVAgent(config, static_data=static_data, device=device)

    # Run test
    logger.info(f"Starting test (timeout: {timeout}s)...")
    logger.info("")

    start_time = time.time()
    results = agent.run()
    end_time = time.time()

    results['actual_execution_time_s'] = end_time - start_time
    results['test_type'] = 'real_device'
    results['device_id'] = device_id
    results['timeout_requested'] = timeout

    logger.info("")
    logger.info("="*80)
    logger.info("✅ Test completed")
    logger.info("="*80)

    return results


def load_offline_results(app_name: str) -> Optional[Dict]:
    """
    Load offline validation results for comparison.

    Args:
        app_name: App identifier (e.g., "cryptoapp")

    Returns:
        Results dict or None if not found
    """
    # Try to find V9 validation results
    possible_files = [
        f"v9_validation_{app_name}.json",
        f"v9_validation_{APK_CONFIGS[app_name]['package_name'].replace('.', '_')}.json"
    ]

    for filename in possible_files:
        filepath = Path(filename)
        if filepath.exists():
            logger.info(f"Loading offline results: {filepath}")
            with open(filepath, 'r') as f:
                return json.load(f)

    logger.warning(f"No offline results found for {app_name}")
    return None


def analyze_results(results: Dict, offline_results: Optional[Dict] = None):
    """
    Analyze and print results with comparison.

    Args:
        results: Real device test results
        offline_results: Optional offline validation results for comparison
    """
    print("\n" + "="*80)
    print("📊 REAL DEVICE TEST RESULTS")
    print("="*80)

    # Basic info
    print(f"\n📱 Device: {results.get('device_id', 'unknown')}")
    print(f"📦 Package: {results.get('app_name', results.get('package_name', 'unknown'))}")
    print(f"🕐 Timeout: {results.get('timeout_requested', 'N/A')}s")

    # Execution metrics
    print(f"\n⏱️  Execution:")
    print(f"   Total time: {results['execution_time_s']:.1f}s")
    print(f"   Actual time: {results.get('actual_execution_time_s', 0):.1f}s")
    print(f"   Iterations: {results['total_iterations']}")

    # Exploration metrics
    exploration = results['exploration']
    print(f"\n🗺️  Exploration:")
    print(f"   Unique screens: {exploration['unique_screens']}")
    print(f"   Activities: {len(exploration['activities'])}")
    for i, activity in enumerate(exploration['activities'], 1):
        print(f"      {i}. {activity}")
    print(f"   Revisit rate: {exploration['revisit_rate']*100:.1f}%")

    # Actions
    actions = results['actions']
    print(f"\n🛠️  Actions Executed:")
    actions_by_type = actions['by_type']
    for action_type, count in sorted(actions_by_type.items(), key=lambda x: x[1], reverse=True):
        print(f"   {action_type}: {count}")

    print(f"\n✅ Valid: {actions['valid']} ({actions['valid_rate']*100:.1f}%)")
    print(f"❌ Invalid: {actions['invalid']}")

    # Device actions (if available)
    if 'device_actions' in results:
        device = results['device_actions']
        print(f"\n📲 Device Actions:")
        print(f"   Total: {device['total_actions']}")
        print(f"   Valid: {device['valid_actions']} ({device['valid_rate']*100:.1f}%)")
        print(f"   Invalid: {device['invalid_actions']}")

        print(f"\n   By type:")
        for action_type, count in sorted(device['action_types'].items(), key=lambda x: x[1], reverse=True):
            print(f"      {action_type}: {count}")

    # LLM usage
    llm = results['llm']
    print(f"\n🤖 LLM Usage:")
    print(f"   Total tokens: {llm['total_tokens']:,}")
    print(f"   Input tokens: {llm['input_tokens']:,}")
    print(f"   Output tokens: {llm['output_tokens']:,}")
    print(f"   Avg per iteration: {llm['avg_tokens_per_iteration']:.0f} tokens")
    print(f"   Total time: {llm['total_time_ms']/1000:.1f}s")
    print(f"   Avg time/iteration: {llm['avg_time_per_iteration_ms']:.0f}ms")

    # Comparison with offline if available
    if offline_results:
        print(f"\n" + "="*80)
        print("📊 COMPARISON: Real vs Offline")
        print("="*80)

        off_exp = offline_results['exploration']
        off_actions = offline_results['actions']
        off_llm = offline_results['llm']
        off_device = offline_results.get('device_actions', {})

        print(f"\n{'Metric':<30} {'Real':<15} {'Offline':<15} {'Diff':>10}")
        print("-"*70)

        # Iterations
        real_iter = results['total_iterations']
        off_iter = offline_results['total_iterations']
        diff = real_iter - off_iter
        print(f"{'Iterations':<30} {real_iter:<15} {off_iter:<15} {diff:+>10}")

        # Unique screens
        real_screens = exploration['unique_screens']
        off_screens = off_exp['unique_screens']
        diff = real_screens - off_screens
        print(f"{'Unique screens':<30} {real_screens:<15} {off_screens:<15} {diff:+>10}")

        # Valid rate
        real_valid = actions['valid_rate']*100
        off_valid = off_actions['valid_rate']*100
        diff = real_valid - off_valid
        print(f"{'Valid rate (%)':<30} {real_valid:<15.1f} {off_valid:<15.1f} {diff:+>10.1f}")

        # TYPE_TEXT usage
        real_type_text = actions_by_type.get('TYPE_TEXT', 0)
        off_type_text = off_actions['by_type'].get('TYPE_TEXT', 0)
        diff = real_type_text - off_type_text
        print(f"{'TYPE_TEXT actions':<30} {real_type_text:<15} {off_type_text:<15} {diff:+>10}")

        # Device action success (if available)
        if 'device_actions' in results and off_device:
            real_dev_rate = device['valid_rate']*100
            off_dev_rate = off_device['valid_rate']*100
            diff = real_dev_rate - off_dev_rate
            print(f"{'Device success rate (%)':<30} {real_dev_rate:<15.1f} {off_dev_rate:<15.1f} {diff:+>10.1f}")

        # Tokens per iteration
        real_tpi = llm['avg_tokens_per_iteration']
        off_tpi = off_llm['avg_tokens_per_iteration']
        diff = real_tpi - off_tpi
        print(f"{'Tokens/iteration':<30} {real_tpi:<15.0f} {off_tpi:<15.0f} {diff:+>10.0f}")

        # Time per iteration
        real_time = llm['avg_time_per_iteration_ms']
        off_time = off_llm['avg_time_per_iteration_ms']
        diff = real_time - off_time
        print(f"{'Time/iteration (ms)':<30} {real_time:<15.0f} {off_time:<15.0f} {diff:+>10.0f}")

    print("\n" + "="*80)


def main():
    """Main test execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Real emulator test for RVAgent")
    parser.add_argument(
        '--app',
        choices=list(APK_CONFIGS.keys()),
        default='cryptoapp',
        help='App to test (default: cryptoapp)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=120,
        help='Execution timeout in seconds (default: 120)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output JSON file path (default: real_test_{app}.json)'
    )

    args = parser.parse_args()

    # Get app config
    app_config = APK_CONFIGS[args.app]
    apk_path = APK_DIR / app_config['apk_file']
    package_name = app_config['package_name']

    # Set default output path
    output_path = args.output or f"real_test_{args.app}.json"

    logger.info("="*80)
    logger.info("🚀 REAL EMULATOR TEST - V9 AGENT")
    logger.info("="*80)
    logger.info(f"   App: {args.app}")
    logger.info(f"   APK: {apk_path}")
    logger.info(f"   Package: {package_name}")
    logger.info(f"   Timeout: {args.timeout}s")
    logger.info(f"   Output: {output_path}")
    logger.info("")

    try:
        # Step 1: Detect emulator
        device_id = get_running_emulator()

        # Step 2: Install APK
        if not install_apk(device_id, apk_path):
            logger.error("Failed to install APK. Aborting test.")
            return False

        logger.info("")

        # Step 3: Run test
        results = run_agent_test(
            device_id=device_id,
            package_name=package_name,
            timeout=args.timeout
        )

        # Step 4: Save results
        logger.info(f"Saving results to {output_path}...")
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"✅ Results saved")

        # Step 5: Load offline results for comparison
        offline_results = load_offline_results(args.app)

        # Step 6: Analyze and display
        analyze_results(results, offline_results)

        logger.info(f"\n✅ Test completed successfully")
        logger.info(f"📄 Results: {output_path}")
        logger.info(f"📋 Log: test_real_emulator.log")

        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
