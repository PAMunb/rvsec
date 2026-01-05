#!/usr/bin/env python3
"""
Teste Comparativo Completo: V10 vs V11 vs V12
================================================

Executa teste de 300 segundos por app em cada versão de prompt.
Coleta métricas abrangentes para apoiar decisões de desenvolvimento.

Comparação:
- V10: Baseline simplificado
- V11: UI Coverage Enhancement (scroll, text fields, spinners, back button)
- V12: Permission Handling

Métricas coletadas (expandidas):
1. Ações gerais e por tipo
2. Decisor (LLM vs Algoritmo)
3. UI Coverage detalhado (overall + por categoria)
4. Exploração (estados, transições)
5. LLM (tokens, tempo, eficiência)
6. UI Tracker (discovery, interactions, distribution)
7. Temporal (discovery rate, timeline)
8. Performance (actions/second, tokens/action)
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
        logging.FileHandler('/tmp/prompt_comparison.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# Dataset directory
DATASET_DIR = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")

# Complete list of 28 apps extracted from dataset using App class (androguard)
TEST_APPS = [
    "ar.rulosoft.mimanganu",  # ar.rulosoft.mimanganu_75.apk
    "au.com.wallaceit.reddinator",  # au.com.wallaceit.reddinator_68.apk
    "biz.gyrus.yaab",  # biz.gyrus.yaab_30.apk
    "byrne.utilities.hashpass",  # byrne.utilities.hashpass_2.apk
    "ca.farrelltonsolar.classic",  # ca.farrelltonsolar.classic_314.apk
    "cf.playhi.freezeyou",  # cf.playhi.freezeyou_151.apk
    "com.aidinhut.simpletextcrypt",  # com.aidinhut.simpletextcrypt_14.apk
    "com.akop.bach",  # com.akop.bach_120.apk
    "com.alienpants.leafpicrevived",  # com.alienpants.leafpicrevived_24.apk
    "com.crazyhitty.chdev.ks.munch",  # com.crazyhitty.chdev.ks.munch_14.apk
    "com.cyanogenmod.filemanager.ics",  # com.cyanogenmod.filemanager.ics_1015.apk
    "com.dougkeen.bart",  # com.dougkeen.bart_50.apk
    "com.dozuki.ifixit",  # com.dozuki.ifixit_46.apk
    "com.gh4a",  # com.gh4a_73.apk
    "com.gianlu.dnshero",  # com.gianlu.dnshero_40.apk
    "com.github.axet.hourlyreminder",  # com.github.axet.hourlyreminder_476.apk
    "com.hwloc.lstopo",  # com.hwloc.lstopo_271.apk
    "com.orpheusdroid.sqliteviewer",  # com.orpheusdroid.sqliteviewer_1.apk
    "com.rafapps.simplenotes",  # com.rafapps.simplenotes_7.apk
    "com.sam.hex",  # com.sam.hex_16.apk
    "br.unb.cic.cryptoapp",  # cryptoapp.apk
    "info.zamojski.soft.towercollector",  # info.zamojski.soft.towercollector_2140302.apk
    "livio.rssreader",  # livio.rssreader_101.apk
    "org.emunix.insteadlauncher",  # org.emunix.insteadlauncher_80601.apk
    "org.pulpdust.lesserpad",  # org.pulpdust.lesserpad_42.apk
    "org.secuso.privacyfriendlydicer",  # org.secuso.privacyfriendlydicer_8.apk
    "org.secuso.privacyfriendlyludo",  # org.secuso.privacyfriendlyludo_5.apk
    "t20kdc.offlinepuzzlesolver",  # t20kdc.offlinepuzzlesolver_4.apk
]

# Versões de prompt a testar
PROMPT_VERSIONS = ["v10", "v11", "v12"]

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

    Categorias de métricas:
    1. AÇÕES GERAIS
    2. DECISOR (LLM vs Algoritmo)
    3. UI COVERAGE GERAL
    4. UI COVERAGE POR CATEGORIA (EditText, Spinner, Button, etc.)
    5. EXPLORAÇÃO (Estados, Transições)
    6. LLM PERFORMANCE (Tokens, Tempo, Eficiência)
    7. UI TRACKER DETALHADO (Discovery, Interactions, Distribution)
    8. TEMPORAL (Discovery rate, Timeline)
    9. PERFORMANCE DERIVADAS (actions/sec, tokens/action, etc.)
    10. SHORT TERM MEMORY (Screen-scoped interactions)
    11. LONG TERM MEMORY (Cross-screen exploration patterns)
    """

    # Handle None values
    short_term_stats = short_term_stats or {}
    long_term_stats = long_term_stats or {}

    metrics = {
        # === 1. AÇÕES GERAIS ===
        "actions": {
            "total": results.get("total_actions", 0),
            "by_type": {},  # CLICK, SET_TEXT, SCROLL, BACK, SWIPE, etc.
            "by_decisor": {
                "llm": results.get("llm_decisions", 0),
                "algorithm": results.get("algorithm_decisions", 0)
            },
            "decisor_percentage": {
                "llm": 0.0,
                "algorithm": 0.0
            }
        },

        # === 2. DECISOR DISTRIBUTION ===
        "decisor": {
            "llm_count": results.get("llm_decisions", 0),
            "algorithm_count": results.get("algorithm_decisions", 0),
            "llm_percentage": 0.0,
            "algorithm_percentage": 0.0,
            "llm_to_algorithm_ratio": 0.0
        },

        # === 3. UI COVERAGE GERAL ===
        "ui_coverage": {
            "total_unique_elements": ui_coverage_stats.get("total_unique_elements", 0),
            "total_interactions": ui_coverage_stats.get("total_interactions", 0),
            "average_interactions_per_element": ui_coverage_stats.get("average_interactions_per_element", 0.0),
            "total_screens": ui_coverage_stats.get("total_screens", 0),
            "discovery_timeline_length": ui_coverage_stats.get("discovery_timeline_length", 0),
            "recent_discoveries": ui_coverage_stats.get("recent_discoveries", 0)
        },

        # === 4. UI COVERAGE POR CATEGORIA ===
        "ui_coverage_by_category": {
            # Será preenchido com categorias: EditText, Spinner, Button, etc.
            # Cada categoria terá: detected, tested, coverage_percentage
        },

        # === 5. EXPLORAÇÃO ===
        "exploration": {
            "unique_states": results.get("unique_states", 0),
            "total_transitions": results.get("total_transitions", 0),
            "states_per_minute": 0.0,
            "transitions_per_state": 0.0
        },

        # === 6. LLM PERFORMANCE ===
        "llm": {
            "tokens_input": results.get("llm_tokens_input", 0),
            "tokens_output": results.get("llm_tokens_output", 0),
            "tokens_total": 0,
            "time_ms": results.get("llm_time_ms", 0.0),
            "time_seconds": 0.0,
            "average_tokens_per_call": 0.0,
            "average_time_per_call_ms": 0.0,
            "tokens_per_second": 0.0,
            "calls_total": results.get("llm_decisions", 0)
        },

        # === 7. UI TRACKER DETALHADO ===
        "ui_tracker": {
            "action_distribution": ui_coverage_stats.get("action_distribution", {}),
            "most_tested_elements": ui_coverage_stats.get("most_tested_elements", []),
            "least_tested_elements": ui_coverage_stats.get("least_tested_elements", []),
            "test_count_distribution": {
                # Elementos com 0, 1, 2, 3, 4, 5+ testes
                "0_tests": 0,
                "1_test": 0,
                "2_tests": 0,
                "3_tests": 0,
                "4_tests": 0,
                "5+_tests": 0
            }
        },

        # === 8. TEMPORAL ===
        "temporal": {
            "execution_time_s": results.get("execution_time_s", 0.0),
            "discovery_rate": 0.0,  # elements discovered per minute
            "interaction_rate": 0.0  # interactions per minute
        },

        # === 9. PERFORMANCE DERIVADAS ===
        "performance": {
            "actions_per_second": 0.0,
            "actions_per_minute": 0.0,
            "tokens_per_action": 0.0,
            "llm_time_per_action_ms": 0.0,
            "unique_elements_per_minute": 0.0
        },

        # === 10. SHORT TERM MEMORY (Screen-scoped) ===
        "short_term_memory": {
            "iteration_count": short_term_stats.get("iteration_count", 0),
            "current_activity": short_term_stats.get("current_activity"),
            "total_actions_generated": short_term_stats.get("total_actions_generated", 0),
            "total_execution_results": short_term_stats.get("total_execution_results", 0),
            "average_success_rate": short_term_stats.get("average_success_rate", 0.0),
            "memory_utilization": short_term_stats.get("memory_utilization", "0/0"),
            "latest_iteration": short_term_stats.get("latest_iteration", {})
        },

        # === 11. LONG TERM MEMORY (Cross-screen patterns) ===
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

        # === 12. METADATA ===
        "metadata": {
            "status": results.get("status", "unknown"),
            "iterations": results.get("iterations", 0),
            "prompt_version": "unknown",
            "app_package": "unknown",
            "timestamp": datetime.now().isoformat()
        }
    }

    # === CÁLCULOS DERIVADOS ===

    total_actions = metrics["actions"]["total"]
    exec_time = metrics["temporal"]["execution_time_s"]
    llm_decisions = metrics["decisor"]["llm_count"]
    algorithm_decisions = metrics["decisor"]["algorithm_count"]

    # Decisor percentages
    if total_actions > 0:
        metrics["actions"]["decisor_percentage"]["llm"] = (llm_decisions / total_actions) * 100
        metrics["actions"]["decisor_percentage"]["algorithm"] = (algorithm_decisions / total_actions) * 100
        metrics["decisor"]["llm_percentage"] = (llm_decisions / total_actions) * 100
        metrics["decisor"]["algorithm_percentage"] = (algorithm_decisions / total_actions) * 100

    # LLM to algorithm ratio
    if algorithm_decisions > 0:
        metrics["decisor"]["llm_to_algorithm_ratio"] = llm_decisions / algorithm_decisions

    # Exploration rates
    unique_states = metrics["exploration"]["unique_states"]
    total_transitions = metrics["exploration"]["total_transitions"]

    if exec_time > 0:
        exec_minutes = exec_time / 60
        metrics["exploration"]["states_per_minute"] = unique_states / exec_minutes
        metrics["performance"]["actions_per_second"] = total_actions / exec_time
        metrics["performance"]["actions_per_minute"] = total_actions / exec_minutes
        metrics["performance"]["unique_elements_per_minute"] = metrics["ui_coverage"]["total_unique_elements"] / exec_minutes
        metrics["temporal"]["discovery_rate"] = metrics["ui_coverage"]["total_unique_elements"] / exec_minutes
        metrics["temporal"]["interaction_rate"] = metrics["ui_coverage"]["total_interactions"] / exec_minutes

    if unique_states > 0:
        metrics["exploration"]["transitions_per_state"] = total_transitions / unique_states

    # LLM performance
    tokens_input = metrics["llm"]["tokens_input"]
    tokens_output = metrics["llm"]["tokens_output"]
    llm_time_ms = metrics["llm"]["time_ms"]
    llm_calls = metrics["llm"]["calls_total"]

    metrics["llm"]["tokens_total"] = tokens_input + tokens_output
    metrics["llm"]["time_seconds"] = llm_time_ms / 1000

    if llm_calls > 0:
        metrics["llm"]["average_tokens_per_call"] = (tokens_input + tokens_output) / llm_calls
        metrics["llm"]["average_time_per_call_ms"] = llm_time_ms / llm_calls

    if llm_time_ms > 0:
        tokens_total = tokens_input + tokens_output
        metrics["llm"]["tokens_per_second"] = (tokens_total / llm_time_ms) * 1000

    # Performance derivadas
    if total_actions > 0:
        metrics["performance"]["tokens_per_action"] = (tokens_input + tokens_output) / total_actions
        metrics["performance"]["llm_time_per_action_ms"] = llm_time_ms / total_actions

    return metrics


