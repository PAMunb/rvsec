package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Shared helper for building the {@code invoke-static} instruction that calls
 * the generated RuntimeMonitor's event method.
 *
 * <p>Every {@link AdviceEmitter} ultimately emits one such invoke; differences
 * between advice kinds are about placement (before/after/try-catch) and about
 * which registers hold the bound args, not about the invoke shape.
 */
public final class MonitorInvokeBuilder {

    private MonitorInvokeBuilder() {}

    /**
     * @return a single-instruction list containing the {@code invoke-static}
     *         call to {@code <monitorOwner>.<monitorCall.method>(<paramTypes>)V}
     *         with arg registers drawn from {@code match.argBindings}.
     *
     * @throws UnresolvedBindingException when any binding name from
     *         {@code monitorCall.args} cannot be resolved to a real register.
     *         {@code DexWeaver} catches this at the {@code emitter.emit(ctx)}
     *         funnel, increments
     *         {@code WeaveReport.plansSkippedUnresolvedBinding}, logs the
     *         site, and continues weaving. The previous contract injected
     *         literal {@code v0} for unresolved names, which produced
     *         type-mismatched invokes that ART rejected with
     *         {@code java.lang.VerifyError} — see INV-INS-71 and
     *         {@code docs/20260514_erro.md}.
     */
    static List<BuilderInstruction> buildInvoke(EmitContext ctx) {
        AdviceDescriptor advice = ctx.advice;
        MonitorCallDescriptor call = ctx.primaryMonitorCall();
        if (call == null) return Collections.emptyList();

        String owner = ctx.monitorOwnerDescriptor;
        String eventMethod = shortName(call.getMethod());
        MethodReference ref = buildMethodReference(owner, eventMethod, advice, ctx.typeResolver);

        int[] regs = registersFor(advice, ctx.match);
        if (regs == null) {
            // Determine which binding name caused the failure for the WARN
            // message. Walk monitorCall.args, find the first name absent from
            // the resolved bindings map, and surface it. We re-resolve to
            // identify the gap rather than threading state out of
            // registersFor — the cost is negligible (LinkedHashMap lookup)
            // and registersFor's contract stays "returns int[] | null, never
            // throws".
            java.util.List<String> argNames = call.getArgs() != null
                    ? call.getArgs() : adviceParamNames(advice);
            java.util.Map<String, Integer> nameToReg = resolveBindings(advice, ctx.match);
            String unresolved = null;
            for (String n : argNames) {
                if (nameToReg.get(n) == null) { unresolved = n; break; }
            }
            throw new UnresolvedBindingException(
                    advice.getName() != null ? advice.getName() : eventMethod,
                    unresolved);
        }
        // gh59 (2nd hunk): expand wide-typed advice args (`J`/`D`) into the
        // pair (vN, vN+1) before handing the operand array to buildInvokeStatic.
        // registersFor produces one register per arg name — correct for narrow
        // types but wrong for wide: the emitted invoke would declare the wrong
        // slot count (`regs.length` instead of `narrow + 2*wide`), and the
        // verifier rejects the low half of the wide as "non-reference register
        // (type=Long Low Half)" used in a position that expects a single slot.
        int[] expandedRegs = expandWideSlots(regs, ref);
        return Collections.singletonList(buildInvokeStatic(ref, expandedRegs));
    }

    /**
     * Expand {@code regs} so that every wide-typed parameter (`J`/`D` per the
     * monitor's {@code ref} descriptors) occupies two consecutive slots
     * {@code (vN, vN+1)} in the operand array. Narrow parameters pass through
     * unchanged. Closes the gh59 2nd hunk — the matched callee already pinned
     * the low half register via {@code PointcutMatcher.buildCallMatch}; the
     * adjacent {@code vN+1} is guaranteed by the wide-pair contiguity
     * invariant of the source bytecode (the verifier requires it). When the
     * monitor signature has no wide param the array is returned unchanged.
     */
    private static int[] expandWideSlots(int[] regs, MethodReference ref) {
        java.util.List<? extends CharSequence> descriptors = ref.getParameterTypes();
        int totalSlots = 0;
        for (CharSequence d : descriptors) {
            totalSlots += isWide(d) ? 2 : 1;
        }
        if (totalSlots == regs.length) {
            return regs;
        }
        int[] out = new int[totalSlots];
        int k = 0;
        for (int i = 0; i < regs.length && i < descriptors.size(); i++) {
            out[k++] = regs[i];
            if (isWide(descriptors.get(i))) {
                out[k++] = regs[i] + 1;
            }
        }
        return out;
    }

