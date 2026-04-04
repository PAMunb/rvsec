# tests/domain/test_task.py
import time
from datetime import datetime
from unittest.mock import MagicMock

from hypothesis import given, strategies as st

from rv_android_core.domain.task import (
    TaskState,
    ToolConfig,
    TaskConfiguration,
    TaskResult,
    Task,
)


class TestTaskState:
    """Tests for the TaskState enumeration"""

    def test_task_state_values(self):
        """Test that TaskState contains all expected states"""
        # Test that all expected states exist
        assert hasattr(TaskState, "CREATED")
        assert hasattr(TaskState, "INITIALIZING")
        assert hasattr(TaskState, "READY")
        assert hasattr(TaskState, "RUNNING")
        assert hasattr(TaskState, "COMPLETED")
        assert hasattr(TaskState, "ERROR")
        assert hasattr(TaskState, "CANCELED")

    def test_task_state_string_values(self):
        """Test that TaskState enum values are correct"""
        assert TaskState.CREATED.value == "created"
        assert TaskState.INITIALIZING.value == "initializing"
        assert TaskState.READY.value == "ready"
        assert TaskState.RUNNING.value == "running"
        assert TaskState.COMPLETED.value == "completed"
        assert TaskState.ERROR.value == "error"
        assert TaskState.CANCELED.value == "canceled"


class TestToolConfig:
    """Tests for ToolConfig data class"""

    def test_basic_tool_config(self):
        """Test creating a basic tool configuration"""
        tool_config = ToolConfig(name="droidbot")

        assert tool_config.name == "droidbot"
        assert tool_config.variant == "default"
        assert tool_config.parameters == {}

    def test_tool_config_with_variant(self):
        """Test creating a tool configuration with variant"""
        tool_config = ToolConfig(name="droidbot", variant="dfs_greedy")

        assert tool_config.name == "droidbot"
        assert tool_config.variant == "dfs_greedy"
        assert tool_config.parameters == {}

    def test_tool_config_with_params(self):
        """Test creating a tool configuration with parameters"""
        params = {"timeout": 300, "interval": 5}
        tool_config = ToolConfig(name="rvandroid", variant="vision", parameters=params)

        assert tool_config.name == "rvandroid"
        assert tool_config.variant == "vision"
        assert tool_config.parameters == params

    def test_get_full_tool_name_default_variant(self):
        """Test getting full tool name with default variant"""
        tool_config = ToolConfig(name="monkey")
        assert tool_config.get_full_tool_name() == "monkey"

    def test_get_full_tool_name_custom_variant(self):
        """Test getting full tool name with custom variant"""
        tool_config = ToolConfig(name="droidbot", variant="bfs_greedy")
        assert tool_config.get_full_tool_name() == "droidbot:bfs_greedy"

    def test_tool_config_to_dict(self):
        """Test tool configuration serialization"""
        tool_config = ToolConfig(name="ape", variant="sata", parameters={"debug": True})

        result = tool_config.to_dict()
        expected = {"name": "ape", "variant": "sata", "parameters": {"debug": True}}

        assert result == expected

    def test_tool_config_from_dict(self):
        """Test tool configuration deserialization"""
        data = {
            "name": "droidbot",
            "variant": "dfs_greedy",
            "parameters": {"count": 5000},
        }

        tool_config = ToolConfig.from_dict(data)

        assert tool_config.name == "droidbot"
        assert tool_config.variant == "dfs_greedy"
        assert tool_config.parameters == {"count": 5000}

    def test_tool_config_from_dict_minimal(self):
        """Test tool configuration deserialization with minimal data"""
        data = {"name": "monkey"}

        tool_config = ToolConfig.from_dict(data)

        assert tool_config.name == "monkey"
        assert tool_config.variant == "default"
        assert tool_config.parameters == {}

    def test_from_tool_specification_simple(self):
        """Test creating tool config from simple specification"""
        tool_config = ToolConfig.from_tool_specification("monkey")

        assert tool_config.name == "monkey"
        assert tool_config.variant == "default"
        assert tool_config.parameters == {}

    def test_from_tool_specification_with_variant(self):
        """Test creating tool config from specification with variant"""
        tool_config = ToolConfig.from_tool_specification("droidbot:dfs_greedy")

        assert tool_config.name == "droidbot"
        assert tool_config.variant == "dfs_greedy"
        assert tool_config.parameters == {}

    def test_from_tool_specification_with_params(self):
        """Test creating tool config from specification with parameters"""
        params = {"count": 1000}
        tool_config = ToolConfig.from_tool_specification("droidbot:random", params)

        assert tool_config.name == "droidbot"
        assert tool_config.variant == "random"
        assert tool_config.parameters == params

    def test_tool_config_string_representation(self):
        """Test tool config string representation"""
        tool_config = ToolConfig(name="droidbot", variant="dfs_greedy")
        expected = "ToolConfig(name=droidbot, variant=dfs_greedy)"
        assert str(tool_config) == expected

    def test_tool_config_repr(self):
        """Test tool config repr"""
        tool_config = ToolConfig(name="droidbot", variant="dfs_greedy")
        expected = "ToolConfig(droidbot, dfs_greedy)"
        assert repr(tool_config) == expected

    @given(
        name=st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
        ),
        variant=st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd", "Pc")),
        ),
    )
    def test_tool_config_property_based(self, name, variant):
        """Property-based test for tool config creation"""
        tool_config = ToolConfig(name=name, variant=variant)

        assert tool_config.name == name
        assert tool_config.variant == variant
        assert isinstance(tool_config.parameters, dict)

        # Test serialization roundtrip
        dict_repr = tool_config.to_dict()
        recreated = ToolConfig.from_dict(dict_repr)

        assert recreated.name == tool_config.name
        assert recreated.variant == tool_config.variant
        assert recreated.parameters == tool_config.parameters


