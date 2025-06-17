"""
Command execution result model for RV-Android Core.

This module provides a validated model for representing command execution results
with standardized error handling and type safety.
"""

from typing import Optional
from pydantic import Field

from rv_android_core.util.validation.base import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


@validated_model(['code', 'stdout', 'stderr'])
class CommandResult(BaseValidatedModel):
    """
    Represents the result of a command execution with comprehensive validation.
    
    ### Architectural Decisions:
    - Inherits from BaseValidatedModel for consistent validation behavior
    - Supports both positional and named parameter construction
    - Uses correct types based on subprocess.communicate() return values
    - Integrates with the system's error handling and logging infrastructure
    
    ### Role in the System:
    - Standardizes command execution results across all system components
    - Provides type-safe access to command output and exit codes
    - Enables consistent error handling for command execution scenarios
    - Supports serialization for logging and debugging purposes
    
    ### Data Types:
    - code: int (process exit code from subprocess)
    - stdout: bytes (raw output from subprocess.communicate())
    - stderr: bytes (raw error output from subprocess.communicate())
    
    ### Usage Examples:
    ```python
    # Legacy positional style (backwards compatible)
    result = CommandResult(0, b"success output", b"")
    
    # Modern named parameter style
    result = CommandResult(
        code=0,
        stdout=b"success output", 
        stderr=b""
    )
    
    # Access properties with validation
    if result.is_success():
        print(f"Command output: {result.stdout.decode()}")
    ```
    """
    
    code: int = Field(
        ...,
        description="Exit code from command execution",
        ge=-128,
        le=127
    )
    
    stdout: Optional[bytes] = Field(
        default=b"",
        description="Standard output from command execution (raw bytes from subprocess, None if redirected)"
    )
    
    stderr: Optional[bytes] = Field(
        default=b"",
        description="Standard error output from command execution (raw bytes from subprocess, None if redirected)"
    )
    
    def is_success(self) -> bool:
        """
        Check if the command executed successfully.
        
        Returns:
            True if exit code is 0, False otherwise
        """
        return self.code == 0
    
    def is_failure(self) -> bool:
        """
        Check if the command failed.
        
        Returns:
            True if exit code is non-zero, False otherwise
        """
        return self.code != 0
    
    def has_output(self) -> bool:
        """
        Check if the command produced any output.
        
        Returns:
            True if stdout or stderr is non-empty, False otherwise
        """
        stdout_has_content = self.stdout and bool(self.stdout.strip())
        stderr_has_content = self.stderr and bool(self.stderr.strip())
        return stdout_has_content or stderr_has_content
    
    def has_error_output(self) -> bool:
        """
        Check if the command produced error output.
        
        Returns:
            True if stderr is non-empty, False otherwise
        """
        return self.stderr is not None and bool(self.stderr.strip())
    
    def get_combined_output(self, encoding: str = 'utf-8', errors: str = 'replace') -> str:
        """
        Get combined stdout and stderr output as decoded string.
        
        Args:
            encoding: Character encoding to use for decoding bytes
            errors: How to handle encoding errors ('replace', 'ignore', 'strict')
        
        Returns:
            Combined output string with stderr appended to stdout
        """
        output_parts = []
        
        if self.stdout and self.stdout.strip():
            stdout_decoded = self.stdout.strip().decode(encoding, errors)
            output_parts.append(stdout_decoded)
        
        if self.stderr and self.stderr.strip():
            stderr_decoded = self.stderr.strip().decode(encoding, errors)
            output_parts.append(f"STDERR: {stderr_decoded}")
        
        return "\n".join(output_parts)
    
    def get_stdout_text(self, encoding: str = 'utf-8', errors: str = 'replace') -> str:
        """
        Get stdout as decoded string.
        
        Args:
            encoding: Character encoding to use for decoding bytes
            errors: How to handle encoding errors ('replace', 'ignore', 'strict')
            
        Returns:
            Decoded stdout string, empty string if stdout is None
        """
        if self.stdout is None:
            return ""
        return self.stdout.decode(encoding, errors)
    
    def get_stderr_text(self, encoding: str = 'utf-8', errors: str = 'replace') -> str:
        """
        Get stderr as decoded string.
        
        Args:
            encoding: Character encoding to use for decoding bytes
            errors: How to handle encoding errors ('replace', 'ignore', 'strict')
            
        Returns:
            Decoded stderr string, empty string if stderr is None
        """
        if self.stderr is None:
            return ""
        return self.stderr.decode(encoding, errors)
    
    def __str__(self) -> str:
        """
        Get string representation of the command result.
        
        Returns:
            String representation including exit code and output summary
        """
        status = "SUCCESS" if self.is_success() else "FAILED"
        output_summary = "with output" if self.has_output() else "no output"
        return f"CommandResult(code={self.code}, status={status}, {output_summary})"