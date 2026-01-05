#!/usr/bin/env python3
"""
Teste Comparativo: V10 vs V12 vs V13 com Auxiliary Counters Detalhados
==========================================================================

Executa teste de 300 segundos (5 min) por app em cada versão de prompt.
Coleta métricas abrangentes incluindo detalhes dos auxiliary counters.

Comparação:
- V10: Baseline simplificado
- V12: Permission Handling
- V13: Compacto + Detailed Counters

Apps testados (5):
- br.unb.cic.cryptoapp
- com.dozuki.ifixit
- org.secuso.privacyfriendlydicer
- com.alienpants.leafpicrevived
- info.zamojski.soft.towercollector

Métricas incluem:
1. Ações gerais e por tipo
2. Decisor (LLM vs Algoritmo) - com primary/auxiliary separation
3. Auxiliary Counters (llm_fallback, forced_back, recovery_actions)
4. UI Coverage detalhado
5. Exploração (estados, transições)
6. LLM Performance (tokens, tempo)
7. UI Tracker (discovery, interactions)
8. Temporal (rates)
9. Performance derivadas
10. Memory stats
"""

import json
import logging
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory
from rv_android_core.domain.app import App

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/v10_v12_v13_comparison.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# Dataset directory
DATASET_DIR = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")

# 5 apps testados no v13_validation
TEST_APPS = [
    "br.unb.cic.cryptoapp",
    "com.dozuki.ifixit",
    "org.secuso.privacyfriendlydicer",
    "com.alienpants.leafpicrevived",
    "info.zamojski.soft.towercollector",
]

# Versões de prompt a testar
PROMPT_VERSIONS = ["v10", "v12", "v13"]

# Configurações do teste
TEST_CONFIG = {
    "timeout": 300,  # 5 minutos por app
    "device_id": "emulator-5554",
    "agent_mode": "multimode",
    "strategy": "greedy",
    "llm_model": "qwen3-vl-4b-8k:latest",
    "llm_probability": 0.7,
    "device_dimensions": (1080, 1920),
    "optimized_dimensions": (704, 1248),
}


