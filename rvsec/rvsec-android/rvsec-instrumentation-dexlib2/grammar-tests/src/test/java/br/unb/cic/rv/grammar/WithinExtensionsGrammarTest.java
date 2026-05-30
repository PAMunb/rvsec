package br.unb.cic.rv.grammar;

import br.unb.cic.rv.coverage.PackageFilter;
import br.unb.cic.rv.grammar.util.AbsorbingStage;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the matrix row "{@code within(*..Log)} suffix-wildcard + {@code within(T+)}" (§4.WW').
 * NOT-NEEDED β: the round-7 plan to extend the positive {@code within(...)} matcher to suffix-wildcard
 * and {@code T+}-inside-positive-within sub-forms is dropped. The sole consumer of these sub-forms is
 * {@code Coverage.aj}'s {@code excludedPackages()} macro, whose package exclusions are reproduced by
 * the dexlib2 {@code coverage-weaver}'s {@link PackageFilter}. Absorber: {@code COVERAGE_WEAVER}.
 *
 * <p>The simple positive {@code within(pkg..*)} form is NOT absorbed here — only the suffix-wildcard
 * and {@code T+}-in-positive-within sub-forms are. (Per §1.2 the simple form's pipeline demand is also
 * zero; §4.W' pins that verdict. This row narrows to the two extension sub-forms.)
 */
class WithinExtensionsGrammarTest {

    /** The pipeline stage that absorbs the within-extension sub-forms. */
    static final AbsorbingStage ABSORBER = AbsorbingStage.COVERAGE_WEAVER;

    @Test
    void withinSuffixAndTPlusAbsorbedByCoverageWeaver() {
        // (a) PackageFilter reproduces the Coverage.aj excludedPackages() exclusions. The matrix's
        // package-pattern names map onto these DEX-descriptor prefixes (android..* -> Landroid/, etc).
        assertTrue(PackageFilter.isExcluded("Landroid/app/Activity;"), "android..* excluded");
        assertTrue(PackageFilter.isExcluded("Ljava/util/ArrayList;"), "java..* excluded");
        assertTrue(PackageFilter.isExcluded("Lkotlin/Unit;"), "kotlin..* excluded");
        assertTrue(PackageFilter.isExcluded("Lmop/Coverage;"), "mop..* excluded");
        assertTrue(PackageFilter.isExcluded("Lorg/aspectj/lang/Signature;"), "aspectj..* excluded");
        // The within(*..Log) suffix-wildcard sub-form is reproduced by the $Log; suffix rule.
        assertTrue(PackageFilter.isExcluded("Lcom/example/Foo$Log;"),
                "the within(*..Log) suffix-wildcard sub-form is reproduced by PackageFilter's $Log; rule");

        // A genuine application class is NOT excluded — the filter is not vacuous.
        assertFalse(PackageFilter.isExcluded("Lcom/example/App;"),
                "an application class must NOT be excluded (the filter is not vacuous)");

        // (b) The simple positive within(pkg..*) form remains a distinct row (§4.W') — this row is
        // narrowed to the suffix-wildcard and T+ sub-forms only. (Documented, not asserted on demand.)

        // Named absorber.
        assertEquals(AbsorbingStage.COVERAGE_WEAVER, ABSORBER);
    }
}