    private static boolean isWide(CharSequence d) {
        return d.length() == 1 && (d.charAt(0) == 'J' || d.charAt(0) == 'D');
    }

    private static String shortName(String fullyQualifiedMethod) {
        if (fullyQualifiedMethod == null) return "";
        int dot = fullyQualifiedMethod.lastIndexOf('.');
        return dot >= 0 ? fullyQualifiedMethod.substring(dot + 1) : fullyQualifiedMethod;
    }

    private static MethodReference buildMethodReference(String owner, String name,
                                                         AdviceDescriptor advice,
                                                         TypeResolver resolver) {
        // Build paramDescriptors in `monitorCall.args` order, looking up each
        // name's declared type in the advice's parameters / returning /
        // throwing list. The runtime monitor's signature follows
        // monitorCall.args order, not the advice's declaration order — they
        // can differ when the advice's bindings are reordered.
        MonitorCallDescriptor call = primaryMonitorCall(advice);
        java.util.List<String> argNames = call != null ? call.getArgs()
                : adviceParamNames(advice);
        if (argNames == null) argNames = adviceParamNames(advice);

        java.util.Map<String, String> nameToType = new java.util.LinkedHashMap<>();
        for (ParameterDescriptor p : advice.getParameters()) {
            nameToType.put(p.getName(), p.getType());
        }
        if (advice.getReturning() != null) {
            for (ParameterDescriptor p : advice.getReturning()) {
                nameToType.putIfAbsent(p.getName(), p.getType());
            }
        }
        if (advice.getThrowing() != null) {
            for (ParameterDescriptor p : advice.getThrowing()) {
                nameToType.putIfAbsent(p.getName(), p.getType());
            }
        }

        List<String> paramDescriptors = new ArrayList<>();
        for (String argName : argNames) {
            String type = nameToType.get(argName);
            if (type == null) {
                // A name in monitorCall.args that we cannot resolve: fall
                // back to Object so the descriptor is structurally valid
                // (the call would VerifyError at runtime; tracked as a
                // limitation in INV-INS-66 follow-up since we know this
                // means the binding system has gaps).
                type = "java.lang.Object";
            }
            paramDescriptors.add(resolver.toDescriptor(type));
        }
        // Monitor event methods return void by MOP convention; RV-Monitor's
        // generated RuntimeMonitor always declares the Event methods as
        // static void.
        return new ImmutableMethodReference(owner, name, paramDescriptors, "V");
    }

    /**
     * Resolve the register that the synthetic {@code returning} binding maps
     * to. For constructor advice, the freshly-constructed instance is the
     * semantic return value of {@code <init>} and lives in
     * {@code match.targetRegister} (regs[0] of the {@code invoke-direct}).
     * For non-constructor advice, the matcher records the destination of the
     * trailing {@code move-result*} under the synthetic key {@code $return}
     * in {@code match.argBindings} (INV-INS-72).
     *
     * <p>Reads {@code match.isConstructor} — the boolean field added by gh56
     * — rather than downcasting {@code matchedAgainst} to {@code CallPC},
     * which would re-introduce a {@code pointcut-engine} descriptor-type
     * dependency in this module.
     *
     * <p>Package-private to allow direct unit testing in
     * {@code MonitorInvokeBindingTest}.
     *
     * @return the resolved register, or {@code null} when neither path
     *         produces one (the caller MUST follow the unresolved-binding
     *         policy: skip the advice, log, increment counter).
     */
    static Integer resolveReturningRegister(Match match) {
        if (match.isConstructor && match.targetRegister >= 0) {
            return match.targetRegister;
        }
        return match.argBindings.get("$return");
    }

