# rv_test_framework/execution/direct_tool_execution.py
"""
Direct tool execution component for test framework to prevent emulator duplication.

This component replaces ToolExecutionComponent for test framework usage, executing
tools directly without invoke_as_daemon to prevent fork-based process duplication
that causes multiple emulator instances on the same port.
"""

import subprocess
import os
import signal
import time
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from rv_android_core.event import EventBus, EventType
from rv_platform.components.base import TaskComponent
from rv_android_core.util.error.exceptions import RVToolTimeoutError
from rv_platform.task import Task
from rv_tools.tools.tool import Tool


class DirectToolExecutionComponent(TaskComponent):
    """
    Direct tool execution component that prevents emulator duplication.
    
    This component executes tools directly using subprocess instead of
    invoke_as_daemon to prevent the fork-based duplication that causes
    multiple emulator processes on the same port.
    
    ### Key Differences from ToolExecutionComponent:
    - Direct subprocess execution instead of daemon execution
    - Process management to prevent duplication
    - Socket validation integration with EmulatorPortManager
    - Test framework specific optimizations
    """
    
    def __init__(self, task: Task, tool: Tool, event_bus: EventBus):
        """
        Initialize direct tool execution component.
        
        Args:
            task: Task to execute
            tool: Tool instance to run
            event_bus: Event bus for communication
        """
        super().__init__(task, event_bus)
        self.tool = tool
        self.logger = logging.getLogger(f"direct_tool_execution.{tool.name}")
        self.process: Optional[subprocess.Popen] = None
        
    def initialize(self, context: Dict[str, Any]) -> bool:
        """Initialize component."""
        self.logger.info(f"Initializing direct tool execution for: {self.tool.name}")
        return True
        
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute tool directly without invoke_as_daemon.
        
        Args:
            context: Task execution context
            
        Returns:
            Success status
        """
        return self.run_tool_direct()
        
    def cleanup(self, context: Dict[str, Any]) -> None:
        """Clean up tool processes."""
        self.cleanup_processes()
        
    def run_tool_direct(self) -> bool:
        """
        Execute tool directly using subprocess to prevent emulator duplication.
        
        Returns:
            Success status
        """
        try:
            self.logger.info(f"Starting direct execution of tool: {self.tool.name}")
            
            # Publish tool started event
            self.event_bus.publish_task_event(
                EventType.TOOL_STARTED,
                task_id=self.task.id,
                details={"tool_name": self.tool.name},
                source="DirectToolExecutionComponent"
            )
            
            # Build command directly from tool configuration
            cmd_parts = self._build_tool_command()
            
            if not cmd_parts:
                raise ValueError(f"Failed to build command for tool: {self.tool.name}")
            
            self.logger.info(f"Executing command: {' '.join(cmd_parts)}")
            
            # Execute directly using subprocess (no daemon fork)
            success = self._execute_direct_command(cmd_parts)
            
            # Publish tool stopped event
            self.event_bus.publish_task_event(
                EventType.TOOL_STOPPED,
                task_id=self.task.id,
                details={"tool_name": self.tool.name},
                source="DirectToolExecutionComponent"
            )
            
            if success:
                self.logger.info(f"Direct execution completed successfully for tool: {self.tool.name}")
            else:
                self.logger.warning(f"Direct execution failed for tool: {self.tool.name}")
                
            return success
            
        except RVToolTimeoutError as e:
            self.logger.info(f"Tool {self.tool.name} timed out (expected): {e}")
            return True  # Timeout is expected for testing tools
            
        except Exception as e:
            self.logger.error(f"Direct execution failed for tool {self.tool.name}: {e}")
            
            # Publish tool failed event
            self.event_bus.publish_task_event(
                EventType.TASK_FAILED,
                task_id=self.task.id,
                details={
                    "tool_name": self.tool.name,
                    "error": str(e)
                },
                source="DirectToolExecutionComponent"
            )
            
            return False
    
    def _build_tool_command(self) -> List[str]:
        """
        Build command parts for direct tool execution.
        
        For rvandroid tool, this builds the droidbot command with proper parameters
        without going through invoke_as_daemon which causes process duplication.
        
        Returns:
            List of command parts for subprocess execution
        """
        if self.tool.name == "rvandroid":
            return self._build_rvandroid_command()
        else:
            # For other tools, delegate to tool's native command building
            return self._build_generic_command()
    
    def _build_rvandroid_command(self) -> List[str]:
        """
        Build RVAndroid/DroidBot command directly (replicating original tool behavior).
        
        This prevents the invoke_as_daemon call that causes emulator duplication
        by building the droidbot command with all necessary parameters exactly
        as the original RVAndroid tool does.
        
        Returns:
            DroidBot command parts
        """
        cmd_parts = ["poetry", "run", "droidbot"]
        
        # Add APK path (from task.app.path in original implementation)
        if hasattr(self.task, 'app') and hasattr(self.task.app, 'path'):
            cmd_parts.extend(["-a", str(self.task.app.path)])
        elif hasattr(self.task, 'apk_path') and self.task.apk_path:
            cmd_parts.extend(["-a", str(self.task.apk_path)])
        
        # Add policy (rvandroid for AI-driven testing)
        cmd_parts.extend(["-policy", "rvandroid"])
        
        # Add output directory (following original pattern: task.results_dir/rvandroid_output)
        if hasattr(self.task, 'results_dir'):
            import os.path
            output_dir = os.path.join(self.task.results_dir, "rvandroid_output")
        else:
            output_dir = self._get_output_directory()
        cmd_parts.extend(["-o", output_dir])
        
        # Add timeout (from task.config.timeout in original implementation)
        if hasattr(self.task, 'config') and hasattr(self.task.config, 'timeout'):
            timeout = self.task.config.timeout
        else:
            timeout = getattr(self.task, 'timeout', 60)
        cmd_parts.extend(["-timeout", str(timeout)])
        
        # Add RVAndroid server URL (from additional_params.server_port)
        if hasattr(self.task, 'additional_params') and self.task.additional_params:
            params = self.task.additional_params
            if 'server_port' in params:
                url = f"http://localhost:{params['server_port']}/api/get_actions"
                cmd_parts.extend(["--rvandroid_url", url])
        
        # Add screenshot configuration (from tool's LLM config)
        # Default to false for test framework to avoid vision complexity
        cmd_parts.extend(["--rvandroid_screenshots", "false"])
        
        # Add device serial (dynamic device_serial for parallel execution)
        device_serial = None
        
        # Check device_serial in additional_params (parallel execution)
        if (hasattr(self.task, 'additional_params') and self.task.additional_params and
            'device_serial' in self.task.additional_params):
            device_serial = self.task.additional_params['device_serial']
        # Fallback to task.device_serial if available
        elif hasattr(self.task, 'device_serial') and self.task.device_serial:
            device_serial = self.task.device_serial
            
        if device_serial:
            cmd_parts.extend(["-d", device_serial])
            self.logger.info(f"Using device serial: {device_serial}")
        
        return cmd_parts
    
    def _build_generic_command(self) -> List[str]:
        """Build command for non-rvandroid tools."""
        # For other tools, create basic command structure
        cmd_parts = ["poetry", "run"]
        
        # Add tool name
        cmd_parts.append(self.tool.name)
        
        # Add basic parameters if available
        if hasattr(self.task, 'apk_path'):
            cmd_parts.extend(["-a", str(self.task.apk_path)])
            
        return cmd_parts
    
    def _get_output_directory(self) -> str:
        """Get output directory for tool execution."""
        if hasattr(self.task, 'output_dir') and self.task.output_dir:
            return str(self.task.output_dir)
        
        # Fallback to default output structure
        base_dir = "/tmp/direct_tool_output"
        tool_dir = f"{base_dir}/{self.tool.name}"
        os.makedirs(tool_dir, exist_ok=True)
        return tool_dir
    
    def _execute_direct_command(self, cmd_parts: List[str]) -> bool:
        """
        Execute command directly using subprocess.
        
        This is the core method that prevents emulator duplication by
        avoiding the invoke_as_daemon fork mechanism.
        
        Args:
            cmd_parts: Command parts to execute
            
        Returns:
            Success status
        """
        try:
            timeout = getattr(self.task, 'timeout', 60)
            
            # Execute directly without daemon fork
            self.process = subprocess.Popen(
                cmd_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid  # Create new process group for clean termination
            )
            
            try:
                # Wait for completion with timeout
                stdout, stderr = self.process.communicate(timeout=timeout)
                
                # Log output for debugging
                if stdout:
                    self.logger.debug(f"Tool stdout: {stdout}")
                if stderr:
                    self.logger.debug(f"Tool stderr: {stderr}")
                
                return_code = self.process.returncode
                success = return_code == 0
                
                if not success:
                    self.logger.warning(f"Tool {self.tool.name} exited with code: {return_code}")
                
                return success
                
            except subprocess.TimeoutExpired:
                # Handle timeout by terminating process group
                self.logger.info(f"Tool {self.tool.name} timed out after {timeout}s")
                self._terminate_process_group()
                raise RVToolTimeoutError(
                    f"Tool {self.tool.name} execution timed out after {timeout} seconds",
                    tool_name=self.tool.name,
                    timeout_duration=timeout
                )
                
        except Exception as e:
            if self.process:
                self._terminate_process_group()
            raise e
        finally:
            self.process = None
    
    def _terminate_process_group(self) -> None:
        """Terminate the process group to clean up all child processes."""
        if self.process:
            try:
                # Terminate entire process group to clean up emulators
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                
                # Wait a moment for graceful shutdown
                time.sleep(2)
                
                # Force kill if still running
                if self.process.poll() is None:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    
            except (OSError, ProcessLookupError):
                # Process already terminated
                pass
    
    def cleanup_processes(self) -> None:
        """Clean up any hanging processes."""
        try:
            if self.process and self.process.poll() is None:
                self._terminate_process_group()
                
            # Additional cleanup for tool-specific processes
            if hasattr(self.tool, 'process_pattern') and self.tool.process_pattern:
                self.tool.kill_related_processes(self.tool.process_pattern)
                
        except Exception as e:
            self.logger.warning(f"Error during process cleanup: {e}")