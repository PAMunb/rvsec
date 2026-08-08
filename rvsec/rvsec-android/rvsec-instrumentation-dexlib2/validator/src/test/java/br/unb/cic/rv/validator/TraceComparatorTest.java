package br.unb.cic.rv.validator;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for {@link TraceComparator}. Each test materializes a small
 * oracle YAML + a paired pair of logcat fixtures under {@code @TempDir}
 * and asserts on the {@link Report} fields. No real APKs / no emulator.
 *
 * <p>
 * Every trace fixture is written in the format the on-device collector
 * actually emits — {@code ErrorSummary.toString()}'s six fields plus the
 * {@code expecting} text {@code ErrorCollector:37} appends, under a padded
 * logcat tag. The fixtures used to feed {@code [SpecX] ErrA: detail one},
 * a shape nothing in the pipeline produces; they were the last thing keeping
 * that invented format alive, so they are rewritten rather than adapted.
 */
class TraceComparatorTest {

    /** Minimal admissible provenance — {@code compare} enforces admission (D-O6). */
    private static final String PROVENANCE =
            "provenance:\n"
          + "  class: hand_validated\n"
          + "  source: synthetic fixture for TraceComparatorTest\n";

    /**
     * One violation line exactly as logcat renders it: the {@code threadtime}
     * prefix, the tag padded to its column width, then the collector's seven
     * comma-separated fields.
     */
    private static String line(String spec, String classQualified, String className,
                               String method, String location, String errorType,
                               String expecting) {
        return "08-06 18:17:04.465  3144  3457 V RVSEC   : "
                + String.join(",", spec, classQualified, className, method,
                              location, errorType, expecting)
                + "\n";
    }

    /** Shorthand for a fixture whose class is only meaningful in its short form. */
    private static String line(String spec, String className, String method, String errorType,
                               String expecting) {
        return line(spec, "com.example." + className, className, method,
                    className + ".java:1", errorType, expecting);
    }

    @Test
    void bothPipelinesHitAllOracleEvents(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path apkDir = Files.createDirectories(tmp.resolve("apks"));
        Files.writeString(oracleDir.resolve("toy-oracle.yaml"),
                "name: toy\n"
              + PROVENANCE
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
        String body = line("SpecX", "C", "m", "ErrA", "detail one")
                    + line("SpecX", "C", "m", "ErrB", "detail two");
        Files.writeString(traceDir.resolve("ajc.logcat"), body);
        Files.writeString(traceDir.resolve("dexlib2.logcat"), body);

        Report r = TraceComparator.compare(oracleDir, apkDir);
        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message);
        assertEquals(1, ((Number) r.metrics.get("totalOracles")).intValue());
        assertEquals(1.0, ((Number) r.metrics.get("minDexF1")).doubleValue(), 1e-9);
        assertEquals(1.0, ((Number) r.metrics.get("minKappa")).doubleValue(), 1e-9);

        Map<?, ?> sx = specMetrics(r, "toy", "SpecX");
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
              + PROVENANCE
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
                line("SpecX", "C", "m", "ErrA", "detail one")
              + line("SpecX", "C", "m", "ErrB", "detail two"));
        Files.writeString(traceDir.resolve("dexlib2.logcat"),
                line("SpecX", "C", "m", "ErrA", "detail one"));

        Report r = TraceComparator.compare(oracleDir, apkDir);
        assertFalse(r.passed, () -> "expected gate fail; got: " + r.message);