    /**
     * Walk the {@code monitorCall.args} list (advice param NAMES) in order
     * and resolve each to a DEX register via {@link #resolveBindings}.
     *
     * @return the resolved register array in {@code monitorCall.args} order;
     *         {@code null} when any name is unresolved. The caller MUST
     *         handle a {@code null} return by skipping the emission site and
     *         incrementing {@code WeaveReport.plansSkippedUnresolvedBinding}.
     *         This method never throws.
     */
    private static int[] registersFor(AdviceDescriptor advice, Match match) {
        // The advice descriptor's `monitorCalls.args` lists the param names
        // in the order the monitor expects them (not necessarily the advice's
        // declaration order), so we honor that order here.
        MonitorCallDescriptor call = primaryMonitorCall(advice);
        java.util.List<String> argNames = call != null ? call.getArgs()
                : adviceParamNames(advice);
        if (argNames == null) argNames = adviceParamNames(advice);

        java.util.Map<String, Integer> nameToReg = resolveBindings(advice, match);

        int[] regs = new int[argNames.size()];
        for (int i = 0; i < argNames.size(); i++) {
            Integer r = nameToReg.get(argNames.get(i));
            if (r == null) {
                // Unresolved binding — surface to the caller. Emitting v0
                // here would mask the gap with a type-mismatched invoke
                // that ART rejects (see INV-INS-71 + docs/20260514_erro.md).
                return null;
            }
            regs[i] = r;
        }
        return regs;
    }

    private static MonitorCallDescriptor primaryMonitorCall(AdviceDescriptor advice) {
        java.util.List<MonitorCallDescriptor> calls = advice.getMonitorCalls();
        return (calls == null || calls.isEmpty()) ? null : calls.get(0);
    }

    private static java.util.List<String> adviceParamNames(AdviceDescriptor advice) {
        java.util.List<String> names = new ArrayList<>();
        for (ParameterDescriptor p : advice.getParameters()) names.add(p.getName());
        return names;
    }

