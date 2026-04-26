package br.unb.cic.rv.validator;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for {@link TraceComparator}. Each test materializes a small
 * oracle YAML + a paired pair of logcat fixtures under {@code @TempDir}
 * and asserts on the {@link Report} fields. No real APKs / no emulator.
 */
class TraceComparatorTest {

    @Test
    void bothPipelinesHitAllOracleEvents(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path apkDir = Files.createDirectories(tmp.resolve("apks"));
        Files.writeString(oracleDir.resolve("toy-oracle.yaml"),
                "name: toy\n"
              + "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: SpecX\n"
              + "    error_type: ErrA\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n"
              + "  - id: 2\n"
              + "    spec: SpecX\n"
              + "    error_type: ErrB\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n");
        Path traceDir = Files.createDirectories(apkDir.resolve("toy"));
        String body = "RVSEC: [SpecX] ErrA: detail one\n"
                    + "RVSEC: [SpecX] ErrB: detail two\n";
        Files.writeString(traceDir.resolve("ajc.logcat"), body);
        Files.writeString(traceDir.resolve("dexlib2.logcat"), body);

        Report r = TraceComparator.compare(oracleDir, apkDir);
        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message);
        assertEquals(1, ((Number) r.metrics.get("totalOracles")).intValue());
        assertEquals(1.0, ((Number) r.metrics.get("minDexF1")).doubleValue(), 1e-9);
        assertEquals(1.0, ((Number) r.metrics.get("minKappa")).doubleValue(), 1e-9);

        Map<?, ?> perOracle = (Map<?, ?>) r.metrics.get("perOracle");
        Map<?, ?> toy = (Map<?, ?>) perOracle.get("toy");
        Map<?, ?> perSpec = (Map<?, ?>) toy.get("perSpec");
        Map<?, ?> sx = (Map<?, ?>) perSpec.get("SpecX");
        assertEquals(2, ((Number) sx.get("ajcTp")).intValue());
        assertEquals(2, ((Number) sx.get("dexTp")).intValue());
        assertEquals(0, ((Number) sx.get("ajcFp")).intValue());
        assertEquals(0, ((Number) sx.get("dexFp")).intValue());
        assertTrue((boolean) sx.get("passed"));

