package br.unb.cic.rvsec.crysl.core.emit;

import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.automata.Transition;
import br.unb.cic.rvsec.crysl.core.metric.ConformanceReport;
import br.unb.cic.rvsec.crysl.core.metric.M1Result;
import br.unb.cic.rvsec.crysl.core.metric.M4Result;
import br.unb.cic.rvsec.crysl.core.model.Guard;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
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

/** INV-CONF-01 at serialization, and the shape of the document the component publishes. */
class JsonEmitterTest {

    private static final JsonEmitter EMITTER = new JsonEmitter();

    private static final Signature INIT = new Signature("javax.crypto.Cipher", "init",
            List.of("int", "java.security.Key"), "void");

    private static SpecModel modelWith(Version version) {
        Automaton order = new Automaton(Set.of("q0", "q1"), "q0", Set.of("q1"),
                List.of(new Transition("q0", INIT, Optional.of(new Guard("mode == 1")), "q1")));
        return new SpecModel(version, "javax.crypto.Cipher", Set.of(), List.of(), order,
                List.of(), List.of(), List.of(), List.of(), Set.of(), Map.of());
    }

    private static Version placeholder(String commit) {
        return new Version("jca_android",
                new SourceStamp("rvsec", commit, Instant.parse("2026-08-24T10:00:00Z")));
    }

    @Test
    @DisplayName("INV-CONF-01: a model whose stamp says nothing is refused, not serialized")
    void test_inv_conf_01_unstamped_refused() {
        // The records reject null, so the reachable hole is the placeholder: an empty or "unknown"
        // commit type-checks and still leaves the document unattributable to a corpus state.
        assertAll(
                () -> assertThrows(MissingVersionError.class,
                        () -> EMITTER.toJson((SpecModel) null)),
                () -> assertThrows(MissingVersionError.class,
                        () -> EMITTER.toJson(modelWith(placeholder("")))),
                () -> assertThrows(MissingVersionError.class,
                        () -> EMITTER.toJson(modelWith(placeholder("unknown")))),
                () -> assertThrows(MissingVersionError.class,
                        () -> EMITTER.toJson(modelWith(placeholder("   ")))));
    }

    @Test
    @DisplayName("the stamp is the first member of the document, and the model serializes")
    void test_stamp_is_first_and_optionals_survive() {
        String json = EMITTER.toJson(modelWith(Fixtures.MOP));

        assertAll(
                () -> assertTrue(json.replaceFirst("^\\{\\s*", "").startsWith("\"stamp\"")),
                () -> assertTrue(json.contains("\"commit\": \"39b000ce\"")),
                // Optional is not reflectable under the module system; the adapter is what keeps
                // a guarded transition from turning into an InaccessibleObjectException.
                () -> assertTrue(json.contains("mode == 1")));
    }

    @Test
    @DisplayName("INV-CONF-02: a result that names no counting rule blocks the whole document")
    void test_inv_conf_02_report_without_a_rule_is_refused() {
        ConformanceReport report = new ConformanceReport(Fixtures.MOP, Fixtures.ORACLE,
                "by declared type", List.of(new M1Result("CipherSpec", "Cipher", 3, 5,
                        List.of(), List.of(), List.of(), "  ")));

        assertThrows(IllegalArgumentException.class, () -> EMITTER.toJson(report));
    }

    @Test
    @DisplayName("D-17: the report carries both stamps and the pairing rule in its header")
    void test_report_header_carries_both_corpora() {
        ConformanceReport report = new ConformanceReport(Fixtures.MOP, Fixtures.ORACLE,
                "by declared type (INV-CONF-11)",
                List.of(new M4Result("CipherSpec", "Cipher",
                        List.of(new PredicateRef("generatedKey", List.of("key"), Polarity.POSITIVE,
                                new Provenance("CipherSpec.mop", 12))),
                        List.of(), List.of(), 1, 0, List.of(), "R4")));

        String json = EMITTER.toJson(report);

        assertAll(
                () -> assertTrue(json.contains("\"repository\": \"rvsec\"")),
                () -> assertTrue(json.contains("\"repository\": \"rvsec-cognicrypt\"")),
                () -> assertTrue(json.contains("by declared type (INV-CONF-11)")),
                () -> assertTrue(json.contains("m4JudgementCaveat"),
                        "INV-CONF-15 travels with any document that reports M4"),
                () -> assertTrue(json.contains("\"countingRule\": \"R4\"")));
    }
}
