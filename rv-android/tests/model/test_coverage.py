import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from rvandroid.model.coverage import (
    MethodCoverageData,
    ClassCoverageData,
    CoverageMetrics,
    LogcatRepository
)
from rvandroid.model.log import RvCoverageLog, RvErrorLog


class TestMethodCoverageData:
    """Tests for the MethodCoverageData class"""

    @pytest.fixture
    def sample_method_data(self):
        """Create a sample method coverage data for testing"""
        return MethodCoverageData(
            class_name="com.example.app.MainActivity",
            method_name="onCreate",
            signature="com.example.app.MainActivity.onCreate(android.os.Bundle)",
            parameters=["android.os.Bundle"],
            reachable=True,
            reaches_mop=False,
            directly_reaches_mop=False
        )

    def test_method_coverage_data_initialization(self, sample_method_data):
        """Test MethodCoverageData constructor"""
        assert sample_method_data.class_name == "com.example.app.MainActivity"
        assert sample_method_data.method_name == "onCreate"
        assert sample_method_data.signature == "com.example.app.MainActivity.onCreate(android.os.Bundle)"
        assert sample_method_data.parameters == ["android.os.Bundle"]
        assert sample_method_data.reachable is True
        assert sample_method_data.reaches_mop is False
        assert sample_method_data.directly_reaches_mop is False
        assert sample_method_data.called is False
        assert sample_method_data.call_count == 0
        assert sample_method_data.first_called_at is None
        assert sample_method_data.last_called_at is None

    def test_register_call(self, sample_method_data):
        """Test register_call method"""
        # First call
        timestamp = datetime.now()
        sample_method_data.register_call(timestamp)

        assert sample_method_data.called is True
        assert sample_method_data.call_count == 1
        assert sample_method_data.first_called_at == timestamp
        assert sample_method_data.last_called_at == timestamp

        # Second call with different timestamp
        timestamp2 = timestamp + timedelta(minutes=5)
        sample_method_data.register_call(timestamp2)

        assert sample_method_data.call_count == 2
        assert sample_method_data.first_called_at == timestamp  # Should remain the same
        assert sample_method_data.last_called_at == timestamp2  # Should be updated

        # Call without timestamp
        with patch('rvandroid.model.coverage.datetime') as mock_datetime:
            mock_now = datetime.now() + timedelta(minutes=10)
            mock_datetime.now.return_value = mock_now

            sample_method_data.register_call()

            assert sample_method_data.call_count == 3
            assert sample_method_data.last_called_at == mock_now

    def test_to_dict(self, sample_method_data):
        """Test to_dict method"""
        # Uncalled method
        dict_data = sample_method_data.to_dict()

        assert dict_data["class_name"] == "com.example.app.MainActivity"
        assert dict_data["method_name"] == "onCreate"
        assert dict_data["signature"] == "com.example.app.MainActivity.onCreate(android.os.Bundle)"
        assert dict_data["parameters"] == ["android.os.Bundle"]
        assert dict_data["reachable"] is True
        assert dict_data["called"] is False
        assert dict_data["first_called_at"] is None

        # Called method
        timestamp = datetime.now()
        sample_method_data.register_call(timestamp)
        dict_data = sample_method_data.to_dict()

        assert dict_data["called"] is True
        assert dict_data["call_count"] == 1
        assert dict_data["first_called_at"] == timestamp.isoformat()
        assert dict_data["last_called_at"] == timestamp.isoformat()

    def test_from_coverage_log(self):
        """Test from_coverage_log method"""
        timestamp = datetime.now()
        log = RvCoverageLog(
            clazz="com.example.app.MainActivity",
            method="onCreate",
            params="android.os.Bundle",
            signature="com.example.app.MainActivity.onCreate(android.os.Bundle)"
        )
        log.time_occurred = timestamp

        method_data = MethodCoverageData.from_coverage_log(log)

        assert method_data.class_name == "com.example.app.MainActivity"
        assert method_data.method_name == "onCreate"
        assert method_data.signature == "com.example.app.MainActivity.onCreate(android.os.Bundle)"
        assert method_data.parameters == ["android.os.Bundle"]
        assert method_data.called is True
        assert method_data.call_count == 1
        assert method_data.first_called_at == timestamp
        assert method_data.last_called_at == timestamp


