package br.unb.cic.rvsec.crysl.core.metric;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.emit.StampedTable;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Version;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * R-M1 and the refusal, over hand-built models.
 *
 * <p>These fixtures are the shapes the corpus produces, written out here so the rule can be checked
 * without either parser on the classpath. The corpus run that measures the real numbers lives in
 * {@code rvsec-crysl-crysl}, where both lifters are available; it is tagged oracle-dependent and CI
 * excludes it, so this test is the part of M1 that a checkout with no sibling repository still
 * verifies.
 */
class M1EventsTest {

    private static final String DIGEST = "java.security.MessageDigest";

    @Test
    @DisplayName("R-M1: a pointcut's '..' expands over every overload the rule declares")
    void test_mop_tail_wildcard_expands_over_the_rule_overloads() {
        Signature pointcut = sig(DIGEST, "update", List.of(".."), "void");

        assertTrue(M1Events.matches(pointcut, sig(DIGEST, "update", List.of("byte"), "void")));
        assertTrue(M1Events.matches(pointcut, sig(DIGEST, "update", List.of("byte[]"), "void")));
        assertTrue(M1Events.matches(pointcut,
                sig(DIGEST, "update", List.of("byte[]", "int", "int"), "void")));
        assertTrue(M1Events.matches(pointcut,
                sig(DIGEST, "update", List.of("java.nio.ByteBuffer"), "void")));
        assertFalse(M1Events.matches(pointcut, sig(DIGEST, "digest", List.of(), "byte[]")),
                "the method name still has to be equal; '..' widens the arguments, not the call");
    }

    @Test
    @DisplayName("R-M1: the rule's unbound argument is not widened by the artifact under test")
    void test_the_rule_hole_is_matched_only_by_a_pointcut_that_is_also_open() {
        Signature hole = sig(DIGEST, "getInstance",
                List.of("java.lang.String", M1Events.RULE_HOLE), "void");

        assertFalse(M1Events.matches(
                        sig(DIGEST, "getInstance", List.of("String", "String"), DIGEST), hole),
                "MessageDigestSpec names the overload; the rule left the position unbound, and "
                        + "widening the oracle to fit what the specification wrote would make "
                        + "coverage a function of the artifact under test");
        assertTrue(M1Events.matches(
                        sig(DIGEST, "getInstance", List.of("String", ".."), DIGEST), hole),
                "SecureRandomSpec writes getInstance(String, ..) and leaves the same position "
                        + "open, which is what covering an unbound argument means");
        assertTrue(M1Events.matches(
                        sig(DIGEST, "getInstance", List.of("String", "*"), DIGEST), hole),
                "the single-parameter wildcard leaves the position open too");
    }

    @Test
    @DisplayName("R-M1: return types are not compared, and unqualified names fold only one way")
    void test_return_types_are_out_and_folding_is_one_sided() {
        assertTrue(M1Events.matches(
                        sig(DIGEST, "digest", List.of("byte[]", "int", "int"), "int"),
                        sig(DIGEST, "digest", List.of("byte[]", "int", "int"), "void")),
                "the rule writes void because it binds no result; the platform method returns int, "
                        + "and return type is not part of overload identity");
        assertTrue(M1Events.matches(
                        sig(DIGEST, "getInstance", List.of("String"), DIGEST),
                        sig(DIGEST, "getInstance", List.of("java.lang.String"), "void")),
                "the pointcut writes String where the rule writes java.lang.String");
        assertFalse(M1Events.matches(
                        sig("javax.crypto.Cipher", "getInstance", List.of("String"), "void"),
                        sig("java.security.Cipher", "getInstance", List.of("String"), "void")),
                "two qualified names that differ never fold, or the comparison would merge types "
                        + "that live in different packages");
    }

