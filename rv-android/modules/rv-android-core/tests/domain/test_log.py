from datetime import datetime
from unittest.mock import patch

import pytest
from rv_android_core.domain.log import (
    TAG_RVSEC,
    TAG_RVSEC_COV,
    RvCoverageLog,
    RvErrorLog,
)


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
            message="Attempted to access camera without permission",
        )

    def test_error_log_initialization(self, sample_error_log):
        """Test RvErrorLog constructor"""
        assert sample_error_log.spec == "SecuritySpec"
        assert sample_error_log.error_type == "PERMISSION_VIOLATION"
        assert sample_error_log.class_full_name == "com.example.app.MainActivity"
        assert sample_error_log.method == "accessCamera"
        assert sample_error_log.source == "MainActivity.java"
        assert (
            sample_error_log.message == "Attempted to access camera without permission"
        )

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
            "time_since_task_start": 30,
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
            "message": "Attempted to access camera without permission",
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
            message="Attempted to access camera without permission",
        )
        assert sample_error_log == error2

        # Different error
        error3 = RvErrorLog(
            spec="SecuritySpec",
            error_type="DIFFERENT_ERROR",
            class_full_name="com.example.app.MainActivity",
            method="accessCamera",
            source="MainActivity.java",
            message="Different message",
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
            signature="com.example.app.MainActivity.onCreate(android.os.Bundle)",
        )

    def test_coverage_log_initialization(self, sample_coverage_log):
        """Test RvCoverageLog constructor"""
        assert sample_coverage_log.clazz == "com.example.app.MainActivity"
        assert sample_coverage_log.method == "onCreate"
        assert sample_coverage_log.params == "android.os.Bundle"
        assert (
            sample_coverage_log.signature
            == "com.example.app.MainActivity.onCreate(android.os.Bundle)"
        )

        # Check auto-generated fields
        assert isinstance(sample_coverage_log.time_occurred, datetime)
        assert sample_coverage_log.time_since_task_start == 0
        assert sample_coverage_log.original_msg == ""

    def test_to_dict(self, sample_coverage_log):
        """Test to_dict method"""
        # Mock utils.datetime_to_milliseconds para um comportamento conhecido
        with patch(
            "rv_android_core.domain.log.utils.datetime_to_milliseconds",
            return_value=123456789,
        ):
            dic = sample_coverage_log.to_dict()

            assert dic["class"] == "com.example.app.MainActivity"
            assert dic["method"] == "onCreate"
            assert dic["params"] == "android.os.Bundle"
            assert (
                dic["signature"]
                == "com.example.app.MainActivity.onCreate(android.os.Bundle)"
            )
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
            "original_msg": "Log message",
        }

        coverage_log = RvCoverageLog.from_dict(data)

        assert coverage_log.clazz == "com.example.app.MainActivity"
        assert coverage_log.method == "onCreate"
        assert coverage_log.params == "android.os.Bundle"
        assert (
            coverage_log.signature
            == "com.example.app.MainActivity.onCreate(android.os.Bundle)"
        )
        assert isinstance(coverage_log.time_occurred, datetime)
        assert coverage_log.time_since_task_start == 30
        assert coverage_log.original_msg == "Log message"

    def test_from_dict_no_timestamp(self):
        """Test from_dict method without timestamp"""
        data = {
            "class": "com.example.app.MainActivity",
            "method": "onCreate",
            "params": "android.os.Bundle",
            "signature": "com.example.app.MainActivity.onCreate(android.os.Bundle)",
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
            signature="com.example.app.MainActivity.onResult(int,java.lang.String)",
        )
        params = log.get_parameters_list()
        assert params == ["int", "java.lang.String"]

        # Test no parameters
        log = RvCoverageLog(
            clazz="com.example.app.MainActivity",
            method="clear",
            params="",
            signature="com.example.app.MainActivity.clear()",
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
            signature="com.example.app.MainActivity.onCreate(android.os.Bundle)",
        )
        assert sample_coverage_log == log2

        # Different signature
        log3 = RvCoverageLog(
            clazz="com.example.app.MainActivity",
            method="onDestroy",
            params="",
            signature="com.example.app.MainActivity.onDestroy()",
        )
        assert sample_coverage_log != log3

        # Different type
        assert sample_coverage_log != "not a coverage log"


def test_tag_constants():
    """Test tag constants"""
    assert TAG_RVSEC == "RVSEC"
    assert TAG_RVSEC_COV == "RVSEC-COV"