class TestClassCoverageData:
    """Tests for the ClassCoverageData class"""

    @pytest.fixture
    def sample_class_data(self):
        """Create a sample class coverage data for testing"""
        return ClassCoverageData(
            name="com.example.app.MainActivity",
            is_activity=True,
            is_main_activity=True
        )

    @pytest.fixture
    def sample_methods(self):
        """Create sample method coverage data for testing"""
        method1 = MethodCoverageData(
            class_name="com.example.app.MainActivity",
            method_name="onCreate",
            signature="com.example.app.MainActivity.onCreate(android.os.Bundle)",
            parameters=["android.os.Bundle"],
            reachable=True,
            reaches_mop=True,
            directly_reaches_mop=True
        )

        method2 = MethodCoverageData(
            class_name="com.example.app.MainActivity",
            method_name="onResume",
            signature="com.example.app.MainActivity.onResume()",
            parameters=[],
            reachable=True,
            reaches_mop=False,
            directly_reaches_mop=False
        )

        method3 = MethodCoverageData(
            class_name="com.example.app.MainActivity",
            method_name="privateMethod",
            signature="com.example.app.MainActivity.privateMethod()",
            parameters=[],
            reachable=False,
            reaches_mop=False,
            directly_reaches_mop=False
        )

        return [method1, method2, method3]

    def test_class_coverage_data_initialization(self, sample_class_data):
        """Test ClassCoverageData constructor"""
        assert sample_class_data.name == "com.example.app.MainActivity"
        assert sample_class_data.is_activity is True
        assert sample_class_data.is_main_activity is True
        assert sample_class_data.methods == {}

    def test_add_method(self, sample_class_data, sample_methods):
        """Test add_method method"""
        sample_class_data.add_method(sample_methods[0])

        assert len(sample_class_data.methods) == 1
        assert sample_methods[0].signature in sample_class_data.methods
        assert sample_class_data.methods[sample_methods[0].signature] == sample_methods[0]

    def test_register_method_call(self, sample_class_data, sample_methods):
        """Test register_method_call method"""
        # Add method
        sample_class_data.add_method(sample_methods[0])

        # Register call
        timestamp = datetime.now()
        result = sample_class_data.register_method_call(sample_methods[0].signature, timestamp)

        assert result is True
        assert sample_methods[0].called is True
        assert sample_methods[0].call_count == 1
        assert sample_methods[0].last_called_at == timestamp

        # Try to register call for non-existent method
        result = sample_class_data.register_method_call("non.existent.method", timestamp)
        assert result is False

    def test_called_property(self, sample_class_data, sample_methods):
        """Test called property"""
        # No methods called
        assert sample_class_data.called is False

        # Add method but not called
        sample_class_data.add_method(sample_methods[0])
        assert sample_class_data.called is False

        # Call method
        sample_class_data.register_method_call(sample_methods[0].signature)
        assert sample_class_data.called is True

    def test_method_count_properties(self, sample_class_data, sample_methods):
        """Test method count properties"""
        # Empty class
        assert sample_class_data.method_count == 0
        assert sample_class_data.called_method_count == 0
        assert sample_class_data.reachable_method_count == 0
        assert sample_class_data.called_reachable_method_count == 0
        assert sample_class_data.mop_reaching_method_count == 0
        assert sample_class_data.called_mop_reaching_method_count == 0

        # Add all methods
        for method in sample_methods:
            sample_class_data.add_method(method)

        # Check counts before calling
        assert sample_class_data.method_count == 3
        assert sample_class_data.called_method_count == 0
        assert sample_class_data.reachable_method_count == 2  # method1 and method2
        assert sample_class_data.called_reachable_method_count == 0
        assert sample_class_data.mop_reaching_method_count == 1  # method1
        assert sample_class_data.called_mop_reaching_method_count == 0

        # Call method1 (reachable, reaches_mop)
        sample_class_data.register_method_call(sample_methods[0].signature)

        assert sample_class_data.called_method_count == 1
        assert sample_class_data.called_reachable_method_count == 1
        assert sample_class_data.called_mop_reaching_method_count == 1

        # Call method2 (reachable, not reaches_mop)
        sample_class_data.register_method_call(sample_methods[1].signature)

        assert sample_class_data.called_method_count == 2
        assert sample_class_data.called_reachable_method_count == 2
        assert sample_class_data.called_mop_reaching_method_count == 1  # unchanged

        # Call method3 (not reachable, not reaches_mop)
        sample_class_data.register_method_call(sample_methods[2].signature)

        assert sample_class_data.called_method_count == 3
        assert sample_class_data.called_reachable_method_count == 2  # unchanged
        assert sample_class_data.called_mop_reaching_method_count == 1  # unchanged

    def test_to_dict(self, sample_class_data, sample_methods):
        """Test to_dict method"""
        # Add methods
        for method in sample_methods:
            sample_class_data.add_method(method)

        # Call one method
        sample_class_data.register_method_call(sample_methods[0].signature)

        dict_data = sample_class_data.to_dict()

        assert dict_data["name"] == "com.example.app.MainActivity"
        assert dict_data["is_activity"] is True
        assert dict_data["is_main_activity"] is True
        assert dict_data["method_count"] == 3
        assert dict_data["called_method_count"] == 1
        assert dict_data["reachable_method_count"] == 2
        assert dict_data["called_reachable_method_count"] == 1
        assert dict_data["mop_reaching_method_count"] == 1
        assert dict_data["called_mop_reaching_method_count"] == 1
        assert len(dict_data["methods"]) == 3


