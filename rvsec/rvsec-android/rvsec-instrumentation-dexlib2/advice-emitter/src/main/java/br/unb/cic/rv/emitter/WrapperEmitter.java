package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.pointcut.CallPC;
import br.unb.cic.rv.pointcut.CombinedPC;
import br.unb.cic.rv.pointcut.PointcutExpression;
import br.unb.cic.rv.pointcut.PointcutExpressionParser;
import br.unb.cic.rv.pointcut.TypeResolver;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Emits {@code mop/MonitorWrappers.java} — a Java source file containing one
 * static wrapper per advice whose hook would otherwise cause register aliasing
 * at injection time. The canonical trigger is {@code after() returning(R r)}
 * on a static factory like {@code Iterator.iterator()}: the weaver needs both
 * the return value and the original argument registers alive at once, and the
 * compiler may well have reused the arg register for the result.
 *
 * <p>Each wrapper:
 * <ol>
 *   <li>Calls the original static method with the same arguments.</li>
 *   <li>Invokes every {@code <RuntimeMonitor>.<Event>(...)} declared by the
 *       advice's {@code monitorCalls} list.</li>
 *   <li>Returns the original result.</li>
 * </ol>
 *
 * <p>At weave time, the {@code dex-mutator} rewrites the call-site's
 * {@code invoke-static} method reference from {@code ClassName.method(args)R}
 * to {@code mop.MonitorWrappers.<wrapperName>(args)R}. The original registers
 * and the {@code move-result*} are kept untouched — no spill needed.
 *
 * <p>Spec-set agnostic: emits wrappers for any {@code after-returning} advice
 * regardless of whether the underlying specification set is JCA or Generic.
 *
 * <p>Implementation note: the prototype's {@code WrapperGenerator} included an
 * android.jar-backed overload-resolution pass so that wrappers respected the
 * Android API's actual parameter types (not the host JDK's). That pass is
 * re-integrated by the {@code dex-mutator} in Group 5 via its
 * {@link br.unb.cic.rv.pointcut.AndroidClassIndex}; the version here uses the
 * advice parameter declarations as the source of truth, which matches how
 * rv-monitor emits the descriptor in both specification sets.
 */
public final class WrapperEmitter {

    public static final String WRAPPER_CLASS_NAME = "MonitorWrappers";
    public static final String WRAPPER_PACKAGE    = "mop";
    public static final String WRAPPER_CLASS_DESC = "Lmop/MonitorWrappers;";

    /** A wrapper entry: metadata the {@code dex-mutator} needs when rewriting call-sites. */
    public static final class WrapperEntry {
        public final String wrapperName;
        public final String originalClassFqn;
        public final String originalMethodName;
        public final List<String> originalParamFqn;
        public final String originalReturnFqn;

        public WrapperEntry(String wrapperName, String cls, String meth,
                            List<String> params, String ret) {
            this.wrapperName = wrapperName;
            this.originalClassFqn = cls;
            this.originalMethodName = meth;
            this.originalParamFqn = params;
            this.originalReturnFqn = ret;
        }
    }

    private WrapperEmitter() {}

    /**
     * Decide whether an advice should be routed through a wrapper.
     * Criteria:
     * <ol>
     *   <li>Position is {@code after} (only after-side advice has the
     *       register-aliasing risk that wrappers exist to fix).</li>
     *   <li>A {@code returning(R r)} clause is present OR an {@code args(...)}
     *       clause is present — both need pre-call register state preserved
     *       across the {@code move-result*}.</li>
     * </ol>
     * Position is the only thing the descriptor reports directly; the args /
     * returning information is read from the advice fields.
     */
    public static boolean shouldWrap(AdviceDescriptor a) {
        if (!"after".equals(a.getPosition())) return false;
        boolean hasReturning = a.getReturning() != null && !a.getReturning().isEmpty();
        boolean hasArgs = a.getExpression() != null
                && a.getExpression().contains("args(");
        return hasReturning || hasArgs;
    }

