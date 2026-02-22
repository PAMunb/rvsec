"""
JAR file resolution utility for Android testing tools.

This module provides centralized JAR file resolution capabilities for tools
that require JAR-based execution, implementing consistent search patterns
and comprehensive error handling across the testing framework.
"""

import os
from typing import Dict, List, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import JarNotFoundError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


@ErrorHandler.handle_errors(component="JarResolver", phase="resolve_jar")
class JarResolver:
    """
    Centralized utility for resolving JAR file paths across testing tools.

    ### Architectural Decisions:
    - Implements standardized JAR file resolution with consistent search patterns
    - Provides comprehensive error handling and logging for JAR operations
    - Centralizes search path logic for easier maintenance and configuration
    - Uses dependency injection pattern compatible with rv-android-core infrastructure
    - Eliminates code duplication across JAR-dependent tools (APE, FastBot, DroidMate)

    ### Role in the System:
    - Acts as centralized JAR file discovery and resolution facility
    - Provides uniform JAR search behavior across all testing tools
    - Enables standardized error reporting for missing tool dependencies
    - Facilitates consistent tool installation validation and troubleshooting
    - Supports flexible configuration of JAR search locations

    ### Key Features:
    - Multiple search path strategies for different deployment scenarios
    - Environment variable based configuration support
    - Comprehensive logging for troubleshooting JAR resolution issues
    - Detailed error reporting with search path information
    - Integration with rv-android-core error handling infrastructure

    ### Usage Pattern:
    Tools requiring JAR files should use this resolver instead of implementing
    custom search logic, ensuring consistent behavior and error handling.
    """

    def __init__(self):
        """
        Initialize JAR resolver with logging and error handling infrastructure.
        """
        # Initialize rv-android-core infrastructure components
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_android_core.jar_resolver", {CONTEXT_COMPONENT: "JarResolver"}
        )

    def resolve_jar_path(
        self, jar_name: str, search_paths: Optional[List[str]] = None
    ) -> str:
        """
        Resolve JAR file path from search locations with standardized patterns.

        Implements comprehensive search strategy across common installation
        locations, environment variables, and tool-specific directories.

        Args:
            jar_name: Name of the JAR file to locate (e.g., "ape.jar")
            search_paths: Optional list of additional directories to search

        Returns:
            Absolute path to located JAR file

        Raises:
            JarNotFoundError: If JAR file cannot be located in any search path
        """
        self.logger.debug(f"Resolving JAR file: {jar_name}")

        # Build comprehensive search path list
        all_search_paths = self._build_search_paths(jar_name, search_paths)

        # Search for JAR file in all paths
        for path in all_search_paths:
            if path and os.path.isfile(path):
                self.logger.debug(f"Found {jar_name} at: {path}")
                return os.path.abspath(path)

        # JAR file not found in any location
        self.logger.error(
            f"JAR file {jar_name} not found in {len(all_search_paths)} search locations"
        )
        raise JarNotFoundError(
            f"JAR file '{jar_name}' not found in search paths",
            jar_name=jar_name,
            search_paths=all_search_paths,
        )

    def resolve_multiple_jars(
        self, jar_names: List[str], search_paths: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Resolve multiple JAR files with consistent search strategy.

        Efficiently resolves multiple JAR files required by complex tools
        while providing detailed error information for missing dependencies.

        Args:
            jar_names: List of JAR file names to locate
            search_paths: Optional list of additional directories to search

        Returns:
            Dictionary mapping JAR names to their resolved absolute paths

        Raises:
            JarNotFoundError: If any required JAR file cannot be located
        """
        self.logger.debug(f"Resolving {len(jar_names)} JAR files: {jar_names}")

        resolved_jars = {}
        missing_jars = []

        for jar_name in jar_names:
            try:
                resolved_path = self.resolve_jar_path(jar_name, search_paths)
                resolved_jars[self._get_jar_key(jar_name)] = resolved_path
            except JarNotFoundError:
                missing_jars.append(jar_name)

        # Report all missing JARs together
        if missing_jars:
            error_msg = f"Missing JAR files: {missing_jars}"
            self.logger.error(error_msg)
            raise JarNotFoundError(
                error_msg,
                jar_name=", ".join(missing_jars),
                search_paths=self._build_search_paths("", search_paths),
            )

        self.logger.info(f"Successfully resolved {len(resolved_jars)} JAR files")
        return resolved_jars

    def resolve_resource_directory(
        self, resource_name: str, search_paths: Optional[List[str]] = None
    ) -> str:
        """
        Resolve resource directory path (e.g., libs directory for FastBot).

        Args:
            resource_name: Name of the resource directory to locate (e.g., "libs")
            search_paths: Optional list of additional directories to search

        Returns:
            Absolute path to located resource directory

        Raises:
            JarNotFoundError: If resource directory cannot be located in any search path
        """
        self.logger.debug(f"Resolving resource directory: {resource_name}")

        # Build search paths for directories
        all_search_paths = self._build_resource_search_paths(
            resource_name, search_paths
        )

        # Search for resource directory in all paths
        for path in all_search_paths:
            if path and os.path.isdir(path):
                self.logger.debug(f"Found {resource_name} directory at: {path}")
                return os.path.abspath(path)

        # Resource directory not found in any location
        self.logger.error(
            f"Resource directory {resource_name} not found in {len(all_search_paths)} search locations"
        )
        raise JarNotFoundError(
            f"Resource directory '{resource_name}' not found in search paths",
            jar_name=resource_name,
            search_paths=all_search_paths,
        )

    def _build_resource_search_paths(
        self, resource_name: str, additional_paths: Optional[List[str]] = None
    ) -> List[str]:
        """
        Build search paths for resource directories.

        Args:
            resource_name: Name of the resource directory
            additional_paths: Optional additional directories to include

        Returns:
            List of absolute paths to search for the resource directory
        """
        search_paths = []

        # 1. HIGHEST PRIORITY: Additional paths from tools (e.g., os.path.dirname(__file__))
        if additional_paths:
            for path in additional_paths:
                if path and path.strip():
                    # Add the resource directory to the path
                    search_paths.append(os.path.join(path, resource_name))

        # 2. RVSEC_HOME based paths
        rvsec_home = os.environ.get("RVSEC_HOME", "")
        if rvsec_home:
            # Try to detect tool from calling context (simple heuristic)
            tool_subdir = "fastbot"  # Default, could be improved
            rvsec_paths = [
                os.path.join(
                    rvsec_home,
                    "rv-android",
                    "modules",
                    "rv-tools",
                    "src",
                    "rv_tools",
                    "builtin",
                    tool_subdir,
                    resource_name,
                ),
                os.path.join(
                    rvsec_home, "rv-android", "tools", tool_subdir, resource_name
                ),
                os.path.join(rvsec_home, "tools", tool_subdir, resource_name),
            ]
            search_paths.extend(rvsec_paths)

        # 3. Standard paths
        search_paths.extend(
            [
                resource_name,  # Current directory
                os.path.join(".", resource_name),
                os.path.join("..", resource_name),
                os.path.join("tools", resource_name),
            ]
        )

        # Convert to absolute paths and filter out empty strings
        absolute_paths = []
        for path in search_paths:
            if path and path.strip():
                absolute_path = os.path.abspath(path)
                if absolute_path not in absolute_paths:
                    absolute_paths.append(absolute_path)

        return absolute_paths

    def _build_search_paths(
        self, jar_name: str, additional_paths: Optional[List[str]] = None
    ) -> List[str]:
        """
        Build comprehensive search path list for JAR file resolution.

        Constructs search paths following standardized patterns with proper priority:
        1. Additional paths (highest priority - tool-specific directories)
        2. RVSEC_HOME based paths
        3. Environment variables and standard locations

        Args:
            jar_name: Name of the JAR file being searched
            additional_paths: Optional additional directories to include (highest priority)

        Returns:
            List of absolute paths to search for the JAR file
        """
        search_paths = []
        tool_subdir = self._get_tool_subdir_from_jar(jar_name)

        # 1. HIGHEST PRIORITY: Additional paths from tools (e.g., os.path.dirname(__file__))
        if additional_paths:
            for path in additional_paths:
                if path and path.strip():
                    # Check if path is a directory or direct file path
                    if os.path.isdir(path):
                        search_paths.append(os.path.join(path, jar_name))
                    else:
                        search_paths.append(path)

        # 2. RVSEC_HOME based paths (second priority)
        rvsec_home = os.environ.get("RVSEC_HOME", "")
        if rvsec_home:
            rvsec_paths = [
                os.path.join(
                    rvsec_home,
                    "rv-android",
                    "modules",
                    "rv-tools",
                    "src",
                    "rv_tools",
                    "builtin",
                    tool_subdir,
                    jar_name,
                ),
                os.path.join(rvsec_home, "rv-android", "tools", tool_subdir, jar_name),
                os.path.join(rvsec_home, "tools", tool_subdir, jar_name),
            ]
            search_paths.extend(rvsec_paths)

        # 3. Environment variable based paths
        tools_dir = os.environ.get("TOOLS_DIR", "")
        if tools_dir:
            search_paths.append(os.path.join(tools_dir, tool_subdir, jar_name))

        # 4. Standard installation paths
        search_paths.extend(
            [
                f"/opt/rv-android/tools/{tool_subdir}/{jar_name}",
                f"./tools/{tool_subdir}/{jar_name}",
                f"../tools/{tool_subdir}/{jar_name}",
                f"/opt/android/{tool_subdir}/{jar_name}",
                os.path.expanduser(f"~/android/{tool_subdir}/{jar_name}"),
                os.path.expanduser(f"~/.rv-android/tools/{tool_subdir}/{jar_name}"),
            ]
        )

        # 5. Current directory and common relative paths (lowest priority)
        search_paths.extend(
            [
                jar_name,  # Current directory
                os.path.join(".", jar_name),
                os.path.join("..", jar_name),
                os.path.join("tools", jar_name),
            ]
        )

        # Convert to absolute paths and filter out empty strings
        absolute_paths = []
        for path in search_paths:
            if path and path.strip():
                try:
                    abs_path = os.path.abspath(path)
                    if abs_path not in absolute_paths:  # Avoid duplicates
                        absolute_paths.append(abs_path)
                except (OSError, ValueError):
                    # Skip invalid paths
                    continue

        return absolute_paths

    def _get_tool_subdir_from_jar(self, jar_name: str) -> str:
        """
        Determine tool subdirectory name from JAR filename.

        Maps JAR file names to their corresponding tool directory names
        following established tool organization patterns.

        Args:
            jar_name: Name of the JAR file

        Returns:
            Tool subdirectory name
        """
        jar_to_tool_map = {
            "ape.jar": "ape",
            "fastbot-thirdpart.jar": "fastbot",
            "framework.jar": "fastbot",
            "monkeyq.jar": "fastbot",
            "droidmate-2-X.X.X-all.jar": "droidmate",
            "droidmate.jar": "droidmate",
        }

        # Direct mapping lookup
        if jar_name in jar_to_tool_map:
            return jar_to_tool_map[jar_name]

        # Pattern-based detection for versioned JARs
        if "droidmate" in jar_name.lower():
            return "droidmate"
        elif "fastbot" in jar_name.lower():
            return "fastbot"
        elif "ape" in jar_name.lower():
            return "ape"

        # Default: use jar name without extension
        return os.path.splitext(jar_name)[0]

    def _get_jar_key(self, jar_name: str) -> str:
        """
        Generate standardized key for JAR file in result dictionary.

        Creates consistent key names for JAR files to enable uniform
        access patterns across different tools.

        Args:
            jar_name: Name of the JAR file

        Returns:
            Standardized key for the JAR file
        """
        # Map specific JAR files to standard keys
        key_map = {
            "fastbot-thirdpart.jar": "fastbot_thirdpart",
            "framework.jar": "framework",
            "monkeyq.jar": "monkeyq",
            "ape.jar": "ape",
        }

        if jar_name in key_map:
            return key_map[jar_name]

        # Generate key from filename
        base_name = os.path.splitext(jar_name)[0]
        return base_name.lower().replace("-", "_").replace(".", "_")

    def verify_jar_accessibility(self, jar_path: str) -> bool:
        """
        Verify that a JAR file is accessible and readable.

        Performs comprehensive validation of JAR file accessibility
        including existence, readability, and basic integrity checks.

        Args:
            jar_path: Path to the JAR file to verify

        Returns:
            True if JAR file is accessible, False otherwise
        """
        try:
            if not os.path.exists(jar_path):
                self.logger.warning(f"JAR file does not exist: {jar_path}")
                return False

            if not os.path.isfile(jar_path):
                self.logger.warning(f"Path is not a file: {jar_path}")
                return False

            if not os.access(jar_path, os.R_OK):
                self.logger.warning(f"JAR file is not readable: {jar_path}")
                return False

            # Basic size check
            file_size = os.path.getsize(jar_path)
            if file_size == 0:
                self.logger.warning(f"JAR file is empty: {jar_path}")
                return False

            self.logger.debug(f"JAR file verified: {jar_path} ({file_size} bytes)")
            return True

        except OSError as e:
            self.logger.warning(f"Error verifying JAR file {jar_path}: {e}")
            return False

    def get_search_paths_info(
        self, jar_name: str, additional_paths: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        Get detailed information about search paths for debugging.

        Provides comprehensive information about JAR resolution search paths
        including existence status and accessibility for troubleshooting.

        Args:
            jar_name: Name of the JAR file
            additional_paths: Optional additional directories to include

        Returns:
            Dictionary with search path information and status
        """
        search_paths = self._build_search_paths(jar_name, additional_paths)

        path_info = {
            "jar_name": jar_name,
            "total_paths": len(search_paths),
            "paths": [],
        }

        for path in search_paths:
            path_status = {
                "path": path,
                "exists": os.path.exists(path),
                "is_file": os.path.isfile(path) if os.path.exists(path) else False,
                "readable": os.access(path, os.R_OK) if os.path.exists(path) else False,
                "size": os.path.getsize(path) if os.path.isfile(path) else 0,
            }
            path_info["paths"].append(path_status)

        return path_info
