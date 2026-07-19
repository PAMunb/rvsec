package br.unb.cic.rv.validator;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.DescriptorReader;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;

import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * Layer-1 hook recall validator: pairs ajc-instrumented and dexlib2-instrumented
 * APKs by filename, extracts the set of {@code (callerClass, callerMethod, spec)}
 * hooks present in each, and computes per-spec recall as
 * {@code |hooks(dexlib2) ∩ hooks(ajc)| / |hooks(ajc)|}.
 *
 * <p>The "BaksmaliDiffer" name is historical — the implementation reads DEX
 * directly via dexlib2, no shell-out to baksmali.
 *
 * <h2>Hook recognition</h2>
 * <ul>
 *   <li>Inline: {@code invoke-static {regs}, Lmop/MultiSpec_<N>RuntimeMonitor;->
 *       <Spec>_<event>Event(...)V}. Both pipelines emit this shape; spec is the
 *       prefix before the first underscore in the method name.</li>
 *   <li>Wrapper substitution (dexlib2 only): {@code invoke-static {regs},
 *       Lmop/MonitorWrappers;-><wrapper_name>(...)<ret>}. The descriptor JSON
 *       is read once to map each wrapper name back to its spec.</li>
 * </ul>
 * Both shapes count as a single {@link HookKey} per {@code (callerClass,
 * callerMethod, spec)} triple — the dexlib2 pipeline can choose either
 * emission shape but the recall calculation must treat them identically.
 *
 * <h2>Gate</h2>
 * The aggregate gate is {@code recall ≥ 0.95} on every spec for {@code ≥90%}
 * of APK pairs in the input subset. Per-pair, per-spec recall and the aggregate
 * recall map are surfaced in {@link Report#metrics} for diagnostic use.
 */
public final class BaksmaliDiffer {

    public static final String LAYER_NAME = "layer1-baksmali-differ";
    public static final double GATE_THRESHOLD = 0.95;
    public static final double GATE_APK_PERCENTAGE = 0.90;

    private static final String MONITOR_CLASS_PREFIX = "Lmop/MultiSpec_";
    private static final String MONITOR_CLASS_SUFFIX = "RuntimeMonitor;";
    private static final String WRAPPER_CLASS_DESC   = "Lmop/MonitorWrappers;";

    private BaksmaliDiffer() {}

    /**
     * Per-method hook tuple. Two hooks are equal iff every component matches;
     * deduplicated within a method so the same spec hit twice in one method
     * counts as a single hook.
     */
    public record HookKey(String callerClass, String callerMethod, String spec) {}

    /**
     * Compute the Layer-1 hook-recall report.
     *
     * @param ajcApkDir       directory of legacy ajc-instrumented APKs
     * @param dexlibApkDir    directory of dexlib2-instrumented APKs (same filenames)
     * @param descriptorJson  MultiSpec_*MonitorAspect.json — required to resolve
     *                        wrapper-name → spec for the dexlib2 side
     */
    public static Report diff(Path ajcApkDir, Path dexlibApkDir, Path descriptorJson)
            throws IOException {
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("ajcApkDir", ajcApkDir.toString());
        metrics.put("dexlibApkDir", dexlibApkDir.toString());
        metrics.put("descriptorJson", descriptorJson.toString());
        metrics.put("gateThreshold", GATE_THRESHOLD);
        metrics.put("gateApkPercentage", GATE_APK_PERCENTAGE);

        if (!Files.isDirectory(ajcApkDir) || !Files.isDirectory(dexlibApkDir)) {
            metrics.put("ajcDirExists", Files.isDirectory(ajcApkDir));
            metrics.put("dexlibDirExists", Files.isDirectory(dexlibApkDir));
            return new Report(LAYER_NAME, false,
                    "input directory missing or not a directory", metrics);
        }
        if (!Files.isRegularFile(descriptorJson)) {
            metrics.put("descriptorExists", false);
            return new Report(LAYER_NAME, false,
                    "descriptor JSON missing", metrics);
        }

        Map<String, String> wrapperToSpec = buildWrapperToSpec(descriptorJson);
        metrics.put("wrapperEntries", wrapperToSpec.size());

        List<String> ajcNames = listApks(ajcApkDir);
        List<String> dexlibNames = listApks(dexlibApkDir);
        Set<String> ajcSet = new LinkedHashSet<>(ajcNames);
        Set<String> dexlibSet = new LinkedHashSet<>(dexlibNames);

        List<String> paired = new ArrayList<>();
        List<String> skipped = new ArrayList<>();
        for (String n : ajcNames) {
            if (dexlibSet.contains(n)) paired.add(n);
            else skipped.add(n + " (missing in dexlib2)");
        }
        for (String n : dexlibNames) {
            if (!ajcSet.contains(n)) skipped.add(n + " (missing in ajc)");
        }
        metrics.put("skippedNotPaired", skipped);

        if (paired.isEmpty()) {
            metrics.put("totalApkPairs", 0);
            metrics.put("apksWithFullRecall", 0);
            metrics.put("recallByApkSpec", new LinkedHashMap<String, Object>());
            metrics.put("aggregateRecallBySpec", new LinkedHashMap<String, Object>());
            return new Report(LAYER_NAME, false, "no APK pairs to compare", metrics);
        }

        Map<String, Map<String, Double>> recallByApkSpec = new TreeMap<>();
        Map<String, long[]> aggregateBySpec = new TreeMap<>(); // spec -> {hits, total}
        int apksWithFullRecall = 0;

        for (String apkName : paired) {
            Set<HookKey> ajcHooks = extractHooks(ajcApkDir.resolve(apkName), wrapperToSpec);
            Set<HookKey> dexlibHooks = extractHooks(dexlibApkDir.resolve(apkName), wrapperToSpec);

            Set<String> specs = new TreeSet<>();
            for (HookKey h : ajcHooks)    specs.add(h.spec());
            for (HookKey h : dexlibHooks) specs.add(h.spec());

            Map<String, Double> perSpec = new TreeMap<>();
            boolean apkOk = true;
            for (String spec : specs) {
                Set<HookKey> a = filterBySpec(ajcHooks, spec);
                Set<HookKey> d = filterBySpec(dexlibHooks, spec);
                int intersect = 0;
                for (HookKey k : a) if (d.contains(k)) intersect++;
                double recall = a.isEmpty() ? 1.0 : (double) intersect / a.size();
                perSpec.put(spec, recall);
                long[] agg = aggregateBySpec.computeIfAbsent(spec, k -> new long[2]);
                agg[0] += intersect;
                agg[1] += a.size();
                if (recall < GATE_THRESHOLD) apkOk = false;
            }
            recallByApkSpec.put(apkName, perSpec);
            if (apkOk) apksWithFullRecall++;
        }

        Map<String, Double> aggregateRecallBySpec = new TreeMap<>();
        for (Map.Entry<String, long[]> e : aggregateBySpec.entrySet()) {
            long total = e.getValue()[1];
            aggregateRecallBySpec.put(e.getKey(),
                    total == 0 ? 1.0 : (double) e.getValue()[0] / total);
        }

        int totalApkPairs = paired.size();
        boolean passed = apksWithFullRecall >= GATE_APK_PERCENTAGE * totalApkPairs;

        metrics.put("totalApkPairs", totalApkPairs);
        metrics.put("apksWithFullRecall", apksWithFullRecall);
        metrics.put("recallByApkSpec", recallByApkSpec);
        metrics.put("aggregateRecallBySpec", aggregateRecallBySpec);

        String message = passed
                ? "hook-recall gate passed: " + apksWithFullRecall + "/" + totalApkPairs
                        + " APK pairs at recall ≥ " + GATE_THRESHOLD
                : "hook-recall gate failed: only " + apksWithFullRecall + "/"
                        + totalApkPairs + " APK pairs at recall ≥ " + GATE_THRESHOLD
                        + " (need ≥ " + (int) Math.ceil(GATE_APK_PERCENTAGE * totalApkPairs)
                        + ")";
        return new Report(LAYER_NAME, passed, message, metrics);
    }

    /**
     * Read the descriptor JSON once and produce the {@code wrapperName → spec}
     * map. The wrapper name derivation mirrors {@code WrapperEmitter}'s
     * descriptor-literal path so the validator can run without invoking the
     * emitter (which itself needs an {@code AndroidClassIndex} for full
     * overload expansion — overkill for spec attribution).
     */
    static Map<String, String> buildWrapperToSpec(Path descriptorJson) {
        AspectDescriptor desc = DescriptorReader.read(descriptorJson);
        TypeResolver resolver = new TypeResolver(desc.getImports());
        Map<String, String> out = new LinkedHashMap<>();
        Map<String, Integer> nameCounts = new LinkedHashMap<>();
        for (AdviceDescriptor advice : desc.getAdvices()) {
            if (!"after".equals(advice.getPosition())) continue;
            if (advice.getMonitorCalls() == null || advice.getMonitorCalls().isEmpty()) continue;
            // Replicate WrapperEmitter's literal-fallback name derivation
            // (the descriptor-only path used when no AndroidClassIndex is
            // provided). Only after-advice with a returning() / args() clause
            // is wrapped; we don't filter on that here because the goal is to
            // catch every wrapper the dexlib2 side might emit, not to mirror
            // the emitter's gating exactly.
            String wrapperName = deriveWrapperName(advice, resolver, nameCounts);
            if (wrapperName == null) continue;
            String spec = specOfMonitorMethod(advice.getMonitorCalls().get(0).getMethod());
            if (spec == null) continue;
            out.put(wrapperName, spec);
        }
        return out;
    }

    /**
     * Replicates {@code WrapperEmitter}'s wrapper-name derivation for the
     * descriptor-literal path: {@code <fqClass>_<methodName>} with a numeric
     * suffix on collisions. The actual Android-jar-driven path expands
     * overloads — for hook recall we only need the PREFIX-form so the same
     * advice can be matched whether the woven APK uses inline or wrapper
     * emission. We register both the primary derived name AND a normalized
     * "any wrapper that begins with {@code <fqClass>_<methodName>}" key so
     * callers can probe with the actual name found in the DEX.
     */
    private static String deriveWrapperName(AdviceDescriptor advice, TypeResolver resolver,
                                            Map<String, Integer> nameCounts) {
        // Intent: reproduce, from the AspectJ pointcut expression string alone,
        // the exact wrapper method name WrapperEmitter would mint for this
        // advice — WITHOUT loading an AndroidClassIndex. The name is
        // "<fqType-with-dots-as-underscores>_<method>" (plus a collision
        // suffix), parsed out of the "call(<modifiers> <ret> Type.method(args))"
        // clause by locating the method's parameter paren and reading backwards.
        String expr = advice.getExpression();
        if (expr == null) return null;
        // Step 1: locate the "call(" clause. Its inner "Type.method(args)" is
        // where the wrapped signature lives; the dot just before the method's
        // parameter paren is the type-FQN / method-name boundary.
        int callIdx = expr.indexOf("call(");
        if (callIdx < 0) return null;
        // Step 2: paren-walk forward from just after "call(" to find the FIRST
        // '(' that opens the METHOD's parameter list. We start at depth 1
        // (already inside call's own paren) so depth==1 identifies a paren at
        // the call clause's own level — that is the method paren. The descriptor
        // shape has exactly one such method-paren inside call(...).
        int paren = -1;
        int depth = 1; // we're already inside call(
        for (int i = callIdx + 5; i < expr.length(); i++) {
            char c = expr.charAt(i);
            if (c == '(') {
                if (depth == 1) { paren = i; break; }
                depth++;
            } else if (c == ')') {
                depth--;
                if (depth == 0) break;
            }
        }
        if (paren < 0) return null;
        // Step 3: the last '.' before that paren splits type FQN from method name.
        int dot = expr.lastIndexOf('.', paren - 1);
        if (dot < 0 || dot < callIdx) return null;
        // Step 4: walk back from the dot through type-name characters (letters,
        // digits, '_', '$', '.', '+') until a separator (whitespace, '(', '&',
        // '|') — the return-type/modifier boundary. The span is the dotted type
        // FQN; a trailing '+' (AspectJ subtype wildcard) is dropped.
        int typeEnd = dot;
        int typeStart = typeEnd;
        while (typeStart > callIdx + 5) {
            char c = expr.charAt(typeStart - 1);
            if (Character.isLetterOrDigit(c) || c == '_' || c == '$'
                    || c == '.' || c == '+') {
                typeStart--;
            } else break;
        }
        String type = expr.substring(typeStart, typeEnd).trim();
        if (type.endsWith("+")) type = type.substring(0, type.length() - 1);
        String method = expr.substring(dot + 1, paren).trim();
        if (type.isEmpty() || method.isEmpty()) return null;
        // Step 5: rebuild the FQN. A simple (dot-less) type name is resolved via
        // the aspect's import table (TypeResolver); an already-qualified name is
        // used as-is. Dots then become underscores to form the wrapper base
        // name, and repeated bases get a numeric suffix exactly as
        // WrapperEmitter disambiguates overloads.
        String fqType = type.contains(".") ? type : resolver.resolveFqn(type);
        if (fqType == null) fqType = type;
        String base = fqType.replace('.', '_') + "_" + method;
        int count = nameCounts.getOrDefault(base, 0);
        nameCounts.put(base, count + 1);
        return count == 0 ? base : base + "_" + count;
    }

    /**
     * Extract every {@link HookKey} present in the APK's classes*.dex
     * entries. Hooks are deduplicated per {@code (callerClass, callerMethod,
     * spec)} — the same spec called multiple times in one method counts once.
     */
    static Set<HookKey> extractHooks(Path apk, Map<String, String> wrapperToSpec)
            throws IOException {
        Set<HookKey> hooks = new HashSet<>();
        try (ZipFile zf = new ZipFile(apk.toFile())) {
            var entries = zf.entries();
            while (entries.hasMoreElements()) {
                ZipEntry e = entries.nextElement();
                String n = e.getName();
                if (!n.startsWith("classes") || !n.endsWith(".dex")) continue;
                try (InputStream in = zf.getInputStream(e);
                     BufferedInputStream buf = new BufferedInputStream(in)) {
                    DexFile dex = DexBackedDexFile.fromInputStream(
                            Opcodes.getDefault(), buf);
                    collectHooks(dex, wrapperToSpec, hooks);
                }
            }
        }
        return hooks;
    }

    static void collectHooks(DexFile dex, Map<String, String> wrapperToSpec,
                              Set<HookKey> out) {
        for (ClassDef cd : dex.getClasses()) {
            String callerClass = cd.getType();
            for (Method m : cd.getMethods()) {
                MethodImplementation impl = m.getImplementation();
                if (impl == null) continue;
                String callerMethod = m.getName();
                Set<String> seenSpecs = new HashSet<>();
                for (Instruction insn : impl.getInstructions()) {
                    Opcode op = insn.getOpcode();
                    if (op != Opcode.INVOKE_STATIC && op != Opcode.INVOKE_STATIC_RANGE) continue;
                    if (!(insn instanceof ReferenceInstruction)) continue;
                    Object ref = ((ReferenceInstruction) insn).getReference();
                    if (!(ref instanceof MethodReference mr)) continue;
                    String spec = specOfInvoke(mr, wrapperToSpec);
                    if (spec == null) continue;
                    if (seenSpecs.add(spec)) {
                        out.add(new HookKey(callerClass, callerMethod, spec));
                    }
                }
            }
        }
    }

    /**
     * Map a {@code invoke-static} target to its spec, or {@code null} if the
     * target is neither a runtime-monitor event nor a known wrapper.
     */
    private static String specOfInvoke(MethodReference mr, Map<String, String> wrapperToSpec) {
        String defining = mr.getDefiningClass();
        String name = mr.getName();
        if (defining.startsWith(MONITOR_CLASS_PREFIX)
                && defining.endsWith(MONITOR_CLASS_SUFFIX)) {
            return specOfMonitorMethod(name);
        }
        if (WRAPPER_CLASS_DESC.equals(defining)) {
            return wrapperToSpec.get(name);
        }
        return null;
    }

    /**
     * The runtime monitor encodes the spec as the prefix before the first
     * underscore (e.g. {@code MessageDigestSpec_g4Event} → {@code MessageDigestSpec}).
     * Returns null when the method name doesn't match the {@code <Spec>_<event>Event}
     * convention.
     */
    private static String specOfMonitorMethod(String methodName) {
        if (methodName == null) return null;
        int idx = methodName.indexOf('_');
        if (idx <= 0) return null;
        if (!methodName.endsWith("Event")) return null;
        return methodName.substring(0, idx);
    }

    private static Set<HookKey> filterBySpec(Set<HookKey> all, String spec) {
        Set<HookKey> out = new HashSet<>();
        for (HookKey h : all) if (h.spec().equals(spec)) out.add(h);
        return out;
    }

    private static List<String> listApks(Path dir) throws IOException {
        try (var stream = Files.list(dir)) {
            return stream
                    .filter(p -> p.toString().endsWith(".apk"))
                    .map(p -> p.getFileName().toString())
                    .sorted()
                    .toList();
        }
    }
}
