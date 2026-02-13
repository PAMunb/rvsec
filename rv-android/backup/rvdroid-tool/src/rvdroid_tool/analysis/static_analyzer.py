"""
Enhanced static analyzer for RVDroid.

This module provides a specialized component for deep integration with static analysis data,
enabling more effective testing by leveraging method reachability, specifications, and 
window transition graph information to guide exploration.
"""

from typing import Dict, Any, List, Optional, Set, Tuple

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.classes import Classes, Method, Clazz
from rv_android_core.domain.window import Windows, Window
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance_monitor import PerformanceMonitor


class EnhancedStaticAnalyzer:
    """
    Provides deep integration with static analysis for improved testing targeting.
    
    ### Architectural Decisions:
    - Implements a layered approach to static data processing and analysis
    - Exposes rich interfaces for accessing structured static analysis insights
    - Extracts and categorizes monitored methods by type and specification
    - Builds optimized indexes for efficient runtime lookups
    - Maintains window transition relationships for guided navigation
    
    ### Role in the System:
    - Serves as the bridge between static analysis and runtime testing
    - Provides rich contextual information to guide exploration strategies
    - Enables specification-aware testing by exposing monitored method relationships
    - Optimizes exploration by identifying high-value navigation paths
    - Supports advanced test generation with static insights
    
    ### Key Considerations:
    - Processing efficiency for large codebase analysis
    - Memory optimization for representation of complex relationships
    - Incremental updates during exploration
    - Clear separation between different specification types
    - Support for both JCA crypto and general API specifications
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the enhanced static analyzer.
        
        Args:
            static_data: Optional static analysis data
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.analysis.static_analyzer",
            {CONTEXT_COMPONENT: "EnhancedStaticAnalyzer"}
        )
        
        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor.get_instance()
        
        # Store static data
        self.static_data = static_data
        
        # Monitored methods categorization
        # Key: method signature, Value: specification type and details
        self.monitored_methods: Dict[str, Dict[str, Any]] = {}
        
        # Map of activity names to corresponding window objects
        self.activity_window_map: Dict[str, Window] = {}
        
        # Map component IDs to potential methods that can be reached
        self.component_method_map: Dict[str, Set[str]] = {}
        
        # Specification types seen in this application
        self.specification_types: Set[str] = set()
        
        # Indexes for efficient lookup
        # Maps method signature to all UI components that can reach it
        self.method_component_index: Dict[str, Set[str]] = {}
        
        # Store potential navigation paths
        self.navigation_paths: Dict[str, List[Dict[str, Any]]] = {}
        
        # Process static data if provided
        if static_data:
            self._initialize_from_static_data()
            
        self.logger.info("Initialized enhanced static analyzer")
            
    def _initialize_from_static_data(self) -> None:
        """
        Initialize the analyzer with static analysis data.
        
        Processes and indexes the static data to enable efficient runtime
        access to method reachability, specifications, and navigation paths.
        """
        if not self.static_data:
            self.logger.warning("No static analysis data provided")
            return
            
        with self.performance_monitor.measure_time("initialize_static_analyzer"):
            # Process classes and methods
            self._process_classes_and_methods()
            
            # Process window transition graph
            self._process_window_transition_graph()
            
            # Build navigation paths
            self._build_navigation_paths()
            
            # Log initialization summary
            self._log_initialization_summary()
    
    def _process_classes_and_methods(self) -> None:
        """
        Process classes and methods from static analysis data.
        
        Extracts and categorizes monitored methods, builds indexes for
        component-method relationships, and identifies specification types.
        """
        if not self.static_data or not self.static_data.classes:
            return
            
        classes = self.static_data.classes
        
        # JCA crypto specification keywords (case insensitive)
        crypto_keywords = {"cipher", "encrypt", "decrypt", "key", "mac", "hash", "digest", 
                          "random", "secure", "sign", "verify", "certificate"}
        
        # General API specifications (iterator, collection, etc.)
        general_api_keywords = {"iterator", "next", "hasnext", "collection", "map", "list", 
                              "compare", "equals", "hashcode", "clone", "close"}
                              
        # Process all classes
        for clazz in classes.get_classes():
            # Process each method in the class
            for method in clazz.methods:
                # Skip methods that don't reach monitored methods
                if not method.reaches_mop and not method.directly_reaches_mop:
                    continue
                    
                # Categorize the method by specification type
                spec_type = "unknown"
                signature_lower = method.signature.lower()
                
                # Check for crypto specifications
                if any(kw in signature_lower for kw in crypto_keywords):
                    spec_type = "crypto"
                # Check for general API specifications
                elif any(kw in signature_lower for kw in general_api_keywords):
                    spec_type = "general_api"
                
                # Store monitored method with categorization
                self.monitored_methods[method.signature] = {
                    "class_name": method.class_name,
                    "name": method.name,
                    "signature": method.signature,
                    "directly_reaches_mop": method.directly_reaches_mop,
                    "specification_type": spec_type
                }
                
                # Add to specification types set
                self.specification_types.add(spec_type)
                
        # Build component-method map if we have windows data
        if self.static_data.windows:
            self._build_component_method_map()
    
    def _build_component_method_map(self) -> None:
        """
        Build a map of UI components to reachable methods.
        
        Creates indexes for efficient lookup of which UI components can reach
        which methods, enabling runtime targeting of monitored methods.
        """
        if not self.static_data or not self.static_data.windows:
            return
            
        windows = self.static_data.windows
        
        # Process all windows
        for window in windows.get_windows():
            # Store activity-window mapping for quick lookup
            if window.activity:
                self.activity_window_map[window.activity] = window
                
            # Process all widgets/components in the window
            for widget in window.get_widgets():
                widget_id = widget.resource_id or f"{window.id}_{widget.id}"
                
                # Initialize component entry if not exists
                if widget_id not in self.component_method_map:
                    self.component_method_map[widget_id] = set()
                    
                # Associate widget with any handlers or callbacks that might reach monitored methods
                for handler in widget.handlers:
                    # Check if this handler reaches monitored methods
                    for method_sig in self.monitored_methods:
                        if handler in method_sig or method_sig in handler:
                            # Associate this component with the monitored method
                            self.component_method_map[widget_id].add(method_sig)
                            
                            # Update reverse index
                            if method_sig not in self.method_component_index:
                                self.method_component_index[method_sig] = set()
                            self.method_component_index[method_sig].add(widget_id)
    
    def _process_window_transition_graph(self) -> None:
        """
        Process window transition graph from static analysis.
        
        Analyzes the window transition graph to identify navigation paths,
        particularly those that lead to windows with monitored methods.
        """
        if not self.static_data or not self.static_data.wtg:
            return
            
        wtg = self.static_data.wtg
        
        # Identify windows with monitored methods
        windows_with_monitored_methods = set()
        
        for window in self.static_data.windows.get_windows():
            for widget in window.get_widgets():
                widget_id = widget.resource_id or f"{window.id}_{widget.id}"
                if widget_id in self.component_method_map and self.component_method_map[widget_id]:
                    windows_with_monitored_methods.add(window.id)
                    break
                    
        # Mark all transitions that lead to these windows
        for transition in wtg.get_transitions():
            # Each transition is a dictionary with source and target keys
            if transition.get("target") in windows_with_monitored_methods:
                # This transition leads to a window with monitored methods
                # We'll use this information in navigation path planning
                pass  # Actual processing happens in _build_navigation_paths
    
    def _build_navigation_paths(self) -> None:
        """
        Build navigation paths between windows.
        
        Constructs optimized paths for navigating between different windows,
        with special focus on reaching windows containing monitored methods.
        """
        if not self.static_data or not self.static_data.wtg:
            return
            
        wtg = self.static_data.wtg
        
        # For each window, compute paths to other windows
        for source_window in self.static_data.windows.get_windows():
            source_id = source_window.id
            
            # Skip if this window doesn't exist in WTG
            if not wtg.has_window(source_id):
                continue
                
            # Get all reachable windows and the shortest path to each
            paths = wtg.get_paths_from_window(source_id)
            
            # Store navigation paths
            self.navigation_paths[source_id] = []
            
            for target_id, path in paths.items():
                # Skip self-transitions
                if target_id == source_id:
                    continue
                    
                target_window = self.static_data.windows.get_window(target_id)
                if not target_window:
                    continue
                    
                # Determine if target window has monitored methods
                has_monitored_methods = False
                specification_types = set()
                
                for widget in target_window.get_widgets():
                    widget_id = widget.resource_id or f"{target_id}_{widget.id}"
                    if widget_id in self.component_method_map and self.component_method_map[widget_id]:
                        has_monitored_methods = True
                        
                        # Identify specification types in this window
                        for method_sig in self.component_method_map[widget_id]:
                            if method_sig in self.monitored_methods:
                                spec_type = self.monitored_methods[method_sig].get("specification_type", "unknown")
                                specification_types.add(spec_type)
                        
                        break
                
                # Store path information
                path_info = {
                    "target_id": target_id,
                    "target_activity": target_window.activity,
                    "path_length": len(path),
                    "has_monitored_methods": has_monitored_methods,
                    "specification_types": list(specification_types),
                    "path": path  # List of transition IDs
                }
                
                self.navigation_paths[source_id].append(path_info)
            
            # Sort paths - prioritize those with monitored methods and shorter length
            self.navigation_paths[source_id].sort(
                key=lambda p: (not p["has_monitored_methods"], p["path_length"])
            )
    
    def _log_initialization_summary(self) -> None:
        """
        Log a summary of the initialization process.
        
        Provides an overview of the processed static data, including counts
        of monitored methods, specification types, and navigation paths.
        """
        # Calculate summary statistics
        monitored_method_count = len(self.monitored_methods)
        directly_monitored_count = sum(1 for info in self.monitored_methods.values() 
                                    if info.get("directly_reaches_mop", False))
        
        crypto_count = sum(1 for info in self.monitored_methods.values() 
                         if info.get("specification_type") == "crypto")
                         
        general_api_count = sum(1 for info in self.monitored_methods.values() 
                              if info.get("specification_type") == "general_api")
        
        # Log summary
        self.logger.info(f"Enhanced static analyzer initialized with {monitored_method_count} monitored methods")
        self.logger.info(f"Monitored methods breakdown: {directly_monitored_count} direct, " +
                       f"{crypto_count} crypto, {general_api_count} general API")
        
        window_count = len(self.static_data.windows.get_windows()) if self.static_data and self.static_data.windows else 0
        self.logger.info(f"Processed {window_count} windows with navigation paths")
        
        # Log specification types
        self.logger.info(f"Detected specification types: {sorted(self.specification_types)}")
    
    def get_monitored_methods(self, specification_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get monitored methods, optionally filtered by specification type.
        
        Args:
            specification_type: Optional specification type filter
            
        Returns:
            List of monitored methods with metadata
        """
        if specification_type:
            return [info for info in self.monitored_methods.values() 
                   if info.get("specification_type") == specification_type]
        else:
            return list(self.monitored_methods.values())
    
    def get_components_reaching_monitored_methods(self, window_id: str) -> List[Dict[str, Any]]:
        """
        Get components in a window that can reach monitored methods.
        
        Args:
            window_id: Window ID to check
            
        Returns:
            List of components with the monitored methods they can reach
        """
        result = []
        
        # Skip if window doesn't exist
        if not self.static_data or not self.static_data.windows:
            return result
            
        window = self.static_data.windows.get_window(window_id)
        if not window:
            return result
            
        # Check each widget in the window
        for widget in window.get_widgets():
            widget_id = widget.resource_id or f"{window_id}_{widget.id}"
            
            if widget_id in self.component_method_map and self.component_method_map[widget_id]:
                # This component can reach monitored methods
                monitored_methods = []
                
                for method_sig in self.component_method_map[widget_id]:
                    if method_sig in self.monitored_methods:
                        monitored_methods.append(self.monitored_methods[method_sig])
                
                if monitored_methods:
                    result.append({
                        "component_id": widget_id,
                        "resource_id": widget.resource_id,
                        "class": widget.class_name,
                        "monitored_methods": monitored_methods
                    })
        
        return result
    
    def get_navigation_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """
        Get navigation path between two windows.
        
        Args:
            source_id: Source window ID
            target_id: Target window ID
            
        Returns:
            List of transition IDs representing the path, or None if no path exists
        """
        if source_id not in self.navigation_paths:
            return None
            
        # Look for path to target window
        for path_info in self.navigation_paths[source_id]:
            if path_info["target_id"] == target_id:
                return path_info["path"]
                
        return None
    
    def get_windows_with_monitored_methods(self, specification_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get windows that contain components reaching monitored methods.
        
        Args:
            specification_type: Optional specification type filter
            
        Returns:
            List of windows with monitored methods information
        """
        result = []
        
        if not self.static_data or not self.static_data.windows:
            return result
            
        # Process all windows
        for window in self.static_data.windows.get_windows():
            window_id = window.id
            
            # Check if any component in this window reaches monitored methods
            components = self.get_components_reaching_monitored_methods(window_id)
            
            if components:
                # If specification type filter is provided, filter components
                if specification_type:
                    filtered_components = []
                    for component in components:
                        filtered_methods = [m for m in component["monitored_methods"] 
                                          if m.get("specification_type") == specification_type]
                        if filtered_methods:
                            component_copy = component.copy()
                            component_copy["monitored_methods"] = filtered_methods
                            filtered_components.append(component_copy)
                    
                    components = filtered_components
                
                # Skip if no components after filtering
                if not components:
                    continue
                
                # Add window to result
                result.append({
                    "window_id": window_id,
                    "activity": window.activity,
                    "components": components
                })
        
        return result
    
    def get_path_to_nearest_monitored_method(self, current_window_id: str, 
                                            specification_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find the shortest path to a window with monitored methods.
        
        Args:
            current_window_id: Current window ID
            specification_type: Optional specification type filter
            
        Returns:
            Path information or None if no path exists
        """
        if current_window_id not in self.navigation_paths:
            return None
            
        # Find paths to windows with monitored methods
        for path_info in self.navigation_paths[current_window_id]:
            if not path_info["has_monitored_methods"]:
                continue
                
            # Check specification type if provided
            if specification_type:
                if specification_type not in path_info["specification_types"]:
                    continue
            
            # This is a valid path to a window with monitored methods
            return path_info
            
        return None
    
    def match_resource_to_monitored_methods(self, resource_id: str) -> List[Dict[str, Any]]:
        """
        Match a resource ID to potentially related monitored methods.
        
        Args:
            resource_id: UI element resource ID
            
        Returns:
            List of potentially related monitored methods
        """
        result = []
        
        # Direct match if resource is in component-method map
        if resource_id in self.component_method_map:
            for method_sig in self.component_method_map[resource_id]:
                if method_sig in self.monitored_methods:
                    result.append(self.monitored_methods[method_sig])
            return result
            
        # Fuzzy matching based on resource ID parts
        if not resource_id:
            return result
            
        # Extract resource name (after slash if present)
        resource_name = resource_id.split("/")[-1].lower()
        
        # Check for keyword matches in resource name
        keywords = ["password", "login", "auth", "encrypt", "key", "iterator", "next", 
                   "hasnext", "cipher", "mac", "hash", "digest", "token", "verify"]
                   
        matching_keywords = [kw for kw in keywords if kw in resource_name]
        
        if not matching_keywords:
            return result
            
        # Find monitored methods matching these keywords
        for method_info in self.monitored_methods.values():
            method_sig = method_info["signature"].lower()
            
            if any(kw in method_sig for kw in matching_keywords):
                result.append(method_info)
                
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the static analysis data.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "monitored_method_count": len(self.monitored_methods),
            "directly_monitored_count": sum(1 for info in self.monitored_methods.values() 
                                         if info.get("directly_reaches_mop", False)),
            "crypto_specification_count": sum(1 for info in self.monitored_methods.values() 
                                           if info.get("specification_type") == "crypto"),
            "general_api_specification_count": sum(1 for info in self.monitored_methods.values() 
                                                if info.get("specification_type") == "general_api"),
            "windows_with_monitored_methods": len(self.get_windows_with_monitored_methods()),
            "specification_types": sorted(self.specification_types)
        }