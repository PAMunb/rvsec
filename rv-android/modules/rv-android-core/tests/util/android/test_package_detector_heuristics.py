"""Unit tests for the pure-logic surface of the package detector.

This file complements ``test_package_detector.py`` (issue #63 fast-path
regressions). It exercises the parts the regression file leaves uncovered:

- The whole ``StringSimilarity`` class (Levenshtein, normalized Levenshtein,
  Jaro-Winkler, combined).
- The ``PackageDetector`` helpers (``is_framework``, ``extract_package``,
  ``find_common_prefix``, ``is_valid_prefix``, ``detect_game_engine``,
  ``find_similar_package``).
- The multi-package priority branches of ``detect_package`` (game-engine
  priority 0, common_prefix, most_common 60% dominance, similarity_match,
  no_consensus).

Design note: every ``detect_package`` scenario is constructed so the manifest
package is NOT a namespace parent of all components. That deliberately avoids
the ``same_package`` fast path (already covered by the regression file) so the
component reaches exactly the priority branch under test.
"""

import pytest

from rv_android_core.util.android.package_detector import (
    PackageDetector,
    StringSimilarity,
)


class _StubAPK:
    """Minimal androguard APK stand-in exposing only the accessors that
    ``detect_package()`` reads. ContentProviders are not consumed by the
    detector, so they are intentionally omitted."""

    def __init__(self, package, activities=None, services=None, receivers=None):
        self._package = package
        self._activities = activities or []
        self._services = services or []
        self._receivers = receivers or []

    def get_package(self):
        return self._package

    def get_activities(self):
        return self._activities

    def get_services(self):
        return self._services

    def get_receivers(self):
        return self._receivers


class TestLevenshteinDistance:
    """``StringSimilarity.levenshtein_distance`` — minimum edit distance.

    Partitions: identical (distance 0), one edit away, empty operand, and the
    length-swap recursion. Boundary values focus on empty and single edits,
    where off-by-one errors in the DP table typically surface.
    """

    def test_identical_strings_have_zero_distance(self):
        """Two identical strings need no edits."""
        assert StringSimilarity.levenshtein_distance("com.foo", "com.foo") == 0

    def test_single_substitution_is_distance_one(self):
        """A one-character substitution costs exactly one edit."""
        assert StringSimilarity.levenshtein_distance("cat", "bat") == 1

    def test_classic_kitten_sitting_is_three(self):
        """The textbook kitten->sitting transformation is three edits
        (two substitutions plus one insertion)."""
        assert StringSimilarity.levenshtein_distance("kitten", "sitting") == 3

    def test_empty_second_operand_returns_length_of_first(self):
        """With an empty target, the distance is the length of the source
        (delete every character). Exercises the ``len(s2) == 0`` short-circuit."""
        assert StringSimilarity.levenshtein_distance("abc", "") == 3

    def test_shorter_first_operand_triggers_swap_recursion(self):
        """When s1 is shorter than s2 the function recurses with arguments
        swapped; the result must stay symmetric. Here two insertions are
        needed to turn ``ab`` into ``abcd``."""
        assert StringSimilarity.levenshtein_distance("ab", "abcd") == 2


class TestNormalizedLevenshtein:
    """``StringSimilarity.normalized_levenshtein`` — distance scaled to [0, 1]."""

    def test_identical_strings_score_one(self):
        """Identical strings have distance 0, so similarity is 1.0."""
        assert StringSimilarity.normalized_levenshtein("app", "app") == 1.0

    def test_both_empty_scores_one(self):
        """Two empty strings are trivially identical; the ``max_len == 0``
        guard must return 1.0 rather than divide by zero."""
        assert StringSimilarity.normalized_levenshtein("", "") == 1.0

    def test_single_edit_over_length_three(self):
        """One edit across a max length of three yields 1 - 1/3."""
        assert StringSimilarity.normalized_levenshtein("cat", "bat") == pytest.approx(
            2 / 3
        )


class TestJaroWinklerSimilarity:
    """``StringSimilarity.jaro_winkler_similarity`` — prefix-weighted metric.

    Partitions: identical, one empty operand, fully disjoint (no matches),
    single differing characters (drives ``match_distance`` negative), and a
    canonical transposition case with a shared prefix.
    """

    def test_identical_strings_score_one(self):
        """Identical inputs short-circuit to a perfect 1.0."""
        assert StringSimilarity.jaro_winkler_similarity("martha", "martha") == 1.0

    def test_empty_operand_scores_zero(self):
        """An empty operand can share nothing, so similarity is 0.0."""
        assert StringSimilarity.jaro_winkler_similarity("martha", "") == 0.0

    def test_disjoint_strings_score_zero(self):
        """Strings with no common characters produce zero matches -> 0.0."""
        assert StringSimilarity.jaro_winkler_similarity("abc", "xyz") == 0.0

    def test_single_differing_chars_score_zero(self):
        """Two distinct single characters drive ``match_distance`` negative
        (clamped to 0) and yield no matches, so the result is 0.0. This is the
        boundary case that exercises the negative-match-distance guard."""
        assert StringSimilarity.jaro_winkler_similarity("a", "b") == 0.0

    def test_canonical_martha_marhta(self):
        """The textbook martha/marhta pair (one transposition, 3-char shared
        prefix) is the standard Jaro-Winkler validation value ~0.961."""
        score = StringSimilarity.jaro_winkler_similarity("martha", "marhta")
        assert score == pytest.approx(0.9611, abs=1e-3)

    def test_shared_prefix_boosts_score_above_plain_jaro(self):
        """The prefix bonus must raise the score for strings that agree on a
        long leading prefix, which is exactly the package-name typo case."""
        score = StringSimilarity.jaro_winkler_similarity("org.fox.tttrss", "org.fox.ttrss")
        assert score >= 0.95


