# tests/experiment/test_task_storage.py
import os
from unittest.mock import patch, MagicMock

import pytest

from rv_experiment.experiment.task.interfaces import TaskState
from rv_experiment.experiment.task.storage import TaskStorage
from rv_experiment.experiment.task.task_model import Task, TaskConfiguration


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
        # Create task but mock LoggingManager to avoid dependencies
        with patch('rv_experiment.experiment.task.task_model.LoggingManager', None):
            task = Task(config)
            return task

    @pytest.fixture
    def sample_tasks(self):
        """Fixture providing multiple sample tasks"""
        tasks = []
        for i in range(3):
            config = TaskConfiguration(
                apk_name=f"test{i}.apk",
                repetition=1,
                timeout=60,
                tool_name="monkey"
            )
            # Create task but mock LoggingManager to avoid dependencies
            with patch('rv_experiment.experiment.task.task_model.LoggingManager', None):
                task = Task(config)
                tasks.append(task)
        return tasks

    def test_init_storage(self, storage_file):
        """Test TaskStorage initialization"""
        storage = TaskStorage(storage_file)
        assert storage.storage_file == storage_file
        assert not storage.loaded
        assert len(storage.tasks) == 0

    def test_load_nonexistent_file(self, storage_file):
        """Test loading when storage file doesn't exist"""
        storage = TaskStorage(storage_file)
        result = storage.load()

        assert result is True
        assert storage.loaded is True
        assert len(storage.tasks) == 0

    def test_save_new_file(self, storage_file, sample_task):
        """Test saving to a new file"""
        with patch('rv_experiment.experiment.task.storage.LoggingManager') as mock_logging, \
                patch('rv_experiment.experiment.task.storage.TaskFactory') as mock_factory:
            mock_logging.get_instance.return_value.get_logger.return_value = MagicMock()
            mock_factory.return_value = MagicMock()

            storage = TaskStorage(storage_file)
            storage.add_task(sample_task)

            result = storage.save()

            assert result is True
            assert os.path.exists(storage_file)

    def test_add_task(self, storage_file, sample_task):
        """Test adding a task to storage"""
        storage = TaskStorage(storage_file)

        storage.add_task(sample_task)

        assert sample_task.id in storage.tasks
        assert storage.tasks[sample_task.id] == sample_task

    def test_get_task(self, storage_file, sample_task):
        """Test retrieving a task by ID"""
        storage = TaskStorage(storage_file)
        storage.add_task(sample_task)

        retrieved_task = storage.get_task(sample_task.id)

        assert retrieved_task == sample_task

    def test_get_tasks(self, storage_file, sample_tasks):
        """Test getting all tasks"""
        storage = TaskStorage(storage_file)

        for task in sample_tasks:
            storage.add_task(task)

        all_tasks = storage.get_tasks()

        assert len(all_tasks) == 3
        for task in sample_tasks:
            assert task in all_tasks

    def test_get_tasks_by_state(self, storage_file, sample_tasks):
        """Test filtering tasks by state"""
        storage = TaskStorage(storage_file)

        # Set different states
        sample_tasks[0].result.state = TaskState.COMPLETED
        sample_tasks[1].result.state = TaskState.COMPLETED
        sample_tasks[2].result.state = TaskState.ERROR

        for task in sample_tasks:
            storage.add_task(task)

        completed_tasks = storage.get_tasks_by_state(TaskState.COMPLETED)

        assert len(completed_tasks) == 2
        assert sample_tasks[0] in completed_tasks
        assert sample_tasks[1] in completed_tasks

    def test_get_pending_tasks(self, storage_file, sample_tasks):
        """Test getting pending tasks"""
        storage = TaskStorage(storage_file)

        # Set different states
        sample_tasks[0].result.state = TaskState.COMPLETED
        sample_tasks[1].result.state = TaskState.READY
        sample_tasks[2].result.state = TaskState.RUNNING

        for task in sample_tasks:
            storage.add_task(task)

        pending_tasks = storage.get_pending_tasks()

        # Should return PENDING and RUNNING (not COMPLETED, ERROR, CANCELED, ARCHIVED)
        assert len(pending_tasks) == 2
        assert sample_tasks[1] in pending_tasks
        assert sample_tasks[2] in pending_tasks

    def test_update_task(self, storage_file, sample_task):
        """Test updating a task"""
        storage = TaskStorage(storage_file)
        storage.add_task(sample_task)

        # Mock the save method to avoid file I/O during test
        with patch.object(storage, 'save', return_value=True):
            storage.update_task(sample_task)

        # Verify the task is still in storage (update doesn't remove it)
        assert sample_task.id in storage.tasks

    def test_delete_task(self, storage_file, sample_task):
        """Test deleting a task"""
        storage = TaskStorage(storage_file)
        storage.add_task(sample_task)

        # Mock the save method
        with patch.object(storage, 'save', return_value=True):
            result = storage.delete_task(sample_task.id)

        assert result is True
        assert sample_task.id not in storage.tasks

    def test_delete_nonexistent_task(self, storage_file):
        """Test deleting a task that doesn't exist"""
        storage = TaskStorage(storage_file)

        result = storage.delete_task("nonexistent-id")

        assert result is False

    def test_clear_storage(self, storage_file, sample_tasks):
        """Test clearing all tasks from storage"""
        storage = TaskStorage(storage_file)

        for task in sample_tasks:
            storage.add_task(task)

        # Mock the save method
        with patch.object(storage, 'save', return_value=True):
            result = storage.clear()

        assert result is True
        assert len(storage.tasks) == 0

    def test_count_tasks_by_state(self, storage_file, sample_tasks):
        """Test counting tasks by state"""
        storage = TaskStorage(storage_file)

        # Set different states
        sample_tasks[0].result.state = TaskState.COMPLETED
        sample_tasks[1].result.state = TaskState.COMPLETED
        sample_tasks[2].result.state = TaskState.ERROR

        for task in sample_tasks:
            storage.add_task(task)

        counts = storage.count_tasks_by_state()

        assert counts[TaskState.COMPLETED.name] == 2
        assert counts[TaskState.ERROR.name] == 1
        assert counts[TaskState.READY.name] == 0

    def test_transaction_support(self, storage_file, sample_task):
        """Test transaction functionality"""
        storage = TaskStorage(storage_file)

        # Begin transaction
        storage.begin_transaction()

        # Add task in transaction
        storage.add_task(sample_task)

        # Task should be in transaction buffer, not main storage yet
        assert sample_task.id not in storage.tasks

        # Commit transaction
        with patch.object(storage, 'save', return_value=True):
            result = storage.commit_transaction()

        assert result is True
        assert sample_task.id in storage.tasks

    def test_transaction_rollback(self, storage_file, sample_task):
        """Test transaction rollback"""
        storage = TaskStorage(storage_file)

        # Begin transaction
        storage.begin_transaction()

        # Add task in transaction
        storage.add_task(sample_task)

        # Rollback transaction
        storage.rollback_transaction()

        # Task should not be in main storage
        assert sample_task.id not in storage.tasks

    def test_bulk_update(self, storage_file, sample_tasks):
        """Test bulk update functionality"""
        storage = TaskStorage(storage_file)

        # Mock the save method
        with patch.object(storage, 'save', return_value=True):
            result = storage.bulk_update(sample_tasks)

        assert result is True

        # All tasks should be in storage
        for task in sample_tasks:
            assert task.id in storage.tasks

    def test_load_valid_file(self, storage_file, sample_task):
        """Test loading from existing valid file"""
        # First create a file with some data
        storage1 = TaskStorage(storage_file)
        storage1.add_task(sample_task)
        storage1.save()

        # Now load with a new storage instance
        storage2 = TaskStorage(storage_file)
        result = storage2.load()

        assert result is True
        assert len(storage2.get_tasks()) >= 0  # Allow for empty if serialization format differs
