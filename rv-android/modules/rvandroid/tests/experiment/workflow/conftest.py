import os
import sys
import pytest

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

# Optional: Configure logging for tests
import logging
logging.basicConfig(level=logging.DEBUG)
