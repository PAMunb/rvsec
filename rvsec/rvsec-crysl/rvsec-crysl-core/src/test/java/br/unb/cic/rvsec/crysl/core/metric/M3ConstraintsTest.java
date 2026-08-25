package br.unb.cic.rvsec.crysl.core.metric;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.model.Constraint;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.UnrecognizedConstraint;
import br.unb.cic.rvsec.crysl.core.model.UntranslatableConstraint;
import br.unb.cic.rvsec.crysl.core.model.Version;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * M3 over hand-written models, where every input is visible in the test itself.
 *
 * <p>The corpus assertions live in {@code rvsec-crysl-crysl}, which is the only module that can lift
 * both sides. What is checked here is the discipline the metric exists to enforce, and each of these
 * would still matter if the corpus were replaced tomorrow: that an unreadable clause is refused
 * rather than counted absent, that the three untranslatable families are refused with their name,
 * that {@code noCallTo} is <em>not</em> one of them, that the alias-table dependency travels per
 * clause, and that the two ceilings cannot be added.
 */
class M3ConstraintsTest {

    private static final Version MOP = new Version("jca_android",
            new SourceStamp("rvsec", "test-fixture", Instant.EPOCH));
    private static final Version ORACLE = new Version("CrySL-Rules",
            new SourceStamp("rvsec-cognicrypt", "test-fixture", Instant.EPOCH));

    @Test
    @DisplayName("8.6: every result carries R1, and R1 says what it counts")
    void test_counting_rule_travels_with_the_denominator() {
        M3Result result = census("Demo(Demo d) { }", clause("VC:int keysize - 128,"));

        assertTrue(result.countingRule().startsWith("R1: "),
                "the denominator must name its counting rule (INV-CONF-02)");
        assertTrue(result.countingRule().contains("';'")
                        && result.countingRule().contains("'&&' conjunctions not split"),
                "R1 must state both halves: one clause per ';', and && not split. Got: "
                        + result.countingRule());
    }

    @Test
    @DisplayName("8.3: an unreadable idiom is refused, never counted absent")
    void test_unrecognised_clause_is_refused_and_not_absent() {
        M3Result result = census("Demo(Demo d) { }", clause("something the reader has never seen"));

        assertEquals(0, result.absent(),
                "a clause the reader could not read is not a clause the specification is missing; "
                        + "counting it absent publishes a limit of the instrument as a defect of "
                        + "the subject");
        assertEquals(1, result.refusals().size(), "it must be counted, and counted as a refusal");
        assertInstanceOfRefusal(result, UnrecognizedConstraint.class);
        assertEquals(1, result.instrumentCeiling(),
                "an unrecognised idiom is exactly what the ceiling of the instrument counts");
    }

    @Test
    @DisplayName("8.5: neverTypeOf, notHardCoded and callTo are refused with their family named")
    void test_untranslatable_families_are_refused_by_name() {
        for (String[] each : new String[][] {
                {"neverTypeOf(char[] password, java.lang.String null)", "neverTypeOf"},
                {"notHardCoded(char[] password)", "notHardCoded"},
                {"callTo(javax.crypto.Cipher.getIV();)", "callTo"}}) {
            M3Result result = census("Demo(Demo d) { }", clause(each[0]));

            assertEquals(0, result.absent(), each[1] + " is unobservable, not missing");
            UntranslatableConstraint refusal = (UntranslatableConstraint) result.refusals().get(0);
            assertEquals(each[1], refusal.family(),
                    "the family must be named, because a comment is not countable");
            assertEquals(0, result.instrumentCeiling(),
                    each[1] + " is a limit of the formalism, not of this reader, so it must not "
                            + "inflate the ceiling of the instrument");
        }
    }

    @Test
    @DisplayName("8.5: noCallTo is not untranslatable — a prohibition is safety")
    void test_no_call_to_is_not_in_the_untranslatable_family() {
        M3Result result = census("Demo(Demo d) { }",
                clause("noCallTo(javax.crypto.Cipher.init(int encmode);)"));

        assertInstanceOfRefusal(result, UnrecognizedConstraint.class);
        assertEquals(ClauseFamily.NO_CALL_TO, result.rows().get(0).family(),
                "noCallTo is observable when it happens; only the obligation callTo is not");
    }

