package br.unb.cic.rvsec.crysl.core.metric;

import static br.unb.cic.rvsec.crysl.core.metric.M4Fixtures.clause;
import static br.unb.cic.rvsec.crysl.core.metric.M4Fixtures.rule;
import static br.unb.cic.rvsec.crysl.core.metric.M4Fixtures.site;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.emit.CsvEmitter;
import br.unb.cic.rvsec.crysl.core.metric.PredicateSiteFacts.Section;
import br.unb.cic.rvsec.crysl.core.metric.PredicateSiteFacts.SiteKind;
import br.unb.cic.rvsec.crysl.core.model.ObjectDecl;
import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * What M4 compares, and what it refuses to claim.
 *
 * <p>Each test names one of the three things the comparison is over - arity, polarity, argument
 * position - or one of the two disciplines the report is held to: an aggregate that describes the
 * rows printed beneath it, and a fidelity class that says whether a person or this metric decided
 * it.
 */
class M4PredicatesTest {

    private final M4Predicates metric = new M4Predicates();

    // ── 9.1 arity, polarity, argument position ────────────────────────────────────────────────

    @Test
    @DisplayName("a site and a clause agreeing on arity and polarity is a present edge, FIEL")
    void test_matching_site_and_clause_is_present_and_fiel() {
        SpecModel rule = rule(List.of(new ObjectDecl("javax.crypto.SecretKey", "key")),
                List.of(clause("generatedKey", Polarity.POSITIVE, 174, "key")),
                List.of(), List.of());
        PredicateSiteFacts write = site(Section.ENSURES, PredicateSubstrate.PREDICATE_STORE,
                "match1", SiteKind.MATCH, "GENERATED_KEY", Polarity.POSITIVE, 292,
                List.of("Key"), "key");

        M4Predicates.M4Analysis analysis = compare(rule, List.of(write));

        assertEquals(1, analysis.result().present().size(),
                "the two pair on name, section, arity and polarity");
        assertTrue(analysis.result().absent().isEmpty(), "the only clause of the rule was matched");
        assertTrue(analysis.result().inverted().isEmpty(), "nothing disagreed");
        assertEquals(CsvEmitter.Fidelity.FIEL, analysis.rows().get(0).fidelity());
        assertEquals(CsvEmitter.Origin.DERIVED, analysis.rows().get(0).origin(),
                "GENERATED_KEY canonicalises onto generatedKey, so no person made this pairing");
    }

    @Test
    @DisplayName("arity: a clause of arity 2 implemented over one object is PROJETADO, not absent")
    void test_lower_arity_is_a_projection() {
        SpecModel rule = rule(
                List.of(new ObjectDecl("javax.crypto.SecretKey", "key"),
                        new ObjectDecl("java.lang.String", "transformation")),
                List.of(clause("generatedKey", Polarity.POSITIVE, 174, "key", "transformation")),
                List.of(), List.of());
        PredicateSiteFacts write = site(Section.ENSURES, PredicateSubstrate.PREDICATE_STORE,
                "match1", SiteKind.MATCH, "GENERATED_KEY", Polarity.POSITIVE, 292,
                List.of("Key"), "key");

        M4Predicates.M4Analysis analysis = compare(rule, List.of(write));

        assertEquals(1, analysis.result().present().size(),
                "the predicate is there; what differs is how much of the clause it carries");
        assertEquals(CsvEmitter.Fidelity.PROJETADO, analysis.rows().get(0).fidelity());
        assertTrue(analysis.rows().get(0).reason().contains("arity 2"),
                "the row names the arity the rule states, so the projection is checkable");
    }

