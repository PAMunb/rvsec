import pytest
import json
from pathlib import Path
import tempfile
import os

from rv_platform.config.platform_config import ToolConfig, PlatformConfig
from pydantic import ValidationError

# --- ToolConfig Tests ---

def test_tool_config_valid_creation():
    config = ToolConfig(name="test_tool", variants=["v1"], parameters={"key": "value"})
    assert config.name == "test_tool"
    assert config.variants == ["v1"]
    assert config.parameters == {"key": "value"}

def test_tool_config_default_values():
    config = ToolConfig(name="another_tool")
    assert config.name == "another_tool"
    assert config.variants == []
    assert config.parameters == {}

def test_tool_config_empty_name_raises_error():
    with pytest.raises(ValidationError, match="Tool name cannot be empty"):
        ToolConfig(name="")

def test_tool_config_whitespace_name_raises_error():
    with pytest.raises(ValidationError, match="Tool name cannot be empty"):
        ToolConfig(name="   ")

# --- PlatformConfig Tests ---

@pytest.fixture
def temp_apks_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a dummy APK file for testing apks_dir validation
        Path(tmpdir, "test.apk").touch()
        yield tmpdir

@pytest.fixture
def temp_config_file(temp_apks_dir):
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config_data = {
            "apks_dir": temp_apks_dir,
            "tools": [{"name": "tool1", "variants": ["v1"]}],
            "repetitions": 2,
            "timeouts": [30, 60],
            "max_parallel_tasks": 2,
            "no_window": True,
            "results_dir": "test_results",
            "task_storage_file": "test_tasks.json",
            "log_level": "DEBUG"
        }
        json.dump(config_data, f)
    yield f.name
    os.unlink(f.name) # Clean up the temporary file

def test_platform_config_valid_creation(temp_apks_dir):
    config = PlatformConfig(
        apks_dir=temp_apks_dir,
        tools=[ToolConfig(name="tool1")],
        repetitions=1,
        timeouts=[60]
    )
    assert config.apks_dir == temp_apks_dir
    assert len(config.tools) == 1
    assert config.repetitions == 1
    assert config.timeouts == [60]
    assert config.max_parallel_tasks == 1 # Default
    assert config.no_window == False # Default
    assert config.results_dir == "results" # Default
    assert config.task_storage_file == "tasks.json" # Default
    assert config.log_level == "INFO" # Default

def test_platform_config_apks_dir_empty_raises_error():
    with pytest.raises(ValidationError, match="APKs directory cannot be empty"):
        PlatformConfig(apks_dir="", tools=[ToolConfig(name="t")], repetitions=1, timeouts=[1])

def test_platform_config_apks_dir_non_existent_raises_error():
    with pytest.raises(ValidationError, match="APKs directory does not exist"):
        PlatformConfig(apks_dir="/non/existent/path", tools=[ToolConfig(name="t")], repetitions=1, timeouts=[1])

def test_platform_config_apks_dir_not_a_directory_raises_error():
    with tempfile.NamedTemporaryFile() as f:
        with pytest.raises(ValidationError, match="APKs directory is not a directory"):
            PlatformConfig(apks_dir=f.name, tools=[ToolConfig(name="t")], repetitions=1, timeouts=[1])

def test_platform_config_tools_empty_raises_error(temp_apks_dir):
    with pytest.raises(ValidationError, match="At least one tool must be specified"):
        PlatformConfig(apks_dir=temp_apks_dir, tools=[], repetitions=1, timeouts=[1])

def test_platform_config_repetitions_less_than_1_raises_error(temp_apks_dir):
    with pytest.raises(ValidationError, match="Repetitions must be at least 1"):
        PlatformConfig(apks_dir=temp_apks_dir, tools=[ToolConfig(name="t")], repetitions=0, timeouts=[1])

def test_platform_config_timeouts_empty_raises_error(temp_apks_dir):
    with pytest.raises(ValidationError, match="At least one timeout must be specified"):
        PlatformConfig(apks_dir=temp_apks_dir, tools=[ToolConfig(name="t")], repetitions=1, timeouts=[])

