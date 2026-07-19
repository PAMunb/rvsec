package br.unb.cic.rv.builder;

import java.nio.file.Path;
import java.util.List;
import java.util.Objects;

/**
 * Configuration for {@link MonitorBuilder} — the paths to external tools
 * and classpath jars needed to compile the generated monitor sources.
 *
 * <p>All fields are validated on construction: paths must exist, JDK + Android
 * SDK binaries must be executable. Failures raise {@link IllegalArgumentException}
 * with the missing/invalid path, so the Python wrapper's
 * {@code DexlibInstrumentationConfig.validate()} can surface the root cause
 * before any weaving starts.
 */
public final class BuilderConfig {

    public final Path javacBin;
    public final Path d8Bin;
    public final Path jdkRtJar;
    public final Path androidJar;
    /**
     * Runtime support jars fed to both {@code javac} (compile) and {@code d8}
     * (dexed inline by {@link MonitorBuilder}; see {@code runD8}). The list
     * arrives pre-narrowed by the Python wrapper to the monitors' runtime
     * allowlist ({@code rv-monitor-rt}, {@code rvsec-core},
     * {@code rvsec-logger-logcat}); the wrapper drops the rest of the
     * {@code mvn dependency:copy-dependencies} output (aspectjrt, kotlin,
     * surefire) because dexing them would bloat the APK and can make d8 fail
     * with duplicate-type errors. See {@code instrumentation.md} §4 steps 2
     * and 9.
     */
    public final List<Path> classpath;

    public BuilderConfig(Path javacBin, Path d8Bin, Path jdkRtJar, Path androidJar,
                         List<Path> classpath) {
        this.javacBin = Objects.requireNonNull(javacBin, "javacBin");
        this.d8Bin = Objects.requireNonNull(d8Bin, "d8Bin");
        this.jdkRtJar = Objects.requireNonNull(jdkRtJar, "jdkRtJar");
        this.androidJar = Objects.requireNonNull(androidJar, "androidJar");
        this.classpath = classpath == null ? List.of() : List.copyOf(classpath);
    }

    public BuilderConfig validated() {
        requireFile(javacBin, "javacBin");
        requireFile(d8Bin, "d8Bin");
        requireFile(jdkRtJar, "jdkRtJar");
        requireFile(androidJar, "androidJar");
        for (Path p : classpath) requireFile(p, "classpath entry");
        return this;
    }

    private static void requireFile(Path p, String label) {
        if (!java.nio.file.Files.isRegularFile(p)) {
            throw new IllegalArgumentException(label + " not a file: " + p);
        }
    }
}
