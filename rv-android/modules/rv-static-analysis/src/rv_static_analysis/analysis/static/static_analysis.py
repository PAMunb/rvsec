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
from typing import Dict, Any, Optional, List

from pydantic import Field, field_validator

from rv_android_core.analysis.base_analyzer import BaseAnalyzer
from rv_android_core.domain.app import App
from rv_android_core.commands.command import Command
from rv_android_core.commands.command_result import CommandResult
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVAndroidError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.context_adapter import ContextAdapter
from rv_android_core.util.validation import BaseValidatedModel, validated_model
from rv_static_analysis.config import RVStaticAnalysisConfig
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser


class StaticAnalysisException(RVAndroidError):
    """Exception raised for errors in static analysis execution."""
    pass


class StaticAnalysisResult(BaseValidatedModel):
    """
    Data model representing comprehensive results from static analysis execution.
    
    This model encapsulates all outputs and metadata from the static analysis pipeline,
    including file paths, execution status, error information, and performance metrics.
    The model provides a standardized interface for accessing static analysis results
    across the RV-Android system.

    ### Architectural Role:
    - Serves as the primary data contract for static analysis output
    - Provides standardized access to analysis artifacts and metadata
    - Enables consistent error reporting and performance tracking
    - Facilitates integration with downstream analysis components
    """

    gesda_file: str = Field(
        default="",
        description="Path to GESDA analysis output file containing application structure"
    )
    gator_file: str = Field(
        default="",
        description="Path to GATOR window transition graph output file"
    )
    reach_file: str = Field(
        default="",
        description="Path to REACH reachability analysis output file"
    )
    success: bool = Field(
        default=True,
        description="Overall success status of the static analysis pipeline"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages encountered during analysis"
    )
    execution_times: Dict[str, float] = Field(
        default_factory=dict,
        description="Execution times for each analysis tool in seconds"
    )