    @Test
    @DisplayName("8.5: 'noCallTo(' must not be read as 'callTo(' — the façade capitalises the C")
    void test_no_call_to_is_not_a_substring_of_call_to() {
        assertFalse("noCallTo(".contains("callTo("),
                "the family test relies on this; if the façade ever lower-cases the C, the "
                        + "asymmetry between safety and liveness silently disappears");
        assertEquals(ClauseFamily.CALL_TO, ClauseFamily.of("x impliescallTo(Cipher.getIV();)"));
        assertEquals(ClauseFamily.NO_CALL_TO, ClauseFamily.of("x impliesnoCallTo(Cipher.init();)"));
    }

    @Test
    @DisplayName("8.1/8.2: an allow-list read through the alias table is idiom A, and says so")
    void test_idiom_a_records_the_alias_table_dependency() {
        String specification = """
                import br.unb.cic.mop.jca.util.ConscryptAliasTable;
                DemoSpec(Demo d) {
                  List<String> safeAlgorithms = Arrays.asList("AES", "HmacSHA256");
                  event g1 after(String alg):
                    call(* Demo.getInstance(String)) && args(alg) &&
                    condition(ConscryptAliasTable.matches("KeyGenerator", alg, safeAlgorithms)) { }
                }
                """;
        M3Result result = census(specification,
                clause("VC:java.lang.String algorithm - AES,HmacSHA256,"));

        ClauseVerdict row = result.rows().get(0);
        assertEquals(Optional.of(M3Result.Idiom.A_ALIAS_TABLE), row.idiom());
        assertEquals(Optional.of("KeyGenerator"), row.aliasTableService(),
                "a list identical to the rule's is more permissive when the table widens it; the "
                        + "dependency is part of the semantics and belongs on the row");
        assertTrue(row.widenedByAliasTable());
        assertEquals(1, result.widenedByAliasTable());
    }

    @Test
    @DisplayName("8.2: an allow-list with no alias table records no dependency")
    void test_idiom_a_without_the_alias_table() {
        String specification = """
                DemoSpec(Demo d) {
                  List<Integer> validLengths = Arrays.asList(96, 104, 112, 120, 128);
                  event c1 after(int tagLen): call(Demo.new(int)) && args(tagLen) {
                    if (!validLengths.contains(tagLen)) { report(); }
                  }
                }
                """;
        M3Result result = census(specification, clause("VC:int tagLen - 96,104,112,120,128,"));

        ClauseVerdict row = result.rows().get(0);
        assertEquals(Optional.of(M3Result.Idiom.A_ALIAS_TABLE), row.idiom());
        assertEquals(Optional.empty(), row.aliasTableService(),
                "this check is literal; recording a dependency it does not have would accuse it "
                        + "of a permissiveness it does not have either");
    }

    @Test
    @DisplayName("8.1: arithmetic in a condition() is idiom B, and the matched text is kept")
    void test_idiom_b_inline_arithmetic() {
        String specification = """
                DemoSpec(Demo d) {
                  event c1 after(int primeSize, int exponentSize):
                    call(Demo.new(int, int)) && args(primeSize, exponentSize) &&
                    condition(exponentSize < primeSize) { }
                }
                """;
        M3Result result = census(specification,
                clause("int exponentSize + int 0 < int primeSize + int 0"));

        ClauseVerdict row = result.rows().get(0);
        assertEquals(Optional.of(M3Result.Idiom.B_INLINE_ARITHMETIC), row.idiom());
        assertTrue(row.evidence().orElseThrow().contains("exponentSize < primeSize"),
                "the row carries what was matched, so a reader can judge the match instead of "
                        + "trusting the count");
    }

