"""
TestOrchestrator for RVSmart direct UIAutomator coordination.

This module provides the TestOrchestrator that replaces the client-server architecture
with direct UIAutomator integration, coordinating LLM action generation with device interaction.
"""

import os
import time
from typing import Dict, Any, Optional
from pathlib import Path

from pydantic import Field

from rv_android_core.domain.app import App
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.performance.performance_monitor import PerformanceMonitor
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model
from rv_uiautomator.adapter import UIAutomator2Adapter
from rv_uiautomator.executor import UIAutomatorActionExecutor
from rv_uiautomator.state import StateConverter
from rvsmart_tool.config.tool_config import RvSmartToolConfig
from rvsmart_tool.constants import (
    DEFAULT_ACTION_DELAY,
    STATE_STABILIZATION_DELAY,
    MAX_CONSECUTIVE_ERRORS,
    MAX_EXTERNAL_ATTEMPTS
)
from rvsmart_tool.llm.service.action_service import LLMActionService


@validated_model(['total_actions', 'successful_actions'])
class TestExecutionMetrics(BaseValidatedModel):
    """
    Metrics tracking for test execution.
    
    ### Architectural Role:
    - Tracks testing progress and performance
    - Provides diagnostics for optimization
    - Enables comparison between testing strategies
    """
    
    total_actions: int = Field(default=0, description="Total actions executed")
    successful_actions: int = Field(default=0, description="Successfully executed actions")
    failed_actions: int = Field(default=0, description="Failed action executions")
    external_navigation_count: int = Field(default=0, description="External navigation attempts")
    app_restarts: int = Field(default=0, description="Application restart count")
    execution_time: float = Field(default=0.0, description="Total execution time in seconds")
    error_count: int = Field(default=0, description="Total error count")


