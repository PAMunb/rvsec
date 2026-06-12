"""
Package detector for Android APK analysis.

This module detects the actual package name of Android APK files by analyzing
component declarations, with support for game engine detection and string similarity
matching. It resolves cases where the AndroidManifest.xml package differs from the
actual code package, which occurs in apps with build variants or game engines.

### Architectural Overview:

The detector uses a priority-based heuristic algorithm that analyzes APK components
(Activities, Services, Receivers) to identify the application package. The approach
extracts package names from 3-level component hierarchies and applies multiple
disambiguation strategies: single package detection, common prefix matching, frequency-
based selection, game engine heuristics, and string similarity fallbacks.

### Key Architectural Decisions:

- **Priority-Based Heuristics**: Applies detection strategies in order of confidence
  rather than single-point heuristic, enabling multi-strategy fallback handling
- **Game Engine Detection**: Identifies runtime frameworks (Godot, Unity, Cocos2D,
  LibGDX) early to avoid false package mismatches
- **3-Level Package Extraction**: Balances specificity with generality for Android
  naming conventions without over-specifying subpackages
- **String Similarity**: Uses weighted combination (Jaro-Winkler 50%, Levenshtein 30%,
  SequenceMatcher 20%) for detecting minor package name variations
- **Common Prefix Validation**: Ensures multi-package apps are captured via package
  namespace prefix matching rather than single component location

### Role in the System:

- Resolves package name ambiguities in APK analysis during instrumentation preparation
- Enables accurate method signature matching between static and runtime analysis
- Provides confidence metrics for package detection decisions in analysis pipelines
- Handles edge cases including build variants, modular architectures, and game engines

### Integration Points:

- Input: APK instance (Androguard) already loaded by App model
- Output: PackageDetectionResult with manifest_package, code_package, confidence
- Used by: App.code_package property for static analysis parsers
- Dependency: Androguard for APK parsing and component enumeration

### Origin:

Adapted from rvsec-02/scripts/processors/package_detector.py (validated with 88.9%
resolution rate, 0 false positives across 40 APKs). The heuristic algorithm is
preserved identically; only the interface was adapted to accept APK instances
instead of file paths.
"""

import os
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import List, Optional, Set, Tuple

from androguard.core.bytecodes.apk import APK


@dataclass
class PackageDetectionResult:
    """Result of package detection analysis."""

    manifest_package: str
    code_package: str
    confidence: str  # "high", "medium", "low"
    detection_method: str  # "same_package", "single_package", "common_prefix", etc.
    all_packages: list = field(default_factory=list)
    similarity_score: float = 0.0
    game_engine: Optional[str] = None


