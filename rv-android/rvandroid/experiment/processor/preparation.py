# rvandroid/experiment/processor/preparation.py
"""
Preparation processor for the unified execution framework.

This module provides the PreparationProcessor class, which handles the
preparation phase of experiment execution, including monitor generation,
APK instrumentation, and resource setup.
"""

import os
from typing import List, Optional, Dict, Any

from rvandroid.app import App
from rvandroid.experiment.core.interfaces import (
    IExecutionContext,
    ExecutionPhase
)
from rvandroid.experiment.event import (
    EventBus,
    EventType,
    Event,
    get_event_bus
)
from rvandroid.experiment.processor.base import BasePhaseProcessor
from rvandroid.rvandroid import RvAndroid
from rvandroid.rvsec import RVSec
from rvandroid.util.logging.constants import LOG_START, LOG_COMPLETE, LOG_ERROR, LOG_SKIPPED
from settings import INSTRUMENTED_DIR


class PreparationProcessor(BasePhaseProcessor):
    """
    Processor for experiment preparation phase.
    
    ### Architectural Decisions:
    - Implements a focused processor for preparation tasks
    - Provides clean separation of preparation concerns
    - Enables flexible configuration of preparation operations
    - Supports comprehensive error handling and recovery
    
    ### Role in the System:
    - Manages monitor generation and APK instrumentation
    - Prepares the environment for experiment execution
    - Ensures proper resource initialization
    - Facilitates experiment setup and configuration
    """
    
    def __init__(self, context: IExecutionContext, event_bus: Optional[EventBus] = None):
        """
        Initialize the preparation processor.
        
        Args:
            context: Execution context
            event_bus: Optional event bus for event publishing
        """
        super().__init__(
            processor_name="PreparationProcessor",
            supported_phases=[ExecutionPhase.SETUP, ExecutionPhase.PREPARATION],
            context=context,
            event_bus=event_bus
        )
        
    def _process_phase(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Process the preparation phase.
        
        Args:
            phase: Phase to process
            context: Execution context
            
        Returns:
            True if processing was successful, False otherwise
        """
        if phase == ExecutionPhase.SETUP:
            return self._handle_setup(context)
        elif phase == ExecutionPhase.PREPARATION:
            return self._handle_preparation(context)
        else:
            self.logger.warning(f"Unsupported phase: {phase.name}")
            return False
            
    def _handle_setup(self, context: IExecutionContext) -> bool:
        """
        Handle the setup phase.
        
        Args:
            context: Execution context
            
        Returns:
            True if setup was successful, False otherwise
        """
        with self.logger.with_context(phase="setup"):
            self.logger.info(LOG_START.format(operation="experiment setup"))
            
            # Ensure results directory exists
            os.makedirs(context.results_dir, exist_ok=True)
            
            # Ensure instrumented directory exists
            os.makedirs(INSTRUMENTED_DIR, exist_ok=True)
            
            # Get configuration options
            config = context.get("configuration", {})
            generate_monitors = config.get("generate_monitors", True)
            instrument = config.get("instrument", True)
            
            # Log configuration
            self.logger.info(f"Configuration: generate_monitors={generate_monitors}, instrument={instrument}")
            
            # Set up experiment structure
            logs_dir = os.path.join(context.results_dir, "logs")
            data_dir = os.path.join(context.results_dir, "data")
            reports_dir = os.path.join(context.results_dir, "reports")
            
            os.makedirs(logs_dir, exist_ok=True)
            os.makedirs(data_dir, exist_ok=True)
            os.makedirs(reports_dir, exist_ok=True)
            
            # Store directories in context
            context.set("directories", {
                "logs": logs_dir,
                "data": data_dir,
                "reports": reports_dir,
                "instrumented": INSTRUMENTED_DIR
            })
            
            self.logger.info(LOG_COMPLETE.format(operation="experiment setup"))
            return True
            
    def _handle_preparation(self, context: IExecutionContext) -> bool:
        """
        Handle the preparation phase.
        
        Args:
            context: Execution context
            
        Returns:
            True if preparation was successful, False otherwise
        """
        with self.logger.with_context(phase="preparation"):
            self.logger.info(LOG_START.format(operation="experiment preparation"))
            
            # Get configuration options
            config = context.get("configuration", {})
            generate_monitors = config.get("generate_monitors", True)
            instrument = config.get("instrument", True)
            
            success = True
            
            # Generate monitors if requested
            if generate_monitors:
                monitor_success = self._generate_monitors(context)
                if not monitor_success:
                    self.logger.error("Monitor generation failed")
                    success = False
                    
            # Instrument APKs if requested
            if instrument and success:
                instrument_success = self._instrument_apks(context)
                if not instrument_success:
                    self.logger.error("APK instrumentation failed")
                    success = False
                    
            # Get instrumented APKs
            if success:
                apks = self._get_instrumented_apks()
                context.set("instrumented_apks", [app.name for app in apks])
                
                # Store app instances in context
                for app in apks:
                    context.set(f"app.{app.name}", app)
                    
            if success:
                self.logger.info(LOG_COMPLETE.format(operation="experiment preparation"))
            else:
                self.logger.error(LOG_ERROR.format(
                    operation="experiment preparation",
                    error="One or more preparation steps failed"
                ))
                
            return success
            
    def _generate_monitors(self, context: IExecutionContext) -> bool:
        """
        Generate runtime verification monitors.
        
        Args:
            context: Execution context
            
        Returns:
            True if monitor generation was successful, False otherwise
        """
        with self.logger.with_context(phase="generate_monitors"):
            self.logger.info(LOG_START.format(operation="monitor generation"))
            
            try:
                # Generate monitors
                rvsec = RVSec()
                rvsec.generate_monitors()
                
                # Publish completion event
                self._event_bus.publish(
                    event=Event(
                        type=EventType.WORKFLOW_COMPLETED,
                        workflow_id="monitor_generation",
                        details={"phase": "monitor_generation"},
                        source="PreparationProcessor"
                    ),
                    channel=EventBus.LIFECYCLE_CHANNEL
                )
                
                self.logger.info(LOG_COMPLETE.format(operation="monitor generation"))
                return True
                
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="monitor generation",
                    error=str(e)
                ))
                return False
                
    def _instrument_apks(self, context: IExecutionContext) -> bool:
        """
        Instrument APKs with runtime verification monitors.
        
        Args:
            context: Execution context
            
        Returns:
            True if APK instrumentation was successful, False otherwise
        """
        with self.logger.with_context(phase="instrument_apks"):
            self.logger.info(LOG_START.format(operation="APK instrumentation"))
            
            try:
                # Instrument APKs
                rvandroid = RvAndroid()
                rvandroid.instrument_apks(results_dir=INSTRUMENTED_DIR)
                
                # Publish completion event
                self._event_bus.publish(
                    event=Event(
                        type=EventType.WORKFLOW_COMPLETED,
                        workflow_id="apk_instrumentation",
                        details={"phase": "apk_instrumentation"},
                        source="PreparationProcessor"
                    ),
                    channel=EventBus.LIFECYCLE_CHANNEL
                )
                
                self.logger.info(LOG_COMPLETE.format(operation="APK instrumentation"))
                return True
                
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="APK instrumentation",
                    error=str(e)
                ))
                return False
                
    def _get_instrumented_apks(self) -> List[App]:
        """
        Get all instrumented APKs from the instrumented directory.
        
        Returns:
            List of App objects representing the instrumented APKs
        """
        apks = []
        
        try:
            for file in os.listdir(INSTRUMENTED_DIR):
                if file.lower().endswith(".apk"):
                    try:
                        app = App(os.path.join(INSTRUMENTED_DIR, file))
                        apks.append(app)
                        self.logger.debug(f"Found instrumented APK: {app.name}")
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