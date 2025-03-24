# tests/experiment/test_task_storage.py
import json
import os
from datetime import datetime
from unittest.mock import patch

import pytest

from rvandroid.experiment.task.task_model import Task, TaskConfiguration, TaskStatus
from rvandroid.experiment.task.task_storage import TaskStorage


class TestTaskStorage:
    """Tests for TaskStorage class that persists tasks"""

    @pytest.fixture
    def storage_file(self, tmp_path):
        """Fixture providing a temporary storage file path"""
        return str(tmp_path / "tasks.json")

    @pytest.fixture
    def sample_task(self):
        """Fixture providing a sample task for testing"""
        config = TaskConfiguration(
            apk_name="test.apk",
            repetition=1,
            timeout=60,
            tool_name="monkey"
        )
        task = Task(config)
        task.id = 42  # Fixed ID for testing

        # Set some result data
        task.result.status = TaskStatus.EXECUTED
        task.result.start_time = datetime(2023, 1, 1, 10, 0, 0)
        task.result.end_time = datetime(2023, 1, 1, 10, 0, 30)
        task.result.execution_time_seconds = 30
        task.result.logcat_file = "/path/to/logcat.log"

        return task

    def test_init(self, storage_file):
        """Test initialization of TaskStorage"""
        storage = TaskStorage(storage_file)

        assert storage.storage_file == storage_file
        assert isinstance(storage.tasks, dict)
        assert len(storage.tasks) == 0
        assert storage.loaded is False

    def test_load_nonexistent_file(self, storage_file):
        """Test loading when file doesn't exist"""
        storage = TaskStorage(storage_file)
        result = storage.load()

        assert result is True
        assert storage.loaded is True
        assert len(storage.tasks) == 0

    def test_load_valid_file(self, storage_file, sample_task):
        """Test loading valid data from a file"""
        # Create a valid storage file
        task_data = {
            "id": 42,
            "config": {
                "apk_name": "test.apk",
                "repetition": 1,
                "timeout": 60,
                "tool_name": "monkey",
                "no_window": False,
                "clean_logcat": True,
                "skip_installation": False,
                "device_id": "emulator-5554"
            },
            "result": {
                "status": "EXECUTED",
                "start_time": "2023-01-01T10:00:00",
                "end_time": "2023-01-01T10:00:30",
                "execution_time_seconds": 30,
                "logcat_file": "/path/to/logcat.log",
                "trace_file": ""
            }
        }

        data = {
            "version": 1,
            "timestamp": "2023-01-01T10:01:00",
            "tasks": [task_data]
        }

        with open(storage_file, 'w') as f:
            json.dump(data, f)

        storage = TaskStorage(storage_file)
        result = storage.load()

        assert result is True
        assert storage.loaded is True
        assert len(storage.tasks) == 1
        assert 42 in storage.tasks

        loaded_task = storage.tasks[42]
        assert loaded_task.id == 42
        assert loaded_task.config.apk_name == "test.apk"
        assert loaded_task.result.status == TaskStatus.EXECUTED
        assert loaded_task.result.execution_time_seconds == 30

    def test_load_corrupt_file(self, storage_file):
        """Test loading behavior with corrupt file"""
        # Create an invalid JSON file
        with open(storage_file, 'w') as f:
            f.write("Not valid JSON")

        storage = TaskStorage(storage_file)
        result = storage.load()

        assert result is False
        assert storage.loaded is False
        assert len(storage.tasks) == 0

    def test_save_new_file(self, storage_file, sample_task):
        """Test saving tasks to a new file"""
        storage = TaskStorage(storage_file)
        storage.add_task(sample_task)

        result = storage.save()

        assert result is True
        assert os.path.exists(storage_file)

        # Verify content
        with open(storage_file, 'r') as f:
            data = json.load(f)

        assert "version" in data
        assert "timestamp" in data
        assert "tasks" in data
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == 42

    def test_save_error_handling(self, storage_file, sample_task):
        """Test error handling during save"""
        storage = TaskStorage(storage_file)
        storage.add_task(sample_task)

        # Mock open to raise an exception
        with patch('builtins.open', side_effect=IOError("Mock IO Error")):
            result = storage.save()

            assert result is False
            assert not os.path.exists(storage_file)

    def test_add_and_update_task(self, storage_file, sample_task):
        """Test adding and updating a task"""
        storage = TaskStorage(storage_file)

        # Add task
        storage.add_task(sample_task)
        assert 42 in storage.tasks
        assert storage.tasks[42] is sample_task

        # Update task
        with patch.object(storage, 'save') as mock_save:
            sample_task.result.error_message = "New error"
            storage.update_task(sample_task)

            assert storage.tasks[42].result.error_message == "New error"
            mock_save.assert_called_once()

    def test_get_task(self, storage_file, sample_task):
        """Test getting a task by ID"""
        storage = TaskStorage(storage_file)
        storage.add_task(sample_task)

        retrieved_task = storage.get_task(42)
        assert retrieved_task is sample_task

        # Task that doesn't exist
        assert storage.get_task(999) is None

    def test_get_tasks(self, storage_file, sample_task):
        """Test getting all tasks"""
        storage = TaskStorage(storage_file)
        storage.add_task(sample_task)

        # Create another task
        config2 = TaskConfiguration(
            apk_name="test2.apk",
            repetition=2,
            timeout=120,
            tool_name="droidbot"
        )
        task2 = Task(config2)
        task2.id = 43
        storage.add_task(task2)

        tasks = storage.get_tasks()
        assert len(tasks) == 2
        assert sample_task in tasks
        assert task2 in tasks

    def test_get_tasks_by_status(self, storage_file, sample_task):
        """Test getting tasks filtered by status"""
        storage = TaskStorage(storage_file)

        # Task 1 (Executed)
        sample_task.result.status = TaskStatus.EXECUTED
        storage.add_task(sample_task)

        # Task 2 (Error)
        config2 = TaskConfiguration(
            apk_name="test2.apk",
            repetition=2,
            timeout=120,
            tool_name="droidbot"
        )
        task2 = Task(config2)
        task2.id = 43
        task2.result.status = TaskStatus.ERROR
        storage.add_task(task2)

        # Get tasks with EXECUTED status
        executed_tasks = storage.get_tasks_by_status(TaskStatus.EXECUTED)
        assert len(executed_tasks) == 1
        assert executed_tasks[0].id == 42

        # Get tasks with ERROR status
        error_tasks = storage.get_tasks_by_status(TaskStatus.ERROR)
        assert len(error_tasks) == 1
        assert error_tasks[0].id == 43

        # Get tasks with status that no task has
        pending_tasks = storage.get_tasks_by_status(TaskStatus.RUNNING)
        assert len(pending_tasks) == 0

    def test_get_pending_tasks(self, storage_file):
        """Test getting pending tasks"""
        storage = TaskStorage(storage_file)

        # Create tasks with different statuses
        statuses = [
            TaskStatus.CREATED,
            TaskStatus.CONFIGURED,
            TaskStatus.RUNNING,
            TaskStatus.EXECUTED,
            TaskStatus.ERROR,
            TaskStatus.CANCELED
        ]

        for i, status in enumerate(statuses, 1):
            config = TaskConfiguration(
                apk_name=f"test{i}.apk",
                repetition=1,
                timeout=60,
                tool_name="monkey"
            )
            task = Task(config)
            task.id = i
            task.result.status = status
            storage.add_task(task)

        pending_tasks = storage.get_pending_tasks()

        # Should include CREATED, CONFIGURED, RUNNING, and CANCELED
        # Should exclude EXECUTED and ERROR
        assert len(pending_tasks) == 4

        pending_ids = [task.id for task in pending_tasks]
        assert 1 in pending_ids  # CREATED
        assert 2 in pending_ids  # CONFIGURED
        assert 3 in pending_ids  # RUNNING
        assert 6 in pending_ids  # CANCELED
        assert 4 not in pending_ids  # EXECUTED
        assert 5 not in pending_ids  # ERROR

    def test_serialize_task(self, storage_file, sample_task):
        """Test task serialization"""
        storage = TaskStorage(storage_file)

        result = storage._serialize_task(sample_task)

        assert result["id"] == 42
        assert result["config"]["apk_name"] == "test.apk"
        assert result["config"]["repetition"] == 1
        assert result["config"]["timeout"] == 60
        assert result["config"]["tool_name"] == "monkey"
        assert result["result"]["status"] == "EXECUTED"
        assert result["result"]["execution_time_seconds"] == 30

    def test_deserialize_task(self, storage_file):
        """Test task deserialization"""
        storage = TaskStorage(storage_file)

        task_data = {
            "id": 42,
            "config": {
                "apk_name": "test.apk",
                "repetition": 1,
                "timeout": 60,
                "tool_name": "monkey"
            },
            "result": {
                "status": "EXECUTED",
                "start_time": "2023-01-01T10:00:00",
                "end_time": "2023-01-01T10:00:30",
                "execution_time_seconds": 30,
                "logcat_file": "/path/to/logcat.log"
            }
        }

        task = storage._deserialize_task(task_data)

        assert task.id == 42
        assert task.config.apk_name == "test.apk"
        assert task.config.repetition == 1
        assert task.config.timeout == 60
        assert task.config.tool_name == "monkey"
        assert task.result.status == TaskStatus.EXECUTED
        assert task.result.start_time == datetime(2023, 1, 1, 10, 0, 0)
        assert task.result.end_time == datetime(2023, 1, 1, 10, 0, 30)
        assert task.result.execution_time_seconds == 30
        assert task.result.logcat_file == "/path/to/logcat.log"

    def test_deserialize_task_error(self, storage_file, caplog):
        """Test error handling during task deserialization"""
        storage = TaskStorage(storage_file)

        # Invalid task data (missing required fields)
        task_data = {
            "id": 42,
            # Missing config
            "result": {
                "status": "INVALID_STATUS"  # Invalid status
            }
        }

        task = storage._deserialize_task(task_data)

        assert task is None
        assert "Error deserializing task" in caplog.text
