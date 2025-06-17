"""
DroidBot screen state parser for Android UI monitoring operations.

Specialized parser implementation for processing DroidBot-generated state data
into standardized ScreenDescription objects for monitored operations analysis.
"""

from typing import Dict, Any, Optional, Type

from rv_android_core.domain.static import StaticAnalysisData
from rv_screen_parser.parser.screen.base_parser import BaseScreenParser
from rv_screen_parser.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, Node


class DroidBotParser(BaseScreenParser[ScreenDescription]):
    """
    Specialized parser for DroidBot-generated Android UI state data.

    ### Architectural Decisions:
    - Implements direct inheritance from BaseScreenParser for full modern architecture benefits
    - Provides specialized handling for DroidBot's unique state data format and structure
    - Uses comprehensive error handling through ErrorHandler integration for robust parsing operations
    - Implements visitor pattern delegation for flexible UI element processing strategies
    - Supports integration with static analysis data for enhanced context-aware parsing

    ### Role in the System:
    - Serves as the primary interface for processing DroidBot state captures in monitored operations
    - Transforms DroidBot's JSON-based state format into standardized ScreenDescription objects
    - Enables seamless integration with the broader screen parsing framework architecture
    - Provides specialized handling for DroidBot-specific data structures and hierarchy patterns
    - Facilitates consistent UI state analysis across different monitoring tool outputs

    ### Design Note - DroidBot Specifics:
    DroidBot generates state data with specific hierarchy structures and activity information.
    This parser handles DroidBot's unique 'view_tree', 'stack', and activity naming conventions
    while normalizing the data into the framework's standard representation.
    """

    def __init__(self, visitor_class: Optional[Type[AbstractScreenVisitor]] = None):
        """
        Initialize the DroidBot parser with specialized configuration.

        Args:
            visitor_class: Optional visitor class for custom UI element processing strategies
        """
        super().__init__("droidbot", visitor_class)

    def _parse_implementation(self, state_data: Dict[str, Any],
                              static_data: Optional[StaticAnalysisData],
                              activity: str) -> ScreenDescription:
        """
        Implementation-specific parsing logic for DroidBot data.
        
        Args:
            state_data: Dictionary containing UI state information
            static_data: Static analysis data for the application
            activity: Current activity name
            
        Returns:
            ScreenDescription object containing parsed UI elements
        """
        # Update stack info if available
        if "stack" in state_data:
            stack = state_data.get("stack", [])
            new_stack = [name.replace("/", "") for name in stack]
            state_data["stack"] = new_stack

        # Create UI hierarchy tree
        tree = self.create_node_tree(state_data)
        if not tree:
            self.logger.error("Failed to create UI tree from view_tree data")
            return ScreenDescription(activity, [])

        # Create visitor and traverse tree
        visitor = self.create_visitor(static_data, activity)
        tree.accept(visitor)

        # Get and return screen description
        description = visitor.get_screen_description()
        self.log_processing_summary("UI elements", len(description.items))

        return description

    def get_activity_name(self, state_data: Dict[str, Any]) -> str:
        """
        Extract activity name from DroidBot state data with fallback options.

        Args:
            state_data: Dictionary containing DroidBot state

        Returns:
            Activity name or fallback identifier

        Raises:
            ValueError: If activity name cannot be determined after fallbacks
        """
        # Try standard activity field
        activity = state_data.get("activity", "")

        # If not found, try alternative sources
        if not activity:
            # Try foreground_activity if available
            activity = state_data.get("foreground_activity", "")

        if not activity:
            # Try to extract from the top of the stack if available
            stack = state_data.get("stack", [])
            if stack and len(stack) > 0:
                activity = stack[0]

        if not activity:
            # Try to extract from currently focused window if available
            windows = state_data.get("windows", [])
            if windows and len(windows) > 0:
                for window in windows:
                    if window.get("focused", False):
                        activity = window.get("activity", "")
                        break

        if not activity:
            self.logger.warning("Could not determine activity name from state data")
            # Provide a fallback value instead of raising an exception
            package_name = state_data.get("package_name", "unknown.package")
            activity = f"{package_name}.UnknownActivity"

        # Clean up activity name
        activity = activity.replace("/", "")

        return activity

    def validate_state_data(self, state_data: Dict[str, Any]) -> bool:
        """
        Validate DroidBot state data.

        Args:
            state_data: Dictionary containing DroidBot state

        Returns:
            True if valid, False otherwise
        """
        return "view_tree" in state_data

    def create_node_tree(self, state_data: Dict[str, Any]) -> Optional[Node]:
        """
        Create a Node tree from the DroidBot state data.

        Args:
            state_data: Dictionary containing DroidBot state data

        Returns:
            Root Node of the UI hierarchy or None if invalid data
        """
        self.logger.debug("Creating UI tree from DroidBot JSON data")

        if "view_tree" not in state_data:
            self.logger.error("No view_tree found in DroidBot state")
            return None

        view_tree = state_data["view_tree"]
        if not isinstance(view_tree, dict):
            self.logger.warning(f"Invalid JSON data format: {type(view_tree)}")
            return None

        def create_node(data: Dict[str, Any], parent: Optional[Node] = None) -> Optional[Node]:
            """
            Recursive function to create nodes from JSON data.

            Args:
                data: Node data dictionary
                parent: Parent node (optional)

            Returns:
                Node instance or None if invalid data
            """
            if not isinstance(data, dict):
                self.logger.warning(f"Invalid node data format: {data}")
                return None

            children = []
            if "children" in data and isinstance(data["children"], list):
                for child_data in data["children"]:
                    child_node = create_node(child_data, parent)
                    if child_node:
                        children.append(child_node)

            node = Node(data=data, children=children)

            # Set parent reference
            for child in node.children:
                child.parent = node

            return node

        return create_node(view_tree)
