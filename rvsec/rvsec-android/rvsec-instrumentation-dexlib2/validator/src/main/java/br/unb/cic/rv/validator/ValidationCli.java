package br.unb.cic.rv.validator;

import picocli.CommandLine;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;
import picocli.CommandLine.Parameters;

import java.io.IOException;
import java.nio.file.Path;

/**
 * Picocli entry for the validator CLI. Every subcommand emits a JSON
 * {@link Report} at the given {@code --report} path and returns the
 * report's {@link Report#exitCode()} so CI can gate on it mechanically.
 */
@Command(
        name = "validator-cli",
        mixinStandardHelpOptions = true,
        version = "0.8.0-SNAPSHOT",
        description = "Layered validation harness for rvsec-instrumentation-dexlib2.",
        subcommands = {
                ValidationCli.Inventory.class,
                ValidationCli.Mapping.class,
                ValidationCli.Parity.class,
                ValidationCli.Oracles.class,
                ValidationCli.Preflight.class,
                ValidationCli.Layer1.class,
                ValidationCli.Layer2.class,
                ValidationCli.Layer3.class,
                ValidationCli.Layer4.class,
                ValidationCli.Layer5.class
        }
)
public final class ValidationCli implements Runnable {

    @Option(names = "--report",
            description = "Where to write the JSON report (default: stdout only)",
            scope = CommandLine.ScopeType.INHERIT)
    Path reportPath;

    @Override
    public void run() {
        new CommandLine(this).usage(System.out);
    }

    @Command(name = "inventory", description = "Regenerate AJ_CONSTRUCTIONS_INVENTORY.md.")
    public static final class Inventory implements Runnable {
        @Parameters(index = "0", description = "RVSEC spec root") Path specRoot;
        @Option(names = "--out", required = true) Path outputMd;
        @picocli.CommandLine.ParentCommand ValidationCli parent;

        @Override public void run() {
            try {
                ConstructionInventoryGenerator.Inventory inv =
                        ConstructionInventoryGenerator.scan(specRoot);
                ConstructionInventoryGenerator.write(inv, outputMd);
                Report r = new Report("inventory", true,
                        "wrote " + outputMd + " with " + inv.totalUsages() + " total usages",
                        java.util.Map.of("outputMd", outputMd.toString(),
                                "totalUsages", inv.totalUsages()));
                emitAndExit(parent, r);
            } catch (IOException e) {
                System.err.println("inventory failed: " + e.getMessage());
                System.exit(2);
            }
        }
    }

    @Command(name = "mapping", description = "Enforce INV-INS-17 mapping closure.")
    public static final class Mapping implements Runnable {
        @Option(names = "--inventory", required = true) Path inventory;
        @Option(names = "--mapping", required = true) Path mapping;
        @Option(names = "--limitations", required = true) Path limitations;
        @picocli.CommandLine.ParentCommand ValidationCli parent;

        @Override public void run() {
            try {
                Report r = FeatureMappingChecker.check(inventory, mapping, limitations);
                emitAndExit(parent, r);
            } catch (IOException e) {
                System.err.println("mapping failed: " + e.getMessage());
                System.exit(2);
            }
        }
    }

    @Command(name = "parity", description = "Enforce INV-INS-19 .aj ↔ .json parity.")
    public static final class Parity implements Runnable {
        @Option(names = "--aj", required = true) Path aj;
        @Option(names = "--json", required = true) Path json;
        @picocli.CommandLine.ParentCommand ValidationCli parent;

        @Override public void run() {
            try {
                Report r = DescriptorAjParityChecker.check(aj, json);
                emitAndExit(parent, r);
            } catch (IOException e) {
                System.err.println("parity failed: " + e.getMessage());
                System.exit(2);
            }
        }
    }

    @Command(name = "oracles", description = "Enforce INV-INS-22 oracle diversity.")
    public static final class Oracles implements Runnable {
        @Option(names = "--dir", required = true) Path oracleDir;
        @picocli.CommandLine.ParentCommand ValidationCli parent;

        @Override public void run() {
            try {
                OracleLoader.LoadResult loaded = OracleLoader.load(oracleDir);
                emitAndExit(parent, OracleLoader.report(loaded));
            } catch (IOException e) {
                System.err.println("oracles failed: " + e.getMessage());
                System.exit(2);
            }
        }
    }

    @Command(name = "preflight", description = "INV-INS-25 Layer-4 method-ref audit.")
    public static final class Preflight implements Runnable {
        @Parameters(index = "0", description = "Directory of candidate APKs") Path apkDir;
        @Option(names = "--projected-added-refs", defaultValue = "250") int projected;
        @picocli.CommandLine.ParentCommand ValidationCli parent;

