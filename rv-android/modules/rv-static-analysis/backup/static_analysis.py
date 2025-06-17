"""
Static analysis module providing analyzers for Android applications.

This module contains analyzers for different static analysis tools:
- GESDA: For extracting application structure and components
- GATOR: For window transition graph analysis
- REACH: For reachability analysis of security-relevant components

The analyzers follow the BaseAnalyzer pattern for consistent interfaces
and interoperability with the rest of the system.
"""

import os.path
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from rv_android_core.analysis.base_analyzer import BaseAnalyzer
from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.commands.command_result import CommandResult
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.exceptions import ConfigurationError
from rv_static_analysis.config import RVStaticAnalysisConfig
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser


class StaticAnalysisException(Exception):
    """Exception raised for errors in static analysis execution."""
    pass


@dataclass
class StaticAnalysisResult:
    """Data class representing results from static analysis."""
    gesda_file: str = ""
    gator_file: str = ""
    reach_file: str = ""
    success: bool = True
    errors: List[str] = field(default_factory=list)
    execution_times: Dict[str, float] = field(default_factory=dict)


class StaticAnalyzer(BaseAnalyzer[StaticAnalysisResult]):
    """
    Analyzer for static analysis of Android applications.
    
    This analyzer orchestrates the execution of multiple static analysis tools
    and aggregates their results. It follows the BaseAnalyzer pattern for
    consistent integration with the rest of the system.
    
    ### Architectural Role:
    - Coordinates execution of static analysis tools
    - Provides a unified interface for accessing static analysis results
    - Integrates with the analysis pipeline for result management
    """

    def __init__(self, 
                 app: App, 
                 config: Optional[RVStaticAnalysisConfig] = None,
                 output_dir: Optional[str] = None):
        """
        Initialize the static analyzer for an application.
        
        Args:
            app: The Android application to analyze
            config: Configuration for static analysis tools
            output_dir: Optional directory for storing analysis output
        """
        super().__init__("static", None)
        self.app = app
        self.config = config or RVStaticAnalysisConfig()
        self.output_dir = output_dir or os.path.join(self.config.output_dir, app.package_name)
        self.execution_times = {}
        self.result = StaticAnalysisResult()
        
        # Initialize error handler for enhanced error handling
        from rv_android_core.util.error.error_handler import ErrorHandler
        self.error_handler = ErrorHandler.get_instance()

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Setup file paths for analysis results
        self.gesda_file = os.path.join(self.output_dir, f"{app.name}.gesda")
        self.gator_file = os.path.join(self.output_dir, f"{app.name}.wtg")
        self.reach_file = os.path.join(self.output_dir, f"{app.name}.reach")

        # Update result with file paths
        self.result.gesda_file = self.gesda_file
        self.result.gator_file = self.gator_file
        self.result.reach_file = self.reach_file

    def _initialize_from_static_data(self) -> None:
        """
        Initialize with static data (unused in this analyzer).
        
        This analyzer doesn't require initialization from static data
        as it is the entry point for generating that data.
        """
        pass

    def analyze(self, data: Any = None) -> StaticAnalysisResult:
        """
        Run static analysis on the application.
        
        This method orchestrates the execution of all static analysis tools
        and aggregates their results.
        
        Args:
            data: Unused parameter (required by base class)
            
        Returns:
            StaticAnalysisResult containing paths to analysis output files
            
        Raises:
            StaticAnalysisException: If any analysis step fails
        """
        self.logger.info(f"Running static analysis on: {self.app.name}")

        try:
            # Run GESDA analysis
            self._run_gesda()

            # Run GATOR analysis
            self._run_gator()

            # Run Reach analysis (depends on GESDA)
            self._run_reachability()

            # Update result with execution times
            self.result.execution_times = self.execution_times

            return self.result

        except StaticAnalysisException as e:
            self.logger.error(f"Static analysis failed: {str(e)}")
            self.result.success = False
            self.result.errors.append(str(e))
            return self.result

    def _run_gesda(self) -> None:
        """
        Run GESDA analysis for component extraction.
        
        GESDA analyzes the application to extract components, methods,
        and other structural elements.
        
        Raises:
            StaticAnalysisException: If GESDA analysis fails
        """
        cmd_args = self.config.get_tool_command('gesda', self.app.path, self.gesda_file)
        gesda_cmd = Command(cmd_args[0], cmd_args[1:])
        self._execute_command("GESDA", self.gesda_file, gesda_cmd)

    def _run_gator(self) -> None:
        """
        Run GATOR analysis for window transition graph.
        
        GATOR builds a window transition graph representing possible
        navigation paths through the application UI.
        
        Raises:
            StaticAnalysisException: If GATOR analysis fails
        """
        cmd_args = self.config.get_tool_command('gator', self.app.path, self.gator_file)
        gator_cmd = Command(cmd_args[0], cmd_args[1:])
        self._execute_command("GATOR", self.gator_file, gator_cmd)

    def _run_reachability(self) -> None:
        """
        Run reachability analysis.
        
        This analysis determines which security-relevant code is
        reachable from entry points in the application.
        
        Raises:
            StaticAnalysisException: If reachability analysis fails
        """
        cmd_args = self.config.get_tool_command(
            'reach', 
            self.app.path, 
            self.reach_file,
            gesda_file=self.gesda_file,
            timeout=300
        )
        reach_cmd = Command(cmd_args[0], cmd_args[1:])
        self._execute_command("REACHABILITY", self.reach_file, reach_cmd)

    def _execute_command(self, name: str, result_file: str, command: Command) -> CommandResult:
        """
        Execute a command with appropriate logging and error handling.
        
        Args:
            name: Name of the analysis tool
            result_file: Path to the expected output file
            command: Command to execute
            
        Returns:
            CommandResult from the execution
            
        Raises:
            StaticAnalysisException: If command execution fails
        """
        # Example: Using auto-introspection for cleaner error handling
        with self.error_handler.error_context(component="StaticAnalyzer", phase="command_execution", tool_name=name):
            # Skip if result already exists
            if os.path.isfile(result_file):
                self.logger.info(f"Skipping APK already analyzed with {name}: {self.app.name}")
                return CommandResult(0, "", "")

            self.logger.info(f"Executing analysis on apk '{self.app.name}': {name}")

            # Execute with timing
            start_time = time.time()
            cmd_result = command.invoke(stdout=sys.stdout)
            execution_time = time.time() - start_time

            # Store execution time
            self.execution_times[name] = execution_time

            # Check for errors
            if cmd_result.code != 0:
                error_msg = f"Error while executing {name}: {cmd_result.code}. {cmd_result.stderr}"
                self.logger.error(error_msg)
                raise StaticAnalysisException(error_msg)

            self.logger.info(f"Completed {name} analysis in {execution_time:.2f} seconds")
            return cmd_result

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about the static analysis process.
        
        Returns:
            Dictionary containing metrics including execution times
            and analysis result status
        """
        return {
            "execution_times": self.execution_times,
            "success": self.result.success,
            "error_count": len(self.result.errors)
        }

    def get_static_data(self) -> Optional[StaticAnalysisData]:
        """
        Load and parse the static analysis data from output files.
        
        This method uses the StaticAnalysisParser to convert raw output
        files into domain objects for use by other analyzers.
        
        Returns:
            StaticAnalysisData if parsing is successful, None otherwise
        """
        if not self.result.success:
            self.logger.warning("Cannot load static data because analysis was not successful")
            return None

        try:
            parser = StaticAnalysisParser()
            return parser.parse(
                self.gesda_file,
                self.gator_file,
                self.reach_file,
                self.app.package_name
            )
        except Exception as e:
            self.logger.error(f"Error parsing static analysis data: {str(e)}")
            return None

