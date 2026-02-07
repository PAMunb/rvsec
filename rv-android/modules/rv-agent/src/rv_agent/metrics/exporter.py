"""
Metrics exporter for rv-agent.

Saves exploration metrics to JSON files for analysis and validation.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class MetricsExporter:
    """
    Exports rv-agent exploration metrics to JSON files.

    Metrics include exploration progress, decision counters, LLM usage,
    UI coverage, and memory statistics.
    """

    @staticmethod
    def _compute_llm_metrics(results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute detailed LLM metrics from raw results.

        Calculates totals, averages, and rates for LLM usage analysis.
        """
        tokens_input = results.get("llm_tokens_input", 0)
        tokens_output = results.get("llm_tokens_output", 0)
        time_ms = results.get("llm_time_ms", 0.0)
        llm_calls = results.get("llm_executed", 0)
        total_tokens = tokens_input + tokens_output

        # Compute averages (avoid division by zero)
        avg_latency_ms = time_ms / llm_calls if llm_calls > 0 else 0.0
        tokens_per_call = total_tokens / llm_calls if llm_calls > 0 else 0.0
        input_per_call = tokens_input / llm_calls if llm_calls > 0 else 0.0
        output_per_call = tokens_output / llm_calls if llm_calls > 0 else 0.0

        return {
            # Totals
            "total_calls": llm_calls,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "total_tokens": total_tokens,
            "total_time_ms": time_ms,
            # Averages per call
            "avg_latency_ms": round(avg_latency_ms, 2),
            "avg_tokens_per_call": round(tokens_per_call, 2),
            "avg_input_per_call": round(input_per_call, 2),
            "avg_output_per_call": round(output_per_call, 2),
            # Validation metrics
            "validation_failed": results.get("llm_validation_failed", 0),
        }

    @staticmethod
    def build_filename(
        package_name: str,
        agent_mode: str,
        timeout: int,
        repetition: int = 1
    ) -> str:
        """
        Build metrics filename following rv-android naming convention.

        Format: {package}__{rep}__{timeout}__{mode}.rvagent_metrics.json

        Args:
            package_name: Application package name
            agent_mode: Agent execution mode
            timeout: Execution timeout in seconds
            repetition: Task repetition number

        Returns:
            Filename string
        """
        return f"{package_name}__{repetition}__{timeout}__rvagent:{agent_mode}.rvagent_metrics.json"

    @classmethod
    def format_metrics(
        cls,
        results: Dict[str, Any],
        package_name: str,
        agent_mode: str,
        timeout: int
    ) -> Dict[str, Any]:
        """
        Format agent results into structured metrics.

        Args:
            results: Raw results from agent.run()
            package_name: Application package name
            agent_mode: Agent execution mode
            timeout: Configured timeout

        Returns:
            Formatted metrics dictionary
        """
        return {
            "metadata": {
                "package_name": package_name,
                "agent_mode": agent_mode,
                "timeout_configured": timeout,
                "timestamp": datetime.now().isoformat(),
                "status": results.get("status", "unknown")
            },
            "exploration": {
                "iterations": results.get("iterations", 0),
                "execution_time_s": results.get("execution_time_s", 0),
                "unique_states": results.get("unique_states", 0),
                "total_transitions": results.get("total_transitions", 0)
            },
            "decisions": {
                "total_actions": results.get("total_actions", 0),
                "llm_executed": results.get("llm_executed", 0),
                "algorithm_chosen": results.get("algorithm_chosen", 0),
                "llm_percentage": results.get("llm_percentage", 0.0),
                "algorithm_percentage": results.get("algorithm_percentage", 0.0),
                "llm_validation_failed": results.get("llm_validation_failed", 0),
                "forced_back": results.get("forced_back", 0)
            },
            "llm": cls._compute_llm_metrics(results),
            "ui_coverage": results.get("ui_coverage", {}),
            "memory_stats": results.get("memory_stats", {})
        }

    @staticmethod
    def save(
        metrics: Dict[str, Any],
        output_dir: str,
        filename: str
    ) -> Optional[Path]:
        """
        Save metrics to JSON file.

        Args:
            metrics: Formatted metrics dictionary
            output_dir: Output directory path
            filename: Output filename

        Returns:
            Path to saved file, or None if save failed
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            filepath = output_path / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2, default=str)

            logger.info(f"Metrics saved to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
            return None

    @classmethod
    def export(
        cls,
        results: Dict[str, Any],
        output_dir: str,
        package_name: str,
        agent_mode: str,
        timeout: int,
        repetition: int = 1
    ) -> Optional[Path]:
        """
        Export agent results to metrics file.

        Convenience method that formats and saves in one call.

        Args:
            results: Raw results from agent.run()
            output_dir: Output directory path
            package_name: Application package name
            agent_mode: Agent execution mode
            timeout: Configured timeout
            repetition: Task repetition number

        Returns:
            Path to saved file, or None if export failed
        """
        metrics = cls.format_metrics(results, package_name, agent_mode, timeout)
        filename = cls.build_filename(package_name, agent_mode, timeout, repetition)
        return cls.save(metrics, output_dir, filename)
