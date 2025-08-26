"""
Process cleanup utility for test framework.

This module provides aggressive cleanup of emulator processes to prevent
accumulation during parallel execution, addressing cleanup failures in
the core EmulatorManager without modifying other modules.
"""

import subprocess
import time
import signal
import os
from typing import List, Tuple
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import LOG_START, LOG_COMPLETE, LOG_ERROR


class ProcessCleaner:
    """
    Aggressive process cleanup for emulator processes.
    
    This class provides cleanup functionality specifically for the test framework
    to handle emulator process cleanup that may fail in the standard EmulatorManager.
    """
    
    def __init__(self):
        """Initialize process cleaner with logging."""
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_test_framework.util.process_cleaner"
        )
    
    def get_emulator_processes(self) -> List[Tuple[int, str]]:
        """
        Get list of running emulator processes.
        
        Returns:
            List of tuples (pid, command_line) for each emulator process
        """
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            processes = []
            
            for line in result.stdout.split('\n'):
                if 'qemu-system' in line and 'grep' not in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[1])
                            command = ' '.join(parts[10:]) if len(parts) > 10 else line
                            processes.append((pid, command))
                        except ValueError:
                            continue
            
            return processes
            
        except Exception as e:
            self.logger.warning(f"Failed to get emulator processes: {e}")
            return []
    
    def cleanup_emulator_processes(self, device_ports: List[int] = None) -> int:
        """
        Clean up emulator processes, optionally filtered by device ports.
        
        Args:
            device_ports: Optional list of device ports to target for cleanup.
                         If None, cleans up all emulator processes.
        
        Returns:
            Number of processes cleaned up
        """
        with self.logger.with_context(phase="cleanup_emulator_processes"):
            self.logger.info(LOG_START.format(phase="aggressive emulator process cleanup"))
            
            initial_processes = self.get_emulator_processes()
            if not initial_processes:
                self.logger.info("No emulator processes found - cleanup not needed")
                return 0
            
            self.logger.info(f"Found {len(initial_processes)} emulator processes to clean up")
            
            # Filter by device ports if specified
            target_processes = []
            if device_ports:
                for pid, command in initial_processes:
                    for port in device_ports:
                        if f"-port {port}" in command:
                            target_processes.append((pid, command))
                            break
            else:
                target_processes = initial_processes
            
            if not target_processes:
                self.logger.info("No matching emulator processes found for cleanup")
                return 0
            
            self.logger.info(f"Targeting {len(target_processes)} processes for cleanup")
            
            cleaned_count = 0
            
            # Phase 1: Try graceful termination (SIGTERM)
            for pid, command in target_processes:
                try:
                    self.logger.debug(f"Sending SIGTERM to PID {pid}")
                    os.kill(pid, signal.SIGTERM)
                    cleaned_count += 1
                except ProcessLookupError:
                    self.logger.debug(f"Process {pid} already terminated")
                except PermissionError:
                    self.logger.warning(f"Permission denied for PID {pid}")
                except Exception as e:
                    self.logger.warning(f"Failed to terminate PID {pid}: {e}")
            
            # Wait for graceful shutdown
            if cleaned_count > 0:
                self.logger.info(f"Sent SIGTERM to {cleaned_count} processes, waiting 5 seconds...")
                time.sleep(5)
            
            # Phase 2: Check what's still running and force kill if needed
            remaining_processes = []
            for pid, command in target_processes:
                try:
                    # Check if process still exists
                    os.kill(pid, 0)  # Signal 0 just checks existence
                    remaining_processes.append((pid, command))
                except ProcessLookupError:
                    # Process is gone, good
                    pass
                except Exception as e:
                    self.logger.debug(f"Error checking PID {pid}: {e}")
            
            # Force kill remaining processes
            force_killed = 0
            for pid, command in remaining_processes:
                try:
                    self.logger.warning(f"Force killing stubborn process PID {pid}")
                    os.kill(pid, signal.SIGKILL)
                    force_killed += 1
                except ProcessLookupError:
                    pass  # Already gone
                except Exception as e:
                    self.logger.error(f"Failed to force kill PID {pid}: {e}")
            
            if force_killed > 0:
                self.logger.warning(f"Force killed {force_killed} stubborn processes")
                time.sleep(2)  # Brief wait after force kill
            
            # Final verification
            final_processes = self.get_emulator_processes()
            total_cleaned = len(initial_processes) - len(final_processes)
            
            if len(final_processes) == 0:
                self.logger.info(LOG_COMPLETE.format(phase=f"cleanup of {total_cleaned} emulator processes"))
            else:
                remaining_pids = [str(pid) for pid, _ in final_processes]
                self.logger.warning(f"Cleanup incomplete: {len(final_processes)} processes still running (PIDs: {', '.join(remaining_pids)})")
            
            return total_cleaned
    
    def cleanup_specific_ports(self, device_ports: List[int]) -> int:
        """
        Clean up emulators on specific device ports.
        
        Args:
            device_ports: List of device ports (e.g., [5554, 5556])
            
        Returns:
            Number of processes cleaned up
        """
        return self.cleanup_emulator_processes(device_ports)
    
    def cleanup_all_emulators(self) -> int:
        """
        Clean up all running emulator processes.
        
        Returns:
            Number of processes cleaned up
        """
        return self.cleanup_emulator_processes(device_ports=None)