class TestTaskConfiguration:
    """Tests for TaskConfiguration data class"""

    def test_basic_configuration(self):
        """Test creating a basic configuration with mandatory fields"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )

        assert config.apk_name == "test.apk"
        assert config.repetition == 1
        assert config.timeout == 60
        assert config.tool_config.name == "monkey"
        assert config.tool_config.variant == "default"
        # Check default values
        assert config.no_window is False
        assert config.clean_logcat is True
        assert config.skip_installation is False
        assert config.device_id == "emulator-5554"
        assert config.export_to_csv is True

    def test_full_configuration(self):
        """Test creating a configuration with all options specified"""
        tool_config = ToolConfig(name="droidbot", variant="dfs_greedy")
        config = TaskConfiguration(
            apk_name="test.apk",
            repetition=2,
            timeout=120,
            tool_config=tool_config,
            no_window=True,
            clean_logcat=False,
            skip_installation=True,
            device_id="custom-device-id",
            export_to_csv=False,
        )

        assert config.apk_name == "test.apk"
        assert config.repetition == 2
        assert config.timeout == 120
        assert config.tool_config.name == "droidbot"
        assert config.tool_config.variant == "dfs_greedy"
        assert config.no_window is True
        assert config.clean_logcat is False
        assert config.skip_installation is True
        assert config.device_id == "custom-device-id"
        assert config.export_to_csv is False

    def test_string_representation(self):
        """Test string representation of TaskConfiguration"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )

        expected = "TaskConfiguration(apk=test.apk, rep=1, timeout=60, tool=monkey)"
        assert str(config) == expected

    def test_string_representation_with_variant(self):
        """Test string representation with tool variant"""
        tool_config = ToolConfig(name="droidbot", variant="dfs_greedy")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )

        expected = "TaskConfiguration(apk=test.apk, rep=1, timeout=60, tool=droidbot:dfs_greedy)"
        assert str(config) == expected

    def test_to_dict(self):
        """Test TaskConfiguration serialization to dictionary"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )

        result = config.to_dict()

        assert result["apk_name"] == "test.apk"
        assert result["repetition"] == 1
        assert result["timeout"] == 60
        assert result["tool_config"]["name"] == "monkey"
        assert result["tool_config"]["variant"] == "default"

    def test_from_dict_new_format(self):
        """Test TaskConfiguration deserialization from dict with tool_config"""
        data = {
            "apk_name": "test.apk",
            "repetition": 1,
            "timeout": 60,
            "tool_config": {
                "name": "droidbot",
                "variant": "dfs_greedy",
                "parameters": {},
            },
        }

        config = TaskConfiguration.from_dict(data)

        assert config.apk_name == "test.apk"
        assert config.repetition == 1
        assert config.timeout == 60
        assert config.tool_config.name == "droidbot"
        assert config.tool_config.variant == "dfs_greedy"

    def test_from_dict_without_tool_config(self):
        """Test TaskConfiguration deserialization when tool_config key is missing"""
        data = {
            "apk_name": "test.apk",
            "repetition": 1,
            "timeout": 60,
        }

        config = TaskConfiguration.from_dict(data)

        assert config.apk_name == "test.apk"
        assert config.repetition == 1
        assert config.timeout == 60
        assert config.tool_config.name == ""
        assert config.tool_config.variant == "default"

    def test_create_from_tool_spec_simple(self):
        """Test creating configuration from simple tool spec"""
        config = TaskConfiguration.create_from_tool_spec(
            apk_name="test.apk", repetition=1, timeout=60, tool_spec="monkey"
        )

        assert config.apk_name == "test.apk"
        assert config.repetition == 1
        assert config.timeout == 60
        assert config.tool_config.name == "monkey"
        assert config.tool_config.variant == "default"

    def test_create_from_tool_spec_with_variant(self):
        """Test creating configuration from tool spec with variant"""
        config = TaskConfiguration.create_from_tool_spec(
            apk_name="test.apk",
            repetition=1,
            timeout=60,
            tool_spec="droidbot:bfs_greedy",
        )

        assert config.apk_name == "test.apk"
        assert config.repetition == 1
        assert config.timeout == 60
        assert config.tool_config.name == "droidbot"
        assert config.tool_config.variant == "bfs_greedy"

    def test_create_from_tool_spec_with_params(self):
        """Test creating configuration from tool spec with parameters"""
        params = {"count": 5000}
        config = TaskConfiguration.create_from_tool_spec(
            apk_name="test.apk",
            repetition=1,
            timeout=60,
            tool_spec="droidbot:random",
            parameters=params,
            no_window=True,
        )

        assert config.apk_name == "test.apk"
        assert config.repetition == 1
        assert config.timeout == 60
        assert config.tool_config.name == "droidbot"
        assert config.tool_config.variant == "random"
        assert config.tool_config.parameters == params
        assert config.no_window is True

    @given(
        apk_name=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd")),
            min_size=1,
            max_size=50,
        ),
        repetition=st.integers(min_value=1, max_value=10),
        timeout=st.integers(min_value=1, max_value=3600),
        tool_name=st.sampled_from(["monkey", "droidbot", "ape", "rvandroid"]),
        variant=st.sampled_from(
            ["default", "dfs_greedy", "bfs_greedy", "sata", "vision"]
        ),
    )
    def test_task_configuration_property_based(
        self, apk_name, repetition, timeout, tool_name, variant
    ):
        """Property-based test for task configuration creation"""
        tool_config = ToolConfig(name=tool_name, variant=variant)
        config = TaskConfiguration(
            apk_name=apk_name,
            repetition=repetition,
            timeout=timeout,
            tool_config=tool_config,
        )

        assert (
            config.apk_name == apk_name
        )  # Use safe alphabet that won't be modified by Pydantic
        assert config.repetition == repetition
        assert config.timeout == timeout
        assert config.tool_config.name == tool_name
        assert config.tool_config.variant == variant

        # Test serialization roundtrip
        dict_repr = config.to_dict()
        recreated = TaskConfiguration.from_dict(dict_repr)

        assert recreated.apk_name == config.apk_name
        assert recreated.repetition == config.repetition
        assert recreated.timeout == config.timeout
        assert recreated.tool_config.name == config.tool_config.name
        assert recreated.tool_config.variant == config.tool_config.variant


class TestTaskResult:
    """Tests for TaskResult data class"""

    def test_task_result_initialization(self):
        """Test TaskResult initialization"""
        result = TaskResult()

        assert result.state == TaskState.CREATED
        assert result.start_time is None
        assert result.end_time is None
        assert result.execution_time_seconds == 0.0
        assert result.error_message is None
        assert result.trace_file == ""
        assert result.logcat_file == ""

    def test_task_result_with_custom_values(self):
        """Test TaskResult with custom values"""
        start_time = datetime.now()
        result = TaskResult(
            state=TaskState.COMPLETED,
            start_time=start_time,
            error_message="Test error",
            trace_file="/path/to/trace",
            logcat_file="/path/to/logcat",
        )

        assert result.state == TaskState.COMPLETED
        assert result.start_time == start_time
        assert result.error_message == "Test error"
        assert result.trace_file == "/path/to/trace"
        assert result.logcat_file == "/path/to/logcat"


class TestTask:
    """Tests for Task class"""

    def test_task_initialization(self):
        """Test basic task initialization"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )

        task = Task(config=config)

        assert task.config == config
        assert task.result.state == TaskState.CREATED
        assert task.id is not None
        assert len(task.id) > 0
        assert task.app is None
        assert task.result is not None

    def test_task_initialization_with_custom_id(self):
        """Test task initialization with custom ID"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )

        custom_id = "custom_test_id"
        task = Task(config=config, task_id=custom_id)

        assert task.id == custom_id

    def test_set_app(self):
        """Test setting app for task"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=config)

        # Mock app
        app = MagicMock()
        app.package_name = "com.example.test"

        task.set_app(app)

        assert task.app == app

    def test_update_state(self):
        """Test updating task state"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=config)

        task.update_state(TaskState.RUNNING)

        assert task.result.state == TaskState.RUNNING

    def test_update_state_with_error(self):
        """Test updating task state with error message"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=config)

        error_msg = "Test error occurred"
        task.update_state(TaskState.ERROR, error_message=error_msg)

        assert task.result.state == TaskState.ERROR
        assert task.result.state == TaskState.ERROR
        assert task.result.error_message == error_msg

    def test_task_properties(self):
        """Test task properties"""
        tool_config = ToolConfig(name="droidbot", variant="dfs_greedy")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=2, timeout=120, tool_config=tool_config
        )
        task = Task(config=config)

        assert task.config.apk_name == "test.apk"
        assert task.config.repetition == 2
        assert task.config.timeout == 120
        assert task.config.tool_config.get_full_tool_name() == "droidbot:dfs_greedy"

    def test_mark_tool_execution_start(self):
        """Test marking tool execution start"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=config)

        task.mark_tool_execution_start()

        assert task.result.tool_execution_start is not None
        # Note: mark_tool_execution_start only sets tool_execution_start, not state

    def test_initialize_task(self):
        """Test task initialization with results directory"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=config)

        results_dir = "/tmp/test_results"
        task.initialize(results_dir)

        assert task.result.state == TaskState.READY
        assert task.results_dir is not None

        # Check that output files are set
        assert task.result.trace_file != ""
        assert task.result.logcat_file != ""

        # Check that files contain app name and tool name
        assert "test.apk" in task.result.trace_file
        assert "test.apk" in task.result.logcat_file

    def test_to_dict(self):
        """Test task serialization"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=config, task_id="test_task_id")

        result = task.to_dict()

        assert result["id"] == "test_task_id"
        assert result["config"]["apk_name"] == "test.apk"
        assert result["config"]["tool_config"]["name"] == "monkey"
        assert result["result"]["state"] == TaskState.CREATED.name

    def test_from_dict(self):
        """Test task deserialization"""
        data = {
            "id": "test_task_id",
            "config": {
                "apk_name": "test.apk",
                "repetition": 1,
                "timeout": 60,
                "tool_config": {
                    "name": "monkey",
                    "variant": "default",
                    "parameters": {},
                },
            },
            "result": {"state": "CREATED"},
        }

        task = Task.from_dict(data)

        assert task.id == "test_task_id"
        assert task.config.apk_name == "test.apk"
        assert task.config.tool_config.name == "monkey"
        assert task.result.state == TaskState.CREATED

    def test_string_representation(self):
        """Test task string representation"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=config, task_id="test_task_id")

        # Task string format: "Task[id={id}, {config}, state={state}]"
        result = str(task)
        assert "test_task_id" in result
        assert "test.apk" in result
        assert "monkey" in result
        assert "CREATED" in result

    @given(
        apk_name=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd")),
            min_size=1,
            max_size=50,
        ),
        repetition=st.integers(min_value=1, max_value=5),
        timeout=st.integers(min_value=30, max_value=600),
    )
    def test_task_property_based(self, apk_name, repetition, timeout):
        """Property-based test for task creation and serialization"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name=apk_name,
            repetition=repetition,
            timeout=timeout,
            tool_config=tool_config,
        )
        task = Task(config=config)

        # Test properties
        assert task.config.apk_name == apk_name
        assert task.config.repetition == repetition
        assert task.config.timeout == timeout
        assert task.result.state == TaskState.CREATED

        # Test serialization roundtrip
        dict_repr = task.to_dict()
        recreated = Task.from_dict(dict_repr)

        assert recreated.id == task.id
        assert recreated.config.apk_name == task.config.apk_name
        assert recreated.config.repetition == task.config.repetition
        assert recreated.config.timeout == task.config.timeout
        assert recreated.result.state == task.result.state


class TestTaskEdgeCases:
    """Tests for edge cases and error conditions"""

    def test_task_configuration_validation_errors(self):
        """Test task configuration edge cases"""
        tool_config = ToolConfig(name="monkey")

        # Test negative repetition (currently allowed by the model)
        config_neg_repetition = TaskConfiguration(
            apk_name="test.apk", repetition=-1, timeout=60, tool_config=tool_config
        )
        assert config_neg_repetition.repetition == -1

        # Test zero timeout (currently allowed by the model)
        config_zero_timeout = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=0, tool_config=tool_config
        )
        assert config_zero_timeout.timeout == 0

    def test_empty_tool_specification(self):
        """Test handling of empty tool specification"""
        tool_config = ToolConfig.from_tool_specification("")
        assert tool_config.name == ""
        assert tool_config.variant == "default"

    def test_tool_specification_with_multiple_colons(self):
        """Test handling of tool specification with multiple colons"""
        # Should split on first colon only
        tool_config = ToolConfig.from_tool_specification("tool:variant:extra")
        assert tool_config.name == "tool"
        assert tool_config.variant == "variant:extra"

    def test_tool_config_with_whitespace(self):
        """Test tool config handling of whitespace"""
        tool_config = ToolConfig.from_tool_specification("  droidbot : dfs_greedy  ")
        assert tool_config.name == "droidbot"
        assert tool_config.variant == "dfs_greedy"

    def test_task_state_transitions(self):
        """Test various task state transitions"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=config)

        # Test state progression
        assert task.result.state == TaskState.CREATED

        task.update_state(TaskState.INITIALIZING)
        assert task.result.state == TaskState.INITIALIZING

        task.update_state(TaskState.READY)
        assert task.result.state == TaskState.READY

        task.update_state(TaskState.RUNNING)
        assert task.result.state == TaskState.RUNNING

        task.update_state(TaskState.COMPLETED)
        assert task.result.state == TaskState.COMPLETED

    def test_task_with_long_execution_time(self):
        """Test task execution time calculation"""
        tool_config = ToolConfig(name="monkey")
        config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=config)

        task.mark_tool_execution_start()

        # Simulate some execution time
        time.sleep(0.1)

        # Tool execution time should be positive
        tool_time = task.get_time_since_tool_start()
        assert tool_time >= 0

    def test_task_serialization_with_missing_fields(self):
        """Test task serialization handling of missing optional fields"""
        minimal_data = {
            "id": "minimal_task",
            "config": {
                "apk_name": "minimal.apk",
                "repetition": 1,
                "timeout": 60,
                "tool_config": {"name": "monkey"},
            },
            "result": {"state": "CREATED"},
        }

        task = Task.from_dict(minimal_data)

        assert task.id == "minimal_task"
        assert task.config.apk_name == "minimal.apk"
        assert task.config.tool_config.name == "monkey"
        assert task.config.tool_config.variant == "default"
        assert task.result.state == TaskState.CREATED
