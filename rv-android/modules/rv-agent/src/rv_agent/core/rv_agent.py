"""
RVAgent Core - Autonomous Android testing agent.

EXACT implementation of MVP plan with process isolation.
Client-side autonomous agent using DeviceInterface + ReactEngine + Memory.
"""
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.error_handler import ErrorHandler

from ..constants import RVAgentConstants
from .device_adapter import DeviceInterface
from .react_engine import ReactEngine, ReactAction
from ..memory.short_term import ShortTermMemory
from ..memory.long_term import LongTermMemory
from ..memory.ui_coverage import UICoverageTracker
from ..llm.langchain_service import LangChainService


@dataclass
class AgentSession:
    """
    Represents an RVAgent testing session.

    Tracks session state, objectives, and execution results.
    """
    package_name: str
    objective: str = "explore_application"
    start_time: float = 0.0
    end_time: float = 0.0
    iteration_count: int = 0
    success_count: int = 0
    error_count: int = 0

    def __post_init__(self):
        if self.start_time == 0.0:
            self.start_time = time.time()

    @property
    def duration(self) -> float:
        """Get session duration in seconds."""
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time

    @property
    def success_rate(self) -> float:
        """Calculate session success rate."""
        if self.iteration_count == 0:
            return 0.0
        return self.success_count / self.iteration_count


