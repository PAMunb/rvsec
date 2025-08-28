#!/usr/bin/env python3
"""
Report generator for vision model benchmark results.
Creates comprehensive analysis reports and visualizations.
"""

import json
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np

from benchmark_framework import TestResult, ModelPerformance
from model_config import AVAILABLE_MODELS, TEST_SCENARIOS

class BenchmarkReportGenerator:
    """Generate comprehensive reports from benchmark results."""
    
    def __init__(self, performances: Dict[str, ModelPerformance], results: List[TestResult]):
        self.performances = performances
        self.results = results
        
        # Configure plotting style
        plt.style.use('default')
        sns.set_palette("husl")
    
    def generate_summary_report(self, output_file: str) -> None:
        """Generate executive summary report."""
        
        report_lines = [
            "# Vision Model Benchmark - Summary Report",
            "",
            f"**Total Models Tested**: {len(self.performances)}",
            f"**Total Test Executions**: {len(self.results)}",
            f"**Test Scenarios**: {len(set(r.scenario for r in self.results))}",
            "",
            "## Executive Summary",
            ""
        ]
        
        if not self.performances:
            report_lines.append("No successful benchmark results to analyze.")
            self._write_report(output_file, report_lines)
            return
        
        # Overall performance ranking
        ranked_models = sorted(
            self.performances.items(),
            key=lambda x: (x[1].overall_success_rate, -x[1].avg_distance),
            reverse=True
        )
        
        report_lines.extend([
            "### 🏆 Model Performance Ranking",
            "",
            "| Rank | Model | Success Rate | Avg Distance | Hit Rate | Response Time |",
            "|------|-------|--------------|--------------|----------|---------------|"
        ])
        
        for i, (name, perf) in enumerate(ranked_models, 1):
            report_lines.append(
                f"| {i} | **{name}** | {perf.overall_success_rate*100:.1f}% | "
                f"{perf.avg_distance:.1f}px | {perf.hit_rate*100:.1f}% | {perf.avg_response_time:.2f}s |"
            )
        
        # Best model in each category
        best_success = max(self.performances.items(), key=lambda x: x[1].overall_success_rate)
        best_accuracy = min(self.performances.items(), key=lambda x: x[1].avg_distance)
        best_speed = min(self.performances.items(), key=lambda x: x[1].avg_response_time)
        
        report_lines.extend([
            "",
            "### 🎯 Category Leaders",
            "",
            f"- **Highest Success Rate**: {best_success[0]} ({best_success[1].overall_success_rate*100:.1f}%)",
            f"- **Best Accuracy**: {best_accuracy[0]} ({best_accuracy[1].avg_distance:.1f}px avg distance)",
            f"- **Fastest Response**: {best_speed[0]} ({best_speed[1].avg_response_time:.2f}s avg)",
            ""
        ])
        
        # Scenario performance summary
        scenarios = set(r.scenario for r in self.results)
        report_lines.extend([
            "### 📊 Performance by Scenario",
            ""
        ])
        
        for scenario in scenarios:
            scenario_results = [r for r in self.results if r.scenario == scenario]
            if scenario_results:
                success_rate = np.mean([r.overall_success for r in scenario_results])
                report_lines.append(f"- **{scenario}**: {success_rate*100:.1f}% average success rate")
        
        # Key insights
        report_lines.extend([
            "",
            "### 💡 Key Insights",
            ""
        ])
        
        # Analyze results for insights
        insights = self._generate_insights()
        for insight in insights:
            report_lines.append(f"- {insight}")
        
        self._write_report(output_file, report_lines)
    
    def generate_detailed_report(self, output_file: str) -> None:
        """Generate detailed analysis report."""
        
        report_lines = [
            "# Vision Model Benchmark - Detailed Analysis",
            "",
            "## Model Configurations",
            ""
        ]
        
        # Model details
        for model_name in self.performances.keys():
            if model_name in AVAILABLE_MODELS:
                config = AVAILABLE_MODELS[model_name]
                perf = self.performances[model_name]
                
                report_lines.extend([
                    f"### {config.full_name}",
                    "",
                    f"- **Model ID**: `{model_name}`",
                    f"- **Family**: {config.family}",
                    f"- **Size**: {config.size}",
                    f"- **Temperature**: {config.temperature}",
                    f"- **Max Tokens**: {config.max_tokens}",
                    "",
                    "**Performance Summary**:",
                    f"- Overall Success Rate: {perf.overall_success_rate*100:.1f}%",
                    f"- Parsing Success: {perf.parsing_success_rate*100:.1f}%",
                    f"- Coordinate Success: {perf.coordinate_success_rate*100:.1f}%",
                    f"- Average Distance: {perf.avg_distance:.1f}px",
                    f"- Hit Rate: {perf.hit_rate*100:.1f}%",
                    f"- Response Time: {perf.avg_response_time:.2f}s",
                    ""
                ])
                
                # Scenario breakdown
                if perf.scenario_performance:
                    report_lines.extend([
                        "**Performance by Scenario**:",
                        ""
                    ])
                    
                    for scenario, metrics in perf.scenario_performance.items():
                        report_lines.extend([
                            f"- **{scenario}**:",
                            f"  - Success: {metrics['success_rate']*100:.1f}%",
                            f"  - Distance: {metrics['avg_distance']:.1f}px",
                            f"  - Hit Rate: {metrics['hit_rate']*100:.1f}%",
                            ""
                        ])
                
                # Known limitations and strengths
                if config.known_limitations:
                    report_lines.extend([
                        "**Known Limitations**:",
                        ""
                    ])
                    for limitation in config.known_limitations:
                        report_lines.append(f"- {limitation}")
                    report_lines.append("")
                
                if config.strengths:
                    report_lines.extend([
                        "**Strengths**:",
                        ""
                    ])
                    for strength in config.strengths:
                        report_lines.append(f"- {strength}")
                    report_lines.append("")
                
                report_lines.append("---")
                report_lines.append("")
        
        self._write_report(output_file, report_lines)
    
    def generate_comparison_tables(self, output_file: str) -> None:
        """Generate comparison tables and charts."""
        
        report_lines = [
            "# Vision Model Benchmark - Comparison Tables",
            "",
            "## Overall Performance Comparison",
            "",
            "| Model | Family | Size | Success Rate | Avg Distance | Hit Rate | Speed |",
            "|-------|--------|------|--------------|--------------|----------|-------|"
        ]
        
        # Sort by success rate
        sorted_models = sorted(
            self.performances.items(),
            key=lambda x: x[1].overall_success_rate,
            reverse=True
        )
        
        for name, perf in sorted_models:
            config = AVAILABLE_MODELS.get(name, None)
            family = config.family if config else "unknown"
            size = config.size if config else "unknown"
            
            report_lines.append(
                f"| {name} | {family} | {size} | {perf.overall_success_rate*100:.1f}% | "
                f"{perf.avg_distance:.1f}px | {perf.hit_rate*100:.1f}% | {perf.avg_response_time:.2f}s |"
            )
        
        # Performance by family
        families = {}
        for name, perf in self.performances.items():
            config = AVAILABLE_MODELS.get(name)
            if config:
                if config.family not in families:
                    families[config.family] = []
                families[config.family].append(perf)
        
        if len(families) > 1:
            report_lines.extend([
                "",
                "## Performance by Model Family",
                "",
                "| Family | Models | Avg Success | Avg Distance | Avg Speed |",
                "|--------|--------|-------------|--------------|-----------|"
            ])
            
            for family, perfs in families.items():
                avg_success = np.mean([p.overall_success_rate for p in perfs])
                avg_distance = np.mean([p.avg_distance for p in perfs])
                avg_speed = np.mean([p.avg_response_time for p in perfs])
                
                report_lines.append(
                    f"| {family} | {len(perfs)} | {avg_success*100:.1f}% | "
                    f"{avg_distance:.1f}px | {avg_speed:.2f}s |"
                )
        
        # Performance by scenario
        scenarios = set(r.scenario for r in self.results)
        if len(scenarios) > 1:
            report_lines.extend([
                "",
                "## Performance by Scenario",
                "",
                "| Model | " + " | ".join(scenarios) + " |",
                "|-------|" + "|".join(["---"] * len(scenarios)) + "|"
            ])
            
            for name, perf in sorted_models:
                row = f"| {name} |"
                for scenario in scenarios:
                    if scenario in perf.scenario_performance:
                        success = perf.scenario_performance[scenario]['success_rate']
                        row += f" {success*100:.1f}% |"
                    else:
                        row += " - |"
                report_lines.append(row)
        
        self._write_report(output_file, report_lines)
    
    def generate_head_to_head_report(self, model1: str, model2: str, output_file: str) -> None:
        """Generate detailed head-to-head comparison report."""
        
        if model1 not in self.performances or model2 not in self.performances:
            print(f"Missing performance data for comparison")
            return
        
        perf1 = self.performances[model1]
        perf2 = self.performances[model2]
        
        report_lines = [
            f"# Head-to-Head Comparison: {model1} vs {model2}",
            "",
            "## Model Overview",
            ""
        ]
        
        # Model details
        for model_name in [model1, model2]:
            config = AVAILABLE_MODELS.get(model_name)
            if config:
                report_lines.extend([
                    f"### {config.full_name}",
                    f"- Family: {config.family}",
                    f"- Size: {config.size}",
                    f"- Temperature: {config.temperature}",
                    ""
                ])
        
        # Direct comparison
        report_lines.extend([
            "## Performance Comparison",
            "",
            "| Metric | " + model1 + " | " + model2 + " | Winner |",
            "|--------|" + "---|" * 3 + "|"
        ])
        
        metrics = [
            ("Overall Success", perf1.overall_success_rate, perf2.overall_success_rate, lambda x: f"{x*100:.1f}%", True),
            ("Average Distance", perf1.avg_distance, perf2.avg_distance, lambda x: f"{x:.1f}px", False),
            ("Hit Rate", perf1.hit_rate, perf2.hit_rate, lambda x: f"{x*100:.1f}%", True),
            ("Response Time", perf1.avg_response_time, perf2.avg_response_time, lambda x: f"{x:.2f}s", False),
        ]
        
        for metric_name, val1, val2, formatter, higher_better in metrics:
            if higher_better:
                winner = model1 if val1 > val2 else model2 if val2 > val1 else "Tie"
            else:
                winner = model1 if val1 < val2 else model2 if val2 < val1 else "Tie"
            
            report_lines.append(
                f"| {metric_name} | {formatter(val1)} | {formatter(val2)} | **{winner}** |"
            )
        
        # Scenario comparison
        all_scenarios = set(perf1.scenario_performance.keys()) | set(perf2.scenario_performance.keys())
        if all_scenarios:
            report_lines.extend([
                "",
                "## Scenario Comparison",
                "",
                "| Scenario | " + model1 + " | " + model2 + " | Winner |",
                "|----------|" + "---|" * 3 + "|"
            ])
            
            for scenario in all_scenarios:
                val1 = perf1.scenario_performance.get(scenario, {}).get('success_rate', 0)
                val2 = perf2.scenario_performance.get(scenario, {}).get('success_rate', 0)
                winner = model1 if val1 > val2 else model2 if val2 > val1 else "Tie"
                
                report_lines.append(
                    f"| {scenario} | {val1*100:.1f}% | {val2*100:.1f}% | **{winner}** |"
                )
        
        self._write_report(output_file, report_lines)
    
    def generate_scenario_analysis_report(self, scenario: str, output_file: str) -> None:
        """Generate detailed analysis of a specific scenario."""
        
        scenario_results = [r for r in self.results if r.scenario == scenario]
        if not scenario_results:
            print(f"No results found for scenario: {scenario}")
            return
        
        report_lines = [
            f"# Scenario Analysis: {scenario}",
            "",
            f"**Scenario Description**: {TEST_SCENARIOS[scenario]['description']}",
            f"**Total Tests**: {len(scenario_results)}",
            f"**Models Tested**: {len(set(r.model_name for r in scenario_results))}",
            "",
            "## Scenario Performance",
            ""
        ]
        
        # Model performance in this scenario
        model_perf = {}
        for result in scenario_results:
            if result.model_name not in model_perf:
                model_perf[result.model_name] = []
            model_perf[result.model_name].append(result)
        
        # Calculate metrics per model
        model_metrics = {}
        for model_name, results in model_perf.items():
            total = len(results)
            successful = sum(1 for r in results if r.overall_success)
            distances = [r.distance for r in results if r.distance is not None]
            times = [r.response_time for r in results]
            
            model_metrics[model_name] = {
                'success_rate': successful / total,
                'avg_distance': np.mean(distances) if distances else 0,
                'avg_time': np.mean(times)
            }
        
        # Sort by success rate
        sorted_metrics = sorted(model_metrics.items(), key=lambda x: x[1]['success_rate'], reverse=True)
        
        report_lines.extend([
            "| Model | Success Rate | Avg Distance | Avg Time |",
            "|-------|--------------|--------------|----------|"
        ])
        
        for model_name, metrics in sorted_metrics:
            report_lines.append(
                f"| {model_name} | {metrics['success_rate']*100:.1f}% | "
                f"{metrics['avg_distance']:.1f}px | {metrics['avg_time']:.2f}s |"
            )
        
        # Analysis insights
        report_lines.extend([
            "",
            "## Key Insights",
            ""
        ])
        
        if sorted_metrics:
            best_model = sorted_metrics[0]
            worst_model = sorted_metrics[-1]
            
            report_lines.extend([
                f"- **Best Performing Model**: {best_model[0]} ({best_model[1]['success_rate']*100:.1f}% success)",
                f"- **Lowest Performing Model**: {worst_model[0]} ({worst_model[1]['success_rate']*100:.1f}% success)",
                f"- **Performance Gap**: {(best_model[1]['success_rate'] - worst_model[1]['success_rate'])*100:.1f} percentage points"
            ])
        
        self._write_report(output_file, report_lines)
    
    def save_performance_charts(self, output_dir: str) -> None:
        """Generate and save performance visualization charts."""
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        if not self.performances:
            return
        
        # Success Rate Comparison
        fig, ax = plt.subplots(figsize=(12, 8))
        
        models = list(self.performances.keys())
        success_rates = [p.overall_success_rate * 100 for p in self.performances.values()]
        
        bars = ax.bar(models, success_rates)
        ax.set_ylabel('Success Rate (%)')
        ax.set_title('Vision Model Success Rate Comparison')
        ax.set_ylim(0, 100)
        
        # Color bars based on performance
        for bar, rate in zip(bars, success_rates):
            if rate >= 80:
                bar.set_color('green')
            elif rate >= 50:
                bar.set_color('orange')
            else:
                bar.set_color('red')
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(output_path / 'success_rate_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Distance vs Success Rate Scatter
        fig, ax = plt.subplots(figsize=(10, 8))
        
        distances = [p.avg_distance for p in self.performances.values()]
        families = [AVAILABLE_MODELS[name].family for name in models if name in AVAILABLE_MODELS]
        
        scatter = ax.scatter(distances, success_rates, s=100, alpha=0.7)
        
        for i, model in enumerate(models):
            ax.annotate(model, (distances[i], success_rates[i]), 
                       xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        ax.set_xlabel('Average Distance (px)')
        ax.set_ylabel('Success Rate (%)')
        ax.set_title('Model Performance: Success Rate vs Accuracy')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path / 'performance_scatter.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _generate_insights(self) -> List[str]:
        """Generate key insights from benchmark results."""
        
        insights = []
        
        if not self.performances:
            return insights
        
        # Model family analysis
        families = {}
        for name, perf in self.performances.items():
            config = AVAILABLE_MODELS.get(name)
            if config:
                if config.family not in families:
                    families[config.family] = []
                families[config.family].append(perf.overall_success_rate)
        
        if len(families) > 1:
            family_avgs = {family: np.mean(rates) for family, rates in families.items()}
            best_family = max(family_avgs.items(), key=lambda x: x[1])
            insights.append(f"Model family '{best_family[0]}' shows best average performance ({best_family[1]*100:.1f}%)")
        
        # Size correlation
        sizes = {}
        for name, perf in self.performances.items():
            config = AVAILABLE_MODELS.get(name)
            if config:
                if config.size not in sizes:
                    sizes[config.size] = []
                sizes[config.size].append(perf.overall_success_rate)
        
        if len(sizes) > 1:
            size_avgs = {size: np.mean(rates) for size, rates in sizes.items()}
            size_order = ['2b', '3b', '4b', '7b', '8b', '11b', '12b']
            
            # Check if larger models perform better
            ordered_sizes = [(size, size_avgs[size]) for size in size_order if size in size_avgs]
            if len(ordered_sizes) > 1:
                correlation = np.corrcoef([i for i, _ in enumerate(ordered_sizes)], 
                                       [rate for _, rate in ordered_sizes])[0, 1]
                if correlation > 0.5:
                    insights.append("Larger models tend to perform better on coordinate generation tasks")
                elif correlation < -0.5:
                    insights.append("Smaller models show competitive or better performance than larger ones")
        
        # Scenario difficulty analysis
        scenarios = set(r.scenario for r in self.results)
        scenario_difficulty = {}
        for scenario in scenarios:
            scenario_results = [r for r in self.results if r.scenario == scenario]
            success_rate = np.mean([r.overall_success for r in scenario_results])
            scenario_difficulty[scenario] = success_rate
        
        if scenario_difficulty:
            easiest = max(scenario_difficulty.items(), key=lambda x: x[1])
            hardest = min(scenario_difficulty.items(), key=lambda x: x[1])
            
            insights.append(f"Easiest scenario: '{easiest[0]}' ({easiest[1]*100:.1f}% average success)")
            insights.append(f"Most challenging scenario: '{hardest[0]}' ({hardest[1]*100:.1f}% average success)")
        
        return insights
    
    def _write_report(self, output_file: str, lines: List[str]) -> None:
        """Write report lines to file."""
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"📄 Report saved: {output_path}")