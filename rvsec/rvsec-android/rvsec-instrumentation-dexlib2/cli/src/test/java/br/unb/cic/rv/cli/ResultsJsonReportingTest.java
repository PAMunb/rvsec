package br.unb.cic.rv.cli;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Covers {@code --results-json} on the {@code instrument} subcommand — the
 * production path's only channel for the weaver's counters (INV-INS-105).
 *
 * <p>The failure case runs end to end through
 * {@link BatchRunner#instrumentOne}: a pipeline that fails still has to produce
 * the document, because an absent file must mean the JVM died rather than that
 * the weave went badly. The success case is asserted one level down, against
 * {@link BatchRunner#writeResultsJson}, because driving a genuine success needs
 * a real APK plus javac, d8 and a keystore — fixtures this suite does not carry.
 * What the success case is here to pin is the document shape the Python wrapper
 * parses, not the pipeline that produced it.
 */
class ResultsJsonReportingTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    /** Config with nothing resolved — runPipeline reports config_validation. */
    private static EffectiveConfig failingConfig() {
        return new EffectiveConfig(null, null, null, null, List.of(),
                null, null, null, true, null, "INFO");
    }

    @Test
    void instrumentWritesResultsJsonWhenTheWeaveFails(@TempDir Path tmp) throws Exception {
        Path apk = Files.createFile(tmp.resolve("sample.apk"));
        // Deliberately under a directory that does not exist yet: the Python
        // wrapper names one file per APK inside a subdirectory it has not
        // necessarily created, and a successful weave must not be reported as
        // a write failure just because the parent was missing.
        Path out = tmp.resolve("reports").resolve("sample.json");

        BatchRunner.instrumentOne(failingConfig(), apk, out);

        assertTrue(Files.isRegularFile(out),
                "a failed weave must still report its counters and phase");
        JsonNode root = MAPPER.readTree(out.toFile());
        assertEquals("dexlib2", root.get("variant").asText(),
                "variant tag is the Python wrapper's contract");
        assertEquals(1, root.get("results").size(),
                "the single-APK path writes a one-element results array");
        JsonNode entry = root.get("results").get(0);
        assertEquals("sample.apk", entry.get("apkName").asText());
        assertFalse(entry.get("success").asBoolean());
        assertTrue(entry.hasNonNull("phase"), "phase pinpoints how far the pipeline got");
        assertTrue(entry.hasNonNull("message"));
    }

    @Test
    void resultsJsonCarriesWeaveCountsForASuccessfulWeave(@TempDir Path tmp) throws Exception {
        BatchRunner.PerApkResult success = new BatchRunner.PerApkResult(
                "cryptoapp.apk", true, "instrumented + signed", "signed",
                Map.of("matchesApplied", 42, "plansSkippedHighRegister", 3));
        Path out = tmp.resolve("results.json");

        BatchRunner.writeResultsJson(List.of(success), out);

        JsonNode entry = MAPPER.readTree(out.toFile()).get("results").get(0);
        assertTrue(entry.get("success").asBoolean());
        assertEquals("signed", entry.get("phase").asText());
        // The counters are the reason the option exists: task 6.4 reads
        // plansSkippedHighRegister to tell whether emitting N invokes instead
        // of 1 pushed any site over its register budget.
        assertEquals(42, entry.get("weaveCounts").get("matchesApplied").asInt());
        assertEquals(3, entry.get("weaveCounts").get("plansSkippedHighRegister").asInt());
    }

    /**
     * {@code advicesExcludedByArity} (INV-INS-122) travels the same channel as
     * {@code wrappersGenerated}, and a zero must be written rather than omitted:
     * the Python wrapper copies {@code weaveCounts} through whole, so an absent
     * key and a measured zero would be indistinguishable downstream — "no
     * incompatible advice" would read as "this build did not measure".
     *
     * <p>Like the case above this is a serialisation test: {@code counts} is
     * built by hand, so it pins the document shape, not the origin of the
     * number. What produces the number is the wrapper grouping loop, and the
     * instrument for that is the re-weave of the frozen descriptor recorded in
     * {@code evidence/e2_reweave.md}.
     */
    @Test
    void resultsJsonCarriesTheArityCounterBesideWrappersGenerated(@TempDir Path tmp)
            throws Exception {
        BatchRunner.PerApkResult measured = new BatchRunner.PerApkResult(
                "cryptoapp.apk", true, "instrumented + signed", "signed",
                Map.of("wrappersGenerated", 96, "advicesExcludedByArity", 10));
        BatchRunner.PerApkResult none = new BatchRunner.PerApkResult(
                "clean.apk", true, "instrumented + signed", "signed",
                Map.of("wrappersGenerated", 4, "advicesExcludedByArity", 0));
        Path out = tmp.resolve("results.json");

        BatchRunner.writeResultsJson(List.of(measured, none), out);

        JsonNode results = MAPPER.readTree(out.toFile()).get("results");
        assertEquals(96, results.get(0).get("weaveCounts").get("wrappersGenerated").asInt());
        assertEquals(10, results.get(0).get("weaveCounts").get("advicesExcludedByArity").asInt());
        assertTrue(results.get(1).get("weaveCounts").hasNonNull("advicesExcludedByArity"),
                "an APK with no incompatible advice carries the key, never omits it");
        assertEquals(0, results.get(1).get("weaveCounts").get("advicesExcludedByArity").asInt());
    }

    @Test
    void instrumentWritesNothingWhenNoResultsJsonIsRequested(@TempDir Path tmp) throws Exception {
        Path apk = Files.createFile(tmp.resolve("sample.apk"));

        BatchRunner.instrumentOne(failingConfig(), apk, null);

        try (var entries = Files.list(tmp)) {
            assertEquals(List.of(apk), entries.toList(),
                    "ad-hoc console runs must not leave report files behind");
        }
    }
}
