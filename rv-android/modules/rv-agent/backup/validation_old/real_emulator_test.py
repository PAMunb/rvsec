#!/usr/bin/env python3
"""
Real Emulator Validation Test for RVAgent.

Tests the complete RVAgent system with real Android emulator using the cryptoapp.apk.
Based on coordinate validation discoveries and successful prototype validation.
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add rv-agent to path
rv_agent_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, rv_agent_path)

from rv_agent.core.rv_agent import RVAgent
from rv_agent.config.agent_config import RVAgentConfig


class RealEmulatorValidator:
    """
    Real emulator validation using complete RVAgent system.

    Tests the integrated system with cryptoapp.apk on real Android emulator,
    validating that coordinate validation discoveries work in practice.
    """

    def __init__(self, model_name: str = "PetrosStav/gemma3-tools:4b"):
        """Initialize validator with tested model."""
        self.model_name = model_name
        self.test_results = []

        print(f"🤖 REAL EMULATOR VALIDATION TEST")
        print(f"=" * 60)
        print(f"Model: {model_name}")
        print(f"Target App: br.unb.cic.cryptoapp")
        print(f"Validation: Real emulator with LLM+Tools")
        print(f"=" * 60)

    def validate_cryptoapp_autonomous(self, timeout_seconds: int = 120) -> Dict[str, Any]:
        """
        Run autonomous validation test with cryptoapp.

        Args:
            timeout_seconds: Maximum test duration

        Returns:
            Test results summary
        """
        print(f"🚀 Starting autonomous CryptoApp validation...")
        print(f"⏱️ Timeout: {timeout_seconds} seconds")

        test_start = time.time()

        try:
            # Initialize RVAgent with validated model
            print(f"🔧 Initializing RVAgent...")
            agent = RVAgent(timeout=timeout_seconds)

            # Connect to emulator
            print(f"📱 Connecting to Android emulator...")
            connected = agent.connect_to_device()
            if not connected:
                return {
                    "success": False,
                    "error": "Failed to connect to Android emulator",
                    "duration": time.time() - test_start
                }

            print(f"✅ Connected to emulator successfully")

            # Start testing session for cryptoapp
            print(f"🎯 Starting testing session for cryptoapp...")
            session_started = agent.start_testing_session(
                package_name="br.unb.cic.cryptoapp",
                objective="Test all cryptographic functions systematically"
            )

            if not session_started:
                return {
                    "success": False,
                    "error": "Failed to start testing session",
                    "duration": time.time() - test_start
                }

            print(f"✅ Testing session started")

            # Run autonomous exploration
            print(f"🔄 Running autonomous exploration...")
            exploration_results = agent.run_autonomous_exploration(timeout=timeout_seconds)

            test_duration = time.time() - test_start

            # Stop session
            agent.stop_session()

            print(f"✅ Autonomous exploration completed in {test_duration:.1f}s")

            # Analyze results
            analysis = self._analyze_exploration_results(exploration_results, test_duration)

            return {
                "success": True,
                "model": self.model_name,
                "duration": test_duration,
                "exploration_results": exploration_results,
                "analysis": analysis
            }

        except Exception as e:
            test_duration = time.time() - test_start
            print(f"❌ Validation failed: {e}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": str(e),
                "duration": test_duration
            }

    def _analyze_exploration_results(self, results: Dict[str, Any], duration: float) -> Dict[str, Any]:
        """Analyze exploration results and extract key metrics."""
        try:
            session_info = results.get("session", {})

            analysis = {
                "test_type": "real_emulator_autonomous",
                "model_performance": {
                    "total_iterations": session_info.get("iterations", 0),
                    "successful_actions": session_info.get("success_count", 0),
                    "error_count": session_info.get("error_count", 0),
                    "success_rate": session_info.get("success_rate", 0.0),
                    "duration_seconds": duration
                },
                "coverage_analysis": {
                    "unique_elements_tested": results.get("total_unique_elements_tested", 0),
                    "total_interactions": results.get("total_interactions", 0),
                    "coverage_efficiency": results.get("coverage_efficiency", 0.0)
                },
                "component_performance": {
                    "react_engine": results.get("react_engine", {}),
                    "ui_coverage": results.get("ui_coverage", {}),
                    "memory_stats": {
                        "short_term": results.get("short_term_memory", {}),
                        "long_term": results.get("long_term_memory", {})
                    }
                }
            }

            # Determine test outcome
            if session_info.get("success_rate", 0) >= 0.5:  # 50%+ success rate
                analysis["outcome"] = "SUCCESSFUL"
                analysis["outcome_reason"] = f"Achieved {session_info.get('success_rate', 0):.1%} success rate"
            elif session_info.get("iterations", 0) >= 5:  # Completed significant work
                analysis["outcome"] = "PARTIALLY_SUCCESSFUL"
                analysis["outcome_reason"] = f"Completed {session_info.get('iterations', 0)} iterations"
            else:
                analysis["outcome"] = "FAILED"
                analysis["outcome_reason"] = "Insufficient successful interactions"

            return analysis

        except Exception as e:
            return {
                "analysis_error": str(e),
                "outcome": "ANALYSIS_FAILED"
            }

    def run_validation_suite(self) -> Dict[str, Any]:
        """
        Run complete validation suite.

        Returns:
            Complete validation results
        """
        print(f"🧪 Starting RVAgent Real Emulator Validation Suite")
        validation_start = time.time()

        # Test 1: Short initial test (60 seconds)
        print(f"\n📋 Test 1: Short Initial Test (60s)")
        test1_results = self.validate_cryptoapp_autonomous(timeout_seconds=60)

        # Test 2: Medium test if first succeeds (120 seconds)
        print(f"\n📋 Test 2: Medium Test (120s)")
        test2_results = self.validate_cryptoapp_autonomous(timeout_seconds=120)

        validation_duration = time.time() - validation_start

        # Compile suite results
        suite_results = {
            "timestamp": datetime.now().isoformat(),
            "model": self.model_name,
            "validation_type": "real_emulator_suite",
            "total_duration": validation_duration,
            "tests": {
                "short_run": test1_results,
                "medium_run": test2_results
            },
            "summary": self._generate_suite_summary(test1_results, test2_results)
        }

        return suite_results

    def _generate_suite_summary(self, test1: Dict[str, Any], test2: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of validation suite."""

        # Extract key metrics
        test1_success = test1.get("success", False)
        test2_success = test2.get("success", False)

        test1_analysis = test1.get("analysis", {})
        test2_analysis = test2.get("analysis", {})

        summary = {
            "overall_success": test1_success and test2_success,
            "tests_passed": sum([test1_success, test2_success]),
            "tests_total": 2,
            "performance_comparison": {
                "short_run": {
                    "success_rate": test1_analysis.get("model_performance", {}).get("success_rate", 0),
                    "iterations": test1_analysis.get("model_performance", {}).get("total_iterations", 0),
                    "outcome": test1_analysis.get("outcome", "UNKNOWN")
                },
                "medium_run": {
                    "success_rate": test2_analysis.get("model_performance", {}).get("success_rate", 0),
                    "iterations": test2_analysis.get("model_performance", {}).get("total_iterations", 0),
                    "outcome": test2_analysis.get("outcome", "UNKNOWN")
                }
            }
        }

        # Determine overall assessment
        if summary["overall_success"]:
            summary["assessment"] = "RVAgent validation SUCCESSFUL - Ready for production testing"
        elif summary["tests_passed"] >= 1:
            summary["assessment"] = "RVAgent validation PARTIALLY SUCCESSFUL - Requires tuning"
        else:
            summary["assessment"] = "RVAgent validation FAILED - Major issues require resolution"

        return summary


