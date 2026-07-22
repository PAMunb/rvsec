package br.unb.cic.rv.coverage;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PackageFilterTest {

    @Test
    void applicationClassesAreIncluded() {
        assertFalse(PackageFilter.isExcluded("Lcom/example/app/MainActivity;"));
        assertFalse(PackageFilter.isExcluded("Lbr/unb/cic/Foo;"));
    }

    @Test
    void frameworkAndRuntimeClassesAreExcluded() {
        assertTrue(PackageFilter.isExcluded("Ljava/util/ArrayList;"));
        assertTrue(PackageFilter.isExcluded("Ljavax/crypto/Cipher;"));
        assertTrue(PackageFilter.isExcluded("Landroid/app/Activity;"));
        assertTrue(PackageFilter.isExcluded("Landroidx/appcompat/app/AppCompatActivity;"));
        assertTrue(PackageFilter.isExcluded("Lkotlin/collections/CollectionsKt;"));
        assertTrue(PackageFilter.isExcluded("Lkotlinx/coroutines/Job;"));
        assertTrue(PackageFilter.isExcluded("Lmop/Coverage;"));
        assertTrue(PackageFilter.isExcluded("Lmop/MultiSpec_1MonitorAspect;"));
        assertTrue(PackageFilter.isExcluded("Ljavamoprt/Foo;"));
        assertTrue(PackageFilter.isExcluded("Lrvmonitorrt/Foo;"));
        assertTrue(PackageFilter.isExcluded("Lcom/google/android/gms/Foo;"));
    }

    @Test
    void innerLogSuffixIsExcluded() {
        // The $Log suffix filter matches inner classes named "Log" inside
        // another class (e.g. Outer$Log). Plain "Log" class names don't match
        // (they would be application code under com.example).
        assertTrue(PackageFilter.isExcluded("Lcom/example/app/Outer$Log;"));
    }

    @Test
    void plainLogClassNameIsIncluded() {
        // Outer class simply named "Log" (without the $ prefix) is user code —
        // not excluded. Only the inner-class form carries the framework-like
        // convention we filter out.
        assertFalse(PackageFilter.isExcluded("Lcom/example/app/Log;"));
    }

    @Test
    void nullClassIsConsideredExcluded() {
        // Defensive: don't propagate nulls; treat as "skip".
        assertTrue(PackageFilter.isExcluded(null));
    }

    // ------------------------------------------------------------------
    // INV-INS-53 boundary fidelity: each excluded prefix carries a trailing
    // slash (e.g. "Ljava/"), so a sibling package that merely SHARES the
    // leading letters ("Ljavafoo/") MUST NOT be swept up. This is the recall
    // guard the line-coverage number hides: dropping the trailing slash from a
    // prefix would silently exclude real application packages from RVSEC-COV.
    // ------------------------------------------------------------------

    @Test
    void prefixBoundaryDoesNotFalselyExcludeSiblingPackages() {
        // Each of these shares the excluded prefix's letters but breaks at the
        // slash boundary — they are APPLICATION code and MUST be included.
        assertFalse(PackageFilter.isExcluded("Ljavafoo/Bar;"),
                "Ljavafoo/ MUST NOT be excluded by the Ljava/ prefix (slash boundary)");
        assertFalse(PackageFilter.isExcluded("Ljavaxfoo/Bar;"),
                "Ljavaxfoo/ MUST NOT be excluded by the Ljavax/ prefix");
        assertFalse(PackageFilter.isExcluded("Lsunny/Bar;"),
                "Lsunny/ MUST NOT be excluded by the Lsun/ prefix");
        assertFalse(PackageFilter.isExcluded("Landroidfoo/Bar;"),
                "Landroidfoo/ MUST NOT be excluded by the Landroid/ prefix");
        assertFalse(PackageFilter.isExcluded("Lkotlinfoo/Bar;"),
                "Lkotlinfoo/ MUST NOT be excluded by the Lkotlin/ prefix");
        assertFalse(PackageFilter.isExcluded("Lcom/googlefoo/Bar;"),
                "Lcom/googlefoo/ MUST NOT be excluded by the Lcom/google/ prefix");
    }

    @Test
    void nonExcludedOrgAndComNamespacesAreIncluded() {
        // Lcom/ and Lorg/ are NOT blanket-excluded — only specific sub-namespaces
        // are. Arbitrary org/com application packages MUST survive the filter.
        assertFalse(PackageFilter.isExcluded("Lcom/example/App;"));
        assertFalse(PackageFilter.isExcluded("Lcom/squareup/okhttp/Client;"));
        assertFalse(PackageFilter.isExcluded("Lorg/example/Service;"));
        // apache is excluded ONLY for commons/geronimo — other apache subpackages
        // (e.g. an app bundling org.apache.http) are application code.
        assertFalse(PackageFilter.isExcluded("Lorg/apache/http/HttpClient;"),
                "Lorg/apache/http/ MUST NOT be excluded — only commons/geronimo are");
    }

    @Test
    void remainingExcludedPrefixesAreExcluded() {
        // The exclusion prefixes not asserted elsewhere — each must skip.
        assertTrue(PackageFilter.isExcluded("Lsun/security/ssl/SSLContextImpl;"));
        assertTrue(PackageFilter.isExcluded("Lcom/runtimeverification/rvmonitor/Foo;"));
        assertTrue(PackageFilter.isExcluded("Lorg/aspectj/lang/JoinPoint;"));
        assertTrue(PackageFilter.isExcluded("Lorg/apache/commons/lang3/StringUtils;"));
        assertTrue(PackageFilter.isExcluded("Lorg/apache/geronimo/mail/Foo;"));
        assertTrue(PackageFilter.isExcluded("Lnet/sf/cglib/proxy/Enhancer;"));
    }
}
