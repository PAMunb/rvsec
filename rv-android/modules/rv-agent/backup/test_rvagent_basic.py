"""
RVAgent Basic Test - Critical Evaluation Run

Tests RVAgent with cryptoapp using enhanced logging for critical evaluation.
"""

import logging
import sys
import subprocess
from pathlib import Path

from rv_agent.core.rv_agent import RVAgent
from rv_agent.config.agent_config import RVAgentConfig


def verify_ollama_model():
    """
    Verify that qwen-vision-tools-v1 custom model exists in Ollama.

    Returns:
        bool: True if model exists, False otherwise
    """
    try:
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            # Check if qwen-vision-tools-v1 is in the output
            if 'qwen-vision-tools-v1' in result.stdout:
                return True
            else:
                print("❌ Custom model 'qwen-vision-tools-v1' not found in Ollama")
                print("\n📝 To create the model, run:")
                print("   cd modules/rv-agent")
                print("   ollama create qwen-vision-tools-v1 -f Modelfile.qwen-vision-tools-v1")
                print("\n   The Modelfile enables tool calling for qwen2.5-vl:7b vision model")
                return False
        else:
            print(f"⚠️  Failed to check Ollama models: {result.stderr}")
            return False

    except FileNotFoundError:
        print("❌ Ollama CLI not found. Is Ollama installed?")
        return False
    except subprocess.TimeoutExpired:
        print("⚠️  Ollama check timed out")
        return False
    except Exception as e:
        print(f"⚠️  Error checking Ollama: {e}")
        return False


def setup_logging():
    """Configure comprehensive logging for evaluation."""

    # Create logs directory
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Console handler with emoji-rich format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)

    # File handler with detailed format
    file_handler = logging.FileHandler(log_dir / 'rvagent_test.log', mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)

    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    print(f"\n📋 Logging configured:")
    print(f"   Console: INFO level with emoji indicators")
    print(f"   File: {log_dir / 'rvagent_test.log'} (DEBUG level)")
    print()


def run_test():
    """Run RVAgent test with cryptoapp."""

    print("="*80)
    print("🤖 RVAgent - Critical Evaluation Test")
    print("="*80)
    print()

    # Verify custom model exists
    print("🔍 Verifying Ollama model...")
    if not verify_ollama_model():
        print("\n❌ Cannot proceed without qwen-vision-tools-v1 model")
        return None
    print("✅ Model verified: qwen-vision-tools-v1")
    print()

    # Configuration
    # NOTE: llm_model in config is ignored - rv_agent.py uses qwen-vision-tools-v1 directly
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        device_id="emulator-5554",
        timeout=120,  # 2 minutes for initial test
        strategy="dfs",
        device_dimensions=(1080, 1920),
        optimized_dimensions=(728, 1288),
        llm_model="qwen-vision-tools-v1",  # Custom modelfile with tool support
        llm_temperature=0.25,
        llm_top_p=0.8,
        llm_top_k=50
    )

    print("📝 Configuration:")
    print(f"   Package: {config.package_name}")
    print(f"   Device: {config.device_id}")
    print(f"   Timeout: {config.timeout}s")
    print(f"   Strategy: {config.strategy}")
    print(f"   LLM: qwen-vision-tools-v1 (custom modelfile)")
    print(f"   Base Model: qwen2.5-vl:7b (98.3% success rate)")
    print(f"   Temperature: {config.llm_temperature}")
    print(f"   Coordinate Conversion: {config.device_dimensions} → {config.optimized_dimensions}")
    print()

    # Validate configuration
    is_valid, error_msg = config.validate()
    if not is_valid:
        print(f"❌ Configuration validation failed: {error_msg}")
        return None

    print("✅ Configuration validated")
    print()

    try:
        # Create agent
        print("🔧 Initializing RVAgent...")
        agent = RVAgent(config=config, static_data=None)
        print("✅ Agent initialized")
        print()

        # Run exploration
        print("🚀 Starting autonomous exploration...")
        print("="*80)
        print()

        metrics = agent.run()

        print()
        print("="*80)
        print("🏁 Exploration completed!")
        print("="*80)
        print()

        # Display results
        print("📊 RESULTS:")
        print(f"   Status: {metrics.get('status', 'unknown')}")
        print(f"   Execution time: {metrics.get('execution_time_s', 0):.1f}s")

        if metrics.get('status') == 'error':
            print(f"   Error: {metrics.get('error', 'Unknown error')}")
        else:
            print(f"   Total iterations: {metrics.get('total_iterations', 0)}")
            print(f"   Unique screens: {metrics.get('unique_screens', 0)}")
            print(f"   Unique activities: {metrics.get('unique_activities', 0)}")
            print(f"   Transitions: {metrics.get('transitions', 0)}")
            print(f"   Average coverage: {metrics.get('avg_screen_coverage_%', 0):.1f}%")
        print()

        # Per-screen breakdown
        if metrics.get('screen_metrics'):
            print("📈 PER-SCREEN COVERAGE:")
            for screen_hash, screen_data in list(metrics['screen_metrics'].items())[:5]:
                print(f"   {screen_hash[:8]}... ({screen_data['activity']}):")
                print(f"      Visits: {screen_data['visit_count']}")
                print(f"      Actions: {screen_data['actions_executed']}/{screen_data['total_actions']}")
                print(f"      Coverage: {screen_data['coverage_%']:.1f}%")

            if len(metrics['screen_metrics']) > 5:
                print(f"   ... and {len(metrics['screen_metrics']) - 5} more screens")
        print()

        # Cleanup
        agent.cleanup()

        return metrics

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point."""
    setup_logging()

    print("Starting test in 3 seconds...")
    import time
    time.sleep(3)

    metrics = run_test()

    if metrics:
        print("\n✅ Test completed successfully!")
        print(f"\n📁 Detailed logs available at: ./logs/rvagent_test.log")
        return 0
    else:
        print("\n❌ Test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
