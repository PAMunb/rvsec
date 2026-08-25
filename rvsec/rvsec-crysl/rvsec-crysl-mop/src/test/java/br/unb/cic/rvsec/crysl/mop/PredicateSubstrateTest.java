package br.unb.cic.rvsec.crysl.mop;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Both predicate substrates, on the real files that use them.
 *
 * <p>The two witnesses are the same specification in two corpora: {@code jca/MacSpec.mop} on
 * {@code ExecutionContext} and {@code jca_android/MacSpec.mop} on {@code PredicateStore}. Reading
 * only one substrate would make one of the two corpora look predicate-free, and since the frozen
 * {@code jca} is the set the published measurements were taken over, the historical comparison
 * would silently compare a set with predicates against a set apparently without.
 */
class PredicateSubstrateTest {

    private final MopLifter lifter = new MopLifter();

    @Test
    @DisplayName("substrate A: jca/MacSpec.mop:73 is an arity-1 GENERATED_MAC ensure")
    void test_execution_context_ensure() throws LiftFailure {
        MopLift lift = lifter.read(Corpora.file("jca", "MacSpec.mop"), Corpora.version("jca"));

        List<PredicateSite> ensures = lift.predicateSites().stream()
                .filter(s -> s.kind() == PredicateSite.Kind.ENSURES)
                .filter(s -> s.ref().name().equals("GENERATED_MAC"))
                .toList();
        assertEquals(2, ensures.size(),
                "the file writes GENERATED_MAC in both f1 and f2; the references are held in a "
                        + "List and not a Set precisely so that two sites stay two sites");

        PredicateSite first = ensures.get(0);
        assertEquals(PredicateSite.Substrate.EXECUTION_CONTEXT, first.substrate());
        assertEquals(73, first.ref().site().line(),
                "ExecutionContext.instance().setProperty(Property.GENERATED_MAC, output)");
        assertEquals("MacSpec.mop", first.ref().site().file());
        assertEquals(1, first.ref().arguments().size(),
                "substrate A binds exactly one object per predicate: arity 1");
        assertEquals("output", first.ref().arguments().get(0));
        assertEquals(Polarity.POSITIVE, first.ref().polarity());
        assertEquals(Optional.empty(), first.verdict(),
                "substrate A answers a boolean; there is no PredicateVerdict to compare against");

        assertTrue(lift.model().ensures().stream()
                        .anyMatch(r -> r.name().equals("GENERATED_MAC") && r.site().line() == 73),
                "the reference reaches SpecModel.ensures with its file:line intact");
    }

    @Test
    @DisplayName("substrate A: validate is a REQUIRES, remove a NEGATES, and the ! is recorded")
    void test_execution_context_requires_and_negates() throws LiftFailure {
        MopLift lift = lifter.read(Corpora.file("jca", "MacSpec.mop"), Corpora.version("jca"));

        assertTrue(lift.model().requires().stream()
                        .anyMatch(r -> r.name().equals("GENERATED_KEY")),
                "condition(...validate(Property.GENERATED_KEY, key)) is a REQUIRES");
        assertTrue(lift.model().negates().stream()
                        .anyMatch(r -> r.name().equals("GENERATED_MAC")),
                "the @fail handler's remove(...) is a NEGATES");

        // The same requirement is written from the violating branch elsewhere in the corpus, and
        // the site records that the source negated it rather than inventing a predicate name.
        MopLift iv = lifter.read(Corpora.file("jca", "IvParameterSpec.mop"), Corpora.version("jca"));
        List<PredicateSite> negated = iv.predicateSites().stream()
                .filter(s -> s.ref().polarity() == Polarity.NEGATED)
                .toList();
        assertFalse(negated.isEmpty(), "condition(!...validate(Property.RANDOMIZED, iv))");
        assertEquals("RANDOMIZED", negated.get(0).ref().name(),
                "the name stays the bare property constant; encoding the ! into it would invent a "
                        + "predicate no CrySL rule declares");
    }