    /**
     * Lexical check: does the {@code call(...)} expression for this target
     * contain the {@code static} modifier prefix? Ported from prototype's
     * {@code WrapperGenerator.targetLooksStatic}. Wrappers emitted for non-
     * static targets would call the original as a static method, producing
     * a {@code MethodNotFoundError} at runtime — so we filter them out and
     * let the inline path (or future per-instance wrapper) handle them.
     */
    static boolean targetLooksStatic(String expression, CallPC ct) {
        if (expression == null) return false;
        String needle = ct.declaringType() + "." + ct.methodName();
        int idx = expression.indexOf(needle);
        if (idx < 0) return false;
        int openParen = expression.lastIndexOf('(', idx);
        if (openParen < 0) return false;
        String head = expression.substring(openParen + 1, idx);
        return head.contains("static");
    }

    /**
     * Generate {@code mop/MonitorWrappers.java} under {@code outputDir} and
     * return the wrapper entries the {@code dex-mutator} needs.
     */
    public static List<WrapperEntry> generate(AspectDescriptor descriptor, Path outputDir)
            throws IOException {
        List<WrapperEntry> entries = new ArrayList<>();
        StringBuilder src = new StringBuilder();
        TypeResolver resolver = new TypeResolver(descriptor.getImports());
        src.append("// Generated by rvsec-instrumentation-dexlib2 WrapperEmitter — DO NOT EDIT.\n");
        src.append("package ").append(WRAPPER_PACKAGE).append(";\n\n");

        // Forward every import from the descriptor (mirrors the source .aj's
        // header) so referenced types like `Cipher`, `KeyGenerator`,
        // `MessageDigest`, etc. resolve at javac time. The descriptor
        // already de-duplicates these. Filter out the AspectJ / MOP runtime
        // imports — those are needed by the monitor + advice .aj sources but
        // not by the generated MonitorWrappers, and pulling them in would
        // require classpath jars that monitor-builder cannot supply.
        if (descriptor.getImports() != null) {
            for (String imp : descriptor.getImports()) {
                if (imp == null || imp.isBlank()) continue;
                String trimmed = imp.trim();
                String pkg = trimmed.startsWith("import ")
                        ? trimmed.substring("import ".length())
                        : trimmed;
                if (pkg.endsWith(";")) pkg = pkg.substring(0, pkg.length() - 1);
                if (isAspectJRuntimeImport(pkg)) continue;
                src.append("import ").append(pkg).append(";\n");
            }
            src.append('\n');
        }

        Map<String, Integer> nameCounts = new LinkedHashMap<>();
        boolean bodyStarted = false;
        for (AdviceDescriptor advice : descriptor.getAdvices()) {
            if (!shouldWrap(advice)) continue;
            CallPC target = firstCallTarget(advice.getExpression());
            if (target == null) continue;
            if (target.isConstructor()) {
                // Constructors don't flow through wrappers — the weaver always
                // has access to the allocated instance as the invoke site's
                // first register.
                continue;
            }
            if (target.varargs() || hasWildcardParam(target.paramTypes())) {
                // AspectJ ".." varargs / wildcard parameters can't be
                // expressed as a concrete Java signature without enumerating
                // every overload (which the prototipo's WrapperGenerator
                // does via AndroidClassIndex). That overload-expansion is a
                // separate port; for now we skip varargs / wildcard targets.
                continue;
            }
            // Only emit wrappers for static calls. Instance-target advices
            // would require the wrapper to take the receiver as the first
            // parameter and rewrite `target(name)` bindings to map to that
            // parameter — that is a separate port (tracked under task 5.4
            // INV-INS-29 follow-up). Without static filtering, the emitter
            // would call instance methods statically and produce a
            // MethodNotFoundError at runtime.
            if (!targetLooksStatic(advice.getExpression(), target)) continue;
            if (!bodyStarted) {
                src.append("public final class ").append(WRAPPER_CLASS_NAME).append(" {\n");
                src.append("    private ").append(WRAPPER_CLASS_NAME).append("() {}\n\n");
                bodyStarted = true;
            }
            WrapperEntry entry = buildEntry(target, nameCounts, resolver);
            if (hasAmbiguousObjectParam(entry)) {
                // Without AndroidClassIndex-driven overload expansion (a
                // separate port from prototipo's WrapperGenerator), the
                // wrapper would emit `Cipher.getInstance(String, Object)`
                // which doesn't match any actual Cipher overload. Skip
                // until the expansion lands.
                continue;
            }
            entries.add(entry);
            appendWrapperMethod(src, advice, entry);
        }
        if (!bodyStarted) {
            // Emit an empty class so monitor-builder compiles uniformly
            // whether wrappers exist or not.
            src.append("public final class ").append(WRAPPER_CLASS_NAME).append(" {\n");
            src.append("    private ").append(WRAPPER_CLASS_NAME).append("() {}\n");
        }
        src.append("}\n");

        Path dir = outputDir.resolve(WRAPPER_PACKAGE);
        Files.createDirectories(dir);
        Files.writeString(dir.resolve(WRAPPER_CLASS_NAME + ".java"), src.toString());
        return entries;
    }