    /**
     * Build a {@code name → register} map covering every advice parameter,
     * by scanning the expression for {@code target()} / {@code args(...)}
     * clauses and the descriptor for {@code returning} / {@code throwing}.
     *
     * <p>Resolution rules (named-binding contract, gh56 INV-INS-71):
     * <ul>
     *   <li>{@code target(name)} → {@code match.targetRegister} when set;
     *       otherwise the name is left unresolved.
     *   <li>{@code args(n1, n2, ...)} → positional {@code match.argBindings}
     *       entries {@code arg00..argNN}; names whose slot is absent from
     *       the matcher's bindings are left unresolved.
     *   <li>{@code returning(name)} → {@link #resolveReturningRegister};
     *       for constructor advice this is the freshly-constructed instance
     *       at {@code match.targetRegister}; for non-constructor advice this
     *       is the {@code move-result*} destination recorded under
     *       {@code "$return"} (INV-INS-72).
     *   <li>{@code throwing(name)} → currently unsupported by the inline
     *       path; left unresolved (the wrapper system handles after-throwing).
     * </ul>
     *
     * <p>Literal-zero fallbacks are forbidden. Any name left out of the
     * returned map propagates as a {@code null} through {@link #registersFor},
     * which signals the caller to skip the emission site rather than emit
     * a malformed invoke with {@code v0} substituted (the root cause of the
     * 2026-05-08 VerifyError campaign — see {@code docs/20260514_erro.md}).
     */
    private static java.util.Map<String, Integer> resolveBindings(
            AdviceDescriptor advice, Match match) {
        java.util.Map<String, Integer> map = new java.util.LinkedHashMap<>();
        String expr = advice.getExpression() == null ? "" : advice.getExpression();

        // target(name) — receiver register; only added when the matcher
        // produced a real target register. Never inject literal 0.
        String targetName = extractSingleName(expr, "target(");
        if (targetName != null && match.targetRegister >= 0) {
            map.put(targetName, match.targetRegister);
        }

        // args(n1, n2, ...) — positional registers from match.argBindings.
        // Missing positional slots are intentionally left out of the map so
        // registersFor can detect the gap and return null.
        java.util.List<String> argsNames = extractCommaList(expr, "args(");
        for (int i = 0; i < argsNames.size(); i++) {
            String key = String.format("arg%02d", i);
            Integer reg = match.argBindings.get(key);
            if (reg != null) map.put(argsNames.get(i), reg);
        }

        // returning(name) — resolve via resolveReturningRegister(match):
        // constructor advice uses targetRegister (the freshly-constructed
        // instance, the semantic return value of <init>); non-constructor
        // advice uses the synthetic "$return" key (the move-result*
        // destination recorded by PointcutMatcher.buildCallMatch under
        // INV-INS-72). When the resolution yields null, the binding is
        // left unresolved and registersFor will skip the emission.
        if (advice.getReturning() != null) {
            Integer returningReg = resolveReturningRegister(match);
            if (returningReg != null) {
                for (ParameterDescriptor p : advice.getReturning()) {
                    map.putIfAbsent(p.getName(), returningReg);
                }
            }
        }
        // throwing(name) — placeholder mapping to the catch-handler register
        // slot. This is NOT a literal-0 unresolved-binding fallback (which
        // gh56 forbids for returning/args/target); it is the catch-block
        // convention where the AfterThrowingEmitter requests a scratch
        // register that move-exception writes into, and RegisterShifter
        // rewrites the placeholder to the allocated scratch index when the
        // catch block is materialised in dex-mutator. The placeholder slot
        // is therefore semantically distinct from the bug pattern in
        // INV-INS-71 (where 0 was substituted for an UNRESOLVABLE name in
        // monitorCall.args, producing a type-mismatched invoke).
        if (advice.getThrowing() != null) {
            for (ParameterDescriptor p : advice.getThrowing()) {
                map.putIfAbsent(p.getName(), 0);
            }
        }

        return map;
    }

    /**
     * Find the first occurrence of {@code prefix} (e.g. {@code "target("})
     * in {@code expr} and return the single identifier inside the parens,
     * or {@code null} when absent. Strips whitespace.
     */
    private static String extractSingleName(String expr, String prefix) {
        int idx = expr.indexOf(prefix);
        if (idx < 0) return null;
        int open = idx + prefix.length();
        int close = expr.indexOf(')', open);
        if (close < 0) return null;
        String body = expr.substring(open, close).trim();
        return body.isEmpty() ? null : body;
    }

    /**
     * Find {@code prefix} (e.g. {@code "args("}) and return the list of
     * comma-separated identifiers inside the parens. Empty list when absent
     * or when the body is empty.
     */
    private static java.util.List<String> extractCommaList(String expr, String prefix) {
        java.util.List<String> out = new ArrayList<>();
        int idx = expr.indexOf(prefix);
        if (idx < 0) return out;
        int open = idx + prefix.length();
        int close = expr.indexOf(')', open);
        if (close < 0) return out;
        String body = expr.substring(open, close).trim();
        if (body.isEmpty()) return out;
        for (String s : body.split(",")) {
            String t = s.trim();
            if (!t.isEmpty()) out.add(t);
        }
        return out;
    }

