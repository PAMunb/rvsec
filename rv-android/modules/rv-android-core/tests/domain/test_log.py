from datetime import datetime
from unittest.mock import patch

import pytest
from rv_android_core.domain.log import RvErrorLog, RvCoverageLog, TAG_RVSEC, TAG_RVSEC_COV


class TestRvErrorLog:
    """Tests for the RvErrorLog class"""

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

    def test_error_log_initialization(self, sample_error_log):
        """Test RvErrorLog constructor"""
        assert sample_error_log.spec == "SecuritySpec"
        assert sample_error_log.error_type == "PERMISSION_VIOLATION"
        assert sample_error_log.class_full_name == "com.example.app.MainActivity"
        assert sample_error_log.method == "accessCamera"
        assert sample_error_log.source == "MainActivity.java"
        assert sample_error_log.message == "Attempted to access camera without permission"

        # Check auto-generated fields
        assert isinstance(sample_error_log.time_occurred, datetime)
        assert sample_error_log.time_since_task_start == 0
        assert sample_error_log.original_msg == ""
        assert "PERMISSION_VIOLATION" in sample_error_log.unique_msg
        assert "com.example.app.MainActivity" in sample_error_log.unique_msg
        assert "accessCamera" in sample_error_log.unique_msg

    def test_from_dict(self):
        """Test from_dict method"""
        data = {
            "spec": "SecuritySpec",
            "error_type": "PERMISSION_VIOLATION",
            "class_full_name": "com.example.app.MainActivity",
            "method": "accessCamera",
            "source": "MainActivity.java",
            "message": "Attempted to access camera without permission",
            "time_occurred": 1617234567890,  # Example timestamp in milliseconds
            "time_since_task_start": 30
        }

        error_log = RvErrorLog.from_dict(data)

        assert error_log.spec == "SecuritySpec"
        assert error_log.error_type == "PERMISSION_VIOLATION"
        assert error_log.class_full_name == "com.example.app.MainActivity"
        assert error_log.method == "accessCamera"
        assert error_log.source == "MainActivity.java"
        assert error_log.message == "Attempted to access camera without permission"
        assert isinstance(error_log.time_occurred, datetime)
        assert error_log.time_since_task_start == 30

    def test_from_dict_no_timestamp(self):
        """Test from_dict method without timestamp"""
        data = {
            "spec": "SecuritySpec",
            "error_type": "PERMISSION_VIOLATION",
            "class_full_name": "com.example.app.MainActivity",
            "method": "accessCamera",
            "source": "MainActivity.java",
            "message": "Attempted to access camera without permission"
        }

        error_log = RvErrorLog.from_dict(data)

        assert error_log.spec == "SecuritySpec"
        assert error_log.error_type == "PERMISSION_VIOLATION"
        assert isinstance(error_log.time_occurred, datetime)

    def test_string_representation(self, sample_error_log):
        """Test __str__ method"""
        string_repr = str(sample_error_log)

        assert "RvErrorLog" in string_repr
        assert "spec=SecuritySpec" in string_repr
        assert "type=PERMISSION_VIOLATION" in string_repr
        assert "method=accessCamera" in string_repr

    def test_repr(self, sample_error_log):
        """Test __repr__ method"""
        repr_str = repr(sample_error_log)

        assert sample_error_log.unique_msg in repr_str
        assert ":" in repr_str  # Should include timestamp

    def test_hash(self, sample_error_log):
        """Test __hash__ method"""
        assert hash(sample_error_log) == hash(sample_error_log.unique_msg)

    def test_equality(self, sample_error_log):
        """Test equality comparison"""
        # Same error
        error2 = RvErrorLog(
            spec="SecuritySpec",
            error_type="PERMISSION_VIOLATION",
            class_full_name="com.example.app.MainActivity",
            method="accessCamera",
            source="MainActivity.java",
            message="Attempted to access camera without permission"
        )
        assert sample_error_log == error2

        # Different error
        error3 = RvErrorLog(
            spec="SecuritySpec",
            error_type="DIFFERENT_ERROR",
            class_full_name="com.example.app.MainActivity",
            method="accessCamera",
            source="MainActivity.java",
            message="Different message"
        )
        assert sample_error_log != error3

        # Different type
        assert sample_error_log != "not an error"


