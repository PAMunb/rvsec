"""
Simple coordinate validator for prototype testing.

Simplified version that parses UIAutomator XML directly without rv-screen-parser dependency.
"""
import xml.etree.ElementTree as ET
from typing import List, Tuple, Dict, Any
from pathlib import Path


class SimpleCoordinateValidator:
    """Simple coordinate validator using direct XML parsing."""
    
    def __init__(self, tolerance: int = 50):
        """
        Initialize simple validator.
        
        Args:
            tolerance: Pixel tolerance for coordinate validation
        """
        self.tolerance = tolerance
    
    def extract_clickable_coordinates(self, xml_path: str) -> List[Tuple[int, int]]:
        """
        Extract clickable coordinates directly from UIAutomator XML.
        
        Args:
            xml_path: Path to UIAutomator XML file
            
        Returns:
            List of (x, y) coordinate tuples for clickable elements
        """
        if not Path(xml_path).exists():
            print(f"XML file not found: {xml_path}")
            return []
        
        coordinates = []
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Find all clickable elements
            for element in root.iter():
                if element.get('clickable') == 'true':
                    bounds = element.get('bounds')
                    if bounds:
                        coords = self._parse_bounds(bounds)
                        if coords:
                            coordinates.append(coords)
            
            print(f"Found {len(coordinates)} clickable elements")
            return coordinates
            
        except Exception as e:
            print(f"Failed to parse XML: {e}")
            return []
    
    def _parse_bounds(self, bounds_str: str) -> Tuple[int, int]:
        """
        Parse UIAutomator bounds string to center coordinates.
        
        Args:
            bounds_str: Bounds string like "[x1,y1][x2,y2]"
            
        Returns:
            Center coordinates (x, y) or None if parsing fails
        """
        try:
            # Remove brackets and split: "[123,456][789,012]" -> "123,456,789,012"
            clean_bounds = bounds_str.replace('[', '').replace(']', ',')
            coords = [int(x) for x in clean_bounds.split(',') if x]
            
            if len(coords) >= 4:
                x1, y1, x2, y2 = coords[:4]
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                return (center_x, center_y)
                
        except (ValueError, IndexError):
            pass
        
        return None
    
    def validate_coordinates(self, generated_coords: Tuple[int, int], xml_path: str) -> Dict[str, Any]:
        """
        Validate generated coordinates against ground truth.
        
        Args:
            generated_coords: Generated (x, y) coordinates
            xml_path: Path to UIAutomator XML file
            
        Returns:
            Validation result dictionary
        """
        ground_truth_coords = self.extract_clickable_coordinates(xml_path)
        
        if not ground_truth_coords:
            return {
                'success': False,
                'distance': float('inf'),
                'closest_element': None,
                'tolerance': self.tolerance,
                'ground_truth_count': 0,
                'error': 'No clickable elements found'
            }
        
        # Find closest element
        min_distance = float('inf')
        closest_element = None
        
        for gt_coords in ground_truth_coords:
            distance = self._euclidean_distance(generated_coords, gt_coords)
            if distance < min_distance:
                min_distance = distance
                closest_element = gt_coords
        
        # Success if within tolerance
        success = min_distance <= self.tolerance
        
        return {
            'success': success,
            'distance': min_distance,
            'closest_element': closest_element,
            'tolerance': self.tolerance,
            'ground_truth_count': len(ground_truth_coords)
        }
    
    def _euclidean_distance(self, coord1: Tuple[int, int], coord2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between two points."""
        x1, y1 = coord1
        x2, y2 = coord2
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


def create_simple_validator(tolerance: int = 50) -> SimpleCoordinateValidator:
    """Factory function for simple validator."""
    return SimpleCoordinateValidator(tolerance)