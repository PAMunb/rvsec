# rvandroid/parser/screen/uiautomator/uiautomator_parser.py

import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, Type

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.visitor.base_visitor import BaseScreenVisitor, Node, ScreenDescription
from rvandroid.util.decorators import task_phase
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class UIAutomator2Parser(AbstractScreenParser):
    """
    Parser for UIAutomator2 XML hierarchy data.

    ### Architectural Decisions:
    - Implements a standardized parsing approach for UIAutomator2 XML
    - Uses a visitor pattern to separate parsing logic from UI hierarchy traversal
    - Provides consistent element attribute normalization
    - Handles system navigation filtering through parsing configuration
    - Maintains compatibility with RV-Android's parser architecture

    ### Role in the System:
    - Translates raw XML hierarchy into structured ScreenDescription objects
    - Enables analysis and action generation on parsed UI elements
    - Provides a clean separation between UI retrieval and UI processing
    - Filters system elements to focus testing on application UI
    """

    def __init__(self, visitor_class: Optional[Type[BaseScreenVisitor]] = None):
        """
        Initialize the UIAutomator2 parser.

        Args:
            visitor_class: Optional visitor class to use for parsing
        """
        super().__init__(visitor_class)

        # Configure logging with context adapter
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "parser.screen.uiautomator.parser",
            {CONTEXT_COMPONENT: "UIAutomator2Parser"}
        )

    @task_phase("parse_xml_hierarchy", measure_performance=True)
    def parse(self, xml_data: str, static_data: Optional[StaticAnalysisData] = None,
              activity: str = "", state_data: Optional[Dict[str, Any]] = None) -> ScreenDescription:
        """
        Parse UIAutomator2 XML data into a screen description.

        Args:
            xml_data: XML hierarchy data
            static_data: Optional static analysis data
            activity: Current activity name
            state_data: Optional state data including system navigation information

        Returns:
            ScreenDescription object with parsed screen elements

        Raises:
            ValueError: If XML data cannot be parsed
        """
        # Create parsing context
        parse_context = {
            "activity": activity,
            "data_size": len(xml_data) if xml_data else 0
        }

        # Use with_context from the ContextAdapter
        with self.logger.with_context(**parse_context):
            self.logger.debug("Starting XML parsing")

            # Create visitor
            visitor = self.create_visitor(static_data, activity)

            # Pass system navigation information to visitor if available
            if state_data and "system_navigation_bounds" in state_data:
                visitor.system_navigation_bounds = state_data["system_navigation_bounds"]

            # Pass device information to visitor if available
            if state_data and "device_info" in state_data:
                visitor.device_info = state_data["device_info"]

            # Parse XML and build node tree
            root_node = self._parse_xml(xml_data)
            if not root_node:
                self.logger.error("Failed to parse XML data")
                raise ValueError("Failed to parse XML data")

            # Visit nodes to build screen description
            root_node.accept(visitor)

            # Get screen description from visitor
            screen_desc = visitor.get_screen_description()
            self.logger.debug(f"Completed XML parsing, found {len(screen_desc.items)} interactive elements")

            return screen_desc

    def get_activity_name(self, state_data: Dict[str, Any]) -> str:
        """
        Extract the current activity name from the state data.

        Args:
            state_data: Dictionary containing UI state information

        Returns:
            Name of the current activity

        Raises:
            ValueError: If activity name cannot be determined
        """
        try:
            # If state_data is a string (XML data), try to parse it
            if isinstance(state_data, str):
                try:
                    root = ET.fromstring(state_data)
                    # Try to find package and activity information
                    package = root.get("package", "")
                    if package:
                        return package
                    # If no package attribute, try first node with package
                    for child in root.iter():
                        package = child.get("package", "")
                        if package:
                            return package
                    raise ValueError("Could not determine activity from XML data")
                except Exception as e:
                    raise ValueError(f"Error parsing XML for activity: {e}")

            # If state_data is a dictionary, look for activity information
            if isinstance(state_data, dict):
                # Check for explicitly provided activity
                if "activity" in state_data:
                    return state_data["activity"]

                # Check for hierarchy XML
                if "hierarchy" in state_data:
                    return self.get_activity_name(state_data["hierarchy"])

            raise ValueError("Could not determine activity from state data")
        except Exception as e:
            self.logger.error(f"Error determining activity name: {e}")
            raise

    def create_node_tree(self, state_data: Dict[str, Any]) -> Optional[Node]:
        """
        Create a Node tree from the state data.

        Args:
            state_data: Dictionary containing UI state information

        Returns:
            Root Node of the UI hierarchy or None if invalid data

        Raises:
            ValueError: If node tree cannot be created from the state data
        """
        try:
            # If state_data is a string (XML data), parse it directly
            if isinstance(state_data, str):
                return self._parse_xml(state_data)

            # If state_data is a dictionary, look for hierarchy XML
            if isinstance(state_data, dict) and "hierarchy" in state_data:
                return self._parse_xml(state_data["hierarchy"])

            raise ValueError("Could not create node tree from state data")
        except Exception as e:
            self.logger.error(f"Error creating node tree: {e}")
            raise

    def _parse_xml(self, xml_data: str) -> Optional[Node]:
        """
        Parse UIAutomator XML data and build a node tree.

        Args:
            xml_data: XML hierarchy data from UIAutomator

        Returns:
            Root Node of the UI hierarchy or None if parsing fails
        """
        try:
            with self.logger.with_context(operation="parse_xml"):
                self.logger.debug(f"Parsing XML data ({len(xml_data)} bytes)")

                # Parse XML string
                root = ET.fromstring(xml_data)

                # Create node tree
                return self._build_node_from_element(root)
        except Exception as e:
            self.logger.error(f"Error parsing XML data: {e}")
            return None

    def validate_state_data(self, state_data: Dict[str, Any]) -> bool:
        """
        Validate that state data contains required fields.

        Args:
            state_data: Dictionary containing UI state information

        Returns:
            True if valid, False otherwise
        """
        try:
            # For XML string data, check if it's parseable
            if isinstance(state_data, str):
                try:
                    ET.fromstring(state_data)
                    return True
                except Exception:
                    return False

            # For dictionary data, check for hierarchy
            if isinstance(state_data, dict):
                if "hierarchy" in state_data:
                    return self.validate_state_data(state_data["hierarchy"])

            return False
        except Exception as e:
            self.logger.error(f"Error validating state data: {e}")
            return False

    def _build_node_from_element(self, element: ET.Element, parent_node: Optional[Node] = None) -> Node:
        """
        Recursively build a Node from an XML element.

        Args:
            element: XML element to convert
            parent_node: Parent Node for the current element

        Returns:
            Node object representing the XML element and its children
        """
        # Extract attributes from element and normalize them
        attributes = {key.lower(): value for key, value in element.attrib.items()}

        # Convert common attributes to expected format
        view_data = {
            "class": attributes.get("class", ""),
            "package": attributes.get("package", ""),
            "resource_id": attributes.get("resource-id", ""),
            "text": attributes.get("text", ""),
            "content_description": attributes.get("content-desc", ""),
            "clickable": attributes.get("clickable", "false").lower() == "true",
            "checkable": attributes.get("checkable", "false").lower() == "true",
            "checked": attributes.get("checked", "false").lower() == "true",
            "scrollable": attributes.get("scrollable", "false").lower() == "true",
            "long_clickable": attributes.get("long-clickable", "false").lower() == "true",
            "editable": attributes.get("editable", "false").lower() == "true",
            "enabled": attributes.get("enabled", "true").lower() == "true",
            "focused": attributes.get("focused", "false").lower() == "true",
            "selected": attributes.get("selected", "false").lower() == "true",
            "password": attributes.get("password", "false").lower() == "true",
        }

        # Parse bounds string into coordinates
        # Format is usually "[left,top][right,bottom]"
        bounds_str = attributes.get("bounds", "")
        if bounds_str:
            try:
                # Extract numbers from string
                import re
                numbers = re.findall(r'\d+', bounds_str)
                if len(numbers) >= 4:
                    # Create bounds as [[left, top], [right, bottom]]
                    view_data["bounds"] = [
                        [int(numbers[0]), int(numbers[1])],
                        [int(numbers[2]), int(numbers[3])]
                    ]
            except Exception as e:
                self.logger.warning(f"Error parsing bounds '{bounds_str}': {e}")

        # Create the node
        node = Node(view_data, [], parent_node)

        # Process child elements
        for child_element in element:
            child_node = self._build_node_from_element(child_element, node)
            node.children.append(child_node)

        return node