class TestCoverageMetrics:
    """Tests for the CoverageMetrics class"""

    @pytest.fixture
    def sample_metrics(self):
        """Create sample coverage metrics for testing"""
        metrics = CoverageMetrics()
        metrics.total_classes = 10
        metrics.total_activities = 5
        metrics.total_methods = 100
        metrics.total_reachable_methods = 80
        metrics.total_mop_methods = 40
        metrics.called_classes = 8
        metrics.called_activities = 4
        metrics.called_methods = 60
        metrics.called_reachable_methods = 50
        metrics.called_mop_methods = 20
        metrics.total_errors = 5
        metrics.unique_errors = 3
        return metrics

    def test_coverage_metrics_initialization(self):
        """Test CoverageMetrics constructor"""
        metrics = CoverageMetrics()

        assert metrics.total_classes == 0
        assert metrics.total_activities == 0
        assert metrics.total_methods == 0
        assert metrics.total_reachable_methods == 0
        assert metrics.total_mop_methods == 0
        assert metrics.called_classes == 0
        assert metrics.called_activities == 0
        assert metrics.called_methods == 0
        assert metrics.called_reachable_methods == 0
        assert metrics.called_mop_methods == 0
        assert metrics.total_errors == 0
        assert metrics.unique_errors == 0

    def test_to_dict(self, sample_metrics):
        """Test to_dict method"""
        dict_data = sample_metrics.to_dict()

        # Check raw counts
        assert dict_data["total_classes"] == 10
        assert dict_data["total_activities"] == 5
        assert dict_data["total_methods"] == 100
        assert dict_data["total_reachable_methods"] == 80
        assert dict_data["total_mop_methods"] == 40
        assert dict_data["called_classes"] == 8
        assert dict_data["called_activities"] == 4
        assert dict_data["called_methods"] == 60
        assert dict_data["called_reachable_methods"] == 50
        assert dict_data["called_mop_methods"] == 20
        assert dict_data["total_errors"] == 5
        assert dict_data["unique_errors"] == 3

        # Check percentages
        assert dict_data["class_coverage"] == 80.0  # 8/10 * 100
        assert dict_data["activity_coverage"] == 80.0  # 4/5 * 100
        assert dict_data["method_coverage"] == 60.0  # 60/100 * 100
        assert dict_data["reachable_method_coverage"] == 62.5  # 50/80 * 100
        assert dict_data["mop_method_coverage"] == 50.0  # 20/40 * 100

    def test_percentage_calculation_with_zero(self):
        """Test percentage calculation with zero denominator"""
        metrics = CoverageMetrics()
        dict_data = metrics.to_dict()

        # All percentages should be 0.0 when denominators are 0
        assert dict_data["class_coverage"] == 0.0
        assert dict_data["activity_coverage"] == 0.0
        assert dict_data["method_coverage"] == 0.0
        assert dict_data["reachable_method_coverage"] == 0.0
        assert dict_data["mop_method_coverage"] == 0.0


