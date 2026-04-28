package br.unb.cic.rv.pointcut;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests that cover matcher logic which does not require a live dexlib2
 * fixture. Full call-site matching is covered by {@code dex-mutator}
 * integration tests (task 5.8/5.9) where real APK inputs are available.
 */
class PointcutMatcherTest {

    @Test
    void typePatternMatchesExactName() {
        assertTrue(PointcutMatcher.matchesTypePattern("com.example.Foo", "com.example.Foo"));
        assertFalse(PointcutMatcher.matchesTypePattern("com.example.Foo", "com.example.Bar"));
    }

    @Test
    void typePatternDotDotStarIsPackageWildcard() {
        assertTrue(PointcutMatcher.matchesTypePattern("com.example.Foo", "com.example..*"));
        assertTrue(PointcutMatcher.matchesTypePattern("com.example.sub.Foo", "com.example..*"));
        assertFalse(PointcutMatcher.matchesTypePattern("com.other.Foo", "com.example..*"));
    }

    @Test
    void typePatternSingleDotStarIsSinglePackage() {
        // "com.example.*" matches direct children only — not sub-packages.
        assertTrue(PointcutMatcher.matchesTypePattern("com.example.Foo", "com.example.*"));
        assertFalse(PointcutMatcher.matchesTypePattern("com.example.sub.Foo", "com.example.*"));
    }

    @Test
    void typePatternTrailingPlusIsStripped() {
        // At the matcher level, T+ patterns are validated against the bare type.
        // The "+" prefix is consumed elsewhere (InheritanceResolver.isAssignableFrom).
        assertTrue(PointcutMatcher.matchesTypePattern("com.example.Foo", "com.example.Foo+"));
    }

    @Test
    void inheritanceResolverDegradesOnMissingClass() {
        // Smoke test — construct against a missing android.jar and empty APK set.
        AndroidClassIndex android = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver resolver = new InheritanceResolver(android, List.of());
        // Even with empty state, exact match must work.
        assertTrue(resolver.isAssignableFrom("java.lang.Object", "com.example.Foo"));
        assertTrue(resolver.isAssignableFrom("com.example.Foo", "com.example.Foo"));
        // Unknown relationship returns false rather than throwing.
        assertFalse(resolver.isAssignableFrom("com.example.Bar", "com.example.Foo"));
    }
}