    @Test
    @DisplayName("both differences are emitted: the MessageDigest shape, in miniature")
    void test_compare_emits_coverage_and_both_differences() {
        M1Result result = M1Events.compare("MessageDigestSpec", specification(),
                "MessageDigest", rule());

        assertEquals(5, result.declared());
        assertEquals(4, result.covered(),
                "the four update overloads are covered by one pointcut; getInstance(String, _) is "
                        + "not, because the specification names the concrete overload instead");
        assertEquals(List.of("getInstance"), result.ruleOnly().stream().map(Signature::name).toList(),
                "an obligation nobody monitors");
        assertEquals(List.of("getInstance"), result.mopOnly().stream().map(Signature::name).toList(),
                "a monitor watching a call the rule does not name");
        assertTrue(result.refusals().isEmpty(),
                "M1 raises no refusal of its own: the platform check is M0.3's, before M1 runs");
        assertEquals(M1Events.COUNTING_RULE, result.countingRule());
    }

    @Test
    @DisplayName("task 7.2: no coverage figure can be produced without both lists beside it")
    void test_no_path_from_a_result_to_a_bare_coverage_number() {
        assertThrows(NullPointerException.class,
                () -> new M1Result("s", "r", 1, 2, null, List.of(), List.of(), "rule"),
                "a result cannot exist without the MOP-only list");
        assertThrows(NullPointerException.class,
                () -> new M1Result("s", "r", 1, 2, List.of(), null, List.of(), "rule"),
                "nor without the rule-only list");

        assertTrue(M1Events.BODY_COLUMNS.contains(M1Events.COVERAGE_COLUMN));
        assertTrue(M1Events.BODY_COLUMNS.contains(M1Events.MOP_ONLY_COLUMN));
        assertTrue(M1Events.BODY_COLUMNS.contains(M1Events.RULE_ONLY_COLUMN));

        // The structural half of the refusal: the only public path from an M1 number to a
        // character is table(), whose row is built from one M1Result into one fixed column set. A
        // reflective sweep is what keeps that true - a later "convenience" method returning the
        // percentage on its own would be exactly the scalar this capability exists to abolish.
        for (var method : M1Events.class.getDeclaredMethods()) {
            if (!java.lang.reflect.Modifier.isPublic(method.getModifiers())) {
                continue;
            }
            Class<?> returned = method.getReturnType();
            assertFalse(returned == double.class || returned == float.class
                            || returned == Double.class || returned == Float.class,
                    "M1Events." + method.getName() + " hands out a bare coverage figure; the "
                            + "percentage may only be rendered beside both difference lists");
        }
    }

    @Test
    @DisplayName("the M1 table carries the oracle stamp, the counting rule and the pairing rule")
    void test_the_table_names_its_oracle_and_its_pairing_rule() {
        M1Result result = M1Events.compare("MessageDigestSpec", specification(),
                "MessageDigest", rule());
        StampedTable table = M1Events.table(List.of(result), mopVersion(), oracleVersion(),
                SpecRulePairing.PAIRING_RULE);

        String markdown = table.markdown(List.of());
        assertTrue(markdown.contains("rvsec-cognicrypt"), "the oracle repository");
        assertTrue(markdown.contains("upstream-commit"), "the oracle commit");
        assertTrue(markdown.contains("INV-CONF-11"), "the pairing rule (INV-CONF-11)");
        assertTrue(markdown.contains("R-M1"), "the counting rule (INV-CONF-02)");

        String csv = table.csv();
        assertTrue(csv.contains(M1Events.MOP_ONLY_COLUMN) && csv.contains(M1Events.RULE_ONLY_COLUMN),
                "the coverage cell never ships without the two difference columns");
        assertTrue(csv.contains("4/5 (80.0%)"), "the coverage fraction, in the same row");
    }

    @Test
    @DisplayName("the table refuses to render when the pairing rule is absent (INV-CONF-11)")
    void test_the_table_refuses_without_a_pairing_rule() {
        M1Result result = M1Events.compare("s", specification(), "r", rule());
        assertThrows(IllegalArgumentException.class,
                () -> M1Events.table(List.of(result), mopVersion(), oracleVersion(), "  "));
    }

