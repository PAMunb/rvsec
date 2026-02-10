"""
Thread-safe pool of emulator ports for parallel calibration.

Each port corresponds to an Android emulator instance.
Ports are allocated in pairs (5554, 5556, 5558, ...) as required by the Android SDK.
"""

import queue


class EmulatorPool:
    """Thread-safe pool of emulator ports for parallel calibration."""

    def __init__(self, n_emulators: int, base_port: int = 5554):
        """
        Initialize port pool.

        Args:
            n_emulators: Number of emulator ports to allocate
            base_port: Starting port (default: 5554)
        """
        self._ports: queue.Queue[int] = queue.Queue()
        for i in range(n_emulators):
            self._ports.put(base_port + 2 * i)

    def acquire(self, timeout: float = None) -> int:
        """Acquire a port. Blocks until one is available."""
        return self._ports.get(timeout=timeout)

    def release(self, port: int) -> None:
        """Release a port back to the pool."""
        self._ports.put(port)