    // --- helpers -------------------------------------------------------------

    /**
     * Walks the pointcut AST and returns the first {@link CallPC} it finds.
     * The corpus uses one call(...) per advice in practice; the walk flattens
     * the AST to pick it up regardless of whether it's nested in {@code &&} /
     * {@code ||} subtrees.
     */
    private static CallPC firstCallTarget(String expression) {
        if (expression == null || expression.isBlank()) return null;
        try {
            PointcutExpression pe = PointcutExpressionParser.parse(expression);
            return findFirstCall(pe);
        } catch (RuntimeException ex) {
            return null;
        }
    }

    private static CallPC findFirstCall(PointcutExpression pe) {
        if (pe instanceof CallPC cpc) return cpc;
        if (pe instanceof CombinedPC c) {
            CallPC left = findFirstCall(c.left());
            if (left != null) return left;
            return findFirstCall(c.right());
        }
        return null;
    }

    private static WrapperEntry buildEntry(CallPC target, Map<String, Integer> nameCounts,
                                            TypeResolver resolver) {
        // Resolve simple names ("String", "Cipher") to fully-qualified names
        // via the descriptor's `imports`. The DexWeaver's wrapperReplacements
        // map uses dexlib2 descriptors as keys and we build those from FQNs;
        // simple names like "String" do not round-trip through fqnToDescriptor
        // (would yield "LString;" instead of "Ljava/lang/String;") and the
        // map lookup misses every call site.
        String cls = resolveFqn(resolver, stripSubtypePlus(target.declaringType()));
        String meth = target.methodName();
        String baseName = cls.replace('.', '_') + "_" + meth;
        int count = nameCounts.getOrDefault(baseName, 0);
        nameCounts.put(baseName, count + 1);
        String wrapperName = count == 0 ? baseName : baseName + "_" + count;

        List<String> params = new ArrayList<>();
        for (String p : target.paramTypes()) {
            params.add(resolveFqn(resolver, stripSubtypePlus(p)));
        }
        String ret = resolveFqn(resolver, stripSubtypePlus(target.returnType()));
        return new WrapperEntry(wrapperName, cls, meth, params, ret);
    }

    /**
     * Resolve a possibly-simple type name (e.g. {@code "String"} or
     * {@code "byte[]"}) to its fully-qualified form. Strips array suffixes
     * before resolving the element type and reattaches them, so
     * {@code "Cipher[][]"} becomes {@code "javax.crypto.Cipher[][]"} given
     * the descriptor's imports.
     */
    private static String resolveFqn(TypeResolver resolver, String type) {
        if (type == null || type.isEmpty()) return type;
        int arr = 0;
        String base = type;
        while (base.endsWith("[]")) { arr++; base = base.substring(0, base.length() - 2); }
        String resolved;
        switch (base) {
            case "void":
            case "boolean":
            case "byte":
            case "short":
            case "char":
            case "int":
            case "long":
            case "float":
            case "double":
                resolved = base;
                break;
            default:
                if (base.contains(".")) {
                    resolved = base; // already FQN
                } else {
                    String r = resolver.resolveFqn(base);
                    resolved = r != null ? r : base;
                }
        }
        StringBuilder sb = new StringBuilder(resolved);
        for (int i = 0; i < arr; i++) sb.append("[]");
        return sb.toString();
    }

    /**
     * AspectJ's {@code Class+} subtype pattern ("any subtype of Class") is
     * preserved by the parser but cannot appear in a generated Java type. We
     * lower it to the base class name; the wrapper accepts the base type and
     * polymorphism handles subtypes at runtime.
     */
    private static String stripSubtypePlus(String type) {
        if (type == null) return null;
        if (type.endsWith("+")) return type.substring(0, type.length() - 1);
        // Could appear inside arrays: "X+[]"; conservatively just trim the
        // trailing '+' if present.
        return type;
    }

