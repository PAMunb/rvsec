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
     */
    static List<BuilderInstruction> buildInvoke(EmitContext ctx) {
        AdviceDescriptor advice = ctx.advice;
        MonitorCallDescriptor call = ctx.primaryMonitorCall();
        if (call == null) return Collections.emptyList();

        String owner = ctx.monitorOwnerDescriptor;
        String eventMethod = shortName(call.getMethod());
        MethodReference ref = buildMethodReference(owner, eventMethod, advice, ctx.typeResolver);

        int[] regs = registersFor(advice, ctx.match);
        return Collections.singletonList(buildInvokeStatic(ref, regs));
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
                // limitation in INV-INS-29 follow-up since we know this
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

    private static int[] registersFor(AdviceDescriptor advice, Match match) {
        // Walk the monitorCall.args list (advice param NAMES) in order. For
        // each, resolve to a register by inspecting the advice's expression:
        //   - target(name)       → match.targetRegister
        //   - args(n1, n2, ...)  → match.argBindings.get("argNN") where NN
        //                          is the param's positional slot in args(...)
        //   - returning(name)    → unsupported here (after-returning is routed
        //                          through the wrapper system; see D5)
        //   - throwing(name)     → likewise
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
            regs[i] = r != null ? r : 0;
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
     * Returning/throwing entries are best-effort: they map to -1 when the
     * inline path can't supply a register (the wrapper system is the
     * canonical handler for those — D5).
     */
    private static java.util.Map<String, Integer> resolveBindings(
            AdviceDescriptor advice, Match match) {
        java.util.Map<String, Integer> map = new java.util.LinkedHashMap<>();
        String expr = advice.getExpression() == null ? "" : advice.getExpression();

        // target(name) — receiver register
        String targetName = extractSingleName(expr, "target(");
        if (targetName != null && match.targetRegister >= 0) {
            map.put(targetName, match.targetRegister);
        }

        // args(n1, n2, ...) — positional registers from match.argBindings
        java.util.List<String> argsNames = extractCommaList(expr, "args(");
        for (int i = 0; i < argsNames.size(); i++) {
            String key = String.format("arg%02d", i);
            Integer reg = match.argBindings.get(key);
            if (reg != null) map.put(argsNames.get(i), reg);
        }

        // returning(name) — best-effort; the inline path doesn't capture
        // the move-result destination, so this is left unbound (caller
        // falls back to v0). The wrapper system handles after-returning
        // correctly via D5 substitution; the inline-skipped paths are
        // tracked under INV-INS-29.
        if (advice.getReturning() != null) {
            for (ParameterDescriptor p : advice.getReturning()) {
                map.putIfAbsent(p.getName(), 0);
            }
        }
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
     * <p>DEX format choice (INV-INS-32):
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
     * MonitorInvokeBuilderHighRegisterTest (INV-INS-32).
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
     * Marker exception for the INV-INS-32 non-contiguous-high-registers
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
}