class TestCombinedSimilarity:
    """``StringSimilarity.combined_similarity`` — weighted blend of three metrics."""

    def test_identical_strings_score_one(self):
        """When every component metric returns 1.0, the weighted blend is 1.0."""
        assert StringSimilarity.combined_similarity("com.foo", "com.foo") == pytest.approx(
            1.0
        )

    def test_near_match_scores_high_but_below_one(self):
        """A single-character package typo stays high (well above the 0.85
        detection threshold) yet strictly below a perfect match."""
        score = StringSimilarity.combined_similarity("org.fox.tttrss", "org.fox.ttrss")
        assert 0.85 <= score < 1.0

    def test_disjoint_strings_score_low(self):
        """Unrelated packages must score far below the detection threshold."""
        score = StringSimilarity.combined_similarity("com.foo", "xyz.qqq")
        assert score < 0.5


class TestIsFramework:
    """``PackageDetector.is_framework`` — framework/library prefix filter."""

    @pytest.fixture
    def detector(self):
        return PackageDetector()

    def test_androidx_component_is_framework(self, detector):
        """A component under a listed framework prefix (androidx.) is framework
        code and must be excluded from application detection."""
        assert detector.is_framework("androidx.appcompat.app.AppCompatActivity") is True

    def test_application_component_is_not_framework(self, detector):
        """A component in an application package is not framework code."""
        assert detector.is_framework("com.example.app.MainActivity") is False


class TestExtractPackage:
    """``PackageDetector.extract_package`` — N-level package extraction."""

    @pytest.fixture
    def detector(self):
        return PackageDetector()

    def test_extracts_three_levels_by_default(self, detector):
        """A deep component name is truncated to three package levels."""
        assert (
            detector.extract_package("com.example.app.ui.MainActivity")
            == "com.example.app"
        )

    def test_short_component_returns_all_available_parts(self, detector):
        """When the component has fewer parts than the requested level, all
        available parts are returned unchanged (no padding, no error)."""
        assert detector.extract_package("com.app", level=3) == "com.app"


class TestFindCommonPrefix:
    """``PackageDetector.find_common_prefix`` — longest namespace prefix.

    The tricky case is character-boundary truncation: ``os.path.commonprefix``
    works char-by-char, so shared prefixes must be pulled back to the last full
    dotted segment.
    """

    @pytest.fixture
    def detector(self):
        return PackageDetector()

    def test_empty_set_returns_empty_string(self, detector):
        """No packages -> no prefix."""
        assert detector.find_common_prefix(set()) == ""

    def test_shared_namespace_returns_aligned_prefix(self, detector):
        """Two packages under the same namespace yield that namespace."""
        assert (
            detector.find_common_prefix({"com.example.app", "com.example.lib"})
            == "com.example"
        )

    def test_disjoint_roots_return_empty_string(self, detector):
        """Packages with no shared leading segment yield an empty prefix."""
        assert detector.find_common_prefix({"com.foo", "org.bar"}) == ""

    def test_partial_segment_is_truncated_to_boundary(self, detector):
        """``com.example.app`` and ``com.example.api`` share the raw character
        prefix ``com.example.ap``; that partial segment must be truncated back
        to the last complete package boundary ``com.example``."""
        assert (
            detector.find_common_prefix({"com.example.app", "com.example.api"})
            == "com.example"
        )


class TestIsValidPrefix:
    """``PackageDetector.is_valid_prefix`` — prefix meaningfulness check.

    Decision table over: emptiness, minimum depth (>= 2 levels), and the three
    ways a prefix can relate to the manifest package (prefix-of, superset-of,
    or shared first two levels).
    """

    @pytest.fixture
    def detector(self):
        return PackageDetector()

    def test_empty_prefix_is_invalid(self, detector):
        """An empty prefix carries no namespace information."""
        assert detector.is_valid_prefix("", "com.example.app") is False

    def test_single_level_prefix_is_invalid(self, detector):
        """A one-level prefix (no dot) is too shallow to be meaningful."""
        assert detector.is_valid_prefix("com", "com.example.app") is False

    def test_prefix_that_manifest_extends_is_valid(self, detector):
        """A prefix that the manifest package extends (manifest starts with the
        prefix) is a valid ancestor namespace."""
        assert detector.is_valid_prefix("com.example", "com.example.app") is True

    def test_prefix_sharing_first_two_levels_is_valid(self, detector):
        """Even without a direct prefix relationship, sharing the first two
        package levels (com.foo) is enough to be considered related."""
        assert detector.is_valid_prefix("com.foo.bar", "com.foo.baz") is True

    def test_unrelated_prefix_is_invalid(self, detector):
        """A prefix that neither extends nor shares the first two levels of the
        manifest package is rejected."""
        assert detector.is_valid_prefix("com.foo", "org.bar") is False