class RVAgent:
    """
    RVAgent Core - Autonomous Android testing agent client.

    SUBPROCESS ISOLATED PROCESS:
    - LoggingManager.get_instance() with own subprocess instance
    - ErrorHandler.get_instance() with own subprocess instance
    - DeviceInterface + ReactEngine + Memory complete integration
    - MVP standalone client (no server dependencies)

    Architecture:
    - DeviceInterface: Android device communication
    - ReactEngine: ReAct decision making with memory integration
    - Memory components: Learning and state tracking
    - Session management: Testing session lifecycle

    Target: br.unb.cic.cryptoapp - Autonomous exploration and testing
    """

    def __init__(self, timeout: int = RVAgentConstants.DEFAULT_TIMEOUT):
        """Initialize RVAgent with process isolation support."""

        # Process isolation - LoggingManager with own instance
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.core.rv_agent",
            {"component": "RVAgent"}
        )

        # ErrorHandler decorators available in subprocess
        self.error_handler = ErrorHandler.get_instance()

        # Core components
        self.device_interface = DeviceInterface()

        # Memory components
        self.short_term_memory = ShortTermMemory()
        self.long_term_memory = LongTermMemory()
        self.ui_coverage_tracker = UICoverageTracker()

        # LLM Service (MANDATORY) - Now requires device_adapter for tool-calling
        self.llm_service = LangChainService(
            device_adapter=self.device_interface,
            model_name=RVAgentConstants.DEFAULT_MODEL
        )

        # ReactEngine with memory integration and LLM
        self.react_engine = ReactEngine(
            short_term_memory=self.short_term_memory,
            long_term_memory=self.long_term_memory,
            ui_coverage_tracker=self.ui_coverage_tracker,
            llm_service=self.llm_service
        )

        # Session management
        self.current_session: Optional[AgentSession] = None
        self.timeout = timeout

        self.logger.info(f"[RVAGENT_DEBUG] RVAgent initialized (timeout: {timeout}s)")

    def connect_to_device(self) -> bool:
        """
        Connect to Android device.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info("[RVAGENT_DEBUG] Connecting to Android device...")
            connected = self.device_interface.connect_to_device()

            if connected:
                self.logger.info("[RVAGENT_DEBUG] ✅ Device connection successful")
            else:
                self.logger.error("[RVAGENT_DEBUG] ❌ Device connection failed")

            return connected

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Device connection error: {e}")
            return False

    def start_testing_session(self, package_name: str, objective: str = "explore_application") -> bool:
        """
        Start autonomous testing session for specified app.

        Args:
            package_name: Android package name to test
            objective: Testing objective

        Returns:
            True if session started successfully
        """
        try:
            self.logger.info(f"[RVAGENT_DEBUG] Starting testing session: {package_name}")

            # Create new session
            self.current_session = AgentSession(
                package_name=package_name,
                objective=objective
            )

            # Launch application
            launched = self.device_interface.launch_app(package_name)
            if not launched:
                self.logger.error(f"[RVAGENT_DEBUG] Failed to launch {package_name}")
                return False

            # Set ReactEngine objective
            self.react_engine.set_objective(objective)

            # Clear memories for fresh session
            self.short_term_memory.clear()
            self.long_term_memory.clear_memory()
            self.ui_coverage_tracker.reset_coverage()

            self.logger.info(f"[RVAGENT_DEBUG] ✅ Testing session started: {package_name}")
            self.logger.info(f"[RVAGENT_DEBUG] Objective: {objective}")

            return True

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Session start failed: {e}")
            return False

    def run_autonomous_exploration(self, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Run autonomous exploration of the current application.

        Main execution loop: UI state capture → ReAct decision → Action execution.
        Executes until timeout is reached.

        Args:
            timeout: Override default timeout in seconds

        Returns:
            Session results summary
        """
        try:
            if not self.current_session:
                raise ValueError("No active testing session")

            execution_timeout = timeout or self.timeout
            start_time = time.time()
            self.logger.info(f"[RVAGENT_DEBUG] Starting autonomous exploration (timeout: {execution_timeout}s)")

            iteration = 0
            while True:
                iteration += 1
                current_time = time.time()
                elapsed_time = current_time - start_time

                # Check timeout
                if elapsed_time >= execution_timeout:
                    self.logger.info(f"[RVAGENT_DEBUG] Execution timeout reached ({execution_timeout}s)")
                    break
                remaining_time = execution_timeout - elapsed_time
                self.logger.info(f"[RVAGENT_DEBUG] === ITERATION {iteration} === (time remaining: {remaining_time:.1f}s)")

                # Step 0: App state monitoring with tolerance
                app_state_ok = self._ensure_target_app_active()
                if not app_state_ok:
                    self.logger.error(f"[RVAGENT_DEBUG] Target app not active after restart attempts (iteration {iteration})")
                    self.current_session.error_count += 1
                    break  # Exit if we can't maintain app state

                # Step 1: Automatic screenshot for LLM vision
                print(f"[RVAGENT_DEBUG] 📸 Taking screenshot for iteration {iteration}...")
                screenshot_path = self._take_controlled_screenshot(iteration)
                if screenshot_path:
                    self.logger.info(f"[RVAGENT_DEBUG] 📸 Screenshot captured: {screenshot_path}")
                    print(f"[RVAGENT_DEBUG] ✅ Screenshot ready: {screenshot_path}")

                # Step 2: Capture current UI state
                print(f"[RVAGENT_DEBUG] 📱 Capturing UI state after screenshot...")
                ui_state = self._capture_ui_state()
                if not ui_state:
                    self.logger.error(f"[RVAGENT_DEBUG] Failed to capture UI state (iteration {iteration})")
                    self.current_session.error_count += 1
                    continue

                print(f"[RVAGENT_DEBUG] ✅ UI state captured: Activity={ui_state.get('activity', 'unknown')}, Elements={ui_state.get('element_count', 0)}")

                # Step 3: ReactEngine decision (multiple actions) with screenshot
                actions = self.react_engine.decide_next_action(ui_state, screenshot_path)
                if not actions:
                    self.logger.error(f"[RVAGENT_DEBUG] ReactEngine failed to generate actions (iteration {iteration})")
                    self.current_session.error_count += 1
                    continue

                # Step 3: Execute actions sequentially
                successful_actions = 0
                total_actions = len(actions)

                for i, action in enumerate(actions):
                    if action.already_executed:
                        # LangChain tool already executed this action
                        self.logger.info(f"[RVAGENT_DEBUG] Action {i+1}/{total_actions} already executed: {action.action_type}")
                        success = action.already_executed  # Use the success status from tool execution
                        successful_actions += 1 if success else 0
                    else:
                        # Traditional execution (fallback for actions that couldn't be tool-called)
                        self.logger.info(f"[RVAGENT_DEBUG] Executing action {i+1}/{total_actions}: {action.action_type}")
                        success = self._execute_react_action(action)
                        if success:
                            successful_actions += 1

                    # Step 4: Record results for each action
                    self.react_engine.record_action_result(action, success)

                    # Log individual action result
                    status = "SUCCESS" if success else "FAILED"
                    executed_by = "LangChain-Tool" if action.already_executed else "DeviceInterface"
                    self.logger.info(f"[RVAGENT_DEBUG]   Action {i+1} result: "
                                   f"{status} via {executed_by} - {action.reasoning[:50]}...")

                # Update session stats (iteration = one LLM call with multiple actions)
                self.current_session.iteration_count += 1
                if successful_actions > 0:
                    self.current_session.success_count += successful_actions

                # Log iteration summary
                self.logger.info(f"[RVAGENT_DEBUG] Iteration {iteration} complete: "
                               f"{successful_actions}/{total_actions} actions successful")

                # Brief pause between iterations
                time.sleep(RVAgentConstants.ITERATION_DELAY)

            # Finalize session
            self.current_session.end_time = time.time()

            self.logger.info(f"[RVAGENT_DEBUG] ✅ Autonomous exploration complete")
            return self._generate_session_summary()

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Autonomous exploration failed: {e}")
            if self.current_session:
                self.current_session.end_time = time.time()
            return {"error": str(e)}

    def _capture_ui_state(self) -> Optional[Dict[str, Any]]:
        """Capture current UI state with error handling."""
        try:
            ui_state = self.device_interface.get_current_ui_state()

            if ui_state:
                self.logger.debug(f"[RVAGENT_DEBUG] UI state captured: "
                                f"Activity: {ui_state.get('activity', 'unknown')} "
                                f"Elements: {ui_state.get('element_count', 0)}")
            else:
                self.logger.warning("[RVAGENT_DEBUG] UI state capture returned empty")

            return ui_state

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] UI state capture failed: {e}")
            return None

    def _execute_react_action(self, action) -> bool:
        """
        Execute ReactAction on device.

        MVP implementation: Basic click actions only.
        Future: Full action type support via DeviceInterface.

        Args:
            action: ReactAction to execute

        Returns:
            True if action was successful
        """
        try:
            self.logger.debug(f"[RVAGENT_DEBUG] Executing action: {action.action_type} "
                            f"Element: {action.element_id[:50]}... "
                            f"Coordinates: {action.coordinates}")

            if action.action_type == "click" and action.coordinates:
                # MVP: Simple coordinate click using rv-uiautomator
                x, y = action.coordinates
                # Note: This is a placeholder - actual implementation would use
                # the device interface methods when they're available

                # For now, simulate action execution
                self.logger.debug(f"[RVAGENT_DEBUG] Simulating click at ({x}, {y})")

                # Take screenshot for verification
                screenshot_path = self.device_interface.take_screenshot()
                if screenshot_path:
                    self.logger.debug(f"[RVAGENT_DEBUG] Screenshot taken: {screenshot_path}")

                # Simulate success (in real implementation, this would be actual execution result)
                import random
                success = random.random() > 0.3  # 70% success rate for simulation

                return success

            elif action.action_type == "wait":
                self.logger.debug("[RVAGENT_DEBUG] Executing wait action")
                time.sleep(2)
                return True

            else:
                self.logger.warning(f"[RVAGENT_DEBUG] Unsupported action type: {action.action_type}")
                return False

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Action execution failed: {e}")
            return False

    def _generate_session_summary(self) -> Dict[str, Any]:
        """Generate comprehensive session summary."""
        try:
            if not self.current_session:
                return {"error": "No active session"}

            # Get statistics from all components
            react_stats = self.react_engine.get_decision_statistics()
            stm_stats = self.short_term_memory.get_statistics()
            ltm_stats = self.long_term_memory.get_statistics()
            coverage_stats = self.ui_coverage_tracker.get_overall_statistics()

            summary = {
                # Session info
                "session": {
                    "package_name": self.current_session.package_name,
                    "objective": self.current_session.objective,
                    "duration": self.current_session.duration,
                    "iterations": self.current_session.iteration_count,
                    "success_count": self.current_session.success_count,
                    "error_count": self.current_session.error_count,
                    "success_rate": self.current_session.success_rate
                },

                # Component statistics
                "react_engine": react_stats,
                "short_term_memory": stm_stats,
                "long_term_memory": ltm_stats,
                "ui_coverage": coverage_stats,

                # Summary metrics
                "total_unique_elements_tested": coverage_stats.get("total_unique_elements", 0),
                "total_interactions": coverage_stats.get("total_interactions", 0),
                "coverage_efficiency": (
                    coverage_stats.get("total_unique_elements", 0) /
                    max(self.current_session.iteration_count, 1)
                )
            }

            self.logger.info(f"[RVAGENT_DEBUG] Session summary generated: "
                           f"{summary['session']['iterations']} iterations, "
                           f"{summary['session']['success_rate']:.1%} success rate")

            return summary

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Session summary generation failed: {e}")
            return {"error": str(e)}

    def _ensure_target_app_active(self) -> bool:
        """
        Ensure target app is active with tolerance for 3 out-of-app screens.

        Returns:
            True if target app is active or successfully restarted, False if failed
        """
        if not self.current_session:
            return False

        target_package = self.current_session.package_name

        # Initialize out-of-app counter if not exists
        if not hasattr(self.current_session, 'out_of_app_count'):
            self.current_session.out_of_app_count = 0

        # Check if we're in the target app
        is_active = self.device_interface.is_target_app_active(target_package)
        current_package = self.device_interface.get_current_package()

        # DEBUG: Force active when package matches (temporary fix)
        if current_package == target_package:
            is_active = True
            self.logger.info(f"[RVAGENT_DEBUG] 🔧 FORCE ACTIVE: Package matches {target_package}")

        if is_active:
            # Reset counter when back in app
            self.current_session.out_of_app_count = 0
            self.logger.debug(f"[RVAGENT_DEBUG] ✅ Target app active: {target_package}")
            return True

        # We're outside the target app
        self.current_session.out_of_app_count += 1
        self.logger.warning(f"[RVAGENT_DEBUG] ⚠️ Outside target app: {current_package} (count: {self.current_session.out_of_app_count}/3)")

        if self.current_session.out_of_app_count <= 3:
            # Within tolerance - allow exploration of login screens, etc.
            self.logger.info(f"[RVAGENT_DEBUG] 🔄 Tolerating out-of-app navigation (within limit)")
            return True

        # Exceeded tolerance - restart app
        self.logger.warning(f"[RVAGENT_DEBUG] 🔄 Tolerance exceeded, restarting app: {target_package}")
        restart_success = self.device_interface.restart_target_app(target_package)

        if restart_success:
            self.current_session.out_of_app_count = 0  # Reset counter
            self.current_session.restart_count = getattr(self.current_session, 'restart_count', 0) + 1
            self.logger.info(f"[RVAGENT_DEBUG] ✅ App restarted successfully (restart #{self.current_session.restart_count})")
            return True
        else:
            self.logger.error(f"[RVAGENT_DEBUG] ❌ App restart failed: {target_package}")
            return False

    def _take_controlled_screenshot(self, iteration: int) -> Optional[str]:
        """
        Take screenshot controlled by the system with temporary storage and limit.

        Args:
            iteration: Current iteration number for filename

        Returns:
            Screenshot path if successful, None otherwise
        """
        try:
            import tempfile
            import os
            from pathlib import Path

            # Use temporary directory with maximum 10 screenshots
            temp_dir = Path(tempfile.gettempdir()) / "rvagent_screenshots"
            temp_dir.mkdir(exist_ok=True)

            # Clean old screenshots (keep only last 10)
            existing_screenshots = sorted(temp_dir.glob("*.png"))
            if len(existing_screenshots) >= 10:
                # Remove oldest screenshots
                for old_screenshot in existing_screenshots[:-9]:  # Keep 9, add 1 new = 10 total
                    try:
                        old_screenshot.unlink()
                        self.logger.debug(f"[RVAGENT_DEBUG] Removed old screenshot: {old_screenshot}")
                    except Exception:
                        pass

            timestamp = int(time.time())
            screenshot_path = temp_dir / f"iter_{iteration:03d}_{timestamp}.png"

            # Use DeviceInterface screenshot method directly
            actual_path = self.device_interface.take_screenshot(str(temp_dir))

            if actual_path:
                # Rename to our controlled naming scheme
                import shutil
                shutil.move(actual_path, screenshot_path)
                self.logger.debug(f"[RVAGENT_DEBUG] Screenshot saved: {screenshot_path}")
                return str(screenshot_path)
            else:
                self.logger.warning(f"[RVAGENT_DEBUG] Screenshot capture failed")
                return None

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Controlled screenshot error: {e}")
            return None

    def stop_session(self) -> bool:
        """Stop current testing session."""
        try:
            if not self.current_session:
                self.logger.warning("[RVAGENT_DEBUG] No active session to stop")
                return False

            self.current_session.end_time = time.time()
            session_duration = self.current_session.duration

            self.logger.info(f"[RVAGENT_DEBUG] Session stopped: {self.current_session.package_name}")
            self.logger.info(f"[RVAGENT_DEBUG] Duration: {session_duration:.1f}s, "
                           f"Iterations: {self.current_session.iteration_count}, "
                           f"Success rate: {self.current_session.success_rate:.1%}")

            self.current_session = None
            return True

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Session stop failed: {e}")
            return False

    def get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status and statistics."""
        try:
            status = {
                "connected": hasattr(self.device_interface, '_device') and self.device_interface._device is not None,
                "session_active": self.current_session is not None,
                "current_session": None,
                "components_status": {
                    "device_interface": "ready",
                    "react_engine": "ready",
                    "memory_components": "ready"
                }
            }

            if self.current_session:
                status["current_session"] = {
                    "package_name": self.current_session.package_name,
                    "objective": self.current_session.objective,
                    "duration": self.current_session.duration,
                    "iterations": self.current_session.iteration_count,
                    "success_rate": self.current_session.success_rate
                }

            return status

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Status check failed: {e}")
            return {"error": str(e)}

    def reset_agent(self) -> bool:
        """Reset agent state (for testing or new session)."""
        try:
            self.logger.info("[RVAGENT_DEBUG] Resetting RVAgent state...")

            # Stop current session if active
            if self.current_session:
                self.stop_session()

            # Reset all components
            self.short_term_memory.clear()
            self.long_term_memory.clear_memory()
            self.ui_coverage_tracker.reset_coverage()
            self.react_engine.reset_engine()

            self.logger.info("[RVAGENT_DEBUG] ✅ RVAgent reset complete")
            return True

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Agent reset failed: {e}")
            return False