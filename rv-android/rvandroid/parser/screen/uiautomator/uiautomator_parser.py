# rvandroid/parser/screen/uiautomator/uiautomator_parser.py
import logging
import xml.etree.ElementTree as ET
from typing import Optional, Type

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, Node, BaseScreenVisitor


class UIAutomator2Parser(AbstractScreenParser):
    """
    Parser for UIAutomator2 XML dump.
    Converts UIAutomator2 XML data into a ScreenDescription.
    """

    def __init__(self, visitor_class: Optional[Type[BaseScreenVisitor]] = None):
        """
        Initialize the UIAutomator2 parser.

        Args:
            visitor_class: Optional visitor class to use for parsing
        """
        super().__init__(visitor_class)
        self.logger = logging.getLogger(__name__)

    def parse(self, xml_data: str, static_data: Optional[StaticAnalysisData] = None) -> ScreenDescription:
        """
        Parse UIAutomator2 XML dump into a ScreenDescription.

        Args:
            xml_data: XML string containing UIAutomator2 hierarchy
            static_data: Optional static analysis data for the application (optional)

        Returns:
            ScreenDescription object

        Raises:
            ValueError: If XML data is invalid or cannot be parsed
        """
        # Avoid logging the entire XML which could be very large
        self.logger.debug(f"Parsing UIAutomator2 XML data: {len(xml_data)} bytes")

        # Verify if it's valid XML
        if not xml_data or not isinstance(xml_data, str):
            raise ValueError("Invalid XML data: must be a non-empty string")

        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse XML: {e}")
            raise ValueError(f"Invalid XML format: {e}")

        # Extract activity name and create node tree
        activity_name = self.get_activity_name(root)
        root_node = self.create_node_tree(root)

        if not root_node:
            self.logger.error("Failed to create UI tree from UIAutomator2 XML")
            return ScreenDescription(activity_name, [])

        # Create visitor and traverse tree
        visitor = self.create_visitor(static_data, activity_name)
        root_node.accept(visitor)

        # Get screen description
        description = visitor.get_screen_description()
        self.logger.info(f"Parsed {len(description.items)} UI elements from UIAutomator2 XML")

        return description

    def get_activity_name(self, root: ET.Element) -> str:
        """
        Extract activity name from XML root.

        Args:
            root: Root XML element

        Returns:
            Activity name
        """
        # Try to extract activity from XML attributes or package
        activity = root.get("activity", "")
        package = root.get("package", "unknown")

        if not activity:
            # Fallback to package if no activity found
            activity = f"{package}.UnknownActivity"

        # Clean up activity name
        if "/" in activity:
            activity = activity.split("/")[-1]

        return activity

    def validate_state_data(self, root: ET.Element) -> bool:
        """
        Validate UIAutomator2 XML data.

        Args:
            root: Root XML element

        Returns:
            True if valid, False otherwise
        """
        # Basic validation: check for hierarchy root
        return (root is not None and
                root.tag.lower() in ["hierarchy", "root", "node"])

    def create_node_tree(self, root: ET.Element) -> Optional[Node]:
        """
        Create a Node tree from UIAutomator2 XML hierarchy.

        Args:
            root: Root XML element

        Returns:
            Root Node or None if invalid data
        """

        def create_node(xml_node: ET.Element, parent: Optional[Node] = None) -> Optional[Node]:
            """
            Recursively create Nodes from XML elements.

            Args:
                xml_node: Current XML node
                parent: Parent Node (optional)

            Returns:
                Created Node or None
            """
            if xml_node is None:
                return None

            # Extract node properties from XML attributes
            node_data = {
                # Standard properties mapping
                "class": xml_node.get("class", ""),
                "package": xml_node.get("package", ""),
                "content_description": xml_node.get("content-desc", ""),
                "resource_id": xml_node.get("resource-id", ""),
                "text": xml_node.get("text", ""),

                # Boolean properties
                "checkable": xml_node.get("checkable", "false") == "true",
                "checked": xml_node.get("checked", "false") == "true",
                "clickable": xml_node.get("clickable", "false") == "true",
                "enabled": xml_node.get("enabled", "true") == "true",
                "focusable": xml_node.get("focusable", "false") == "true",
                "focused": xml_node.get("focused", "false") == "true",
                "long_clickable": xml_node.get("long-clickable", "false") == "true",
                "password": xml_node.get("password", "false") == "true",
                "scrollable": xml_node.get("scrollable", "false") == "true",
                "selected": xml_node.get("selected", "false") == "true"
            }

            # Parse bounds
            bounds_str = xml_node.get("bounds", "[0,0][0,0]")
            try:
                # Extract coordinates from bounds string like "[100,200][300,400]"
                bounds = [
                    [int(x) for x in bounds_str[1:bounds_str.index("][")].split(",")],
                    [int(x) for x in bounds_str[bounds_str.index("][") + 2:-1].split(",")]
                ]
                node_data["bounds"] = bounds
            except (ValueError, IndexError):
                node_data["bounds"] = [[0, 0], [0, 0]]

            # Create Node
            node = Node(node_data, [], parent)

            # Recursively process child nodes
            for child_xml in xml_node:
                child_node = create_node(child_xml, node)
                if child_node:
                    node.children.append(child_node)

            return node

        return create_node(root)

    def get_package_name(self, root: ET.Element) -> Optional[str]:
        """
        Extract package name from XML root.

        Args:
            root: Root XML element

        Returns:
            Package name if available, None otherwise
        """
        return root.get("package")
