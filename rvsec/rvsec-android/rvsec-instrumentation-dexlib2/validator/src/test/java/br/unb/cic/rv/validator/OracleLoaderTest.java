package br.unb.cic.rv.validator;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Admission and the three-oracle gate.
 *
 * <p>Before gh100 the loader counted files, so an empty slot carrying
 * {@code ground_truth_run: pending} counted the same as a populated oracle —
 * which is how the minimum of three came to stand against two real oracles.
 * Admission now runs on the provenance block, and these tests pin both halves:
 * what gets in, and what must not.
 */
class OracleLoaderTest {

    // --- fixtures ---------------------------------------------------------

    private static void handValidated(Path dir, String name) throws IOException {
        Files.writeString(dir.resolve(name + "-oracle.yaml"), """
                name: %s
                profile: java_pre_r8
                provenance:
                  class: hand_validated
                  source: docs/20260423_plano_validacao.md §3.4, oracle table
                expected_events: []
                """.formatted(name));
    }

    private static void derived(Path dir, String name, String weaver) throws IOException {
        Files.writeString(dir.resolve(name + "-oracle.yaml"), """
                name: %s
                profile: paired_execution
                provenance:
                  class: derived_from_independent_weaver
                  source_weaver: %s
                  source_data: out/run_jca_compare_consolidated/events_fair.csv
                  source_sha256: 0000000000000000000000000000000000000000000000000000000000000000
                  derivation_script: derive_l3b_oracle.py
                expected_events: []
                """.formatted(name, weaver));
    }

    @SuppressWarnings("unchecked")
    private static Map<String, String> rejections(Report r) {
        return (Map<String, String>) r.metrics.get("rejectedOracles");
    }

    // --- admission --------------------------------------------------------

    @Test
    void admitsAHandValidatedOracle(@TempDir Path tmp) throws Exception {
        handValidated(tmp, "cryptoapp");
        var loaded = OracleLoader.load(tmp);
        assertEquals(1, loaded.admitted().size());
        assertTrue(loaded.rejected().isEmpty());
    }

    @Test
    void admitsAnOracleDerivedFromAnIndependentWeaver(@TempDir Path tmp) throws Exception {
        derived(tmp, "l3b-paired", "ajc");
        var loaded = OracleLoader.load(tmp);
        assertEquals(1, loaded.admitted().size(), "ajc is not the implementation under test");
    }

    @Test
    void passesWithThreeAdmissibleOracles(@TempDir Path tmp) throws Exception {
        handValidated(tmp, "cryptoapp");
        derived(tmp, "l3b-paired", "ajc");
        derived(tmp, "l3c-control", "aspectj_javaagent");
        Report r = OracleLoader.report(OracleLoader.load(tmp));
        assertTrue(r.passed, r.message);
        assertEquals(3, ((Number) r.metrics.get("oracleCount")).intValue());
    }

    // --- rejection --------------------------------------------------------

    @Test
    void rejectsAnOracleDerivedFromTheImplementationUnderTest(@TempDir Path tmp) throws Exception {
        handValidated(tmp, "cryptoapp");
        derived(tmp, "l3b-paired", "ajc");
        derived(tmp, "circular", "dexlib2");

        Report r = OracleLoader.report(OracleLoader.load(tmp));

        assertFalse(r.passed, "a circular oracle must not be counted toward the minimum");
        String why = rejections(r).get("circular-oracle.yaml");
        assertNotNull(why, "the rejection must name the file");
        // The message has to diagnose the argument, not the file: a reader told
        // "malformed" would go and fix the YAML, which is not what is wrong.
        assertTrue(why.contains("circular"), "message must name the circularity: " + why);
        assertFalse(why.toLowerCase().contains("malformed"),
                "the file is well formed; it is the provenance that is invalid: " + why);
    }