def extract_comprehensive_metrics(
    results: Dict[str, Any],
    ui_coverage_stats: Dict[str, Any],
    short_term_stats: Dict[str, Any] = None,
    long_term_stats: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Extrai métricas abrangentes dos resultados do agent.

    IMPORTANTE: Adaptado para incluir novos campos de detailed counters (v13+).

    Categorias de métricas:
    1. AÇÕES GERAIS
    2. DECISOR (LLM vs Algoritmo) - PRIMARY vs AUXILIARY
    3. AUXILIARY COUNTERS (llm_fallback, forced_back, recovery_actions)
    4. UI COVERAGE GERAL
    5. UI COVERAGE POR CATEGORIA
    6. EXPLORAÇÃO
    7. LLM PERFORMANCE
    8. UI TRACKER DETALHADO
    9. TEMPORAL
    10. PERFORMANCE DERIVADAS
    11. SHORT TERM MEMORY
    12. LONG TERM MEMORY
    """

    # Handle None values
    short_term_stats = short_term_stats or {}
    long_term_stats = long_term_stats or {}

    # Compatibility: Detect if using new counter semantics (v13+) or old (v10/v12)
    has_new_counters = "llm_executed" in results and "algorithm_chosen" in results

    if has_new_counters:
        # V13+: Use new detailed counters
        llm_count = results.get("llm_executed", 0)
        algorithm_count = results.get("algorithm_chosen", 0)
        llm_percentage = results.get("llm_percentage", 0.0)

        # Extract auxiliary counters
        llm_fallback = results.get("llm_fallback", 0)
        forced_back = results.get("forced_back", 0)
        recovery_actions = results.get("recovery_actions", 0)
        auxiliary_total = llm_fallback + forced_back + recovery_actions
    else:
        # V10/V12: Use old counter fields
        llm_count = results.get("llm_decisions", 0)
        algorithm_count = results.get("algorithm_decisions", 0)
        total = llm_count + algorithm_count
        llm_percentage = (llm_count / total * 100) if total > 0 else 0.0

        # No auxiliary counters in old versions
        llm_fallback = 0
        forced_back = 0
        recovery_actions = 0
        auxiliary_total = 0

    metrics = {
        # === 1. AÇÕES GERAIS ===
        "actions": {
            "total": results.get("total_actions", 0),
            "by_type": {},  # Will be filled from memory if available
            "by_decisor": {
                "llm": llm_count,
                "algorithm": algorithm_count
            },
            "decisor_percentage": {
                "llm": llm_percentage,
                "algorithm": 100.0 - llm_percentage
            }
        },

        # === 2. DECISOR DISTRIBUTION ===
        "decisor": {
            "llm_count": llm_count,
            "algorithm_count": algorithm_count,
            "llm_percentage": llm_percentage,
            "algorithm_percentage": 100.0 - llm_percentage,
            "llm_to_algorithm_ratio": (llm_count / algorithm_count) if algorithm_count > 0 else 0.0
        },

        # === 3. AUXILIARY COUNTERS (NEW - v13+) ===
        "auxiliary_counters": {
            "llm_fallback": llm_fallback,
            "forced_back": forced_back,
            "recovery_actions": recovery_actions,
            "auxiliary_total": auxiliary_total,
            "has_data": has_new_counters  # Flag to indicate if data is available
        },

        # === 4. UI COVERAGE GERAL ===
        "ui_coverage": {
            "total_unique_elements": ui_coverage_stats.get("total_unique_elements", 0),
            "total_interactions": ui_coverage_stats.get("total_interactions", 0),
            "average_interactions_per_element": ui_coverage_stats.get("average_interactions_per_element", 0.0),
            "total_screens": ui_coverage_stats.get("total_screens", 0),
            "discovery_timeline_length": ui_coverage_stats.get("discovery_timeline_length", 0),
            "recent_discoveries": ui_coverage_stats.get("recent_discoveries", 0)
        },

        # === 5. UI COVERAGE POR CATEGORIA ===
        "ui_coverage_by_category": {},

        # === 6. EXPLORAÇÃO ===
        "exploration": {
            "unique_states": results.get("unique_states", 0),
            "total_transitions": results.get("total_transitions", 0),
            "states_per_minute": 0.0,
            "transitions_per_state": 0.0
        },

        # === 7. LLM PERFORMANCE ===
        "llm": {
            "tokens_input": results.get("llm_tokens_input", 0),
            "tokens_output": results.get("llm_tokens_output", 0),
            "tokens_total": 0,
            "time_ms": results.get("llm_time_ms", 0.0),
            "time_seconds": 0.0,
            "average_tokens_per_call": 0.0,
            "average_time_per_call_ms": 0.0,
            "tokens_per_second": 0.0,
            "calls_total": llm_count  # Use actual LLM executions
        },

        # === 8. UI TRACKER DETALHADO ===
        "ui_tracker": {
            "action_distribution": ui_coverage_stats.get("action_distribution", {}),
            "most_tested_elements": ui_coverage_stats.get("most_tested_elements", []),
            "least_tested_elements": ui_coverage_stats.get("least_tested_elements", []),
            "test_count_distribution": {
                "0_tests": 0,
                "1_test": 0,
                "2_tests": 0,
                "3_tests": 0,
                "4_tests": 0,
                "5+_tests": 0
            }
        },

        # === 9. TEMPORAL ===
        "temporal": {
            "execution_time_s": results.get("execution_time_s", 0.0),
            "discovery_rate": 0.0,
            "interaction_rate": 0.0
        },

        # === 10. PERFORMANCE DERIVADAS ===
        "performance": {
            "actions_per_second": 0.0,
            "actions_per_minute": 0.0,
            "tokens_per_action": 0.0,
            "llm_time_per_action_ms": 0.0,
            "unique_elements_per_minute": 0.0,
            "states_actions_ratio": 0.0  # V13 specific metric
        },

        # === 11. SHORT TERM MEMORY ===
        "short_term_memory": {
            "iteration_count": short_term_stats.get("iteration_count", 0),
            "current_activity": short_term_stats.get("current_activity"),
            "total_actions_generated": short_term_stats.get("total_actions_generated", 0),
            "total_execution_results": short_term_stats.get("total_execution_results", 0),
            "average_success_rate": short_term_stats.get("average_success_rate", 0.0),
            "memory_utilization": short_term_stats.get("memory_utilization", "0/0"),
            "latest_iteration": short_term_stats.get("latest_iteration", {})
        },

        # === 12. LONG TERM MEMORY ===
        "long_term_memory": {
            "total_states": long_term_stats.get("total_states", 0),
            "total_activities": long_term_stats.get("total_activities", 0),
            "total_action_types": long_term_stats.get("total_action_types", 0),
            "total_actions_executed": long_term_stats.get("total_actions_executed", 0),
            "total_successful_actions": long_term_stats.get("total_successful_actions", 0),
            "overall_success_rate": long_term_stats.get("overall_success_rate", 0.0),
            "total_transitions": long_term_stats.get("total_transitions", 0),
            "most_visited_states": long_term_stats.get("most_visited_states", [])
        },

        # === 13. METADATA ===
        "metadata": {
            "status": results.get("status", "unknown"),
            "iterations": results.get("iterations", 0),
            "prompt_version": "unknown",
            "app_package": "unknown",
            "timestamp": datetime.now().isoformat()
        }
    }

    # Calculate derived LLM metrics
    tokens_in = metrics["llm"]["tokens_input"]
    tokens_out = metrics["llm"]["tokens_output"]
    metrics["llm"]["tokens_total"] = tokens_in + tokens_out

    time_ms = metrics["llm"]["time_ms"]
    metrics["llm"]["time_seconds"] = time_ms / 1000.0

    llm_calls = metrics["llm"]["calls_total"]
    if llm_calls > 0:
        metrics["llm"]["average_tokens_per_call"] = metrics["llm"]["tokens_total"] / llm_calls
        metrics["llm"]["average_time_per_call_ms"] = time_ms / llm_calls

    if time_ms > 0:
        metrics["llm"]["tokens_per_second"] = (metrics["llm"]["tokens_total"] / time_ms) * 1000.0

    # Calculate exploration metrics
    exec_time = metrics["temporal"]["execution_time_s"]
    if exec_time > 0:
        exec_minutes = exec_time / 60.0
        metrics["exploration"]["states_per_minute"] = metrics["exploration"]["unique_states"] / exec_minutes

        # Temporal discovery rates
        metrics["temporal"]["discovery_rate"] = metrics["ui_coverage"]["total_unique_elements"] / exec_minutes
        metrics["temporal"]["interaction_rate"] = metrics["ui_coverage"]["total_interactions"] / exec_minutes

    unique_states = metrics["exploration"]["unique_states"]
    if unique_states > 0:
        metrics["exploration"]["transitions_per_state"] = metrics["exploration"]["total_transitions"] / unique_states

    # Calculate performance metrics
    total_actions = metrics["actions"]["total"]
    if exec_time > 0:
        metrics["performance"]["actions_per_second"] = total_actions / exec_time
        metrics["performance"]["actions_per_minute"] = total_actions / (exec_time / 60.0)
        metrics["performance"]["unique_elements_per_minute"] = metrics["ui_coverage"]["total_unique_elements"] / (exec_time / 60.0)

    if total_actions > 0:
        metrics["performance"]["tokens_per_action"] = metrics["llm"]["tokens_total"] / total_actions
        metrics["performance"]["llm_time_per_action_ms"] = time_ms / total_actions
        metrics["performance"]["states_actions_ratio"] = unique_states / total_actions

    # UI coverage by category
    ui_categories = ui_coverage_stats.get("ui_categories", {})
    for category, data in ui_categories.items():
        detected = data.get("detected", 0)
        tested = data.get("tested", 0)
        coverage = (tested / detected * 100) if detected > 0 else 0.0

        metrics["ui_coverage_by_category"][category] = {
            "detected": detected,
            "tested": tested,
            "coverage": coverage
        }

    # Test count distribution
    element_test_counts = ui_coverage_stats.get("element_test_counts", {})
    for element_id, count in element_test_counts.items():
        if count == 0:
            metrics["ui_tracker"]["test_count_distribution"]["0_tests"] += 1
        elif count == 1:
            metrics["ui_tracker"]["test_count_distribution"]["1_test"] += 1
        elif count == 2:
            metrics["ui_tracker"]["test_count_distribution"]["2_tests"] += 1
        elif count == 3:
            metrics["ui_tracker"]["test_count_distribution"]["3_tests"] += 1
        elif count == 4:
            metrics["ui_tracker"]["test_count_distribution"]["4_tests"] += 1
        else:  # 5+
            metrics["ui_tracker"]["test_count_distribution"]["5+_tests"] += 1

    # Action type distribution from long term memory
    action_types = long_term_stats.get("action_type_counts", {})
    if action_types:
        metrics["actions"]["by_type"] = action_types

    return metrics


def discover_apks() -> Dict[str, Path]:
    """Descobrir APKs para os apps de teste."""
    logger.info("Discovering APKs from dataset...")

    apks_found = {}
    all_apks = list(DATASET_DIR.glob("*.apk"))

    logger.info(f"Found {len(all_apks)} APK files in {DATASET_DIR}")

    for apk_path in all_apks:
        try:
            app = App(str(apk_path))
            package_name = app.get_package()

            if package_name in TEST_APPS:
                apks_found[package_name] = apk_path
                logger.info(f"✓ Found: {package_name} → {apk_path.name}")
        except Exception as e:
            logger.debug(f"Could not extract package from {apk_path.name}: {e}")

    # Report missing apps
    missing = set(TEST_APPS) - set(apks_found.keys())
    if missing:
        logger.warning(f"Missing APKs for: {missing}")

    logger.info(f"Discovered {len(apks_found)}/{len(TEST_APPS)} APKs")

    return apks_found


def install_apk(apk_path: Path, device_id: str) -> bool:
    """Install APK on device with uninstall first."""
    try:
        # Extract package name
        app = App(str(apk_path))
        package = app.get_package()

        # Uninstall first (ignore errors if not installed)
        logger.info(f"Uninstalling {package} if present...")
        subprocess.run(
            ["adb", "-s", device_id, "uninstall", package],
            capture_output=True,
            timeout=30
        )

        # Install with -r (replace) and -g (grant permissions)
        logger.info(f"Installing {apk_path.name}...")
        result = subprocess.run(
            ["adb", "-s", device_id, "install", "-r", "-g", str(apk_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            logger.info(f"✓ Installed: {package}")
            return True
        else:
            logger.error(f"✗ Install failed: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"Install exception: {e}")
        return False


def run_single_test(
    app_package: str,
    apk_path: Path,
    prompt_version: str,
    device_id: str
) -> Dict[str, Any]:
    """Run single app test with specified prompt version."""

    logger.info("="*80)
    logger.info(f"TESTING: {app_package} | Version: {prompt_version}")
    logger.info("="*80)

    # Install APK
    if not install_apk(apk_path, device_id):
        return {
            "metadata": {
                "status": "install_failed",
                "app_package": app_package,
                "prompt_version": prompt_version,
                "timestamp": datetime.now().isoformat(),
                "error": "APK installation failed"
            }
        }

    # Wait for installation to settle
    time.sleep(3)

    # Configure agent
    config = RVAgentConfig(
        package_name=app_package,
        device_id=device_id,
        timeout=TEST_CONFIG["timeout"],
        agent_mode=TEST_CONFIG["agent_mode"],
        strategy=TEST_CONFIG["strategy"],
        llm_model=TEST_CONFIG["llm_model"],
        llm_probability=TEST_CONFIG["llm_probability"],
        prompt_version=prompt_version,
        device_dimensions=TEST_CONFIG["device_dimensions"],
        optimized_dimensions=TEST_CONFIG["optimized_dimensions"],
        screenshot_dir=f"/tmp/v10_v12_v13_test/{app_package}_{prompt_version}",
        screenshot_rotation_limit=50
    )

    try:
        # Create and run agent
        logger.info(f"Creating agent for {app_package} with {prompt_version}...")
        agent = AgentFactory.create_agent(config=config)

        logger.info(f"Running agent (timeout={TEST_CONFIG['timeout']}s)...")
        start_time = time.time()
        results = agent.run()
        elapsed = time.time() - start_time

        logger.info(f"✓ Test completed in {elapsed:.1f}s")

        # Get memory stats
        memory_stats = results.get("memory_stats", {})
        short_term_stats = memory_stats.get("short_term", {})
        long_term_stats = memory_stats.get("long_term", {})
        ui_coverage_stats = memory_stats.get("ui_coverage", {})

        # Extract comprehensive metrics
        metrics = extract_comprehensive_metrics(
            results,
            ui_coverage_stats,
            short_term_stats,
            long_term_stats
        )

        # Add metadata
        metrics["metadata"]["app_package"] = app_package
        metrics["metadata"]["prompt_version"] = prompt_version
        metrics["metadata"]["timestamp"] = datetime.now().isoformat()

        # Log summary
        logger.info(f"Actions: {metrics['actions']['total']}")
        logger.info(f"LLM: {metrics['decisor']['llm_count']} ({metrics['decisor']['llm_percentage']:.1f}%)")
        logger.info(f"Algorithm: {metrics['decisor']['algorithm_count']} ({metrics['decisor']['algorithm_percentage']:.1f}%)")

        if metrics["auxiliary_counters"]["has_data"]:
            logger.info(f"Auxiliary Counters:")
            logger.info(f"  - LLM Fallback: {metrics['auxiliary_counters']['llm_fallback']}")
            logger.info(f"  - Forced Back: {metrics['auxiliary_counters']['forced_back']}")
            logger.info(f"  - Recovery: {metrics['auxiliary_counters']['recovery_actions']}")

        logger.info(f"States: {metrics['exploration']['unique_states']}")
        logger.info(f"UI Elements: {metrics['ui_coverage']['total_unique_elements']}")
        logger.info(f"Tokens/Action: {metrics['performance']['tokens_per_action']:.1f}")

        return metrics

    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        return {
            "metadata": {
                "status": "error",
                "app_package": app_package,
                "prompt_version": prompt_version,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        }


def save_progress(results: Dict[str, Dict[str, Dict[str, Any]]], output_dir: Path):
    """Save incremental progress."""
    progress_file = output_dir / "progress.json"
    with open(progress_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.debug(f"Progress saved to {progress_file}")


def generate_comparative_analysis(
    all_results: Dict[str, Dict[str, Dict[str, Any]]],
    output_dir: Path
):
    """Generate comparative analysis across versions."""

    logger.info("Generating comparative analysis...")

    # Aggregate by version
    version_aggregates = {}

    for version in PROMPT_VERSIONS:
        version_results = all_results.get(version, {})
        successful_results = [
            r for r in version_results.values()
            if r.get("metadata", {}).get("status") == "completed"
        ]

        if not successful_results:
            logger.warning(f"No successful results for {version}")
            continue

        # Calculate averages
        aggregate = {
            "apps_tested": len(successful_results),
            "averages": {},
            "action_types_average": defaultdict(float)
        }

        # Metrics to average
        avg_metrics = [
            ("actions.total", "actions_total"),
            ("decisor.llm_count", "llm_count"),
            ("decisor.algorithm_count", "algorithm_count"),
            ("decisor.llm_percentage", "llm_percentage"),
            ("auxiliary_counters.llm_fallback", "llm_fallback"),
            ("auxiliary_counters.forced_back", "forced_back"),
            ("auxiliary_counters.recovery_actions", "recovery_actions"),
            ("ui_coverage.total_unique_elements", "unique_elements"),
            ("ui_coverage.total_interactions", "total_interactions"),
            ("exploration.unique_states", "unique_states"),
            ("exploration.total_transitions", "total_transitions"),
            ("llm.tokens_total", "tokens_total"),
            ("llm.time_seconds", "llm_time_seconds"),
            ("performance.actions_per_minute", "actions_per_minute"),
            ("performance.tokens_per_action", "tokens_per_action"),
            ("performance.states_actions_ratio", "states_actions_ratio"),
            ("temporal.discovery_rate", "discovery_rate"),
        ]

        for metric_path, metric_name in avg_metrics:
            values = []
            for result in successful_results:
                # Navigate nested dict
                val = result
                for key in metric_path.split('.'):
                    val = val.get(key, {})
                    if not isinstance(val, dict):
                        break

                if isinstance(val, (int, float)):
                    values.append(val)

            if values:
                aggregate["averages"][metric_name] = sum(values) / len(values)

        # Average action types
        for result in successful_results:
            action_types = result.get("actions", {}).get("by_type", {})
            for action_type, count in action_types.items():
                aggregate["action_types_average"][action_type] += count / len(successful_results)

        version_aggregates[version] = aggregate

    # Save comparative analysis
    analysis_file = output_dir / "comparative_analysis.json"
    with open(analysis_file, 'w') as f:
        json.dump(version_aggregates, f, indent=2)

    logger.info(f"✓ Comparative analysis saved to {analysis_file}")

    return version_aggregates


def generate_auxiliary_counters_analysis(
    all_results: Dict[str, Dict[str, Dict[str, Any]]],
    output_dir: Path
):
    """Generate detailed analysis of auxiliary counters."""

    logger.info("Generating auxiliary counters analysis...")

    analysis = {}

    for version in PROMPT_VERSIONS:
        version_results = all_results.get(version, {})
        successful_results = [
            r for r in version_results.values()
            if r.get("metadata", {}).get("status") == "completed"
        ]

        if not successful_results:
            continue

        # Check if this version has auxiliary counter data
        has_data = any(
            r.get("auxiliary_counters", {}).get("has_data", False)
            for r in successful_results
        )

        if not has_data:
            analysis[version] = {
                "has_data": False,
                "note": "Version does not support auxiliary counters"
            }
            continue

        # Aggregate auxiliary counters
        total_fallbacks = 0
        total_forced_back = 0
        total_recovery = 0
        total_actions = 0
        total_llm_exec = 0
        total_alg_chosen = 0

        app_details = {}

        for app_package, result in version_results.items():
            if result.get("metadata", {}).get("status") != "completed":
                continue

            aux = result.get("auxiliary_counters", {})
            actions = result.get("actions", {}).get("total", 0)
            llm_exec = result.get("decisor", {}).get("llm_count", 0)
            alg_chosen = result.get("decisor", {}).get("algorithm_count", 0)

            fallback = aux.get("llm_fallback", 0)
            forced = aux.get("forced_back", 0)
            recovery = aux.get("recovery_actions", 0)

            total_fallbacks += fallback
            total_forced_back += forced
            total_recovery += recovery
            total_actions += actions
            total_llm_exec += llm_exec
            total_alg_chosen += alg_chosen

            app_details[app_package] = {
                "llm_fallback": fallback,
                "forced_back": forced,
                "recovery_actions": recovery,
                "total_actions": actions,
                "llm_executed": llm_exec,
                "algorithm_chosen": alg_chosen,
                "fallback_percentage": (fallback / actions * 100) if actions > 0 else 0.0,
                "forced_back_percentage": (forced / actions * 100) if actions > 0 else 0.0,
                "recovery_percentage": (recovery / actions * 100) if actions > 0 else 0.0
            }

        analysis[version] = {
            "has_data": True,
            "totals": {
                "llm_fallback": total_fallbacks,
                "forced_back": total_forced_back,
                "recovery_actions": total_recovery,
                "total_actions": total_actions,
                "llm_executed": total_llm_exec,
                "algorithm_chosen": total_alg_chosen
            },
            "averages": {
                "llm_fallback_per_test": total_fallbacks / len(successful_results),
                "forced_back_per_test": total_forced_back / len(successful_results),
                "recovery_per_test": total_recovery / len(successful_results),
                "fallback_percentage": (total_fallbacks / total_actions * 100) if total_actions > 0 else 0.0,
                "forced_back_percentage": (total_forced_back / total_actions * 100) if total_actions > 0 else 0.0,
                "recovery_percentage": (total_recovery / total_actions * 100) if total_actions > 0 else 0.0
            },
            "by_app": app_details
        }

    # Save analysis
    aux_file = output_dir / "auxiliary_counters_analysis.json"
    with open(aux_file, 'w') as f:
        json.dump(analysis, f, indent=2)

    logger.info(f"✓ Auxiliary counters analysis saved to {aux_file}")

    return analysis


def generate_markdown_report(
    comparative_analysis: Dict[str, Any],
    auxiliary_analysis: Dict[str, Any],
    output_dir: Path
):
    """Generate comprehensive markdown report."""

    logger.info("Generating markdown report...")

    report_lines = [
        "# V10 vs V12 vs V13 Comparison Report",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"**Test Duration**: {TEST_CONFIG['timeout']}s (5 min) per app",
        f"**Apps Tested**: {len(TEST_APPS)}",
        f"**Versions Compared**: {', '.join(PROMPT_VERSIONS)}",
        "",
        "---",
        "",
        "## Apps Tested",
        "",
    ]

    for i, app in enumerate(TEST_APPS, 1):
        report_lines.append(f"{i}. `{app}`")

    report_lines.extend([
        "",
        "---",
        "",
        "## Primary Metrics Comparison",
        "",
        "| Metric | V10 | V12 | V13 | Winner |",
        "|--------|-----|-----|-----|--------|",
    ])

    # Compare key metrics
    metrics_to_compare = [
        ("actions_total", "Total Actions", "higher"),
        ("llm_percentage", "LLM %", "target_70"),
        ("unique_elements", "UI Elements", "higher"),
        ("unique_states", "Unique States", "higher"),
        ("tokens_per_action", "Tokens/Action", "lower"),
        ("actions_per_minute", "Actions/Min", "higher"),
        ("discovery_rate", "Discovery Rate", "higher"),
        ("states_actions_ratio", "States/Actions", "higher"),
    ]

    for metric_key, metric_label, winner_criteria in metrics_to_compare:
        v10_val = comparative_analysis.get("v10", {}).get("averages", {}).get(metric_key, 0)
        v12_val = comparative_analysis.get("v12", {}).get("averages", {}).get(metric_key, 0)
        v13_val = comparative_analysis.get("v13", {}).get("averages", {}).get(metric_key, 0)

        # Determine winner
        if winner_criteria == "higher":
            winner = max([("V10", v10_val), ("V12", v12_val), ("V13", v13_val)], key=lambda x: x[1])[0]
        elif winner_criteria == "lower":
            winner = min([("V10", v10_val), ("V12", v12_val), ("V13", v13_val)], key=lambda x: x[1])[0]
        elif winner_criteria == "target_70":
            # Closest to 70%
            distances = [
                ("V10", abs(v10_val - 70)),
                ("V12", abs(v12_val - 70)),
                ("V13", abs(v13_val - 70))
            ]
            winner = min(distances, key=lambda x: x[1])[0]
        else:
            winner = "-"

        report_lines.append(
            f"| {metric_label} | {v10_val:.2f} | {v12_val:.2f} | {v13_val:.2f} | **{winner}** |"
        )

    # Auxiliary Counters Section
    report_lines.extend([
        "",
        "---",
        "",
        "## Auxiliary Counters (V13 Only)",
        "",
        "V13 introduces detailed tracking of special case actions that don't count toward the 70/30 LLM/Algorithm proportion:",
        "",
        "| Counter | Total | Per Test | % of Actions |",
        "|---------|-------|----------|--------------|",
    ])

    v13_aux = auxiliary_analysis.get("v13", {})
    if v13_aux.get("has_data"):
        totals = v13_aux.get("totals", {})
        averages = v13_aux.get("averages", {})

        report_lines.append(
            f"| LLM Fallback | {totals.get('llm_fallback', 0)} | "
            f"{averages.get('llm_fallback_per_test', 0):.1f} | "
            f"{averages.get('fallback_percentage', 0):.1f}% |"
        )
        report_lines.append(
            f"| Forced Back | {totals.get('forced_back', 0)} | "
            f"{averages.get('forced_back_per_test', 0):.1f} | "
            f"{averages.get('forced_back_percentage', 0):.1f}% |"
        )
        report_lines.append(
            f"| Recovery | {totals.get('recovery_actions', 0)} | "
            f"{averages.get('recovery_per_test', 0):.1f} | "
            f"{averages.get('recovery_percentage', 0):.1f}% |"
        )
    else:
        report_lines.append("| - | N/A | N/A | N/A |")
        report_lines.append("")
        report_lines.append("_Auxiliary counters not available in V13 results_")

    # Detailed insights
    report_lines.extend([
        "",
        "---",
        "",
        "## Detailed Insights",
        "",
        "### LLM Decision Making",
        "",
    ])

    for version in PROMPT_VERSIONS:
        agg = comparative_analysis.get(version, {})
        avgs = agg.get("averages", {})

        llm_pct = avgs.get("llm_percentage", 0)
        llm_count = avgs.get("llm_count", 0)
        alg_count = avgs.get("algorithm_count", 0)

        report_lines.append(f"**{version.upper()}**: {llm_pct:.1f}% LLM ({llm_count:.1f} LLM / {alg_count:.1f} Algorithm)")

    report_lines.extend([
        "",
        "### UI Coverage Performance",
        "",
    ])

    for version in PROMPT_VERSIONS:
        avgs = comparative_analysis.get(version, {}).get("averages", {})
        elements = avgs.get("unique_elements", 0)
        interactions = avgs.get("total_interactions", 0)
        discovery_rate = avgs.get("discovery_rate", 0)

        report_lines.append(
            f"**{version.upper()}**: {elements:.1f} elements discovered, "
            f"{interactions:.1f} interactions, {discovery_rate:.1f} elements/min"
        )

    report_lines.extend([
        "",
        "### Token Efficiency",
        "",
    ])

    for version in PROMPT_VERSIONS:
        avgs = comparative_analysis.get(version, {}).get("averages", {})
        tokens_per_action = avgs.get("tokens_per_action", 0)
        tokens_total = avgs.get("tokens_total", 0)

        report_lines.append(
            f"**{version.upper()}**: {tokens_per_action:.1f} tokens/action "
            f"({tokens_total:.0f} tokens total avg)"
        )

    # Save report
    report_file = output_dir / "comparative_report.md"
    with open(report_file, 'w') as f:
        f.write('\n'.join(report_lines))

    logger.info(f"✓ Markdown report saved to {report_file}")


def main():
    """Main test orchestration."""

    logger.info("="*80)
    logger.info("V10 vs V12 vs V13 COMPARISON TEST")
    logger.info("="*80)
    logger.info(f"Apps: {len(TEST_APPS)}")
    logger.info(f"Versions: {PROMPT_VERSIONS}")
    logger.info(f"Duration per app: {TEST_CONFIG['timeout']}s")
    logger.info(f"Total estimated time: ~{len(TEST_APPS) * len(PROMPT_VERSIONS) * 5 + 15} minutes")
    logger.info("")

    # Discover APKs
    apks_found = discover_apks()

    if not apks_found:
        logger.error("No APKs found!")
        return

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"results/v10_v12_v13_comparison_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Output directory: {output_dir}")
    logger.info("")

    # Create version subdirectories
    for version in PROMPT_VERSIONS:
        (output_dir / f"{version}_results").mkdir(exist_ok=True)

    # Run tests
    all_results = {version: {} for version in PROMPT_VERSIONS}

    test_count = 0
    total_tests = len(apks_found) * len(PROMPT_VERSIONS)

    for app_package, apk_path in apks_found.items():
        for version in PROMPT_VERSIONS:
            test_count += 1
            logger.info(f"\n[{test_count}/{total_tests}] Testing {app_package} with {version}")

            # Run test
            result = run_single_test(
                app_package,
                apk_path,
                version,
                TEST_CONFIG["device_id"]
            )

            # Store result
            all_results[version][app_package] = result

            # Save individual result
            result_file = output_dir / f"{version}_results" / f"{app_package}_{version}.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)

            # Save progress
            save_progress(all_results, output_dir)

            # Wait between tests
            if test_count < total_tests:
                logger.info("Waiting 5s before next test...")
                time.sleep(5)

    # Generate analyses
    logger.info("\n" + "="*80)
    logger.info("GENERATING ANALYSES")
    logger.info("="*80)

    comparative_analysis = generate_comparative_analysis(all_results, output_dir)
    auxiliary_analysis = generate_auxiliary_counters_analysis(all_results, output_dir)
    generate_markdown_report(comparative_analysis, auxiliary_analysis, output_dir)

    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETED")
    logger.info("="*80)
    logger.info(f"Results saved to: {output_dir}")
    logger.info("")

    # Quick summary
    for version in PROMPT_VERSIONS:
        successful = sum(
            1 for r in all_results[version].values()
            if r.get("metadata", {}).get("status") == "completed"
        )
        logger.info(f"{version.upper()}: {successful}/{len(TEST_APPS)} tests successful")

    logger.info("\nOutput files:")
    logger.info(f"  - {output_dir}/comparative_analysis.json")
    logger.info(f"  - {output_dir}/auxiliary_counters_analysis.json")
    logger.info(f"  - {output_dir}/comparative_report.md")
    logger.info(f"  - {output_dir}/progress.json")


if __name__ == "__main__":
    main()