    @Test
    @DisplayName("polarity: REQUIRES p against REQUIRES !p is an inverted edge, never a present one")
    void test_opposite_polarity_is_inverted() {
        SpecModel rule = rule(List.of(new ObjectDecl("byte[]", "output1")), List.of(),
                List.of(clause("encrypted", Polarity.NEGATED, 51, "output1")), List.of());
        PredicateSiteFacts read = site(Section.REQUIRES, PredicateSubstrate.PREDICATE_STORE,
                "f5", SiteKind.BODY, "ENCRYPTED", Polarity.POSITIVE, 307,
                List.of("byte[]"), "output");

        M4Predicates.M4Analysis analysis = compare(rule, List.of(read));

        assertEquals(1, analysis.result().inverted().size(),
                "the rule demands the predicate be absent and the site demands it hold");
        assertTrue(analysis.result().present().isEmpty(),
                "without polarity on the reference the two would have agreed for the wrong reason");
        assertEquals(CsvEmitter.Fidelity.AUSENTE, analysis.rows().get(0).fidelity(),
                "the clause the rule states is not implemented; its inverse is");
        assertEquals("read:body", analysis.rows().get(0).verdict(),
                "the site-level vocabulary describes the site, which is a positive read");
    }

    @Test
    @DisplayName("argument position: the same types in a different order is an inverted edge")
    void test_permuted_argument_positions_are_inverted() {
        SpecModel rule = rule(
                List.of(new ObjectDecl("javax.crypto.SecretKey", "key"),
                        new ObjectDecl("byte[]", "plainText")),
                List.of(clause("encrypted", Polarity.POSITIVE, 191, "key", "plainText")),
                List.of(), List.of());
        PredicateSiteFacts write = site(Section.ENSURES, PredicateSubstrate.PREDICATE_STORE,
                "match1", SiteKind.MATCH, "ENCRYPTED", Polarity.POSITIVE, 292,
                List.of("byte[]", "SecretKey"), "plain", "k");

        M4Predicates.M4Analysis analysis = compare(rule, List.of(write));

        assertEquals(1, analysis.result().inverted().size(),
                "equal multisets in a different order cannot be a naming difference");
        assertTrue(analysis.rows().get(0).reason().contains("different order"),
                "the row says which positions, so the finding is actionable");
    }

    @Test
    @DisplayName("a clause no site implements is an absent edge with a row of its own")
    void test_unimplemented_clause_is_absent() {
        SpecModel rule = rule(List.of(new ObjectDecl("javax.crypto.SecretKey", "key")),
                List.of(clause("generatedKey", Polarity.POSITIVE, 174, "key")),
                List.of(clause("randomized", Polarity.POSITIVE, 180, "key")), List.of());
        PredicateSiteFacts write = site(Section.ENSURES, PredicateSubstrate.PREDICATE_STORE,
                "match1", SiteKind.MATCH, "GENERATED_KEY", Polarity.POSITIVE, 292,
                List.of("Key"), "key");

        M4Predicates.M4Analysis analysis = compare(rule, List.of(write));

        assertEquals(1, analysis.result().absent().size(), "randomized is required and never read");
        assertEquals(2, analysis.rows().size(),
                "one row per site plus one per clause no site implements");
        CsvEmitter.M4Row absence = analysis.rows().get(1);
        assertEquals("absent", absence.disposition());
        assertEquals(CsvEmitter.Fidelity.AUSENTE, absence.fidelity());
        assertEquals(CsvEmitter.Origin.DERIVED, absence.origin(),
                "nobody had to judge that a clause with no site is not implemented");
    }

    // ── 9.9 a REQUIRES with no reachable producer ─────────────────────────────────────────────

    @Test
    @DisplayName("9.9: a REQUIRES whose predicate nothing writes is found from the graph")
    void test_read_with_no_reachable_producer() {
        PredicateSiteFacts orphan = site(Section.REQUIRES, PredicateSubstrate.PREDICATE_STORE,
                "c1", SiteKind.BODY, "RANDOMIZED", Polarity.POSITIVE, 38, List.of(), "password");
        PredicateSiteFacts unrelated = site(Section.ENSURES, PredicateSubstrate.PREDICATE_STORE,
                "match", SiteKind.MATCH, "SPECCED_KEY", Polarity.POSITIVE, 42, List.of(), "spec");

        PredicateGraph graph = PredicateGraph.of(List.of(orphan, unrelated));

        assertEquals(List.of(orphan), graph.orphanReads(),
                "no site of the graph writes RANDOMIZED, so the read answers the same thing on "
                        + "every trace and the clause it translates cannot be violated");
        assertEquals(List.of(unrelated), graph.deadEndWrites(),
                "and the dual: a write nothing reads changes no verdict");
        assertFalse(graph.hasProducer("RANDOMIZED"));
        assertTrue(graph.hasProducer("specced_key"),
                "the reachability question is asked under the canonical name rule");
    }

