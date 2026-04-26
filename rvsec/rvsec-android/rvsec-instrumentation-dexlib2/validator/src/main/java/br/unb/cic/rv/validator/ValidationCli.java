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

    @Command(name = "layer2", description = "BootValidator (Phase 5 skeleton).")
    public static final class Layer2 implements Runnable {
        @Parameters(index = "0") Path apkDir;
        @Option(names = "--seconds", defaultValue = "30") int seconds;
        @picocli.CommandLine.ParentCommand ValidationCli parent;
        @Override public void run() {
            emitAndExit(parent, LayerSkeletons.layer2BootValidator(apkDir, seconds));
        }
    }

    @Command(name = "layer3", description = "TraceComparator (Phase 5 skeleton).")
    public static final class Layer3 implements Runnable {
        @Option(names = "--oracles", required = true) Path oracleDir;
        @Option(names = "--apks", required = true) Path apkDir;
        @picocli.CommandLine.ParentCommand ValidationCli parent;
        @Override public void run() {
            emitAndExit(parent, LayerSkeletons.layer3TraceComparator(oracleDir, apkDir));
        }
    }

    @Command(name = "layer4", description = "BatchValidator (Phase 5 skeleton).")
    public static final class Layer4 implements Runnable {
        @Option(names = "--thresholds", required = true) Path thresholdsYaml;
        @Option(names = "--results", required = true) Path batchResultsDir;
        @picocli.CommandLine.ParentCommand ValidationCli parent;
        @Override public void run() {
            emitAndExit(parent, LayerSkeletons.layer4BatchValidator(thresholdsYaml, batchResultsDir));
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
