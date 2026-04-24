package br.unb.cic.rv.cli;

import br.unb.cic.rv.builder.BuilderConfig;
import br.unb.cic.rv.merger.MergerConfig;

import java.nio.file.Path;
import java.util.List;

/**
 * Merges command-line arguments, environment variables, and sensible defaults
 * into a single {@link EffectiveConfig}. Precedence, highest first:
 * <ol>
 *   <li>Explicit CLI flags ({@link InstrumentationCli} fields).</li>
 *   <li>Environment variables ({@code ANDROID_HOME}, {@code JAVA_HOME},
 *       {@code RVSEC_KEYSTORE}, {@code RVSEC_KEYSTORE_PASS}, ...).</li>
 *   <li>Built-in defaults (e.g. last-used Android API level under
 *       {@code $ANDROID_HOME/platforms/}).</li>
 * </ol>
 *
 * <p>Fails fast when a required input cannot be resolved — the {@code ciphertext}
 * of a monitor-builder or multidex-merger tool path missing.
 */
public final class ConfigResolver {

    private ConfigResolver() {}

    public static EffectiveConfig resolve(InstrumentationCli args) {
        Path androidJar = requirePath(args.androidJar,
                resolveAndroidJarFromEnv(), "--android-jar / ANDROID_HOME");
        Path javac = requirePath(args.javacBin,
                resolveJavacFromEnv(), "--javac / JAVA_HOME");
        Path d8 = requirePath(args.d8Bin,
                resolveD8FromEnv(), "--d8 / ANDROID_HOME");
        Path zipalign = requirePath(args.zipalignBin,
                resolveZipalignFromEnv(), "--zipalign / ANDROID_HOME");
        Path apksigner = requirePath(args.apksignerBin,
                resolveApksignerFromEnv(), "--apksigner / ANDROID_HOME");
        Path keystore = requirePath(args.keystore,
                envPath("RVSEC_KEYSTORE"), "--keystore / RVSEC_KEYSTORE");
        Path rtJar = requirePath(args.jdkRtJar,
                resolveJdkRtFromEnv(), "--jdk-rt / JAVA_HOME");

        String keystorePass = firstNonNull(args.keystorePass, System.getenv("RVSEC_KEYSTORE_PASS"), "android");
        String keyAlias = firstNonNull(args.keyAlias, System.getenv("RVSEC_KEY_ALIAS"), "androiddebugkey");
        String keyPass = firstNonNull(args.keyPass, System.getenv("RVSEC_KEY_PASS"), "android");

        BuilderConfig builder = new BuilderConfig(javac, d8, rtJar, androidJar,
                args.extraClasspath == null ? List.of() : args.extraClasspath);
        MergerConfig merger = new MergerConfig(apksigner, zipalign, keystore,
                keystorePass, keyAlias, keyPass);
        return new EffectiveConfig(
                args.descriptorPath,
                androidJar,
                args.workDir,
                args.outputDir,
                List.of(),
                builder,
                merger,
                args.enableCoverage,
                keystore,
                args.logLevel == null ? "INFO" : args.logLevel
        );
    }

    private static Path requirePath(Path fromCli, Path fromEnv, String label) {
        Path p = fromCli != null ? fromCli : fromEnv;
        if (p == null) {
            throw new IllegalArgumentException("missing " + label);
        }
        return p;
    }

    private static String firstNonNull(String... values) {
        for (String v : values) if (v != null && !v.isEmpty()) return v;
        return null;
    }

    private static Path envPath(String name) {
        String v = System.getenv(name);
        return v == null ? null : Path.of(v);
    }

    private static Path resolveAndroidJarFromEnv() {
        String home = System.getenv("ANDROID_HOME");
        if (home == null) return null;
        Path platforms = Path.of(home, "platforms");
        if (!java.nio.file.Files.isDirectory(platforms)) return null;
        try (java.util.stream.Stream<Path> lvls = java.nio.file.Files.list(platforms)) {
            return lvls
                    .filter(java.nio.file.Files::isDirectory)
                    .map(p -> p.resolve("android.jar"))
                    .filter(java.nio.file.Files::isRegularFile)
                    .max((a, b) -> a.getParent().getFileName().toString()
                            .compareTo(b.getParent().getFileName().toString()))
                    .orElse(null);
        } catch (Exception ex) {
            return null;
        }
    }

    private static Path resolveJavacFromEnv() {
        String home = System.getenv("JAVA_HOME");
        if (home == null) return null;
        Path p = Path.of(home, "bin", "javac");
        return java.nio.file.Files.isRegularFile(p) ? p : null;
    }

    private static Path resolveJdkRtFromEnv() {
        // JDK 9+ ships java.* in jmods; bootclasspath with rt.jar is optional on
        // modern JDKs. Accept a manually-pointed rt.jar as a fallback; if not
        // supplied we pick any jrt image available or leave null (callers must
        // pass --jdk-rt explicitly on JDK 9+).
        String home = System.getenv("JAVA_HOME");
        if (home == null) return null;
        Path rt = Path.of(home, "jre", "lib", "rt.jar");
        if (java.nio.file.Files.isRegularFile(rt)) return rt;
        // fallback — JRT image; javac accepts an empty bootclasspath on JDK 9+.
        return Path.of(home, "lib", "modules");
    }

    private static Path resolveD8FromEnv() {
        String home = System.getenv("ANDROID_HOME");
        if (home == null) return null;
        Path tools = Path.of(home, "build-tools");
        return latestUnder(tools, "d8");
    }

    private static Path resolveZipalignFromEnv() {
        String home = System.getenv("ANDROID_HOME");
        if (home == null) return null;
        Path tools = Path.of(home, "build-tools");
        return latestUnder(tools, "zipalign");
    }

    private static Path resolveApksignerFromEnv() {
        String home = System.getenv("ANDROID_HOME");
        if (home == null) return null;
        Path tools = Path.of(home, "build-tools");
        return latestUnder(tools, "apksigner");
    }

    private static Path latestUnder(Path buildTools, String name) {
        if (!java.nio.file.Files.isDirectory(buildTools)) return null;
        try (java.util.stream.Stream<Path> lvls = java.nio.file.Files.list(buildTools)) {
            return lvls
                    .filter(java.nio.file.Files::isDirectory)
                    .map(p -> p.resolve(name))
                    .filter(java.nio.file.Files::isRegularFile)
                    .max((a, b) -> a.getParent().getFileName().toString()
                            .compareTo(b.getParent().getFileName().toString()))
                    .orElse(null);
        } catch (Exception ex) {
            return null;
        }
    }
}