def analyze_ui_categories(screen_descriptions: List[Any]) -> Dict[str, Dict[str, int]]:
    """
    Analisa distribuição de elementos UI por categoria.

    Categorias rastreadas:
    - EditText (text input fields)
    - Spinner (dropdown selectors)
    - Button (clickable buttons)
    - ImageView (images)
    - TextView (text displays)
    - RecyclerView/ListView (scrollable lists)
    - CheckBox, RadioButton, Switch (toggles)

    Para cada categoria:
    - detected: Total detectado
    - tested: Total testado
    - coverage: % de cobertura
    """
    categories = defaultdict(lambda: {"detected": 0, "tested": 0, "coverage": 0.0})

    # Esta função seria melhor integrada com o screen_processor real
    # Por enquanto, retorna estrutura placeholder
    return dict(categories)


def discover_apks() -> List[Dict[str, Any]]:
    """
    Discover all APKs in dataset directory.

    Returns list of dicts with:
    - package: Package name (from App class using androguard)
    - apk_path: Path to APK file
    - app_dir: Directory name
    """
    # Suppress androguard verbose logging
    logging.getLogger("androguard").setLevel(logging.WARNING)

    apks = []

    for app_dir in sorted(DATASET_DIR.iterdir()):
        if not app_dir.is_dir():
            continue

        # Find APK file in directory
        apk_files = list(app_dir.glob("*.apk"))
        if not apk_files:
            logger.warning(f"No APK found in {app_dir.name}")
            continue

        apk_path = apk_files[0]

        try:
            # Use App class with androguard to extract package name
            app = App(app_path=str(apk_path))
            package = app.package_name

            apks.append({
                'package': package,
                'apk_path': apk_path,
                'app_dir': app_dir.name
            })

            logger.info(f"✓ Discovered: {app_dir.name} → {package}")

        except Exception as e:
            logger.error(f"✗ Failed to extract package from {app_dir.name}: {e}")

    return apks


