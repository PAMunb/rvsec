# tests/model/test_coverage.py
from datetime import datetime

import pytest
from rv_android_core.domain.coverage import (
    ClassCoverageData,
    CoverageMetrics,
    LogcatRepository,
    MethodCoverageData,
)
from rv_android_core.domain.log import RvCoverageLog, RvErrorLog

from .test_framework import ModelTestBase


class TestMethodCoverageData(ModelTestBase):
    """
    Unit tests for the MethodCoverageData class.

    Tests cover initialization, registration of method calls, and property access.
    """

    @pytest.fixture
    def method_data(self):
        """Create a standard method coverage data instance for testing."""
        return MethodCoverageData(
            class_name="com.example.TestClass",
            method_name="testMethod",
            signature="com.example.TestClass.testMethod(Ljava/lang/String;)V",
            parameters=["java.lang.String"],
            reachable=True,
            reaches_target=True,
            directly_reaches_target=False,
        )

    def test_initialization(self, method_data):
        """Test that MethodCoverageData initializes with correct attributes."""
        assert method_data.class_name == "com.example.TestClass"
        assert method_data.method_name == "testMethod"
        assert (
            method_data.signature
            == "com.example.TestClass.testMethod(Ljava/lang/String;)V"
        )
        assert method_data.parameters == ["java.lang.String"]
        assert method_data.reachable is True
        assert method_data.reaches_target is True
        assert method_data.directly_reaches_target is False
        assert method_data.called is False
        assert method_data.call_count == 0
        assert method_data.first_called_at is None
        assert method_data.last_called_at is None
        assert method_data.from_static_analysis is False

    def test_register_call(self, method_data):
        """Test registration of method calls with timestamps."""
        # Test with auto timestamp
        method_data.register_call()
        assert method_data.called is True
        assert method_data.call_count == 1
        assert method_data.first_called_at is not None
        assert method_data.last_called_at is not None
        assert method_data.first_called_at == method_data.last_called_at

        # Store the first timestamp
        first_timestamp = method_data.first_called_at

        # Test with explicit timestamp
        explicit_time = datetime(2023, 1, 1, 12, 0, 0)
        method_data.register_call(explicit_time)
        assert method_data.call_count == 2
        assert method_data.first_called_at == first_timestamp  # Should remain unchanged
        assert method_data.last_called_at == explicit_time

    def test_register_multiple_calls(self, method_data):
        """Test registration of multiple method calls."""
        # Register multiple calls
        call_times = [
            datetime(2023, 1, 1, 12, 0, 0),
            datetime(2023, 1, 1, 12, 5, 0),
            datetime(2023, 1, 1, 12, 10, 0),
        ]

        for time in call_times:
            method_data.register_call(time)

        assert method_data.called is True
        assert method_data.call_count == 3
        assert method_data.first_called_at == call_times[0]
        assert method_data.last_called_at == call_times[-1]