class TestSourceIsPreservedButNotIdentifying:
    """INV-CORE-40 (gh89): `source` reaches the written schema without entering any key.

    The distinction being asserted is between excluding a field from the *identity* of a
    violation and *discarding* it. Two occurrences of one misuse at different source lines
    are one misuse — so the position must not identify a violation — but it is still the
    most direct pointer to where the violation happened, and the evidence needed to audit a
    frame-form normalization after a campaign has run.
    """

    @staticmethod
    def _error(source):
        return RvErrorLog(
            spec="MessageDigestSpec",
            error_type="MessageDigest",
            class_full_name="okio.ByteString",
            method="digest$okio",
            source=source,
            message="expecting one of {SHA-256} but found MD5.",
        )

    def test_to_dict_includes_source(self):
        error = self._error("ByteString.kt:83")
        assert error.to_dict()["source"] == "ByteString.kt:83"

    def test_to_dict_carries_every_written_field(self):
        """The dict is the row `errors.csv` is built from; a dropped key silently
        empties a column."""
        keys = set(self._error("ByteString.kt:83").to_dict())
        assert keys == {
            "spec",
            "error_type",
            "class_full_name",
            "method",
            "source",
            "code",
            "event",
            "message",
            "obj",
            "val",
            "exp",
            "msg",
            "truncated",
            "time_occurred",
            "time_since_task_start",
            "unique_msg",
        }

    def test_source_does_not_affect_identity(self):
        """Adjacent lines 83 and 84 are one misuse, not two."""
        first, second = self._error("ByteString.kt:83"), self._error("ByteString.kt:84")

        assert first.unique_msg == second.unique_msg
        assert first == second
        assert hash(first) == hash(second)
        assert "ByteString.kt" not in first.unique_msg

    def test_source_does_not_affect_unique_error_count(self):
        from rv_android_core.domain.coverage import LogcatRepository

        repo = LogcatRepository()
        repo.register_rv_error(self._error("ByteString.kt:83"))
        repo.register_rv_error(self._error("ByteString.kt:84"))

        assert len(repo.errors) == 2
        assert len(repo.unique_errors) == 1

    def test_round_trip_through_dict_preserves_source(self):
        error = self._error("ByteString.kt:83")
        assert RvErrorLog.from_dict(error.to_dict()).source == "ByteString.kt:83"

    def test_distinct_offending_parameters_remain_distinct_events(self):
        """INV-CORE-41: `unique_msg` counts at event granularity, and that is deliberate.

        Two violations of the same method under the same spec whose messages name
        different offending algorithms are two different misuses of that method, not one
        counted twice — so `message` belongs in the key. The downstream
        `(apk, class, method, spec)` analysis key coarsens them back to 1. Both counts are
        correct at their own granularity, which is exactly why this must not be "fixed"
        by dropping `message`.
        """
        from rv_android_core.domain.coverage import LogcatRepository

        def violation(message):
            return RvErrorLog(
                spec="MessageDigestSpec",
                error_type="MessageDigest",
                class_full_name="com.apk.axml.APKParser",
                method="getCertificateFingerprint",
                source="APKParser.java:120",
                message=message,
            )

        sha1 = violation("expecting one of {SHA-256, SHA-384, SHA-512} but found SHA1.")
        md5 = violation("expecting one of {SHA-256, SHA-384, SHA-512} but found MD5.")

        assert sha1.unique_msg != md5.unique_msg
        assert sha1 != md5

        repo = LogcatRepository()
        repo.register_rv_error(sha1)
        repo.register_rv_error(md5)
        assert len(repo.unique_errors) == 2

        # The analysis key deliberately drops error_type and message.
        analysis_keys = {(e.class_full_name, e.method, e.spec) for e in (sha1, md5)}
        assert len(analysis_keys) == 1


