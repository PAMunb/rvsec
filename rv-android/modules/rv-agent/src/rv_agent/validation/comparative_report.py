"""
Comparative report generator for multi-app validation results.

Aggregates metrics from multiple app validations and generates
comparative analysis reports.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AppElementCoverage:
    """Element type coverage for a single app."""
    app_name: str
    element_types: List[str]
    element_counts: Dict[str, int]


@dataclass
class ComparativeMetrics:
    """Aggregated metrics across multiple apps."""

    # App metadata
    total_apps: int = 0
    app_names: List[str] = field(default_factory=list)

    # Element coverage across all apps
    all_element_types: set = field(default_factory=set)
    element_frequency: Dict[str, int] = field(default_factory=dict)  # How many apps have each type

    # Per-app coverage
    app_coverages: List[AppElementCoverage] = field(default_factory=list)

    # Action distribution across all apps
    total_actions: int = 0
    action_distribution: Dict[str, int] = field(default_factory=dict)

    # Validation metrics
    total_valid_actions: int = 0
    total_invalid_actions: int = 0

    # LLM metrics
    total_tokens: int = 0
    total_llm_time_ms: float = 0.0

    # Exploration metrics
    total_screens: int = 0
    total_activities: int = 0


class ComparativeReportGenerator:
    """
    Generates comparative reports from multi-app validation results.

    Analyzes and compares metrics across multiple app validations to identify
    patterns, coverage gaps, and systematic issues.
    """

    def __init__(self, results_dir: Path):
        """
        Initialize report generator.

        Args:
            results_dir: Directory containing validation result JSON files
        """
        self.results_dir = Path(results_dir)
        self.app_results: Dict[str, dict] = {}

    def load_results(self, pattern: str = "*_validation.json") -> int:
        """
        Load all validation results from directory.

        Args:
            pattern: Glob pattern for result files

        Returns:
            Number of results loaded
        """
        result_files = list(self.results_dir.glob(pattern))
        logger.info(f"Found {len(result_files)} result files matching '{pattern}'")

        for result_file in result_files:
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    app_name = data.get('app_name', result_file.stem)
                    self.app_results[app_name] = data
                    logger.info(f"  Loaded: {app_name}")
            except Exception as e:
                logger.error(f"  Failed to load {result_file}: {e}")

        return len(self.app_results)

    def aggregate_metrics(self) -> ComparativeMetrics:
        """
        Aggregate metrics across all loaded results.

        Returns:
            ComparativeMetrics with aggregated data
        """
        metrics = ComparativeMetrics()
        metrics.total_apps = len(self.app_results)
        metrics.app_names = list(self.app_results.keys())

        # Element type tracking per app
        element_type_apps = defaultdict(set)  # element_type -> set of apps

        for app_name, result in self.app_results.items():
            # Element coverage
            element_data = result.get('element_coverage', {})
            types_seen = element_data.get('types_seen', [])
            type_counts = element_data.get('type_counts', {})

            # Track which apps have which types
            for elem_type in types_seen:
                metrics.all_element_types.add(elem_type)
                element_type_apps[elem_type].add(app_name)

            # Store per-app coverage
            metrics.app_coverages.append(AppElementCoverage(
                app_name=app_name,
                element_types=types_seen,
                element_counts=type_counts
            ))

            # Action distribution
            actions = result.get('actions', {})
            for action_type, count in actions.get('by_type', {}).items():
                metrics.action_distribution[action_type] = \
                    metrics.action_distribution.get(action_type, 0) + count
            metrics.total_actions += sum(actions.get('by_type', {}).values())
            metrics.total_valid_actions += actions.get('valid', 0)
            metrics.total_invalid_actions += actions.get('invalid', 0)

            # LLM metrics
            llm = result.get('llm', {})
            metrics.total_tokens += llm.get('total_tokens', 0)
            metrics.total_llm_time_ms += llm.get('total_time_ms', 0.0)

            # Exploration metrics
            exploration = result.get('exploration', {})
            metrics.total_screens += exploration.get('unique_screens', 0)
            metrics.total_activities += len(exploration.get('activities', []))

        # Calculate element frequency (how many apps have each type)
        for elem_type, apps in element_type_apps.items():
            metrics.element_frequency[elem_type] = len(apps)

        return metrics

    def generate_markdown_report(self, output_path: Path, metrics: ComparativeMetrics):
        """
        Generate markdown comparative report.

        Args:
            output_path: Path to save markdown report
            metrics: Aggregated metrics
        """
        lines = []

        # Header
        lines.append("# RVAgent Multi-App Validation Report")
        lines.append("")
        lines.append(f"**Total Apps**: {metrics.total_apps}")
        lines.append(f"**Apps**: {', '.join(sorted(metrics.app_names))}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Element Type Coverage
        lines.append("## 📊 Element Type Coverage")
        lines.append("")
        lines.append(f"**Total element types discovered**: {len(metrics.all_element_types)}")
        lines.append("")
        lines.append("### Element Types by Frequency")
        lines.append("")
        lines.append("| Element Type | Apps with Type | Frequency % |")
        lines.append("|--------------|----------------|-------------|")

        sorted_types = sorted(metrics.element_frequency.items(),
                             key=lambda x: x[1], reverse=True)
        for elem_type, app_count in sorted_types:
            frequency_pct = (app_count / metrics.total_apps * 100) if metrics.total_apps > 0 else 0
            lines.append(f"| {elem_type} | {app_count}/{metrics.total_apps} | {frequency_pct:.1f}% |")

        lines.append("")

        # Critical Element Types Analysis
        lines.append("### Critical Element Types")
        lines.append("")

        critical_types = {
            'Spinner': 'Combobox/Dropdown',
            'EditText': 'Input Field',
            'RadioButton': 'Radio Button',
            'CheckBox': 'Checkbox',
            'Switch': 'Switch/Toggle',
            'ImageView': 'Image',
            'ImageButton': 'Image Button',
            'CheckedTextView': 'List Item',
            'ListView': 'List View',
            'RecyclerView': 'Recycler View'
        }

        for elem_type, description in critical_types.items():
            app_count = metrics.element_frequency.get(elem_type, 0)
            if app_count > 0:
                status = "✅"
                apps_with = [cov.app_name for cov in metrics.app_coverages
                            if elem_type in cov.element_types]
                apps_str = f"Found in: {', '.join(apps_with)}"
            else:
                status = "❌"
                apps_str = "Not found in any app"

            lines.append(f"- **{elem_type}** ({description}): {status} {app_count}/{metrics.total_apps} apps")
            lines.append(f"  - {apps_str}")

        lines.append("")
        lines.append("---")
        lines.append("")

        # Action Distribution
        lines.append("## 🎯 Action Distribution (All Apps)")
        lines.append("")
        lines.append(f"**Total actions**: {metrics.total_actions}")
        lines.append("")
        lines.append("| Action Type | Count | Percentage |")
        lines.append("|-------------|-------|------------|")

        sorted_actions = sorted(metrics.action_distribution.items(),
                               key=lambda x: x[1], reverse=True)
        for action_type, count in sorted_actions:
            pct = (count / metrics.total_actions * 100) if metrics.total_actions > 0 else 0
            lines.append(f"| {action_type} | {count} | {pct:.1f}% |")

        lines.append("")

        # Action validity
        total_actions_validated = metrics.total_valid_actions + metrics.total_invalid_actions
        if total_actions_validated > 0:
            valid_rate = (metrics.total_valid_actions / total_actions_validated * 100)
            lines.append(f"**Validation**: {metrics.total_valid_actions}/{total_actions_validated} valid ({valid_rate:.1f}%)")
            lines.append("")

        # Critical issues
        lines.append("### ⚠️ Critical Issues")
        lines.append("")

        type_text_count = metrics.action_distribution.get('TYPE_TEXT', 0)
        type_text_pct = (type_text_count / metrics.total_actions * 100) if metrics.total_actions > 0 else 0

        if type_text_pct < 5:
            lines.append(f"- **TYPE_TEXT usage very low**: {type_text_count} actions ({type_text_pct:.1f}%)")
            edittext_apps = [cov.app_name for cov in metrics.app_coverages if 'EditText' in cov.element_types]
            if edittext_apps:
                lines.append(f"  - EditText found in {len(edittext_apps)} apps: {', '.join(edittext_apps)}")
                lines.append("  - **Agent is not typing into input fields!**")

        click_pct = (metrics.action_distribution.get('CLICK', 0) / metrics.total_actions * 100) if metrics.total_actions > 0 else 0
        if click_pct > 90:
            lines.append(f"- **CLICK dominance**: {click_pct:.1f}% of all actions are clicks")
            lines.append("  - Agent is not using action diversity")

        lines.append("")
        lines.append("---")
        lines.append("")

        # LLM Metrics
        lines.append("## 🤖 LLM Usage Metrics")
        lines.append("")

        if metrics.total_tokens > 0:
            avg_tokens_per_app = metrics.total_tokens / metrics.total_apps if metrics.total_apps > 0 else 0
            avg_tokens_per_action = metrics.total_tokens / metrics.total_actions if metrics.total_actions > 0 else 0

            lines.append(f"- **Total tokens**: {metrics.total_tokens:,}")
            lines.append(f"- **Avg tokens per app**: {avg_tokens_per_app:,.0f}")
            lines.append(f"- **Avg tokens per action**: {avg_tokens_per_action:,.1f}")
        else:
            lines.append("- **Token tracking**: Not available (0 tokens recorded)")

        if metrics.total_llm_time_ms > 0:
            avg_time_per_app = metrics.total_llm_time_ms / metrics.total_apps if metrics.total_apps > 0 else 0
            avg_time_per_action = metrics.total_llm_time_ms / metrics.total_actions if metrics.total_actions > 0 else 0

            lines.append(f"- **Total LLM time**: {metrics.total_llm_time_ms / 1000:.1f}s")
            lines.append(f"- **Avg time per app**: {avg_time_per_app / 1000:.1f}s")
            lines.append(f"- **Avg time per action**: {avg_time_per_action:.0f}ms")

        lines.append("")
        lines.append("---")
        lines.append("")

        # Exploration Metrics
        lines.append("## 🗺️ Exploration Metrics")
        lines.append("")

        avg_screens = metrics.total_screens / metrics.total_apps if metrics.total_apps > 0 else 0
        avg_activities = metrics.total_activities / metrics.total_apps if metrics.total_apps > 0 else 0

        lines.append(f"- **Total unique screens**: {metrics.total_screens}")
        lines.append(f"- **Avg screens per app**: {avg_screens:.1f}")
        lines.append(f"- **Total activities**: {metrics.total_activities}")
        lines.append(f"- **Avg activities per app**: {avg_activities:.1f}")
        lines.append("")

        # Per-app breakdown
        lines.append("### Per-App Breakdown")
        lines.append("")
        lines.append("| App | Screens | Activities | Element Types |")
        lines.append("|-----|---------|------------|---------------|")

        for app_name, result in sorted(self.app_results.items()):
            exploration = result.get('exploration', {})
            element_coverage = result.get('element_coverage', {})

            screens = exploration.get('unique_screens', 0)
            activities = len(exploration.get('activities', []))
            elem_types = len(element_coverage.get('types_seen', []))

            lines.append(f"| {app_name} | {screens} | {activities} | {elem_types} |")

        lines.append("")
        lines.append("---")
        lines.append("")

        # Recommendations
        lines.append("## 💡 Recommendations")
        lines.append("")
        lines.append("### Immediate Actions")
        lines.append("")

        if type_text_pct < 5:
            lines.append("1. **Fix TYPE_TEXT usage**: Agent is not typing into EditText fields")
            lines.append("   - Review prompts to encourage text input actions")
            lines.append("   - Add explicit examples of TYPE_TEXT usage")
            lines.append("   - Test with apps that require text input")

        if click_pct > 90:
            lines.append("2. **Increase action diversity**: Agent is over-reliant on CLICK")
            lines.append("   - Enable LONG_CLICK, BACK, HOME actions")
            lines.append("   - Adjust exploration strategy to try different action types")

        if metrics.total_tokens == 0:
            lines.append("3. **Enable token tracking**: Token metrics are not being captured")
            lines.append("   - Verify LangSmith integration or metadata extraction")
            lines.append("   - Important for context growth analysis")

        lines.append("")

        # Write report
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))

        logger.info(f"✅ Markdown report saved to: {output_path}")

    def generate_csv_report(self, output_path: Path):
        """
        Generate CSV report with per-app metrics.

        Args:
            output_path: Path to save CSV report
        """
        import csv

        with open(output_path, 'w', newline='') as f:
            # Define columns
            fieldnames = [
                'app_name',
                'total_iterations',
                'execution_time_s',
                'unique_screens',
                'activities_count',
                'element_types_count',
                'total_actions',
                'valid_actions',
                'invalid_actions',
                'valid_rate',
                'click_count',
                'type_text_count',
                'long_click_count',
                'back_count',
                'home_count',
                'total_tokens',
                'avg_tokens_per_iteration',
                'avg_llm_time_ms',
                'has_spinner',
                'has_edittext',
                'has_radiobutton',
                'has_checkbox',
                'has_imageview'
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for app_name, result in sorted(self.app_results.items()):
                # Extract metrics
                actions = result.get('actions', {})
                by_type = actions.get('by_type', {})
                exploration = result.get('exploration', {})
                element_coverage = result.get('element_coverage', {})
                types_seen = element_coverage.get('types_seen', [])
                llm = result.get('llm', {})

                row = {
                    'app_name': app_name,
                    'total_iterations': result.get('total_iterations', 0),
                    'execution_time_s': result.get('execution_time_s', 0.0),
                    'unique_screens': exploration.get('unique_screens', 0),
                    'activities_count': len(exploration.get('activities', [])),
                    'element_types_count': len(types_seen),
                    'total_actions': sum(by_type.values()),
                    'valid_actions': actions.get('valid', 0),
                    'invalid_actions': actions.get('invalid', 0),
                    'valid_rate': actions.get('valid_rate', 0.0),
                    'click_count': by_type.get('CLICK', 0),
                    'type_text_count': by_type.get('TYPE_TEXT', 0),
                    'long_click_count': by_type.get('LONG_CLICK', 0),
                    'back_count': by_type.get('BACK', 0),
                    'home_count': by_type.get('HOME', 0),
                    'total_tokens': llm.get('total_tokens', 0),
                    'avg_tokens_per_iteration': llm.get('avg_tokens_per_iteration', 0.0),
                    'avg_llm_time_ms': llm.get('avg_time_per_iteration_ms', 0.0),
                    'has_spinner': 'Spinner' in types_seen,
                    'has_edittext': 'EditText' in types_seen,
                    'has_radiobutton': 'RadioButton' in types_seen,
                    'has_checkbox': 'CheckBox' in types_seen,
                    'has_imageview': 'ImageView' in types_seen
                }

                writer.writerow(row)

        logger.info(f"✅ CSV report saved to: {output_path}")
