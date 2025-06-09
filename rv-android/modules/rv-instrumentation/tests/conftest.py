"""
Test configuration and fixtures for rv-instrumentation tests.

This module provides common test fixtures and configuration for the 
rv-instrumentation test suite.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch


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
    mock_env = {
        'ANDROID_HOME': '/mock/android/sdk',
        'RVSEC_HOME': '/mock/rvsec'
    }
    
    with patch.dict(os.environ, mock_env):
        yield mock_env


@pytest.fixture
def sample_monitor_artifacts(temp_workspace):
    """
    Create sample monitor artifacts for testing.
    
    Args:
        temp_workspace: Temporary workspace fixture
        
    Returns:
        Path: Directory containing sample monitor artifacts
    """
    monitor_dir = temp_workspace / "monitors"
    monitor_dir.mkdir()
    
    # Create sample AspectJ files
    (monitor_dir / "MonitorAspect.aj").write_text("""
    public aspect MonitorAspect {
        pointcut monitoredOperation() : call(* javax.crypto.Cipher.getInstance(..));
        before() : monitoredOperation() {
            System.out.println("Monitor triggered");
        }
    }
    """)
    
    # Create sample Java monitor classes
    (monitor_dir / "RuntimeMonitor.java").write_text("""
    public class RuntimeMonitor {
        public static void monitorEvent(String event) {
            System.out.println("Monitor event: " + event);
        }
    }
    """)
    
    return monitor_dir


@pytest.fixture
def mock_tools_directory(temp_workspace):
    """
    Create mock tools directory structure.
    
    Args:
        temp_workspace: Temporary workspace fixture
        
    Returns:
        dict: Dictionary with tool paths
    """
    tools_dir = temp_workspace / "tools"
    tools_dir.mkdir()
    
    # Create dex2jar tools
    dex2jar_dir = tools_dir / "dex2jar"
    dex2jar_dir.mkdir()
    
    dex2jar_tools = {
        'dex2jar': dex2jar_dir / "d2j-dex2jar.sh",
        'asm_verify': dex2jar_dir / "d2j-asm-verify.sh", 
        'apk_sign': dex2jar_dir / "d2j-apk-sign.sh"
    }
    
    # Create tool files
    for tool_path in dex2jar_tools.values():
        tool_path.touch()
        tool_path.chmod(0o755)
    
    return {
        'dex2jar_home': str(dex2jar_dir),
        'tools': dex2jar_tools
    }


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
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )