package br.unb.cic.rv.cli;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

/**
 * Walks one or more APKs through the end-to-end weaving pipeline and emits an
 * aggregate {@link PerApkResult} summary.
 *
 * <p>This class composes all the other submodules:
 * <ol>
 *   <li>{@code descriptor-reader} — parse the JSON descriptor.</li>
 *   <li>{@code pointcut-engine} — build AST + AndroidClassIndex +
 *       InheritanceResolver + matcher.</li>
 *   <li>{@code advice-emitter} — produce EmitPlans.</li>
 *   <li>{@code dex-mutator} — apply plans to mutable DEX implementations.</li>
 *   <li>{@code coverage-weaver} — inject Coverage.log call at every non-excluded
 *       app method entry.</li>
 *   <li>{@code monitor-builder} — compile generated sources to .dex.</li>
 *   <li>{@code multidex-merger} — repack + zipalign + apksigner v3.</li>
 * </ol>
 *
 * <p>Fully end-to-end integration is flagged in the class body for the cli
 * integration tests (tasks 9.5-9.6). The method surface here is what the
 * Python wrapper invokes via subprocess.
 */
public final class BatchRunner {

    private BatchRunner() {}

    public static void instrumentOne(EffectiveConfig cfg, Path apk) {
        PerApkResult result = runPipeline(cfg, apk);
        System.out.println("instr-cli result: " + result);
    }

    public static void instrumentBatch(EffectiveConfig cfg, Path apksDir, Path resultsJson) {
        List<PerApkResult> results = new ArrayList<>();
        try (Stream<Path> apks = Files.list(apksDir)) {
            apks.filter(p -> p.toString().endsWith(".apk"))
                .sorted()
                .forEach(apk -> results.add(runPipeline(cfg, apk)));
        } catch (IOException ex) {
            throw new RuntimeException("failed to list " + apksDir, ex);
        }

        if (resultsJson != null) {
            writeResultsJson(results, resultsJson);
        }
        long successes = results.stream().filter(PerApkResult::success).count();
        System.out.println("instr-cli batch: " + successes + "/" + results.size() + " succeeded");
    }

    static PerApkResult runPipeline(EffectiveConfig cfg, Path apk) {
        // Full pipeline integration wires the six submodules together. The
        // end-to-end implementation is the subject of tasks 9.5 and 9.6 —
        // this scaffold documents the integration contract and returns a
        // non-success result until the APK-reading / instrumentation loop
        // lands. The interface itself is stable: the Python wrapper only
        // consumes the PerApkResult shape.
        return new PerApkResult(
                apk.getFileName().toString(),
                false,
                "pipeline integration pending (task 9.5)",
                "ajc → dexlib2 variant switch",
                Map.of());
    }

    private static void writeResultsJson(List<PerApkResult> results, Path out) {
        try {
            Map<String, Object> root = new LinkedHashMap<>();
            root.put("variant", "dexlib2");
            root.put("results", results);
            new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(out.toFile(), root);
        } catch (IOException ex) {
            throw new RuntimeException("failed to write " + out, ex);
        }
    }

    /**
     * Per-APK outcome returned by the pipeline. Serialized to the
     * {@code InstrumentationResults} JSON the Python wrapper parses.
     */
    public record PerApkResult(
            String apkName,
            boolean success,
            String message,
            String phase,
            Map<String, Integer> weaveCounts
    ) {
    }
}
