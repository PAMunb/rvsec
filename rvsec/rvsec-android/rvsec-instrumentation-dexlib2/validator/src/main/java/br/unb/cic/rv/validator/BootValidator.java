package br.unb.cic.rv.validator;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.UncheckedIOException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * Layer-2 boot regression validator. Splits into a pure-data analyzer and
 * a thin-IO capture mode so the gate logic is fully unit-testable while
 * the actual emulator interaction stays a thin shell over {@code adb}.
 *
 * <h2>Pure-data analyzer ({@link #analyze})</h2>
 * Pairs ajc and dexlib2 logcat captures by APK name (immediate parent
 * directory of each {@code .logcat} file, same convention as
 * {@link CoverageValidator}). For each pair, extracts the set of distinct
 * {@code VerifyError} sites — the substring that follows {@code VerifyError:}
 * up to end-of-line, trimmed and de-duplicated per APK. A regression is any
 * VE site that appears in dexlib2 but NOT in the ajc baseline (set
 * difference, NOT count). The gate passes iff total regressions across
 * all pairs is zero.
 *
 * <h2>Thin-IO capture mode ({@link #capture})</h2>
 * Drives {@code adb install / monkey / logcat -d} for every {@code .apk}
 * under a directory, on an emulator already managed by rv-platform.
 * Critically does NOT start, stop, or otherwise manage the emulator
 * lifecycle (CLAUDE.md rule). Returns operational metadata as a
 * {@link CaptureReport}, not a {@link Report} — capture is not itself a
 * gate; the resulting logcats are then fed back through {@link #analyze}.
 *
 * <p>Manual smoke for capture mode:
 * <pre>{@code
 *   # An emulator must already be attached (managed by rv-platform).
 *   adb devices
 *   java -jar validator-cli.jar layer2 --capture \
 *        --apk-dir build/instrumented/dexlib2 \
 *        --output  build/logcat/dexlib2 \
 *        --seconds 30 --report build/reports/layer2-capture.json
 * }</pre>
 */
public final class BootValidator {

    public static final String LAYER_NAME = "layer2-boot-validator";

    /** Distinct-VE-site signature: everything after "VerifyError:" up to EOL, trimmed. */
    private static final Pattern VE_SITE = Pattern.compile("VerifyError:\\s*(.+)$");

    /** Cap on diagnostic "new VE sites" listed per APK, to keep reports compact. */
    private static final int MAX_DIAGNOSTIC_SITES = 5;

    private BootValidator() {}

    // --- analyze (pure data) ------------------------------------------------

    public static Report analyze(Path ajcLogcatDir, Path dexlibLogcatDir) throws IOException {
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("ajcLogcatDir", ajcLogcatDir.toString());
        metrics.put("dexlibLogcatDir", dexlibLogcatDir.toString());
        metrics.put("gateRegressionThreshold", 0);

        boolean ajcOk = Files.isDirectory(ajcLogcatDir);
        boolean dexOk = Files.isDirectory(dexlibLogcatDir);
        if (!ajcOk || !dexOk) {
            metrics.put("ajcDirExists", ajcOk);
            metrics.put("dexlibDirExists", dexOk);
            return new Report(LAYER_NAME, false,
                    "input directory missing or not a directory", metrics);
        }

        Map<String, Set<String>> ajcByApk = collectByApk(ajcLogcatDir);
        Map<String, Set<String>> dexByApk = collectByApk(dexlibLogcatDir);
        List<String> skipped = collectSkippedRelative(ajcLogcatDir, dexlibLogcatDir,
                ajcByApk.keySet(), dexByApk.keySet());

        Set<String> paired = new TreeSet<>(ajcByApk.keySet());
        paired.retainAll(dexByApk.keySet());

        Map<String, Map<String, Object>> perApk = new LinkedHashMap<>();
        int totalRegressions = 0;
        int apksClean = 0;

        for (String apk : paired) {
            Set<String> aSites = ajcByApk.getOrDefault(apk, Collections.emptySet());
            Set<String> dSites = dexByApk.getOrDefault(apk, Collections.emptySet());

            List<String> newSites = new ArrayList<>();
            for (String s : dSites) {
                if (!aSites.contains(s)) {
                    if (newSites.size() < MAX_DIAGNOSTIC_SITES) newSites.add(s);
                }
            }
            int regressionCount = 0;
            for (String s : dSites) if (!aSites.contains(s)) regressionCount++;

            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("ajcVeCount", aSites.size());
            entry.put("dexVeCount", dSites.size());
            entry.put("regressionCount", regressionCount);
            entry.put("newSites", newSites);
            perApk.put(apk, entry);

            totalRegressions += regressionCount;
            if (regressionCount == 0) apksClean++;
        }

        boolean passed = totalRegressions == 0;

        metrics.put("totalPairs", paired.size());
        metrics.put("skippedNotPaired", skipped);
        metrics.put("perApk", perApk);
        metrics.put("totalRegressions", totalRegressions);
        metrics.put("apksClean", apksClean);

        String message = String.format(Locale.ROOT,
                "boot regressions: %d (gate %s)",
                totalRegressions, passed ? "passed" : "failed");
        return new Report(LAYER_NAME, passed, message, metrics);
    }

    /** Distinct VE sites in one logcat file. Returns the set of trimmed post-prefix strings. */
    static Set<String> extractVerifyErrorSites(Path logcatFile) throws IOException {
        Set<String> out = new LinkedHashSet<>();
        var decoder = java.nio.charset.Charset.defaultCharset().newDecoder()
                .onMalformedInput(CodingErrorAction.IGNORE)
                .onUnmappableCharacter(CodingErrorAction.IGNORE);
        try (var reader = new BufferedReader(
                new InputStreamReader(Files.newInputStream(logcatFile), decoder));
             Stream<String> lines = reader.lines()) {
            lines.forEach(line -> {
                Matcher m = VE_SITE.matcher(line);
                if (m.find()) {
                    String site = m.group(1).trim();
                    if (!site.isEmpty()) out.add(site);
                }
            });
        }
        return out;
    }

    private static Map<String, Set<String>> collectByApk(Path root) throws IOException {
        Map<String, Set<String>> out = new TreeMap<>();
        try (Stream<Path> stream = Files.walk(root)) {
            stream.filter(Files::isRegularFile)
                    .filter(p -> p.getFileName().toString().endsWith(".logcat"))
                    .forEach(p -> {
                        Path parent = p.getParent();
                        String apk = parent == null ? "" : parent.getFileName().toString();
                        Set<String> sites = out.computeIfAbsent(apk, k -> new LinkedHashSet<>());
                        try {
                            sites.addAll(extractVerifyErrorSites(p));
                        } catch (IOException e) {
                            throw new UncheckedIOException(e);
                        }
                    });
        } catch (UncheckedIOException e) {
            throw e.getCause();
        }
        return out;
    }

    private static List<String> collectSkippedRelative(Path ajcRoot, Path dexRoot,
                                                       Set<String> ajcKeys, Set<String> dexKeys)
            throws IOException {
        List<String> out = new ArrayList<>();
        Set<String> onlyAjc = new TreeSet<>(ajcKeys);
        onlyAjc.removeAll(dexKeys);
        Set<String> onlyDex = new TreeSet<>(dexKeys);
        onlyDex.removeAll(ajcKeys);
        for (String apk : onlyAjc) {
            for (String rel : listLogcatRel(ajcRoot, apk)) out.add(rel + " (missing in dexlib2)");
        }
        for (String apk : onlyDex) {
            for (String rel : listLogcatRel(dexRoot, apk)) out.add(rel + " (missing in ajc)");
        }
        return out;
    }

    private static List<String> listLogcatRel(Path root, String apkName) throws IOException {
        List<String> out = new ArrayList<>();
        try (Stream<Path> stream = Files.walk(root)) {
            stream.filter(Files::isRegularFile)
                    .filter(p -> p.getFileName().toString().endsWith(".logcat"))
                    .filter(p -> {
                        Path parent = p.getParent();
                        return parent != null && apkName.equals(parent.getFileName().toString());
                    })
                    .map(p -> root.relativize(p).toString())
                    .sorted()
                    .forEach(out::add);
        }
        return out;
    }

    // --- capture (thin IO) --------------------------------------------------

    public static CaptureReport capture(Path apkDir, Path outputDir, BootCaptureOptions opts)
            throws IOException {
        if (opts == null) opts = new BootCaptureOptions();
        Files.createDirectories(outputDir);

        List<Path> apks = new ArrayList<>();
        if (Files.isDirectory(apkDir)) {
            try (Stream<Path> ls = Files.list(apkDir)) {
                ls.filter(Files::isRegularFile)
                        .filter(p -> p.getFileName().toString().endsWith(".apk"))
                        .sorted()
                        .forEach(apks::add);
            }
        }

        Map<String, String> failures = new LinkedHashMap<>();
        int succeeded = 0;
        String adb = opts.adbBinary == null ? "adb" : opts.adbBinary.toString();

        for (Path apk : apks) {
            String name = apk.getFileName().toString();
            try {
                String pkg = extractPackageName(apk, opts.aapt2Binary);
                if (pkg == null || pkg.isEmpty()) {
                    failures.put(name, "could not extract package name from manifest");
                    continue;
                }
                Path apkOutDir = Files.createDirectories(outputDir.resolve(stripExt(name)));
                Path bootLog = apkOutDir.resolve("boot.logcat");

                // The per-APK adb sequence below is ORDER-SENSITIVE: each step
                // establishes a precondition the next one relies on. Doing them
                // out of order silently corrupts the capture (e.g. picking up a
                // stale install's logcat lines, or stalling on a permission
                // prompt).

                // Step 1: uninstall any prior copy so the reinstall starts from
                // a clean slate — a leftover install from an earlier run could
                // keep granted permissions or cached state that masks a
                // regression we are trying to reproduce.
                runAdb(adb, opts.adbSerial, 10, "uninstall", pkg);

                // Step 2: install fresh with -r (reinstall keeping data if any)
                // and -g (grant ALL runtime permissions at install time). -g is
                // essential: without it the app would block on a runtime
                // permission dialog during the monkey run, producing no boot
                // trace and a false "clean" capture.
                int instExit = runAdb(adb, opts.adbSerial, 60, "install", "-r", "-g", apk.toString());
                if (instExit != 0) {
                    failures.put(name, "adb install failed with exit " + instExit);
                    continue;
                }

                // Step 3: clear the device log buffer so ONLY this run's lines
                // are captured. Must come AFTER install (install itself emits
                // PackageManager chatter we don't want) and BEFORE launch.
                runAdb(adb, opts.adbSerial, 10, "logcat", "-c");

                // Step 4: drive the app with a single monkey event. This is a
                // boot smoke test — one event is enough to force class loading
                // and surface any VerifyError raised while verifying the woven
                // bytecode; we are not exercising features here.
                runAdb(adb, opts.adbSerial, 10, "shell", "monkey", "-p", pkg, "-v", "1");

                // Step 5: sleep so the app has time to boot, load classes, and
                // let any asynchronous VerifyError reach the log buffer before
                // we dump it.
                try {
                    Thread.sleep(Math.max(1, opts.captureSeconds) * 1000L);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    failures.put(name, "interrupted during capture sleep");
                    continue;
                }

                // Step 6: dump (-d = print-and-exit, not follow) the buffer to
                // the per-APK boot.logcat that analyze() will later scan for
                // VerifyError sites. threadtime format keeps tag/pid columns.
                int dumpExit = runAdbToFile(adb, opts.adbSerial, 60, bootLog,
                        "logcat", "-d", "-v", "threadtime");
                if (dumpExit != 0) {
                    failures.put(name, "adb logcat -d failed with exit " + dumpExit);
                    continue;
                }

                // Step 7: uninstall so the device is left clean for the next
                // APK (and the next run) — prevents package-name collisions and
                // keeps residual state from leaking between captures.
                runAdb(adb, opts.adbSerial, 10, "uninstall", pkg);
                succeeded++;
            } catch (IOException | InterruptedException e) {
                if (e instanceof InterruptedException) Thread.currentThread().interrupt();
                failures.put(name, e.getClass().getSimpleName() + ": " + e.getMessage());
            }
        }

        return new CaptureReport(outputDir, apks.size(), succeeded, failures);
    }

    /**
     * Best-effort package name extraction. Tries (in order): explicit
     * {@code aapt2Binary} option; {@code aapt2} resolved via
     * {@code ANDROID_HOME/build-tools/<latest>/aapt2}; finally a
     * regex-on-bytes fallback over the APK's binary AndroidManifest.xml that
     * looks for the {@code package="..."} attribute among the AXML string
     * pool. The fallback is intentionally permissive — we only need a
     * package name string, not a full AXML decode.
     */
    static String extractPackageName(Path apk, Path aapt2Override) throws IOException {
        Path aapt2 = aapt2Override != null ? aapt2Override : resolveAapt2();
        if (aapt2 != null && Files.isExecutable(aapt2)) {
            try {
                String pkg = aapt2DumpPackage(aapt2, apk);
                if (pkg != null) return pkg;
            } catch (IOException | InterruptedException ignore) {
                // fall through to AXML byte scan
            }
        }
        return scanManifestForPackage(apk);
    }

    private static Path resolveAapt2() {
        String home = System.getenv("ANDROID_HOME");
        if (home == null || home.isEmpty()) home = System.getenv("ANDROID_SDK_ROOT");
        if (home == null || home.isEmpty()) return null;
        Path bt = Path.of(home, "build-tools");
        if (!Files.isDirectory(bt)) return null;
        try (Stream<Path> ls = Files.list(bt)) {
            return ls.filter(Files::isDirectory)
                    .map(p -> p.resolve("aapt2"))
                    .filter(Files::isExecutable)
                    .sorted(Collections.reverseOrder())
                    .findFirst()
                    .orElse(null);
        } catch (IOException e) {
            return null;
        }
    }

    private static String aapt2DumpPackage(Path aapt2, Path apk) throws IOException, InterruptedException {
        ProcessBuilder pb = new ProcessBuilder(aapt2.toString(), "dump", "badging", apk.toString());
        pb.redirectErrorStream(true);
        Process p = pb.start();
        Pattern pkgLine = Pattern.compile("^package: name='([^']+)'");
        try (BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = r.readLine()) != null) {
                Matcher m = pkgLine.matcher(line);
                if (m.find()) {
                    p.waitFor(5, TimeUnit.SECONDS);
                    return m.group(1);
                }
            }
        }
        p.waitFor(5, TimeUnit.SECONDS);
        return null;
    }

    /**
     * Permissive AXML scan: read the binary AndroidManifest.xml, decode UTF-16LE
     * and UTF-8 string pools, and return the first string matching a Java
     * package shape ({@code com.foo.bar}) that comes after a "manifest"
     * attribute marker, or just the first such string. Good enough to unblock
     * adb commands when aapt2 is unavailable.
     */
    private static String scanManifestForPackage(Path apk) throws IOException {
        try (ZipFile zf = new ZipFile(apk.toFile())) {
            ZipEntry e = zf.getEntry("AndroidManifest.xml");
            if (e == null) return null;
            byte[] data;
            try (InputStream is = zf.getInputStream(e)) {
                data = is.readAllBytes();
            }
            // Try UTF-16LE first (AXML string pool default), then UTF-8.
            String s16 = new String(data, StandardCharsets.UTF_16LE);
            String hit = firstPackageLikeToken(s16);
            if (hit != null) return hit;
            String s8 = new String(data, StandardCharsets.UTF_8);
            return firstPackageLikeToken(s8);
        }
    }

    /** Java-package-shape regex: 2+ dot-separated lowercase-ish identifiers. */
    private static final Pattern PKG_SHAPE = Pattern.compile(
            "([a-zA-Z][a-zA-Z0-9_]*(?:\\.[a-zA-Z][a-zA-Z0-9_]*){1,})");

    /**
     * First token in {@code s} that looks like the app's own package name.
     * The prefix blocklist skips framework/library namespaces
     * ({@code android.}, {@code androidx.}, {@code java.}, {@code javax.},
     * {@code com.android.}, {@code com.google.android.}) because those appear
     * throughout the AXML string pool (attribute namespaces, referenced
     * framework classes) and would otherwise be returned before the app's
     * real package. Filtering them out lets the first surviving dotted token
     * be the application id we need for the adb commands. This is a heuristic
     * for the aapt2-unavailable fallback only, not a full AXML decode.
     */
    private static String firstPackageLikeToken(String s) {
        Matcher m = PKG_SHAPE.matcher(s);
        while (m.find()) {
            String tok = m.group(1);
            if (tok.contains(".") && !tok.startsWith("android.") && !tok.startsWith("java.")
                    && !tok.startsWith("javax.") && !tok.startsWith("androidx.")
                    && !tok.startsWith("com.android.") && !tok.startsWith("com.google.android.")) {
                return tok;
            }
        }
        return null;
    }

    private static int runAdb(String adb, String serial, int timeoutSec, String... args)
            throws IOException, InterruptedException {
        List<String> cmd = new ArrayList<>();
        cmd.add(adb);
        if (serial != null && !serial.isEmpty()) {
            cmd.add("-s");
            cmd.add(serial);
        }
        Collections.addAll(cmd, args);
        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.redirectErrorStream(true);
        Process p = pb.start();
        try (InputStream in = p.getInputStream()) {
            in.transferTo(java.io.OutputStream.nullOutputStream());
        }
        if (!p.waitFor(timeoutSec, TimeUnit.SECONDS)) {
            p.destroyForcibly();
            return -1;
        }
        return p.exitValue();
    }

    private static int runAdbToFile(String adb, String serial, int timeoutSec, Path output, String... args)
            throws IOException, InterruptedException {
        List<String> cmd = new ArrayList<>();
        cmd.add(adb);
        if (serial != null && !serial.isEmpty()) {
            cmd.add("-s");
            cmd.add(serial);
        }
        Collections.addAll(cmd, args);
        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.redirectErrorStream(true);
        Process p = pb.start();
        Files.createDirectories(output.getParent());
        try (InputStream in = p.getInputStream()) {
            Files.copy(in, output, StandardCopyOption.REPLACE_EXISTING);
        }
        if (!p.waitFor(timeoutSec, TimeUnit.SECONDS)) {
            p.destroyForcibly();
            return -1;
        }
        return p.exitValue();
    }

    private static String stripExt(String name) {
        int dot = name.lastIndexOf('.');
        return dot < 0 ? name : name.substring(0, dot);
    }

    // --- value types --------------------------------------------------------

    /** Tunables for {@link #capture}; all optional with the defaults below. */
    public static final class BootCaptureOptions {
        /** {@code adb -s} device serial; null/empty targets the single attached device. */
        public String adbSerial;
        /** Seconds to let each app boot before dumping logcat. */
        public int captureSeconds = 30;
        /** Explicit adb executable; null defaults to {@code adb} on PATH. */
        public Path adbBinary;
        /** Explicit aapt2 executable for package extraction; null triggers ANDROID_HOME resolution then AXML byte-scan fallback. */
        public Path aapt2Binary;
    }

    /** Operational outcome of a {@link #capture} run (not a gate — see class javadoc). */
    public static final class CaptureReport {
        /** Root directory the per-APK {@code boot.logcat} files were written under. */
        public final Path outputDir;
        /** Number of {@code .apk} files discovered under the input directory. */
        public final int totalApks;
        /** Number of APKs whose full install→monkey→dump→uninstall cycle succeeded. */
        public final int succeeded;
        /** APK filename → failure reason for every APK that did not complete. */
        public final Map<String, String> failures;

        public CaptureReport(Path outputDir, int totalApks, int succeeded,
                             Map<String, String> failures) {
            this.outputDir = outputDir;
            this.totalApks = totalApks;
            this.succeeded = succeeded;
            this.failures = failures == null ? Collections.emptyMap()
                    : Collections.unmodifiableMap(new LinkedHashMap<>(failures));
        }

        /** Project to a JSON-friendly map for {@link Report}-shaped serialization. */
        public Map<String, Object> toMetrics() {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("outputDir", outputDir.toString());
            m.put("totalApks", totalApks);
            m.put("succeeded", succeeded);
            m.put("failures", failures);
            return m;
        }
    }

}
