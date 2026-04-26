package br.unb.cic.rv.validator;

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
 * Unit tests for {@link BootValidator#analyze(Path, Path)}. Each test
 * builds two parallel logcat trees ({@code ajc/<apk>/<rep>.logcat} and
 * {@code dexlib2/<apk>/<rep>.logcat}) under {@code @TempDir} and asserts
 * on the {@link Report} fields. No emulator. The capture-mode IO path is
 * exercised manually per the BootValidator class javadoc.
 */
class BootValidatorTest {

    private static final String VE_FOO =
            "Verifier rejected class com.foo.Bar: void m() failed to verify";
    private static final String VE_BAZ =
            "Verifier rejected class com.baz.Qux: int run() bad type on operand stack";
    private static final String VE_NEW =
            "Verifier rejected class com.new1.Site: void m() bytecode regression";

    @Test
    void bothPipelinesCleanLogcats(@TempDir Path tmp) throws Exception {
        Path ajcDir = Files.createDirectories(tmp.resolve("ajc"));
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        writeLogcat(ajcDir, "com.example_1.apk", noiseOnly());
        writeLogcat(dexDir, "com.example_1.apk", noiseOnly());

        Report r = BootValidator.analyze(ajcDir, dexDir);
        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message);
        assertEquals(0, ((Number) r.metrics.get("totalRegressions")).intValue());
        assertEquals(1, ((Number) r.metrics.get("totalPairs")).intValue());
        assertEquals(1, ((Number) r.metrics.get("apksClean")).intValue());

        // Optional report dump for manual inspection.
        String dumpPath = System.getProperty("dumpLayer2Sample");
        if (dumpPath != null) r.write(Path.of(dumpPath));
    }

    @Test
    void dexlib2IntroducesNewVe(@TempDir Path tmp) throws Exception {
        Path ajcDir = Files.createDirectories(tmp.resolve("ajc"));
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        writeLogcat(ajcDir, "com.example_2.apk", noiseOnly());
        writeLogcat(dexDir, "com.example_2.apk", veLines(VE_NEW));

        Report r = BootValidator.analyze(ajcDir, dexDir);
        assertFalse(r.passed, () -> "expected gate fail; got: " + r.message);
        assertEquals(1, ((Number) r.metrics.get("totalRegressions")).intValue());
        Map<?, ?> perApk = (Map<?, ?>) r.metrics.get("perApk");
        Map<?, ?> entry = (Map<?, ?>) perApk.get("com.example_2.apk");
        assertEquals(0, ((Number) entry.get("ajcVeCount")).intValue());
        assertEquals(1, ((Number) entry.get("dexVeCount")).intValue());
        assertEquals(1, ((Number) entry.get("regressionCount")).intValue());
        List<?> newSites = (List<?>) entry.get("newSites");
        assertEquals(1, newSites.size());
        assertTrue(((String) newSites.get(0)).contains("com.new1.Site"));
    }

    @Test
    void sameVeOnBothSidesNotARegression(@TempDir Path tmp) throws Exception {
        Path ajcDir = Files.createDirectories(tmp.resolve("ajc"));
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        // Both pipelines hit the SAME flaky-framework VerifyError -> not a regression.
        writeLogcat(ajcDir, "com.example_3.apk", veLines(VE_FOO));
        writeLogcat(dexDir, "com.example_3.apk", veLines(VE_FOO));

        Report r = BootValidator.analyze(ajcDir, dexDir);
        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message);
        assertEquals(0, ((Number) r.metrics.get("totalRegressions")).intValue());
        Map<?, ?> perApk = (Map<?, ?>) r.metrics.get("perApk");
        Map<?, ?> entry = (Map<?, ?>) perApk.get("com.example_3.apk");
        assertEquals(1, ((Number) entry.get("ajcVeCount")).intValue());
        assertEquals(1, ((Number) entry.get("dexVeCount")).intValue());
        assertEquals(0, ((Number) entry.get("regressionCount")).intValue());
        assertEquals(0, ((List<?>) entry.get("newSites")).size());
    }

    @Test
    void multiplePairsAggregate(@TempDir Path tmp) throws Exception {
        Path ajcDir = Files.createDirectories(tmp.resolve("ajc"));
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        // APK A: clean on both sides.
        writeLogcat(ajcDir, "com.alpha.apk", noiseOnly());
        writeLogcat(dexDir, "com.alpha.apk", noiseOnly());
        // APK B: ajc has VE_BAZ (baseline), dexlib2 has VE_BAZ + VE_NEW (regression).
        writeLogcat(ajcDir, "com.bravo.apk", veLines(VE_BAZ));
        writeLogcat(dexDir, "com.bravo.apk", veLines(VE_BAZ, VE_NEW));

        Report r = BootValidator.analyze(ajcDir, dexDir);
        assertFalse(r.passed, () -> "expected gate fail; got: " + r.message);
        assertEquals(1, ((Number) r.metrics.get("totalRegressions")).intValue());
        assertEquals(2, ((Number) r.metrics.get("totalPairs")).intValue());
        assertEquals(1, ((Number) r.metrics.get("apksClean")).intValue());
        Map<?, ?> perApk = (Map<?, ?>) r.metrics.get("perApk");
        Map<?, ?> alpha = (Map<?, ?>) perApk.get("com.alpha.apk");
        Map<?, ?> bravo = (Map<?, ?>) perApk.get("com.bravo.apk");
        assertEquals(0, ((Number) alpha.get("regressionCount")).intValue());
        assertEquals(1, ((Number) bravo.get("regressionCount")).intValue());
    }

    // --- fixture builders ---------------------------------------------------

    private static void writeLogcat(Path root, String apkName, String body) throws Exception {
        Path apkDir = Files.createDirectories(root.resolve(apkName));
        Path logcat = apkDir.resolve(apkName + "__1__30__layer2.logcat");
        Files.writeString(logcat, body);
    }

    private static String noiseOnly() {
        return String.join("\n",
                "01-01 10:00:00.000  1234  1234 I ActivityManager: Start proc",
                "01-01 10:00:00.500  1234  1234 D OtherTag: nothing here",
                "01-01 10:00:01.000  1234  1234 I InputReader: monkey injected event",
                "") + "\n";
    }

    private static String veLines(String... sites) {
        StringBuilder sb = new StringBuilder();
        int i = 0;
        for (String site : sites) {
            sb.append("01-01 10:00:0")
                    .append(i++)
                    .append(".000  1234  1234 E AndroidRuntime: java.lang.VerifyError: ")
                    .append(site)
                    .append('\n');
        }
        return sb.toString();
    }
}