    // ── 9.10 the known propagation bridge ─────────────────────────────────────────────────────

    @Test
    @DisplayName("9.10: byte[] written, char[] read through String.valueOf(Object).toCharArray()")
    void test_propagation_bridge_across_the_type_conversion() {
        PredicateSiteFacts producer = new PredicateSiteFacts("SecureRandomSpec.mop",
                Section.ENSURES, PredicateSubstrate.PREDICATE_STORE, "nb1", SiteKind.BODY,
                java.util.Optional.empty(), List.of("byte[]"),
                new PredicateRef("RANDOMIZED", List.of("bytes"), Polarity.POSITIVE,
                        new br.unb.cic.rvsec.crysl.core.model.Provenance("SecureRandomSpec.mop", 90)));
        PredicateSiteFacts consumer = new PredicateSiteFacts("PBEKeySpecSpec.mop",
                Section.REQUIRES, PredicateSubstrate.PREDICATE_STORE, "c1", SiteKind.BODY,
                java.util.Optional.empty(), List.of("char[]"),
                new PredicateRef("RANDOMIZED",
                        List.of("String.valueOf(obj).toCharArray()"), Polarity.POSITIVE,
                        new br.unb.cic.rvsec.crysl.core.model.Provenance("PBEKeySpecSpec.mop", 38)));

        List<PropagationBridge> bridges =
                PredicateGraph.of(List.of(producer, consumer)).bridges();

        assertEquals(2, bridges.size(), "both routes decide this edge, and each is reported once");
        PropagationBridge byType = bridges.stream()
                .filter(bridge -> bridge.cause() == PropagationBridge.Cause.INCOMPATIBLE_TYPES)
                .findFirst().orElseThrow();
        assertTrue(byType.detail().contains("byte[]") && byType.detail().contains("char[]"),
                "the finding names the type incompatibility rather than asserting a break");
        PropagationBridge byIdentity = bridges.stream()
                .filter(bridge -> bridge.cause() == PropagationBridge.Cause.RECREATED_VALUE)
                .findFirst().orElseThrow();
        assertTrue(byIdentity.detail().contains("IDENTITY"),
                "identity keying over a recreated value cannot carry the predicate");
        assertEquals("SecureRandomSpec.mop:90", byType.producer().ref().site().toString());
        assertEquals("PBEKeySpecSpec.mop:38", byType.consumer().ref().site().toString());
    }

    @Test
    @DisplayName("a negated read is not reported as a broken bridge: absence is what it asked for")
    void test_negated_reads_are_not_bridges() {
        PredicateSiteFacts producer = new PredicateSiteFacts("MacSpec.mop", Section.ENSURES,
                PredicateSubstrate.PREDICATE_STORE, "match", SiteKind.MATCH,
                java.util.Optional.empty(), List.of("byte[]"),
                new PredicateRef("MACED", List.of("out"), Polarity.POSITIVE,
                        new br.unb.cic.rvsec.crysl.core.model.Provenance("MacSpec.mop", 366)));
        PredicateSiteFacts consumer = new PredicateSiteFacts("CipherSpec.mop", Section.REQUIRES,
                PredicateSubstrate.PREDICATE_STORE, "f5", SiteKind.BODY,
                java.util.Optional.empty(), List.of("char[]"),
                new PredicateRef("MACED", List.of("plain"), Polarity.NEGATED,
                        new br.unb.cic.rvsec.crysl.core.model.Provenance("CipherSpec.mop", 158)));

        assertTrue(PredicateGraph.of(List.of(producer, consumer)).bridges().isEmpty(),
                "a write that never reaches a validateAbsent makes it answer 'absent', which is "
                        + "what it demanded; that is a different finding and gets a different name");
    }

    // ── 9.3 the structural ceiling of substrate A ─────────────────────────────────────────────