    @Test
    @DisplayName("8.1: a helper declared inside the specification is idiom C, not B and not D")
    void test_idiom_c_local_helper() {
        String specification = """
                DemoSpec(Demo d) {
                  private boolean validate(int keySize) {
                    return Arrays.asList(4096, 3072, 2048).contains(keySize);
                  }
                  event g1 after(int keySize): call(* Demo.init(int)) && args(keySize) &&
                    condition(validate(keySize)) { }
                }
                """;
        M3Result result = census(specification,
                clause("VC:java.lang.String algorithm - RSA,impliesVC:int keysize - 4096,3072,2048,"));

        assertEquals(Optional.of(M3Result.Idiom.C_LOCAL_HELPER), result.rows().get(0).idiom(),
                "the consequent of the implication is what a specification implements, and here it "
                        + "lives in a method of the specification itself");
    }

    @Test
    @DisplayName("8.4: the transformation parts route to idiom D, the external helper")
    void test_idiom_d_external_helper_for_transformation_parts() {
        String specification = """
                import static br.unb.cic.mop.jca.util.CipherTransformationUtil.*;
                CipherSpec(Cipher c) {
                  event g1 after(String transformation):
                    call(* Cipher.getInstance(String)) && args(transformation) &&
                    condition(isValid(transformation)) { }
                }
                """;
        M3Result result = census(specification, clause(
                "VC:java.lang.String transformation.split(/)[0] - AES,"
                        + "impliesVC:java.lang.String transformation.split(/)[1] - CBC,GCM,"));

        ClauseVerdict row = result.rows().get(0);
        assertEquals(ClauseFamily.TRANSFORMATION_PART, row.family());
        assertEquals(Optional.of(M3Result.Idiom.D_EXTERNAL_HELPER), row.idiom());
    }

    @Test
    @DisplayName("8.4: instanceOf is exact at runtime, and its absence is a real absence")
    void test_instance_of_absent_is_absent_not_unknown() {
        M3Result result = census("DemoSpec(Demo d) { }",
                clause("instanceOf(java.security.Key key, javax.crypto.SecretKey null)"
                        + "impliesVC:java.lang.String transformation - AES,"));

        ClauseVerdict row = result.rows().get(0);
        assertEquals(ClauseFamily.INSTANCE_OF, row.family());
        assertTrue(row.absent(),
                "a runtime instanceof is expressible — the monitor is stronger than the analyser "
                        + "here — so not writing it is a measured absence, not a refusal");
        assertEquals(0, result.instrumentCeiling());
    }

    @Test
    @DisplayName("8.3: comments are not countable — a clause quoted in a comment is not implemented")
    void test_a_clause_quoted_in_a_comment_is_not_an_implementation() {
        String specification = """
                DemoSpec(Demo d) {
                  // These three conjuncts were deleted on purpose:
                  // offset >= 0 && len >= 0 && src.length >= offset + len
                  event c1 after(byte[] src, int offset, int len):
                    call(Demo.new(byte[], int, int)) && args(src, offset, len) { }
                }
                """;
        M3Result result = census(specification,
                clause("length(byte[] src) + int 0 >= int offset + int 0 + int len + int 0"));

        assertTrue(result.rows().get(0).absent(),
                "the corpus documents its deletions in comments; a reader that scanned raw text "
                        + "would report every deleted clause as implemented");
    }

    @Test
    @DisplayName("8.3: a clause whose values the reader cannot extract is refused, not absent")
    void test_a_value_clause_the_reader_cannot_read_is_refused() {
        // A VALUE_LIST clause the family recogniser accepts and the value reader does not: the
        // atom has no "- values" tail, so consequentValues(...) comes back empty. Searching the
        // specification for an empty set of values matches nothing by construction, so the search
        // failing says nothing whatever about the specification - and the specification below does
        // implement an allow-list, which is what makes "absent" here a claim and not a shrug.
        String specification = """
                DemoSpec(Demo d) {
                  List<String> algorithms = Arrays.asList("AES");
                }
                """;
        M3Result result = census(specification, clause("VC:java.lang.String algorithm"));

        ClauseVerdict row = result.rows().get(0);
        assertEquals(ClauseFamily.VALUE_LIST, row.family());
        assertEquals(0, result.absent(),
                "the reader could not read the clause; reporting that as a missing implementation "
                        + "publishes a limit of the instrument as a defect of the subject");
        assertInstanceOfRefusal(result, UnrecognizedConstraint.class);
        assertEquals(1, result.instrumentCeiling(),
                "and it is counted in the ceiling of the instrument, where a reader can see how "
                        + "far this reader reaches");
    }

