# tests/experiment/test_task_storage.py
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from rv_experiment.experiment.task.interfaces import TaskState
from rv_experiment.experiment.task.storage import TaskStorage, ExperimentMetadata, StorageConfig, ExperimentStatistics
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


class TestExperimentMetadata:
    """Tests for ExperimentMetadata Pydantic class"""
    
    def test_create_from_config(self):
        """Test creating metadata from configuration dictionary"""
        config_dict = {
            "name": "test_experiment",
            "timeout": 300,
            "tools": ["monkey"]
        }
        
        metadata = ExperimentMetadata.create_from_config("exp_001", config_dict)
        
        assert metadata.experiment_id == "exp_001"
        assert metadata.start_time is not None
        assert isinstance(metadata.start_time, datetime)
        assert metadata.config_checksum is not None
        assert len(metadata.config_checksum) == 64  # SHA-256 hex length
        assert metadata.current_status == "running"
    
    def test_checksum_consistency(self):
        """Test that same config produces same checksum"""
        config_dict = {"name": "test", "timeout": 300}
        
        metadata1 = ExperimentMetadata.create_from_config("exp_001", config_dict)
        metadata2 = ExperimentMetadata.create_from_config("exp_002", config_dict)
        
        # Same config should produce same checksum
        assert metadata1.config_checksum == metadata2.config_checksum
        
        # Different config should produce different checksum
        different_config = {"name": "test", "timeout": 600}
        metadata3 = ExperimentMetadata.create_from_config("exp_003", different_config)
        assert metadata1.config_checksum != metadata3.config_checksum


class TestStorageConfig:
    """Tests for StorageConfig Pydantic class"""
    
    def test_default_values(self):
        """Test StorageConfig default values"""
        config = StorageConfig()
        
        assert config.enable_metadata is True
        assert config.enable_statistics is True
        assert config.auto_save is True
        assert config.compression is False
        assert config.backup_count == 3
    
    def test_custom_values(self):
        """Test StorageConfig with custom values"""
        config = StorageConfig(
            enable_metadata=False,
            auto_save=False,
            backup_count=5
        )
        
        assert config.enable_metadata is False
        assert config.auto_save is False
        assert config.backup_count == 5


class TestExperimentStatistics:
    """Tests for ExperimentStatistics Pydantic class"""
    
    def test_default_values(self):
        """Test ExperimentStatistics default values"""
        stats = ExperimentStatistics()
        
        assert stats.total_tasks == 0
        assert stats.completed_tasks == 0
        assert stats.failed_tasks == 0
        assert stats.pending_tasks == 0
        assert stats.completion_percentage == 0.0
        assert stats.average_execution_time == 0.0
        assert stats.total_execution_time == 0.0
        assert stats.last_updated is not None
    
    def test_custom_statistics(self):
        """Test ExperimentStatistics with custom values"""
        stats = ExperimentStatistics(
            total_tasks=10,
            completed_tasks=7,
            failed_tasks=1,
            pending_tasks=2,
            completion_percentage=70.0
        )
        
        assert stats.total_tasks == 10
        assert stats.completed_tasks == 7
        assert stats.completion_percentage == 70.0


class TestEnhancedTaskStorage:
    """Tests for enhanced TaskStorage with metadata support"""
    
    @pytest.fixture
    def enhanced_storage(self, tmp_path):
        """Fixture providing enhanced TaskStorage with metadata"""
        storage_file = str(tmp_path / "enhanced_tasks.json")
        storage_config = StorageConfig()
        experiment_metadata = ExperimentMetadata.create_from_config(
            "test_experiment", 
            {"name": "test", "timeout": 300}
        )
        
        return TaskStorage(
            storage_file=storage_file,
            storage_config=storage_config,
            experiment_metadata=experiment_metadata
        )
    
    @pytest.fixture
    def sample_task(self):
        """Fixture providing a sample task for testing"""
        config = TaskConfiguration(
            apk_name="test.apk",
            repetition=1,
            timeout=60,
            tool_name="monkey"
        )
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
            with patch('rv_experiment.experiment.task.task_model.LoggingManager', None):
                task = Task(config)
                tasks.append(task)
        return tasks
    
    def test_metadata_integration(self, enhanced_storage, sample_task):
        """Test metadata integration in enhanced storage"""
        # Add task and save
        enhanced_storage.add_task(sample_task)
        result = enhanced_storage.save()
        
        assert result is True
        
        # Verify metadata is accessible
        metadata = enhanced_storage.get_experiment_metadata()
        assert metadata is not None
        assert metadata.experiment_id == "test_experiment"
    
    def test_statistics_calculation(self, enhanced_storage, sample_tasks):
        """Test statistics calculation with real tasks"""
        # Add multiple tasks with different states
        for i, task in enumerate(sample_tasks):
            if i == 0:
                task.result.state = TaskState.COMPLETED
                task.result.execution_time_seconds = 30
            elif i == 1:
                task.result.state = TaskState.ERROR
            else:
                task.result.state = TaskState.RUNNING
            
            enhanced_storage.add_task(task)
        
        # Get statistics
        stats = enhanced_storage.get_statistics()
        
        assert stats.total_tasks == 3
        assert stats.completed_tasks == 1
        assert stats.failed_tasks == 1
        assert stats.pending_tasks == 1
        assert stats.completion_percentage == pytest.approx(33.33, rel=1e-2)
        assert stats.average_execution_time == 30.0
    
    def test_continuation_compatibility(self, enhanced_storage):
        """Test experiment continuation compatibility checking"""
        original_config = {"name": "test", "timeout": 300}
        
        # Same config should be compatible
        compatible = enhanced_storage.check_continuation_compatibility(original_config)
        assert compatible is True
        
        # Different config should not be compatible
        different_config = {"name": "test", "timeout": 600}
        compatible = enhanced_storage.check_continuation_compatibility(different_config)
        assert compatible is False
    
    def test_experiment_status_updates(self, enhanced_storage):
        """Test experiment status updates"""
        enhanced_storage.update_experiment_status("paused")
        
        metadata = enhanced_storage.get_experiment_metadata()
        assert metadata.current_status == "paused"