class StringSimilarity:
    """
    String similarity algorithms for package name matching.

    Implements multiple distance metrics (Levenshtein, Jaro-Winkler, SequenceMatcher)
    to detect typos and minor variations in package names. Used as a fallback
    heuristic when component analysis produces ambiguous results.

    ### Key Features:

    - Levenshtein distance: Minimum edit distance between strings
    - Normalized Levenshtein: Distance scaled to 0.0-1.0 range
    - Jaro-Winkler: Optimized for short strings with prefix weighting
    - Combined similarity: Weighted average of three metrics for robust matching
    """

    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.

        Args:
            s1: First string.
            s2: Second string.

        Returns:
            Minimum number of single-character edits (insertions, deletions,
            substitutions) required to transform s1 into s2.
        """
        if len(s1) < len(s2):
            return StringSimilarity.levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    @staticmethod
    def normalized_levenshtein(s1: str, s2: str) -> float:
        """
        Calculate normalized Levenshtein similarity.

        Args:
            s1: First string.
            s2: Second string.

        Returns:
            Similarity score from 0.0 (completely different) to 1.0 (identical).
            Calculated as 1.0 - (distance / max_length).
        """
        distance = StringSimilarity.levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        return 1.0 - (distance / max_len)

    @staticmethod
    def jaro_winkler_similarity(s1: str, s2: str, prefix_weight: float = 0.1) -> float:
        """
        Calculate Jaro-Winkler similarity between two strings.

        Optimized for short string matching with extra weight given to common
        prefixes. Combines Jaro distance with a prefix scaling factor.

        Args:
            s1: First string.
            s2: Second string.
            prefix_weight: Weight bonus for matching prefixes (default: 0.1).

        Returns:
            Similarity score from 0.0 (completely different) to 1.0 (identical).
            Considers character matches within distance threshold and
            applies bonus for common prefixes.
        """
        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0

        match_distance = max(len1, len2) // 2 - 1
        if match_distance < 0:
            match_distance = 0

        s1_matches = [False] * len1
        s2_matches = [False] * len2

        matches = 0
        transpositions = 0

        # Find matches
        for i in range(len1):
            start = max(0, i - match_distance)
            end = min(i + match_distance + 1, len2)

            for j in range(start, end):
                if s2_matches[j] or s1[i] != s2[j]:
                    continue
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

        if matches == 0:
            return 0.0

        # Find transpositions
        k = 0
        for i in range(len1):
            if not s1_matches[i]:
                continue
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1

        jaro = (
            matches / len1 + matches / len2 + (matches - transpositions / 2) / matches
        ) / 3

        # Jaro-Winkler: add prefix bonus
        prefix_len = 0
        for i in range(min(len1, len2, 4)):
            if s1[i] == s2[i]:
                prefix_len += 1
            else:
                break

        return jaro + prefix_len * prefix_weight * (1 - jaro)

    @staticmethod
    def combined_similarity(s1: str, s2: str) -> float:
        """
        Calculate combined similarity using weighted average of three metrics.

        Combines three similarity algorithms into a single score for robustness:
        Jaro-Winkler (50% weight), normalized Levenshtein (30% weight),
        and SequenceMatcher (20% weight).

        Args:
            s1: First string.
            s2: Second string.

        Returns:
            Weighted combined similarity score from 0.0 to 1.0.
        """
        jw_score = StringSimilarity.jaro_winkler_similarity(s1, s2)
        lev_score = StringSimilarity.normalized_levenshtein(s1, s2)
        seq_score = SequenceMatcher(None, s1, s2).ratio()

        return jw_score * 0.5 + lev_score * 0.3 + seq_score * 0.2


class PackageDetector:
    """
    Detects the actual package name of Android APK files.

    Resolves package name discrepancies between AndroidManifest.xml declarations
    and actual code organization. Uses a priority-based heuristic approach combining
    component analysis, game engine detection, and string similarity matching.

    ### Architectural Decisions:

    - **Priority-Based Detection**: Applies six heuristics in order of confidence
      rather than single-method detection, enabling graceful fallbacks for edge cases
    - **Game Engine Handling**: Detects Godot/Unity/Cocos2D/LibGDX frameworks early
      to avoid false package mismatches (manifest package is developer-specified)
    - **3-Level Package Extraction**: Extracts package to 3 components (e.g.,
      com.example.app) to balance specificity with generality across Android conventions
    - **Common Prefix for Multi-Package**: Uses namespace prefix matching rather than
      single component location to capture modular/multi-package apps
    - **String Similarity as Fallback**: Uses weighted combination of three metrics
      (Jaro-Winkler, Levenshtein, SequenceMatcher) to detect minor variations/typos
    - **Framework Filtering**: Excludes Android framework, libraries, and common
      third-party packages to focus on application code

    ### Role in the System:

    - Resolves package name ambiguities during APK instrumentation preparation
    - Enables accurate method signature matching between static and runtime analysis
    - Provides confidence metrics for downstream processing and result validation
    - Handles edge cases: build variants, modular architectures, game engines

    ### Key Features:

    - Game engine detection (4 known runtimes: Godot, Unity, Cocos2D, LibGDX)
    - Multi-package support via common prefix detection
    - String similarity matching for typo/variation detection
    - Confidence scoring (high, medium, low) with decision reasoning
    """

    # Package prefixes to exclude from application code detection.
    # Filters out Android framework, standard libraries, and common third-party
    # packages to focus detection on application code. Organized by category.
    FRAMEWORK_PREFIXES = [
        # Android core
        "android.",
        "androidx.",
        "com.google.android.",
        "com.android.",
        "dalvik.",
        # Java standard
        "java.",
        "javax.",
        "kotlin.",
        "kotlinx.",
        # Common third-party libraries
        "org.apache.",
        "org.json.",
        "org.w3c.",
        "org.xml.",
        "org.xmlpull.",
        # Analytics and testing frameworks
        "org.acra.",
        "com.actionbarsherlock.",
        "com.viewpagerindicator.",
    ]

    # Known game engine runtime packages and their short names.
    # Maps engine package prefix to engine identifier used in detection output.
    # Game engines implement all application code in their package while
    # developers declare custom package in manifest.
    GAME_ENGINES = {
        "org.godotengine.godot": "godot",
        "com.unity3d.player": "unity",
        "org.cocos2dx.lib": "cocos2d",
        "com.badlogicgames.gdx": "libgdx",
    }

    def __init__(self, similarity_threshold: float = 0.85) -> None:
        """
        Initialize PackageDetector.

        Args:
            similarity_threshold: Minimum similarity score (0.0-1.0) for string
                similarity matching fallback. Default 0.85.
        """
        self.similarity_threshold = similarity_threshold
        self.similarity = StringSimilarity()

    def is_framework(self, component: str) -> bool:
        """
        Check if component belongs to framework or library code.

        Args:
            component: Full component name (e.g., androidx.appcompat.app.Activity).

        Returns:
            True if component is from framework/library, False if application code.
        """
        for prefix in self.FRAMEWORK_PREFIXES:
            if component.startswith(prefix):
                return True
        return False

    def _is_in_namespace(self, child: str, parent: str) -> bool:
        """
        Check whether ``child`` belongs to the ``parent`` namespace.

        A namespace match requires ``child`` to be ``parent`` itself or a true
        dotted sub-package — not merely a substring. This distinguishes a genuine
        sub-package (``com.foo.ui.MainActivity`` is in ``com.foo``) from a sibling
        package that only shares a textual prefix (``com.foobar.MainActivity`` is
        NOT in ``com.foo``, even though ``"com.foo"`` is a substring of it).

        Args:
            child: Component or package name to test (e.g., com.foo.ui.MainActivity).
            parent: Candidate namespace (e.g., com.foo).

        Returns:
            True if child is the parent namespace or nested within it.
        """
        return child == parent or child.startswith(parent + ".")

    def extract_package(self, component: str, level: int = 3) -> str:
        """
        Extract package name from component class name.

        Args:
            component: Full component class name (e.g., com.example.app.MainActivity).
            level: Number of package levels to extract (default: 3).

        Returns:
            Extracted package name (e.g., com.example.app).

        Example:
            >>> detector = PackageDetector()
            >>> detector.extract_package("com.example.app.ui.MainActivity", level=3)
            'com.example.app'
            >>> detector.extract_package("com.example.app.ui.MainActivity", level=4)
            'com.example.app.ui'
        """
        parts = component.split(".")
        if len(parts) >= level:
            return ".".join(parts[:level])
        return ".".join(parts)

    def find_common_prefix(self, packages: Set[str]) -> str:
        """
        Find common package namespace prefix.

        Identifies the longest common prefix across multiple packages,
        adjusted to package boundaries (dot-separated segments).

        Args:
            packages: Set of package names.

        Returns:
            Common prefix aligned to package boundary, or empty string if none.

        Example:
            >>> detector = PackageDetector()
            >>> detector.find_common_prefix({'com.example.app', 'com.example.lib'})
            'com.example'
            >>> detector.find_common_prefix({'com.foo', 'org.bar'})
            ''
        """
        if not packages:
            return ""

        sorted_pkgs = sorted(packages)
        prefix = os.path.commonprefix(sorted_pkgs)

        # os.path.commonprefix operates character-by-character, so "com.example.app"
        # and "com.example.api" yields "com.example.a" -- truncate to last full segment.
        if prefix and not prefix.endswith("."):
            prefix = prefix.rsplit(".", 1)[0] if "." in prefix else ""

        # Remove trailing dot
        prefix = prefix.rstrip(".")

        return prefix

    def is_valid_prefix(self, prefix: str, manifest_pkg: str) -> bool:
        """
        Validate if detected prefix is meaningful.

        A valid prefix must have minimum depth (at least 2 package levels) and
        relate to the manifest package (share ancestry or be derived from it).

        Args:
            prefix: Detected common package prefix.
            manifest_pkg: Package name from AndroidManifest.xml.

        Returns:
            True if prefix is valid and meaningful, False otherwise.
        """
        if not prefix:
            return False

        # At least 2 levels (com.example)
        if prefix.count(".") < 1:
            return False

        # Should relate to manifest package
        # (either prefix of manifest, or manifest is prefix of it)
        if prefix.startswith(manifest_pkg) or manifest_pkg.startswith(prefix):
            return True

        # Or at least share first 2 levels
        prefix_parts = prefix.split(".")[:2]
        manifest_parts = manifest_pkg.split(".")[:2]

        return prefix_parts == manifest_parts

    def detect_game_engine(self, components: List[str]) -> Optional[Tuple[str, str]]:
        """
        Detect if APK uses a known game engine runtime.

        Game engines (Godot, Unity, Cocos2D, LibGDX) implement application code
        in their own packages while developers declare custom packages in manifest.
        Early detection prevents false package mismatches.

        Args:
            components: List of component class names.

        Returns:
            Tuple of (engine_name, engine_package) if engine detected, else None.
            Engine names: 'godot', 'unity', 'cocos2d', 'libgdx'.
        """
        for comp in components:
            for engine_pkg, engine_name in self.GAME_ENGINES.items():
                if comp.startswith(engine_pkg):
                    return (engine_name, engine_pkg)
        return None

    def find_similar_package(
        self, manifest_pkg: str, candidates: Set[str]
    ) -> Optional[Tuple[str, float]]:
        """
        Find package most similar to manifest package.

        Uses combined string similarity (weighted average of Jaro-Winkler,
        Levenshtein, and SequenceMatcher) to detect typos and minor variations
        in package names.

        Args:
            manifest_pkg: Package name from AndroidManifest.xml.
            candidates: Set of candidate packages extracted from components.

        Returns:
            Tuple of (package, similarity_score) if score >= threshold, else None.
            Similarity score ranges from 0.0 (different) to 1.0 (identical).

        Example:
            >>> detector = PackageDetector(similarity_threshold=0.85)
            >>> detector.find_similar_package("org.fox.tttrss", {"org.fox.ttrss"})
            ('org.fox.ttrss', 0.96)
        """
        if not candidates:
            return None

        best_match = None
        best_score = 0.0

        for candidate in candidates:
            score = self.similarity.combined_similarity(manifest_pkg, candidate)

            if score > best_score:
                best_score = score
                best_match = candidate

        # Only return if above threshold
        if best_score >= self.similarity_threshold:
            return (best_match, best_score)

        return None

    def detect_package(self, apk: APK) -> PackageDetectionResult:
        """
        Detect actual package name of APK using priority-based heuristics.

        Applies six detection strategies in order of confidence: game engine
        detection, single package, common prefix, frequency-based selection,
        string similarity matching, and manifest fallback.

        ### Detection Priority:

        1. Same-as-manifest: All components in manifest package
        2. Game engine: Known runtime detected (Godot, Unity, Cocos2D, LibGDX)
        3. Single package: Only one package detected in components
        4. Common prefix: Multiple packages share valid namespace prefix
        5. Most common: One package covers 60%+ of components
        6. String similarity: Detected package 85%+ similar to manifest
        7. Manifest fallback: No consensus achieved

        Args:
            apk: Androguard APK instance (already loaded).

        Returns:
            PackageDetectionResult with manifest_package, code_package,
            confidence, detection_method, and supporting data.
        """
        manifest_pkg = apk.get_package()

        # Extract all components from manifest (Activities, Services, Receivers).
        # Providers are intentionally excluded: ContentProviders are frequently
        # from third-party libraries (Firebase, Room, etc.) and would pollute
        # frequency-based detection with non-application packages.
        all_components = []
        all_components.extend(apk.get_activities())
        all_components.extend(apk.get_services())
        all_components.extend(apk.get_receivers())

        # Filter to application components only (exclude Android framework,
        # libraries, and common third-party packages).
        app_components = [c for c in all_components if not self.is_framework(c)]

        # Fast path: check if all components belong to the manifest package.
        # This is the common case (~72.5% of APKs) and avoids the more expensive
        # heuristic pipeline below. Requires at least one application component —
        # an empty list carries no evidence and must fall through to the
        # no_app_components branch rather than yielding a vacuous same_package.
        # Namespace matching (not substring) ensures a sibling package such as
        # com.foobar does not match manifest com.foo.
        same_package = bool(app_components) and all(
            self._is_in_namespace(component, manifest_pkg)
            for component in app_components
        )

        if same_package:
            # All components in manifest package: no mismatch.
            return PackageDetectionResult(
                manifest_package=manifest_pkg,
                code_package=manifest_pkg,
                confidence="high",
                detection_method="same_package",
            )

        # Detect known game engine runtimes (Priority 0).
        # Game engines (Godot, Unity, etc.) implement all code in their package,
        # while developer declares custom package in manifest.
        engine_info = self.detect_game_engine(all_components)

        # Extract packages from app components (3-level)
        app_packages = set()
        for comp in app_components:
            pkg = self.extract_package(comp, level=3)
            app_packages.add(pkg)

        # Calculate package frequencies
        pkg_freq = Counter()
        for comp in app_components:
            pkg = self.extract_package(comp, level=3)
            pkg_freq[pkg] += 1

        # =============================================================================
        # PRIORITY-BASED DETECTION ALGORITHM
        # =============================================================================
        # Applies detection strategies in order of confidence. Each strategy
        # returns early if a match is found, enabling graceful fallback.

        detected_pkg = manifest_pkg
        confidence = "low"
        reason = "fallback"
        similarity_score = 0.0

        # Priority 0: Game Engine Detection
        # Game engines declare all code in their own package while developer
        # specifies custom package in manifest. Detected engine means manifest
        # package is authoritative (not a library mismatch).
        if engine_info and len(app_packages) > 0:
            manifest_in_components = any(
                self._is_in_namespace(pkg, manifest_pkg) for pkg in app_packages
            )

            if not manifest_in_components:
                # Game engine detected, manifest package not in components.
                detected_pkg = manifest_pkg
                confidence = "high"
                reason = f"game_engine_{engine_info[0]}"

        # Priority 1: No app components
        elif len(app_packages) == 0:
            # No application components found (rare edge case).
            detected_pkg = manifest_pkg
            confidence = "low"
            reason = "no_app_components"

        # Priority 2: Single package detected
        elif len(app_packages) == 1:
            # Only one package detected: use it directly.
            detected_pkg = list(app_packages)[0]
            confidence = "high"
            reason = "single_package"

        # Priority 3+: Multiple packages
        elif len(app_packages) > 1:
            # Priority 3: Common package prefix
            # For modular/multi-package apps, namespace prefix captures all subpackages.
            prefix = self.find_common_prefix(app_packages)

            if prefix and self.is_valid_prefix(prefix, manifest_pkg):
                # Valid namespace prefix found (e.g., edu.cmu.cylab for multi-package).
                detected_pkg = prefix
                confidence = "medium"
                reason = "common_prefix"

            else:
                # Priority 4: Most common package (dominance heuristic)
                top_pkg, top_count = pkg_freq.most_common(1)[0]

                # 60% threshold chosen empirically: lower values produced false
                # positives from library packages; higher values missed legitimate
                # main packages in apps with many library components.
                if top_count >= len(app_components) * 0.6:
                    # One package covers 60%+ of components: likely main package.
                    detected_pkg = top_pkg
                    confidence = "medium"
                    reason = "most_common"

                else:
                    # Priority 5: String similarity fallback
                    # Detects typos/minor variations (e.g., tttrss vs ttrss).
                    similar = self.find_similar_package(manifest_pkg, app_packages)

                    if similar:
                        similar_pkg, score = similar
                        detected_pkg = similar_pkg
                        confidence = "medium"
                        reason = "similarity_match"
                        similarity_score = score

                    else:
                        # Priority 6: Manifest fallback
                        # No consensus achieved, use manifest as conservative fallback.
                        detected_pkg = manifest_pkg
                        confidence = "low"
                        reason = "no_consensus"

        return PackageDetectionResult(
            manifest_package=manifest_pkg,
            code_package=detected_pkg,
            confidence=confidence,
            detection_method=reason,
            all_packages=list(app_packages),
            similarity_score=similarity_score,
            game_engine=engine_info[0] if engine_info else None,
        )