    @Test
    @DisplayName("8.3: an arithmetic clause with no readable operand is refused, not absent")
    void test_an_arithmetic_clause_with_no_bound_name_is_refused() {
        M3Result result = census("Demo(Demo d) { }", clause("int 1 + int 0 >= int 0 + int 0"));

        assertEquals(ClauseFamily.ARITHMETIC, result.rows().get(0).family());
        assertEquals(0, result.absent());
        assertInstanceOfRefusal(result, UnrecognizedConstraint.class);
    }

    @Test
    @DisplayName("8.7: the two ceilings are separate, and there is no way to add them")
    void test_the_two_ceilings_are_reported_separately() {
        M3Result paired = census("Demo(Demo d) { }", clause("an unreadable clause"));
        SpecModel unpaired = rule(clause("VC:int size - 2048,"), clause("VC:int other - 1,"));

        M3Ceilings ceilings = M3Constraints.ceilings(List.of(paired), List.of(unpaired));

        assertEquals(2, ceilings.subject(), "clauses of rules that have no specification");
        assertEquals(1, ceilings.instrument(), "clauses this reader declined to decide");
        assertEquals(CountingRule.R1, ceilings.countingRule());
        assertTrue(java.util.Arrays.stream(M3Ceilings.class.getDeclaredMethods())
                        .noneMatch(method -> method.getName().equals("total")),
                "the two ceilings err in different places; a sum describes neither and would let "
                        + "the number be improved by breaking the reader");
    }

    @Test
    @DisplayName("a clause is implemented or refused, never both")
    void test_a_row_cannot_be_implemented_and_refused() {
        Provenance site = new Provenance("Demo.crysl", 1);
        assertThrows(IllegalArgumentException.class,
                () -> new ClauseVerdict("x", ClauseFamily.OTHER,
                        Optional.of(M3Result.Idiom.A_ALIAS_TABLE), Optional.empty(),
                        Optional.empty(), Optional.empty(),
                        Optional.of(new UnrecognizedConstraint("x", site)), site));
    }

    @Test
    @DisplayName("the aggregate is always re-derivable from the rows")
    void test_aggregate_agrees_with_rows() {
        String specification = """
                DemoSpec(Demo d) {
                  List<String> algorithms = Arrays.asList("AES");
                }
                """;
        M3Result result = census(specification,
                clause("VC:java.lang.String algorithm - AES,"),
                clause("neverTypeOf(char[] password, java.lang.String null)"),
                clause("int len + int 0 > int 0 + int 0"));

        assertEquals(3, result.denominator());
        assertEquals(1, result.implemented());
        assertEquals(1, result.refusals().size());
        assertEquals(1, result.absent());
        assertEquals(result.denominator(),
                result.implemented() + result.refusals().size() + result.absent(),
                "every clause lands in exactly one of the three, or a number is being lost");
    }

    // ── fixtures ──────────────────────────────────────────────────────────────────────────────

    private static M3Result census(String specificationText, Constraint... clauses) {
        SpecModel mop = new SpecModel(MOP, "Demo", Set.of(), List.of(), empty(), List.of(),
                List.of(), List.of(), List.of(), Set.of(), Map.of());
        return M3Constraints.census(mop, rule(clauses),
                SpecificationIdioms.of("DemoSpec.mop", specificationText));
    }

    private static SpecModel rule(Constraint... clauses) {
        return new SpecModel(ORACLE, "demo.Demo", Set.of(), List.of(), empty(), List.of(clauses),
                List.of(), List.of(), List.of(), Set.of(), Map.of());
    }

    private static Constraint clause(String text) {
        return new Constraint(text, new Provenance("Demo.crysl", 10));
    }

    private static Automaton empty() {
        return new Automaton(Set.of("q0"), "q0", Set.of("q0"), List.of());
    }

    private static void assertInstanceOfRefusal(M3Result result, Class<?> expected) {
        assertEquals(1, result.refusals().size());
        assertTrue(expected.isInstance(result.refusals().get(0)),
                "expected " + expected.getSimpleName() + " but got "
                        + result.refusals().get(0).getClass().getSimpleName());
    }
}