    /**
     * Returns true if any parameter type is the AspectJ wildcard
     * {@code ..} (matches "any sequence of types from this point"). Such
     * patterns cannot be lowered to a concrete Java signature without
     * enumerating overloads via {@code AndroidClassIndex} — deferred port.
     */
    private static boolean hasWildcardParam(List<String> paramTypes) {
        if (paramTypes == null) return false;
        for (String p : paramTypes) {
            if ("..".equals(p) || (p != null && p.contains(".."))) return true;
        }
        return false;
    }

    /**
     * Returns true when the given package import is from the AspectJ /
     * JavaMOP / RV-Monitor runtime — those packages are referenced by the
     * generated {@code .aj} aspect and runtime monitor but not by the
     * generated wrappers, and javac would fail to find them on monitor-
     * builder's classpath (which only has android.jar + rv-monitor-rt +
     * rvsec-agent).
     */
    private static boolean isAspectJRuntimeImport(String pkg) {
        if (pkg == null) return true;
        return pkg.startsWith("javamoprt")
                || pkg.startsWith("org.aspectj")
                || pkg.startsWith("rvmonitorrt")
                || pkg.startsWith("com.runtimeverification");
    }

    /**
     * Returns true if any wrapper-method type ({@code Object} treated as a
     * "lost overload" sentinel — the descriptor encodes ".." varargs as a
     * solitary {@code Object} parameter when the parser can't enumerate
     * concrete overloads) would produce an ambiguous javac call. Used to
     * skip wrappers that, without {@code AndroidClassIndex}-driven overload
     * expansion, would emit a call like {@code Cipher.getInstance(String,
     * Object)} that does not match any actual Cipher overload.
     */
    static boolean hasAmbiguousObjectParam(WrapperEntry entry) {
        for (int i = 1; i < entry.originalParamFqn.size(); i++) {
            String p = entry.originalParamFqn.get(i);
            if ("Object".equals(p) || "java.lang.Object".equals(p)) return true;
        }
        return false;
    }

    private static void appendWrapperMethod(StringBuilder src, AdviceDescriptor advice,
                                             WrapperEntry entry) {
        String ret = entry.originalReturnFqn;
        src.append("    public static ").append(ret).append(' ').append(entry.wrapperName)
                .append('(');
        List<String> paramNames = new ArrayList<>();
        for (int i = 0; i < entry.originalParamFqn.size(); i++) {
            if (i > 0) src.append(", ");
            String p = entry.originalParamFqn.get(i);
            String name = "p" + i;
            paramNames.add(name);
            src.append(p).append(' ').append(name);
        }
        // Declare a permissive throws so the wrapper compiles regardless of
        // which checked exceptions the wrapped method declares (Cipher.
        // getInstance throws NoSuchAlgorithmException, KeyStore.getInstance
        // throws KeyStoreException, ...). The original call sites already
        // handle these — the wrapper just propagates them transparently.
        src.append(") throws Exception {\n");
        src.append("        ").append(ret).append(" result = ").append(entry.originalClassFqn)
                .append('.').append(entry.originalMethodName).append('(')
                .append(String.join(", ", paramNames)).append(");\n");

        for (MonitorCallDescriptor mc : advice.getMonitorCalls()) {
            src.append("        ").append(mc.getMethod()).append('(');
            src.append(buildMonitorArgs(advice, mc, paramNames));
            src.append(");\n");
        }
        src.append("        return result;\n");
        src.append("    }\n\n");
    }

    private static String buildMonitorArgs(AdviceDescriptor advice, MonitorCallDescriptor mc,
                                            List<String> wrapperParamNames) {
        Collection<String> args = new ArrayList<>();
        Map<String, String> byName = new LinkedHashMap<>();
        for (int i = 0; i < advice.getParameters().size(); i++) {
            ParameterDescriptor pd = advice.getParameters().get(i);
            String local = i < wrapperParamNames.size()
                    ? wrapperParamNames.get(i)
                    : pd.getName();
            byName.put(pd.getName(), local);
        }
        if (advice.getReturning() != null) {
            for (ParameterDescriptor pd : advice.getReturning()) {
                byName.put(pd.getName(), "result");
            }
        }
        for (String argName : mc.getArgs()) {
            args.add(byName.getOrDefault(argName, argName));
        }
        return String.join(", ", args);
    }
}