class TestOrchestrator:
    """
    Orchestrates test execution using UIAutomator and LLM guidance.
    
    ### Architectural Decisions:
    - Replaces server-based architecture with direct execution loop
    - Uses RVSmart LLM service components (not referenced from rvandroid)
    - Provides synchronous execution model for reliability
    - Implements comprehensive error recovery mechanisms
    - Uses PerformanceMonitor for execution timing
    - Uses BaseValidatedModel for metrics tracking
    
    ### Role in the System:
    - Central coordinator for test execution lifecycle
    - Bridges UIAutomator device interaction with LLM intelligence
    - Manages test state and execution flow
    - Provides metrics and monitoring capabilities
    
    ### Execution Flow:
    1. Capture device state via UIAutomator
    2. Convert state format for compatibility
    3. Process through LLM service pipeline
    4. Execute generated actions on device
    5. Monitor results and adapt strategy
    """
    
    def __init__(self, 
                 static_data: StaticAnalysisData,
                 tool_config: RvSmartToolConfig,
                 app: App,
                 device_id: str = "emulator-5554",
                 results_dir: str = "./results"):
        """
        Initialize test orchestrator with required components.
        
        Args:
            static_data: Static analysis data for application
            tool_config: Tool configuration including LLM settings
            app: Application object containing package name and metadata
            device_id: Target device identifier
            results_dir: Directory for storing results
        """
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvsmart_tool.orchestration",
            {CONTEXT_COMPONENT: "TestOrchestrator"}
        )
        
        # Initialize error handling and performance monitoring
        self.error_handler = ErrorHandler.get_instance()
        self.performance_monitor = PerformanceMonitor.get_instance()
        
        # Store configuration
        self.config = tool_config
        self.device_id = device_id
        self.target_package = app.package_name
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize UIAutomator components
        self.ui_adapter = UIAutomator2Adapter(device_id=device_id)
        self.action_executor = UIAutomatorActionExecutor()
        self.state_converter = StateConverter()
        
        # Initialize LLM service with all capabilities
        self.llm_service = LLMActionService(
            static_data=static_data,
            tool_config=tool_config
        )
        
        # Execution state
        self.is_running = False
        self.metrics = None
        
        self.logger.info("TestOrchestrator initialized successfully")
        
    @ErrorHandler.handle_errors(
        component="TestOrchestrator",
        phase="test_execution"
    )
    def execute_test_cycle(self, timeout: int = 300) -> None:
        """
        Execute the main test cycle with external navigation integration.
        
        ### Execution Flow:
        1. Connect to device and launch application
        2. Main testing loop with state capture and action generation
        3. External navigation handling with package validation
        4. Action execution and error recovery
        5. Metrics collection and cleanup
        
        Args:
            timeout: Maximum execution time in seconds
        """
        start_time = time.time()
        self.logger.info("="*60)
        self.logger.warning("🎬 RVSMART TESTORCHESTRATOR EXECUTION START")
        self.logger.info("="*60)
        self.logger.info(f"Target device: {self.device_id}")
        self.logger.info(f"Target package: {self.target_package}")
        self.logger.info(f"Timeout: {timeout}s")
        self.logger.info(f"Results dir: {self.results_dir}")
        self.logger.info("="*60)
        
        try:
            # Connect to device
            self._connect_to_device()
            
            # Launch target application
            self._launch_application()
            
            # Initialize metrics
            self.metrics = TestExecutionMetrics(execution_time=0.0)
            
            # Main testing loop
            while (time.time() - start_time) < timeout:
                try:
                    # Check if we need external navigation
                    current_package = self._get_current_package()
                    if current_package != self.target_package:
                        if not self._handle_external_navigation():
                            break # TODO sera que usa break aqui mesmo? ai vai parar a execucao, nao?
                        continue
                    
                    # Execute single test cycle
                    success = self._execute_single_cycle()
                    
                    if not success:
                        self.metrics.error_count += 1
                        if self.metrics.error_count >= MAX_CONSECUTIVE_ERRORS:
                            self.logger.error("Too many consecutive errors, stopping")
                            break # TODO sera que usa break aqui mesmo? nao seria bom tentar algo, tipo reiniciar o app (ou ate reconectar com o device antes), e se ainda assim continuar com erro termina a execucao ... devemos pensar em algo
                    else:
                        self.metrics.error_count = 0
                    
                    # Wait for UI stabilization
                    time.sleep(STATE_STABILIZATION_DELAY)
                    
                except KeyboardInterrupt:
                    self.logger.info("Test cycle interrupted by user")
                    break
                except Exception as e:
                    self.logger.error(f"Error in test cycle: {e}")
                    self.metrics.error_count += 1
                    if self.metrics.error_count >= MAX_CONSECUTIVE_ERRORS:
                        break
            
            # Update final execution time
            self.metrics.execution_time = time.time() - start_time
            self.logger.info(f"Test cycle completed in {self.metrics.execution_time:.1f}s")
            
        finally:
            self.cleanup()
    
    def _connect_to_device(self) -> bool:
        """Connect to the target device."""
        self.logger.info("🔌 DEVICE CONNECTION PHASE")
        self.logger.info(f"   Connecting to device: {self.device_id}")
        self.logger.info(f"   UIAutomator adapter: {type(self.ui_adapter).__name__}")
        
        try:
            if not self.ui_adapter.connect(self.device_id):
                self.logger.error(f"❌ Device connection failed: {self.device_id}")
                raise Exception(f"Failed to connect to device {self.device_id}")
            
            self.logger.info(f"✅ Device connection established: {self.device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Device connection error: {e}")
            raise
    
    def _launch_application(self) -> bool:
        """Launch the target application."""
        self.logger.info(f"Launching application: {self.target_package}")
        
        if not self.ui_adapter.launch_app(self.target_package):
            raise Exception(f"Failed to launch application {self.target_package}")
        
        # Wait for app to start
        time.sleep(3.0)
        self.logger.info("Application launched successfully")
        return True
    
    def _get_current_package(self) -> Optional[str]:
        """Get the currently active package name."""
        self.logger.debug("🔍 Getting current package name")
        try:
            ui_state = self.ui_adapter.get_ui_state()
            current_package = ui_state.get("current_package")
            self.logger.debug(f"✅ Current package: {current_package}")
            return current_package
        except Exception as e:
            self.logger.warning(f"❌ Failed to get current package: {e}")
            return None
    
    def _handle_external_navigation(self) -> bool:
        """Handle navigation outside the target application."""
        self.metrics.external_navigation_count += 1
        
        self.logger.warning("🔄 EXTERNAL NAVIGATION DETECTED")
        self.logger.warning(f"   Attempt: {self.metrics.external_navigation_count}/{MAX_EXTERNAL_ATTEMPTS}")
        
        if self.metrics.external_navigation_count >= MAX_EXTERNAL_ATTEMPTS:
            self.logger.warning("🔄 Max external attempts reached, restarting application")
            return self._restart_application()
        
        # Try to navigate back
        self.logger.info("⬅️ Attempting to navigate back to target app")
        if self.ui_adapter.press_back():
            self.logger.warning("✅ Back navigation successful, waiting 2s")
            time.sleep(2.0)
            return True
        else:
            self.logger.error("❌ Back navigation failed")
        
        return False
    
    def _restart_application(self) -> bool:
        """Restart the target application."""
        try:
            self.logger.warning("🔄 APPLICATION RESTART PROCEDURE")
            self.logger.info(f"   Target package: {self.target_package}")
            
            # Stop application
            self.logger.info("🛑 Stopping application")
            self.ui_adapter.stop_app(self.target_package)
            self.logger.info("⏱️ Waiting 2s after stop")
            time.sleep(2.0)
            
            # Launch application
            self.logger.warning("🚀 Launching application")
            if self.ui_adapter.launch_app(self.target_package):
                self.logger.info("⏱️ Waiting 3s after launch")
                time.sleep(3.0)
                self.metrics.app_restarts += 1
                self.metrics.external_navigation_count = 0
                self.logger.warning("✅ Application restarted successfully")
                self.logger.info(f"   Total app restarts: {self.metrics.app_restarts}")
                return True
            else:
                self.logger.error("❌ Failed to launch application after stop")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Application restart failed: {e}")
            self.logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def _execute_single_cycle(self) -> bool:
        """Execute a single test cycle: capture state -> generate actions -> execute."""
        self.logger.warning("🔄 STARTING SINGLE TEST CYCLE")
        self.logger.info(f"   UI Adapter type: {type(self.ui_adapter).__name__}")
        self.logger.info(f"   Action Executor type: {type(self.action_executor).__name__}")
        self.logger.info(f"   State Converter type: {type(self.state_converter).__name__}")
        
        try:
            with self.performance_monitor.measure_time("test_cycle"):
                # Phase 1: Capture current device state
                self.logger.warning("📱 PHASE 1: CAPTURING DEVICE STATE")
                ui_state = self.ui_adapter.get_ui_state(force_refresh=True)
                if not ui_state:
                    self.logger.error("❌ PHASE 1 FAILED: Could not capture UI state")
                    return False
                    
                self.logger.info(f"✅ UI state captured - Keys: {list(ui_state.keys()) if ui_state else 'None'}")
                
                # Phase 2: Take screenshot for vision strategies
                self.logger.info("📸 PHASE 2: TAKING SCREENSHOT")
                screenshot_path = self.ui_adapter.take_screenshot() # TODO devemos rever a questao do diretorio onde salva o screenshot: acho que deve ser um diretorio temporario e com no maximo 10-20 ultimas imagens
                if screenshot_path:
                    ui_state["screenshot_path"] = screenshot_path
                    self.logger.info(f"✅ Screenshot saved: {screenshot_path}")
                else:
                    self.logger.warning("⚠️ Screenshot capture failed or not available")
                
                # Phase 3: Convert to DroidBot format for compatibility with LLM service
                self.logger.warning("🔄 PHASE 3: STATE FORMAT CONVERSION")
                droidbot_state = self.state_converter.uiautomator_to_droidbot(ui_state)
                self.logger.info(f"✅ State converted - DroidBot format keys: {list(droidbot_state.keys()) if droidbot_state else 'None'}")
                
                # Phase 4: Process through LLM service (returns GeneratedAction objects)
                self.logger.info("🤖 PHASE 4: LLM ACTION GENERATION")
                self.logger.info(f"   LLM Service type: {type(self.llm_service).__name__}")
                actions = self.llm_service.process_state(droidbot_state)
                
                if not actions:
                    self.logger.info("ℹ️ PHASE 4 RESULT: No actions generated for current state")
                    return True # TODO retorna true? por que?
                    
                self.logger.info(f"✅ PHASE 4 COMPLETED: {len(actions)} actions generated")
                for i, action in enumerate(actions):
                    self.logger.info(f"   Action {i+1}: {action.text if hasattr(action, 'text') else str(action)}")
                
                # Phase 5: Execute generated actions
                self.logger.info("⚡ PHASE 5: ACTION EXECUTION")
                for i, action in enumerate(actions):
                    self.logger.info(f"🎯 Executing action {i+1}/{len(actions)}: {action.text if hasattr(action, 'text') else str(action)}")
                    self.logger.info(f"   Action type: {type(action).__name__}")
                    self.logger.info(f"   Action attributes: {[attr for attr in dir(action) if not attr.startswith('_')]}")
                    
                    success = self.action_executor.execute(action, self.ui_adapter)
                    self.metrics.total_actions += 1
                    
                    if success:
                        self.metrics.successful_actions += 1
                        self.logger.info(f"✅ Action {i+1} executed successfully")
                    else:
                        self.metrics.failed_actions += 1
                        self.logger.error(f"❌ Action {i+1} execution failed")
                    
                    # Delay between actions
                    self.logger.debug(f"⏱️ Waiting {DEFAULT_ACTION_DELAY}s between actions")
                    time.sleep(DEFAULT_ACTION_DELAY)
                
                self.logger.warning("✅ SINGLE TEST CYCLE COMPLETED SUCCESSFULLY")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ TEST CYCLE EXECUTION FAILED: {e}")
            self.logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def cleanup(self) -> None:
        """Clean up resources and log final metrics."""
        self.logger.info("🧹 TESTORCHESTRATOR CLEANUP PHASE")
        try:
            if self.metrics:
                self.logger.info("="*60)
                self.logger.warning("📊 FINAL TEST EXECUTION SUMMARY")
                self.logger.info("="*60)
                self.logger.info(f"📈 Total actions: {self.metrics.total_actions}")
                self.logger.info(f"✅ Successful actions: {self.metrics.successful_actions}")
                self.logger.info(f"❌ Failed actions: {self.metrics.failed_actions}")
                success_rate = (self.metrics.successful_actions/max(1,self.metrics.total_actions))*100
                self.logger.info(f"📊 Success rate: {success_rate:.1f}%")
                self.logger.info(f"🔄 App restarts: {self.metrics.app_restarts}")
                self.logger.info(f"🔀 External navigations: {self.metrics.external_navigation_count}")
                self.logger.info(f"⏱️ Total execution time: {self.metrics.execution_time:.1f}s")
                self.logger.info("="*60)
            else:
                self.logger.warning("⚠️ No metrics available for summary")
                
        except Exception as e:
            self.logger.error(f"❌ Cleanup error: {e}")
            self.logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
        
        self.logger.warning("✅ TestOrchestrator cleanup completed")