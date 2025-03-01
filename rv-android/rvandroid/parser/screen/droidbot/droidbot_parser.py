import logging
from typing import Dict, Any, Optional, Callable

from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, BaseScreenVisitor, Node


class DroidBotParser(AbstractScreenParser):
    """
    Parser for DroidBot state data.
    Converts DroidBot state data into a ScreenDescription.
    """

    def __init__(self, visitor_factory: Optional[Callable[[StaticAnalysisData, str], BaseScreenVisitor]] = None):
        """
        Initialize the DroidBot parser.

        Args:
            visitor_factory: Optional factory function to create visitor instances
        """
        super().__init__(visitor_factory)
        self.logger = logging.getLogger(__name__)

    def parse(self, state_data: Dict[str, Any], static_data: Optional[StaticAnalysisData] = None) -> ScreenDescription:
        """
        Parse DroidBot state data into a ScreenDescription.

        Args:
            state_data: Dictionary containing DroidBot state
            static_data: Static analysis data for the application (optional)

        Returns:
            ScreenDescription object

        Raises:
            ValueError: If state data is invalid or cannot be parsed
        """
        # Validate state data
        if not self.validate_state_data(state_data):
            raise ValueError("Invalid DroidBot state data: missing required fields")

        self.logger.info(f"Parsing DroidBot state for activity: {self.get_activity_name(state_data)}")

        # Clean up activity name
        activity = self.get_activity_name(state_data)

        # Update stack info if available
        if "stack" in state_data:
            stack = state_data.get("stack", [])
            new_stack = [name.replace("/", "") for name in stack]
            state_data["stack"] = new_stack

        # Create UI hierarchy tree
        if "view_tree" not in state_data:
            self.logger.error("No view_tree found in DroidBot state")
            return ScreenDescription(activity, [])

        tree = self._create_tree_from_json(state_data["view_tree"])
        if not tree:
            self.logger.error("Failed to create UI tree from view_tree data")
            return ScreenDescription(activity, [])

        # Create visitor and traverse tree
        visitor = self._create_visitor(static_data, activity)
        tree.accept(visitor)

        # Get and return screen description
        description = visitor.get_screen_description()
        self.logger.info(f"Parsed {len(description.items)} UI elements from DroidBot state")

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
        required_fields = ["activity", "view_tree"]
        return all(field in state_data for field in required_fields)

    def _create_tree_from_json(self, json_data: Dict[str, Any]) -> Optional[Node]:
        """
        Create a Node tree from JSON representation of an Android UI hierarchy.

        Args:
            json_data: JSON dictionary containing UI hierarchy data

        Returns:
            Root Node of the UI hierarchy tree or None if invalid data
        """
        self.logger.debug("Creating UI tree from DroidBot JSON data")

        if not isinstance(json_data, dict):
            self.logger.warning(f"Invalid JSON data format: {type(json_data)}")
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

            node = Node(data, children)

            # Set parent reference
            for child in node.children:
                child.parent = node

            return node

        return create_node(json_data)
