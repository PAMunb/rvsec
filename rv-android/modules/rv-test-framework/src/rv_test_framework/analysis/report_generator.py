"""
Simple report generator for test framework analysis results.

Following the simplicity principle, this component generates basic reports
without complex templating or visualization libraries.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class ReportGenerator:
    """Simple report generator for analysis results."""
    
    @ErrorHandler.handle_errors(
        component="ReportGenerator",
        phase="initialization"
    )
    def __init__(self, results_dir: str):
        """Initialize report generator."""
        self.results_dir = Path(results_dir)
        self.reports_dir = self.results_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'rv_test_framework.analysis.report_generator',
            {CONTEXT_COMPONENT: 'ReportGenerator'}
        )
        
        self.logger.info(f"ReportGenerator initialized: {results_dir}")
    
    def generate_summary_report(self, analysis_results: Dict[str, Any]) -> str:
        """
        Generate simple text summary report.
        
        Args:
            analysis_results: Comprehensive analysis results
            
        Returns:
            Path to generated report file
        """
        report_content = []
        
        # Header
        report_content.append("# RV-Android Test Framework - Execution Summary")
        report_content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_content.append("")
        
        # Configuration analysis
        if "configuration_analysis" in analysis_results:
            config_data = analysis_results["configuration_analysis"]
            report_content.append("## Configuration Performance")
            
            for config in config_data.get("configuration_ranking", [])[:5]:  # Top 5
                report_content.append(f"- {config['configuration']}")
                report_content.append(f"  Quality Score: {config['quality_score']:.1f}")
                report_content.append(f"  Success Rate: {config['success_rate']:.1f}%")
                report_content.append(f"  Avg Time: {config['average_execution_time']:.1f}s")
                report_content.append("")
        
        # Save report
        report_file = self.reports_dir / "summary_report.txt"
        with open(report_file, 'w') as f:
            f.write('\n'.join(report_content))
        
        self.logger.info(f"Summary report generated: {report_file}")
        return str(report_file)