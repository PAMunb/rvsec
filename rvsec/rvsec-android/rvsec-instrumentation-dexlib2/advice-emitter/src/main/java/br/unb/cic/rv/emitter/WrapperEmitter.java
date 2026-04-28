package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.pointcut.AndroidClassIndex;
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
import java.util.Collections;
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
 *   <li>Calls the original method with the same arguments. For instance-target
 *       advices the wrapper is still emitted as a {@code public static} method
 *       and prepends the receiver as its first parameter; the weaver rewrites
 *       the original {@code invoke-virtual / invoke-direct / invoke-interface}
 *       call site to {@code invoke-static} keeping the same register list, so
 *       the original receiver register slots in as the wrapper's first
 *       argument.</li>
 *   <li>Invokes every {@code <RuntimeMonitor>.<Event>(...)} declared by the
 *       advice's {@code monitorCalls} list.</li>
 *   <li>Returns the original result.</li>
 * </ol>
 *
 * <p>At weave time, the {@code dex-mutator} rewrites the call-site's
 * {@code invoke-*} method reference to {@code mop.MonitorWrappers.<wrapperName>(args)R}.
 * The original registers and the {@code move-result*} are kept untouched —
 * no spill needed.
 *
 * <p>Spec-set agnostic: emits wrappers for any {@code after-returning} advice
 * regardless of whether the underlying specification set is JCA or Generic.
 *
 * <p>Implementation note: when an {@link AndroidClassIndex} is supplied we
 * enumerate concrete overloads from android.jar so wrappers respect the actual
 * Android API parameter types — this lifts the previous defensive skips for
 * {@code ..} varargs, {@code T+} subtype patterns and "ambiguous Object"
 * params (ported from prototipo-dexlib2's {@code WrapperGenerator}). When the
 * index is null the emitter falls back to the descriptor's literal types
 * (preserving the old behavior so unit tests without an android.jar still
 * exercise the static-only path).
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
        /**
         * {@code true} when the wrapped method is a static method: the wrapper
         * calls {@code Cls.method(args)} directly. {@code false} for instance
         * methods: the wrapper accepts the receiver as its first parameter and
         * calls {@code recv.method(args)}; the dex-mutator preserves the
         * original receiver register as the first invoke argument so this is
         * register-stable.
         */
        public final boolean isStatic;

        public WrapperEntry(String wrapperName, String cls, String meth,
                            List<String> params, String ret, boolean isStatic) {
            this.wrapperName = wrapperName;
            this.originalClassFqn = cls;
            this.originalMethodName = meth;
            this.originalParamFqn = params;
            this.originalReturnFqn = ret;
            this.isStatic = isStatic;
        }
    }

    /** One concrete (Android API-resolved) overload to wrap. */
    public static final class ConcreteCall {
        public final String declFqn;
        public final String methodName;
        public final List<String> paramFqns;
        public final String returnFqn;
        public final boolean isStatic;

        public ConcreteCall(String declFqn, String methodName,
                            List<String> paramFqns, String returnFqn, boolean isStatic) {
            this.declFqn = declFqn;
            this.methodName = methodName;
            this.paramFqns = paramFqns;
            this.returnFqn = returnFqn;
            this.isStatic = isStatic;
        }
    }

    private WrapperEmitter() {}

    /**
     * Decide whether an advice should be routed through a wrapper.
     *
     * <p>Every after-side advice is wrapped, regardless of which binding
     * clauses (args, target, returning, throwing) it carries. The
     * register-aliasing risk that motivates the wrapper system applies to
     * any after-side hook: between the matched invoke and the inline hook,
     * the verifier can observe register-type changes (move-result
     * overwrite, compiler-driven reuse of the receiver register, etc.) that
     * make the inline path unsafe even when the advice has no bindings at
     * all. The earlier {@code returning || args} filter accidentally let
     * {@code target(...)}-only advices fall through to inline-AFTER and
     * then get defensively skipped in {@code DexWeaver}, costing the
     * monitor every {@code Mac.update}, {@code MessageDigest.update},
     * {@code SSLContext.init}, {@code SecureRandom.setSeed(long)}, etc.
     * event on the JCA-400 corpus.
     *
     * <p>Before-side advice is handled by the inline path (no aliasing
     * risk; {@code BeforeEmitter} reads pre-call registers directly).
     * Around-advice is rejected upstream by {@code EmitterDispatch}.
     */
    public static boolean shouldWrap(AdviceDescriptor a) {
        return "after".equals(a.getPosition());
    }

    /**
     * Lexical check: does the {@code call(...)} expression for this target
     * contain the {@code static} modifier prefix? Used as a fallback when
     * {@code AndroidClassIndex} is not available — with the index we read
     * the {@code ACC_STATIC} bit from android.jar directly.
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
     * Back-compat overload that omits the android.jar index. Falls back to
     * the descriptor-literal path (no overload expansion, instance targets
     * filtered out, varargs / wildcard / ambiguous-Object params skipped).
     */
    public static List<WrapperEntry> generate(AspectDescriptor descriptor, Path outputDir)
            throws IOException {
        return generate(descriptor, outputDir, null);
    }

    /**
     * Generate {@code mop/MonitorWrappers.java} under {@code outputDir} and
     * return the wrapper entries the {@code dex-mutator} needs.
     *
     * @param androidIndex when non-null, drives concrete-overload expansion via
     *                     android.jar (lifts the defensive skips for varargs,
     *                     {@code T+} patterns and ambiguous Object params, and
     *                     enables wrappers for instance-method advices). When
     *                     null the emitter behaves identically to the legacy
     *                     {@code generate(descriptor, outputDir)} two-arg form.
     */
    public static List<WrapperEntry> generate(AspectDescriptor descriptor, Path outputDir,
                                              AndroidClassIndex androidIndex) throws IOException {
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

            List<ConcreteCall> overloads = expandCallTarget(
                    target, resolver, androidIndex, /*instanceAllowed=*/ true);
            if (overloads.isEmpty()) {
                // Fallback path used when no android.jar index is available
                // OR the index has no matching overloads. Mirrors the legacy
                // behavior: only static targets, no varargs, no ambiguous
                // Object params; instance targets are dropped.
                ConcreteCall fallback = literalFallback(advice, target, resolver);
                if (fallback == null) continue;
                overloads = Collections.singletonList(fallback);
            }

            for (ConcreteCall cc : overloads) {
                if (!bodyStarted) {
                    src.append("public final class ").append(WRAPPER_CLASS_NAME).append(" {\n");
                    src.append("    private ").append(WRAPPER_CLASS_NAME).append("() {}\n\n");
                    bodyStarted = true;
                }
                WrapperEntry entry = buildEntry(cc, nameCounts);
                entries.add(entry);
                appendWrapperMethod(src, advice, entry);
            }
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

    // --- expansion -----------------------------------------------------------

    /**
     * Expand an AspectJ call target into the concrete (Android API-resolved)
     * overloads it can match. Ported from prototipo-dexlib2's
     * {@code WrapperGenerator.expandSupertypes}.
     *
     * <p>{@code instanceAllowed} controls whether non-static overloads are
     * kept: {@code WrapperEmitter} passes {@code true} (instance and static
     * advices are both wrapped). The dex-mutator will rewrite the call site
     * to {@code invoke-static} and route through the wrapper either way; the
     * wrapper itself is the one piece that needs to know whether to emit
     * {@code Cls.method(p0,p1)} or {@code recv.method(p0,p1)}.
     *
     * <p>Returns an empty list when:
     * <ul>
     *   <li>{@code androidIndex == null} and the target uses any pattern that
     *       can't be resolved without it (varargs, {@code T+}, etc.).</li>
     *   <li>The declared class is not present in android.jar, or has no
     *       method with the requested name and matching arity / patterns.</li>
     * </ul>
     * The caller's fallback (when index is null) handles the non-pattern
     * static-only case.
     */
    public static List<ConcreteCall> expandCallTarget(CallPC ct, TypeResolver resolver,
                                                      AndroidClassIndex index,
                                                      boolean instanceAllowed) {
        if (ct == null || ct.isConstructor()) return Collections.emptyList();

        boolean hasTrailingVarargs = ct.varargs();
        boolean needsExpansion = hasTrailingVarargs;
        for (int i = 0; i < ct.paramTypes().size(); i++) {
            String p = ct.paramTypes().get(i);
            if (p == null) continue;
            if (p.endsWith("+")) needsExpansion = true;
            if ("..".equals(p)) {
                needsExpansion = true;
                if (i == ct.paramTypes().size() - 1) hasTrailingVarargs = true;
                else {
                    // Middle-position ".." cannot be lowered to a Java
                    // signature; the prototipo logged + skipped.
                    return Collections.emptyList();
                }
            }
        }
        boolean returnIsSubtypePattern = ct.returnType() != null
                && ct.returnType().endsWith("+");
        if (returnIsSubtypePattern) needsExpansion = true;

        if (index == null) {
            // No android.jar — caller will run the descriptor-literal
            // fallback; we cannot expand patterns safely here.
            if (needsExpansion) return Collections.emptyList();
            return Collections.emptyList();
        }

        String declFqn = stripSubtypePlus(ct.declaringType());
        if (!declFqn.contains(".")) {
            String resolved = resolver.resolveFqn(declFqn);
            if (resolved != null) declFqn = resolved;
        }

        List<AndroidClassIndex.MethodInfo> methods =
                index.methods(declFqn, ct.methodName(), /*onlyStatic=*/ false);
        if (methods.isEmpty()) return Collections.emptyList();

        int fixedPrefix = hasTrailingVarargs
                ? ct.paramTypes().size() - 1
                : ct.paramTypes().size();
        // When the param list is just "(..)" the parser leaves paramTypes
        // empty AND sets varargs=true; fixedPrefix becomes -1 so clamp it.
        if (fixedPrefix < 0) fixedPrefix = 0;

        List<ConcreteCall> out = new ArrayList<>();
        for (AndroidClassIndex.MethodInfo m : methods) {
            if (!instanceAllowed && !m.isStatic()) continue;
            if (hasTrailingVarargs) {
                if (m.paramFqns.size() < fixedPrefix) continue;
            } else if (m.paramFqns.size() != ct.paramTypes().size()) {
                continue;
            }
            boolean paramsOk = true;
            for (int i = 0; i < fixedPrefix; i++) {
                if (!patternMatchesFqn(ct.paramTypes().get(i), m.paramFqns.get(i),
                        resolver, index)) {
                    paramsOk = false; break;
                }
            }
            if (!paramsOk) continue;
            if (ct.returnType() != null && !ct.returnType().isEmpty()) {
                if (!patternMatchesFqn(ct.returnType(), m.returnFqn, resolver, index)) continue;
            }
            out.add(new ConcreteCall(declFqn, ct.methodName(),
                    new ArrayList<>(m.paramFqns), m.returnFqn, m.isStatic()));
        }
        return out;
    }

    /**
     * Match an AspectJ type pattern against a fully-qualified Java type.
     * <ul>
     *   <li>"X+" (subtype): {@code X} is a supertype of {@code actualFqn} per
     *       {@link AndroidClassIndex#isAssignableFrom}.</li>
     *   <li>"X" (exact): {@code actualFqn} equals the resolved FQN of {@code X}.</li>
     *   <li>Primitives and arrays handled by string comparison.</li>
     * </ul>
     */
    private static boolean patternMatchesFqn(String pattern, String actualFqn,
                                             TypeResolver resolver, AndroidClassIndex index) {
        if (pattern == null || actualFqn == null) return false;
        boolean supertype = pattern.endsWith("+");
        String raw = supertype ? pattern.substring(0, pattern.length() - 1) : pattern;

        int arrays = 0;
        while (raw.endsWith("[]")) { arrays++; raw = raw.substring(0, raw.length() - 2); }

        String actualBase = actualFqn;
        for (int i = 0; i < arrays; i++) {
            if (!actualBase.endsWith("[]")) return false;
            actualBase = actualBase.substring(0, actualBase.length() - 2);
        }
        if (actualBase.endsWith("[]") && arrays == 0) return false;

        if (isPrimitiveFqn(raw)) return actualBase.equals(raw);
        if ("*".equals(raw)) return !isPrimitiveFqn(actualBase);

        String patternFqn = raw.contains(".") ? raw : resolver.resolveFqn(raw);
        if (patternFqn == null) return false;
        if (!supertype) return actualBase.equals(patternFqn);
        return index.isAssignableFrom(patternFqn, actualBase);
    }

    private static boolean isPrimitiveFqn(String fqn) {
        switch (fqn) {
            case "void": case "boolean": case "byte": case "short": case "char":
            case "int":  case "long":    case "float": case "double": return true;
            default: return false;
        }
    }

    /**
     * Build a {@link ConcreteCall} from the descriptor's literal types — used
     * when no {@link AndroidClassIndex} is available. Mirrors the legacy
     * (pre-expansion) behavior: only static targets, no varargs / wildcard
     * params, and the heuristic "ambiguous Object" filter.
     */
    private static ConcreteCall literalFallback(AdviceDescriptor advice, CallPC target,
                                                TypeResolver resolver) {
        if (target.varargs() || hasWildcardParam(target.paramTypes())) return null;
        if (!targetLooksStatic(advice.getExpression(), target)) return null;

        String cls = resolveFqn(resolver, stripSubtypePlus(target.declaringType()));
        List<String> params = new ArrayList<>();
        for (String p : target.paramTypes()) {
            params.add(resolveFqn(resolver, stripSubtypePlus(p)));
        }
        String ret = resolveFqn(resolver, stripSubtypePlus(target.returnType()));
        if (hasAmbiguousObjectParam(params)) return null;
        return new ConcreteCall(cls, target.methodName(), params, ret, /*isStatic=*/ true);
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

    private static WrapperEntry buildEntry(ConcreteCall cc, Map<String, Integer> nameCounts) {
        String baseName = cc.declFqn.replace('.', '_') + "_" + cc.methodName;
        int count = nameCounts.getOrDefault(baseName, 0);
        nameCounts.put(baseName, count + 1);
        String wrapperName = count == 0 ? baseName : baseName + "_" + count;
        return new WrapperEntry(wrapperName, cc.declFqn, cc.methodName,
                cc.paramFqns, cc.returnFqn, cc.isStatic);
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
        return type;
    }

    /**
     * Returns true if any parameter type is the AspectJ wildcard
     * {@code ..} (matches "any sequence of types from this point"). Used by
     * the literal fallback path; the index-driven path handles {@code ..}
     * directly via {@link #expandCallTarget}.
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
     * Heuristic used by the literal fallback (no android.jar): the descriptor
     * encodes ".." varargs as a solitary {@code Object} parameter when the
     * parser can't enumerate concrete overloads. Skipping wrappers in that
     * shape avoids emitting a call like {@code Cipher.getInstance(String,
     * Object)} that does not match any actual Cipher overload. Kept as a
     * static helper so the unit tests that exercise the no-index path still
     * see the same defensive behavior.
     */
    static boolean hasAmbiguousObjectParam(List<String> params) {
        for (int i = 1; i < params.size(); i++) {
            String p = params.get(i);
            if ("Object".equals(p) || "java.lang.Object".equals(p)) return true;
        }
        return false;
    }

    /** @deprecated use {@link #hasAmbiguousObjectParam(List)} on the FQN list. */
    @Deprecated
    static boolean hasAmbiguousObjectParam(WrapperEntry entry) {
        return hasAmbiguousObjectParam(entry.originalParamFqn);
    }

    private static void appendWrapperMethod(StringBuilder src, AdviceDescriptor advice,
                                             WrapperEntry entry) {
        String ret = entry.originalReturnFqn;
        src.append("    public static ").append(ret).append(' ').append(entry.wrapperName)
                .append('(');
        List<String> paramNames = new ArrayList<>();
        boolean first = true;
        if (!entry.isStatic) {
            // Receiver: occupies the same DEX register slot the original
            // invoke-virtual / invoke-direct put it in. Named "recv" so the
            // monitor-arg builder can map advice's `target(name)` binding to
            // it.
            src.append(entry.originalClassFqn).append(" recv");
            first = false;
        }
        for (int i = 0; i < entry.originalParamFqn.size(); i++) {
            if (!first) src.append(", ");
            first = false;
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
        boolean isVoid = "void".equals(ret);
        src.append("        ");
        if (!isVoid) src.append(ret).append(" result = ");
        if (entry.isStatic) {
            src.append(entry.originalClassFqn).append('.');
        } else {
            src.append("recv.");
        }
        src.append(entry.originalMethodName).append('(')
                .append(String.join(", ", paramNames)).append(");\n");

        for (MonitorCallDescriptor mc : advice.getMonitorCalls()) {
            src.append("        ").append(mc.getMethod()).append('(');
            src.append(buildMonitorArgs(advice, mc, paramNames, entry.isStatic));
            src.append(");\n");
        }
        if (!isVoid) src.append("        return result;\n");
        src.append("    }\n\n");
    }

    private static String buildMonitorArgs(AdviceDescriptor advice, MonitorCallDescriptor mc,
                                            List<String> wrapperParamNames, boolean isStatic) {
        Collection<String> args = new ArrayList<>();
        Map<String, String> byName = new LinkedHashMap<>();
        // For instance wrappers we map the advice's `target(<name>)` binding
        // (parsed lexically from the expression) to "recv"; the rest of the
        // advice parameters slot into wrapper params p0..pN positionally.
        // For static wrappers every advice parameter maps positionally to
        // wrapper params.
        String targetName = !isStatic ? extractTargetBinding(advice.getExpression()) : null;
        int wrapperIdx = 0;
        for (ParameterDescriptor pd : advice.getParameters()) {
            if (targetName != null && targetName.equals(pd.getName())) {
                byName.put(pd.getName(), "recv");
                continue;
            }
            String local = wrapperIdx < wrapperParamNames.size()
                    ? wrapperParamNames.get(wrapperIdx)
                    : pd.getName();
            byName.put(pd.getName(), local);
            wrapperIdx++;
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

    /**
     * Lexically pull the parameter name from a {@code target(<name>)} clause.
     * Returns {@code null} when the expression has no {@code target(...)},
     * leaving the monitor-arg builder to fall back to positional mapping —
     * which is correct because in that case the advice doesn't reference the
     * receiver at all.
     */
    private static String extractTargetBinding(String expr) {
        if (expr == null) return null;
        int idx = expr.indexOf("target(");
        if (idx < 0) return null;
        int start = idx + "target(".length();
        int end = expr.indexOf(')', start);
        if (end < 0) return null;
        String inner = expr.substring(start, end).trim();
        if (inner.isEmpty()) return null;
        return inner;
    }
}
