# rv_test_framework/util/port_manager.py
"""
Emulator port management for test framework parallel execution.

Provides EmulatorPortManager class for thread-safe allocation and validation
of emulator ports to prevent duplicated processes.

Inspired by RVSec_Paralelo implementation but adapted for test framework scope.
"""

import socket
import threading
from typing import Set, Optional
import logging


class EmulatorPortManager:
    """
    Thread-safe emulator port allocation manager for test framework.
    
    This class coordinates port allocation using socket validation to prevent
    emulator process duplication during parallel task execution.
    
    ### Key Features:
    - Socket validation: Confirms port is actually available via bind()
    - Thread-safe: Uses threading.Lock for internal pool coordination
    - Pool management: Tracks allocated ports internally
    - Auto-cleanup: Supports port release for resource management
    
    ### Design Decision:
    Uses threading.Lock (not multiprocessing.Lock) because test framework
    operates within single process with multiple threads.
    """
    
    # Thread synchronization for internal pool
    _lock = threading.Lock()
    _allocated_ports: Set[int] = set()
    _process_ports: dict = {}  # process_id -> allocated ports
    
    # Port ranges for emulator allocation
    MIN_EMULATOR_PORT = 5554
    MAX_EMULATOR_PORT = 5654  # Support up to 50 parallel emulators
    EMULATOR_PORT_STEP = 2    # ADB uses consecutive port pairs
    
    @classmethod
    def allocate_port(cls, process_id: str, base_port: int = None) -> int:
        """
        Allocate unique emulator port with socket validation.
        
        This method performs both internal pool checking and real socket
        validation to ensure the port is truly available.
        
        Args:
            process_id: Unique identifier for the requesting process
            base_port: Starting port for search (default: MIN_EMULATOR_PORT)
            
        Returns:
            Allocated port number that passed socket validation
            
        Raises:
            RuntimeError: If no available ports found in range
        """
        if base_port is None:
            base_port = cls.MIN_EMULATOR_PORT
            
        with cls._lock:
            # Search for available port with socket validation
            for port in range(base_port, cls.MAX_EMULATOR_PORT, cls.EMULATOR_PORT_STEP):
                if port not in cls._allocated_ports and cls._is_socket_available(port):
                    # Allocate port in internal pool
                    cls._allocated_ports.add(port)
                    
                    # Track process -> port mapping for cleanup
                    if process_id not in cls._process_ports:
                        cls._process_ports[process_id] = []
                    cls._process_ports[process_id].append(port)
                    
                    logging.info(f"EmulatorPortManager: Allocated port {port} for process {process_id}")
                    return port
            
            # No available ports found
            raise RuntimeError(
                f"No available emulator ports in range {base_port}-{cls.MAX_EMULATOR_PORT}. "
                f"Currently allocated: {sorted(cls._allocated_ports)}"
            )
    
    @classmethod
    def _is_socket_available(cls, port: int) -> bool:
        """
        Validate if port is actually available via socket binding.
        
        This is the core validation that prevents emulator duplication by
        confirming the port is not occupied by any process.
        
        Args:
            port: Port number to validate
            
        Returns:
            True if port is available for binding
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('localhost', port))
                return True
        except OSError:
            # Port is occupied or unavailable
            return False
    
    @classmethod
    def release_port(cls, process_id: str, port: int) -> bool:
        """
        Release allocated port for reuse.
        
        Args:
            process_id: Process that owns the port
            port: Port number to release
            
        Returns:
            True if port was successfully released
        """
        with cls._lock:
            if port in cls._allocated_ports:
                cls._allocated_ports.remove(port)
                
                # Remove from process tracking
                if process_id in cls._process_ports:
                    if port in cls._process_ports[process_id]:
                        cls._process_ports[process_id].remove(port)
                    
                    # Clean up empty process entries
                    if not cls._process_ports[process_id]:
                        del cls._process_ports[process_id]
                
                logging.info(f"EmulatorPortManager: Released port {port} from process {process_id}")
                return True
            
            return False
    
    @classmethod
    def release_process_ports(cls, process_id: str) -> int:
        """
        Release all ports allocated to a specific process.
        
        Args:
            process_id: Process identifier
            
        Returns:
            Number of ports released
        """
        with cls._lock:
            if process_id not in cls._process_ports:
                return 0
            
            ports_to_release = cls._process_ports[process_id].copy()
            released_count = 0
            
            for port in ports_to_release:
                if cls.release_port(process_id, port):
                    released_count += 1
            
            logging.info(f"EmulatorPortManager: Released {released_count} ports from process {process_id}")
            return released_count
    
    @classmethod
    def get_allocated_ports(cls) -> Set[int]:
        """
        Get currently allocated ports.
        
        Returns:
            Set of currently allocated port numbers
        """
        with cls._lock:
            return cls._allocated_ports.copy()
    
    @classmethod
    def get_port_status(cls) -> dict:
        """
        Get comprehensive port allocation status.
        
        Returns:
            Dictionary with allocation statistics and mappings
        """
        with cls._lock:
            return {
                'total_allocated': len(cls._allocated_ports),
                'allocated_ports': sorted(cls._allocated_ports),
                'available_range': f"{cls.MIN_EMULATOR_PORT}-{cls.MAX_EMULATOR_PORT}",
                'process_mappings': dict(cls._process_ports),
                'max_capacity': (cls.MAX_EMULATOR_PORT - cls.MIN_EMULATOR_PORT) // cls.EMULATOR_PORT_STEP
            }
    
    @classmethod
    def cleanup_all_ports(cls) -> int:
        """
        Emergency cleanup - release all allocated ports.
        
        Returns:
            Number of ports released
        """
        with cls._lock:
            released_count = len(cls._allocated_ports)
            cls._allocated_ports.clear()
            cls._process_ports.clear()
            
            logging.warning(f"EmulatorPortManager: Emergency cleanup released {released_count} ports")
            return released_count