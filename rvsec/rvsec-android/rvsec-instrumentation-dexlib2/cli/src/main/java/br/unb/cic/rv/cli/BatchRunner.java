package br.unb.cic.rv.cli;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.DescriptorReader;
import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.PointcutExpression;
import br.unb.cic.rv.pointcut.PointcutExpressionParser;
import br.unb.cic.rv.pointcut.PointcutMatcher;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

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
        // Pipeline (current shape — all read+match phases live; mutation +
        // signing remain stubs called out in the report so reviewers see
        // exactly where the work stops):
        //   1. Read descriptor JSON via descriptor-reader.
        //   2. Build TypeResolver from descriptor.imports.
        //   3. Build AndroidClassIndex against cfg.androidJar.
        //   4. Extract every classes<N>.dex from the APK.
        //   5. Per DEX: parse via dexlib2, build InheritanceResolver, run
        //      PointcutMatcher per advice × class × method × instruction;
        //      count matches without mutating (mutation needs the full
        //      DexBuilder pipeline; tracked under the "mutation" stub).
        //   6. Return PerApkResult with detailed per-phase counts.
        Map<String, Integer> counts = new LinkedHashMap<>();
        try {
            // Phase 1: descriptor.
            if (cfg.descriptorPath() == null) {
                return failed(apk, "config.descriptorPath is null", "config_validation");
            }
            AspectDescriptor descriptor = DescriptorReader.read(cfg.descriptorPath());
            counts.put("advices", descriptor.getAdvices().size());

            // Phase 2: type resolution + android index.
            TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
            AndroidClassIndex androidIndex = new AndroidClassIndex(cfg.androidJar());

            // Phase 3: extract DEX files from APK.
            List<DexFile> dexes = extractDexes(apk);
            counts.put("dexFiles", dexes.size());
            if (dexes.isEmpty()) {
                return failed(apk, "no classes*.dex entries in APK", "apk_read");
            }

            // Phase 4: parse pointcut ASTs once (cached across all advices).
            List<PointcutExpression> pcAsts = new ArrayList<>();
            for (AdviceDescriptor a : descriptor.getAdvices()) {
                String expr = a.getExpression();
                if (expr == null || expr.isBlank()) continue;
                try {
                    pcAsts.add(PointcutExpressionParser.parse(expr));
                } catch (RuntimeException ex) {
                    // unparseable expression — skipped (would surface in a
                    // FeatureMappingChecker run before this point).
                }
            }
            counts.put("parsedPointcuts", pcAsts.size());

            // Phase 5: walk every dex × class × method × instruction, run
            // matcher, count hits. The matcher is the same one that the
            // dex-mutator will drive at injection time, so this dry-run
            // produces an accurate weave-count projection.
            int classesSeen = 0;
            int methodsSeen = 0;
            int matches = 0;
            for (DexFile dx : dexes) {
                InheritanceResolver inheritance = new InheritanceResolver(androidIndex, dx);
                PointcutMatcher matcher = new PointcutMatcher(typeResolver, inheritance);
                for (ClassDef cd : dx.getClasses()) {
                    classesSeen++;
                    for (Method m : cd.getMethods()) {
                        methodsSeen++;
                        MethodImplementation impl = m.getImplementation();
                        if (impl == null) continue;
                        int idx = 0;
                        int total = -1; // unknown without iterating; not needed by current matcher
                        for (Instruction inst : impl.getInstructions()) {
                            for (PointcutExpression pe : pcAsts) {
                                if (matcher.match(pe, cd, m, inst, idx, total).isPresent()) {
                                    matches++;
                                }
                            }
                            idx++;
                        }
                    }
                }
            }
            counts.put("classesSeen", classesSeen);
            counts.put("methodsSeen", methodsSeen);
            counts.put("matchesProjected", matches);

            // Phase 6: mutation + monitor build + APK assembly.
            // These remain documented stubs — the integration is feasible but
            // requires fixture APK landings + the DexBuilder write-back path
            // that's the next implementation step. The report explicitly
            // names "matching ran; mutation pending" so reviewers see the
            // boundary without inspecting the code.
            String message = "matching ran (" + matches + " projected hits across "
                    + methodsSeen + " methods); mutation+sign pending (next step)";
            return new PerApkResult(
                    apk.getFileName().toString(),
                    /*success=*/ false,  // explicit: signed APK NOT produced
                    message,
                    "matched_pending_mutation",
                    counts);
        } catch (IOException ex) {
            return failed(apk, "I/O error: " + ex.getMessage(), "io_error");
        } catch (RuntimeException ex) {
            return failed(apk, "uncaught error: " + ex.getMessage(), "uncaught");
        }
    }

    private static PerApkResult failed(Path apk, String message, String phase) {
        return new PerApkResult(apk.getFileName().toString(), false, message, phase, Map.of());
    }

    /**
     * Extract every {@code classes<N>.dex} from the APK as in-memory
     * {@link DexBackedDexFile} objects. Resources / manifest / assets are
     * left untouched in the input file; the merger reattaches them later.
     */
    private static List<DexFile> extractDexes(Path apk) throws IOException {
        List<DexFile> out = new ArrayList<>();
        try (ZipFile zf = new ZipFile(apk.toFile())) {
            var entries = zf.entries();
            while (entries.hasMoreElements()) {
                ZipEntry e = entries.nextElement();
                String n = e.getName();
                if (!n.startsWith("classes") || !n.endsWith(".dex")) continue;
                try (InputStream in = zf.getInputStream(e);
                     java.io.BufferedInputStream buf = new java.io.BufferedInputStream(in)) {
                    out.add(DexBackedDexFile.fromInputStream(Opcodes.getDefault(), buf));
                }
            }
        }
        return out;
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
