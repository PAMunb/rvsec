package br.unb.cic.rv.cli;

import picocli.CommandLine;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;
import picocli.CommandLine.Parameters;

import java.nio.file.Path;
import java.util.List;

/**
 * Picocli entry point for the DEX-native weaver.
 *
 * <p>Subcommands:
 * <ul>
 *   <li>{@code instrument <apk>} — weave a single APK.</li>
 *   <li>{@code batch <apks-dir>} — weave every {@code .apk} in the directory,
 *       emitting an aggregate {@code InstrumentationResults} JSON.</li>
 * </ul>
 *
 * <p>Flags follow the precedence declared in {@link ConfigResolver}:
 * explicit flag → environment variable → built-in default.
 */
@Command(
        name = "instr-cli",
        mixinStandardHelpOptions = true,
        version = "0.9.3-SNAPSHOT",
        description = "DEX-native bytecode weaver for rvsec monitors. Spec-set agnostic.",
        subcommands = {InstrumentationCli.Instrument.class, InstrumentationCli.Batch.class}
)
public final class InstrumentationCli implements Runnable {

    @Option(names = "--descriptor", description = "Path to MultiSpec_*MonitorAspect.json",
            scope = CommandLine.ScopeType.INHERIT)
    Path descriptorPath;

    @Option(names = "--android-jar", description = "Path to android.jar",
            scope = CommandLine.ScopeType.INHERIT)
    Path androidJar;

    @Option(names = "--javac", description = "Path to javac binary",
            scope = CommandLine.ScopeType.INHERIT)
    Path javacBin;

    @Option(names = "--jdk-rt", description = "Path to JDK rt.jar / jrt image",
            scope = CommandLine.ScopeType.INHERIT)
    Path jdkRtJar;

    @Option(names = "--d8", description = "Path to Android SDK d8",
            scope = CommandLine.ScopeType.INHERIT)
    Path d8Bin;

    @Option(names = "--zipalign", description = "Path to Android SDK zipalign",
            scope = CommandLine.ScopeType.INHERIT)
    Path zipalignBin;

    @Option(names = "--apksigner", description = "Path to Android SDK apksigner",
            scope = CommandLine.ScopeType.INHERIT)
    Path apksignerBin;

    @Option(names = "--keystore", description = "Signing keystore path",
            scope = CommandLine.ScopeType.INHERIT)
    Path keystore;

    @Option(names = "--keystore-pass", description = "Keystore password",
            scope = CommandLine.ScopeType.INHERIT)
    String keystorePass;

    @Option(names = "--key-alias", description = "Signing key alias",
            scope = CommandLine.ScopeType.INHERIT)
    String keyAlias;

    @Option(names = "--key-pass", description = "Signing key password",
            scope = CommandLine.ScopeType.INHERIT)
    String keyPass;

    @Option(names = "--classpath",
            description = "Extra jars to add to javac classpath (comma-separated)",
            split = ",",
            scope = CommandLine.ScopeType.INHERIT)
    List<Path> extraClasspath;

    @Option(names = "--output", description = "Output directory for signed APK(s)",
            scope = CommandLine.ScopeType.INHERIT)
    Path outputDir;

    @Option(names = "--work-dir", description = "Working directory for intermediate artifacts",
            scope = CommandLine.ScopeType.INHERIT)
    Path workDir;

    @Option(names = "--monitor-src-dir",
            description = "Directory with rv-monitor-emitted .java sources (e.g. mop/MultiSpec_1RuntimeMonitor.java); "
                    + "when set, monitor-builder runs javac+d8 and multidex-merger produces a signed APK. "
                    + "When omitted, the pipeline stops at written DEXes (phase=dex_only).",
            scope = CommandLine.ScopeType.INHERIT)
    Path monitorSrcDir;

    @Option(names = "--coverage", description = "Enable Coverage catch-all weaving (default true)",
            scope = CommandLine.ScopeType.INHERIT, defaultValue = "true", negatable = true)
    boolean enableCoverage;

    @Option(names = "--log-level", description = "SLF4J simple-logger level",
            scope = CommandLine.ScopeType.INHERIT)
    String logLevel;

    @Override
    public void run() {
        // Root command alone does nothing; one of the subcommands must be given.
        new CommandLine(this).usage(System.out);
    }

    @Command(name = "instrument", description = "Weave a single APK.")
    public static final class Instrument implements Runnable {
        @Parameters(index = "0", description = "APK to instrument")
        Path apk;
        @picocli.CommandLine.ParentCommand InstrumentationCli parent;

        @Override
        public void run() {
            EffectiveConfig cfg = ConfigResolver.resolve(parent);
            BatchRunner.instrumentOne(cfg, apk);
        }
    }

    @Command(name = "batch", description = "Weave every .apk under a directory.")
    public static final class Batch implements Runnable {
        @Parameters(index = "0", description = "Directory containing APKs")
        Path apksDir;
        @Option(names = "--results-json",
                description = "Path to write the aggregate InstrumentationResults JSON")
        Path resultsJson;
        @picocli.CommandLine.ParentCommand InstrumentationCli parent;

        @Override
        public void run() {
            EffectiveConfig cfg = ConfigResolver.resolve(parent);
            BatchRunner.instrumentBatch(cfg, apksDir, resultsJson);
        }
    }

    public static void main(String[] args) {
        int exit = new CommandLine(new InstrumentationCli()).execute(args);
        System.exit(exit);
    }
}
