import pytest
import os
import sys
import logging
from unittest.mock import MagicMock

# Add the parent directory to the path to make imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Global fixtures that can be used by multiple test modules

@pytest.fixture
def mock_logger():
    """Fixture that provides a mock logger"""
    logger = MagicMock()
    return logger

@pytest.fixture
def suppress_logging():
    """Fixture to suppress logging during tests"""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)