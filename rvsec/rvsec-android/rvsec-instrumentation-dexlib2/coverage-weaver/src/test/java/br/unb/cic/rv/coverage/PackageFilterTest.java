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
}
