package br.unb.cic.rv.coverage;

import java.util.Arrays;
import java.util.List;

/**
 * Canonical exclusion filter for the Coverage catch-all weaver.
 *
 * <p>Matches the filter baked into the legacy {@code Coverage.aj} so that
 * {@code RVSEC-COV} recall stays equivalent across the {@code ajc} and
 * {@code dexlib2} variants (INV-INS-60 / Layer-5 gate).
 *
 * <p>Excluded prefixes cover the runtime, the generated monitor namespace,
 * and the Android/Kotlin/Google support libraries — any method inside these
 * is skipped, matching what {@code Coverage.aj} does.
 *
 * <p>Spec-set agnostic: the same exclusions apply whether the weave is for
 * the JCA or Generic specification set.
 */
public final class PackageFilter {

    private static final List<String> EXCLUDED_PREFIXES = Arrays.asList(
            "Ljava/",
            "Ljavax/",
            "Lsun/",
            "Landroid/",
            "Landroidx/",
            "Lkotlin/",
            "Lkotlinx/",
            "Lmop/",
            "Ljavamoprt/",
            "Lrvmonitorrt/",
            "Lcom/runtimeverification/",
            "Lcom/google/",
            "Lorg/aspectj/",
            "Lorg/apache/commons/",
            "Lorg/apache/geronimo/",
            "Lnet/sf/cglib/"
    );

    private static final List<String> EXCLUDED_SUFFIXES = Arrays.asList(
            "$Log;"  // convention: logging helpers end in ..Log; these are not user methods.
    );

    private PackageFilter() {}

    /**
     * @return true when the class descriptor belongs to an excluded package;
     *         such classes are skipped by the coverage catch-all.
     */
    public static boolean isExcluded(String classDescriptor) {
        if (classDescriptor == null) return true;
        for (String prefix : EXCLUDED_PREFIXES) {
            if (classDescriptor.startsWith(prefix)) return true;
        }
        for (String suffix : EXCLUDED_SUFFIXES) {
            if (classDescriptor.endsWith(suffix)) return true;
        }
        return false;
    }
}