    @Test
    @DisplayName("9.3: on ExecutionContext a clause of arity 2 is inexpressible, however written")
    void test_substrate_a_arity_ceiling() {
        PredicateRef arityTwo = clause("generatedKey", Polarity.POSITIVE, 174, "key", "alg");

        assertFalse(PredicateSubstrate.EXECUTION_CONTEXT.canExpress(arityTwo),
                "substrate A binds one object per predicate: there is no second position");
        assertTrue(PredicateSubstrate.PREDICATE_STORE.canExpress(arityTwo));
        assertEquals(PredicateSubstrate.Ceiling.Kind.INEXPRESSIBLE,
                PredicateSubstrate.EXECUTION_CONTEXT.ceiling(arityTwo).orElseThrow().kind());
    }

    @Test
    @DisplayName("9.3: a negated clause on ExecutionContext is DEGRADED, not inexpressible")
    void test_substrate_a_negation_is_a_projection_not_an_absence() {
        PredicateRef negated = clause("encrypted", Polarity.NEGATED, 51, "output1");

        PredicateSubstrate.Ceiling ceiling =
                PredicateSubstrate.EXECUTION_CONTEXT.ceiling(negated).orElseThrow();

        assertEquals(PredicateSubstrate.Ceiling.Kind.DEGRADED, ceiling.kind(),
                "jca/PBEKeySpecSpec.mop:56 writes condition(!validate(...)), so the demand is "
                        + "written; what the boolean substrate loses is the third value");
        assertTrue(PredicateSubstrate.EXECUTION_CONTEXT.canExpress(negated),
                "calling it inexpressible would contradict a file of the frozen corpus");
        assertTrue(PredicateSubstrate.PREDICATE_STORE.ceiling(negated).isEmpty(),
                "substrate B has validateAbsent and a third value, so it costs the clause nothing");
    }

    @Test
    @DisplayName("9.3: a negated read on substrate A pairs, and pairs as a projection")
    void test_negated_read_on_substrate_a_is_projetado() {
        SpecModel rule = rule(List.of(new ObjectDecl("byte[]", "output1")), List.of(),
                List.of(clause("encrypted", Polarity.NEGATED, 51, "output1")), List.of());
        PredicateSiteFacts read = site(Section.REQUIRES, PredicateSubstrate.EXECUTION_CONTEXT,
                "f5", SiteKind.BODY, "ENCRYPTED", Polarity.NEGATED, 307, List.of(), "output");

        M4Predicates.M4Analysis analysis = compare(rule, List.of(read));

        assertEquals(CsvEmitter.Fidelity.PROJETADO, analysis.rows().get(0).fidelity());
        assertEquals("read-absent:body", analysis.rows().get(0).verdict());
        assertTrue(analysis.rows().get(0).reason().contains("never written"),
                "the row states the three-valued collapse rather than implying faithfulness");
    }

    @Test
    @DisplayName("9.3: the ceiling of an absent clause names the substrate, not the author")
    void test_absent_clause_on_substrate_a_names_the_ceiling() {
        SpecModel rule = rule(
                List.of(new ObjectDecl("javax.crypto.SecretKey", "key"),
                        new ObjectDecl("java.lang.String", "alg")),
                List.of(clause("generatedKey", Polarity.POSITIVE, 174, "key", "alg")),
                List.of(), List.of());
        PredicateSiteFacts unrelated = site(Section.ENSURES, PredicateSubstrate.EXECUTION_CONTEXT,
                "match", SiteKind.MATCH, "DIGESTED", Polarity.POSITIVE, 100, List.of(), "out");

        M4Predicates.M4Analysis analysis = compare(rule, List.of(unrelated));

        CsvEmitter.M4Row absence = analysis.rows().get(1);
        assertTrue(absence.reason().contains("inexpressible"),
                "the clause is absent because the substrate cannot state it");
        assertTrue(absence.reason().contains("not of the specification's author"));
        assertEquals(1, analysis.ceilings().size(),
                "the ceiling is also carried as a finding of its own, with the clause named");
    }

    // ── 9.4 / 9.4-bis two vocabularies, and an aggregate held to its rows ─────────────────────

