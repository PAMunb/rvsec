"""Frame-form normalization of violation class/method fields (gh89, issue #89).

The Java monitor is meant to hand the parser a class and a method already split apart.
For every method name containing ``$``, ``-`` or a space its own split fails and it falls
back to copying the whole ``StackTraceElement`` — source position included — into *both*
fields. The position then joins the ``(apk, class, method, spec)`` key every downstream
analysis uses, and one misuse is counted once per line it occurs at.

These tests drive ``_normalize_frame`` from the shared corner-case corpus in
``fixtures/frame_form_corpus.py``, whose values are taken verbatim from the frozen
2026-07-06 dataset. The same corpus is mirrored in the sibling ``rvsec`` reactor at
``rvsec/rvsec-core/src/test/resources/frame-form-corpus.txt`` and drives the Java suite, so
the two implementations of one algorithm cannot drift apart unnoticed
(``TestCorpusParity`` asserts that whenever the sibling repository is present).

Covers INV-ANA-50 (no source position in class/method), INV-ANA-51 (idempotent, no-op on
well-formed values) and INV-ANA-52 (guard anchored on the trailing group only).
"""

import importlib.util
import os
import re
from pathlib import Path

import pytest
from rv_coverage.parser.log.logcat_parser import (
    _normalize_frame,
    _parse_error_message,
    parse_logcat_line,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_corpus():
    """Load the corpus fixture by path: ``fixtures/`` is a data directory, not a package."""
    spec = importlib.util.spec_from_file_location(
        "frame_form_corpus", FIXTURES / "frame_form_corpus.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_corpus = _load_corpus()
FRAME_FORM_CASES = _corpus.FRAME_FORM_CASES
PASS_THROUGH_CASES = _corpus.PASS_THROUGH_CASES

# Any value still carrying a source position at the end fails INV-ANA-50.
_POSITION_SUFFIX = re.compile(r"\(.*:\d+\)$")

_CORPUS_UNDER_REACTOR = Path(
    "rvsec/rvsec-core/src/test/resources/frame-form-corpus.txt"
)


def _java_corpus() -> Path:
    """Locate the Java corpus mirror in the sibling ``rvsec`` reactor.

    ``$RVSEC_HOME`` is tried first because it is the reactor's own declared location and
    survives the tree being checked out anywhere. The relative walk is the fallback for a
    workspace where the variable is not exported; it is positional and would break if the
    directory depth changed, which is exactly why it is not the primary route.
    """
    home = os.environ.get("RVSEC_HOME")
    if home:
        candidate = Path(home) / _CORPUS_UNDER_REACTOR
        if candidate.exists():
            return candidate
    return Path(__file__).resolve().parents[6] / _CORPUS_UNDER_REACTOR


_JAVA_CORPUS = _java_corpus()


class TestNormalizeFrame:
    """INV-ANA-50/51/52 at the unit level, one assertion per real corner case."""

    @pytest.mark.parametrize(
        "value,expected_class,expected_method,expected_source",
        FRAME_FORM_CASES,
        ids=[c[0] for c in FRAME_FORM_CASES],
    )
    def test_frame_form_value_is_split(
        self, value, expected_class, expected_method, expected_source
    ):
        assert _normalize_frame(value) == (
            expected_class,
            expected_method,
            expected_source,
        )

    @pytest.mark.parametrize("value", PASS_THROUGH_CASES, ids=PASS_THROUGH_CASES)
    def test_well_formed_value_is_not_touched(self, value):
        """INV-ANA-51: a value not in frame form yields None, so the caller keeps it
        byte-identical. This is what guarantees the fix cannot damage correct records.
        """
        assert _normalize_frame(value) is None

    def test_empty_string_is_not_touched(self):
        assert _normalize_frame("") is None

    @pytest.mark.parametrize(
        "value,expected_class,expected_method,expected_source", FRAME_FORM_CASES
    )
    def test_normalization_is_idempotent(
        self, value, expected_class, expected_method, expected_source
    ):
        """INV-ANA-51: normalizing the *output* is a no-op, so running the parser over a
        corrected monitor's output produces exactly the same records as over an
        uncorrected one's."""
        assert _normalize_frame(expected_class) is None
        assert _normalize_frame(expected_method) is None

    @pytest.mark.parametrize(
        "value,expected_class,expected_method,expected_source", FRAME_FORM_CASES
    )
    def test_no_position_survives_in_either_field(
        self, value, expected_class, expected_method, expected_source
    ):
        """INV-ANA-50 / INV-CORE-42."""
        assert not _POSITION_SUFFIX.search(expected_class)
        assert not _POSITION_SUFFIX.search(expected_method)
        assert "(" not in expected_class

    def test_backtick_name_with_nested_parens(self):
        """INV-ANA-52: the guard must not constrain the prefix. This value carries a
        parenthesis pair *inside* the method name; a guard anchored on a dotted path
        before the parenthesis silently fails on it."""
        value = (
            "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest."
            "V2-header files (3xx format) are still decryptable after reading a V1-header file"
            "(CryptoMigrationV2CompatibilityTest.kt:131)"
        )
        clazz, method, source = _normalize_frame(value)
        assert (
            clazz
            == "dev.leonlatsch.photok.encryption.integration.CryptoMigrationV2CompatibilityTest"
        )
        assert (
            method
            == "V2-header files (3xx format) are still decryptable after reading a V1-header file"
        )
        assert source == "CryptoMigrationV2CompatibilityTest.kt:131"

    def test_position_group_without_dotted_remainder_warns_and_keeps_value(
        self, caplog
    ):
        """A frame with no class/method separator cannot come from a real
        StackTraceElement; refuse to guess, and say so."""
        with caplog.at_level("WARNING"):
            assert _normalize_frame("digest$okio(ByteString.kt:83)") is None
        assert "left unnormalized" in caplog.text


class TestFormat2EndToEnd:
    """Task 2.4/2.5: the normalization reaches the record built by the parser."""

    @staticmethod
    def _jca_line(frame, spec="MessageDigestSpec"):
        """Build an RVSEC line in the JCA Format 2 the Java ErrorSummary emits:
        ``spec,class,className,method,location,error[,message]``. When the upstream
        split fell back, class, method and location all hold the same whole frame."""
        return (
            f"07-06 10:00:00.000  4321  4321 E RVSEC: "
            f"{spec},{frame},init,{frame},{frame},MessageDigest,"
            f"expecting one of {{SHA-256, SHA-384, SHA-512}} but found MD5."
        )

    def test_real_frame_form_line_is_normalized(self):
        line = self._jca_line("okio.ByteString.digest$okio(ByteString.kt:83)")
        error, coverage = parse_logcat_line(line)

        assert coverage is None
        assert error.class_full_name == "okio.ByteString"
        assert error.method == "digest$okio"
        assert error.source == "ByteString.kt:83"
        assert "(" not in error.class_full_name
        assert "(" not in error.method

    def test_two_adjacent_lines_collapse_to_one_key(self):
        """The defect, stated as a test: two occurrences of one misuse at lines 83 and 84
        must agree on (class, method, spec) and differ only in source."""
        first, _ = parse_logcat_line(
            self._jca_line("okio.ByteString.digest$okio(ByteString.kt:83)")
        )
        second, _ = parse_logcat_line(
            self._jca_line("okio.ByteString.digest$okio(ByteString.kt:84)")
        )

        assert (first.class_full_name, first.method, first.spec) == (
            second.class_full_name,
            second.method,
            second.spec,
        )
        assert first.unique_msg == second.unique_msg
        assert first.source != second.source
        assert (first.source, second.source) == ("ByteString.kt:83", "ByteString.kt:84")

    def test_well_formed_format2_message_is_unchanged(self, caplog):
        """A record from a corrected monitor passes through byte-identical, and silently.

        The absence of the log line matters as much as the values: the debug entry is what
        makes a normalization auditable after a campaign, so it must fire only when one
        actually happened.
        """
        with caplog.at_level("DEBUG"):
            error = _parse_error_message(
                "SSLContextSpec,okhttp3.internal.platform.Platform,init,newSSLContext,"
                "Platform.kt:104,SSLContext,uses a default TLS version"
            )
        assert error.class_full_name == "okhttp3.internal.platform.Platform"
        assert error.method == "newSSLContext"
        assert error.source == "Platform.kt:104"
        assert "Normalized frame-form" not in caplog.text

    @pytest.mark.parametrize(
        "value,expected_class,expected_method,expected_source",
        FRAME_FORM_CASES,
        ids=[c[0] for c in FRAME_FORM_CASES],
    )
    def test_no_frame_form_in_output(
        self, value, expected_class, expected_method, expected_source
    ):
        """INV-ANA-50 over the whole corpus, through the public entry point.

        Values carrying a comma would be re-split by Format 2's comma parse, so the
        end-to-end assertion is made only on the values that can actually travel in this
        format; the corpus has none with a comma today, and this skip documents why if
        one is ever added."""
        if "," in value:
            pytest.skip("value contains a comma and cannot travel in Format 2 verbatim")
        error, _ = parse_logcat_line(TestFormat2EndToEnd._jca_line(value))
        assert error.class_full_name == expected_class
        assert error.method == expected_method
        assert error.source == expected_source
        assert not _POSITION_SUFFIX.search(error.class_full_name)
        assert not _POSITION_SUFFIX.search(error.method)


class TestOtherFormatsUntouched:
    """Design D3: Formats 1 and 3 already split structurally and are not normalized."""

    def test_generic_spec_error_format_unchanged(self):
        error, _ = parse_logcat_line(
            "07-06 10:00:00.000 1234 5678 E RVSEC: "
            "com.example.app.Auth.login(Auth.java:123) ::: AuthSpec went into an error state."
        )
        assert error.class_full_name == "com.example.app.Auth"
        assert error.method == "login"
        assert error.source == "Auth.java"

    def test_fsm_format_unchanged(self):
        error, _ = parse_logcat_line(
            "07-06 10:00:00.000 1234 5678 E RVSEC: "
            "com.example.app.Auth.login():::AuthSpec went into an error state."
        )
        assert error.class_full_name == "com.example.app.Auth"
        assert error.method == "login"
        # The FSM line carries no source position; the parser names that rather than
        # fabricating the line number 1 (INV-ANA-08).
        assert error.source == "UNSPECIFIED:0"


class TestCorpusParity:
    """Task 5.1: the Java and the Python suite must be driven by the same values.

    Divergence here is a blocker, not a note — the whole point of a shared corpus is that
    one algorithm implemented twice is tested against one set of inputs.
    """

    @pytest.mark.skipif(
        not _JAVA_CORPUS.exists(),
        reason="sibling rvsec reactor not present in this checkout",
    )
    def test_java_corpus_matches_python_corpus(self):
        frame_cases = []
        pass_through = []
        for raw in _JAVA_CORPUS.read_text(encoding="utf-8").splitlines():
            if not raw.strip() or raw.startswith("#"):
                continue
            value, clazz, method, source = raw.split("\t")
            if clazz == "-":
                pass_through.append(value)
            else:
                frame_cases.append((value, clazz, method, source))

        assert frame_cases == FRAME_FORM_CASES
        assert pass_through == PASS_THROUGH_CASES