def main():
    """Run real emulator validation test."""

    print(f"🔬 RVAgent Real Emulator Validation")
    print(f"Based on coordinate validation discoveries")
    print(f"Testing with complete system integration\n")

    # Check prerequisites
    print(f"📋 Checking prerequisites...")
    print(f"  ✓ Android emulator should be running")
    print(f"  ✓ cryptoapp.apk should be installed")
    print(f"  ✓ Ollama should be running with gemma3-tools")
    print(f"  ✓ ADB should be available")

    print(f"\nStarting validation automatically...")

    # Initialize validator
    validator = RealEmulatorValidator(model_name="PetrosStav/gemma3-tools:4b")

    # Run validation suite
    results = validator.run_validation_suite()

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"real_emulator_validation_results_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"\n" + "="*60)
    print(f"📊 REAL EMULATOR VALIDATION RESULTS")
    print(f"="*60)

    summary = results["summary"]
    print(f"📈 Overall Success: {'✅' if summary['overall_success'] else '❌'}")
    print(f"📝 Tests Passed: {summary['tests_passed']}/{summary['tests_total']}")
    print(f"⏱️ Total Duration: {results['total_duration']:.1f}s")

    print(f"\n🎯 Performance Comparison:")
    for test_name, perf in summary["performance_comparison"].items():
        print(f"  {test_name}:")
        print(f"    Success Rate: {perf['success_rate']:.1%}")
        print(f"    Iterations: {perf['iterations']}")
        print(f"    Outcome: {perf['outcome']}")

    # Detailed analysis for Phase 0 style reporting
    print(f"\n📊 DETAILED ANALYSIS:")
    print(f"  Short Run (60s):")
    if "short_run" in results["tests"] and results["tests"]["short_run"].get("exploration_results"):
        short_results = results["tests"]["short_run"]["exploration_results"]
        print(f"    Session Duration: {short_results.get('session', {}).get('duration', 0):.1f}s")
        print(f"    Total Interactions: {short_results.get('total_interactions', 0)}")
        print(f"    Unique Elements: {short_results.get('total_unique_elements_tested', 0)}")
        print(f"    Coverage Efficiency: {short_results.get('coverage_efficiency', 0):.2f}")

    print(f"  Medium Run (120s):")
    if "medium_run" in results["tests"] and results["tests"]["medium_run"].get("exploration_results"):
        medium_results = results["tests"]["medium_run"]["exploration_results"]
        print(f"    Session Duration: {medium_results.get('session', {}).get('duration', 0):.1f}s")
        print(f"    Total Interactions: {medium_results.get('total_interactions', 0)}")
        print(f"    Unique Elements: {medium_results.get('total_unique_elements_tested', 0)}")
        print(f"    Coverage Efficiency: {medium_results.get('coverage_efficiency', 0):.2f}")

    print(f"\n🏆 Assessment: {summary['assessment']}")
    print(f"\n💾 Detailed results saved to: {output_file}")

    # Analysis commands
    print(f"\n📋 Analysis commands:")
    print(f"  cat {output_file} | jq '.summary'")
    print(f"  cat {output_file} | jq '.tests.short_run.analysis'")
    print(f"  cat {output_file} | jq '.tests.extended_run.analysis'")


if __name__ == "__main__":
    main()