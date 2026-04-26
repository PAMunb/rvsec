package br.unb.cic.rv.validator;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for {@link TraceComparator#batchAnalyze(Path, Path, Path, Path)}.
 * Each test materializes synthetic results trees + oracle YAMLs under
 * {@code @TempDir}, invokes batchAnalyze, then asserts on the CSV file
 * and the {@link Report} metrics.
 */
class TraceComparatorBatchTest {

    private static final String EXPECTED_HEADER =
            "apk,rep,tool,spec,ajcF1,dexF1,kappa,ajcTp,ajcFp,ajcFn,dexTp,dexFp,dexFn";

    @Test
    void singleApkSingleSpecRoundTrip(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path ajcDir = Files.createDirectories(tmp.resolve("ajc"));
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        Path csv = tmp.resolve("out/metrics.csv");

        Files.writeString(oracleDir.resolve("cryptoapp-oracle.yaml"),
                "name: cryptoapp\n"
              + "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: SpecX\n"
              + "    error_type: ErrA\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n");

        String body = "RVSEC: [SpecX] ErrA: detail\n";
        writeLogcat(ajcDir, "cryptoapp.apk", "1", "300", "aperv", body);
        writeLogcat(dexDir, "cryptoapp.apk", "1", "300", "aperv", body);

        Report r = TraceComparator.batchAnalyze(oracleDir, ajcDir, dexDir, csv);
        assertTrue(r.passed, () -> "expected pass; got: " + r.message);
        assertEquals(1, ((Number) r.metrics.get("pairedTriples")).intValue());
        assertEquals(1, ((Number) r.metrics.get("rowsWritten")).intValue());
        assertEquals(1, ((Number) r.metrics.get("uniqueApks")).intValue());
        assertEquals(1, ((Number) r.metrics.get("uniqueSpecs")).intValue());

        List<String> lines = Files.readAllLines(csv);
        assertEquals(2, lines.size());
        assertEquals(EXPECTED_HEADER, lines.get(0));
        // Row: apk, rep, tool, spec, ajcF1=1.0, dexF1=1.0, kappa=1.0, all-TP=1, FPs/FNs=0
        assertEquals("cryptoapp.apk,1,aperv,SpecX,1.0,1.0,1.0,1,0,0,1,0,0", lines.get(1));
    }

    @Test
    void multipleRepsAndToolsPaired(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path ajcDir = Files.createDirectories(tmp.resolve("ajc"));
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        Path csv = tmp.resolve("metrics.csv");

        Files.writeString(oracleDir.resolve("cryptoapp-oracle.yaml"),
                "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: SpecA\n"
              + "    error_type: ErrA\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n"
              + "  - id: 2\n"
              + "    spec: SpecB\n"
              + "    error_type: ErrB\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n");

        String body = "RVSEC: [SpecA] ErrA: x\nRVSEC: [SpecB] ErrB: y\n";
        // 1 APK x 3 reps x 2 tools = 6 logcats per side. Use rep=10 to verify
        // numeric (not lexicographic) sorting puts it after rep=2.
        String[] reps = {"1", "2", "10"};
        String[] tools = {"aperv", "monkey"};
        for (String rep : reps) {
            for (String tool : tools) {
                writeLogcat(ajcDir, "cryptoapp.apk", rep, "300", tool, body);
                writeLogcat(dexDir, "cryptoapp.apk", rep, "300", tool, body);
            }
        }

        Report r = TraceComparator.batchAnalyze(oracleDir, ajcDir, dexDir, csv);
        assertTrue(r.passed);
        assertEquals(6, ((Number) r.metrics.get("pairedTriples")).intValue());
        assertEquals(12, ((Number) r.metrics.get("rowsWritten")).intValue());
        assertEquals(2, ((Number) r.metrics.get("uniqueSpecs")).intValue());

        List<String> lines = Files.readAllLines(csv);
        assertEquals(13, lines.size()); // header + 12 rows
        assertEquals(EXPECTED_HEADER, lines.get(0));

        // Verify sorted order: (apk asc, rep numeric asc, tool asc, spec asc).
        // Expected first 4 rows: rep=1 aperv {SpecA, SpecB}, rep=1 monkey {SpecA, SpecB}.
        assertTrue(lines.get(1).startsWith("cryptoapp.apk,1,aperv,SpecA,"));
        assertTrue(lines.get(2).startsWith("cryptoapp.apk,1,aperv,SpecB,"));
        assertTrue(lines.get(3).startsWith("cryptoapp.apk,1,monkey,SpecA,"));
        assertTrue(lines.get(4).startsWith("cryptoapp.apk,1,monkey,SpecB,"));
        // Then rep=2 (numeric sort: 2 before 10).
        assertTrue(lines.get(5).startsWith("cryptoapp.apk,2,aperv,SpecA,"));
        // Last block is rep=10.
        assertTrue(lines.get(11).startsWith("cryptoapp.apk,10,monkey,SpecA,"));
        assertTrue(lines.get(12).startsWith("cryptoapp.apk,10,monkey,SpecB,"));
    }

    @Test
    void apkWithoutOracleSkipped(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path ajcDir = Files.createDirectories(tmp.resolve("ajc"));
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        Path csv = tmp.resolve("metrics.csv");

        // Only cryptoapp has an oracle; orphan.apk has none.
        Files.writeString(oracleDir.resolve("cryptoapp-oracle.yaml"),
                "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: SpecX\n"
              + "    error_type: ErrA\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n");

        String body = "RVSEC: [SpecX] ErrA: x\n";
        writeLogcat(ajcDir, "cryptoapp.apk", "1", "300", "aperv", body);
        writeLogcat(dexDir, "cryptoapp.apk", "1", "300", "aperv", body);
        writeLogcat(ajcDir, "orphan.apk", "1", "300", "aperv", body);
        writeLogcat(dexDir, "orphan.apk", "1", "300", "aperv", body);

        Report r = TraceComparator.batchAnalyze(oracleDir, ajcDir, dexDir, csv);
        assertEquals(2, ((Number) r.metrics.get("pairedTriples")).intValue());
        assertEquals(1, ((Number) r.metrics.get("rowsWritten")).intValue());

        @SuppressWarnings("unchecked")
        List<String> skippedNoOracle = (List<String>) r.metrics.get("skippedNoOracle");
        assertEquals(1, skippedNoOracle.size());
        assertEquals("orphan.apk", skippedNoOracle.get(0));

        List<String> lines = Files.readAllLines(csv);
        assertEquals(2, lines.size());
        assertTrue(lines.get(1).startsWith("cryptoapp.apk,"));
    }

    @Test
    void unpairedLogcatRecorded(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path ajcDir = Files.createDirectories(tmp.resolve("ajc"));
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        Path csv = tmp.resolve("metrics.csv");

        Files.writeString(oracleDir.resolve("cryptoapp-oracle.yaml"),
                "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: SpecX\n"
              + "    error_type: ErrA\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n");

        String body = "RVSEC: [SpecX] ErrA: x\n";
        // Triple (cryptoapp.apk, rep=1, monkey) only on the ajc side -> unpaired.
        writeLogcat(ajcDir, "cryptoapp.apk", "1", "300", "monkey", body);
        // Triple (cryptoapp.apk, rep=1, aperv) on both sides -> paired.
        writeLogcat(ajcDir, "cryptoapp.apk", "1", "300", "aperv", body);
        writeLogcat(dexDir, "cryptoapp.apk", "1", "300", "aperv", body);

        Report r = TraceComparator.batchAnalyze(oracleDir, ajcDir, dexDir, csv);
        assertEquals(1, ((Number) r.metrics.get("pairedTriples")).intValue());
        assertEquals(1, ((Number) r.metrics.get("rowsWritten")).intValue());

        @SuppressWarnings("unchecked")
        List<String> skippedUnpaired = (List<String>) r.metrics.get("skippedUnpaired");
        assertEquals(1, skippedUnpaired.size());
        String unpaired = skippedUnpaired.get(0);
        assertTrue(unpaired.contains("cryptoapp.apk|1|monkey"),
                () -> "expected triple cryptoapp.apk|1|monkey in unpaired entry: " + unpaired);
        assertTrue(unpaired.contains("missing in dexlib2"),
                () -> "expected 'missing in dexlib2' annotation: " + unpaired);

        List<String> lines = Files.readAllLines(csv);
        assertEquals(2, lines.size());
        assertTrue(lines.get(1).startsWith("cryptoapp.apk,1,aperv,SpecX,"));
    }

    @Test
    void apkBaseNameStripsVersionSuffix(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path ajcDir = Files.createDirectories(tmp.resolve("ajc"));
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        Path csv = tmp.resolve("metrics.csv");

        // Mirrors the F-Droid corpus: app.pwhs.blockads_45.apk -> app.pwhs.blockads-oracle.yaml.
        Files.writeString(oracleDir.resolve("app.pwhs.blockads-oracle.yaml"),
                "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: SpecX\n"
              + "    error_type: ErrA\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n");

        String body = "RVSEC: [SpecX] ErrA: x\n";
        writeLogcat(ajcDir, "app.pwhs.blockads_45.apk", "1", "300", "aperv", body);
        writeLogcat(dexDir, "app.pwhs.blockads_45.apk", "1", "300", "aperv", body);

        Report r = TraceComparator.batchAnalyze(oracleDir, ajcDir, dexDir, csv);
        assertEquals(1, ((Number) r.metrics.get("rowsWritten")).intValue());
        @SuppressWarnings("unchecked")
        List<String> skippedNoOracle = (List<String>) r.metrics.get("skippedNoOracle");
        assertTrue(skippedNoOracle.isEmpty(),
                () -> "expected no skippedNoOracle, got: " + skippedNoOracle);

        List<String> lines = Files.readAllLines(csv);
        assertNotNull(lines);
        assertEquals(2, lines.size());
        assertTrue(lines.get(1).startsWith("app.pwhs.blockads_45.apk,1,aperv,SpecX,"));
    }

    @Test
    void emptyResultsDirsProduceNoRows(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path ajcDir = Files.createDirectories(tmp.resolve("ajc"));
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        Path csv = tmp.resolve("metrics.csv");

        Report r = TraceComparator.batchAnalyze(oracleDir, ajcDir, dexDir, csv);
        assertFalse(r.passed);
        assertEquals(0, ((Number) r.metrics.get("rowsWritten")).intValue());
        List<String> lines = Files.readAllLines(csv);
        assertEquals(1, lines.size());
        assertEquals(EXPECTED_HEADER, lines.get(0));
    }

    /**
     * Materialize a logcat at
     * {@code <root>/<apk>/<apk>__<rep>__<timeout>__<tool>.logcat}.
     */
    private static void writeLogcat(Path root, String apk, String rep,
                                    String timeout, String tool, String body) throws Exception {
        Path apkDir = Files.createDirectories(root.resolve(apk));
        Path logcat = apkDir.resolve(apk + "__" + rep + "__" + timeout + "__" + tool + ".logcat");
        Files.writeString(logcat, body);
    }
}
