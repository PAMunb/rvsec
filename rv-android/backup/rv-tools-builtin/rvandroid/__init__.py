"""
RVAndroid tool package for monitored operations testing.

This package provides the RVAndroid tool implementation with LLM-based
testing capabilities and hybrid variant configuration system.
"""

from .tool import RVAndroidTool, register_rvandroid_variants, RVANDROID_VARIANTS

__all__ = [
    'RVAndroidTool',
    'register_rvandroid_variants',
    'RVANDROID_VARIANTS'
]