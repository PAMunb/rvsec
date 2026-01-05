"""
Coordinate validation using rv-screen-parser with UIAutomator XML files.

Implements the coordinate validation approach from vision research findings.
"""
import logging
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT

from rv_agent.config import PrototypeConfig


class CoordinateValidator:
    """
    Validates generated coordinates against ground truth from UIAutomator XML.
    
    Uses rv-screen-parser for consistent UI element extraction and implements
    the 50-pixel tolerance coordinate validation approach from research.
    """
    
    def __init__(self, config: PrototypeConfig):
        """
        Initialize coordinate validator.
        
        Args:
            config: Prototype configuration
        """
        self.config = config
        self.parser = UIAutomator2Parser()
        
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.coordinate_validator",
            {CONTEXT_COMPONENT: "CoordinateValidator"}
        )
        
    def parse_uiautomator_xml(self, xml_path: str) -> Optional[ScreenDescription]:
        """
        Parse UIAutomator XML using rv-screen-parser.
        
        Args:
            xml_path: Path to UIAutomator XML dump file
            
        Returns:
            ScreenDescription or None if parsing failed
        """
        try:
            if not Path(xml_path).exists():
                self.logger.error(f"UIAutomator XML file not found: {xml_path}")
                return None
            
            # Read XML file content
            with open(xml_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # Use rv-screen-parser to parse UIAutomator XML
            screen_description = self.parser.parse(xml_content)
            
            self.logger.debug(f"Parsed {len(screen_description.items)} UI elements from {xml_path}")
            return screen_description
            
        except Exception as e:
            self.logger.error(f"Failed to parse UIAutomator XML: {e}")
            return None
    
    def extract_clickable_coordinates(self, xml_path: str) -> List[Tuple[int, int]]:
        """
        Extract all clickable element coordinates for ground truth validation.
        
        Args:
            xml_path: Path to UIAutomator XML file
            
        Returns:
            List of (x, y) coordinate tuples for all clickable elements
        """
        screen_desc = self.parse_uiautomator_xml(xml_path)
        if not screen_desc:
            return []
            
        coordinates = []
        
        try:
            # Extract coordinates from screen description nodes
            for item in screen_desc.items:
                if hasattr(item, 'clickable') and item.clickable:
                    # Get bounds and calculate center
                    if hasattr(item, 'bounds') and item.bounds:
                        try:
                            # Parse bounds format "[x1,y1][x2,y2]"
                            bounds_str = item.bounds
                            if isinstance(bounds_str, str) and '[' in bounds_str:
                                # Remove brackets and split
                                coords = bounds_str.replace('[', '').replace(']', ',').split(',')
                                if len(coords) >= 4:
                                    x1, y1, x2, y2 = map(int, coords[:4])
                                    center_x = (x1 + x2) // 2
                                    center_y = (y1 + y2) // 2
                                    coordinates.append((center_x, center_y))
                        except (ValueError, AttributeError):
                            continue
            
            self.logger.debug(f"Extracted {len(coordinates)} clickable coordinates from {xml_path}")
            return coordinates
            
        except Exception as e:
            self.logger.error(f"Failed to extract coordinates: {e}")
            return []
    
    def validate_coordinates(self, 
                           generated_coords: Tuple[int, int], 
                           xml_path: str) -> Dict[str, Any]:
        """
        Validate generated coordinates against ground truth using research methodology.
        
        Implements the coordinate validation approach from vision research:
        - Finds closest clickable element to generated coordinates
        - Success if distance <= 50 pixels (research tolerance)
        - Returns comprehensive validation metrics
        
        Args:
            generated_coords: (x, y) coordinates generated by vision model
            xml_path: Path to UIAutomator XML file
            
        Returns:
            Dictionary with validation results:
            {
                'success': bool,
                'distance': float,
                'closest_element': tuple,
                'tolerance': int,
                'ground_truth_count': int,
                'error': str (optional)
            }
        """
        try:
            # Extract ground truth coordinates
            ground_truth_coords = self.extract_clickable_coordinates(xml_path)
            
            if not ground_truth_coords:
                return {
                    'success': False,
                    'distance': float('inf'),
                    'closest_element': None,
                    'tolerance': self.config.COORDINATE_TOLERANCE,
                    'ground_truth_count': 0,
                    'error': 'No clickable elements found in XML'
                }
            
            # Find closest element using Euclidean distance
            min_distance = float('inf')
            closest_element = None
            
            for gt_coords in ground_truth_coords:
                distance = self._calculate_euclidean_distance(generated_coords, gt_coords)
                
                if distance < min_distance:
                    min_distance = distance
                    closest_element = gt_coords
            
            # Determine success based on tolerance (50 pixels from research)
            success = min_distance <= self.config.COORDINATE_TOLERANCE
            
            result = {
                'success': success,
                'distance': min_distance,
                'closest_element': closest_element,
                'tolerance': self.config.COORDINATE_TOLERANCE,
                'ground_truth_count': len(ground_truth_coords),
                'all_ground_truth': ground_truth_coords  # For debugging
            }
            
            self.logger.debug(
                f"Validation: {generated_coords} -> closest: {closest_element}, "
                f"distance: {min_distance:.1f}px, success: {success}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Coordinate validation failed: {e}")
            return {
                'success': False,
                'distance': float('inf'),
                'closest_element': None,
                'tolerance': self.config.COORDINATE_TOLERANCE,
                'ground_truth_count': 0,
                'error': str(e)
            }
    
    def _calculate_euclidean_distance(self, 
                                    coords1: Tuple[int, int], 
                                    coords2: Tuple[int, int]) -> float:
        """
        Calculate Euclidean distance between two coordinate pairs.
        
        Args:
            coords1: First coordinate pair (x1, y1)
            coords2: Second coordinate pair (x2, y2)
            
        Returns:
            Euclidean distance in pixels
        """
        x1, y1 = coords1
        x2, y2 = coords2
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
    
    def get_validation_stats(self, xml_path: str) -> Dict[str, Any]:
        """
        Get statistics about clickable elements in the UI.
        
        Args:
            xml_path: Path to UIAutomator XML file
            
        Returns:
            Dictionary with UI statistics for analysis
        """
        try:
            screen_desc = self.parse_uiautomator_xml(xml_path)
            if not screen_desc:
                return {'error': 'Failed to parse XML'}
            
            clickable_count = 0
            total_elements = len(screen_desc.items)
            element_types = {}
            
            for item in screen_desc.items:
                for action in item.actions:
                    if action.actionable:
                        clickable_count += 1
                        
                        # Count element types
                        element_type = getattr(action, 'widget_type', 'unknown')
                        element_types[element_type] = element_types.get(element_type, 0) + 1
            
            return {
                'total_elements': total_elements,
                'clickable_elements': clickable_count,
                'clickable_percentage': (clickable_count / total_elements * 100) if total_elements > 0 else 0,
                'element_types': element_types,
                'activity': screen_desc.activity,
                'package': screen_desc.package
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get validation stats: {e}")
            return {'error': str(e)}


def create_coordinate_validator(config: PrototypeConfig) -> CoordinateValidator:
    """Factory function to create coordinate validator."""
    return CoordinateValidator(config)