    @Test
    @DisplayName("the alignment comes from the signature intersection: one label, four symbols")
    void test_alignment_expands_the_aggregate_from_signatures_alone() {
        LabelAlignment alignment = M1Events.align("MessageDigestSpec", specification(),
                "MessageDigest", rule());

        LabelAlignment.Entry update = entry(alignment, "update");
        assertEquals(4, update.ruleSymbols().size(),
                "one pointcut, four rule symbols - the aggregate expansion, derived from the "
                        + "signature set and not from the fact that both sides say 'update'");
        assertEquals(4, update.sharedSignatures().size(), "the witness travels with the entry");

        assertTrue(entry(alignment, "g2").unaligned(),
                "the specification's g2 names an overload the rule left unbound, so it aligns with "
                        + "nothing - a fact M2 needs stated rather than omitted");
        assertEquals(1, alignment.unalignedRuleSymbols().size(),
                "and the rule symbol nobody reaches is listed on the other side");
        assertEquals(M1Events.ALIGNMENT_COUNTING_RULE, alignment.countingRule());

        // The alignment leaves this class as a stamped table, because G10 consumes it as a file
        // and a file with no oracle identity beside it is not a comparable input (INV-CONF-11).
        String csv = M1Events.alignmentTable(List.of(alignment), mopVersion(), oracleVersion(),
                SpecRulePairing.PAIRING_RULE).csv();
        assertTrue(csv.contains("update"), "one row per declared label");
        assertTrue(csv.contains("u1 u2 u3 u4"), "with the rule symbols it stands for");
        assertTrue(csv.contains("rvsec-cognicrypt"), "and the oracle stamp on every row");
    }

    private static LabelAlignment.Entry entry(LabelAlignment alignment, String label) {
        return alignment.entries().stream()
                .filter(e -> e.mopLabel().name().equals(label))
                .findFirst()
                .orElseThrow(() -> new AssertionError("no entry for " + label));
    }

    /** A miniature of {@code jca_android/MessageDigestSpec.mop}: one aggregate, one overload. */
    private static SpecModel specification() {
        return model("MessageDigest", List.of(
                event("update", 0, sig(DIGEST, "update", List.of(".."), "void")),
                event("g2", 1, sig(DIGEST, "getInstance", List.of("String", "String"), DIGEST))));
    }

    /** A miniature of {@code MessageDigest.crysl}: four overloads and one unbound argument. */
    private static SpecModel rule() {
        return model(DIGEST, List.of(
                event("u1", 0, sig(DIGEST, "update", List.of("byte"), "void")),
                event("u2", 1, sig(DIGEST, "update", List.of("byte[]"), "void")),
                event("u3", 2, sig(DIGEST, "update", List.of("byte[]", "int", "int"), "void")),
                event("u4", 3, sig(DIGEST, "update", List.of("java.nio.ByteBuffer"), "void")),
                event("g2", 4, sig(DIGEST, "getInstance",
                        List.of("java.lang.String", M1Events.RULE_HOLE), "void"))));
    }

    private static SpecModel model(String type, List<Event> events) {
        return new SpecModel(mopVersion(), type, Set.of(), events,
                new Automaton(Set.of("q0"), "q0", Set.of("q0"), List.of()),
                List.of(), List.of(), List.of(), List.of(), Set.of(), Map.of());
    }

    private static Event event(String label, int index, Signature signature) {
        return new Event(new Label(label), label, Set.of(signature), Optional.empty(), index);
    }

    private static Signature sig(String owner, String name, List<String> params, String returns) {
        return new Signature(owner, name, params, returns);
    }

    private static Version mopVersion() {
        return new Version("jca_android", new SourceStamp("rvsec", "spec-commit", Instant.EPOCH));
    }

    private static Version oracleVersion() {
        return new Version("CrySL-Rules",
                new SourceStamp("rvsec-cognicrypt", "upstream-commit", Instant.EPOCH));
    }
}