    @Test
    void rejectsAnOracleWithNoProvenanceBlock(@TempDir Path tmp) throws Exception {
        Files.writeString(tmp.resolve("legacy-oracle.yaml"), """
                name: legacy
                expected_events: []
                """);
        var loaded = OracleLoader.load(tmp);
        assertTrue(loaded.admitted().isEmpty());
        assertTrue(loaded.rejected().get("legacy-oracle.yaml").contains("INV-INS-107"));
    }

    @Test
    void rejectsADerivedOracleThatIsNotFrozen(@TempDir Path tmp) throws Exception {
        Files.writeString(tmp.resolve("unfrozen-oracle.yaml"), """
                name: unfrozen
                provenance:
                  class: derived_from_independent_weaver
                  source_weaver: ajc
                  source_data: out/run_jca_compare_consolidated/events_fair.csv
                  derivation_script: derive_l3b_oracle.py
                expected_events: []
                """);
        var loaded = OracleLoader.load(tmp);
        assertTrue(loaded.admitted().isEmpty(),
                "without the source hash the oracle could be re-derived after the comparison "
                        + "and quietly retrofitted to the observed behaviour");
        assertTrue(loaded.rejected().get("unfrozen-oracle.yaml").contains("source_sha256"));
    }

    @Test
    void rejectsAnEmptySlotThatUsedToPadTheCount(@TempDir Path tmp) throws Exception {
        // The historical hateitorrateit shape: a structural placeholder whose
        // provenance declares no admissible class.
        Files.writeString(tmp.resolve("placeholder-oracle.yaml"), """
                name: placeholder
                provenance:
                  source: docs/20260423_plano_validacao.md §Camada 3.1.b
                  ground_truth_run: pending
                expected_events: []
                """);
        var loaded = OracleLoader.load(tmp);
        assertTrue(loaded.admitted().isEmpty(), "a pending slot is not ground truth");
        assertTrue(loaded.rejected().get("placeholder-oracle.yaml").contains("class"));
    }

    @Test
    void failsBelowTheMinimum(@TempDir Path tmp) throws Exception {
        handValidated(tmp, "cryptoapp");
        Report r = OracleLoader.report(OracleLoader.load(tmp));
        assertFalse(r.passed);
        assertEquals(1, ((Number) r.metrics.get("oracleCount")).intValue());
        assertTrue(r.message.contains("INV-INS-59"));
    }

    /**
     * The committed oracle set, not a fixture. The minimum of three has to be
     * met by the oracles actually in the tree, and met by provenance rather
     * than by lowering the threshold (D-O1) — so the assertion is on the
     * admitted count with MINIMUM_ORACLES left where it is.
     */
    @Test
    void theCommittedOracleSetSatisfiesTheMinimum() throws Exception {
        Path oracles = MonitorCallsPremiseContractTest.moduleDir().resolve("oracles");
        assertTrue(Files.isDirectory(oracles), "oracle directory not found at " + oracles);

        var loaded = OracleLoader.load(oracles);
        Report r = OracleLoader.report(loaded);

        assertEquals(3, OracleLoader.MINIMUM_ORACLES,
                "the minimum is met by provenance, never by lowering it (D-O1)");
        assertTrue(r.passed,
                "committed oracles: " + loaded.admitted().stream()
                        .map(p -> p.getFileName().toString()).toList()
                        + "; rejected: " + loaded.rejected());
        // The placeholder slot must be rejected rather than counted — it used
        // to pad the count to two while carrying no ground truth at all.
        assertTrue(loaded.rejected().containsKey("hateitorrateit-oracle.yaml"),
                "the pending kotlin_r8 slot must not count toward the minimum");
    }

    @Test
    void ignoresNonOracleYamls(@TempDir Path tmp) throws Exception {
        handValidated(tmp, "cryptoapp");
        Files.createFile(tmp.resolve("layer4-thresholds.yaml"));
        Files.createFile(tmp.resolve("README.md"));
        var loaded = OracleLoader.load(tmp);
        // The thresholds file is NOT an oracle — the glob filters on the suffix.
        assertEquals(1, loaded.files().size());
    }
}