    /**
     * Build the {@code invoke-static} instruction for the monitor event call.
     *
     * <p>DEX format choice (INV-INS-69):
     * <ul>
     *   <li>{@code Format35c} — 4-bit register fields, addresses v0–v15
     *       only; preferred for ≤5-arg invokes when ALL operand registers
     *       fit in the 4-bit window.</li>
     *   <li>{@code Format3rc} (range) — 16-bit register fields, addresses
     *       v0–v65535 but requires CONTIGUOUS ASCENDING operands.</li>
     * </ul>
     *
     * <p>When any binding register is &gt; v15, Format35c cannot encode it
     * and the dexlib2 builder rejects the instruction at construction time
     * ({@code Invalid register: vN. Must be between v0 and v15, inclusive.}).
     * The fix: if the operands are already contiguous + ascending (the
     * usual case when the matched invoke was itself in {@code 3rc} form
     * with high registers and {@code monitorCall.args} preserves the
     * source order), escalate to Format3rc regardless of arg count. When
     * operands are non-contiguous AND any reg is high, throw the marker
     * exception {@link HighRegisterNonContiguous}; the caller in
     * {@code DexWeaver} catches it and increments
     * {@code plansSkippedHighRegister} so the failure is surfaced at a
     * counter rather than as an uncaught exception. A future enhancement
     * (move-from16 preambles into a contiguous low window) is the
     * canonical fix for the non-contiguous case.
     *
     * <p>Package-private for unit testing — see
     * MonitorInvokeBuilderHighRegisterTest (INV-INS-69).
     */
    static BuilderInstruction buildInvokeStatic(MethodReference ref, int[] regs) {
        boolean anyHighReg = false;
        for (int r : regs) {
            if (r > 15) { anyHighReg = true; break; }
        }
        if (regs.length <= 5 && !anyHighReg) {
            int[] padded = new int[5];
            System.arraycopy(regs, 0, padded, 0, regs.length);
            return new BuilderInstruction35c(
                    Opcode.INVOKE_STATIC, regs.length,
                    padded[0], padded[1], padded[2], padded[3], padded[4],
                    ref);
        }
        if (regs.length == 0 || isContiguousAscending(regs)) {
            int start = regs.length > 0 ? regs[0] : 0;
            return new BuilderInstruction3rc(
                    Opcode.INVOKE_STATIC_RANGE, start, regs.length, ref);
        }
        throw new HighRegisterNonContiguous(regs);
    }

    private static boolean isContiguousAscending(int[] regs) {
        for (int i = 1; i < regs.length; i++) {
            if (regs[i] != regs[0] + i) return false;
        }
        return true;
    }

    /**
     * Marker exception for the INV-INS-69 non-contiguous-high-registers
     * case. {@code DexWeaver}'s after-side advice loop catches this and
     * increments the {@code plansSkippedHighRegister} counter, so the
     * failure is surfaced as a tracked diagnostic rather than aborting
     * the whole APK's instrumentation.
     */
    public static final class HighRegisterNonContiguous extends RuntimeException {
        public final int[] regs;
        public HighRegisterNonContiguous(int[] regs) {
            super("non-contiguous high registers " + java.util.Arrays.toString(regs)
                    + " — Format35c overflow + Format3rc requires contiguity");
            this.regs = regs.clone();
        }
    }

    /**
     * Marker exception for gh56 INV-INS-71. Thrown by {@link #buildInvoke}
     * when at least one binding name in {@code monitorCall.args} cannot be
     * resolved to a real DEX register (the previous behaviour of
     * substituting literal {@code v0} produced ART {@code VerifyError} on
     * every constructor-with-returning advice in the 2026-05-08 campaign).
     *
     * <p>{@code DexWeaver} catches this at the per-advice emission funnel,
     * increments {@link DexWeaver.WeaveReport#plansSkippedUnresolvedBinding},
     * logs the site with the advice + binding name, and continues weaving
     * the rest of the APK.
     */
    public static final class UnresolvedBindingException extends RuntimeException {
        public final String adviceName;
        public final String bindingName;
        public UnresolvedBindingException(String adviceName, String bindingName) {
            super("unresolved binding '" + bindingName
                    + "' in advice '" + adviceName
                    + "' — emission skipped (would produce VerifyError)");
            this.adviceName = adviceName;
            this.bindingName = bindingName;
        }
    }
}
