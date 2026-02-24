"""
LaTeX table generation for experiment results.
"""

from pathlib import Path
from typing import Any, Dict, List


class LaTeXExporter:
    """
    Exports experiment results to LaTeX tables.
    """

    @staticmethod
    def export_summary_table(
        summary_by_strategy: Dict[str, Dict[str, Dict[str, float]]],
        output_path: Path,
        metrics: List[str],
        caption: str = "Summary statistics by strategy",
        label: str = "tab:summary",
    ) -> Path:
        """
        Export summary statistics to LaTeX table.

        Args:
            summary_by_strategy: Summary statistics by strategy.
            output_path: Output file path.
            metrics: List of metrics.
            caption: Table caption.
            label: Table label for references.

        Returns:
            Path to output file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build table
        lines = [
            r"\begin{table}[htbp]",
            r"\centering",
            f"\\caption{{{caption}}}",
            f"\\label{{{label}}}",
        ]

        # Column specification
        n_cols = 1 + len(metrics) * 2  # strategy + (mean, std) per metric
        col_spec = "l" + "rr" * len(metrics)
        lines.append(f"\\begin{{tabular}}{{{col_spec}}}")
        lines.append(r"\toprule")

        # Header row
        header_parts = ["Strategy"]
        for metric in metrics:
            header_parts.append(
                f"\\multicolumn{{2}}{{c}}{{{LaTeXExporter._format_metric_name(metric)}}}"
            )
        lines.append(" & ".join(header_parts) + r" \\")

        # Subheader row
        subheader_parts = [""]
        for _ in metrics:
            subheader_parts.extend(["Mean", "Std"])
        lines.append(" & ".join(subheader_parts) + r" \\")
        lines.append(r"\midrule")

        # Data rows
        for strategy, strategy_stats in summary_by_strategy.items():
            row_parts = [LaTeXExporter._format_strategy_name(strategy)]
            for metric in metrics:
                if metric in strategy_stats:
                    stats = strategy_stats[metric]
                    mean = stats.get("mean", 0)
                    std = stats.get("std", 0)
                    row_parts.append(f"{mean:.2f}")
                    row_parts.append(f"{std:.2f}")
                else:
                    row_parts.extend(["--", "--"])
            lines.append(" & ".join(row_parts) + r" \\")

        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        return output_path

    @staticmethod
    def export_significance_table(
        pairwise_results: List[Dict[str, Any]],
        output_path: Path,
        caption: str = "Pairwise significance tests (Wilcoxon)",
        label: str = "tab:significance",
    ) -> Path:
        """
        Export significance test results to LaTeX table.

        Args:
            pairwise_results: List of pairwise test results.
            output_path: Output file path.
            caption: Table caption.
            label: Table label.

        Returns:
            Path to output file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            r"\begin{table}[htbp]",
            r"\centering",
            f"\\caption{{{caption}}}",
            f"\\label{{{label}}}",
            r"\begin{tabular}{lrrcc}",
            r"\toprule",
            r"Comparison & $p$-value & Cliff's $\delta$ & Sig. & Sig. (Bonf.) \\",
            r"\midrule",
        ]

        for result in pairwise_results:
            comparison = result.get("comparison", "")
            p_value = result.get("p_value", 1.0)
            cliff_delta = result.get("cliff_delta", 0.0)
            significant = result.get("significant", False)
            significant_bonf = result.get("significant_bonferroni", False)

            # Format comparison name
            comp_formatted = comparison.replace("_vs_", " vs ")
            comp_formatted = LaTeXExporter._format_strategy_name(comp_formatted)

            # Format p-value
            if p_value < 0.001:
                p_str = "$<$0.001"
            else:
                p_str = f"{p_value:.3f}"

            # Format significance markers
            sig_str = r"\checkmark" if significant else "--"
            sig_bonf_str = r"\checkmark" if significant_bonf else "--"

            row = f"{comp_formatted} & {p_str} & {cliff_delta:.3f} & {sig_str} & {sig_bonf_str} \\\\"
            lines.append(row)

        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        return output_path

    @staticmethod
    def export_effect_size_matrix(
        effect_matrix: Dict[str, Dict[str, float]],
        strategies: List[str],
        output_path: Path,
        caption: str = "Cliff's Delta effect size matrix",
        label: str = "tab:effect_size",
    ) -> Path:
        """
        Export effect size matrix to LaTeX table.

        Args:
            effect_matrix: Effect size matrix.
            strategies: List of strategies.
            output_path: Output file path.
            caption: Table caption.
            label: Table label.

        Returns:
            Path to output file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        n_strategies = len(strategies)
        col_spec = "l" + "r" * n_strategies

        lines = [
            r"\begin{table}[htbp]",
            r"\centering",
            f"\\caption{{{caption}}}",
            f"\\label{{{label}}}",
            f"\\begin{{tabular}}{{{col_spec}}}",
            r"\toprule",
        ]

        # Header row
        header = [""] + [LaTeXExporter._format_strategy_name(s) for s in strategies]
        lines.append(" & ".join(header) + r" \\")
        lines.append(r"\midrule")

        # Data rows
        for s1 in strategies:
            row_parts = [LaTeXExporter._format_strategy_name(s1)]
            for s2 in strategies:
                if s1 == s2:
                    row_parts.append("--")
                else:
                    delta = effect_matrix.get(s1, {}).get(s2, 0.0)
                    row_parts.append(f"{delta:.3f}")
            lines.append(" & ".join(row_parts) + r" \\")

        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        return output_path

    @staticmethod
    def _format_metric_name(metric: str) -> str:
        """Format metric name for display."""
        replacements = {
            "coverage": "Coverage",
            "states_explored": "States",
            "actions_executed": "Actions",
            "mop_events": "MOP Events",
            "app_crashes": "Crashes",
            "unique_activities": "Activities",
        }
        return replacements.get(metric, metric.replace("_", " ").title())

    @staticmethod
    def _format_strategy_name(strategy: str) -> str:
        """Format strategy name for display."""
        replacements = {
            "rvagent": "RVAgent",
            "dfs": "DFS",
            "bfs": "BFS",
            "greedy": "Greedy",
        }
        # Handle composite names like "dfs vs bfs"
        parts = strategy.split(" vs ")
        if len(parts) == 2:
            return f"{replacements.get(parts[0], parts[0])} vs {replacements.get(parts[1], parts[1])}"
        return replacements.get(strategy, strategy)