class TestClassCoverageData(ModelTestBase):
    """
    Unit tests for the ClassCoverageData class.

    Tests cover initialization, method management, and property calculations.
    """

    @pytest.fixture
    def class_data(self):
        """Create a standard class coverage data instance for testing."""
        return ClassCoverageData(
            name="com.example.TestClass", component_type="activity", is_main=False
        )

    @pytest.fixture
    def method_data_1(self):
        """Create a method coverage instance for testing."""
        return MethodCoverageData(
            class_name="com.example.TestClass",
            method_name="method1",
            signature="com.example.TestClass.method1()V",
            parameters=[],
            reachable=True,
            reaches_target=True,
        )

    @pytest.fixture
    def method_data_2(self):
        """Create another method coverage instance for testing."""
        return MethodCoverageData(
            class_name="com.example.TestClass",
            method_name="method2",
            signature="com.example.TestClass.method2(Ljava/lang/String;)V",
            parameters=["java.lang.String"],
            reachable=True,
            reaches_target=False,
        )

    def test_initialization(self, class_data):
        """Test that ClassCoverageData initializes with correct attributes."""
        assert class_data.name == "com.example.TestClass"
        assert class_data.component_type == "activity"
        assert class_data.is_main is False
        assert len(class_data.methods) == 0

    def test_add_method(self, class_data, method_data_1, method_data_2):
        """Test adding methods to class coverage data."""
        class_data.add_method(method_data_1)
        assert len(class_data.methods) == 1
        assert method_data_1.signature in class_data.methods

        class_data.add_method(method_data_2)
        assert len(class_data.methods) == 2
        assert method_data_2.signature in class_data.methods

        # Test adding a method with the same signature again (should replace)
        modified_method = MethodCoverageData(
            class_name="com.example.TestClass",
            method_name="method1",
            signature=method_data_1.signature,  # Same signature
            parameters=[],
            reachable=False,  # Different value
            reaches_target=False,  # Different value
        )
        class_data.add_method(modified_method)
        assert len(class_data.methods) == 2  # Count should remain the same
        assert (
            class_data.methods[modified_method.signature].reachable is False
        )  # Should be updated

    def test_register_method_call(self, class_data, method_data_1, method_data_2):
        """Test registering method calls."""
        # Add methods first
        class_data.add_method(method_data_1)
        class_data.add_method(method_data_2)

        # Test successful registration
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        result = class_data.register_method_call(method_data_1.signature, timestamp)
        assert result is True
        assert class_data.methods[method_data_1.signature].called is True
        assert class_data.methods[method_data_1.signature].call_count == 1
        assert class_data.methods[method_data_1.signature].last_called_at == timestamp

        # Test non-existent method
        non_existent_result = class_data.register_method_call(
            "non.existent.method", timestamp
        )
        assert non_existent_result is False

    def test_called_property(self, class_data, method_data_1, method_data_2):
        """Test the called property based on method call status."""
        # When no methods are called
        class_data.add_method(method_data_1)
        class_data.add_method(method_data_2)
        assert class_data.called is False

        # When one method is called
        class_data.register_method_call(method_data_1.signature)
        assert class_data.called is True

        # Create new class with no methods
        empty_class = ClassCoverageData("com.example.EmptyClass")
        assert empty_class.called is False

    def test_method_count_properties(self, class_data, method_data_1, method_data_2):
        """Test the method count properties."""
        # Add methods
        class_data.add_method(method_data_1)
        class_data.add_method(method_data_2)

        # Initial counts
        assert class_data.method_count == 2
        assert class_data.called_method_count == 0
        assert class_data.reachable_method_count == 2  # Both are reachable
        assert class_data.called_reachable_method_count == 0
        assert class_data.mop_reaching_method_count == 1  # Only method1 reaches MOP
        assert class_data.called_mop_reaching_method_count == 0

        # After calling method1
        class_data.register_method_call(method_data_1.signature)
        assert class_data.called_method_count == 1
        assert class_data.called_reachable_method_count == 1
        assert class_data.called_mop_reaching_method_count == 1

        # After calling method2
        class_data.register_method_call(method_data_2.signature)
        assert class_data.called_method_count == 2
        assert class_data.called_reachable_method_count == 2
        assert (
            class_data.called_mop_reaching_method_count == 1
        )  # Still 1 since method2 doesn't reach MOP


