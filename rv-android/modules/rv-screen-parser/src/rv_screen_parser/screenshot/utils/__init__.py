"""
Utility components for screenshot analysis.

This package provides shared utility functions and classes used across
screenshot analysis components for geometric calculations, coordinate
validation, and spatial analysis operations.
"""

from .geometry_utils import GeometryUtils, get_geometry_utils

__all__ = [
    'GeometryUtils',
    'get_geometry_utils'
]