class TestSevenPartIdentity:
    """INV-CORE-25/56/57: `unique_msg` is
    `class:::method:::spec:::error_type:::code:::event:::message`, and it is built here
    and nowhere else.

    The two new parts are the `code=` and `ev=` values of the message envelope the
    `jca_android` monitors write. A record with no envelope — the frozen `jca` set, and
    everything persisted before this change — carries the sentinel `UNSPECIFIED` in both
    rather than an empty string, so a legacy key is still seven readable parts and a
    reader can tell "no envelope" from "envelope with an empty value".
    """

    @staticmethod
    def _envelope_error():
        return RvErrorLog(
            spec="PBEKeySpecSpec",
            error_type="ForbiddenMethod",
            class_full_name="com.example.vault.KeyDeriver",
            method="derive",
            source="KeyDeriver.java:31",
            code="PBEKEYSPEC-FORB-01",
            event="f1",
            obj="PBEKeySpec",
            val="PBEKeySpec(char[])",
            exp="PBEKeySpec(char[],byte[],int,int)",
            msg="forbidden constructor",
            message=(
                "v=1 code=PBEKEYSPEC-FORB-01 ev=f1 obj=PBEKeySpec "
                "val='PBEKeySpec(char[])' exp='PBEKeySpec(char[],byte[],int,int)' "
                "msg='forbidden constructor'"
            ),
        )

    @staticmethod
    def _legacy_error():
        return RvErrorLog(
            spec="MessageDigestSpec",
            error_type="SequenceViolation",
            class_full_name="okio.ByteString",
            method="digest$okio",
            source="ByteString.kt:83",
            message="unknown",
        )

    def test_an_envelope_message_yields_code_and_event_parts(self):
        error = self._envelope_error()

        assert error.unique_msg == (
            "com.example.vault.KeyDeriver:::derive:::PBEKeySpecSpec:::ForbiddenMethod"
            ":::PBEKEYSPEC-FORB-01:::f1:::"
            "v=1 code=PBEKEYSPEC-FORB-01 ev=f1 obj=PBEKeySpec "
            "val='PBEKeySpec(char[])' exp='PBEKeySpec(char[],byte[],int,int)' "
            "msg='forbidden constructor'"
        )

        parts = error.unique_msg.split(":::")
        assert len(parts) == 7
        assert parts[4] == "PBEKEYSPEC-FORB-01"
        assert parts[5] == "f1"

    def test_a_legacy_unknown_message_yields_the_sentinels(self):
        error = self._legacy_error()

        assert error.code == "UNSPECIFIED"
        assert error.event == "UNSPECIFIED"
        assert error.unique_msg == (
            "okio.ByteString:::digest$okio:::MessageDigestSpec:::SequenceViolation"
            ":::UNSPECIFIED:::UNSPECIFIED:::unknown"
        )

    def test_two_legacy_records_deduplicate(self):
        from rv_android_core.domain.coverage import LogcatRepository

        repo = LogcatRepository()
        repo.register_rv_error(self._legacy_error())
        repo.register_rv_error(self._legacy_error())

        assert len(repo.unique_errors) == 1

    def test_an_empty_code_or_event_still_renders_the_sentinel(self):
        """A caller that writes `code=""` gets the sentinel, not an empty part: an empty
        part would make the key ambiguous with a key whose part was genuinely absent."""
        error = self._legacy_error().model_copy(update={"code": "", "event": ""})

        assert error.unique_msg.split(":::")[4] == "UNSPECIFIED"
        assert error.unique_msg.split(":::")[5] == "UNSPECIFIED"

    def test_event_separates_two_records_that_agree_on_everything_else(self):
        """INV-CORE-57: the identity discontinuity is not a no-op on an envelope corpus."""
        from rv_android_core.domain.coverage import LogcatRepository

        def violation(event):
            return RvErrorLog(
                spec="MessageDigestSpec",
                error_type="UnsafeAlgorithm",
                class_full_name="com.apk.axml.APKParser",
                method="getCertificateFingerprint",
                source="APKParser.java:120",
                code="MESSAGEDIGEST-ALG-01",
                event=event,
                message="v=1 code=MESSAGEDIGEST-ALG-01 ev=%s obj=MessageDigest val='MD5' exp='SHA-256' msg='bad'"
                % event,
            )

        g1, d1 = violation("g1"), violation("d1")
        assert g1.unique_msg != d1.unique_msg

        repo = LogcatRepository()
        repo.register_rv_error(g1)
        repo.register_rv_error(d1)
        assert len(repo.unique_errors) == 2

    def test_round_trip_through_dict_preserves_the_envelope_fields(self):
        error = self._envelope_error()
        restored = RvErrorLog.from_dict(error.to_dict())

        assert restored.code == "PBEKEYSPEC-FORB-01"
        assert restored.event == "f1"
        assert restored.obj == "PBEKeySpec"
        assert restored.val == "PBEKeySpec(char[])"
        assert restored.exp == "PBEKeySpec(char[],byte[],int,int)"
        assert restored.msg == "forbidden constructor"
        assert restored.unique_msg == error.unique_msg

    def test_a_dict_without_the_envelope_keys_restores_the_sentinels(self):
        """`tasks.json` files written before this change carry no `code`/`event` keys."""
        restored = RvErrorLog.from_dict(
            {
                "spec": "MessageDigestSpec",
                "error_type": "SequenceViolation",
                "class_full_name": "okio.ByteString",
                "method": "digest$okio",
                "source": "ByteString.kt:83",
                "message": "unknown",
            }
        )

        assert restored.code == "UNSPECIFIED"
        assert restored.event == "UNSPECIFIED"
        assert restored.truncated is False

    def test_a_message_carrying_the_separator_is_not_rewritten(self):
        """INV-CORE-56: the model does not hide a producer's violation of the grammar."""
        error = self._legacy_error().model_copy(
            update={"message": "expecting one of {A:::B} but found C."}
        )

        assert error.unique_msg.count(":::") == 7
        assert len(error.unique_msg.split(":::")) == 8
