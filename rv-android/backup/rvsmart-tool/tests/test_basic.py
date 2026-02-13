"""
Basic tests for rvandroid-tool module.
"""

import pytest


class TestBasicFunctionality:
    """Basic tests for rvandroid-tool."""
    
    def test_import_works(self):
        """Test that module can be imported."""
        import rvandroid_tool
        assert rvandroid_tool is not None
        
    def test_config_import_works(self):
        """Test that config can be imported."""
        from rvandroid_tool.config.tool_config import RvAndroidToolConfig
        assert RvAndroidToolConfig is not None