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
 * Unit tests for {@link CoverageValidator}. Each test materializes two
 * parallel directory trees ({@code ajc/<apk>/<apk>.logcat} and
 * {@code dexlib2/<apk>/<apk>.logcat}) using {@code @TempDir} and asserts
 * on the {@link Report} fields. No real APKs / no emulator.
 */
class CoverageValidatorTest {

    private static final String SIG_INIT =
            "<com.mine.autoshine.MainActivity: void <init>()>";
    private static final String SIG_ON_CREATE =
            "<com.mine.autoshine.MainActivity: void onCreate(android.os.Bundle)>";
    private static final String SIG_ON_START =
            "<com.mine.autoshine.MainActivity: void onStart()>";
    private static final String SIG_ON_RESUME =
            "<com.mine.autoshine.MainActivity: void onResume()>";
    private static final String SIG_ON_PAUSE =
            "<com.mine.autoshine.MainActivity: void onPause()>";

    @Test
    void pairedDirsWithIdenticalCoverage(@TempDir Path tmp) throws Exception {
        Path ajcDir = Files.createDirectories(tmp.resolve("ajc"));
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        String body = covLines(SIG_INIT, SIG_ON_CREATE, SIG_ON_START, SIG_ON_RESUME, SIG_ON_PAUSE);
        writeLogcat(ajcDir, "com.mine.autoshine_3.apk", body);
        writeLogcat(dexDir, "com.mine.autoshine_3.apk", body);

        Report r = CoverageValidator.compare(ajcDir, dexDir);
        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message);
        assertEquals(1, r.metrics.get("totalPairs"));
        assertEquals(1.0, ((Number) r.metrics.get("aggregateRecall")).doubleValue(), 1e-9);
        assertEquals(0L, ((Number) r.metrics.get("aggregateDelta")).longValue());
        Map<?, ?> perApk = (Map<?, ?>) r.metrics.get("perApk");
        Map<?, ?> entry = (Map<?, ?>) perApk.get("com.mine.autoshine_3.apk");
        assertEquals(5, ((Number) entry.get("ajcCovered")).intValue());
        assertEquals(5, ((Number) entry.get("dexCovered")).intValue());
        assertEquals(5, ((Number) entry.get("intersect")).intValue());

        // Optional report dump for manual inspection.
        String dumpPath = System.getProperty("dumpLayer5Sample");
        if (dumpPath != null) r.write(Path.of(dumpPath));
    }

    @Test
    void dexlib2MissesTwoOfFive(@TempDir Path tmp) throws Exception {
        Path ajcDir = Files.createDirectories(tmp.resolve("ajc"));
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        writeLogcat(ajcDir, "a.apk",
                covLines(SIG_INIT, SIG_ON_CREATE, SIG_ON_START, SIG_ON_RESUME, SIG_ON_PAUSE));
        writeLogcat(dexDir, "a.apk",
                covLines(SIG_INIT, SIG_ON_CREATE, SIG_ON_START));

        Report r = CoverageValidator.compare(ajcDir, dexDir);
        assertFalse(r.passed, () -> "expected gate fail; got: " + r.message);
        assertEquals(0.6, ((Number) r.metrics.get("aggregateRecall")).doubleValue(), 1e-9);
        assertEquals(-2L, ((Number) r.metrics.get("aggregateDelta")).longValue());
        Map<?, ?> perApk = (Map<?, ?>) r.metrics.get("perApk");
        Map<?, ?> entry = (Map<?, ?>) perApk.get("a.apk");
        assertEquals(0.6, ((Number) entry.get("recall")).doubleValue(), 1e-9);
        assertEquals(-2, ((Number) entry.get("delta")).intValue());
    }

    @Test
    void noiseLinesIgnored(@TempDir Path tmp) throws Exception {
        Path ajcDir = Files.createDirectories(tmp.resolve("ajc"));
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        // Mix one real RVSEC-COV line with several noise lines that must NOT
        // be counted: a Layer-3 violation tag (RVSEC: ...) and a fake
        // RVSEC-COV-DEBUG variant whose tag has trailing chars after "COV".
        String body = String.join("\n",
                "04-25 16:50:44.921  3198  3198 I RVSEC-COV: " + SIG_INIT,
                "04-25 16:50:44.922  3198  3198 E RVSEC: [Spec] error something",
                "04-25 16:50:44.923  3198  3198 I RVSEC-COV-DEBUG: " + SIG_ON_CREATE,
                "04-25 16:50:44.924  3198  3198 D OtherTag: nothing here",
                "") + "\n";
        writeLogcat(ajcDir, "a.apk", body);
        writeLogcat(dexDir, "a.apk", body);

        Report r = CoverageValidator.compare(ajcDir, dexDir);
        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message);
        Map<?, ?> perApk = (Map<?, ?>) r.metrics.get("perApk");
        Map<?, ?> entry = (Map<?, ?>) perApk.get("a.apk");
        // Only the SIG_INIT line counts; SIG_ON_CREATE was on a noise tag.
        assertEquals(1, ((Number) entry.get("ajcCovered")).intValue());
        assertEquals(1, ((Number) entry.get("dexCovered")).intValue());
        assertEquals(1, ((Number) entry.get("intersect")).intValue());
    }

    // --- fixture builders ----------------------------------------------------

    private static void writeLogcat(Path root, String apkName, String body) throws Exception {
        Path apkDir = Files.createDirectories(root.resolve(apkName));
        Path logcat = apkDir.resolve(apkName + "__1__300__aperv:sata_mop.logcat");
        Files.writeString(logcat, body);
    }

    private static String covLines(String... sigs) {
        StringBuilder sb = new StringBuilder();
        int i = 0;
        for (String s : sigs) {
            sb.append("04-25 16:50:44.")
                    .append(String.format("%03d", 921 + i++))
                    .append("  3198  3198 I RVSEC-COV: ")
                    .append(s)
                    .append('\n');
        }
        return sb.toString();
    }
}
