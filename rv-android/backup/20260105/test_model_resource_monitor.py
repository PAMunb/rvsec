#!/usr/bin/env python3
"""
Monitor de recursos para testes LLM - 16K vs 8K
Monitora GPU, CPU, RAM durante execução e analisa tokens
"""

import json
import logging
import sys
import time
import subprocess
import threading
import psutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-agent" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-android-core" / "src"))

from rv_agent.core.agent_factory import AgentFactory
from rv_agent.config.agent_config import RVAgentConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Monitor GPU, CPU, RAM usage during test."""

    def __init__(self):
        self.monitoring = False
        self.samples = []
        self.monitor_thread = None

    def get_gpu_stats(self) -> Dict[str, Any]:
        """Get GPU usage via nvidia-smi."""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu',
                 '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode == 0:
                parts = result.stdout.strip().split(', ')
                return {
                    'gpu_memory_used_mb': int(parts[0]),
                    'gpu_memory_total_mb': int(parts[1]),
                    'gpu_utilization_pct': int(parts[2]),
                    'gpu_temperature_c': int(parts[3])
                }
        except Exception as e:
            logger.debug(f"GPU stats error: {e}")

        return {}

    def get_cpu_stats(self) -> Dict[str, Any]:
        """Get CPU and RAM usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()

            return {
                'cpu_percent': cpu_percent,
                'ram_used_mb': mem.used // (1024 * 1024),
                'ram_total_mb': mem.total // (1024 * 1024),
                'ram_percent': mem.percent
            }
        except Exception as e:
            logger.debug(f"CPU stats error: {e}")
            return {}

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.monitoring:
            sample = {
                'timestamp': time.time(),
                **self.get_gpu_stats(),
                **self.get_cpu_stats()
            }
            self.samples.append(sample)
            time.sleep(2)  # Sample every 2 seconds

    def start(self):
        """Start monitoring."""
        self.monitoring = True
        self.samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("🔍 Resource monitoring started")

    def stop(self):
        """Stop monitoring and return stats."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        logger.info("🔍 Resource monitoring stopped")
        return self.get_summary()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if not self.samples:
            return {}

        # Filter out samples without GPU data
        gpu_samples = [s for s in self.samples if 'gpu_memory_used_mb' in s]

        summary = {
            'total_samples': len(self.samples),
            'duration_s': self.samples[-1]['timestamp'] - self.samples[0]['timestamp']
        }

        # GPU stats
        if gpu_samples:
            gpu_mem = [s['gpu_memory_used_mb'] for s in gpu_samples]
            gpu_util = [s['gpu_utilization_pct'] for s in gpu_samples]
            gpu_temp = [s['gpu_temperature_c'] for s in gpu_samples]

            summary.update({
                'gpu_memory_min_mb': min(gpu_mem),
                'gpu_memory_max_mb': max(gpu_mem),
                'gpu_memory_avg_mb': sum(gpu_mem) / len(gpu_mem),
                'gpu_utilization_min_pct': min(gpu_util),
                'gpu_utilization_max_pct': max(gpu_util),
                'gpu_utilization_avg_pct': sum(gpu_util) / len(gpu_util),
                'gpu_temperature_min_c': min(gpu_temp),
                'gpu_temperature_max_c': max(gpu_temp),
                'gpu_temperature_avg_c': sum(gpu_temp) / len(gpu_temp)
            })

        # CPU/RAM stats
        if self.samples:
            cpu_pct = [s.get('cpu_percent', 0) for s in self.samples]
            ram_mb = [s.get('ram_used_mb', 0) for s in self.samples]

            summary.update({
                'cpu_min_pct': min(cpu_pct),
                'cpu_max_pct': max(cpu_pct),
                'cpu_avg_pct': sum(cpu_pct) / len(cpu_pct),
                'ram_min_mb': min(ram_mb),
                'ram_max_mb': max(ram_mb),
                'ram_avg_mb': sum(ram_mb) / len(ram_mb)
            })

        return summary


def run_monitored_test(model_name: str, package_name: str = "br.unb.cic.cryptoapp") -> Dict[str, Any]:
    """Run test with resource monitoring."""

    logger.warning("="*80)
    logger.warning(f"RESOURCE MONITORED TEST")
    logger.warning("="*80)
    logger.warning(f"Model: {model_name}")
    logger.warning(f"App: {package_name}")
    logger.warning(f"Duration: 120s")
    logger.warning("="*80)
    logger.warning("")

    # Create config
    config = RVAgentConfig(
        package_name=package_name,
        agent_mode="multimode",
        strategy="greedy",
        llm_provider="ollama",
        llm_model=model_name,
        llm_temperature=0.1,
        llm_top_p=0.9,
        llm_top_k=40,
        prompt_version="v13",
        max_iterations=20,
        timeout=120,
        device_id="emulator-5554"
    )

    # Start resource monitoring
    monitor = ResourceMonitor()
    monitor.start()

    start_time = time.time()

    try:
        # Create and run agent
        logger.info(f"Creating RVAgent with model {model_name}...")
        agent = AgentFactory.create_agent(config)

        logger.info("Starting execution...")
        results = agent.run()

        execution_time = time.time() - start_time

        # Stop monitoring
        resource_stats = monitor.stop()

        # Extract metrics
        metrics = {
            "model": model_name,
            "package_name": package_name,
            "execution_time_s": execution_time,
            "timestamp": datetime.now().isoformat(),

            # Core metrics
            "iterations": results.get("iterations", 0),
            "llm_executed": results.get("llm_executed", 0),
            "algorithm_chosen": results.get("algorithm_chosen", 0),
            "llm_fallback": results.get("llm_fallback", 0),
            "actions_executed": results.get("actions_executed", 0),

            # LLM metrics
            "llm_tokens_input": results.get("llm_tokens_input", 0),
            "llm_tokens_output": results.get("llm_tokens_output", 0),
            "llm_time_ms": results.get("llm_time_ms", 0),

            # Resource stats
            "resources": resource_stats
        }

        # Calculate derived metrics
        llm_total = metrics["llm_executed"] + metrics["llm_fallback"]
        if llm_total > 0:
            metrics["llm_success_rate"] = (metrics["llm_executed"] / llm_total) * 100
            metrics["llm_fallback_rate"] = (metrics["llm_fallback"] / llm_total) * 100
        else:
            metrics["llm_success_rate"] = 0.0
            metrics["llm_fallback_rate"] = 0.0

        if metrics["llm_executed"] > 0:
            total_tokens = metrics["llm_tokens_input"] + metrics["llm_tokens_output"]
            metrics["avg_tokens_per_call"] = total_tokens / metrics["llm_executed"]
            metrics["avg_time_per_call_ms"] = metrics["llm_time_ms"] / metrics["llm_executed"]
        else:
            metrics["avg_tokens_per_call"] = 0.0
            metrics["avg_time_per_call_ms"] = 0.0

        # Print results
        logger.warning("")
        logger.warning("="*80)
        logger.warning(f"RESULTS: {model_name}")
        logger.warning("="*80)
        logger.warning(f"Iterations: {metrics['iterations']}")
        logger.warning(f"LLM executed: {metrics['llm_executed']}")
        logger.warning(f"LLM fallback: {metrics['llm_fallback']}")
        logger.warning(f"Success rate: {metrics['llm_success_rate']:.1f}%")
        logger.warning(f"Fallback rate: {metrics['llm_fallback_rate']:.1f}%")
        logger.warning("")
        logger.warning("LLM Token Usage:")
        logger.warning(f"  Input tokens: {metrics['llm_tokens_input']}")
        logger.warning(f"  Output tokens: {metrics['llm_tokens_output']}")
        logger.warning(f"  Avg tokens/call: {metrics['avg_tokens_per_call']:.1f}")
        logger.warning(f"  Avg time/call: {metrics['avg_time_per_call_ms']:.1f}ms")
        logger.warning("")

        if resource_stats:
            logger.warning("Resource Usage:")
            if 'gpu_memory_avg_mb' in resource_stats:
                logger.warning(f"  GPU Memory: {resource_stats['gpu_memory_min_mb']}-{resource_stats['gpu_memory_max_mb']} MB (avg: {resource_stats['gpu_memory_avg_mb']:.0f} MB)")
                logger.warning(f"  GPU Utilization: {resource_stats['gpu_utilization_min_pct']}-{resource_stats['gpu_utilization_max_pct']}% (avg: {resource_stats['gpu_utilization_avg_pct']:.1f}%)")
                logger.warning(f"  GPU Temperature: {resource_stats['gpu_temperature_min_c']}-{resource_stats['gpu_temperature_max_c']}°C (avg: {resource_stats['gpu_temperature_avg_c']:.1f}°C)")

            if 'cpu_avg_pct' in resource_stats:
                logger.warning(f"  CPU Usage: {resource_stats['cpu_min_pct']:.1f}-{resource_stats['cpu_max_pct']:.1f}% (avg: {resource_stats['cpu_avg_pct']:.1f}%)")
                logger.warning(f"  RAM Usage: {resource_stats['ram_min_mb']}-{resource_stats['ram_max_mb']} MB (avg: {resource_stats['ram_avg_mb']:.0f} MB)")

        logger.warning("="*80)
        logger.warning("")

        return metrics

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

        monitor.stop()

        return {
            "model": model_name,
            "package_name": package_name,
            "error": str(e),
            "execution_time_s": time.time() - start_time,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Run monitored tests for both 16K and 8K models."""

    logger.warning("="*80)
    logger.warning("RESOURCE MONITORING TEST - 16K vs 8K")
    logger.warning("="*80)
    logger.warning("Testing both models with resource monitoring")
    logger.warning("Duration per model: 120s")
    logger.warning("="*80)
    logger.warning("")

    results = []

    # Test 16K model
    logger.warning("\n" + "="*80)
    logger.warning("TEST 1/2: 16K Model")
    logger.warning("="*80 + "\n")

    result_16k = run_monitored_test("qwen3-vl-4b-16k:latest")
    results.append(result_16k)

    logger.info("Waiting 10s before next test...")
    time.sleep(10)

    # Test 8K model
    logger.warning("\n" + "="*80)
    logger.warning("TEST 2/2: 8K Model")
    logger.warning("="*80 + "\n")

    result_8k = run_monitored_test("qwen3-vl-4b-8k:latest")
    results.append(result_8k)

    # Comparison
    logger.warning("\n" + "="*80)
    logger.warning("COMPARISON: 16K vs 8K")
    logger.warning("="*80 + "\n")

    if "error" not in result_16k and "error" not in result_8k:
        logger.warning("Performance Metrics:")
        logger.warning(f"  LLM Success Rate: 16K={result_16k['llm_success_rate']:.1f}% vs 8K={result_8k['llm_success_rate']:.1f}%")
        logger.warning(f"  LLM Fallback Rate: 16K={result_16k['llm_fallback_rate']:.1f}% vs 8K={result_8k['llm_fallback_rate']:.1f}%")
        logger.warning(f"  Avg Tokens/Call: 16K={result_16k['avg_tokens_per_call']:.1f} vs 8K={result_8k['avg_tokens_per_call']:.1f}")
        logger.warning(f"  Avg Time/Call: 16K={result_16k['avg_time_per_call_ms']:.1f}ms vs 8K={result_8k['avg_time_per_call_ms']:.1f}ms")
        logger.warning("")

        if result_16k.get('resources') and result_8k.get('resources'):
            r16 = result_16k['resources']
            r8 = result_8k['resources']

            logger.warning("Resource Comparison:")
            if 'gpu_memory_avg_mb' in r16 and 'gpu_memory_avg_mb' in r8:
                logger.warning(f"  GPU Memory (avg): 16K={r16['gpu_memory_avg_mb']:.0f}MB vs 8K={r8['gpu_memory_avg_mb']:.0f}MB")
                logger.warning(f"  GPU Utilization (avg): 16K={r16['gpu_utilization_avg_pct']:.1f}% vs 8K={r8['gpu_utilization_avg_pct']:.1f}%")

            if 'cpu_avg_pct' in r16 and 'cpu_avg_pct' in r8:
                logger.warning(f"  CPU Usage (avg): 16K={r16['cpu_avg_pct']:.1f}% vs 8K={r8['cpu_avg_pct']:.1f}%")
                logger.warning(f"  RAM Usage (avg): 16K={r16['ram_avg_mb']:.0f}MB vs 8K={r8['ram_avg_mb']:.0f}MB")

    logger.warning("="*80)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"resource_monitor_16k_vs_8k_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.warning(f"Results saved to: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
