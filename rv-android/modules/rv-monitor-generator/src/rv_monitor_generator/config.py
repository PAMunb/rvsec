import os
import glob
import subprocess
from typing import Optional, Dict, Any
from pathlib import Path

import rv_android_core.constants as constants


class ConfigurationError(Exception):
    """Raised when there's an error in the configuration."""
    pass


class RVGeneratorConfig:
    """
    Configuration management for RuntimeVerificationGenerator with flexible path resolution.
    
    The RVGeneratorConfig provides a sophisticated configuration system that supports
    multiple deployment scenarios from development environments to production systems.
    It implements an intelligent path resolution strategy with fallback mechanisms.

    ### Architectural Decisions:
    - Implements a priority-based path resolution system for maximum flexibility
    - Provides validation at initialization time to fail fast on configuration errors
    - Supports both environment-based and explicit configuration modes
    - Delegates to specialized validation methods for different configuration aspects
    - Uses pathlib for robust cross-platform path handling where applicable

    ### Role in the System:
    - Acts as the central configuration authority for monitor generation workflows
    - Provides validated and normalized paths for all required tools and directories
    - Enables deployment flexibility through multiple configuration sources
    - Ensures configuration consistency across different execution environments
    - Supports both automated discovery and explicit path specification
    
    ### Configuration Priority (highest to lowest):
    1. Individual tool paths explicitly provided (javamop_bin, rvmonitor_bin, etc.)
    2. Explicit rvsec_root parameter with relative path resolution
    3. ENV_RVSEC_HOME environment variable with relative path resolution
    4. Configuration error if no valid source is available
    """
    
    def __init__(self,
                 rvsec_root: Optional[str] = None,
                 javamop_bin: Optional[str] = None,
                 rvmonitor_bin: Optional[str] = None,
                 mop_specs_dir: Optional[str] = None,
                 aspects_dir: Optional[str] = None):
        """
        Initialize RVGeneratorConfig with intelligent path resolution and validation.
        
        The initialization process follows a strict priority order for path resolution,
        ensuring predictable behavior across different deployment scenarios. All paths
        are validated for existence and accessibility during initialization.
        
        Args:
            rvsec_root: Root directory of RVSEC installation. Used for automatic
                       path discovery when individual paths are not provided.
            javamop_bin: Explicit path to JavaMOP binary executable. Takes precedence
                        over automatic discovery.
            rvmonitor_bin: Explicit path to RV-Monitor binary executable. Takes precedence
                          over automatic discovery.
            mop_specs_dir: Directory containing MOP specification files (.mop). Must be
                          explicitly provided as it determines the type of monitored operations.
            aspects_dir: Directory containing custom AspectJ files (.aj). Takes precedence
                        over automatic discovery.
                        
        Raises:
            ConfigurationError: If path resolution fails or required tools are not accessible
        """
        self.javamop_bin = javamop_bin
        self.rvmonitor_bin = rvmonitor_bin
        self.mop_specs_dir = mop_specs_dir
        self.aspects_dir = aspects_dir
        
        # Resolve paths based on priority
        self._resolve_paths(rvsec_root)
        
        # Validate configuration
        self._validate_configuration()
    
    def _resolve_paths(self, rvsec_root: Optional[str]) -> None:
        """
        Execute intelligent path resolution based on configuration priority system.
        
        This method implements the core path resolution logic, following the established
        priority order to determine final paths for all required tools and directories.
        The resolution process is designed to support both development and production
        deployment scenarios.
        
        ### Resolution Strategy:
        1. Check if all individual paths are explicitly provided (highest priority)
        2. Use explicit rvsec_root for automatic path discovery
        3. Fall back to ENV_RVSEC_HOME environment variable
        4. Raise ConfigurationError if no valid configuration source exists
        
        Args:
            rvsec_root: Optional explicit RVSEC root directory
            
        Raises:
            ConfigurationError: If no valid configuration source is available
        """
        # Priority 1: Check if all critical individual paths are explicitly provided
        # Note: mop_specs_dir is always required as it determines monitored operations type
        tool_paths = [self.javamop_bin, self.rvmonitor_bin]
        
        if all(path is not None for path in tool_paths) and self.mop_specs_dir is not None:
            # All critical paths explicitly provided - highest priority resolution
            # aspects_dir will use default if not provided
            if self.aspects_dir is None:
                # Set default aspects_dir relative to mop_specs_dir if not provided
                self.aspects_dir = os.path.join(os.path.dirname(self.mop_specs_dir), 'aspect')
            return
        
        # Priority 2 & 3: Determine rvsec_root source for automatic path discovery
        resolved_rvsec_root = None
        
        if rvsec_root is not None:
            # Priority 2: Explicit rvsec_root provided
            resolved_rvsec_root = rvsec_root
        else:
            # Priority 3: Try ENV_RVSEC_HOME environment variable
            env_rvsec = os.getenv(constants.ENV_RVSEC_HOME)
            if env_rvsec:
                resolved_rvsec_root = env_rvsec
            else:
                # Priority 4: No valid configuration source available
                raise ConfigurationError(
                    "Configuration resolution failed. Must provide one of:\n"
                    "1. Individual paths: javamop_bin, rvmonitor_bin, mop_specs_dir\n"
                    "2. rvsec_root parameter for automatic discovery\n"
                    "3. ENV_RVSEC_HOME environment variable for automatic discovery"
                )
        
        # Perform automatic path discovery from resolved rvsec_root
        self._resolve_from_rvsec_root(resolved_rvsec_root)
    
    def _resolve_from_rvsec_root(self, rvsec_root: str) -> None:
        """
        Resolve individual tool paths from RVSEC root directory using standard layout.
        
        This method implements the standard RVSEC directory layout assumptions for
        automatic path discovery. It follows the conventional RVSEC installation
        structure to locate tools and specification directories.
        
        Args:
            rvsec_root: Validated RVSEC root directory path
        """
        # Resolve tool binaries using standard RVSEC layout
        if self.javamop_bin is None:
            self.javamop_bin = os.path.join(rvsec_root, "javamop", "bin", "javamop")
        
        if self.rvmonitor_bin is None:
            self.rvmonitor_bin = os.path.join(rvsec_root, "rv-monitor", "bin", "rv-monitor")
        
        # Critical: mop_specs_dir determines the type of monitored operations
        # User must explicitly specify which specification set to use (JCA, generic, custom)
        if self.mop_specs_dir is None:
            # Default to JCA specs for backward compatibility
            # TODO: Consider making this explicitly required in future versions
            mop_base_dir = os.path.join(rvsec_root, "rvsec", "rvsec-mop", "src", "main", "resources")
            self.mop_specs_dir = os.path.join(mop_base_dir, "jca")
        
        if self.aspects_dir is None:
            # Standard aspects directory location
            mop_base_dir = os.path.join(rvsec_root, "rvsec", "rvsec-mop", "src", "main", "resources")
            self.aspects_dir = os.path.join(mop_base_dir, "aspect")
    
    def _validate_configuration(self) -> None:
        """
        Execute comprehensive configuration validation to ensure operational readiness.
        
        This validation process performs extensive checks to verify that all configured
        paths and tools are accessible and functional. It's designed to fail fast during
        initialization rather than during execution, providing clear diagnostic information.
        
        ### Validation Phases:
        1. Binary existence and executable permissions verification
        2. Directory existence and accessibility checks
        3. Specification file availability verification
        4. Tool functionality validation through basic execution tests
        
        Raises:
            ConfigurationError: If any validation check fails with detailed diagnostic information
        """
        # Phase 1: Critical tool binary validation
        self._validate_tool_binary(self.javamop_bin, "JavaMOP")
        self._validate_tool_binary(self.rvmonitor_bin, "RV-Monitor")
        
        # Phase 2: Directory accessibility validation
        self._validate_directory(self.mop_specs_dir, "MOP specifications")
        self._validate_directory(self.aspects_dir, "AspectJ aspects")
        
        # Phase 3: Specification availability validation
        self._validate_mop_specifications()
        
        # Phase 4: Tool functionality validation
        self._validate_tool_functionality()
    
    def validate_output_directory(self, output_dir: str) -> None:
        """
        Validate that output directory can be created/written to.
        
        Args:
            output_dir: Directory where monitors will be generated
        """
        try:
            # Create directory if it doesn't exist
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = os.path.join(output_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
        except (OSError, PermissionError) as e:
            raise ConfigurationError(f"Cannot write to output directory: {output_dir} - {e}")
    
    def _validate_tool_binary(self, binary_path: str, tool_name: str) -> None:
        """
        Validate individual tool binary for existence and executable permissions.
        
        Args:
            binary_path: Path to the tool binary
            tool_name: Human-readable tool name for error messages
            
        Raises:
            ConfigurationError: If binary validation fails
        """
        if not os.path.isfile(binary_path):
            raise ConfigurationError(f"{tool_name} binary not found: {binary_path}")
        
        if not os.access(binary_path, os.X_OK):
            raise ConfigurationError(f"{tool_name} binary not executable: {binary_path}")
    
    def _validate_directory(self, directory_path: str, directory_purpose: str) -> None:
        """
        Validate directory existence and accessibility.
        
        Args:
            directory_path: Path to the directory
            directory_purpose: Human-readable purpose for error messages
            
        Raises:
            ConfigurationError: If directory validation fails
        """
        if not os.path.isdir(directory_path):
            raise ConfigurationError(f"{directory_purpose} directory not found: {directory_path}")
        
        if not os.access(directory_path, os.R_OK):
            raise ConfigurationError(f"{directory_purpose} directory not readable: {directory_path}")
    
    def _validate_mop_specifications(self) -> None:
        """
        Validate availability of MOP specification files in the configured directory.
        
        Raises:
            ConfigurationError: If no MOP specifications are found
        """
        mop_files = glob.glob(os.path.join(self.mop_specs_dir, f"*{constants.EXTENSION_MOP}"))
        if not mop_files:
            raise ConfigurationError(
                f"No MOP specification files (*{constants.EXTENSION_MOP}) found in: {self.mop_specs_dir}\n"
                f"Available specification sets:\n"
                f"  - JCA: Java Cryptography Architecture monitored operations\n"
                f"  - Generic: General programming pattern monitored operations"
            )
    
    def _validate_tool_functionality(self) -> None:
        """
        Validate tool functionality through basic execution tests.
        
        This method performs lightweight functionality tests to ensure tools
        can be executed successfully in the current environment.
        
        Raises:
            ConfigurationError: If tool functionality validation fails
        """
        # Test JavaMOP functionality
        try:
            result = subprocess.run(
                [self.javamop_bin, '-h'], 
                capture_output=True, 
                timeout=10,
                text=True
            )
            # JavaMOP may return non-zero exit status with -h, but should produce output
            if not result.stdout and not result.stderr:
                raise ConfigurationError(f"JavaMOP produced no output: {self.javamop_bin}")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise ConfigurationError(f"JavaMOP functionality test failed: {self.javamop_bin}\nError: {e}")
        
        # Test RV-Monitor functionality
        try:
            result = subprocess.run(
                [self.rvmonitor_bin, '-h'], 
                capture_output=True, 
                timeout=10,
                text=True
            )
            # RV-Monitor may return non-zero exit status with -h, but should produce output
            if not result.stdout and not result.stderr:
                raise ConfigurationError(f"RV-Monitor produced no output: {self.rvmonitor_bin}")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise ConfigurationError(f"RV-Monitor functionality test failed: {self.rvmonitor_bin}\nError: {e}")
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive summary of current configuration.
        
        Returns:
            Dict containing detailed configuration information
        """
        mop_files = glob.glob(os.path.join(self.mop_specs_dir, f"*{constants.EXTENSION_MOP}"))
        
        return {
            'tools': {
                'javamop_bin': self.javamop_bin,
                'rvmonitor_bin': self.rvmonitor_bin
            },
            'directories': {
                'mop_specs_dir': self.mop_specs_dir,
                'aspects_dir': self.aspects_dir
            },
            'specifications': {
                'count': len(mop_files),
                'files': [os.path.basename(f) for f in mop_files],
                'type': 'JCA' if 'jca' in self.mop_specs_dir.lower() else 'Generic/Custom'
            },
            'validation_status': 'Validated'
        }
    
    def __str__(self) -> str:
        """Detailed string representation for debugging and logging."""
        return (
            f"RVGeneratorConfig(\n"
            f"  JavaMOP: {self.javamop_bin}\n"
            f"  RV-Monitor: {self.rvmonitor_bin}\n"
            f"  Specifications: {self.mop_specs_dir}\n"
            f"  Aspects: {self.aspects_dir}\n"
            f"  Status: Validated\n"
            f")"
        )