class TestDetectGameEngine:
    """``PackageDetector.detect_game_engine`` — known-runtime detection."""

    @pytest.fixture
    def detector(self):
        return PackageDetector()

    def test_godot_component_is_detected(self, detector):
        """A component under a known engine package returns the engine name and
        its package prefix."""
        result = detector.detect_game_engine(["org.godotengine.godot.GodotActivity"])
        assert result == ("godot", "org.godotengine.godot")

    def test_no_engine_returns_none(self, detector):
        """Ordinary application components map to no known engine."""
        assert detector.detect_game_engine(["com.example.app.MainActivity"]) is None


class TestFindSimilarPackage:
    """``PackageDetector.find_similar_package`` — similarity fallback."""

    def test_empty_candidates_returns_none(self):
        """With no candidates there is nothing to compare against."""
        assert PackageDetector().find_similar_package("com.foo", set()) is None

    def test_typo_variant_above_threshold_is_returned(self):
        """A near-identical package (single extra character) scores above the
        default 0.85 threshold and is returned with its score."""
        result = PackageDetector().find_similar_package(
            "org.fox.tttrss", {"org.fox.ttrss"}
        )
        assert result is not None
        pkg, score = result
        assert pkg == "org.fox.ttrss"
        assert score >= 0.85

    def test_dissimilar_candidate_below_threshold_returns_none(self):
        """A candidate that is not similar enough (below threshold) yields no
        match, so the detector must fall through rather than pick it."""
        assert (
            PackageDetector().find_similar_package("com.foo", {"xyz.abc.qqq"}) is None
        )


class TestDetectPackageMultiPackageBranches:
    """``PackageDetector.detect_package`` — the priority branches beyond the
    ``same_package`` fast path.

    Each scenario is engineered so the manifest package is not a namespace
    parent of all components (skipping the fast path) and so exactly one
    priority branch fires.
    """

    def test_game_engine_priority_wins(self):
        """Priority 0: a Godot runtime component with the manifest package
        absent from the code yields a high-confidence game_engine result whose
        code_package stays the (authoritative) manifest package."""
        apk = _StubAPK(
            package="ir.hsn6.trans",
            activities=["org.godotengine.godot.GodotActivity"],
        )

        result = PackageDetector().detect_package(apk)

        assert result.detection_method == "game_engine_godot"
        assert result.confidence == "high"
        assert result.code_package == "ir.hsn6.trans"
        assert result.game_engine == "godot"

    def test_common_prefix_across_subpackages(self):
        """Priority 3: two distinct 3-level packages under a shared namespace
        that relates to the manifest package resolve to that common prefix with
        medium confidence."""
        apk = _StubAPK(
            package="com.example.app",
            activities=["com.example.app.MainActivity"],
            services=["com.example.lib.SyncService"],
        )

        result = PackageDetector().detect_package(apk)

        assert result.detection_method == "common_prefix"
        assert result.confidence == "medium"
        assert result.code_package == "com.example"

    def test_most_common_dominance_selects_top_package(self):
        """Priority 4: with no valid common prefix, a package covering 60%+ of
        components wins by frequency dominance. Here three of four components
        live in ``org.acme.app`` (75%)."""
        apk = _StubAPK(
            package="com.foo",
            activities=[
                "org.acme.app.MainActivity",
                "org.acme.app.SecondActivity",
                "org.acme.app.ThirdActivity",
            ],
            services=["net.other.lib.Helper"],
        )

        result = PackageDetector().detect_package(apk)

        assert result.detection_method == "most_common"
        assert result.confidence == "medium"
        assert result.code_package == "org.acme.app"

    def test_similarity_match_recovers_typo(self):
        """Priority 5: no prefix and no 60% dominance, but one candidate is a
        near-identical typo of the manifest package. Similarity matching
        recovers it and records the score."""
        apk = _StubAPK(
            package="org.fox.tttrss",
            activities=["org.fox.ttrss.MainActivity"],
            services=["com.other.lib.SyncService"],
        )

        result = PackageDetector().detect_package(apk)

        assert result.detection_method == "similarity_match"
        assert result.confidence == "medium"
        assert result.code_package == "org.fox.ttrss"
        assert result.similarity_score >= 0.85

    def test_no_consensus_falls_back_to_manifest(self):
        """Priority 6: multiple unrelated packages with no prefix, no dominance,
        and no similar candidate leave the detector with no consensus. It falls
        back to the manifest package at low confidence."""
        apk = _StubAPK(
            package="com.foo",
            activities=["org.aaa.bbb.MainActivity"],
            services=["net.ccc.ddd.SyncService"],
        )

        result = PackageDetector().detect_package(apk)

        assert result.detection_method == "no_consensus"
        assert result.confidence == "low"
        assert result.code_package == "com.foo"