class TestRvCoverageLog:
    """Tests for the RvCoverageLog class"""

    @pytest.fixture
    def sample_coverage_log(self):
        """Create a sample coverage log for testing"""
        return RvCoverageLog(
            clazz="com.example.app.MainActivity",
            method="onCreate",
            params="android.os.Bundle",
            signature="com.example.app.MainActivity.onCreate(android.os.Bundle)"
        )

    def test_coverage_log_initialization(self, sample_coverage_log):
        """Test RvCoverageLog constructor"""
        assert sample_coverage_log.clazz == "com.example.app.MainActivity"
        assert sample_coverage_log.method == "onCreate"
        assert sample_coverage_log.params == "android.os.Bundle"
        assert sample_coverage_log.signature == "com.example.app.MainActivity.onCreate(android.os.Bundle)"

        # Check auto-generated fields
        assert isinstance(sample_coverage_log.time_occurred, datetime)
        assert sample_coverage_log.time_since_task_start == 0
        assert sample_coverage_log.original_msg == ""

    def test_to_dict(self, sample_error_log):
        """Test to_dict method"""
        # Mock utils.datetime_to_milliseconds para um comportamento conhecido
        with patch('rv_android_core.domain.log.utils.datetime_to_milliseconds', return_value=123456789):
            dic = sample_error_log.to_dict()

            assert dic["spec"] == "SecuritySpec"
            assert dic["error_type"] == "PERMISSION_VIOLATION"
            assert dic["class_full_name"] == "com.example.app.MainActivity"
            assert dic["method"] == "accessCamera"
            assert dic["message"] == "Attempted to access camera without permission"
            assert dic["time_occurred"] == 123456789
            assert dic["time_since_task_start"] == 0
            assert "unique_msg" in dic

    def test_to_dict(self, sample_coverage_log):
        """Test to_dict method"""
        # Mock utils.datetime_to_milliseconds para um comportamento conhecido
        with patch('rv_android_core.domain.log.utils.datetime_to_milliseconds', return_value=123456789):
            dic = sample_coverage_log.to_dict()

            assert dic["class"] == "com.example.app.MainActivity"
            assert dic["method"] == "onCreate"
            assert dic["params"] == "android.os.Bundle"
            assert dic["signature"] == "com.example.app.MainActivity.onCreate(android.os.Bundle)"
            assert dic["time_occurred"] == 123456789
            assert dic["time_since_task_start"] == 0
            assert dic["original_msg"] == ""

    def test_from_dict(self):
        """Test from_dict method"""
        data = {
            "class": "com.example.app.MainActivity",
            "method": "onCreate",
            "params": "android.os.Bundle",
            "signature": "com.example.app.MainActivity.onCreate(android.os.Bundle)",
            "time_occurred": 1617234567890,  # Example timestamp in milliseconds
            "time_since_task_start": 30,
            "original_msg": "Log message"
        }

        coverage_log = RvCoverageLog.from_dict(data)

        assert coverage_log.clazz == "com.example.app.MainActivity"
        assert coverage_log.method == "onCreate"
        assert coverage_log.params == "android.os.Bundle"
        assert coverage_log.signature == "com.example.app.MainActivity.onCreate(android.os.Bundle)"
        assert isinstance(coverage_log.time_occurred, datetime)
        assert coverage_log.time_since_task_start == 30
        assert coverage_log.original_msg == "Log message"

    def test_from_dict_no_timestamp(self):
        """Test from_dict method without timestamp"""
        data = {
            "class": "com.example.app.MainActivity",
            "method": "onCreate",
            "params": "android.os.Bundle",
            "signature": "com.example.app.MainActivity.onCreate(android.os.Bundle)"
        }

        coverage_log = RvCoverageLog.from_dict(data)

        assert coverage_log.clazz == "com.example.app.MainActivity"
        assert coverage_log.method == "onCreate"
        assert isinstance(coverage_log.time_occurred, datetime)

    def test_get_parameters_list(self, sample_coverage_log):
        """Test get_parameters_list method"""
        params = sample_coverage_log.get_parameters_list()
        assert params == ["android.os.Bundle"]

        # Test multiple parameters
        log = RvCoverageLog(
            clazz="com.example.app.MainActivity",
            method="onResult",
            params="int;java.lang.String",
            signature="com.example.app.MainActivity.onResult(int,java.lang.String)"
        )
        params = log.get_parameters_list()
        assert params == ["int", "java.lang.String"]

        # Test no parameters
        log = RvCoverageLog(
            clazz="com.example.app.MainActivity",
            method="clear",
            params="",
            signature="com.example.app.MainActivity.clear()"
        )
        params = log.get_parameters_list()
        assert params == []

    def test_string_representation(self, sample_coverage_log):
        """Test __str__ method"""
        string_repr = str(sample_coverage_log)

        assert "RvCoverageLog" in string_repr
        assert "clazz=com.example.app.MainActivity" in string_repr
        assert "method=onCreate" in string_repr
        assert "params=android.os.Bundle" in string_repr

    def test_repr(self, sample_coverage_log):
        """Test __repr__ method"""
        repr_str = repr(sample_coverage_log)

        assert sample_coverage_log.signature in repr_str
        assert ":" in repr_str  # Should include timestamp

    def test_hash(self, sample_coverage_log):
        """Test __hash__ method"""
        assert hash(sample_coverage_log) == hash(sample_coverage_log.signature)

    def test_equality(self, sample_coverage_log):
        """Test equality comparison"""
        # Same coverage log
        log2 = RvCoverageLog(
            clazz="com.example.app.MainActivity",
            method="onCreate",
            params="android.os.Bundle",
            signature="com.example.app.MainActivity.onCreate(android.os.Bundle)"
        )
        assert sample_coverage_log == log2

        # Different signature
        log3 = RvCoverageLog(
            clazz="com.example.app.MainActivity",
            method="onDestroy",
            params="",
            signature="com.example.app.MainActivity.onDestroy()"
        )
        assert sample_coverage_log != log3

        # Different type
        assert sample_coverage_log != "not a coverage log"


def test_tag_constants():
    """Test tag constants"""
    assert TAG_RVSEC == "RVSEC"
    assert TAG_RVSEC_COV == "RVSEC-COV"