    @Test
    @DisplayName("substrate B: jca_android/MacSpec.mop is a negated REQUIRES on the three-valued store")
    void test_predicate_store_validate_absent() throws LiftFailure {
        MopLift lift = lifter.read(Corpora.file("jca_android", "MacSpec.mop"),
                Corpora.version("jca_android"));

        List<PredicateSite> absent = lift.predicateSites().stream()
                .filter(s -> s.substrate() == PredicateSite.Substrate.PREDICATE_STORE)
                .filter(s -> s.ref().polarity() == Polarity.NEGATED)
                .toList();
        assertEquals(1, absent.size(), "the file makes exactly one validateAbsent call");

        PredicateSite site = absent.get(0);
        assertEquals(PredicateSite.Kind.REQUIRES, site.kind(),
                "validateAbsent is the CrySL !p[...] of a REQUIRES clause, not a NEGATES: NEGATES "
                        + "is the rule withdrawing a predicate it ensured");
        assertEquals(Polarity.NEGATED, site.ref().polarity(),
                "validateAbsent is the CrySL !p[...]: the reference asks for the absence of "
                        + "ENCRYPTED, and M4 compares that against Mac.crysl:51");
        assertEquals("ENCRYPTED", site.ref().name());
        assertEquals(List.of("output"), site.ref().arguments());
        assertEquals(Optional.of("VIOLATED"), site.verdict(),
                "the three-valued verdict is compared on the call itself here");
        // The call is on line 307. The task file cited :303, which is the line the enclosing
        // "event f2" is declared on; provenance is stamped at the reference, not at the event that
        // contains it, so 307 is what a reader following the file:line will find.
        assertEquals(307, site.ref().site().line());
        assertEquals("MacSpec.mop", site.ref().site().file());
    }

    @Test
    @DisplayName("substrate B: ensure carries arity beyond 1, which substrate A cannot express")
    void test_predicate_store_multi_arity_ensure() throws LiftFailure {
        MopLift lift = lifter.read(Corpora.file("jca_android", "KeyGeneratorSpec.mop"),
                Corpora.version("jca_android"));

        List<PredicateRef> multi = lift.predicateSites().stream()
                .filter(s -> s.kind() == PredicateSite.Kind.ENSURES)
                .map(PredicateSite::ref)
                .filter(r -> r.arguments().size() >= 2)
                .toList();
        assertFalse(multi.isEmpty(),
                "ensure(Property.GENERATED_KEY, generatedKey, generatedKeyAlgorithm) is arity 2; "
                        + "substrate A's setProperty has no room for the second argument, which is "
                        + "why the two substrates are not interchangeable");
        assertTrue(lift.predicateSites().stream()
                        .allMatch(s -> s.substrate() == PredicateSite.Substrate.PREDICATE_STORE),
                "the current jca_android is entirely on substrate B");
    }

    @Test
    @DisplayName("the frozen jca is entirely on substrate A, which is why it may not be deleted")
    void test_frozen_jca_is_substrate_a() throws LiftFailure {
        int executionContextSites = 0;
        int predicateStoreSites = 0;
        for (var file : Corpora.filesOf("jca")) {
            MopLift lift = lifter.read(file, Corpora.version("jca"));
            for (PredicateSite site : lift.predicateSites()) {
                if (site.substrate() == PredicateSite.Substrate.EXECUTION_CONTEXT) {
                    executionContextSites++;
                } else {
                    predicateStoreSites++;
                }
            }
        }
        assertEquals(0, predicateStoreSites, "the frozen set never adopted PredicateStore");
        assertTrue(executionContextSites > 0,
                "if this ever reaches 0, substrate A is genuinely dead and may be deleted; until "
                        + "then, the set the published measurements were taken over needs it");
    }

    @Test
    @DisplayName("a commented-out idiom is not a predicate reference")
    void test_comments_are_not_counted() throws LiftFailure {
        MopLift lift = lifter.read(Corpora.file("jca_android", "MacSpec.mop"),
                Corpora.version("jca_android"));
        // MacSpec.mop:254 is prose naming validateAbsent thirteen lines above the only real call.
        assertTrue(lift.predicateSites().stream().noneMatch(s -> s.ref().site().line() == 254),
                "SourceText blanks comments before the scan; without that, the file would report a "
                        + "predicate reference it does not make");
    }

    @Test
    @DisplayName("accepting-state marks are recognised and kept out of ENSURES")
    void test_accepting_state_marks_are_not_predicates() throws LiftFailure {
        MopLift lift = lifter.read(Corpora.file("jca", "MacSpec.mop"), Corpora.version("jca"));

        assertEquals(1, lift.acceptingStateMarks().size());
        PredicateIdioms.AcceptingStateMark mark = lift.acceptingStateMarks().get(0);
        assertTrue(mark.set());
        assertEquals("mac", mark.object());
        assertEquals(92, mark.site().line());

        assertTrue(lift.model().ensures().stream().noneMatch(r -> r.name().contains("Accepting")),
                "the mark is the guard CrySL puts on ENSURES, not an ENSURES; counting it as one "
                        + "would move M4's denominator");
    }
}
