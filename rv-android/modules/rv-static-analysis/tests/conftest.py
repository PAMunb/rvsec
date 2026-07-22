"""
Test configuration and fixtures for rv-static-analysis tests.

This module provides common test fixtures and configuration for the
rv-static-analysis test suite.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_workspace():
    """
    Create a temporary workspace for testing.

    Returns:
        Path: Temporary directory path that is automatically cleaned up
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_android_environment():
    """
    Mock Android environment variables and paths.

    Returns:
        dict: Mocked environment configuration
    """
    mock_env = {"ANDROID_HOME": "/mock/android/sdk", "RVSEC_HOME": "/mock/rvsec"}

    with patch.dict(os.environ, mock_env):
        yield mock_env


@pytest.fixture
def mock_static_analysis_tools(temp_workspace):
    """
    Create mock static analysis tools directory structure.

    The unified analysis uses GATOR with the RvsecAnalysisClient JAR.

    Args:
        temp_workspace: Temporary workspace fixture

    Returns:
        dict: Dictionary with tool paths
    """
    tools_dir = temp_workspace / "lib"
    tools_dir.mkdir()

    # Create GATOR directory with launcher and analysis client JAR
    gator_dir = tools_dir / "gator"
    gator_dir.mkdir()
    gator_python = gator_dir / "gator"
    gator_python.touch()
    gator_python.chmod(0o755)
    analysis_client_jar = gator_dir / "rvsec-analysis-client.jar"
    analysis_client_jar.touch()

    return {
        "lib_dir": str(tools_dir),
        "gator_dir": str(gator_dir),
        "gator_python": str(gator_python),
        "analysis_client_jar": str(analysis_client_jar),
    }


@pytest.fixture
def mock_android_sdk(temp_workspace):
    """
    Create mock Android SDK structure.

    Args:
        temp_workspace: Temporary workspace fixture

    Returns:
        dict: Dictionary with Android SDK paths
    """
    android_sdk = temp_workspace / "android-sdk"
    android_sdk.mkdir()

    platforms_dir = android_sdk / "platforms"
    platforms_dir.mkdir()

    # Create multiple Android API levels
    for api_level in ["27", "28", "29"]:
        api_dir = platforms_dir / f"android-{api_level}"
        api_dir.mkdir()
        android_jar = api_dir / "android.jar"
        android_jar.touch()

    return {
        "android_home": str(android_sdk),
        "platforms_dir": str(platforms_dir),
        "android_jar": str(platforms_dir / "android-29" / "android.jar"),
    }


@pytest.fixture
def mock_mop_directory(temp_workspace):
    """
    Create mock MOP specifications directory.

    Args:
        temp_workspace: Temporary workspace fixture

    Returns:
        Path: Path to MOP directory
    """
    mop_dir = temp_workspace / "specs" / "jca"
    mop_dir.mkdir(parents=True)

    # Create sample MOP specification files
    (mop_dir / "Cipher.mop").write_text("Cipher monitor specification")
    (mop_dir / "KeyGenerator.mop").write_text("KeyGenerator monitor specification")

    return mop_dir


@pytest.fixture
def sample_apk_file(temp_workspace):
    """
    Create a sample APK file for testing.

    Args:
        temp_workspace: Temporary workspace fixture

    Returns:
        Path: Path to sample APK file
    """
    apk_file = temp_workspace / "test_app.apk"

    # Create a minimal APK-like file (just for testing file operations)
    apk_file.write_bytes(b"PK\x03\x04")  # ZIP signature (APKs are ZIP files)

    return apk_file


# Configure pytest options
def pytest_configure(config):
    """Configure pytest with custom markers and options."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
