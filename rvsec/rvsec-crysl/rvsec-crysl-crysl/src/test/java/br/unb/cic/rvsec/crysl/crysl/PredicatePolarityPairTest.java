package br.unb.cic.rvsec.crysl.crysl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Version;
import br.unb.cic.rvsec.crysl.mop.MopLifter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * The one pair of the two corpora that says the same negated thing on both sides, read end to end.
 *
 * <p>{@code Mac.crysl:51} requires {@code !encrypted[output1, _]} — the MAC may not be taken over
 * something already encrypted — and {@code jca_android/MacSpec.mop:307} implements exactly that,
 * as {@code validateAbsent(Property.ENCRYPTED, output) == PredicateVerdict.VIOLATED}. Both sides
 * demand the <em>absence</em> of the predicate, and this is the only place in either corpus where a
 * {@code REQUIRES} entry does.
 *
 * <p>This is the pair that made the defect invisible. Before polarity existed, both lifters dropped
 * the signal — the CrySL {@code !} and the {@code Absent} of the method name — and the two models
 * agreed for the wrong reason: they agreed on {@code encrypted} being <em>required to hold</em>,
 * which is the opposite of what either artifact says, and M4 would have called it conformant.
 * Eyeballing the output could never reveal that, because the two errors cancel. So the assertion
 * has to be that both sides read {@link Polarity#NEGATED}, and that a side whose polarity is
 * flipped stops matching — the second test is what proves the first is not vacuous.
 *
 * <p>The pairing here is by hand and by name, on one known pair. It is a regression test for the
 * lift, not an implementation of M4: M4 pairs by declared type and compares whole sections.
 */
@Tag(OracleCorpus.TAG)
class PredicatePolarityPairTest {

    /** The specification side, read from the working tree of the sibling {@code rvsec-mop}. */
    private static final Path MOP_SPEC = Paths.get("..", "..", "rvsec-mop", "src", "main",
            "resources", "jca_android", "MacSpec.mop").normalize();

    private static final String CRYSL_PREDICATE = "encrypted";
    private static final String MOP_PROPERTY = "ENCRYPTED";

    @Test
    @DisplayName("RISK-017: Mac.crysl:51 and jca_android/MacSpec.mop:307 both lift to NEGATED")
    void test_the_negated_pair_is_negated_on_both_sides() throws LiftFailure {
        PredicateRef rule = cryslRequirement();
        PredicateRef specification = mopRequirement();

        assertEquals(Polarity.NEGATED, rule.polarity(),
                "Mac.crysl:51 is '!encrypted[output1, _]': the rule demands the predicate be "
                        + "absent, and dropping the ! inverts the requirement");
        assertEquals(Polarity.NEGATED, specification.polarity(),
                "MacSpec.mop:307 is validateAbsent(Property.ENCRYPTED, output): the specification "
                        + "demands the same absence");
        assertEquals(rule.polarity(), specification.polarity(),
                "the two artifacts agree, and they now agree for the reason they are written "
                        + "rather than because both lifts lost the same signal");
    }

    @Test
    @DisplayName("RISK-017: flipping one side's polarity makes the pair disagree")
    void test_flipping_one_side_makes_the_pair_disagree() throws LiftFailure {
        PredicateRef rule = cryslRequirement();
        PredicateRef specification = mopRequirement();

        // The same reference with the opposite polarity: a .mop that had written validate(...)
        // where the rule writes !encrypted[...] — a specification demanding the predicate hold
        // where the rule demands it be absent. That is the inversion M4 exists to report, and the
        // model must be able to tell it apart from the pair above.
        Polarity flipped = specification.polarity() == Polarity.NEGATED
                ? Polarity.POSITIVE : Polarity.NEGATED;
        PredicateRef inverted = new PredicateRef(specification.name(), specification.arguments(),
                flipped, specification.site());

        assertNotEquals(rule.polarity(), inverted.polarity(),
                "with polarity on the reference, an inverted specification is distinguishable "
                        + "from the conformant one; without it, both read the same");
        assertNotEquals(specification, inverted,
                "polarity participates in the record's identity, so the two references are not "
                        + "the same edge of the M4 graph");
    }

    @Test
    @DisplayName("polarity is per reference, not per section: Mac.crysl REQUIRES holds both")
    void test_polarity_varies_inside_one_requires_block() throws LiftFailure {
        SpecModel rule = liftRule();

        List<PredicateRef> negated = rule.requires().stream()
                .filter(ref -> ref.polarity() == Polarity.NEGATED)
                .toList();
        List<PredicateRef> positive = rule.requires().stream()
                .filter(ref -> ref.polarity() == Polarity.POSITIVE)
                .toList();

        assertEquals(2, negated.size(),
                "Mac.crysl requires !encrypted twice, at :51 and :52; counting rule = entries of "
                        + "getRequiredPredicates() whose isNegated() is true");
        assertTrue(negated.stream().allMatch(ref -> ref.name().equals(CRYSL_PREDICATE)),
                "the name stays bare: '" + CRYSL_PREDICATE + "', never '!" + CRYSL_PREDICATE
                        + "', or M4's pairing would miss the predicate the ENSURES side writes");
        assertFalse(positive.isEmpty(),
                "preparedHMAC[params] and generatedKey[key,_] sit in the same block, so the block "
                        + "cannot carry the polarity for its entries");

        assertTrue(rule.negates().isEmpty(),
                "Mac.crysl declares no NEGATES section; a negated requirement filed there would "
                        + "claim a clause the rule does not have");
    }

    private static PredicateRef cryslRequirement() throws LiftFailure {
        Optional<PredicateRef> found = liftRule().requires().stream()
                .filter(ref -> ref.name().equals(CRYSL_PREDICATE))
                .findFirst();
        assertTrue(found.isPresent(), "Mac.crysl no longer requires '" + CRYSL_PREDICATE
                + "'; the upstream corpus moved and this pair has to be re-chosen");
        return found.get();
    }

    private static SpecModel liftRule() throws LiftFailure {
        return new CryslLifter().lift(OracleCorpus.cryslRules().resolve("Mac.crysl"),
                OracleCorpus.version());
    }

    private static PredicateRef mopRequirement() throws LiftFailure {
        Assumptions.assumeTrue(Files.isReadable(MOP_SPEC),
                "the .mop corpus is read from the sibling rvsec-mop module at "
                        + MOP_SPEC.toAbsolutePath() + "; the working directory of the test must be "
                        + "the module base directory");
        SpecModel specification = new MopLifter().lift(MOP_SPEC,
                new Version("jca_android", new SourceStamp("rvsec", "working-tree", Instant.EPOCH)));
        Optional<PredicateRef> found = specification.requires().stream()
                .filter(ref -> ref.name().equals(MOP_PROPERTY))
                .findFirst();
        assertTrue(found.isPresent(), "jca_android/MacSpec.mop no longer requires '" + MOP_PROPERTY
                + "'; the specification moved and this pair has to be re-chosen");
        return found.get();
    }
}