class TestLogcatRepository:
    """Tests for the LogcatRepository class"""

    @pytest.fixture
    def sample_repository(self):
        """Create a sample repository for testing"""
        return LogcatRepository()

    @pytest.fixture
    def sample_class_data(self):
        """Create a sample class coverage data for testing"""
        class_data = ClassCoverageData(
            name="com.example.app.MainActivity",
            is_activity=True,
            is_main_activity=True
        )

        # Add methods with different properties
        method1 = MethodCoverageData(
            class_name="com.example.app.MainActivity",
            method_name="onCreate",
            signature="com.example.app.MainActivity.onCreate(android.os.Bundle)",
            parameters=["android.os.Bundle"],
            reachable=True,
            reaches_mop=True,
            directly_reaches_mop=True
        )

        method2 = MethodCoverageData(
            class_name="com.example.app.MainActivity",
            method_name="onResume",
            signature="com.example.app.MainActivity.onResume()",
            parameters=[],
            reachable=True,
            reaches_mop=False,
            directly_reaches_mop=False
        )

        class_data.add_method(method1)
        class_data.add_method(method2)

        return class_data

    @pytest.fixture
    def sample_coverage_log(self):
        """Create a sample coverage log for testing"""
        return RvCoverageLog(
            clazz="com.example.app.MainActivity",
            method="onCreate",
            params="android.os.Bundle",
            signature="com.example.app.MainActivity.onCreate(android.os.Bundle)"
        )

    @pytest.fixture
    def sample_error_log(self):
        """Create a sample error log for testing"""
        return RvErrorLog(
            spec="SecuritySpec",
            error_type="PERMISSION_VIOLATION",
            class_full_name="com.example.app.MainActivity",
            method="accessCamera",
            source="MainActivity.java",
            message="Attempted to access camera without permission"
        )

    def test_repository_initialization(self, sample_repository):
        """Test LogcatRepository constructor"""
        assert sample_repository.classes == {}
        assert sample_repository.errors == []
        assert sample_repository.unique_errors == set()

    def test_add_class_and_get_class(self, sample_repository, sample_class_data):
        """Test add_class and get_class methods"""
        sample_repository.add_class(sample_class_data)

        # Test get_class with existing class
        retrieved_class = sample_repository.get_class("com.example.app.MainActivity")
        assert retrieved_class == sample_class_data

        # Test get_class with non-existent class
        retrieved_class = sample_repository.get_class("com.example.NonExistentClass")
        assert retrieved_class is None

    def test_register_method_call_existing_class(self, sample_repository, sample_class_data, sample_coverage_log):
        """Test register_method_call with existing class"""
        sample_repository.add_class(sample_class_data)
        sample_repository.register_method_call(sample_coverage_log)

        # Verify method was called
        class_data = sample_repository.get_class("com.example.app.MainActivity")
        method_data = class_data.methods["com.example.app.MainActivity.onCreate(android.os.Bundle)"]

        assert method_data.called is True
        assert method_data.call_count == 1

    def test_register_method_call_new_class(self, sample_repository, sample_coverage_log):
        """Test register_method_call with new class"""
        # Repository starts empty
        assert len(sample_repository.classes) == 0

        # Register call for non-existent class
        sample_repository.register_method_call(sample_coverage_log)

        # Verify class and method were created
        assert len(sample_repository.classes) == 1
        assert "com.example.app.MainActivity" in sample_repository.classes

        class_data = sample_repository.get_class("com.example.app.MainActivity")
        assert class_data is not None
        assert len(class_data.methods) == 1
        assert "com.example.app.MainActivity.onCreate(android.os.Bundle)" in class_data.methods

        method_data = class_data.methods["com.example.app.MainActivity.onCreate(android.os.Bundle)"]
        assert method_data.called is True
        assert method_data.call_count == 1

    def test_register_error(self, sample_repository, sample_error_log):
        """Test register_error method"""
        sample_repository.register_error(sample_error_log)

        assert len(sample_repository.errors) == 1
        assert sample_repository.errors[0] == sample_error_log
        assert len(sample_repository.unique_errors) == 1
        assert sample_error_log.unique_msg in sample_repository.unique_errors

        # Register duplicate error (same unique_msg)
        duplicate_error = RvErrorLog(
            spec="SecuritySpec",
            error_type="PERMISSION_VIOLATION",
            class_full_name="com.example.app.MainActivity",
            method="accessCamera",
            source="MainActivity.java",
            message="Attempted to access camera without permission"
        )
        sample_repository.register_error(duplicate_error)

        assert len(sample_repository.errors) == 2  # Both errors are stored
        assert len(sample_repository.unique_errors) == 1  # But unique count remains 1

    def test_calculate_metrics_empty(self, sample_repository):
        """Test calculate_metrics with empty repository"""
        metrics = sample_repository.calculate_metrics()

        assert metrics.total_classes == 0
        assert metrics.total_activities == 0
        assert metrics.total_methods == 0
        assert metrics.total_reachable_methods == 0
        assert metrics.total_mop_methods == 0
        assert metrics.called_classes == 0
        assert metrics.called_activities == 0
        assert metrics.called_methods == 0
        assert metrics.called_reachable_methods == 0
        assert metrics.called_mop_methods == 0
        assert metrics.total_errors == 0
        assert metrics.unique_errors == 0

    def test_calculate_metrics(self, sample_repository, sample_class_data, sample_error_log):
        """Test calculate_metrics with data"""
        # Add class
        sample_repository.add_class(sample_class_data)

        # Add non-activity class
        class_data2 = ClassCoverageData(
            name="com.example.app.Utility",
            is_activity=False,
            is_main_activity=False
        )
        method_utility = MethodCoverageData(
            class_name="com.example.app.Utility",
            method_name="helperMethod",
            signature="com.example.app.Utility.helperMethod()",
            parameters=[],
            reachable=True,
            reaches_mop=False,
            directly_reaches_mop=False
        )
        class_data2.add_method(method_utility)
        sample_repository.add_class(class_data2)

        # Call one method in each class
        sample_repository.classes["com.example.app.MainActivity"].register_method_call(
            "com.example.app.MainActivity.onCreate(android.os.Bundle)")
        sample_repository.classes["com.example.app.Utility"].register_method_call(
            "com.example.app.Utility.helperMethod()")

        # Register an error
        sample_repository.register_error(sample_error_log)

        # Calculate metrics
        metrics = sample_repository.calculate_metrics()

        # Verify metrics
        assert metrics.total_classes == 2
        assert metrics.total_activities == 1
        assert metrics.total_methods == 3  # onCreate, onResume, helperMethod
        assert metrics.total_reachable_methods == 3  # all methods are reachable
        assert metrics.total_mop_methods == 1  # only onCreate reaches_mop
        assert metrics.called_classes == 2  # both classes have called methods
        assert metrics.called_activities == 1
        assert metrics.called_methods == 2  # onCreate and helperMethod
        assert metrics.called_reachable_methods == 2
        assert metrics.called_mop_methods == 1  # onCreate
        assert metrics.total_errors == 1
        assert metrics.unique_errors == 1

    def test_to_dict(self, sample_repository, sample_class_data, sample_error_log):
        """Test to_dict method"""
        # Add class and error
        sample_repository.add_class(sample_class_data)
        sample_repository.register_error(sample_error_log)

        dict_data = sample_repository.to_dict()

        assert "metrics" in dict_data
        assert "classes" in dict_data
        assert "errors" in dict_data
        assert len(dict_data["classes"]) == 1
        assert dict_data["errors"]["count"] == 1
        assert dict_data["errors"]["unique_count"] == 1