        // Optional report dump for manual inspection.
        String dumpPath = System.getProperty("dumpLayer3Sample");
        if (dumpPath != null) r.write(Path.of(dumpPath));
    }

    @Test
    void dexlib2MissesOneEvent(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path apkDir = Files.createDirectories(tmp.resolve("apks"));
        Files.writeString(oracleDir.resolve("toy-oracle.yaml"),
                "name: toy\n"
              + "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: SpecX\n"
              + "    error_type: ErrA\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n"
              + "  - id: 2\n"
              + "    spec: SpecX\n"
              + "    error_type: ErrB\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n");
        Path traceDir = Files.createDirectories(apkDir.resolve("toy"));
        Files.writeString(traceDir.resolve("ajc.logcat"),
                "RVSEC: [SpecX] ErrA: detail one\n"
              + "RVSEC: [SpecX] ErrB: detail two\n");
        Files.writeString(traceDir.resolve("dexlib2.logcat"),
                "RVSEC: [SpecX] ErrA: detail one\n");

        Report r = TraceComparator.compare(oracleDir, apkDir);
        assertFalse(r.passed, () -> "expected gate fail; got: " + r.message);

        Map<?, ?> perOracle = (Map<?, ?>) r.metrics.get("perOracle");
        Map<?, ?> toy = (Map<?, ?>) perOracle.get("toy");
        Map<?, ?> perSpec = (Map<?, ?>) toy.get("perSpec");
        Map<?, ?> sx = (Map<?, ?>) perSpec.get("SpecX");
        // dex: TP=1, FP=0, FN=1 -> P=1.0, R=0.5, F1 = 2*1*0.5/1.5 = 0.6667
        assertEquals(0.6667, ((Number) sx.get("dexF1")).doubleValue(), 1e-4);
        assertEquals(1.0, ((Number) sx.get("ajcF1")).doubleValue(), 1e-9);
        assertFalse((boolean) sx.get("passed"));
    }

    @Test
    void kappaDetectsDisagreement(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path apkDir = Files.createDirectories(tmp.resolve("apks"));
        // Four oracle events, all on SpecX, distinguished by error_type.
        Files.writeString(oracleDir.resolve("toy-oracle.yaml"),
                "name: toy\n"
              + "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: SpecX\n"
              + "    error_type: E1\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n"
              + "  - id: 2\n"
              + "    spec: SpecX\n"
              + "    error_type: E2\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n"
              + "  - id: 3\n"
              + "    spec: SpecX\n"
              + "    error_type: E3\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n"
              + "  - id: 4\n"
              + "    spec: SpecX\n"
              + "    error_type: E4\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n");
        Path traceDir = Files.createDirectories(apkDir.resolve("toy"));
        // ajc fires events 1+2, dexlib2 fires events 3+4: zero overlap -> kappa=0.
        Files.writeString(traceDir.resolve("ajc.logcat"),
                "RVSEC: [SpecX] E1: x\n"
              + "RVSEC: [SpecX] E2: x\n");
        Files.writeString(traceDir.resolve("dexlib2.logcat"),
                "RVSEC: [SpecX] E3: x\n"
              + "RVSEC: [SpecX] E4: x\n");

        Report r = TraceComparator.compare(oracleDir, apkDir);
        assertFalse(r.passed, () -> "expected gate fail; got: " + r.message);

        Map<?, ?> perOracle = (Map<?, ?>) r.metrics.get("perOracle");
        Map<?, ?> toy = (Map<?, ?>) perOracle.get("toy");
        Map<?, ?> perSpec = (Map<?, ?>) toy.get("perSpec");
        Map<?, ?> sx = (Map<?, ?>) perSpec.get("SpecX");
        // Po = 0/4 = 0 (every item disagrees), Pa1 = 0.5, Pb1 = 0.5,
        // Pe = 0.5*0.5 + 0.5*0.5 = 0.5, kappa = (0 - 0.5) / 0.5 = -1.0
        assertEquals(-1.0, ((Number) sx.get("kappa")).doubleValue(), 1e-9);
        // Both pipelines have F1 = 0.667 (TP=2, FN=2) so the F1 gate fails too.
        assertFalse((boolean) sx.get("passed"));
    }

    @Test
    void messageSubstringFiltersFalsePositive(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path apkDir = Files.createDirectories(tmp.resolve("apks"));
        Files.writeString(oracleDir.resolve("toy-oracle.yaml"),
                "name: toy\n"
              + "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: MessageDigestSpec\n"
              + "    error_type: UnsafeAlgorithm\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: \"MD5\"\n");
        Path traceDir = Files.createDirectories(apkDir.resolve("toy"));
        // ajc does fire the MD5 event correctly.
        Files.writeString(traceDir.resolve("ajc.logcat"),
                "RVSEC: [MessageDigestSpec] UnsafeAlgorithm: but found MD5.\n");
        // dexlib2 fires the same spec/etype but with SHA-1: not a TP, it's a FP.
        Files.writeString(traceDir.resolve("dexlib2.logcat"),
                "RVSEC: [MessageDigestSpec] UnsafeAlgorithm: but found SHA-1\n");

        Report r = TraceComparator.compare(oracleDir, apkDir);
        assertFalse(r.passed, () -> "expected gate fail; got: " + r.message);

        Map<?, ?> perOracle = (Map<?, ?>) r.metrics.get("perOracle");
        Map<?, ?> toy = (Map<?, ?>) perOracle.get("toy");
        Map<?, ?> perSpec = (Map<?, ?>) toy.get("perSpec");
        Map<?, ?> sx = (Map<?, ?>) perSpec.get("MessageDigestSpec");
        // dex: TP=0, FP=1, FN=1 -> recall = 0.0, F1 = 0.0
        assertEquals(0, ((Number) sx.get("dexTp")).intValue());
        assertEquals(1, ((Number) sx.get("dexFp")).intValue());
        assertEquals(1, ((Number) sx.get("dexFn")).intValue());
        assertEquals(0.0, ((Number) sx.get("dexF1")).doubleValue(), 1e-9);
        assertFalse((boolean) sx.get("passed"));
    }

    @Test
    void emptyOracleIsSkipped(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path apkDir = Files.createDirectories(tmp.resolve("apks"));
        // Mirrors hateitorrateit slot: structural file with empty list.
        Files.writeString(oracleDir.resolve("empty-oracle.yaml"),
                "name: empty\n"
              + "expected_events: []\n");
        // Plus one real oracle with passing traces, so the gate evaluates.
        Files.writeString(oracleDir.resolve("good-oracle.yaml"),
                "name: good\n"
              + "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: SpecX\n"
              + "    error_type: ErrA\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n");
        Path traceDir = Files.createDirectories(apkDir.resolve("good"));
        Files.writeString(traceDir.resolve("ajc.logcat"), "RVSEC: [SpecX] ErrA: ok\n");
        Files.writeString(traceDir.resolve("dexlib2.logcat"), "RVSEC: [SpecX] ErrA: ok\n");

        Report r = TraceComparator.compare(oracleDir, apkDir);
        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message);
        @SuppressWarnings("unchecked")
        java.util.List<String> empties = (java.util.List<String>) r.metrics.get("emptyOracles");
        assertEquals(1, empties.size());
        assertEquals("empty", empties.get(0));
    }
}