        @Override public void run() {
            try {
                emitAndExit(parent, MethodRefAuditor.audit(apkDir, projected));
            } catch (IOException e) {
                System.err.println("preflight failed: " + e.getMessage());
                System.exit(2);
            }
        }
    }

    @Command(name = "layer1", description = "BaksmaliDiffer: per-spec hook recall ≥ 0.95.")
    public static final class Layer1 implements Runnable {
        @Option(names = "--ajc", required = true) Path ajcApks;
        @Option(names = "--dexlib2", required = true) Path dexlibApks;
        @Option(names = "--descriptor", required = true,
                description = "MultiSpec_*MonitorAspect.json — spec catalog for wrapper attribution")
        Path descriptorJson;
        @picocli.CommandLine.ParentCommand ValidationCli parent;
        @Override public void run() {
            try {
                emitAndExit(parent, BaksmaliDiffer.diff(ajcApks, dexlibApks, descriptorJson));
            } catch (IOException e) {
                System.err.println("layer1 failed: " + e.getMessage());
                System.exit(2);
            }
        }
    }

    @Command(name = "layer2",
            description = "BootValidator: zero VerifyError regressions vs ajc baseline. "
                    + "Default: analyze mode (compare two logcat trees). "
                    + "With --capture: drive adb install/monkey/logcat for every APK in --apk-dir "
                    + "(emulator must already be running; rv-platform manages its lifecycle).")
    public static final class Layer2 implements Runnable {
        @Option(names = "--ajc",
                description = "ajc-baseline logcat dir (analyze mode)") Path ajcLogs;
        @Option(names = "--dexlib2",
                description = "dexlib2-pipeline logcat dir (analyze mode)") Path dexlibLogs;

        @Option(names = "--capture",
                description = "Switch to capture mode: drive adb against an attached emulator")
        boolean capture;
        @Option(names = "--apk-dir", description = "APK directory (capture mode)") Path apkDir;
        @Option(names = "--output", description = "Logcat output directory (capture mode)") Path outputDir;
        @Option(names = "--serial", description = "adb device serial (capture mode)") String serial;
        @Option(names = "--seconds", defaultValue = "30",
                description = "Capture window in seconds (capture mode)") int seconds;

        @picocli.CommandLine.ParentCommand ValidationCli parent;

        @Override public void run() {
            try {
                if (capture) {
                    if (apkDir == null || outputDir == null) {
                        System.err.println("layer2 --capture requires --apk-dir and --output");
                        System.exit(2);
                    }
                    BootValidator.BootCaptureOptions opts = new BootValidator.BootCaptureOptions();
                    opts.adbSerial = serial;
                    opts.captureSeconds = seconds;
                    BootValidator.CaptureReport cr = BootValidator.capture(apkDir, outputDir, opts);
                    boolean ok = cr.failures.isEmpty();
                    Report r = new Report(BootValidator.LAYER_NAME, ok,
                            String.format(java.util.Locale.ROOT,
                                    "capture: %d/%d apks succeeded",
                                    cr.succeeded, cr.totalApks),
                            cr.toMetrics());
                    emitAndExit(parent, r);
                } else {
                    if (ajcLogs == null || dexlibLogs == null) {
                        System.err.println("layer2 analyze mode requires --ajc and --dexlib2");
                        System.exit(2);
                    }
                    emitAndExit(parent, BootValidator.analyze(ajcLogs, dexlibLogs));
                }
            } catch (IOException e) {
                System.err.println("layer2 failed: " + e.getMessage());
                System.exit(2);
            }
        }
    }

    @Command(name = "layer3", description = "TraceComparator: per-spec F1 >= 0.98, kappa >= 0.9.")
    public static final class Layer3 implements Runnable {
        @Option(names = "--oracles", required = true) Path oracleDir;
        @Option(names = "--apks", required = true) Path apkDir;
        @picocli.CommandLine.ParentCommand ValidationCli parent;
        @Override public void run() {
            try {
                emitAndExit(parent, TraceComparator.compare(oracleDir, apkDir));
            } catch (IOException e) {
                System.err.println("layer3 failed: " + e.getMessage());
                System.exit(2);
            }
        }
    }