class TestCoverageMetrics(ModelTestBase):
    """
    Unit tests for the CoverageMetrics class.

    Tests cover metrics calculation and dictionary conversion.
    """

    @pytest.fixture
    def empty_metrics(self):
        """Create empty coverage metrics for testing."""
        return CoverageMetrics()

    @pytest.fixture
    def populated_metrics(self):
        """Create populated coverage metrics for testing."""
        metrics = CoverageMetrics()
        metrics.total_classes = 10
        metrics.total_activities = 5
        metrics.total_methods = 100
        metrics.total_reachable_methods = 80
        metrics.total_target_methods = 50

        metrics.called_classes = 8
        metrics.called_activities = 4
        metrics.called_methods = 70
        metrics.called_reachable_methods = 60
        metrics.called_target_methods = 30

        metrics.total_errors = 5
        metrics.unique_errors = 3
        return metrics

    def test_initialization(self, empty_metrics):
        """Test that CoverageMetrics initializes with zero values."""
        assert empty_metrics.total_classes == 0
        assert empty_metrics.total_activities == 0
        assert empty_metrics.total_methods == 0
        assert empty_metrics.total_reachable_methods == 0
        assert empty_metrics.total_target_methods == 0

        assert empty_metrics.called_classes == 0
        assert empty_metrics.called_activities == 0
        assert empty_metrics.called_methods == 0
        assert empty_metrics.called_reachable_methods == 0
        assert empty_metrics.called_target_methods == 0

        assert empty_metrics.total_errors == 0
        assert empty_metrics.unique_errors == 0

    def test_percentage_calculation(self):
        """Test the _percentage static method."""
        # Test normal case
        assert CoverageMetrics._percentage(50, 100) == 50.0

        # Test zero denominator
        assert CoverageMetrics._percentage(10, 0) == 0.0

        # Test zero numerator
        assert CoverageMetrics._percentage(0, 100) == 0.0

        # Test both zero
        assert CoverageMetrics._percentage(0, 0) == 0.0

    def test_to_dict(self, populated_metrics):
        """Test conversion to dictionary with calculated percentages."""
        result = populated_metrics.to_dict()

        # Check raw counts
        assert result["total_classes"] == 10
        assert result["total_methods"] == 100
        assert result["called_methods"] == 70
        assert result["unique_errors"] == 3

        # Check calculated percentages
        assert result["class_coverage"] == 80.0  # 8/10 * 100
        assert result["activity_coverage"] == 80.0  # 4/5 * 100
        assert result["method_coverage"] == 70.0  # 70/100 * 100
        assert result["reachable_method_coverage"] == 75.0  # 60/80 * 100
        assert result["mop_method_coverage"] == 60.0  # 30/50 * 100

    def test_to_dict_with_zeros(self, empty_metrics):
        """Test to_dict() with all zeros to ensure no division by zero errors."""
        result = empty_metrics.to_dict()

        # All percentages should be 0.0
        assert result["class_coverage"] == 0.0
        assert result["activity_coverage"] == 0.0
        assert result["method_coverage"] == 0.0
        assert result["reachable_method_coverage"] == 0.0
        assert result["mop_method_coverage"] == 0.0


