# tests/model/test_coverage.py
from datetime import datetime

import pytest
from rv_android_core.domain.coverage import (
    ClassCoverageData,
    CoverageMetrics,
    LogcatRepository,
    MethodCoverageData,
)
from rv_android_core.domain.log import RvCoverageLog, RvDiagnosticEvent, RvErrorLog

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

    def test_to_dict_with_timestamps(self, method_data):
        """to_dict() emits ISO strings for both datetimes once the method is called.

        Basis-path: exercises the truthy branch of both `if self.first_called_at`
        and `if self.last_called_at` in to_dict() (lines 146-152).
        """
        call_time = datetime(2023, 5, 4, 10, 30, 0)
        method_data.register_call(call_time, time_since_task_start=7)

        result = method_data.to_dict()

        # Static/dynamic scalar fields
        assert result["class_name"] == "com.example.TestClass"
        assert result["method_name"] == "testMethod"
        assert result["signature"] == (
            "com.example.TestClass.testMethod(Ljava/lang/String;)V"
        )
        assert result["parameters"] == ["java.lang.String"]
        assert result["reachable"] is True
        assert result["reaches_target"] is True
        assert result["directly_reaches_target"] is False
        assert result["called"] is True
        assert result["call_count"] == 1
        # Both timestamps present as ISO strings
        assert result["first_called_at"] == call_time.isoformat()
        assert result["last_called_at"] == call_time.isoformat()

    def test_to_dict_without_timestamps(self, method_data):
        """to_dict() yields None for both datetimes on a never-called method.

        Basis-path: exercises the falsy (else) branch of both datetime guards in
        to_dict() (lines 148-149, 153-154).
        """
        result = method_data.to_dict()

        assert result["called"] is False
        assert result["call_count"] == 0
        assert result["first_called_at"] is None
        assert result["last_called_at"] is None

    def test_from_coverage_log(self):
        """from_coverage_log() builds a called instance mirroring the log entry.

        Traceability: the classmethod is the bridge from a raw RvCoverageLog to a
        MethodCoverageData, registering the first call and preserving timing.
        """
        log = RvCoverageLog(
            clazz="com.example.Foo",
            method="bar",
            params="java.lang.String;int",
            signature="com.example.Foo.bar(Ljava/lang/String;I)V",
            original_msg="RVSEC-COV raw line",
            time_occurred=datetime(2023, 6, 1, 9, 0, 0),
            time_since_task_start=12,
        )

        instance = MethodCoverageData.from_coverage_log(log)

        assert instance.class_name == log.clazz
        assert instance.method_name == log.method
        assert instance.signature == log.signature
        assert instance.parameters == log.get_parameters_list()
        # register_call runs inside the classmethod
        assert instance.called is True
        assert instance.call_count == 1
        assert instance.time_since_task_start == log.time_since_task_start


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

    def test_to_dict(self, class_data, method_data_1, method_data_2):
        """to_dict() aggregates class metadata, per-metric counts, and methods list.

        Covers ClassCoverageData.to_dict() (line 309): asserts identity fields,
        every count property, and that `methods` is a serialized list.
        """
        class_data.add_method(method_data_1)
        class_data.add_method(method_data_2)
        class_data.register_method_call(method_data_1.signature)

        result = class_data.to_dict()

        assert result["name"] == "com.example.TestClass"
        assert result["component_type"] == "activity"
        assert result["is_main"] is False
        assert result["method_count"] == 2
        assert result["called_method_count"] == 1
        assert result["reachable_method_count"] == 2
        assert result["called_reachable_method_count"] == 1
        assert result["mop_reaching_method_count"] == 1
        assert result["called_mop_reaching_method_count"] == 1
        assert isinstance(result["methods"], list)
        assert len(result["methods"]) == 2
        # Each entry is a method dict (from MethodCoverageData.to_dict())
        assert {m["signature"] for m in result["methods"]} == {
            method_data_1.signature,
            method_data_2.signature,
        }


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

    def test_metrics_empty_classes_counts_errors(self, repository):
        """Error aggregates survive the empty-classes early return (D-2, INV-ANA-25).

        Analysis scenario "Metrics Over Empty Classes Still Count Errors": a
        repository with no static-analysis data but K registered violations (J
        distinct) MUST report total_errors==K and unique_errors==J via to_dict(),
        while every coverage percentage stays 0.
        """
        # K = 3 violations, J = 2 distinct unique_msg (two share spec/method/message)
        repeated = RvErrorLog(
            spec="SpecA",
            error_type="TypeA",
            class_full_name="com.example.A",
            method="m1",
            source="src",
            message="boom",
        )
        repository.register_rv_error(repeated)
        repository.register_rv_error(repeated)  # same unique_msg
        repository.register_rv_error(
            RvErrorLog(
                spec="SpecB",
                error_type="TypeB",
                class_full_name="com.example.B",
                method="m2",
                source="src",
                message="bang",
            )
        )

        # No classes added — static analysis absent.
        assert len(repository.classes) == 0

        metrics_dict = repository.calculate_metrics().to_dict()

        assert metrics_dict["total_errors"] == 3
        assert metrics_dict["unique_errors"] == 2
        assert metrics_dict["method_coverage"] == 0
        assert metrics_dict["class_coverage"] == 0
        assert metrics_dict["reachable_method_coverage"] == 0
        assert metrics_dict["mop_method_coverage"] == 0
        assert metrics_dict["direct_mop_method_coverage"] == 0
        assert metrics_dict["activity_coverage"] == 0

    def test_error_count_matches_get_errors_logcat_only(self, repository):
        """total_errors == get_errors() after a logcat-only reconstruction (D-2).

        Analysis scenario "Error Count Matches get_errors After Logcat-Only
        Reconstruction": when a repository is reconstructed from a logcat without
        static data, its `classes` dict is empty (so coverage is zeroed) but each
        RVSEC violation line is registered. The metrics aggregate consumed by the
        summary writer MUST match get_errors() exactly. Reproduced here at the
        domain layer (no static data, N errors registered directly — the same
        state parse_logcat_file(..., static_data=None) leaves).
        """
        n = 4
        for i in range(n):
            repository.register_rv_error(
                RvErrorLog(
                    spec="Spec",
                    error_type="Type",
                    class_full_name="com.example.C",
                    method=f"m{i}",
                    source="src",
                    message=f"violation {i}",
                )
            )

        assert len(repository.classes) == 0
        assert len(repository.get_errors()) == n
        assert repository.calculate_metrics().to_dict()["total_errors"] == n
        assert repository.calculate_metrics().to_dict()["total_errors"] == len(
            repository.get_errors()
        )

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

    @pytest.fixture
    def diagnostic_event(self):
        """Create a minimal valid RvDiagnosticEvent instance for testing."""
        return RvDiagnosticEvent(
            category="crash",
            class_full_name="java.lang.NullPointerException",
            method="onCreate",
            message="FATAL EXCEPTION: main",
            source="MainActivity.java:42",
            process="com.example.app",
            pid="1234",
            tid="1234",
            fatal=True,
            stack_head="at com.example.MainActivity.onCreate(MainActivity.java:42)",
            n_frames=5,
            original_msg="FATAL EXCEPTION: main\n\tat ...",
            time_occurred=datetime(2023, 7, 1, 8, 0, 0),
            time_since_task_start=3,
        )

    def test_register_diagnostic_event(self, repository, diagnostic_event):
        """register_diagnostic_event() appends to the isolated diagnostic collection.

        Covers line 589. Diagnostic events are kept separate from coverage/errors
        (INV-CORE-39); this only asserts the append side effect.
        """
        repository.register_diagnostic_event(diagnostic_event)

        assert len(repository.diagnostic_events) == 1
        assert repository.diagnostic_events[0] is diagnostic_event

    def test_get_diagnostic_events_sorted(self, repository):
        """get_diagnostic_events() returns dicts sorted ascending by task time.

        Covers lines 598-599. Registers two events out of chronological order and
        asserts the returned list is dict-serialized and time-sorted.
        """
        later = RvDiagnosticEvent(
            category="crash",
            class_full_name="java.lang.IllegalStateException",
            method="onResume",
            message="FATAL EXCEPTION: main",
            time_since_task_start=20,
        )
        earlier = RvDiagnosticEvent(
            category="verify_error",
            class_full_name="com.example.Rejected",
            method="",
            message="Rejecting class",
            time_since_task_start=5,
        )
        # Register out of order to prove sorting happens on read.
        repository.register_diagnostic_event(later)
        repository.register_diagnostic_event(earlier)

        result = repository.get_diagnostic_events()

        assert len(result) == 2
        assert all(isinstance(d, dict) for d in result)
        assert [d["time_since_task_start"] for d in result] == [5, 20]

    def test_calculate_metrics_static_totals_unavailable(
        self, repository, class_data, method_data
    ):
        """Defensive else path when static totals are empty/unavailable.

        Covers lines 656-658: with at least one class present (so the empty-classes
        early return at 631 is skipped) but `_static_totals` forced to an empty dict
        ({} is falsy yet not None, so line 638 does NOT recompute and line 642's
        `if self._static_totals:` is False), calculate_metrics() must fall through to
        the defensive "static totals unavailable" branch without crashing. Total
        counts stay 0 because the totals dict was emptied.
        """
        class_data.add_method(method_data)
        repository.add_class(class_data)

        # Force the falsy-but-not-None state that triggers the defensive else.
        repository._static_totals = {}

        metrics = repository.calculate_metrics()

        assert isinstance(metrics, CoverageMetrics)
        assert metrics.total_methods == 0
        assert metrics.total_classes == 0

    def test_calculate_metrics_direct_target_called(self, repository):
        """called_direct_target_methods increments for a called direct-MOP method.

        Covers line 677 (and, as a side effect, line 777's
        total_direct_target_methods increment inside _calculate_static_totals).
        """
        cls = ClassCoverageData(
            name="com.example.DirectClass", component_type="activity"
        )
        direct_method = MethodCoverageData(
            class_name="com.example.DirectClass",
            method_name="doCrypto",
            signature="com.example.DirectClass.doCrypto()V",
            parameters=[],
            reachable=True,
            reaches_target=True,
            directly_reaches_target=True,
        )
        cls.add_method(direct_method)
        cls.register_method_call(direct_method.signature)
        repository.add_class(cls)

        metrics = repository.calculate_metrics()

        assert metrics.called_direct_target_methods == 1
        # Static side effect: _calculate_static_totals counted the direct method.
        assert metrics.total_direct_target_methods == 1

    def test_calculate_coverage_metrics(
        self, repository, class_data, method_data, coverage_log
    ):
        """calculate_coverage_metrics() returns the standardized percentage dict.

        Covers lines 698-714. A repo with one called method yields 100% class and
        method coverage plus the full standardized key set.
        """
        class_data.add_method(method_data)
        repository.add_class(class_data)
        repository.register_method_call(coverage_log)

        result = repository.calculate_coverage_metrics()

        assert result["total_classes"] == 1
        assert result["covered_classes"] == 1
        assert result["class_coverage_percentage"] == 100.0
        assert result["total_methods"] == 1
        assert result["covered_methods"] == 1
        assert result["method_coverage_percentage"] == 100.0
        # Standardized keys expected by downstream consumers
        assert "mop_method_coverage_percentage" in result
        assert "total_errors" in result
        assert "timestamp" in result

    def test_diagnose_static_totals_zero_methods(self, repository):
        """diagnose() flags static totals that report zero methods.

        Covers line 815: a class WITH NO methods makes _calculate_static_totals
        produce total_methods == 0 (not None), tripping the `elif` branch.
        """
        repository.add_class(ClassCoverageData(name="com.example.Empty"))
        # Force _static_totals to a non-None dict whose total_methods is 0.
        repository.get_static_method_count()

        diagnostics = repository.diagnose()

        assert "Static totals shows zero methods" in diagnostics["issues"]

    def test_to_dict(self, repository, class_data, method_data, error_log):
        """to_dict() serializes metrics, classes, and error aggregates.

        Covers lines 827-829: asserts the top-level keys and that the error count
        matches the number of registered violations.
        """
        class_data.add_method(method_data)
        repository.add_class(class_data)
        repository.register_rv_error(error_log)

        result = repository.to_dict()

        assert "metrics" in result
        assert "classes" in result
        assert "errors" in result
        assert "com.example.TestClass" in result["classes"]
        assert result["errors"]["count"] == 1
        assert result["errors"]["unique_count"] == 1

    def test_get_method_calls(self, repository):
        """get_method_calls() returns one time-sorted entry per called method.

        Covers lines 855-889. Two called methods with distinct task times must come
        back sorted ascending by "time", each carrying the full CSV-row key set. The
        class is an activity, so the "activity" key equals the class name.
        """
        cls = ClassCoverageData(
            name="com.example.ActivityClass", component_type="activity"
        )
        early_method = MethodCoverageData(
            class_name="com.example.ActivityClass",
            method_name="first",
            signature="com.example.ActivityClass.first()V",
            parameters=[],
            reaches_target=True,
        )
        late_method = MethodCoverageData(
            class_name="com.example.ActivityClass",
            method_name="second",
            signature="com.example.ActivityClass.second()V",
            parameters=[],
            reaches_target=False,
        )
        cls.add_method(early_method)
        cls.add_method(late_method)
        # Register with explicit, out-of-order task times to prove sorting.
        cls.register_method_call(
            late_method.signature,
            datetime(2023, 8, 1, 10, 0, 0),
            time_since_task_start=30,
        )
        cls.register_method_call(
            early_method.signature,
            datetime(2023, 8, 1, 10, 0, 0),
            time_since_task_start=5,
        )
        repository.add_class(cls)

        calls = repository.get_method_calls()

        assert len(calls) == 2
        # Sorted ascending by task time.
        assert [c["time"] for c in calls] == [5, 30]
        first = calls[0]
        for key in (
            "time",
            "class_name",
            "method_name",
            "signature",
            "is_mop_method",
            "activity",
            "call_count",
            "first_called_at",
            "last_called_at",
        ):
            assert key in first
        # Activity branch: component_type == "activity" -> activity == class name.
        assert first["activity"] == "com.example.ActivityClass"
        assert first["method_name"] == "first"
        assert first["is_mop_method"] is True

    def test_get_static_methods(self, repository, class_data, method_data):
        """get_static_methods() returns all method signatures across classes.

        Covers lines 913-916.
        """
        class_data.add_method(method_data)
        repository.add_class(class_data)

        signatures = repository.get_static_methods()

        assert signatures == [method_data.signature]

    def test_get_static_activities(self, repository):
        """get_static_activities() returns only activity-typed class names.

        Covers line 925: with one activity and one non-activity class, only the
        activity name is returned.
        """
        activity = ClassCoverageData(
            name="com.example.MyActivity", component_type="activity"
        )
        service = ClassCoverageData(
            name="com.example.MyService", component_type="service"
        )
        repository.add_class(activity)
        repository.add_class(service)

        activities = repository.get_static_activities()

        assert activities == ["com.example.MyActivity"]

    def test_get_target_methods(self, repository):
        """get_target_methods() returns only signatures that reach MOP operations.

        Covers lines 938-943: equivalence partitioning on `reaches_target` -
        exactly the True-partition signature is returned.
        """
        cls = ClassCoverageData(name="com.example.TargetClass")
        mop_method = MethodCoverageData(
            class_name="com.example.TargetClass",
            method_name="reaches",
            signature="com.example.TargetClass.reaches()V",
            parameters=[],
            reaches_target=True,
        )
        non_mop_method = MethodCoverageData(
            class_name="com.example.TargetClass",
            method_name="plain",
            signature="com.example.TargetClass.plain()V",
            parameters=[],
            reaches_target=False,
        )
        cls.add_method(mop_method)
        cls.add_method(non_mop_method)
        repository.add_class(cls)

        targets = repository.get_target_methods()

        assert targets == [mop_method.signature]
