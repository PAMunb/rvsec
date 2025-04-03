# rvandroid/parser/screen/uiautomator/uiautomator_parser.py

import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, Type

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.visitor.base_visitor import BaseScreenVisitor, Node, ScreenDescription
from rvandroid.util.decorators import task_phase
from rvandroid.util.logging.constants import CONTEXT_COMPONENT


class UIAutomator2Parser(AbstractScreenParser):
    """
    Parser for UIAutomator2 XML hierarchy data.

    ### Architectural Decisions:
    - Implements a standardized parsing approach for UIAutomator2 XML
    - Uses a visitor pattern to separate parsing logic from UI hierarchy traversal
    - Provides consistent element attribute normalization
    - Handles system navigation filtering through parsing configuration
    - Maintains compatibility with RV-Android's parser architecture
    """

    def __init__(self, visitor_class: Optional[Type[BaseScreenVisitor]] = None):
        """
        Initialize the UIAutomator2 parser.

        Args:
            visitor_class: Optional visitor class to use for parsing
        """
        super().__init__(visitor_class)
        self.parser_name = "uiautomator"
        
        # Configure logging with context adapter
        self.logger = self.logging_manager.get_logger(
            f"parser.screen.{self.parser_name}",
            {CONTEXT_COMPONENT: "UIAutomator2Parser"}
        )

    @task_phase("parse_xml_hierarchy", measure_performance=True)
    def parse(self, xml_data: str, static_data: Optional[StaticAnalysisData] = None,
              activity: str = "", state_data: Optional[Dict[str, Any]] = None) -> ScreenDescription:
        """
        Special parse method for XML data that maintains backward compatibility.
        
        This method handles both string XML data and dictionary state data.

        Args:
            xml_data: XML hierarchy data or state data dict
            static_data: Optional static analysis data
            activity: Current activity name (optional)
            state_data: Optional state data including system navigation information

        Returns:
            ScreenDescription object with parsed screen elements

        Raises:
            ValueError: If XML data cannot be parsed
        """
        # Determine data type and handle accordingly
        if isinstance(xml_data, str):
            # XML string data
            if not activity:
                activity = self._extract_activity_from_xml(xml_data)
                
            # Create simple state data for processing
            state_data_dict = {
                "hierarchy": xml_data,
                "activity": activity
            }
            
            if state_data and isinstance(state_data, dict):
                # Merge any additional state data
                state_data_dict.update(state_data)
                
            return self.parse_screen(state_data_dict, static_data)
        elif isinstance(xml_data, dict):
            # Already dictionary state data
            return self.parse_screen(xml_data, static_data)
        else:
            raise ValueError(f"Unsupported data type: {type(xml_data)}")

    def _parse_implementation(self, state_data: Dict[str, Any],
                             static_data: Optional[StaticAnalysisData],
                             activity: str) -> ScreenDescription:
        """
        Implementation-specific parsing logic for UIAutomator2 data.
        
        Args:
            state_data: Dictionary containing UI state information
            static_data: Static analysis data for the application
            activity: Current activity name
            
        Returns:
            ScreenDescription object containing parsed UI elements
        """
        # Create visitor
        visitor = self.create_visitor(static_data, activity)

        # Pass system navigation information to visitor if available
        if "system_navigation_bounds" in state_data:
            visitor.system_navigation_bounds = state_data["system_navigation_bounds"]

        # Pass device information to visitor if available
        if "device_info" in state_data:
            visitor.device_info = state_data["device_info"]

        # Parse XML and build node tree
        root_node = self.create_node_tree(state_data)
        if not root_node:
            self.logger.error("Failed to parse XML data")
            raise ValueError("Failed to parse XML data")

        # Visit nodes to build screen description
        root_node.accept(visitor)

        # Get screen description from visitor
        screen_desc = visitor.get_screen_description()
        self.log_processing_summary("interactive elements", len(screen_desc.items))

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
            # First check if activity is explicitly provided
            if "activity" in state_data and state_data["activity"]:
                return state_data["activity"]
                
            # If state_data has hierarchy, extract from XML
            if "hierarchy" in state_data and isinstance(state_data["hierarchy"], str):
                return self._extract_activity_from_xml(state_data["hierarchy"])
                
            # If all else fails
            raise ValueError("Could not determine activity from state data")
        except Exception as e:
            self.logger.error(f"Error determining activity name: {e}")
            raise
            
    def _extract_activity_from_xml(self, xml_data: str) -> str:
        """
        Extract activity/package name from XML string.
        
        Args:
            xml_data: XML hierarchy string
            
        Returns:
            Activity or package name
            
        Raises:
            ValueError: If activity cannot be determined
        """
        try:
            root = ET.fromstring(xml_data)
            # Try to find package attribute
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
            # If state_data has hierarchy, parse the XML
            if "hierarchy" in state_data and isinstance(state_data["hierarchy"], str):
                return self._parse_xml(state_data["hierarchy"])
                
            raise ValueError("Could not create node tree from state data (missing hierarchy)")
        except Exception as e:
            self.logger.error(f"Error creating node tree: {e}")
            raise

    def validate_state_data(self, state_data: Dict[str, Any]) -> bool:
        """
        Validate that state data contains required fields.

        Args:
            state_data: Dictionary containing UI state information

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check for hierarchy
            if "hierarchy" in state_data:
                xml_data = state_data["hierarchy"]
                if isinstance(xml_data, str):
                    try:
                        ET.fromstring(xml_data)
                        return True
                    except Exception:
                        self.logger.error("Invalid XML data")
                        return False
                        
            return False
        except Exception as e:
            self.logger.error(f"Error validating state data: {e}")
            return False

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