    @Test
    @DisplayName("9.4: every row carries the site vocabulary and the clause vocabulary at once")
    void test_both_vocabularies_travel_in_the_same_row() {
        SpecModel rule = rule(List.of(new ObjectDecl("javax.crypto.SecretKey", "key")),
                List.of(clause("generatedKey", Polarity.POSITIVE, 174, "key")), List.of(),
                List.of());
        PredicateSiteFacts write = site(Section.ENSURES, PredicateSubstrate.PREDICATE_STORE,
                "match1", SiteKind.MATCH, "GENERATED_KEY", Polarity.POSITIVE, 292,
                List.of("Key"), "key");
        PredicateSiteFacts read = site(Section.REQUIRES, PredicateSubstrate.PREDICATE_STORE,
                "i2", SiteKind.BODY, "GENERATED_KEY", Polarity.POSITIVE, 158, List.of("Key"), "k");

        M4Predicates.M4Analysis analysis = compare(rule, List.of(write, read));

        CsvEmitter.M4Row writeRow = analysis.rows().get(0);
        assertEquals("write:acceptance", writeRow.verdict(), "site vocabulary: where and what");
        assertEquals("n/a", writeRow.automatonMembership(), "a @match handler is not a letter");
        assertEquals(CsvEmitter.Fidelity.FIEL, writeRow.fidelity(), "clause vocabulary: how faithful");
        assertEquals("member", analysis.rows().get(1).automatonMembership(),
                "an event body is a letter of the order automaton");
        assertEquals("store", writeRow.mechanism(),
                "the mechanism column names the substrate that carries the site");
    }

    @Test
    @DisplayName("9.4-bis: the aggregate is held to the rows the emitter is handed")
    void test_aggregate_agrees_with_its_own_rows() {
        SpecModel rule = rule(List.of(new ObjectDecl("javax.crypto.SecretKey", "key")),
                List.of(clause("generatedKey", Polarity.POSITIVE, 174, "key")), List.of(),
                List.of());
        PredicateSiteFacts write = site(Section.ENSURES, PredicateSubstrate.PREDICATE_STORE,
                "match1", SiteKind.MATCH, "GENERATED_KEY", Polarity.POSITIVE, 292,
                List.of("Key"), "key");

        M4Predicates.M4Analysis analysis = compare(rule, List.of(write));

        assertEquals(analysis.rows().size(),
                analysis.result().derivedRows() + analysis.result().inheritedRows(),
                "the two counts of the aggregate are counts of these rows and of nothing else");

        M4Result skewed = new M4Result(analysis.result().specification(),
                analysis.result().rule(), analysis.result().present(), analysis.result().absent(),
                analysis.result().inverted(), analysis.result().derivedRows() + 1,
                analysis.result().inheritedRows(), analysis.result().refusals(),
                analysis.result().countingRule());
        IllegalStateException thrown = assertThrows(IllegalStateException.class,
                () -> new M4Predicates.M4Analysis(skewed, analysis.rows(), analysis.compared(),
                        analysis.bridges(), analysis.ceilings()));
        assertTrue(thrown.getMessage().contains("disagrees with its own rows"),
                "an aggregate that does not describe the table beneath it must not be emitted");
    }

    // ── 9.5 derived and inherited ─────────────────────────────────────────────────────────────

    @Test
    @DisplayName("9.5: a pairing a person supplied makes the row inherited, not derived")
    void test_alias_paired_rows_are_inherited() {
        SpecModel rule = rule(List.of(new ObjectDecl("byte[]", "out")),
                List.of(clause("macced", Polarity.POSITIVE, 60, "out")), List.of(), List.of());
        PredicateSiteFacts write = site(Section.ENSURES, PredicateSubstrate.PREDICATE_STORE,
                "match", SiteKind.MATCH, "MACED", Polarity.POSITIVE, 366, List.of("byte[]"), "out");

        M4Predicates.M4Analysis derived = compare(rule, List.of(write));
        assertEquals(CsvEmitter.Origin.INHERITED, derived.rows().get(0).origin(),
                "MACED does not canonicalise onto macced, so with no alias there is no pairing");
        assertEquals(2, derived.rows().size(),
                "the site pairs with nothing and the clause is implemented by nothing, so both "
                        + "get a row and neither is folded into the other");
        assertEquals(0.5, derived.derivedFraction(), 1e-9,
                "the absence row is derived; the unpaired site row is not");

        M4Predicates.M4Analysis aliased = metric.compare("CipherSpec.mop", "Mac.crysl",
                List.of(write), rule, PredicateGraph.of(List.of(write)),
                new M4Predicates.Judgements(Map.of("MACED", "macced"), Map.of()));
        assertEquals(CsvEmitter.Origin.INHERITED, aliased.rows().get(0).origin(),
                "the alias pairs them, and the row stays inherited because a person paired them: "
                        + "the derived fraction must not rise by being handed more judgement");
        assertEquals(CsvEmitter.Fidelity.FIEL, aliased.rows().get(0).fidelity());
        assertEquals(1, aliased.result().present().size());
    }

