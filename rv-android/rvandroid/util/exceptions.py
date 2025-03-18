# rvandroid/util/exceptions.py
# rvandroid/util/exceptions.py - Custom exception hierarchy

class RVAndroidError(Exception):
    """Base exception class for all RV-Android errors."""

    def __init__(self, message: str, cause: Exception = None):
        self.message = message
        self.cause = cause
        super().__init__(message)

    def __str__(self):
        cause_str = f" caused by {type(self.cause).__name__}: {self.cause}" if self.cause else ""
        return f"{type(self).__name__}: {self.message}{cause_str}"


class ConfigurationError(RVAndroidError):
    """Error raised when there's a problem with the configuration."""
    pass


class ResourceError(RVAndroidError):
    """Error raised when there's a problem with resource management."""
    pass


class NetworkError(RVAndroidError):
    """Error raised when there's a network-related problem."""
    pass


class EmulatorError(RVAndroidError):
    """Error raised when there's a problem with the Android emulator."""
    pass


class ADBError(NetworkError):
    """Error raised when there's a problem with ADB commands."""
    pass


class InstrumentationError(RVAndroidError):
    """Error raised when there's a problem with APK instrumentation."""
    pass


class AnalysisError(RVAndroidError):
    """Error raised when there's a problem with static or dynamic analysis."""
    pass


class TestExecutionError(RVAndroidError):
    """Error raised when there's a problem during test execution."""
    pass


class MonitorError(RVAndroidError):
    """Error raised when there's a problem with monitor generation or execution."""
    pass


class RvTimeoutError(RVAndroidError):
    """Error raised when an operation times out."""
    pass
