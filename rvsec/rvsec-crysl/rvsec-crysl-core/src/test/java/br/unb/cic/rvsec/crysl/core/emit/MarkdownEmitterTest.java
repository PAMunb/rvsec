package br.unb.cic.rvsec.crysl.core.emit;

import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.emit.MarkdownEmitter.Claim;
import br.unb.cic.rvsec.crysl.core.emit.MarkdownEmitter.VerdictEntry;
import br.unb.cic.rvsec.crysl.core.metric.M2Result;
import br.unb.cic.rvsec.crysl.core.model.Normalization;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.Witness;
import br.unb.cic.rvsec.crysl.core.model.WitnessStatus;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/** INV-CONF-08 and INV-CONF-13 at rendering: a report may not say more than the measurement does. */
class MarkdownEmitterTest {

    private static final MarkdownEmitter EMITTER = new MarkdownEmitter();

    private static final Signature DO_FINAL = new Signature("javax.crypto.Cipher", "doFinal",
            List.of("byte[]"), "byte[]");

    private static final Normalization N1 =
            new Normalization("N1", "ε-erasure of `getInstance`, declared unmapped by the map");

    private static M2Result verdictWith(Witness witness) {
        return new M2Result("CipherSpec", "Cipher", M2Result.Verdict.MOP_MORE_PERMISSIVE,
                Optional.ofNullable(witness), List.of(N1), true, List.of(), "R2");
    }

    private static Witness abstractWitness() {
        return new Witness(List.of(DO_FINAL), WitnessStatus.ABSTRACT, List.of(N1),
                Optional.empty());
    }

    private static Witness concreteWitness() {
        return new Witness(List.of(DO_FINAL), WitnessStatus.CONCRETE, List.of(N1),
                Optional.of("TraceRunner/CipherSpec-unsafe.txt"));
    }

    @Test
    @DisplayName("INV-CONF-08: no false-positive or false-negative claim beside an abstract witness")
    void test_inv_conf_08_abstract_no_claim() {
        // The word was found by product search and never run: javax.crypto.Cipher carries a mode
        // state machine neither side models, so an accepted word can throw before a monitor sees it.
        List<VerdictEntry> falsePositive =
                List.of(new VerdictEntry(verdictWith(abstractWitness()), Claim.FALSE_POSITIVE));
        List<VerdictEntry> falseNegative =
                List.of(new VerdictEntry(verdictWith(abstractWitness()), Claim.FALSE_NEGATIVE));
        List<VerdictEntry> noWitness =
                List.of(new VerdictEntry(verdictWith(null), Claim.FALSE_POSITIVE));

        assertAll(
                () -> assertThrows(IllegalArgumentException.class, () -> report(falsePositive)),
                () -> assertThrows(IllegalArgumentException.class, () -> report(falseNegative)),
                () -> assertThrows(IllegalArgumentException.class, () -> report(noWitness)),
                // The same verdict without the claim is publishable, and so is the claim once the
                // word has actually been executed by a named harness.
                () -> assertDoesNotThrow(() -> report(
                        List.of(new VerdictEntry(verdictWith(abstractWitness()), Claim.NONE)))),
                () -> assertDoesNotThrow(() -> report(List.of(
                        new VerdictEntry(verdictWith(concreteWitness()), Claim.FALSE_POSITIVE)))));
    }

    @Test
    @DisplayName("INV-CONF-13: the normalizations and the M2-decl qualifier sit beside the verdict")
    void test_normalizations_and_qualifier_travel_with_the_verdict() {
        String markdown = report(List.of(new VerdictEntry(verdictWith(abstractWitness()),
                Claim.NONE)));

        assertAll(
                () -> assertTrue(markdown.contains("M2-decl: MOP_MORE_PERMISSIVE")),
                () -> assertTrue(markdown.contains("| N1 |"), "the row names its normalizations"),
                () -> assertTrue(markdown.contains("ε-erasure of `getInstance`"),
                        "and the report spells out what each of them did"),
                () -> assertTrue(markdown.contains(MarkdownEmitter.M2_DECL_QUALIFIER)),
                () -> assertTrue(markdown.contains("ABSTRACT"),
                        "the status is printed, so a reader is never left to assume it ran"));
    }

    @Test
    @DisplayName("the report opens on the H1 and the two stamps, as the gh104 evidence files do")
    void test_shape_matches_the_evidence_reports() {
        String markdown = report(List.of(new VerdictEntry(verdictWith(abstractWitness()),
                Claim.NONE)));

        assertAll(
                () -> assertTrue(markdown.startsWith("# CipherSpec — order comparison\n\n- **mop**")),
                () -> assertTrue(markdown.contains("- **oracle** `CrySL-Rules`")),
                () -> assertTrue(markdown.contains("- **counting rule** R2")));
    }

    @Test
    @DisplayName("INV-CONF-15: the M4 report publishes the derived fraction, not just the classes")
    void test_m4_report_publishes_the_derived_fraction() {
        String markdown = EMITTER.predicateReport("CipherSpec — predicates", Fixtures.MOP,
                Fixtures.ORACLE, "R4", List.of(
                        new CsvEmitter.M4Row("CipherSpec.mop", "i2", "body", "positive", "", "2",
                                "GENERATED_KEY", "Key|", "", "Cipher.crysl:174", "store",
                                "read:body", "", "", "member", CsvEmitter.Fidelity.CONFLADO,
                                CsvEmitter.Origin.DERIVED)));

        assertAll(
                () -> assertTrue(markdown.contains("- derived rows: 1")),
                () -> assertTrue(markdown.contains("- inherited rows: 0")),
                () -> assertTrue(markdown.contains(CsvSchema.M4_JUDGEMENT_CAVEAT)),
                () -> assertTrue(markdown.contains("| read:body |"), "the site verdict"),
                () -> assertTrue(markdown.contains("| CONFLADO |"), "and the clause fidelity"));
    }

    private static String report(List<VerdictEntry> entries) {
        return EMITTER.orderReport("CipherSpec — order comparison", Fixtures.MOP, Fixtures.ORACLE,
                "R2", entries);
    }
}