class TestLogcatRepository(ModelTestBase):
    """
    Unit tests for the LogcatRepository class.

    Tests cover class and method registration, coverage tracking, and metrics calculation.
    """

    @pytest.fixture
    def repository(self):
        """Create a standard LogcatRepository instance for testing."""
        return LogcatRepository()

    @pytest.fixture
    def class_data(self):
        """Create a class coverage data instance for testing."""
        return ClassCoverageData(
            name="com.example.TestClass", component_type="activity", is_main=False
        )

    @pytest.fixture
    def method_data(self):
        """Create a method coverage instance for testing."""
        return MethodCoverageData(
            class_name="com.example.TestClass",
            method_name="testMethod",
            signature="com.example.TestClass.testMethod()V",
            parameters=[],
            reachable=True,
            reaches_target=True,
            from_static_analysis=True,
        )

    @pytest.fixture
    def coverage_log(self):
        """Create an RvCoverageLog instance for testing."""
        return RvCoverageLog(
            clazz="com.example.TestClass",
            method="testMethod",
            params="",
            signature="com.example.TestClass.testMethod()V",
        )

    @pytest.fixture
    def error_log(self):
        """Create an RvErrorLog instance for testing."""
        return RvErrorLog(
            spec="TestSpec",
            error_type="TestError",
            class_full_name="com.example.TestClass",
            method="testMethod",
            source="TestSource",
            message="Test error message",
        )

    def test_initialization(self, repository):
        """Test that LogcatRepository initializes with empty collections."""
        assert len(repository.classes) == 0
        assert len(repository.errors) == 0
        assert len(repository.unique_errors) == 0
        assert repository._static_totals is None

    def test_add_class(self, repository, class_data, method_data):
        """Test adding a class to the repository."""
        # Add method to class
        class_data.add_method(method_data)

        # Add class to repository
        repository.add_class(class_data)

        # Verify class was added
        assert "com.example.TestClass" in repository.classes
        assert len(repository.classes) == 1

        # Verify method was added with static analysis flag
        retrieved_class = repository.classes["com.example.TestClass"]
        assert method_data.signature in retrieved_class.methods
        assert (
            retrieved_class.methods[method_data.signature].from_static_analysis is True
        )

        # Verify static totals were reset
        assert repository._static_totals is None

        # Try adding the same class again
        class_data_duplicate = ClassCoverageData(
            name="com.example.TestClass",
            component_type=None,  # Different value
            is_main=True,  # Different value
        )
        repository.add_class(class_data_duplicate)

        # Should still only have one class, and values shouldn't change
        assert len(repository.classes) == 1
        assert repository.classes["com.example.TestClass"].component_type == "activity"
        assert repository.classes["com.example.TestClass"].is_main is False

    def test_get_class(self, repository, class_data):
        """Test retrieving a class from the repository."""
        # Add class
        repository.add_class(class_data)

        # Test successful retrieval
        retrieved = repository.get_class("com.example.TestClass")
        assert retrieved is not None
        assert retrieved.name == "com.example.TestClass"

        # Test non-existent class
        assert repository.get_class("non.existent.Class") is None

    def test_register_method_call(
        self, repository, class_data, method_data, coverage_log
    ):
        """Test registering a method call."""
        # Add class with method to repository
        class_data.add_method(method_data)
        repository.add_class(class_data)

        # Register a method call
        repository.register_method_call(coverage_log)

        # Verify method was marked as called
        retrieved_class = repository.get_class("com.example.TestClass")
        assert retrieved_class.methods[method_data.signature].called is True
        assert retrieved_class.methods[method_data.signature].call_count == 1

        # Test non-existent class
        non_existent_log = RvCoverageLog(
            clazz="non.existent.Class",
            method="method",
            params="",
            signature="non.existent.Class.method()V",
        )
        repository.register_method_call(non_existent_log)
        # Should not raise exception, just log debug message

        # Test non-existent method in existing class
        non_existent_method_log = RvCoverageLog(
            clazz="com.example.TestClass",
            method="nonExistentMethod",
            params="",
            signature="com.example.TestClass.nonExistentMethod()V",
        )
        repository.register_method_call(non_existent_method_log)
        # Should not add the method since it's not in static analysis
        assert (
            "com.example.TestClass.nonExistentMethod()V" not in retrieved_class.methods
        )

    def test_register_rv_error(self, repository, error_log):
        """Test registering a runtime verification error."""
        # Register an error
        repository.register_rv_error(error_log)

        # Verify error was added
        assert len(repository.errors) == 1
        assert repository.errors[0] == error_log
        assert len(repository.unique_errors) == 1
        assert error_log.unique_msg in repository.unique_errors

        # Register the same error again
        repository.register_rv_error(error_log)

        # Should have two errors but only one unique
        assert len(repository.errors) == 2
        assert len(repository.unique_errors) == 1

        # Register a different error
        different_error = RvErrorLog(
            spec="TestSpec",
            error_type="TestError",
            class_full_name="com.example.TestClass",
            method="differentMethod",  # Different method
            source="TestSource",
            message="Test error message",
        )
        repository.register_rv_error(different_error)

        # Should have three errors and two unique
        assert len(repository.errors) == 3
        assert len(repository.unique_errors) == 2

    def test_get_static_method_count(self, repository, class_data, method_data):
        """Test getting the count of methods from static analysis."""
        # Initially, should be 0
        assert repository.get_static_method_count() == 0

        # Add class with method
        class_data.add_method(method_data)
        repository.add_class(class_data)

        # Force recalculation of static totals
        repository._static_totals = None
        repository._calculate_static_totals()

        # Now should return 1
        current_count = repository.get_static_method_count()
        assert current_count == 1, f"Expected 1 method, got {current_count}"

        # Create and add a new method to a new class instance
        # (instead of modifying the existing one)
        new_class = ClassCoverageData(
            name="com.example.TestClass", component_type="activity", is_main=False
        )

        # Add the original method
        new_class.add_method(method_data)

        # Add the second method
        second_method = MethodCoverageData(
            class_name="com.example.TestClass",
            method_name="anotherMethod",
            signature="com.example.TestClass.anotherMethod()V",
            parameters=[],
            reachable=True,
            reaches_target=False,
            from_static_analysis=True,
        )
        new_class.add_method(second_method)

        # Replace the class in the repository
        repository.classes = {new_class.name: new_class}

        # Force recalculation of static totals
        repository._static_totals = None
        repository._calculate_static_totals()

        # Should now return 2
        final_count = repository.get_static_method_count()
        assert final_count == 2, f"Expected 2 methods, got {final_count}"

    def test_calculate_metrics_no_data(self, repository):
        """Test calculating metrics with no data."""
        metrics = repository.calculate_metrics()

        # All counts should be 0
        assert metrics.total_classes == 0
        assert metrics.total_methods == 0
        assert metrics.called_methods == 0
        assert metrics.total_errors == 0

        # All percentages in dict should be 0.0
        metrics_dict = metrics.to_dict()
        assert metrics_dict["method_coverage"] == 0.0
        assert metrics_dict["activity_coverage"] == 0.0
        assert metrics_dict["mop_method_coverage"] == 0.0

    def test_calculate_metrics(
        self, repository, class_data, method_data, coverage_log, error_log
    ):
        """Test calculating metrics with data."""
        # Add class with method
        class_data.add_method(method_data)
        repository.add_class(class_data)

        # Register a method call and an error
        repository.register_method_call(coverage_log)
        repository.register_rv_error(error_log)

        # Calculate metrics
        metrics = repository.calculate_metrics()

        # Verify counts
        assert metrics.total_classes == 1
        assert metrics.total_activities == 1
        assert metrics.total_methods == 1
        assert metrics.total_reachable_methods == 1
        assert metrics.total_target_methods == 1

        assert metrics.called_classes == 1
        assert metrics.called_activities == 1
        assert metrics.called_methods == 1
        assert metrics.called_reachable_methods == 1
        assert metrics.called_target_methods == 1

        assert metrics.total_errors == 1
        assert metrics.unique_errors == 1

        # Verify percentages in dict
        metrics_dict = metrics.to_dict()
        assert metrics_dict["class_coverage"] == 100.0
        assert metrics_dict["activity_coverage"] == 100.0
        assert metrics_dict["method_coverage"] == 100.0
        assert metrics_dict["reachable_method_coverage"] == 100.0
        assert metrics_dict["mop_method_coverage"] == 100.0

    def test_diagnose(
        self, repository, class_data, method_data, coverage_log, error_log
    ):
        """Test the diagnose method."""
        # Empty repository
        empty_diagnostics = repository.diagnose()
        assert empty_diagnostics["class_count"] == 0
        assert empty_diagnostics["activity_count"] == 0
        assert empty_diagnostics["method_count"] == 0
        assert "No methods found in repository" in empty_diagnostics["issues"]

        # Add data
        class_data.add_method(method_data)
        repository.add_class(class_data)
        repository.register_method_call(coverage_log)
        repository.register_rv_error(error_log)

        # Force calculation of static totals before diagnosis
        repository._calculate_static_totals()

        # Get diagnostics
        diagnostics = repository.diagnose()
        assert diagnostics["class_count"] == 1
        assert diagnostics["activity_count"] == 1
        assert diagnostics["method_count"] == 1
        assert diagnostics["called_method_count"] == 1
        assert diagnostics["error_count"] == 1
        assert diagnostics["unique_error_count"] == 1
        assert diagnostics["static_totals"] is not None
        assert len(diagnostics["issues"]) == 0  # No issues expected
