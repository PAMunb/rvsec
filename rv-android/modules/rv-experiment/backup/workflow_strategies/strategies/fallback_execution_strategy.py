"""
Fallback Execution Strategy

This module implements the fallback execution strategy for graceful degradation
when full functionality is not available. This strategy enables experiments to
continue with reduced functionality rather than failing completely.

### Strategy Characteristics:
- Graceful degradation when dependencies unavailable
- Clear fallback mode notifications and logging
- Artifact reuse prioritization over regeneration
- Continuation support even with missing components

### Architecture Benefits:
- Experiment resilience in imperfect environments
- Clear communication of degraded functionality
- Researcher visibility into fallback scenarios
- Productive experiment execution despite limitations
"""

import os
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.exceptions import RVExperimentError
from rv_android_core.event.bus import EventBus
from rv_android_core.event.models import EventType

from .base_strategy import PhaseExecutionStrategy
from .phase_result import PhaseResult, PhaseExecutionMode, PhaseExecutionContext


class FallbackExecutionStrategy(PhaseExecutionStrategy):
    """
    Fallback execution strategy with graceful degradation.
    
    ### Execution Philosophy:
    - Prioritize experiment continuation over perfect execution
    - Clearly communicate when operating in degraded mode
    - Maximize artifact reuse to minimize regeneration
    - Provide meaningful fallback alternatives
    - Maintain experiment value despite missing dependencies
    
    ### Key Features:
    - Graceful handling of missing dependencies
    - Artifact reuse prioritization
    - Clear fallback mode notifications
    - Alternative execution paths for missing functionality
    - Comprehensive logging of degraded operations
    
    ### Fallback Scenarios:
    - Missing monitor generators → copy original APKs
    - Missing instrumentation tools → use original APKs for analysis
    - Missing static analysis tools → skip analysis phase
    - Invalid existing artifacts → regenerate or use alternatives
    """
    
    def __init__(self, config: Any):
        """Initialize fallback execution strategy."""
        super().__init__(config, "FallbackExecutionStrategy")
        self.fallback_notifications: List[str] = []
        self.event_bus = EventBus.get_instance()
        self.logger.info("Fallback execution strategy initialized - graceful degradation enabled")
    
    @ErrorHandler.handle_errors(
        component="FallbackExecutionStrategy",
        phase="phase_execution",
        context={"strategy_type": "fallback_execution"}
    )
    def execute_phase(self, context: PhaseExecutionContext) -> PhaseResult:
        """
        Execute phase with fallback support and graceful degradation.
        
        ### Fallback Execution Process:
        1. Attempt full execution if dependencies available
        2. Detect missing dependencies and limitations
        3. Apply appropriate fallback strategy
        4. Notify researcher of degraded mode operation
        5. Ensure experiment can continue productively
        
        Args:
            context: Phase execution context with configuration and constraints
            
        Returns:
            PhaseResult with fallback information and continuation guidance
        """
        phase_name = context.phase_name
        self.logger.info(f"Executing phase '{phase_name}' with fallback strategy")
        
        # Create result instance for fallback mode
        result = self.create_result(
            phase_name=phase_name,
            success=False,  # Will be updated based on execution outcome
            execution_mode=PhaseExecutionMode.FALLBACK,
            can_continue=True  # Fallback strategy prioritizes continuation
        )
        
        try:
            # Route to specific phase implementation with fallback support
            if phase_name == "monitor_generation":
                self._execute_monitor_generation_fallback(context, result)
            elif phase_name == "apk_instrumentation":
                self._execute_apk_instrumentation_fallback(context, result)
            elif phase_name == "static_analysis":
                self._execute_static_analysis_fallback(context, result)
            else:
                # Unknown phase - try to continue with skip
                self._skip_unknown_phase(phase_name, result)
            
            # Mark completion based on execution outcome
            result.mark_completed(success=True)
            
            # Publish phase execution mode event
            self._publish_phase_execution_event(phase_name, result)
            
            # Log fallback notifications for researcher awareness
            self._log_fallback_notifications(result)
            
        except Exception as e:
            # Even in fallback mode, log errors but try to continue
            result.mark_completed(success=False)
            result.error_context = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "strategy": "fallback_execution",
                "phase": phase_name,
                "fallback_attempted": True
            }
            
            # In fallback mode, we try to continue despite errors
            result.can_continue = True
            result.set_fallback_mode(f"Error in fallback execution: {e}")
            
            self.logger.warning(f"Phase '{phase_name}' encountered error in fallback mode: {e}")
        
        finally:
            # Record execution and log summary
            self.record_execution(result)
            self.log_execution_summary(result)
        
        return result
    
    @ErrorHandler.handle_errors(
        component="FallbackExecutionStrategy",
        phase="monitor_generation_fallback"
    )
    def _execute_monitor_generation_fallback(self, context: PhaseExecutionContext, result: PhaseResult) -> None:
        """
        Execute monitor generation with fallback to existing artifacts or skip.
        
        ### Monitor Generation Fallback Strategy:
        1. Check for existing valid monitors → reuse
        2. Attempt generation if tools available
        3. If generation fails → continue without monitors
        4. Notify researcher of monitor availability status
        
        Args:
            context: Execution context with configuration
            result: Result object to update with execution data
        """
        self.logger.info("Executing monitor generation with fallback support")
        
        monitors_dir = getattr(self.config.get_monitored_operations_config(), 'output_dir', 'mop_out')
        
        # First priority: reuse existing valid monitors
        if self._attempt_monitor_reuse(monitors_dir, result):
            self.logger.info("Reusing existing monitors - fallback successful")
            return
        
        # Second priority: attempt generation if tools available
        if self._attempt_monitor_generation(monitors_dir, result):
            self.logger.info("Monitor generation successful in fallback mode")
            return
        
        # Final fallback: continue without monitors
        self._fallback_no_monitors(result)
        self.logger.warning("Continuing without monitors - experiment will use original APKs")
    
    @ErrorHandler.handle_errors(
        component="FallbackExecutionStrategy",
        phase="apk_instrumentation_fallback"
    )
    def _execute_apk_instrumentation_fallback(self, context: PhaseExecutionContext, result: PhaseResult) -> None:
        """
        Execute APK instrumentation with fallback to original APK copying.
        
        ### APK Instrumentation Fallback Strategy:
        1. Check for existing instrumented APKs → reuse
        2. Attempt instrumentation if monitors and tools available
        3. If instrumentation fails → copy original APKs
        4. Ensure experiment has APKs to work with
        
        Args:
            context: Execution context with configuration
            result: Result object to update with execution data
        """
        self.logger.info("Executing APK instrumentation with fallback support")
        
        instrumented_dir = context.get_artifact_dir("instrumented") or "out"
        monitors_dir = context.get_artifact_dir("monitors") or "mop_out"
        
        # First priority: reuse existing instrumented APKs
        if self._attempt_instrumentation_reuse(instrumented_dir, result):
            self.logger.info("Reusing existing instrumented APKs - fallback successful")
            return
        
        # Second priority: attempt instrumentation if monitors available
        if self._attempt_apk_instrumentation(instrumented_dir, monitors_dir, result):
            self.logger.info("APK instrumentation successful in fallback mode")
            return
        
        # Final fallback: copy original APKs
        self._fallback_copy_original_apks(instrumented_dir, result)
        self.logger.warning("Using original APKs without instrumentation - monitoring limited")
    
    @ErrorHandler.handle_errors(
        component="FallbackExecutionStrategy",
        phase="static_analysis_fallback"
    )
    def _execute_static_analysis_fallback(self, context: PhaseExecutionContext, result: PhaseResult) -> None:
        """
        Execute static analysis with fallback to skip if tools unavailable.
        
        ### Static Analysis Fallback Strategy:
        1. Check for existing analysis results → reuse
        2. Attempt analysis on available APKs
        3. If analysis fails → skip and continue
        4. Notify researcher of analysis availability
        
        Args:
            context: Execution context with configuration
            result: Result object to update with execution data
        """
        self.logger.info("Executing static analysis with fallback support")
        
        # First priority: reuse existing analysis results
        if self._attempt_analysis_reuse(result):
            self.logger.info("Reusing existing static analysis results - fallback successful")
            return
        
        # Second priority: attempt analysis if tools available
        if self._attempt_static_analysis(result):
            self.logger.info("Static analysis successful in fallback mode")
            return
        
        # Final fallback: skip analysis
        self._fallback_skip_analysis(result)
        self.logger.warning("Skipping static analysis - tools unavailable or failed")
    
    def _attempt_monitor_reuse(self, monitors_dir: str, result: PhaseResult) -> bool:
        """Attempt to reuse existing monitors."""
        if not os.path.exists(monitors_dir):
            return False
        
        monitor_files = list(Path(monitors_dir).glob("*.rvm")) + list(Path(monitors_dir).glob("*.aj"))
        if monitor_files:
            for monitor_file in monitor_files:
                result.add_artifact(str(monitor_file), "reused")
            
            result.execution_mode = PhaseExecutionMode.SKIPPED
            self._add_fallback_notification("Reusing existing monitors", result)
            return True
        
        return False
    
    def _attempt_monitor_generation(self, monitors_dir: str, result: PhaseResult) -> bool:
        """Attempt monitor generation with graceful failure."""
        try:
            from rv_monitor_generator.generator import RuntimeVerificationGenerator
            
            monitor_config = self.config.get_monitored_operations_config()
            self.prepare_output_directory(monitors_dir, clean_existing=False)
            
            generator = RuntimeVerificationGenerator(monitor_config)
            success = generator.generate_monitors(monitors_dir)
            
            if success:
                # Catalog generated monitors
                for pattern in ["*.rvm", "*.aj"]:
                    artifacts = list(Path(monitors_dir).glob(pattern))
                    for artifact in artifacts:
                        result.add_artifact(str(artifact), "created")
                
                return True
            
        except ImportError:
            self._add_fallback_notification("Monitor generator module unavailable", result)
        except Exception as e:
            self._add_fallback_notification(f"Monitor generation failed: {e}", result)
        
        return False
    
    def _fallback_no_monitors(self, result: PhaseResult) -> None:
        """Fallback for continuing without monitors."""
        result.execution_mode = PhaseExecutionMode.SKIPPED
        self._add_fallback_notification(
            "Continuing without runtime verification monitors - using original APKs",
            result
        )
    
    def _attempt_instrumentation_reuse(self, instrumented_dir: str, result: PhaseResult) -> bool:
        """Attempt to reuse existing instrumented APKs."""
        if not os.path.exists(instrumented_dir):
            return False
        
        apk_files = list(Path(instrumented_dir).glob("*.apk"))
        if apk_files:
            for apk_file in apk_files:
                if apk_file.stat().st_size > 0:  # Basic validation
                    result.add_artifact(str(apk_file), "reused")
            
            if result.artifacts.total_artifacts > 0:
                result.execution_mode = PhaseExecutionMode.SKIPPED
                self._add_fallback_notification("Reusing existing instrumented APKs", result)
                return True
        
        return False
    
    def _attempt_apk_instrumentation(self, instrumented_dir: str, monitors_dir: str, result: PhaseResult) -> bool:
        """Attempt APK instrumentation with graceful failure."""
        try:
            from rv_instrumentation.instrumenter import APKInstrumenter
            
            # Check if monitors are available
            if not os.path.exists(monitors_dir) or not list(Path(monitors_dir).glob("*.rvm")):
                return False
            
            instrumentation_config = self.config.get_rv_instrumentation_config()
            self.prepare_output_directory(instrumented_dir, clean_existing=False)
            
            instrumenter = APKInstrumenter(instrumentation_config)
            apk_list = self.config.get_apk_list()
            
            success_count = 0
            for apk_path in apk_list:
                try:
                    apk_name = os.path.basename(apk_path)
                    output_path = os.path.join(instrumented_dir, apk_name)
                    
                    if instrumenter.instrument_apk(apk_path, monitors_dir, output_path):
                        result.add_artifact(output_path, "created")
                        success_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"Instrumentation failed for {apk_path}: {e}")
            
            return success_count > 0
            
        except ImportError:
            self._add_fallback_notification("APK instrumentation module unavailable", result)
        except Exception as e:
            self._add_fallback_notification(f"APK instrumentation failed: {e}", result)
        
        return False
    
    def _fallback_copy_original_apks(self, instrumented_dir: str, result: PhaseResult) -> None:
        """Fallback to copying original APKs."""
        try:
            self.prepare_output_directory(instrumented_dir, clean_existing=False)
            
            apk_list = self.config.get_apk_list()
            for apk_path in apk_list:
                apk_name = os.path.basename(apk_path)
                output_path = os.path.join(instrumented_dir, apk_name)
                
                shutil.copy2(apk_path, output_path)
                result.add_artifact(output_path, "created")
            
            self._add_fallback_notification(
                f"Copied {len(apk_list)} original APKs - no instrumentation applied",
                result
            )
            
        except Exception as e:
            self._add_fallback_notification(f"Failed to copy original APKs: {e}", result)
    
    def _attempt_analysis_reuse(self, result: PhaseResult) -> bool:
        """Attempt to reuse existing static analysis results."""
        # Placeholder for analysis result reuse logic
        # Implementation depends on where analysis results are stored
        return False
    
    def _attempt_static_analysis(self, result: PhaseResult) -> bool:
        """Attempt static analysis with graceful failure."""
        try:
            from rv_static_analysis.analyzer import StaticAnalysisCoordinator
            
            static_config = self.config.get_static_analysis_config()
            analyzer = StaticAnalysisCoordinator(static_config)
            
            # Use original APKs if instrumented not available
            target_apks = self.config.get_apk_list()
            analysis_results = analyzer.analyze_apks(target_apks)
            
            if analysis_results:
                result.add_artifact("static_analysis_results.json", "created")
                return True
            
        except ImportError:
            self._add_fallback_notification("Static analysis module unavailable", result)
        except Exception as e:
            self._add_fallback_notification(f"Static analysis failed: {e}", result)
        
        return False
    
    def _fallback_skip_analysis(self, result: PhaseResult) -> None:
        """Fallback for skipping static analysis."""
        result.execution_mode = PhaseExecutionMode.SKIPPED
        self._add_fallback_notification(
            "Skipping static analysis - tools unavailable or failed",
            result
        )
    
    def _skip_unknown_phase(self, phase_name: str, result: PhaseResult) -> None:
        """Skip unknown phase gracefully."""
        result.execution_mode = PhaseExecutionMode.SKIPPED
        self._add_fallback_notification(f"Unknown phase '{phase_name}' - skipping", result)
    
    
    def _log_fallback_notifications(self, result: PhaseResult) -> None:
        """Log all fallback notifications for researcher awareness."""
        if self.fallback_notifications:
            self.logger.warning("🔄 FALLBACK MODE NOTIFICATIONS:")
            for notification in self.fallback_notifications:
                self.logger.warning(f"  • {notification}")
            
            self.logger.warning(
                f"Experiment continues in degraded mode - "
                f"{len(self.fallback_notifications)} fallback scenarios applied"
            )
        
        # Clear notifications for next phase
        self.fallback_notifications.clear()

    @ErrorHandler.handle_errors(component="FallbackExecutionStrategy", phase="event_publishing")
    def _publish_phase_execution_event(self, phase_name: str, result: PhaseResult) -> None:
        """
        Publish phase execution mode event for tracking fallback execution.
        
        Args:
            phase_name: Name of the executed phase
            result: Phase execution result with mode information
        """
        try:
            # Determine execution mode from result
            execution_mode = result.execution_mode.value if hasattr(result.execution_mode, 'value') else str(result.execution_mode)
            
            # Get artifacts information from result
            artifacts_available = {}
            if hasattr(result, 'artifacts') and result.artifacts:
                artifacts_available = {
                    'total_artifacts': result.artifacts.total_artifacts,
                    'has_created': len(result.artifacts.created) > 0,
                    'has_reused': len(result.artifacts.reused) > 0
                }
            
            # Get fallback reason from result
            fallback_reason = None
            if hasattr(result, 'error_context') and result.error_context:
                fallback_reason = result.error_context.get('fallback_reason')
            
            # Publish phase execution mode event using EventBus convenience method
            self.event_bus.publish_phase_execution_mode_event(
                phase_name=phase_name,
                execution_mode=execution_mode,
                fallback_reason=fallback_reason,
                artifacts_available=artifacts_available,
                source="FallbackExecutionStrategy",
                async_mode=False  # Synchronous for immediate feedback
            )
            
            self.logger.debug(f"Published phase execution event for {phase_name} in {execution_mode} mode")
            
        except Exception as e:
            # Don't fail the strategy if event publishing fails
            self.logger.warning(f"Failed to publish phase execution event: {e}")
    
    def _add_fallback_notification(self, message: str, result: PhaseResult) -> None:
        """Add fallback notification for researcher awareness."""
        self.fallback_notifications.append(message)
        result.set_fallback_mode(message)