    @Command(name = "layer4",
            description = "BatchValidator: Wilcoxon signed-rank TOST on cov_method vs ajc baseline. "
                    + "Default: analyze mode (paired summary.csv comparison). "
                    + "With --orchestrate: drive `docker compose run` for every (variant, tool, rep) "
                    + "cell (operator-only; not unit-tested).")
    public static final class Layer4 implements Runnable {
        // analyze mode
        @Option(names = "--thresholds",
                description = "Pre-registered thresholds YAML (analyze mode)") Path thresholdsYaml;
        @Option(names = "--ajc",
                description = "ajc-baseline results dir containing summary.csv (analyze mode)") Path ajcResults;
        @Option(names = "--dexlib2",
                description = "dexlib2 results dir containing summary.csv (analyze mode)") Path dexlibResults;

        // orchestrate mode
        @Option(names = "--orchestrate",
                description = "Switch to orchestrate mode: drive docker compose for every cell")
        boolean orchestrate;
        @Option(names = "--apks",
                description = "APK directory (orchestrate mode)") Path apksDir;
        @Option(names = "--output",
                description = "Output directory for per-variant summary.csv (orchestrate mode)") Path outputDir;
        @Option(names = "--variants",
                description = "Comma-separated variant list (orchestrate mode)",
                split = ",") java.util.List<String> variants;
        @Option(names = "--tools",
                description = "Comma-separated tool list (orchestrate mode)",
                split = ",") java.util.List<String> tools;
        @Option(names = "--reps", defaultValue = "3",
                description = "Replicates per cell (orchestrate mode)") int reps;
        @Option(names = "--timeout", defaultValue = "300",
                description = "Per-run timeout seconds (orchestrate mode)") int timeoutSeconds;
        @Option(names = "--docker-compose",
                description = "docker-compose.yml file (orchestrate mode)") Path dockerComposeFile;

        @picocli.CommandLine.ParentCommand ValidationCli parent;

        @Override public void run() {
            try {
                if (orchestrate) {
                    if (apksDir == null || outputDir == null) {
                        System.err.println("layer4 --orchestrate requires --apks and --output");
                        System.exit(2);
                    }
                    BatchValidator.BatchOrchestrationOptions opts =
                            new BatchValidator.BatchOrchestrationOptions();
                    if (variants != null && !variants.isEmpty()) opts.variants = variants;
                    if (tools != null && !tools.isEmpty()) opts.tools = tools;
                    opts.reps = reps;
                    opts.timeoutSeconds = timeoutSeconds;
                    opts.dockerComposeFile = dockerComposeFile;

                    BatchValidator.OrchestrationReport orep =
                            BatchValidator.orchestrate(apksDir, outputDir, opts);
                    boolean ok = orep.failures.isEmpty();
                    Report r = new Report(BatchValidator.LAYER_NAME, ok,
                            String.format(java.util.Locale.ROOT,
                                    "orchestrate: %d/%d cells succeeded",
                                    orep.succeededCells, orep.totalCells),
                            orep.toMetrics());
                    emitAndExit(parent, r);
                } else {
                    if (thresholdsYaml == null || ajcResults == null || dexlibResults == null) {
                        System.err.println("layer4 analyze mode requires --thresholds, --ajc, --dexlib2");
                        System.exit(2);
                    }
                    emitAndExit(parent, BatchValidator.analyze(ajcResults, dexlibResults, thresholdsYaml));
                }
            } catch (IOException e) {
                System.err.println("layer4 failed: " + e.getMessage());
                System.exit(2);
            }
        }
    }

    @Command(name = "layer5", description = "CoverageValidator: RVSEC-COV recall >= 0.99, |delta| <= 1pp.")
    public static final class Layer5 implements Runnable {
        @Option(names = "--ajc", required = true) Path ajcLogs;
        @Option(names = "--dexlib2", required = true) Path dexlibLogs;
        @picocli.CommandLine.ParentCommand ValidationCli parent;
        @Override public void run() {
            try {
                emitAndExit(parent, CoverageValidator.compare(ajcLogs, dexlibLogs));
            } catch (IOException e) {
                System.err.println("layer5 failed: " + e.getMessage());
                System.exit(2);
            }
        }
    }

    private static void emitAndExit(ValidationCli parent, Report r) {
        if (parent.reportPath != null) {
            try {
                r.write(parent.reportPath);
            } catch (IOException e) {
                System.err.println("failed to write report: " + e.getMessage());
                System.exit(2);
            }
        } else {
            System.out.println("{ \"layer\": \"" + r.layer + "\", \"passed\": " + r.passed
                    + ", \"message\": \"" + r.message.replace("\"", "\\\"") + "\" }");
        }
        System.exit(r.exitCode());
    }

    public static void main(String[] args) {
        int exit = new CommandLine(new ValidationCli()).execute(args);
        System.exit(exit);
    }
}
