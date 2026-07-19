package br.unb.cic.rv.cli;

import br.unb.cic.rv.builder.CoverageSourceEmitter;
import br.unb.cic.rv.builder.MonitorBuilder;
import br.unb.cic.rv.coverage.CoverageWeaver;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.DescriptorReader;
import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.emitter.WrapperEmitter;
import br.unb.cic.rv.merger.MultidexMerger;
import br.unb.cic.rv.mutator.DexFileMutator;
import br.unb.cic.rv.mutator.DexWeaver;
import br.unb.cic.rv.mutator.RegisterAllocator;
import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.writer.pool.DexPool;
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
 * <p>Pipeline phases (each surfaces in {@link PerApkResult#phase} on failure
 * and in {@link PerApkResult#weaveCounts} on success):
 * <ol>
 *   <li>Descriptor read.</li>
 *   <li>Type resolver + Android class index.</li>
 *   <li>DEX extraction from APK.</li>
 *   <li>Per-DEX advice weave + coverage weave + DexPool serialization.</li>
 *   <li>(Optional, when {@code monitorSrcDir} is configured)
 *       monitor-builder javac+d8 → monitor DEX(es).</li>
 *   <li>(Optional, when {@code mergerConfig} is configured)
 *       multidex-merger repack + zipalign + apksigner.</li>
 * </ol>
 *
 * <p>Phase outcomes:
 * <ul>
 *   <li>{@code phase=signed} + {@code success=true}: full pipeline ran;
 *       output APK is at {@code outputDir / apkName}.</li>
 *   <li>{@code phase=dex_only} + {@code success=false}: DEX mutation succeeded
 *       but build/sign was skipped (caller didn't supply
 *       {@code --monitor-src-dir} or builder/merger paths). The mutated DEXes
 *       live under {@code workDir} for downstream consumption.</li>
 *   <li>{@code phase=build_only} + {@code success=false}: DEX mutation and the
 *       monitor DEX build both succeeded, but repack/sign was skipped (caller
 *       didn't supply {@code --apksigner}/{@code --zipalign}/{@code --keystore}
 *       + {@code --output}). The mutated app DEXes and freshly built monitor
 *       DEX(es) live under {@code workDir}.</li>
 *   <li>{@code phase=apk_read|io_error|config_validation|uncaught} +
 *       {@code success=false}: well-formed failure; the Python wrapper
 *       continues onto the next APK.</li>
 * </ul>
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

            // Phase 3: extract DEX files from APK (preserving entry names).
            ExtractedDex[] dexes = extractDexes(apk);
            counts.put("dexFiles", dexes.length);
            if (dexes.length == 0) {
                return failed(apk, "no classes*.dex entries in APK", "apk_read");
            }

            // Max DEX-format API across the APK's input dexes (each dex's
            // preserved opcodes.api). Threaded into the monitor builder so d8
            // emits the monitor DEX at >= this API via --min-api; without it the
            // d8-produced monitor dex would default low even though the app
            // dexes now preserve their own version.
            int maxInputApi = 0;
            for (ExtractedDex ed : dexes) {
                maxInputApi = Math.max(maxInputApi, ed.dex.getOpcodes().api);
            }
            counts.put("maxInputApi", maxInputApi);

            // Phase 4: weave + serialize per DEX.
            Path workDir = cfg.workDir() != null
                    ? cfg.workDir()
                    : Files.createTempDirectory("rvsec-dexlib2-");
            Files.createDirectories(workDir);

            // Generate mop/MonitorWrappers.java alongside the rv-monitor
            // sources so monitor-builder picks it up. The wrapper entries
            // returned tell the DexWeaver which call sites to redirect.
            // When --monitor-src-dir is unset, we still compute wrappers
            // (in a tmp dir) so the substitution map is populated for the
            // dex_only / build_only paths' weave-counts to be accurate.
            Path wrapperOutDir = cfg.monitorSrcDir() != null
                    ? cfg.monitorSrcDir()
                    : workDir.resolve("monitor-src");
            Files.createDirectories(wrapperOutDir);
            List<WrapperEmitter.WrapperEntry> wrappers =
                    WrapperEmitter.generate(descriptor, wrapperOutDir, androidIndex);
            counts.put("wrappersGenerated", wrappers.size());
            DexWeaver weaver = new DexWeaver(
                    new EmitterDispatch(), new RegisterAllocator(), wrappers);

            // Build a single InheritanceResolver covering EVERY DEX of the APK
            // BEFORE the per-DEX weave loop. This serves two purposes:
            //   (1) wrapper subtype expansion (INV-INS-68 phase 2) — the
            //       resolver must see app-internal subclasses that may live in
            //       a different DEX than the call site (e.g. classes2.dex
            //       declares the subclass, classes.dex contains the call).
            //   (2) downstream pointcut matching during weave gets the same
            //       multi-DEX view (pointcuts that test T+ across DEX
            //       boundaries no longer miss).
            DexFile[] allDexes = new DexFile[dexes.length];
            for (int i = 0; i < dexes.length; i++) allDexes[i] = dexes[i].dex;
            InheritanceResolver inheritance =
                    new InheritanceResolver(androidIndex, allDexes);
            weaver.expandWrapperReplacementsForApk(inheritance);

            CoverageWeaver coverageWeaver = cfg.enableCoverage() ? new CoverageWeaver() : null;
            Map<String, Path> appDexEntries = new LinkedHashMap<>();
            int matchesApplied = 0;
            int plansSkipped = 0;
            int plansSkippedAliasing = 0;
            int wrappersSubstituted = 0;
            int wrappersAliasedToSubtype = 0;
            int constructorInlineApplied = 0;
            int constructorInlineSkippedAliasing = 0;
            int plansSkippedHighRegister = 0;
            int plansSkippedUnresolvedBinding = 0;
            int coverageInstrumented = 0;
            int coverageSpillFailed = 0;
            int classesSeen = 0;
            int methodsSeen = 0;

            for (ExtractedDex ed : dexes) {
                DexFile dx = ed.dex;
                DexFileMutator mutator = new DexFileMutator(dx);

                // Wire BOTH forMethod and replaceImpl into the supplier so the
                // weaver can update the cache after RegisterShifter spills a
                // method (gh61 INV-INS-87 / design.md D5). The previous
                // mutator::forMethod method-reference only overrode forMethod
                // and silently lost the cache update.
                DexWeaver.MutableImplSupplier weaverSupplier = new DexWeaver.MutableImplSupplier() {
                    @Override
                    public com.android.tools.smali.dexlib2.builder.MutableMethodImplementation forMethod(
                            com.android.tools.smali.dexlib2.iface.Method m) {
                        return mutator.forMethod(m);
                    }
                    @Override
                    public void replaceImpl(com.android.tools.smali.dexlib2.iface.Method m,
                            com.android.tools.smali.dexlib2.builder.MutableMethodImplementation impl) {
                        mutator.replaceImpl(m, impl);
                    }
                    @Override
                    public void addSynthesizedMethod(String definingClassDescriptor,
                            com.android.tools.smali.dexlib2.iface.Method m) {
                        mutator.addSynthesizedMethod(definingClassDescriptor, m);
                    }
                };

                // 4a. Advice weave (counts also accumulate the read-side stats
                // matchesApplied = matches that produced an emit + injection).
                DexWeaver.WeaveReport wr = weaver.weave(
                        dx, descriptor, typeResolver, inheritance, weaverSupplier);
                matchesApplied += wr.matchesApplied();
                plansSkipped += wr.plansSkipped();
                plansSkippedAliasing += wr.plansSkippedAliasing();
                wrappersSubstituted += wr.wrappersSubstituted();
                // wrappersAliasedToSubtype is APK-scoped (set once by
                // expandWrapperReplacementsForApk above) but the report carries
                // the same value for every DEX; record it once via the first
                // DEX's report.
                wrappersAliasedToSubtype = wr.wrappersAliasedToSubtype();
                constructorInlineApplied += wr.constructorInlineApplied();
                constructorInlineSkippedAliasing += wr.constructorInlineSkippedAliasing();
                plansSkippedHighRegister += wr.plansSkippedHighRegister();
                plansSkippedUnresolvedBinding += wr.plansSkippedUnresolvedBinding();
                classesSeen += wr.classesSeen();
                methodsSeen += wr.methodsSeen();

                // 4b. Coverage weave (optional). Same wiring concern as the
                // advice weaver above — replaceImpl MUST be plumbed through
                // for spill-induced MMI replacements to persist.
                if (coverageWeaver != null) {
                    CoverageWeaver.MutableImplSupplier covSupplier = new CoverageWeaver.MutableImplSupplier() {
                        @Override
                        public com.android.tools.smali.dexlib2.builder.MutableMethodImplementation forMethod(
                                com.android.tools.smali.dexlib2.iface.Method m) {
                            return mutator.forMethod(m);
                        }
                        @Override
                        public void replaceImpl(com.android.tools.smali.dexlib2.iface.Method m,
                                com.android.tools.smali.dexlib2.builder.MutableMethodImplementation impl) {
                            mutator.replaceImpl(m, impl);
                        }
                    };
                    CoverageWeaver.CoverageReport cr =
                            coverageWeaver.weave(dx, covSupplier);
                    coverageInstrumented += cr.methodsInstrumented();
                    coverageSpillFailed += cr.methodsSpillFailed();
                }

                // 4c. Serialize. DexPool accepts the original DexFile for
                // pass-through dexes (when no method was mutated) and the
                // rewritten DexFile when mutations exist.
                Path outDex = workDir.resolve("woven_" + ed.entryName);
                Files.createDirectories(outDex.getParent() == null ? workDir : outDex.getParent());
                DexPool.writeTo(outDex.toString(), mutator.toDexFile());
                appDexEntries.put(ed.entryName, outDex);
            }

            counts.put("classesSeen", classesSeen);
            counts.put("methodsSeen", methodsSeen);
            counts.put("matchesApplied", matchesApplied);
            counts.put("plansSkipped", plansSkipped);
            counts.put("plansSkippedAliasing", plansSkippedAliasing);
            counts.put("wrappersSubstituted", wrappersSubstituted);
            counts.put("wrappersAliasedToSubtype", wrappersAliasedToSubtype);
            counts.put("constructorInlineApplied", constructorInlineApplied);
            counts.put("constructorInlineSkippedAliasing", constructorInlineSkippedAliasing);
            counts.put("plansSkippedHighRegister", plansSkippedHighRegister);
            // gh56 INV-INS-71: surfaced in instrument_results.json so the
            // jq guard in run_phase5_validators.sh can fail the build when
            // cryptoapp regresses (replaces the previous manual grep).
            counts.put("plansSkippedUnresolvedBinding", plansSkippedUnresolvedBinding);
            if (coverageWeaver != null) {
                counts.put("coverageInstrumented", coverageInstrumented);
                counts.put("coverageSpillFailed", coverageSpillFailed);
            }
            counts.put("wovenDexes", appDexEntries.size());

            // Phase 5: monitor-builder javac+d8. Skipped unless the caller has
            // supplied both --monitor-src-dir AND a fully-resolved BuilderConfig
            // (javac/d8/rt.jar). When skipped, we stop here and report dex_only.
            boolean canBuild = cfg.builderConfig() != null && cfg.monitorSrcDir() != null;
            boolean canMerge = cfg.mergerConfig() != null && cfg.outputDir() != null;

            if (!canBuild) {
                return new PerApkResult(
                        apk.getFileName().toString(), false,
                        "DEXes woven (" + appDexEntries.size() + ") under " + workDir
                                + "; monitor build skipped (need --monitor-src-dir + "
                                + "--javac/--d8/--jdk-rt configured)",
                        "dex_only", counts);
            }

            // 5a. Emit Coverage.java alongside the rv-monitor-emitted sources.
            if (cfg.enableCoverage()) {
                CoverageSourceEmitter.emit(cfg.monitorSrcDir());
            }

            // 5b. javac + d8 → monitor DEX(es).
            MonitorBuilder mb = new MonitorBuilder(cfg.builderConfig().validated());
            Path monitorOut = workDir.resolve("monitor-build");
            List<Path> monitorDexes = mb.build(cfg.monitorSrcDir(), monitorOut, maxInputApi);
            counts.put("monitorDexes", monitorDexes.size());

            if (!canMerge) {
                return new PerApkResult(
                        apk.getFileName().toString(), false,
                        "DEXes woven + monitor DEX built (" + monitorDexes.size()
                                + "); merge skipped (need --apksigner/--zipalign/--keystore + --output)",
                        "build_only", counts);
            }

            // Phase 6: repack + sign.
            Files.createDirectories(cfg.outputDir());
            Path outApk = cfg.outputDir().resolve(apk.getFileName());
            new MultidexMerger(cfg.mergerConfig().validated())
                    .merge(apk, appDexEntries, monitorDexes, outApk);

            return new PerApkResult(
                    apk.getFileName().toString(), true,
                    "instrumented + signed → " + outApk,
                    "signed", counts);

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
     * {@link DexBackedDexFile} objects, preserving the original ZIP entry
     * name so the merger can drop the woven version into the same slot.
     */
    private static ExtractedDex[] extractDexes(Path apk) throws IOException {
        List<ExtractedDex> out = new ArrayList<>();
        try (ZipFile zf = new ZipFile(apk.toFile())) {
            var entries = zf.entries();
            while (entries.hasMoreElements()) {
                ZipEntry e = entries.nextElement();
                String n = e.getName();
                if (!n.startsWith("classes") || !n.endsWith(".dex")) continue;
                byte[] bytes;
                try (InputStream in = zf.getInputStream(e)) {
                    bytes = in.readAllBytes();
                }
                // Preserve the input DEX format version. Reading with
                // Opcodes.forDexVersion(parsedVersion) makes DexPool.writeTo
                // stamp the SAME version on output (the writer's magic derives
                // from opcodes.api). Reading with Opcodes.getDefault() instead
                // (== forApi(20) → dex035 in smali 3.0.9) would downgrade every
                // output DEX to 035; Kotlin/Compose interface static/default
                // methods are legal only in dex >= 037, so a downgraded 037+ app
                // crashes at runtime with IncompatibleClassChangeError.
                Opcodes opcodes = opcodesForDex(bytes, n);
                out.add(new ExtractedDex(n, new DexBackedDexFile(opcodes, bytes)));
            }
        }
        // Sort by entry name so classes.dex precedes classes2.dex precedes ...
        out.sort((a, b) -> a.entryName.compareTo(b.entryName));
        return out.toArray(new ExtractedDex[0]);
    }

    /**
     * Resolve the {@link Opcodes} matching the DEX container version parsed from
     * the file's 8-byte magic header {@code "dex\n0XY\0"} — bytes {@code [4,7)}
     * are the ASCII version digits {@code XY}. Falls back to
     * {@link Opcodes#getDefault()} when {@link Opcodes#forDexVersion(int)} rejects
     * the version (e.g. {@code dex036}, absent from the dataset), logging the
     * entry name and raw version.
     */
    static Opcodes opcodesForDex(byte[] dex, String entryName) {
        int version = (dex[4] - '0') * 100 + (dex[5] - '0') * 10 + (dex[6] - '0');
        try {
            return Opcodes.forDexVersion(version);
        } catch (RuntimeException ex) {
            System.err.println("[dexlib2] unsupported DEX version " + version
                    + " for entry " + entryName
                    + "; falling back to Opcodes.getDefault()");
            return Opcodes.getDefault();
        }
    }

    private record ExtractedDex(String entryName, DexBackedDexFile dex) {}

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