def install_apk(apk_path: Path, package: str) -> bool:
    """
    Install APK on emulator.

    Uninstalls existing version first, then installs with -r (reinstall) and -g (grant permissions).
    """
    try:
        # Uninstall first if exists (ignore errors)
        subprocess.run(
            ["adb", "uninstall", package],
            capture_output=True,
            timeout=30
        )

        # Install with reinstall and grant all permissions
        result = subprocess.run(
            ["adb", "install", "-r", "-g", str(apk_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"Failed to install {apk_path}: {result.stderr}")
            return False

        logger.info(f"✅ Installed {package}")
        return True

    except Exception as e:
        logger.error(f"Error installing {apk_path}: {e}")
        return False


def run_single_test(
    app_package: str,
    prompt_version: str,
    results_dir: Path,
    apk_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Executa um único teste para app e versão de prompt."""

    logger.info(f"\n{'='*80}")
    logger.info(f"Testing: {app_package} with {prompt_version}")
    logger.info(f"{'='*80}\n")

    # Criar configuração
    config = RVAgentConfig(
        package_name=app_package,
        device_id=TEST_CONFIG["device_id"],
        timeout=TEST_CONFIG["timeout"],
        agent_mode=TEST_CONFIG["agent_mode"],
        strategy=TEST_CONFIG["strategy"],
        llm_model=TEST_CONFIG["llm_model"],
        llm_probability=TEST_CONFIG["llm_probability"],
        prompt_version=prompt_version,
        device_dimensions=TEST_CONFIG["device_dimensions"],
        optimized_dimensions=TEST_CONFIG["optimized_dimensions"],
        screenshot_dir=f"/tmp/rvagent_prompt_test_{prompt_version}_{app_package}",
        screenshot_rotation_limit=50
    )

    try:
        # Criar e executar agent
        agent = AgentFactory.create_agent(config=config)
        results = agent.run()

        # Extrair estatísticas via facade (memory_stats já incluído no results)
        # Usar facade do agent como fallback caso não esteja no results
        if "memory_stats" in results:
            memory_stats = results["memory_stats"]
        else:
            memory_stats = agent.get_memory_stats()

        ui_coverage_stats = memory_stats.get("ui_coverage", {})
        short_term_stats = memory_stats.get("short_term", {})
        long_term_stats = memory_stats.get("long_term", {})

        # Extrair métricas abrangentes
        metrics = extract_comprehensive_metrics(
            results,
            ui_coverage_stats,
            short_term_stats,
            long_term_stats
        )
        metrics["metadata"]["prompt_version"] = prompt_version
        metrics["metadata"]["app_package"] = app_package

        # Salvar resultado individual
        result_file = results_dir / f"{app_package}_{prompt_version}.json"
        with open(result_file, 'w') as f:
            json.dump(metrics, f, indent=2)

        logger.info(f"✅ Test completed successfully")
        logger.info(f"   Actions: {metrics['actions']['total']}")
        logger.info(f"   LLM: {metrics['decisor']['llm_percentage']:.1f}%")
        logger.info(f"   UI Elements: {metrics['ui_coverage']['total_unique_elements']}")
        logger.info(f"   States: {metrics['exploration']['unique_states']}")

        return metrics

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return {
            "metadata": {
                "status": "error",
                "error": str(e),
                "prompt_version": prompt_version,
                "app_package": app_package,
                "timestamp": datetime.now().isoformat()
            }
        }


def generate_comparative_analysis(all_results: Dict[str, List[Dict[str, Any]]], output_dir: Path):
    """
    Gera análise comparativa abrangente entre versões de prompt.

    Análises geradas:
    1. Tabela comparativa geral (médias por versão)
    2. Distribuição de ações por tipo e versão
    3. LLM vs Algoritmo por versão
    4. UI Coverage por categoria e versão
    5. Performance metrics comparison
    6. Rankings (melhor versão por métrica)
    7. Análise estatística (diferenças significativas)
    """

    logger.info("\n" + "="*80)
    logger.info("GENERATING COMPARATIVE ANALYSIS")
    logger.info("="*80 + "\n")

    # Estrutura para agregação
    aggregated = {
        version: {
            "count": 0,
            "actions_total": [],
            "llm_percentage": [],
            "algorithm_percentage": [],
            "unique_elements": [],
            "unique_states": [],
            "tokens_total": [],
            "llm_time_seconds": [],
            "actions_per_minute": [],
            "tokens_per_action": [],
            "ui_coverage_average_interactions": [],
            "action_types": defaultdict(list),
            "discovery_rate": [],
            "interaction_rate": [],
            "short_term_success_rate": [],
            "long_term_success_rate": [],
            "long_term_total_transitions": []
        }
        for version in PROMPT_VERSIONS
    }

    # Agregar dados
    for version, results in all_results.items():
        for result in results:
            if result["metadata"]["status"] != "completed":
                continue

            agg = aggregated[version]
            agg["count"] += 1
            agg["actions_total"].append(result["actions"]["total"])
            agg["llm_percentage"].append(result["decisor"]["llm_percentage"])
            agg["algorithm_percentage"].append(result["decisor"]["algorithm_percentage"])
            agg["unique_elements"].append(result["ui_coverage"]["total_unique_elements"])
            agg["unique_states"].append(result["exploration"]["unique_states"])
            agg["tokens_total"].append(result["llm"]["tokens_total"])
            agg["llm_time_seconds"].append(result["llm"]["time_seconds"])
            agg["actions_per_minute"].append(result["performance"]["actions_per_minute"])
            agg["tokens_per_action"].append(result["performance"]["tokens_per_action"])
            agg["ui_coverage_average_interactions"].append(result["ui_coverage"]["average_interactions_per_element"])
            agg["discovery_rate"].append(result["temporal"]["discovery_rate"])
            agg["interaction_rate"].append(result["temporal"]["interaction_rate"])

            # Memory metrics
            stm_success = result["short_term_memory"]["average_success_rate"] * 100  # Convert to percentage
            ltm_success = result["long_term_memory"]["overall_success_rate"] * 100  # Convert to percentage
            agg["short_term_success_rate"].append(stm_success)
            agg["long_term_success_rate"].append(ltm_success)
            agg["long_term_total_transitions"].append(result["long_term_memory"]["total_transitions"])

            # Action types distribution
            for action_type, count in result["ui_tracker"]["action_distribution"].items():
                agg["action_types"][action_type].append(count)

    # Calcular médias
    def safe_mean(values):
        return sum(values) / len(values) if values else 0.0

    comparison = {}
    for version, agg in aggregated.items():
        if agg["count"] == 0:
            continue

        comparison[version] = {
            "apps_tested": agg["count"],
            "averages": {
                "actions_total": safe_mean(agg["actions_total"]),
                "llm_percentage": safe_mean(agg["llm_percentage"]),
                "algorithm_percentage": safe_mean(agg["algorithm_percentage"]),
                "unique_elements": safe_mean(agg["unique_elements"]),
                "unique_states": safe_mean(agg["unique_states"]),
                "tokens_total": safe_mean(agg["tokens_total"]),
                "llm_time_seconds": safe_mean(agg["llm_time_seconds"]),
                "actions_per_minute": safe_mean(agg["actions_per_minute"]),
                "tokens_per_action": safe_mean(agg["tokens_per_action"]),
                "ui_coverage_average_interactions": safe_mean(agg["ui_coverage_average_interactions"]),
                "discovery_rate": safe_mean(agg["discovery_rate"]),
                "interaction_rate": safe_mean(agg["interaction_rate"]),
                "short_term_success_rate": safe_mean(agg["short_term_success_rate"]),
                "long_term_success_rate": safe_mean(agg["long_term_success_rate"]),
                "long_term_total_transitions": safe_mean(agg["long_term_total_transitions"])
            },
            "action_types_average": {
                action_type: safe_mean(counts)
                for action_type, counts in agg["action_types"].items()
            }
        }

    # Salvar análise comparativa
    comparison_file = output_dir / "comparative_analysis.json"
    with open(comparison_file, 'w') as f:
        json.dump(comparison, f, indent=2)

    # Gerar relatório em markdown
    generate_markdown_report(comparison, output_dir)

    # Gerar rankings
    generate_rankings(comparison, output_dir)

    logger.info(f"✅ Comparative analysis saved to: {comparison_file}")


def generate_markdown_report(comparison: Dict, output_dir: Path):
    """Gera relatório detalhado em Markdown."""

    report_lines = [
        "# Comparative Analysis: V10 vs V11 vs V12",
        "",
        f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Test Duration:** {TEST_CONFIG['timeout']}s per app",
        f"**Apps Tested:** {len(TEST_APPS)}",
        "",
        "## Prompt Versions",
        "",
        "- **V10**: Baseline simplificado",
        "- **V11**: UI Coverage Enhancement (scroll, text fields, spinners, back button)",
        "- **V12**: Permission Handling",
        "",
        "---",
        "",
        "## Overall Comparison",
        "",
        "| Metric | V10 | V11 | V12 | Winner |",
        "|--------|-----|-----|-----|--------|"
    ]

    # Métricas principais para tabela
    metrics_to_compare = [
        ("actions_total", "Total Actions", "higher"),
        ("llm_percentage", "LLM Usage %", "neutral"),
        ("unique_elements", "UI Elements Discovered", "higher"),
        ("unique_states", "Unique States", "higher"),
        ("actions_per_minute", "Actions/Minute", "higher"),
        ("discovery_rate", "Discovery Rate (elem/min)", "higher"),
        ("tokens_per_action", "Tokens/Action", "lower"),
        ("llm_time_seconds", "LLM Time (s)", "lower"),
        ("short_term_success_rate", "STM Success Rate %", "higher"),
        ("long_term_success_rate", "LTM Success Rate %", "higher")
    ]

    for metric_key, metric_name, better in metrics_to_compare:
        values = {}
        for version in ["v10", "v11", "v12"]:
            if version in comparison:
                values[version] = comparison[version]["averages"].get(metric_key, 0.0)

        # Determinar winner
        if better == "higher":
            winner = max(values, key=values.get) if values else "N/A"
        elif better == "lower":
            winner = min(values, key=values.get) if values else "N/A"
        else:
            winner = "N/A"

        v10_val = f"{values.get('v10', 0):.2f}"
        v11_val = f"{values.get('v11', 0):.2f}"
        v12_val = f"{values.get('v12', 0):.2f}"

        report_lines.append(f"| {metric_name} | {v10_val} | {v11_val} | {v12_val} | **{winner}** |")

    report_lines.extend([
        "",
        "---",
        "",
        "## Action Type Distribution",
        "",
        "Average action count by type:",
        ""
    ])

    # Coletar todos os action types
    all_action_types = set()
    for version_data in comparison.values():
        all_action_types.update(version_data["action_types_average"].keys())

    if all_action_types:
        report_lines.append("| Action Type | V10 | V11 | V12 |")
        report_lines.append("|-------------|-----|-----|-----|")

        for action_type in sorted(all_action_types):
            v10 = comparison.get("v10", {}).get("action_types_average", {}).get(action_type, 0)
            v11 = comparison.get("v11", {}).get("action_types_average", {}).get(action_type, 0)
            v12 = comparison.get("v12", {}).get("action_types_average", {}).get(action_type, 0)
            report_lines.append(f"| {action_type} | {v10:.1f} | {v11:.1f} | {v12:.1f} |")

    report_lines.extend([
        "",
        "---",
        "",
        "## Detailed Insights",
        "",
        "### LLM vs Algorithm Decision Making",
        ""
    ])

    for version in ["v10", "v11", "v12"]:
        if version in comparison:
            llm_pct = comparison[version]["averages"]["llm_percentage"]
            alg_pct = comparison[version]["averages"]["algorithm_percentage"]
            report_lines.append(f"**{version.upper()}**: LLM={llm_pct:.1f}% | Algorithm={alg_pct:.1f}%")

    report_lines.extend([
        "",
        "### UI Coverage Performance",
        ""
    ])

    for version in ["v10", "v11", "v12"]:
        if version in comparison:
            elements = comparison[version]["averages"]["unique_elements"]
            discovery = comparison[version]["averages"]["discovery_rate"]
            interactions = comparison[version]["averages"]["ui_coverage_average_interactions"]
            report_lines.append(
                f"**{version.upper()}**: {elements:.1f} elements discovered | "
                f"{discovery:.2f} elem/min | {interactions:.2f} interactions/element"
            )

    report_lines.extend([
        "",
        "### Memory System Performance",
        ""
    ])

    for version in ["v10", "v11", "v12"]:
        if version in comparison:
            stm_success = comparison[version]["averages"]["short_term_success_rate"]
            ltm_success = comparison[version]["averages"]["long_term_success_rate"]
            ltm_transitions = comparison[version]["averages"]["long_term_total_transitions"]
            report_lines.append(
                f"**{version.upper()}**: STM success={stm_success:.1f}% | "
                f"LTM success={ltm_success:.1f}% | "
                f"Transitions={ltm_transitions:.1f}"
            )

    report_lines.extend([
        "",
        "---",
        "",
        "## Recommendations",
        "",
        "Based on the comparative analysis:",
        ""
    ])

    # Determinar recomendações baseadas nas métricas
    # (Lógica simplificada - pode ser expandida)
    report_lines.extend([
        "- **For Maximum Coverage**: Use the version with highest unique_elements and discovery_rate",
        "- **For Efficiency**: Use the version with best actions_per_minute and lowest tokens_per_action",
        "- **For Balanced Approach**: Consider LLM usage % and overall action distribution",
        "",
        "---",
        "",
        f"*Report generated: {datetime.now().isoformat()}*"
    ])

    # Salvar relatório
    report_file = output_dir / "comparative_report.md"
    with open(report_file, 'w') as f:
        f.write('\n'.join(report_lines))

    logger.info(f"✅ Markdown report saved to: {report_file}")


def generate_rankings(comparison: Dict, output_dir: Path):
    """Gera rankings das versões por métrica."""

    rankings = {}

    metrics_to_rank = [
        ("actions_total", "higher"),
        ("unique_elements", "higher"),
        ("unique_states", "higher"),
        ("actions_per_minute", "higher"),
        ("discovery_rate", "higher"),
        ("tokens_per_action", "lower"),
        ("llm_time_seconds", "lower"),
        ("short_term_success_rate", "higher"),
        ("long_term_success_rate", "higher"),
        ("long_term_total_transitions", "higher")
    ]

    for metric_key, direction in metrics_to_rank:
        values = []
        for version in ["v10", "v11", "v12"]:
            if version in comparison:
                value = comparison[version]["averages"].get(metric_key, 0.0)
                values.append((version, value))

        # Ordenar
        reverse = (direction == "higher")
        values.sort(key=lambda x: x[1], reverse=reverse)

        rankings[metric_key] = [
            {"rank": i+1, "version": v, "value": val}
            for i, (v, val) in enumerate(values)
        ]

    # Salvar rankings
    rankings_file = output_dir / "rankings.json"
    with open(rankings_file, 'w') as f:
        json.dump(rankings, f, indent=2)

    logger.info(f"✅ Rankings saved to: {rankings_file}")


def main():
    """Executa teste comparativo completo."""

    print("\n" + "="*80)
    print("PROMPT COMPARISON TEST: V10 vs V11 vs V12")
    print("="*80)
    print()

    # Descobrir APKs no dataset
    logger.info("Discovering APKs in dataset...")
    apks = discover_apks()

    if not apks:
        logger.error("No APKs found in dataset directory")
        return 1

    logger.info(f"Found {len(apks)} APKs to test")

    print(f"\nConfiguration:")
    print(f"  - Dataset: {DATASET_DIR}")
    print(f"  - Timeout: {TEST_CONFIG['timeout']}s per app")
    print(f"  - Apps: {len(apks)} apps")
    print(f"  - Prompt versions: {', '.join(PROMPT_VERSIONS)}")
    print(f"  - Total tests: {len(apks) * len(PROMPT_VERSIONS)}")
    print(f"  - Estimated duration: ~{(len(apks) * len(PROMPT_VERSIONS) * TEST_CONFIG['timeout']) / 60:.0f} minutes ({(len(apks) * len(PROMPT_VERSIONS) * TEST_CONFIG['timeout']) / 3600:.1f} hours)")
    print()

    # Criar diretório de resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_base_dir = Path(f"results/prompt_comparison_{timestamp}")
    results_base_dir.mkdir(parents=True, exist_ok=True)

    # Armazenar todos os resultados
    all_results = {version: [] for version in PROMPT_VERSIONS}

    # Executar testes
    test_count = 0
    total_tests = len(apks) * len(PROMPT_VERSIONS)

    for apk_info in apks:
        for prompt_version in PROMPT_VERSIONS:
            test_count += 1

            logger.info(f"\n{'='*80}")
            logger.info(f"Test {test_count}/{total_tests}")
            logger.info(f"App: {apk_info['package']}")
            logger.info(f"APK: {apk_info['app_dir']}")
            logger.info(f"Prompt: {prompt_version}")
            logger.info(f"{'='*80}")

            # Instalar APK
            if not install_apk(apk_info['apk_path'], apk_info['package']):
                logger.error(f"⚠️  Skipping {apk_info['package']} - installation failed")

                # Registrar falha de instalação
                all_results[prompt_version].append({
                    "metadata": {
                        "status": "install_failed",
                        "error": "APK installation failed",
                        "prompt_version": prompt_version,
                        "app_package": apk_info['package'],
                        "timestamp": datetime.now().isoformat()
                    }
                })

                # Salvar progresso intermediário
                save_progress_file = results_base_dir / "progress.json"
                with open(save_progress_file, 'w') as f:
                    json.dump(all_results, f, indent=2)

                continue

            # Criar subdiretório por versão
            version_dir = results_base_dir / f"{prompt_version}_results"
            version_dir.mkdir(exist_ok=True)

            # Executar teste
            result = run_single_test(
                apk_info['package'],
                prompt_version,
                version_dir,
                apk_info['apk_path']
            )
            all_results[prompt_version].append(result)

            # Salvar progresso intermediário
            save_progress_file = results_base_dir / "progress.json"
            with open(save_progress_file, 'w') as f:
                json.dump(all_results, f, indent=2)

            # Mostrar estatísticas de progresso
            completed = sum(
                1 for v_results in all_results.values()
                for r in v_results
                if r.get("metadata", {}).get("status") == "completed"
            )
            failed = sum(
                1 for v_results in all_results.values()
                for r in v_results
                if r.get("metadata", {}).get("status") in ["error", "install_failed"]
            )

            logger.info(f"Progress: {completed} completed, {failed} failed, {test_count}/{total_tests} total")

            # Pequena pausa entre testes
            time.sleep(2)

    # Gerar análise comparativa
    generate_comparative_analysis(all_results, results_base_dir)

    print("\n" + "="*80)
    print("✅ COMPARATIVE TEST COMPLETED")
    print("="*80)
    print(f"\nResults saved to: {results_base_dir}")
    print("\nGenerated files:")
    print(f"  - comparative_analysis.json")
    print(f"  - comparative_report.md")
    print(f"  - rankings.json")
    print(f"  - progress.json (intermediate progress)")
    print(f"  - Individual results in v10_results/, v11_results/, v12_results/")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
