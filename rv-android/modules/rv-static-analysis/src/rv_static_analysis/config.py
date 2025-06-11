"""
Configuration management for rv-static-analysis module.

This module provides configuration management for static analysis tools
(GATOR, GESDA, REACH) with flexible path resolution and validation.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from rv_android_core.util.exceptions import ConfigurationError
from rv_android_core.constants import ENV_RVSEC_HOME, ENV_ANDROID_HOME, ENV_RT_JAR


class RVStaticAnalysisConfig:
    """
    Configuration manager for static analysis tools and environments.
    
    Manages paths for GATOR, GESDA, and REACH tools with priority-based resolution:
    1. Explicit parameters (highest priority)
    2. rvsec_root parameter + relative paths
    3. ENV_RVSEC_HOME environment variable + relative paths
    4. Error if no valid configuration source
    """
    
    def __init__(self,
                 rvsec_root: Optional[str] = None,
                 lib_dir: Optional[str] = None,
                 android_platforms_dir: Optional[str] = None,
                 android_jar: Optional[str] = None,
                 rt_jar: Optional[str] = None,
                 mop_dir: Optional[str] = None,
                 output_dir: Optional[str] = None,
                 working_dir: Optional[str] = None,
                 gesda_jar: Optional[str] = None,
                 gator_dir: Optional[str] = None,
                 reach_jar: Optional[str] = None,
                 validate_on_init: bool = True):
        """
        Initialize static analysis configuration.
        
        Args:
            rvsec_root: RVSEC installation root directory
            lib_dir: Directory containing static analysis tool JARs
            android_platforms_dir: Android SDK platforms directory
            android_jar: Android SDK JAR path (android.jar)
            rt_jar: Java runtime JAR path (rt.jar) - uses RV_RT_JAR environment variable
            mop_dir: Monitor-Oriented Programming specifications directory
            output_dir: Base output directory for analysis results
            working_dir: Working directory for temporary files
            gesda_jar: Explicit path to GESDA JAR file
            gator_dir: Explicit path to GATOR tools directory
            reach_jar: Explicit path to REACH JAR file
            validate_on_init: Whether to validate configuration on initialization
        
        Raises:
            ConfigurationError: If configuration is invalid and validate_on_init=True
        """
        # Store explicit parameters
        self.rvsec_root = rvsec_root
        self.lib_dir = lib_dir
        self.android_platforms_dir = android_platforms_dir
        self.android_jar = android_jar
        self.rt_jar = rt_jar
        self.mop_dir = mop_dir
        self.output_dir = output_dir
        self.working_dir = working_dir
        self.gesda_jar = gesda_jar
        self.gator_dir = gator_dir
        self.reach_jar = reach_jar
        
        # Apply path resolution strategy
        self._resolve_paths()
        
        # Validate configuration if requested
        if validate_on_init:
            self._validate_configuration()
    
    def _resolve_paths(self) -> None:
        """Resolve all configuration paths using priority strategy."""
        # Determine RVSEC root directory
        if not self.rvsec_root:
            self.rvsec_root = os.environ.get(ENV_RVSEC_HOME)
            if not self.rvsec_root:
                self.rvsec_root = os.getcwd()
        
        # Apply default paths based on RVSEC root
        self._apply_default_paths()
        
        # Ensure all paths are absolute
        self._normalize_paths()
    
    def _apply_default_paths(self) -> None:
        """Apply default path values based on RVSEC root."""
        rvsec_path = Path(self.rvsec_root)
        
        # Lib directory (contains all tools)
        if not self.lib_dir:
            self.lib_dir = str(rvsec_path / "lib")
        
        # Android SDK configuration
        if not self.android_platforms_dir:
            android_home = os.environ.get(ENV_ANDROID_HOME)
            if android_home:
                self.android_platforms_dir = str(Path(android_home) / "platforms")
        
        # Android JAR - try common Android SDK locations
        if not self.android_jar and self.android_platforms_dir:
            # Try Android API 29 first, then 28, 27
            for api_level in ["29", "28", "27", "26"]:
                candidate = Path(self.android_platforms_dir) / f"android-{api_level}" / "android.jar"
                if candidate.exists():
                    self.android_jar = str(candidate)
                    break
        
        # Java Runtime JAR - use RV_RT_JAR environment variable with SDKMAN fallback
        if not self.rt_jar:
            default_rt_jar = str(Path.home() / ".sdkman" / "candidates" / "java" / "8.0.302-open" / "jre" / "lib" / "rt.jar")
            self.rt_jar = os.environ.get(ENV_RT_JAR, default_rt_jar)
        
        # MOP directory for monitor specifications
        if not self.mop_dir:
            # Default to JCA specifications
            self.mop_dir = str(rvsec_path / "specs" / "jca")
        
        # Output directory
        if not self.output_dir:
            self.output_dir = str(rvsec_path / "out")
        
        # Working directory
        if not self.working_dir:
            self.working_dir = str(rvsec_path / "working")
        
        # Tool-specific paths
        lib_path = Path(self.lib_dir)
        
        if not self.gesda_jar:
            self.gesda_jar = str(lib_path / "gesda" / "rvsec-gesda.jar")
        
        if not self.gator_dir:
            self.gator_dir = str(lib_path / "gator")
        
        if not self.reach_jar:
            self.reach_jar = str(lib_path / "reach" / "rvsec-reach.jar")
    
    def _normalize_paths(self) -> None:
        """Convert all paths to absolute paths."""
        path_attributes = [
            'rvsec_root', 'lib_dir', 'android_platforms_dir', 'android_jar', 'rt_jar',
            'mop_dir', 'output_dir', 'working_dir', 'gesda_jar', 'gator_dir', 'reach_jar'
        ]
        
        for attr in path_attributes:
            value = getattr(self, attr)
            if value:
                setattr(self, attr, os.path.abspath(value))
    
    def _validate_configuration(self) -> None:
        """
        Validate configuration completeness and tool availability.
        
        Raises:
            ConfigurationError: If configuration is invalid
        """
        self._validate_required_paths()
        self._validate_tool_availability()
        self._validate_android_sdk()
        self._validate_mop_directory()
    
    def _validate_required_paths(self) -> None:
        """Validate that required paths are configured."""
        required_paths = {
            'lib_dir': self.lib_dir,
            'output_dir': self.output_dir,
            'working_dir': self.working_dir
        }
        
        for name, path in required_paths.items():
            if not path:
                raise ConfigurationError(f"Required path '{name}' is not configured")
    
    def _validate_tool_availability(self) -> None:
        """Validate that all static analysis tools are available."""
        # Validate tool components (not the logical tools returned by get_static_analysis_tools)
        components = self.get_tool_components()
        
        for component_name, component_path in components.items():
            if component_name == 'gator_python':
                # GATOR python script might not have .py extension
                if not os.path.isfile(component_path):
                    raise ConfigurationError(f"Static analysis tool component '{component_name}' not found: {component_path}")
            elif component_name in ['gesda_jar', 'gator_client_jar', 'reach_jar']:
                if not os.path.isfile(component_path):
                    raise ConfigurationError(f"Static analysis tool component '{component_name}' not found: {component_path}")
    
    def _validate_android_sdk(self) -> None:
        """Validate Android SDK and Java runtime configuration."""
        if not self.android_platforms_dir:
            raise ConfigurationError("Android platforms directory not configured")
        
        if not os.path.isdir(self.android_platforms_dir):
            raise ConfigurationError(f"Android platforms directory does not exist: {self.android_platforms_dir}")
        
        if not self.android_jar:
            raise ConfigurationError("Android JAR (android_jar) not configured")
        
        if not os.path.isfile(self.android_jar):
            raise ConfigurationError(f"Android JAR does not exist: {self.android_jar}")
        
        if not self.rt_jar:
            raise ConfigurationError(f"Java runtime JAR (rt_jar) not configured. Set {ENV_RT_JAR} environment variable")
        
        if not os.path.isfile(self.rt_jar):
            raise ConfigurationError(f"Java runtime JAR does not exist: {self.rt_jar}. Set {ENV_RT_JAR} environment variable to correct path.")
    
    def _validate_mop_directory(self) -> None:
        """Validate MOP specifications directory."""
        if not self.mop_dir:
            raise ConfigurationError("MOP specifications directory not configured")
        
        if not os.path.isdir(self.mop_dir):
            raise ConfigurationError(f"MOP specifications directory does not exist: {self.mop_dir}")
    
    def get_static_analysis_tools(self) -> Dict[str, str]:
        """
        Get paths to static analysis tools (3 logical tools: GESDA, GATOR, REACH).
        
        Returns:
            Dictionary mapping tool names to primary executable paths
        """
        return {
            'gesda': self.gesda_jar,
            'gator': self.gator_dir,
            'reach': self.reach_jar
        }
    
    def get_tool_components(self) -> Dict[str, str]:
        """
        Get detailed paths to all tool components for internal use.
        
        Returns:
            Dictionary mapping component names to executable paths
        """
        gator_path = Path(self.gator_dir)
        
        return {
            'gesda_jar': self.gesda_jar,
            'gator_python': str(gator_path / "gator"),
            'gator_client_jar': str(gator_path / "rvsec-gator-client.jar"),
            'reach_jar': self.reach_jar
        }
    
    def validate_apk_input(self, apk_path: str) -> None:
        """
        Validate APK input file.
        
        Args:
            apk_path: Path to APK file
        
        Raises:
            ConfigurationError: If APK is invalid
        """
        if not apk_path:
            raise ConfigurationError("APK path is required")
        
        if not os.path.isfile(apk_path):
            raise ConfigurationError(f"APK file does not exist: {apk_path}")
        
        if not apk_path.lower().endswith('.apk'):
            raise ConfigurationError(f"File is not an APK: {apk_path}")
    
    def get_tool_command(self, tool_name: str, apk_path: str, output_file: str, **kwargs) -> list:
        """
        Generate command line for static analysis tool execution.
        
        Args:
            tool_name: Name of tool ('gesda', 'gator', 'reach')
            apk_path: Path to APK file to analyze
            output_file: Path to output file
            **kwargs: Additional tool-specific arguments
        
        Returns:
            Command line as list of strings
        
        Raises:
            ConfigurationError: If tool is not supported
        """
        tools = self.get_static_analysis_tools()
        components = self.get_tool_components()
        
        if tool_name == 'gesda':
            return [
                'java', '-jar', components['gesda_jar'],
                '--android-dir', self.android_platforms_dir,
                '--rt-jar', self.rt_jar,
                '--output', output_file,
                '--apk', apk_path
            ]
        elif tool_name == 'gator':
            client_jar = kwargs.get('client_jar', components['gator_client_jar'])
            return [
                'python', components['gator_python'], 'a',
                '-p', apk_path,
                '--client-jar', client_jar,
                '--out', output_file,
                '-client', 'RvsecWtgClient'
            ]
        elif tool_name == 'reach':
            gesda_file = kwargs.get('gesda_file')
            if not gesda_file:
                raise ConfigurationError("REACH tool requires GESDA output file")
            
            timeout = kwargs.get('timeout', 300)
            return [
                'java', '-jar', components['reach_jar'],
                '--android-dir', self.android_platforms_dir,
                '--rt-jar', self.rt_jar,
                '--mop-dir', self.mop_dir,
                '--gesda', gesda_file,
                '--writer', 'csv',
                '--timeout', str(timeout),
                '--apk', apk_path,
                '--output', output_file
            ]
        else:
            raise ConfigurationError(f"Unsupported static analysis tool: {tool_name}")
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive configuration summary for debugging.
        
        Returns:
            Dictionary with configuration details
        """
        tools = self.get_static_analysis_tools()
        components = self.get_tool_components()
        
        return {
            'rvsec_integration': {
                'rvsec_root': self.rvsec_root,
                'lib_dir': self.lib_dir,
                'mop_dir': self.mop_dir,
                'output_dir': self.output_dir,
                'working_dir': self.working_dir
            },
            'java_android_integration': {
                'android_platforms_dir': getattr(self, 'android_platforms_dir', None),
                'android_jar': getattr(self, 'android_jar', None),
                'rt_jar': getattr(self, 'rt_jar', None)
            },
            'static_analysis_tools': {
                'gesda': tools['gesda'],
                'gator': tools['gator'],
                'reach': tools['reach']
            },
            'tool_components': {
                'gesda_jar': components['gesda_jar'],
                'gator_python': components['gator_python'],
                'gator_client_jar': components['gator_client_jar'],
                'reach_jar': components['reach_jar']
            },
            'tool_availability': {
                tool_name: os.path.isfile(tool_path) if tool_name != 'gator' else os.path.isdir(tool_path)
                for tool_name, tool_path in tools.items()
            },
            'validation_status': 'Validated'
        }
    
    def create_output_directories(self) -> None:
        """Create necessary output directories."""
        directories = [self.output_dir, self.working_dir]
        
        for directory in directories:
            if directory:
                os.makedirs(directory, exist_ok=True)