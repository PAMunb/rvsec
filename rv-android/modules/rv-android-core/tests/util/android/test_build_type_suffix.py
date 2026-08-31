"""Tests for the build-type suffix neutralization rule (INV-CORE-58).

The rule is one function and four properties: it compares in lowercase, it
applies repeatedly, it never reduces a key below two segments, and it returns
anything it does not recognise unchanged. The last is not a gap to be closed by
a longer list — it is INV-CORE-59, and the denominator gate is its backstop.
"""

import pytest
from rv_android_core.util.android.build_type_suffix import (
    BUILD_TYPE_DENYLIST,
    MIN_SEGMENTS,
    neutralize_build_type_suffix,
)


class TestSingleSuffix:
    """The common case: one Gradle `applicationIdSuffix` segment."""

    @pytest.mark.parametrize(
        "declared,expected",
        [
            ("br.com.colman.petals.debug", "br.com.colman.petals"),
            ("org.fossify.calendar.debug", "org.fossify.calendar"),
            ("com.github.cvzi.screenshottile.debug", "com.github.cvzi.screenshottile"),
            ("com.example.app.staging", "com.example.app"),
            ("com.example.app.nightly", "com.example.app"),
        ],
    )
    def test_trailing_denied_segment_is_removed(self, declared, expected):
        assert neutralize_build_type_suffix(declared) == expected

    def test_every_denylist_entry_is_stripped(self):
        """The list is data, so the test enumerates it rather than sampling it."""
        for segment in BUILD_TYPE_DENYLIST:
            assert (
                neutralize_build_type_suffix(f"com.example.app.{segment}")
                == "com.example.app"
            )


class TestStackedSuffixes:
    """Suffixes stack: `.qa.debug` is one Gradle variant, not two keys."""

    def test_two_segments_are_removed_in_one_call(self):
        assert neutralize_build_type_suffix("com.example.app.qa.debug") == (
            "com.example.app"
        )

    def test_three_segments_are_removed_in_one_call(self):
        assert neutralize_build_type_suffix("com.example.app.dev.qa.debug") == (
            "com.example.app"
        )

    def test_the_rule_is_idempotent(self):
        once = neutralize_build_type_suffix("com.example.app.beta.debug")
        assert neutralize_build_type_suffix(once) == once


class TestCaseInsensitivity:
    """Comparison is lowercase; the surviving spelling is the original one."""

    @pytest.mark.parametrize(
        "declared", ["com.example.app.BETA", "com.example.app.Debug", "com.a.b.DeV"]
    )
    def test_capitalized_suffix_is_recognized(self, declared):
        expected = ".".join(declared.split(".")[:-1])
        assert neutralize_build_type_suffix(declared) == expected

    def test_surviving_segments_keep_their_own_case(self):
        """The key must still match compiled class names, which are case-sensitive."""
        assert neutralize_build_type_suffix("com.Example.MyApp.DEBUG") == (
            "com.Example.MyApp"
        )


class TestTwoSegmentFloor:
    """Stripping to one segment would turn a key into a namespace-wide wildcard."""

    def test_a_two_segment_id_is_never_reduced(self):
        assert neutralize_build_type_suffix("com.debug") == "com.debug"

    def test_stripping_stops_at_the_floor(self):
        assert neutralize_build_type_suffix("com.app.debug.debug") == "com.app"
        assert neutralize_build_type_suffix("app.debug.debug") == "app.debug"

    def test_the_floor_is_two(self):
        assert MIN_SEGMENTS == 2


class TestUnrecognizedInput:
    """A rule that cannot resolve a key says so by changing nothing."""

    @pytest.mark.parametrize(
        "declared",
        [
            "com.example.app",  # nothing to strip
            "de.grobox.liberario",  # ships as de.grobox.transportr: no string rule
            "nerd.tuxmobil.fahrplan.congress",
            "com.example.app.foss",  # a real suffix family the denylist omits
            "com.example.app.debugger",  # not a segment boundary match
        ],
    )
    def test_returned_unchanged(self, declared):
        assert neutralize_build_type_suffix(declared) == declared

    def test_uncovered_suffix_reaches_the_gate_unresolved(self):
        """INV-CORE-59: the denylist is not total, and the unresolved key is the
        state the denominator gate exists to refuse.

        `.foss` is a build flavour, not a build type, and no compiled class in
        such an APK starts with the flavoured id. The rule leaves it standing —
        so the key that reaches GATOR is one that matches nothing, and what
        catches that is `check_denominator`'s zero-universe branch, not a longer
        list here.
        """
        declared = "com.example.app.foss"

        assert neutralize_build_type_suffix(declared) == declared
        assert declared.split(".")[-1] not in BUILD_TYPE_DENYLIST

    @pytest.mark.parametrize("declared", ["", "app", "debug"])
    def test_malformed_input_is_returned_unchanged(self, declared):
        assert neutralize_build_type_suffix(declared) == declared