        Map<?, ?> sx = specMetrics(r, "toy", "SpecX");
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
              + PROVENANCE
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
                line("SpecX", "C", "m", "E1", "x")
              + line("SpecX", "C", "m", "E2", "x"));
        Files.writeString(traceDir.resolve("dexlib2.logcat"),
                line("SpecX", "C", "m", "E3", "x")
              + line("SpecX", "C", "m", "E4", "x"));

        Report r = TraceComparator.compare(oracleDir, apkDir);
        assertFalse(r.passed, () -> "expected gate fail; got: " + r.message);

        Map<?, ?> sx = specMetrics(r, "toy", "SpecX");
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
              + PROVENANCE
              + "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: MessageDigestSpec\n"
              + "    error_type: UnsafeAlgorithm\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: \"MD5\"\n");
        Path traceDir = Files.createDirectories(apkDir.resolve("toy"));
        // ajc does fire the MD5 event correctly.
        Files.writeString(traceDir.resolve("ajc.logcat"),
                line("MessageDigestSpec", "C", "m", "UnsafeAlgorithm", "but found MD5."));
        // dexlib2 fires the same spec/etype but with SHA-1: not a TP, it's a FP.
        Files.writeString(traceDir.resolve("dexlib2.logcat"),
                line("MessageDigestSpec", "C", "m", "UnsafeAlgorithm", "but found SHA-1"));

        Report r = TraceComparator.compare(oracleDir, apkDir);
        assertFalse(r.passed, () -> "expected gate fail; got: " + r.message);

        Map<?, ?> sx = specMetrics(r, "toy", "MessageDigestSpec");
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
              + PROVENANCE
              + "expected_events: []\n");
        // Plus one real oracle with passing traces, so the gate evaluates.
        Files.writeString(oracleDir.resolve("good-oracle.yaml"),
                "name: good\n"
              + PROVENANCE
              + "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: SpecX\n"
              + "    error_type: ErrA\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n");
        Path traceDir = Files.createDirectories(apkDir.resolve("good"));
        String body = line("SpecX", "C", "m", "ErrA", "ok");
        Files.writeString(traceDir.resolve("ajc.logcat"), body);
        Files.writeString(traceDir.resolve("dexlib2.logcat"), body);

        Report r = TraceComparator.compare(oracleDir, apkDir);
        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message);
        @SuppressWarnings("unchecked")
        java.util.List<String> empties = (java.util.List<String>) r.metrics.get("emptyOracles");
        assertEquals(1, empties.size());
        assertEquals("empty", empties.get(0));
    }

    /**
     * The measured case from D-O4, and the reason location has to be matched.
     *
     * <p>
     * {@code MessageDigestSpec/InvalidSequenceOfMethodCalls} is reported once by
     * {@code ajc} at {@code jh.h.c} and once by {@code dexlib2} at
     * {@code okio.ByteString.digest$okio}. These are two different misuses in
     * two different apps. Keyed on {@code (spec, errorType)} alone they score as
     * one agreement — the comparator would report perfect agreement about a site
     * neither pipeline shares. With location they score as what they are: the
     * oracle's site is missed (one FN) and an unexpected site is reported (one
     * FP).
     */
    @Test
    void differentSitesOfOneSpecAreNotOneAgreement(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path apkDir = Files.createDirectories(tmp.resolve("apks"));
        Files.writeString(oracleDir.resolve("sites-oracle.yaml"),
                "name: sites\n"
              + PROVENANCE
              + "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: MessageDigestSpec\n"
              + "    error_type: InvalidSequenceOfMethodCalls\n"
              + "    location: { class: jh.h, method: c }\n"
              + "    expected_message_substring: null\n");
        Path traceDir = Files.createDirectories(apkDir.resolve("sites"));
        Files.writeString(traceDir.resolve("ajc.logcat"),
                line("MessageDigestSpec", "jh.h", "h", "c", "SourceFile:17",
                     "InvalidSequenceOfMethodCalls", "unknown"));
        Files.writeString(traceDir.resolve("dexlib2.logcat"),
                line("MessageDigestSpec", "okio.ByteString", "ByteString", "digest$okio",
                     "ByteString.kt:17", "InvalidSequenceOfMethodCalls", "unknown"));

        Report r = TraceComparator.compare(oracleDir, apkDir);
        Map<?, ?> sx = specMetrics(r, "sites", "MessageDigestSpec");
        assertEquals(1, ((Number) sx.get("ajcTp")).intValue(), "ajc is at the oracle's site");
        assertEquals(0, ((Number) sx.get("ajcFp")).intValue());
        assertEquals(0, ((Number) sx.get("dexTp")).intValue(),
                "dexlib2 is at a different site: not a true positive");
        assertEquals(1, ((Number) sx.get("dexFn")).intValue(), "the oracle's site was missed");
        assertEquals(1, ((Number) sx.get("dexFp")).intValue(), "a site the oracle does not have");
        assertFalse((boolean) sx.get("passed"));
    }

    /**
     * An oracle event that declares no location keeps matching on
     * {@code (spec, errorType)} — the deliberate escape hatch of D-O4, for an
     * oracle author with no site to name.
     */
    @Test
    void oracleWithoutLocationStillMatchesAnySite(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path apkDir = Files.createDirectories(tmp.resolve("apks"));
        Files.writeString(oracleDir.resolve("loose-oracle.yaml"),
                "name: loose\n"
              + PROVENANCE
              + "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: SpecX\n"
              + "    error_type: ErrA\n"
              + "    expected_message_substring: null\n");
        Path traceDir = Files.createDirectories(apkDir.resolve("loose"));
        String body = line("SpecX", "somewhere.Else", "Else", "whatever",
                           "Else.java:9", "ErrA", "unknown");
        Files.writeString(traceDir.resolve("ajc.logcat"), body);
        Files.writeString(traceDir.resolve("dexlib2.logcat"), body);

        Report r = TraceComparator.compare(oracleDir, apkDir);
        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message);
        Map<?, ?> sx = specMetrics(r, "loose", "SpecX");
        assertEquals(1, ((Number) sx.get("dexTp")).intValue());
        assertEquals(0, ((Number) sx.get("dexFp")).intValue());
    }

    /** An oracle whose provenance is rejected contributes to no verdict (D-O6). */
    @Test
    void circularOracleIsNotScored(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path apkDir = Files.createDirectories(tmp.resolve("apks"));
        Files.writeString(oracleDir.resolve("circular-oracle.yaml"),
                "name: circular\n"
              + "provenance:\n"
              + "  class: derived_from_independent_weaver\n"
              + "  source_weaver: dexlib2\n"
              + "  source_data: somewhere.csv\n"
              + "  source_sha256: deadbeef\n"
              + "  derivation_script: nope.py\n"
              + "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: SpecX\n"
              + "    error_type: ErrA\n"
              + "    expected_message_substring: null\n");
        Path traceDir = Files.createDirectories(apkDir.resolve("circular"));
        String body = line("SpecX", "C", "m", "ErrA", "ok");
        Files.writeString(traceDir.resolve("ajc.logcat"), body);
        Files.writeString(traceDir.resolve("dexlib2.logcat"), body);

        Report r = TraceComparator.compare(oracleDir, apkDir);
        assertFalse(r.passed, "a directory of only inadmissible oracles cannot pass");
        assertEquals(0, ((Number) r.metrics.get("totalOracles")).intValue());
        assertEquals(1, ((Number) r.metrics.get("discoveredOracles")).intValue());
        Map<?, ?> rejected = (Map<?, ?>) r.metrics.get("rejectedOracles");
        assertTrue(rejected.containsKey("circular-oracle.yaml"));
        assertTrue(String.valueOf(rejected.get("circular-oracle.yaml")).contains("circular"));
    }

    /**
     * A spec reported by the pipeline but absent from the oracle is scored, and
     * every event under it is a false positive.
     *
     * <p>
     * This is the shape a wrapper-registry collision takes: the call site is
     * bound to the <em>wrong</em> specification, so it surfaces under a spec the
     * independent weaver never reported for this APK — which is exactly the spec
     * the oracle has no entry for. Scoring only the oracle's own specs made the
     * gate blind to the one defect the paired profile exists to discriminate.
     */
    @Test
    void specAbsentFromTheOracleIsStillScored(@TempDir Path tmp) throws Exception {
        Path oracleDir = Files.createDirectories(tmp.resolve("oracles"));
        Path apkDir = Files.createDirectories(tmp.resolve("apks"));
        Files.writeString(oracleDir.resolve("collision-oracle.yaml"),
                "name: collision\n"
              + PROVENANCE
              + "expected_events:\n"
              + "  - id: 1\n"
              + "    spec: SpecX\n"
              + "    error_type: ErrA\n"
              + "    location: { class: C, method: m }\n"
              + "    expected_message_substring: null\n");
        Path traceDir = Files.createDirectories(apkDir.resolve("collision"));
        Files.writeString(traceDir.resolve("ajc.logcat"),
                line("SpecX", "C", "m", "ErrA", "ok"));
        // dexlib2 fires the same site under a specification the ground truth
        // never reports here: the wrong binding, not a missing one.
        Files.writeString(traceDir.resolve("dexlib2.logcat"),
                line("SpecX", "C", "m", "ErrA", "ok")
              + line("SpecWrong", "C", "m", "ErrA", "ok"));

        Report r = TraceComparator.compare(oracleDir, apkDir);
        Map<?, ?> wrong = specMetrics(r, "collision", "SpecWrong");
        assertEquals(1, ((Number) wrong.get("dexFp")).intValue(),
                "an event under a spec the oracle does not declare is a false positive");
        assertEquals(0, ((Number) wrong.get("ajcFp")).intValue(),
                "the independent weaver never reported it");
        assertFalse(r.passed, "a fabricated specification binding must fail the gate");
    }

    // --- format tests, against a verbatim recorded line ----------------------

    /**
     * A line copied byte-for-byte out of
     * {@code data/results/cmp163_00/.../app.eduroam.geteduroam_2685.apk__1__300__aperv:mop_on_llm_off.logcat}
     * recorded on 2026-08-06. It exercises the three properties the parser has
     * to get right on real input at once: the tag is padded, the {@code
     * expecting} text carries its own comma, and the class arrives in both
     * forms.
     */
    private static final String RECORDED_LINE =
            "08-06 18:17:04.465  3144  3457 V RVSEC   : TrustManagerFactorySpec,"
            + "okhttp3.internal.platform.Platform,Platform,platformTrustManager,"
            + "Platform.kt:80,UnsafeAlgorithm,expecting one of PKIX,SunX509 but found .";

    @Test
    void parsesARecordedViolationLine(@TempDir Path tmp) throws Exception {
        Path logcat = tmp.resolve("recorded.logcat");
        Files.writeString(logcat, RECORDED_LINE + "\n");

        List<TraceComparator.ObservedEvent> events = TraceComparator.parseObserved(logcat);
        assertEquals(1, events.size(), "the padded RVSEC tag must be accepted");
        TraceComparator.ObservedEvent e = events.get(0);
        assertEquals("TrustManagerFactorySpec", e.spec());
        assertEquals("UnsafeAlgorithm", e.etype());
        assertEquals("okhttp3.internal.platform.Platform", e.classQualified());
        assertEquals("Platform", e.className());
        assertEquals("platformTrustManager", e.method());
        assertEquals("Platform.kt:80", e.location());
        assertEquals("expecting one of PKIX,SunX509 but found .", e.msg(),
                "fields 6+ are rejoined: the expecting text carries its own comma");
    }

    /**
     * The coverage tag shares the {@code RVSEC} prefix and outnumbers violation
     * lines by three orders of magnitude in a real recording (2,266 to 5). A
     * parser that accepted it would fabricate events out of package signatures.
     */
    @Test
    void coverageLinesAreNotViolations(@TempDir Path tmp) throws Exception {
        Path logcat = tmp.resolve("mixed.logcat");
        Files.writeString(logcat,
                "08-06 18:17:00.647  3144  3144 I RVSEC-COV: "
                        + "<app.eduroam.geteduroam.AndroidApp: void <clinit>()>\n"
              + RECORDED_LINE + "\n"
              + "08-06 18:17:00.805  3144  3144 I RVSEC-COV: "
                        + "<app.eduroam.geteduroam.AndroidApp: void onCreate()>\n");

        List<TraceComparator.ObservedEvent> events = TraceComparator.parseObserved(logcat);
        assertEquals(1, events.size(), "only the RVSEC violation line counts");
        assertEquals("TrustManagerFactorySpec", events.get(0).spec());
    }

    /**
     * An {@code RVSEC} line whose payload is not a violation record — too few
     * fields — is skipped rather than mis-split. Guessing at it would inject a
     * fabricated event into a comparison.
     */
    @Test
    void shortPayloadIsSkipped(@TempDir Path tmp) throws Exception {
        Path logcat = tmp.resolve("short.logcat");
        Files.writeString(logcat,
                "08-06 18:17:04.465  3144  3457 V RVSEC   : some,diagnostic,text\n");
        assertEquals(List.of(), TraceComparator.parseObserved(logcat));
    }

    private static Map<?, ?> specMetrics(Report r, String oracleName, String spec) {
        Map<?, ?> perOracle = (Map<?, ?>) r.metrics.get("perOracle");
        Map<?, ?> oracle = (Map<?, ?>) perOracle.get(oracleName);
        assertNotNull(oracle, () -> "oracle '" + oracleName + "' was not scored: " + r.message);
        Map<?, ?> perSpec = (Map<?, ?>) oracle.get("perSpec");
        Map<?, ?> sx = (Map<?, ?>) perSpec.get(spec);
        assertNotNull(sx, () -> "spec '" + spec + "' absent from " + perSpec.keySet());
        return sx;
    }
}
