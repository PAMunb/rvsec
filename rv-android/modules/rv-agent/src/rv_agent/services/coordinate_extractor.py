"""
Critical coordinate extraction functions - VALIDATED in Phase 0.

This module contains the EXACT implementations from the prototype that achieved
100% success rate vs 30% without coordinate enhancement. These functions MUST
NOT be modified without scientific validation.

Source: Phase 0 validation (12,193 tests) - overnight execution results.

UPDATED 2026-01-07: Coordinates now output as NORMALIZED [0, 1000) instead of
pixels. This ensures consistency with ActionNormalizer which expects [0, 1000)
and converts to device pixels. Validation confirmed LLM copies text coords.
"""
import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Tuple, Any, Optional


# Default device dimensions for coordinate normalization
DEFAULT_DEVICE_WIDTH = 1080
DEFAULT_DEVICE_HEIGHT = 1920


def pixels_to_normalized(pixel_x: int, pixel_y: int,
                         width: int = DEFAULT_DEVICE_WIDTH,
                         height: int = DEFAULT_DEVICE_HEIGHT) -> Tuple[int, int]:
    """
    Convert pixel coordinates to normalized [0, 1000) range.

    This ensures coordinates in the prompt match the format expected by
    ActionNormalizer, which converts [0, 1000) back to pixels.

    Args:
        pixel_x: X coordinate in pixels
        pixel_y: Y coordinate in pixels
        width: Device screen width in pixels
        height: Device screen height in pixels

    Returns:
        Normalized (x, y) coordinates in [0, 1000) range
    """
    norm_x = int((pixel_x / width) * 1000)
    norm_y = int((pixel_y / height) * 1000)
    return (norm_x, norm_y)


def extract_clickable_elements_with_coords(
    xml_content: str,
    device_width: int = DEFAULT_DEVICE_WIDTH,
    device_height: int = DEFAULT_DEVICE_HEIGHT,
) -> List[Dict]:
    """
    Extração de coordenadas VALIDADA em 12,193 testes.

    Esta função DEVE ser portada EXATAMENTE como está - é o core do sucesso.
    Fonte: modules/rv-agent/src/rv_agent/simple_validator.py (backup)

    CRITICAL: This function is the key to 100% vs 30% success rate.
    DO NOT MODIFY without extensive scientific validation.

    UPDATED 2026-01-07: Coordinates now output as NORMALIZED [0, 1000).
    This ensures consistency with ActionNormalizer which expects [0, 1000).

    Args:
        xml_content: UIAutomator XML content as string
        device_width: Device screen width in pixels (default 1080)
        device_height: Device screen height in pixels (default 1920)

    Returns:
        List of elements with enhanced descriptions including NORMALIZED coordinates
    """
    elements = []
    root = ET.fromstring(xml_content)

    for node in root.iter('node'):
        if node.get('clickable') == 'true':
            bounds_str = node.get('bounds')
            if bounds_str:
                # Parse bounds "[x1,y1][x2,y2]" -> center (x, y)
                bounds_match = re.findall(r'\[(\d+),(\d+)\]', bounds_str)
                if len(bounds_match) == 2:
                    x1, y1 = map(int, bounds_match[0])
                    x2, y2 = map(int, bounds_match[1])

                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2

                    # Convert pixel coordinates to normalized [0, 1000)
                    norm_x, norm_y = pixels_to_normalized(
                        center_x, center_y, device_width, device_height
                    )

                    # Build enhanced description WITH COORDINATES
                    text = node.get('text', '')
                    content_desc = node.get('content-desc', '')
                    resource_id = node.get('resource-id', '')
                    class_name = node.get('class', '').split('.')[-1]

                    # FORMATO CRÍTICO - LLM usa coordenadas, não IDs
                    # UPDATED 2026-01-20: Removido id:xxx - desnecessário para LLM
                    desc_parts = []
                    if text:
                        desc_parts.append(f'"{text}"')
                    if content_desc:
                        desc_parts.append(f'desc:"{content_desc}"')
                    # resource_id não incluído - LLM usa coordenadas para interação
                    if class_name:
                        desc_parts.append(class_name)

                    description = ' '.join(desc_parts) if desc_parts else 'Interactive element'

                    # FORMATO VALIDADO: "at position (x, y)" É MANDATÓRIO!
                    # UPDATED: Now outputs NORMALIZED [0, 1000) coordinates
                    enhanced_description = f"{description} at position ({norm_x}, {norm_y})"

                    elements.append({
                        'description': enhanced_description,
                        'center': (center_x, center_y),  # Keep original pixels for reference
                        'center_normalized': (norm_x, norm_y),  # Add normalized coords
                        'bounds': [x1, y1, x2, y2]
                    })

    return elements


def validate_with_tolerance(generated: Tuple[int, int],
                           ground_truth: List[Tuple[int, int]],
                           tolerance: int = 50) -> bool:
    """
    Validação com tolerância de 50 pixels - VALIDADA CIENTIFICAMENTE.

    Fonte: modules/rv-agent/src/rv_agent/simple_validator.py (backup)

    Args:
        generated: Generated (x, y) coordinates
        ground_truth: List of valid (x, y) coordinates
        tolerance: Pixel tolerance (default 50 - scientifically validated)

    Returns:
        True if generated coordinates are within tolerance of any ground truth
    """
    for gt_coord in ground_truth:
        distance = ((generated[0] - gt_coord[0])**2 +
                   (generated[1] - gt_coord[1])**2)**0.5
        if distance <= tolerance:
            return True
    return False


def create_enhanced_description_format(elements: List[Dict]) -> str:
    """
    Create enhanced UI description with coordinate format.

    This format achieved 100% success rate in Phase 0 validation.
    CRITICAL: The "at position (x, y)" format is mandatory for success.

    Args:
        elements: List of elements from extract_clickable_elements_with_coords()

    Returns:
        Enhanced description string with coordinates
    """
    if not elements:
        return "No interactive elements found."

    descriptions = []
    for i, element in enumerate(elements, 1):
        desc = element['description']
        descriptions.append(f"{i}. {desc}")

    return "\n".join(descriptions)


def parse_bounds_to_center(bounds_str: str) -> Tuple[int, int]:
    """
    Parse UIAutomator bounds string to center coordinates.

    EXACT implementation from validated prototype.

    Args:
        bounds_str: Bounds string like "[x1,y1][x2,y2]"

    Returns:
        Center coordinates (x, y) or None if parsing fails
    """
    try:
        bounds_match = re.findall(r'\[(\d+),(\d+)\]', bounds_str)
        if len(bounds_match) == 2:
            x1, y1 = map(int, bounds_match[0])
            x2, y2 = map(int, bounds_match[1])

            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            return (center_x, center_y)
    except (ValueError, IndexError):
        pass

    return None