    @Test
    @DisplayName("9.5: the derived fraction is computable from the origin column alone")
    void test_derived_fraction() {
        SpecModel rule = rule(List.of(new ObjectDecl("javax.crypto.SecretKey", "key")),
                List.of(clause("generatedKey", Polarity.POSITIVE, 174, "key")), List.of(),
                List.of());
        PredicateSiteFacts paired = site(Section.ENSURES, PredicateSubstrate.PREDICATE_STORE,
                "match1", SiteKind.MATCH, "GENERATED_KEY", Polarity.POSITIVE, 292, List.of(), "key");
        PredicateSiteFacts unpaired = site(Section.ENSURES, PredicateSubstrate.PREDICATE_STORE,
                "match2", SiteKind.MATCH, "DIGESTED", Polarity.POSITIVE, 300, List.of(), "out");

        M4Predicates.M4Analysis analysis = compare(rule, List.of(paired, unpaired));

        assertEquals(2, analysis.rows().size());
        assertEquals(1, analysis.result().derivedRows());
        assertEquals(1, analysis.result().inheritedRows());
        assertEquals(0.5, analysis.derivedFraction(), 1e-9);
        assertEquals(1L, analysis.derivedScalars().get(CsvEmitter.Fidelity.FIEL));
        assertEquals(0L, analysis.derivedScalars().get(CsvEmitter.Fidelity.AUSENTE),
                "the inherited AUSENTE row is not counted in a scalar published about the corpus");
    }

    // ── 9.7 / 9.8 the stamp and the four parcels ──────────────────────────────────────────────

    @Test
    @DisplayName("9.7: the counting rule carries the substrate trajectory and its own rule")
    void test_counting_rule_carries_the_trajectory() {
        assertTrue(M4Predicates.COUNTING_RULE.contains("64/21/5 (d64f3a40)"));
        assertTrue(M4Predicates.COUNTING_RULE.contains("0/70/21 (5fbe8173)"));
        assertTrue(M4Predicates.COUNTING_RULE.contains(SubstrateTrajectory.COUNTING_RULE),
                "a triple without the rule it was counted under is not a measurement");
        assertEquals(5, SubstrateTrajectory.JCA_ANDROID.size(),
                "five states in four days is why the stamp is a requirement, not a formality");
        assertEquals("0/70/21", SubstrateTrajectory.PINNED.triple());
    }

    @Test
    @DisplayName("9.8: the four parcels are published as structure, and three carry no scalar")
    void test_the_four_parcels_are_not_published_as_scalars() {
        assertEquals(List.of("fiéis", "fiação", "substrato", "cobertura"),
                M4Predicates.DECOMPOSITION.stream().map(M4Predicates.Parcel::name).toList());
        assertEquals(1, M4Predicates.DECOMPOSITION.stream()
                        .filter(M4Predicates.Parcel::paid).count(),
                "only the substrate parcel is measurably paid; the other three wait on the "
                        + "judgement columns and are published as structure");
        assertEquals("substrato", M4Predicates.DECOMPOSITION.stream()
                .filter(M4Predicates.Parcel::paid).findFirst().orElseThrow().name());
        M4Predicates.DECOMPOSITION.stream().filter(parcel -> !parcel.paid()).forEach(parcel ->
                assertFalse(parcel.status().matches(".*\\b\\d+(?:[.,]\\d+)?\\s*%.*"),
                        "an unpaid parcel must not carry a percentage: " + parcel.name()));
    }

    private M4Predicates.M4Analysis compare(SpecModel rule, List<PredicateSiteFacts> sites) {
        return metric.compare("CipherSpec.mop", "Cipher.crysl", sites, rule,
                PredicateGraph.of(sites), M4Predicates.Judgements.empty());
    }
}