@validated_model(['app', 'config', 'output_dir'])
class StaticAnalyzer(BaseValidatedModel, BaseAnalyzer[StaticAnalysisResult]):
    """
    Comprehensive analyzer for static analysis of Android applications.
    
    The StaticAnalyzer orchestrates the execution of multiple static analysis tools
    (GESDA, GATOR, REACH) and aggregates their results into a unified output format.
    It follows the BaseAnalyzer pattern for consistent integration with the broader
    analysis pipeline and provides robust error handling and logging.

    ### Architectural Decisions:
    - Integrates with centralized ErrorHandler for consistent error management
    - Uses structured logging through LoggingManager for operational visibility
    - Follows dependency-aware execution order (GESDA → GATOR, REACH)
    - Provides comprehensive validation and error reporting
    - Supports both individual tool execution and complete pipeline execution

    ### Role in the System:
    - Acts as the primary interface for static analysis execution
    - Coordinates execution of multiple static analysis tools
    - Provides unified result aggregation and error handling
    - Integrates with the broader analysis pipeline for data flow
    - Enables downstream analyzers through parsed static data access

    ### Integration Points:
    - Consumed by coverage analyzers for static-dynamic correlation
    - Used by experiment orchestration systems for batch analysis
    - Integrated with result storage and reporting systems
    - Provides data for UI navigation and security analysis components
    """

    app: App = Field(
        ...,
        description="Android application to analyze"
    )
    config: RVStaticAnalysisConfig = Field(
        default_factory=RVStaticAnalysisConfig,
        description="Configuration for static analysis tools"
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="Directory for storing analysis output"
    )

    # BaseAnalyzer inherited fields (excluded from constructor but maintained internally)
    analyzer_name: str = Field(default="static", exclude=True)
    static_data: Optional[StaticAnalysisData] = Field(default=None, exclude=True)

    # Internal state fields (not part of constructor)
    execution_times: Dict[str, float] = Field(default_factory=dict, exclude=True)
    result: StaticAnalysisResult = Field(default_factory=StaticAnalysisResult, exclude=True)
    logger: Optional[ContextAdapter] = Field(default=None, exclude=True)
    error_handler: Optional[ErrorHandler] = Field(default=None, exclude=True)
    gesda_file: str = Field(default="", exclude=True)
    gator_file: str = Field(default="", exclude=True)
    reach_file: str = Field(default="", exclude=True)

    @field_validator('app')
    @classmethod
    def validate_app(cls, v):
        """Validate that app is a valid App instance."""
        if not hasattr(v, 'name') or not hasattr(v, 'package_name') or not hasattr(v, 'path'):
            raise ValueError("app must be a valid App instance with name, package_name, and path attributes")
        return v

    def model_post_init(self, __context) -> None:
        """
        Initialize analyzer components after Pydantic model construction.
        
        This method sets up all necessary components for static analysis execution,
        including configuration validation, output directory preparation, and integration
        with centralized error handling and logging infrastructure.
        """
        # Resolve output directory
        if self.output_dir is None:
            self.output_dir = os.path.join(self.config.output_dir, self.app.package_name)

        # Initialize internal state
        self.execution_times = {}
        self.result = StaticAnalysisResult()

        # Initialize structured logging through LoggingManager
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'rv_static_analysis.StaticAnalyzer',
            {
                CONTEXT_COMPONENT: 'StaticAnalyzer',
                'component_module': 'rv-static-analysis',
                'app_package': self.app.package_name
            }
        )

        # Initialize centralized error handling
        self.error_handler = ErrorHandler.get_instance()

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Setup file paths for analysis results using application name
        self.gesda_file = os.path.join(self.output_dir, f"{self.app.name}.gesda")
        self.gator_file = os.path.join(self.output_dir, f"{self.app.name}.wtg")
        self.reach_file = os.path.join(self.output_dir, f"{self.app.name}.reach")

        # Update result model with resolved file paths
        self.result.gesda_file = self.gesda_file
        self.result.gator_file = self.gator_file
        self.result.reach_file = self.reach_file

        self.logger.info("StaticAnalyzer initialized", extra={
            'output_dir': self.output_dir,
            'app_name': self.app.name,
            'config_summary': self.config.get_configuration_summary()
        })

    def _initialize_from_static_data(self) -> None:
        """
        Initialize analyzer from existing static data.
        
        This analyzer serves as the entry point for generating static data
        rather than consuming it, so no initialization from static data is required.
        This method satisfies the BaseAnalyzer interface contract.
        """
        pass

    @ErrorHandler.handle_errors(component="StaticAnalyzer", phase="static_analysis")
    def analyze(self, data: Any = None) -> StaticAnalysisResult:
        """
        Execute the complete static analysis pipeline for the Android application.
        
        This method orchestrates the execution of all static analysis tools in the
        correct dependency order and aggregates their results. It provides comprehensive
        error handling and performance tracking for each analysis step.
        
        ### Analysis Pipeline:
        1. GESDA analysis for application structure extraction
        2. GATOR analysis for window transition graph generation
        3. REACH analysis for security-relevant code reachability (depends on GESDA)
        4. Result aggregation and performance metrics collection
        
        Args:
            data: Unused parameter (required by BaseAnalyzer interface)
            
        Returns:
            StaticAnalysisResult containing paths to analysis output files,
            execution status, and performance metrics
            
        Raises:
            StaticAnalysisException: If any critical analysis step fails
        """
        self.logger.info("Starting comprehensive static analysis pipeline", extra={
            'app_name': self.app.name,
            'app_package': self.app.package_name,
            'pipeline_stage': 'initialization'
        })
        self.logger.debug(self.config)

        try:
            # Execute analysis pipeline in dependency order
            self._run_gesda()
            self._run_gator()
            self._run_reachability()

            # Update result with execution performance metrics
            self.result.execution_times = self.execution_times

            self.logger.info("Static analysis pipeline completed successfully", extra={
                'execution_times': self.execution_times,
                'total_time': sum(self.execution_times.values()),
                'pipeline_stage': 'completed'
            })

            return self.result

        except StaticAnalysisException as e:
            self.logger.error("Static analysis pipeline failed", extra={
                'error_message': str(e),
                'pipeline_stage': 'failed'
            })
            self.result.success = False
            self.result.errors.append(str(e))
            return self.result

    def _run_gesda(self) -> None:
        """
        Execute GESDA analysis for comprehensive application component extraction.
        
        GESDA (General Static Data Analyzer) analyzes the application bytecode to extract
        structural information including components, methods, class hierarchies, and
        security-relevant code patterns. This analysis forms the foundation for
        subsequent reachability analysis.
        
        ### GESDA Analysis Output:
        - Application component inventory (Activities, Services, etc.)
        - Method-level call graph information
        - Class hierarchy and inheritance relationships
        - Security-relevant API usage patterns
        
        Raises:
            StaticAnalysisException: If GESDA analysis execution fails
        """
        cmd_args = self.config.get_tool_command('gesda', self.app.path, self.gesda_file)
        gesda_cmd = Command(cmd_args[0], cmd_args[1:])
        self._execute_command("GESDA", self.gesda_file, gesda_cmd)

    def _run_gator(self) -> None:
        """
        Execute GATOR analysis for window transition graph generation.
        
        GATOR (GUI Analysis TOol foR Android) performs static analysis of the application's
        user interface to construct a window transition graph. This graph represents all
        possible navigation paths through the application's UI components and activities.
        
        ### GATOR Analysis Output:
        - Window transition graph representing UI navigation flows
        - Activity and fragment relationship mappings
        - Event handler and callback analysis
        - UI element hierarchy and interaction patterns
        
        Raises:
            StaticAnalysisException: If GATOR analysis execution fails
        """
        cmd_args = self.config.get_tool_command('gator', self.app.path, self.gator_file)
        gator_cmd = Command(cmd_args[0], cmd_args[1:])
        self._execute_command("GATOR", self.gator_file, gator_cmd)

    def _run_reachability(self) -> None:
        """
        Execute comprehensive reachability analysis for security-relevant code detection.
        
        REACH analysis determines which security-relevant code (defined by MOP specifications)
        is reachable from application entry points. This analysis depends on GESDA output
        for accurate call graph information and uses monitor specifications to identify
        security-critical API usage patterns.
        
        ### REACH Analysis Output:
        - Reachability information for security-relevant methods
        - Call path analysis from entry points to critical APIs
        - Monitor specification coverage analysis
        - Security risk assessment based on reachable code patterns
        
        Raises:
            StaticAnalysisException: If reachability analysis execution fails
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
        Execute static analysis command with comprehensive logging and error handling.
        
        This method provides standardized execution for all static analysis tools with
        consistent error handling, performance tracking, and result validation. It
        implements intelligent caching by skipping analysis if output already exists.
        
        Args:
            name: Human-readable name of the analysis tool for logging
            result_file: Path to the expected output file for result validation
            command: Command object configured for tool execution
            
        Returns:
            CommandResult containing execution status and output information
            
        Raises:
            StaticAnalysisException: If command execution fails or produces invalid results
        """
        # Use centralized error handling for consistent error management
        with self.error_handler.error_context(
                component="StaticAnalyzer",
                phase="command_execution",
                tool_name=name,
                app_name=self.app.name
        ):
            # Implement intelligent caching - skip if result already exists
            if os.path.isfile(result_file):
                self.logger.info("Analysis result already exists, skipping execution", extra={
                    'tool_name': name,
                    'result_file': result_file,
                    'execution_status': 'cached'
                })
                return CommandResult(0, b"", b"")

            self.logger.info(f"Executing static analysis tool: {name}", extra={
                'tool_name': name,
                'app_name': self.app.name,
                'command_args': command.args[:3] if len(command.args) > 3 else command.args,  # Truncate for logging
                'execution_status': 'starting'
            })

            # Execute with comprehensive timing and monitoring
            start_time = time.time()
            cmd_result = command.invoke(stdout=sys.stdout)
            execution_time = time.time() - start_time

            # Store execution performance metrics
            # TODO usar performance monitor
            self.execution_times[name] = execution_time

            # Validate execution results
            if cmd_result.code != 0:
                error_msg = f"Static analysis tool {name} failed with exit code {cmd_result.code}"
                if cmd_result.stderr:
                    stderr_text = cmd_result.get_stderr_text()
                    error_msg += f". Error output: {stderr_text}"

                self.logger.error("Static analysis tool execution failed", extra={
                    'tool_name': name,
                    'exit_code': cmd_result.code,
                    'execution_time': execution_time,
                    'execution_status': 'failed'
                })
                raise StaticAnalysisException(error_msg)

            self.logger.info(f"Static analysis tool '{name}' execution completed successfully", extra={
                'tool_name': name,
                'execution_time': execution_time,
                'execution_status': 'completed'
            })

            return cmd_result

    def get_metrics(self) -> Dict[str, Any]:
        """
        Generate comprehensive metrics about the static analysis execution process.
        
        This method provides detailed performance and status information that can be
        used for monitoring, debugging, and optimization of the static analysis pipeline.
        
        Returns:
            Dictionary containing comprehensive execution metrics including:
            - Individual tool execution times
            - Overall success status
            - Error count and details
            - Tool-specific performance characteristics
        """
        total_execution_time = sum(self.execution_times.values())

        return {
            "execution_times": self.execution_times,
            "total_execution_time": total_execution_time,
            "success": self.result.success,
            "error_count": len(self.result.errors),
            "errors": self.result.errors,
            "tools_executed": list(self.execution_times.keys()),
            "average_tool_time": total_execution_time / len(self.execution_times) if self.execution_times else 0,
            "output_files": {
                "gesda": self.gesda_file,
                "gator": self.gator_file,
                "reach": self.reach_file
            }
        }

    def get_static_data(self) -> Optional[StaticAnalysisData]:
        """
        Load and parse static analysis data from generated output files.
        
        This method uses the StaticAnalysisParser to convert raw tool output files
        into structured domain objects that can be consumed by other analyzers and
        components in the RV-Android system.
        
        ### Data Integration:
        - Parses GESDA output for application structure information
        - Processes GATOR output for UI navigation graph data
        - Integrates REACH output for security reachability information
        - Provides unified StaticAnalysisData object for downstream consumption
        
        Returns:
            StaticAnalysisData containing parsed and structured static analysis
            information, or None if parsing fails or analysis was unsuccessful
            
        Raises:
            No exceptions raised - errors are logged and None is returned for robustness
        """
        if not self.result.success:
            self.logger.warning("Cannot load static data because analysis was not successful", extra={
                'error_count': len(self.result.errors),
                'errors': self.result.errors
            })
            return None

        try:
            parser = StaticAnalysisParser()
            static_data = parser.parse(
                self.gesda_file,
                self.gator_file,
                self.reach_file,
                self.app.package_name
            )

            self.logger.info("Static analysis data parsed successfully", extra={
                'package_name': self.app.package_name,
                'data_available': static_data is not None
            })

            return static_data

        except Exception as e:
            self.logger.error("Error parsing static analysis data", extra={
                'error_message': str(e),
                'package_name': self.app.package_name,
                'gesda_file': self.gesda_file,
                'gator_file': self.gator_file,
                'reach_file': self.reach_file
            })
            return None
