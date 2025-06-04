# rvandroid/experiment/processor/static_analysis.py
"""
Static analysis processor for the unified execution framework.

This module provides the StaticAnalysisProcessor class, which handles the
static analysis phase of experiment execution, including code analysis,
reachability analysis, and GUI analysis.
"""

import os
from typing import List, Optional

from rvandroid.app import App
from rvandroid.constants import (
    EXTENSION_APK, EXTENSION_REACH, EXTENSION_GATOR,
    EXTENSION_GESDA, EXTENSION_METHODS
)
from rvandroid.experiment.core.interfaces import (
    IExecutionContext,
    ExecutionPhase
)
from rvandroid.experiment.event import (
    EventBus,
    EventType,
    Event
)
from rvandroid.experiment.processor.base import BasePhaseProcessor
from rvandroid.analysis.static.static_analysis import StaticAnalyzer
from rvandroid.util.logging.constants import LOG_START, LOG_COMPLETE, LOG_ERROR
from settings import INSTRUMENTED_DIR


class StaticAnalysisProcessor(BasePhaseProcessor):
    """
    Processor for static analysis phase.
    
    ### Architectural Decisions:
    - Implements a focused processor for static analysis tasks
    - Provides clean separation of analysis concerns
    - Enables flexible configuration of analysis operations
    - Supports comprehensive error handling and recovery
    
    ### Role in the System:
    - Manages static code analysis of applications
    - Performs reachability and GUI analysis
    - Generates essential data for experiment execution
    - Prepares applications for runtime monitoring
    """
    
    def __init__(self, context: IExecutionContext, event_bus: Optional[EventBus] = None):
        """
        Initialize the static analysis processor.
        
        Args:
            context: Execution context
            event_bus: Optional event bus for event publishing
        """
        super().__init__(
            processor_name="StaticAnalysisProcessor",
            supported_phases=[ExecutionPhase.STATIC_ANALYSIS],
            context=context,
            event_bus=event_bus
        )
        
    def _process_phase(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Process the static analysis phase.
        
        Args:
            phase: Phase to process
            context: Execution context
            
        Returns:
            True if processing was successful, False otherwise
        """
        if phase != ExecutionPhase.STATIC_ANALYSIS:
            self.logger.warning(f"Unsupported phase: {phase.name}")
            return False
            
        return self._run_static_analysis(context)
        
    def _run_static_analysis(self, context: IExecutionContext) -> bool:
        """
        Run static analysis on instrumented APKs.
        
        Args:
            context: Execution context
            
        Returns:
            True if analysis was successful, False otherwise
        """
        with self.logger.with_context(phase="static_analysis"):
            self.logger.info(LOG_START.format(operation="static analysis"))
            
            # Get instrumented APKs
            instrumented_apks = self._get_apks_for_analysis(context)
            
            if not instrumented_apks:
                self.logger.warning("No APKs found for static analysis")
                return True  # Not having APKs is not considered a failure
                
            self.logger.info(f"Running static analysis on {len(instrumented_apks)} APKs")
            
            all_success = True
            analysis_results = {}
            
            # Run analysis on each APK
            for app in instrumented_apks:
                with self.logger.with_context(app_name=app.name):
                    try:
                        # Set up output file paths
                        base_name_template = app.name + "{}"
                        gesda_file = os.path.join(INSTRUMENTED_DIR, base_name_template.format(EXTENSION_GESDA))
                        gator_file = os.path.join(INSTRUMENTED_DIR, base_name_template.format(EXTENSION_GATOR))
                        reach_file = os.path.join(INSTRUMENTED_DIR, base_name_template.format(EXTENSION_REACH))
                        methods_file = os.path.join(INSTRUMENTED_DIR, base_name_template.format(EXTENSION_METHODS))
                        
                        self.logger.info(LOG_START.format(operation=f"static analysis for {app.name}"))
                        
                        # Create analyzer
                        analyzer = StaticAnalyzer(app, output_dir=INSTRUMENTED_DIR)
                        
                        # Set output files
                        analyzer.gesda_file = gesda_file
                        analyzer.gator_file = gator_file
                        analyzer.reach_file = reach_file
                        analyzer.methods_file = methods_file
                        
                        # Run analysis
                        result = analyzer.analyze()
                        
                        # Store metrics
                        metrics = analyzer.get_metrics()
                        analysis_results[app.name] = {
                            "success": result.success,
                            "execution_times": result.execution_times,
                            "metrics": metrics
                        }
                        
                        # Store files in context
                        context.set(f"static_analysis.{app.name}", {
                            "gesda_file": gesda_file,
                            "gator_file": gator_file,
                            "reach_file": reach_file,
                            "methods_file": methods_file,
                            "metrics": metrics
                        })
                        
                        # Publish event
                        self._event_bus.publish(
                            event=Event(
                                type=EventType.ANALYSIS_COMPLETED,
                                data={
                                    "app_name": app.name,
                                    "success": result.success,
                                    "execution_times": result.execution_times,
                                    "metrics": metrics
                                },
                                source="StaticAnalysisProcessor"
                            ),
                            channel=EventBus.ANALYSIS_CHANNEL
                        )
                        
                        if result.success:
                            self.logger.info(LOG_COMPLETE.format(operation=f"static analysis for {app.name}"))
                        else:
                            self.logger.error(LOG_ERROR.format(
                                operation=f"static analysis for {app.name}",
                                error="Analysis failed"
                            ))
                            all_success = False
                            
                    except Exception as e:
                        self.logger.error(LOG_ERROR.format(
                            operation=f"static analysis for {app.name}",
                            error=str(e)
                        ))
                        all_success = False
                        
            # Store overall results in context
            context.set("static_analysis.results", analysis_results)
            
            if all_success:
                self.logger.info(LOG_COMPLETE.format(operation="static analysis"))
            else:
                self.logger.error(LOG_ERROR.format(
                    operation="static analysis",
                    error="One or more analyses failed"
                ))
                
            return all_success
            
    def _get_apks_for_analysis(self, context: IExecutionContext) -> List[App]:
        """
        Get APKs for static analysis.
        
        Args:
            context: Execution context
            
        Returns:
            List of App objects representing APKs for analysis
        """
        # Get APKs from context if available
        apk_names = context.get("instrumented_apks", [])
        
        apks = []
        
        # Get App instances from context
        for name in apk_names:
            app = context.get(f"app.{name}")
            
            if app is not None:
                apks.append(app)
                
        # If no APKs found in context, get from instrumented directory
        if not apks:
            try:
                for file in os.listdir(INSTRUMENTED_DIR):
                    if file.lower().endswith(EXTENSION_APK):
                        try:
                            app = App(os.path.join(INSTRUMENTED_DIR, file))
                            apks.append(app)
                        except Exception as e:
                            self.logger.error(LOG_ERROR.format(
                                operation=f"processing APK {file}",
                                error=str(e)
                            ))
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="listing instrumented APKs",
                    error=str(e)
                ))
                
        return apks