def test_platform_config_timeouts_less_than_1_raises_error(temp_apks_dir):
    with pytest.raises(ValidationError, match="Timeout must be at least 1 second"):
        PlatformConfig(apks_dir=temp_apks_dir, tools=[ToolConfig(name="t")], repetitions=1, timeouts=[0])

def test_platform_config_max_parallel_tasks_less_than_1_raises_error(temp_apks_dir):
    with pytest.raises(ValidationError, match="Max parallel tasks must be at least 1"):
        PlatformConfig(apks_dir=temp_apks_dir, tools=[ToolConfig(name="t")], repetitions=1, timeouts=[1], max_parallel_tasks=0)

def test_platform_config_log_level_invalid_raises_error(temp_apks_dir):
    with pytest.raises(ValidationError, match="Log level must be one of"):
        PlatformConfig(apks_dir=temp_apks_dir, tools=[ToolConfig(name="t")], repetitions=1, timeouts=[1], log_level="INVALID")

def test_platform_config_from_file_valid(temp_config_file, temp_apks_dir):
    config = PlatformConfig.from_file(temp_config_file)
    assert config.apks_dir == temp_apks_dir
    assert len(config.tools) == 1
    assert config.tools[0].name == "tool1"
    assert config.repetitions == 2
    assert config.timeouts == [30, 60]
    assert config.max_parallel_tasks == 2
    assert config.no_window == True
    assert config.results_dir == "test_results"
    assert config.task_storage_file == "test_tasks.json"
    assert config.log_level == "DEBUG"

def test_platform_config_from_file_non_existent_raises_error():
    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        PlatformConfig.from_file("/non/existent/config.json")

def test_platform_config_from_file_invalid_json_raises_error():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        f.write("{invalid json")
    with pytest.raises(ValueError, match="Invalid JSON in configuration file"):
        PlatformConfig.from_file(f.name)
    os.unlink(f.name)

def test_platform_config_to_file(temp_apks_dir):
    config = PlatformConfig(
        apks_dir=temp_apks_dir,
        tools=[ToolConfig(name="tool1")],
        repetitions=1,
        timeouts=[60]
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output_config.json"
        config.to_file(str(output_path))
        
        assert output_path.exists()
        loaded_config = PlatformConfig.from_file(str(output_path))
        assert loaded_config.apks_dir == config.apks_dir
        assert loaded_config.tools[0].name == config.tools[0].name

def test_platform_config_get_total_tasks(temp_apks_dir):
    # Create multiple dummy APKs
    Path(temp_apks_dir, "test2.apk").touch()
    Path(temp_apks_dir, "test3.apk").touch()

    config = PlatformConfig(
        apks_dir=temp_apks_dir,
        tools=[
            ToolConfig(name="toolA", variants=["v1", "v2"]),
            ToolConfig(name="toolB") # No variants specified, so 1 variant
        ],
        repetitions=2,
        timeouts=[10, 20, 30]
    )
    
    # Expected: 3 APKs * (2 variants for toolA + 1 variant for toolB) * 2 repetitions * 3 timeouts
    # 3 * (2 + 1) * 2 * 3 = 3 * 3 * 2 * 3 = 54
    assert config.get_total_tasks() == 54

def test_platform_config_validate_dependencies_no_apks_raises_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = PlatformConfig(
            apks_dir=tmpdir, # Empty directory
            tools=[ToolConfig(name="tool1")],
            repetitions=1,
            timeouts=[60]
        )
        with pytest.raises(ValueError, match="No APK files found"):
            config.validate_dependencies()

def test_platform_config_validate_dependencies_valid(temp_apks_dir):
    config = PlatformConfig(
        apks_dir=temp_apks_dir,
        tools=[ToolConfig(name="tool1")],
        repetitions=1,
        timeouts=[60]
    )
    assert config.validate_dependencies() == True


