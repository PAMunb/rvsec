package br.unb.cic.rv.mutator;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.emitter.AdviceEmitter;
import br.unb.cic.rv.emitter.EmitContext;
import br.unb.cic.rv.emitter.EmitPlan;
import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.emitter.InsertionPoint;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.PointcutExpression;
import br.unb.cic.rv.pointcut.PointcutExpressionParser;
import br.unb.cic.rv.pointcut.PointcutMatcher;
import br.unb.cic.rv.pointcut.TypeResolver;

import br.unb.cic.rv.emitter.WrapperEmitter;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.OneRegisterInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

import java.util.List;
import java.util.Objects;
import java.util.Optional;

/**
 * Top-level orchestrator that walks {@code ClassDef × Method × Instruction}
 * of a {@link DexFile} and applies every {@link EmitPlan} the
 * {@link EmitterDispatch} produces for each match.
 *
 * <p>This is the executor side of the advice-emitter / dex-mutator split:
 * plans come in, mutations go out. The class does not build instruction
 * sequences — that is the emitter's job. The class does not decide pointcut
 * semantics — that is the matcher's job. It only:
 * <ol>
 *   <li>Parses each advice's pointcut expression once (cached via Map).</li>
 *   <li>Iterates instructions, runs {@link PointcutMatcher} for each advice.</li>
 *   <li>On match, asks {@link EmitterDispatch} for the right emitter, builds
 *       an {@link EmitContext}, and applies the returned plan via
 *       {@link InstructionInjector} (with scratch registers supplied by
 *       {@link RegisterAllocator}).</li>
 * </ol>
 *
 * <p>The weaver never mutates the input {@link DexFile} directly: it builds
 * a {@code MutableDexFile}-shaped delta and returns it. (Dexlib2's immutable
 * model requires a rewrite step anyway; we lean on that to keep the input
 * side effect-free.) Plans requiring {@code <clinit>} synthesis, try/catch
 * ranges, or wrapper rewrites are marked in the returned weave report and
 * handled by follow-on passes (task 5.x integration).
 */
public final class DexWeaver {

    private final EmitterDispatch emitterDispatch;
    private final RegisterAllocator allocator;
    /**
     * Original {@link MethodReference} → wrapper {@link MethodReference}.
     * When an invoke instruction matches a key, the weaver REPLACES the
     * invoke's reference with the wrapper (instead of inserting an inline
     * hook), eliminating the register-aliasing class of bug (INV-INS-29):
     * the wrapper is a static method that calls the original AND fires the
     * monitor events, all using its own local register frame, so the
     * caller's registers stay byte-identical.
     */
    private final Map<String, MethodReference> wrapperReplacements;
    /**
     * Tracks the original wrapper entries (instance, non-static) so subtype
     * expansion can be performed after construction once a multi-DEX
     * {@link InheritanceResolver} is available. We retain ALL entries (including
     * statics) for simplicity, but {@link #expandWrapperReplacementsForApk}
     * filters to instance-only — statics aren't dispatched through subtypes.
     */
    private final java.util.List<WrapperEmitter.WrapperEntry> registeredWrappers;
    /**
     * Number of additional lookup keys registered by
     * {@link #expandWrapperReplacementsForApk} (i.e. subtype keys beyond the
     * original parent FQN key). Surfaced via {@link WeaveReport#wrappersAliasedToSubtype}.
     */
    private int wrappersAliasedToSubtype;

    public DexWeaver() {
        this(new EmitterDispatch(), new RegisterAllocator(),
                Collections.emptyList());
    }

    public DexWeaver(EmitterDispatch emitterDispatch, RegisterAllocator allocator) {
        this(emitterDispatch, allocator, Collections.emptyList());
    }

    public DexWeaver(EmitterDispatch emitterDispatch, RegisterAllocator allocator,
                     java.util.List<WrapperEmitter.WrapperEntry> wrappers) {
        this.emitterDispatch = Objects.requireNonNull(emitterDispatch);
        this.allocator = Objects.requireNonNull(allocator);
        this.wrapperReplacements = new LinkedHashMap<>();
        this.registeredWrappers = new ArrayList<>(wrappers);
        this.wrappersAliasedToSubtype = 0;
        for (WrapperEmitter.WrapperEntry w : wrappers) {
            registerWrapper(w);
        }
    }

    private void registerWrapper(WrapperEmitter.WrapperEntry w) {
        String origClassDesc = fqnToDescriptor(w.originalClassFqn);
        java.util.List<String> origParamDescs = new ArrayList<>(w.originalParamFqn.size());
        for (String p : w.originalParamFqn) origParamDescs.add(fqnToDescriptor(p));
        String origReturnDesc = fqnToDescriptor(w.originalReturnFqn);
        // Lookup key uses the ORIGINAL signature (no implicit receiver in
        // params) — that is exactly what dexlib2 reports as the call site's
        // MethodReference for both invoke-static and invoke-virtual /
        // invoke-direct / invoke-interface.
        String key = origClassDesc + "#" + w.originalMethodName + "("
                + String.join(",", origParamDescs) + ")" + origReturnDesc;
        // The wrapper is always emitted as a static method. For instance
        // wrappers we prepend the receiver descriptor so the wrapper's arity
        // matches the original invoke's register count: the receiver register
        // (first register of an invoke-virtual / invoke-direct / invoke-
        // interface) becomes the wrapper's first formal parameter when the
        // weaver rewrites the opcode to invoke-static.
        java.util.List<String> wrapperParamDescs = w.isStatic
                ? origParamDescs
                : prepend(origClassDesc, origParamDescs);
        MethodReference wrapperRef = new ImmutableMethodReference(
                WrapperEmitter.WRAPPER_CLASS_DESC, w.wrapperName,
                wrapperParamDescs, origReturnDesc);
        wrapperReplacements.put(key, wrapperRef);
    }

    /**
     * Register additional lookup keys for every APK-internal subtype of each
     * instance wrapper's parent class, so that virtual / interface dispatch
     * sites whose defining class is the subtype (e.g.
     * {@code Lcom/myapp/CustomCipher;->doFinal([B)[B} extending
     * {@code Ljavax/crypto/Cipher;}) also resolve to the same wrapper.
     *
     * <p>The wrapper {@link MethodReference} itself is unchanged — it still
     * points at {@code mop.MonitorWrappers.X(...)} declaring the parent type
     * as the receiver formal. The DEX verifier accepts the substitution
     * because subtypes are assignable to their supertypes.
     *
     * <p>Static wrappers are skipped: an {@code invoke-static MyCipher.create(...)}
     * resolves to {@code MyCipher}'s own static, not the parent's, so subtype
     * expansion would over-match.
     *
     * <p>The expansion is idempotent: keys already present in the lookup map
     * (notably the parent FQN key, plus any subtype keys from earlier calls)
     * are not double-counted toward {@code wrappersAliasedToSubtype}.
     *
     * <p>Hot-path note: lookup is O(1) (single map get); registration is
     * O(N×M) where N = wrappers and M = APK class count, and runs once per
     * APK before the per-DEX weave loop.
     *
     * @param inheritance multi-DEX inheritance resolver covering every DEX of
     *                    the APK being instrumented.
     */
    public void expandWrapperReplacementsForApk(InheritanceResolver inheritance) {
        Objects.requireNonNull(inheritance);
        for (WrapperEmitter.WrapperEntry w : registeredWrappers) {
            if (w.isStatic) continue;  // statics aren't dispatched via subtypes
            String origClassDesc = fqnToDescriptor(w.originalClassFqn);
            java.util.List<String> origParamDescs = new ArrayList<>(w.originalParamFqn.size());
            for (String p : w.originalParamFqn) origParamDescs.add(fqnToDescriptor(p));
            String origReturnDesc = fqnToDescriptor(w.originalReturnFqn);
            String paramSig = String.join(",", origParamDescs);
            // The wrapper's own MethodReference is parent-typed; reuse the
            // exact ref we already registered under the parent key.
            String parentKey = origClassDesc + "#" + w.originalMethodName + "("
                    + paramSig + ")" + origReturnDesc;
            MethodReference wrapperRef = wrapperReplacements.get(parentKey);
            if (wrapperRef == null) continue;  // shouldn't happen, defensive
            for (String subFqn : inheritance.subtypesOf(w.originalClassFqn)) {
                String subDesc = fqnToDescriptor(subFqn);
                String subKey = subDesc + "#" + w.originalMethodName + "("
                        + paramSig + ")" + origReturnDesc;
                if (wrapperReplacements.containsKey(subKey)) continue;  // idempotent
                wrapperReplacements.put(subKey, wrapperRef);
                wrappersAliasedToSubtype++;
            }
        }
    }

    private static java.util.List<String> prepend(String head, java.util.List<String> tail) {
        java.util.List<String> out = new ArrayList<>(tail.size() + 1);
        out.add(head);
        out.addAll(tail);
        return out;
    }

    private static String fqnToDescriptor(String fqn) {
        if (fqn == null || fqn.isEmpty() || "void".equals(fqn)) return "V";
        String base = fqn;
        int arr = 0;
        while (base.endsWith("[]")) { arr++; base = base.substring(0, base.length() - 2); }
        String d;
        switch (base) {
            case "boolean": d = "Z"; break;
            case "byte":    d = "B"; break;
            case "short":   d = "S"; break;
            case "char":    d = "C"; break;
            case "int":     d = "I"; break;
            case "long":    d = "J"; break;
            case "float":   d = "F"; break;
            case "double":  d = "D"; break;
            default:        d = "L" + base.replace('.', '/') + ";";
        }
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < arr; i++) sb.append('[');
        sb.append(d);
        return sb.toString();
    }

    private static String refKey(MethodReference r) {
        java.util.List<String> params = new ArrayList<>();
        for (CharSequence p : r.getParameterTypes()) params.add(p.toString());
        return r.getDefiningClass() + "#" + r.getName() + "("
                + String.join(",", params) + ")" + r.getReturnType();
    }

    private MethodReference findWrapperReplacement(Instruction insn) {
        if (wrapperReplacements.isEmpty()) return null;
        if (!(insn instanceof ReferenceInstruction)) return null;
        // Accept every invoke opcode the InstructionInjector knows how to
        // rewrite; the injector normalizes all of them to invoke-static while
        // preserving the register list (the receiver, when present, becomes
        // the first wrapper argument).
        if (!isInvokeOpcode(insn.getOpcode())) return null;
        Object refObj = ((ReferenceInstruction) insn).getReference();
        if (!(refObj instanceof MethodReference)) return null;
        return wrapperReplacements.get(refKey((MethodReference) refObj));
    }

    private static boolean isInvokeOpcode(Opcode op) {
        switch (op) {
            case INVOKE_VIRTUAL: case INVOKE_VIRTUAL_RANGE:
            case INVOKE_SUPER:   case INVOKE_SUPER_RANGE:
            case INVOKE_DIRECT:  case INVOKE_DIRECT_RANGE:
            case INVOKE_STATIC:  case INVOKE_STATIC_RANGE:
            case INVOKE_INTERFACE: case INVOKE_INTERFACE_RANGE:
                return true;
            default:
                return false;
        }
    }

    /**
     * Weave the given descriptor into every matching instruction of every
     * method of {@code dexFile}. Returns a simple counter report — the
     * mutation itself happens via the caller's {@link MutableMethodImplementation}
     * supplier (dexlib2 doesn't let us mutate read-only implementations
     * directly).
     */
    public WeaveReport weave(DexFile dexFile, AspectDescriptor descriptor,
                              TypeResolver typeResolver,
                              InheritanceResolver inheritance,
                              MutableImplSupplier mutableSupplier) {
        Objects.requireNonNull(dexFile);
        Objects.requireNonNull(descriptor);

        PointcutMatcher matcher = new PointcutMatcher(typeResolver, inheritance);
        int classesSeen = 0;
        int methodsSeen = 0;
        int matchesApplied = 0;
        int plansSkipped = 0;
        int plansSkippedAliasing = 0;
        int wrappersSubstituted = 0;
        int constructorInlineApplied = 0;
        int constructorInlineSkippedAliasing = 0;
        int plansSkippedHighRegister = 0;

        for (ClassDef classDef : dexFile.getClasses()) {
            classesSeen++;
            for (Method method : classDef.getMethods()) {
                methodsSeen++;
                MethodImplementation impl = method.getImplementation();
                if (impl == null) continue;
                List<Instruction> instructions = new java.util.ArrayList<>();
                for (Instruction ins : impl.getInstructions()) instructions.add(ins);

                // Materialize a mutable view eagerly only if there is at
                // least one wrapper substitution candidate in this method;
                // the materialization itself is cheap, but the supplier may
                // be lazy and we want to avoid pinning every method.
                MutableMethodImplementation mutCached = null;

                // Pass 1: wrapper substitution. `replaceInstruction` is
                // size-stable so the snapshot's indices remain valid for the
                // entire pass. We track which indices were substituted so
                // pass 2 (inline advice) can skip them — the wrapper already
                // handles the events for those call sites.
                java.util.Set<Integer> substitutedIndices = new java.util.HashSet<>();
                for (int idx = 0; idx < instructions.size(); idx++) {
                    Instruction ins = instructions.get(idx);
                    MethodReference wrapper = findWrapperReplacement(ins);
                    if (wrapper != null) {
                        if (mutCached == null) mutCached = mutableSupplier.forMethod(method);
                        if (mutCached != null) {
                            new InstructionInjector(mutCached).replaceInvoke(idx, wrapper);
                            substitutedIndices.add(idx);
                            wrappersSubstituted++;
                        }
                    }
                }

                // Pass 2: inline advice. Iterate from right to left so each
                // applyPlan insertion (BEFORE/AFTER/METHOD_ENTRY) shifts only
                // indices we have already processed — never the indices we
                // are about to visit. Snapshot indices remain valid against
                // BOTH the snapshot list AND mut's current state at the
                // moment of access.
                for (int idx = instructions.size() - 1; idx >= 0; idx--) {
                    if (substitutedIndices.contains(idx)) continue;
                    Instruction ins = instructions.get(idx);
                    for (AdviceDescriptor advice : descriptor.getAdvices()) {
                        PointcutExpression pe = parseCached(advice);
                        if (pe == null) { plansSkipped++; continue; }
                        Optional<Match> m = matcher.match(pe, classDef, method, ins,
                                idx, instructions.size());
                        if (m.isEmpty()) continue;
                        AdviceEmitter emitter;
                        try {
                            emitter = emitterDispatch.select(advice);
                        } catch (UnsupportedOperationException ex) {
                            plansSkipped++;
                            continue;
                        }
                        EmitContext ctx = new EmitContext(advice, m.get(), typeResolver,
                                monitorOwnerFor(descriptor));
                        EmitPlan plan;
                        try {
                            plan = emitter.emit(ctx);
                        } catch (br.unb.cic.rv.emitter.MonitorInvokeBuilder.HighRegisterNonContiguous ex) {
                            // INV-INS-32: bindings include a register > v15 and
                            // are non-contiguous, so neither Format35c (4-bit)
                            // nor Format3rc (contiguous) can encode the invoke.
                            // Defensive skip + counter; future fix is to emit
                            // move-from16 preambles into a contiguous low
                            // window before the invoke.
                            plansSkippedHighRegister++;
                            continue;
                        }

                        // INV-INS-29: AFTER advice that didn't get wrapper
                        // substitution (because the matched invoke is not
                        // a static call we can route through a wrapper —
                        // typically virtual / interface calls) is skipped
                        // defensively. The argBindings captured at match
                        // time (pre-call register values) would be read by
                        // an inline post-call hook AFTER the matched
                        // invoke's `move-result*` has overwritten them →
                        // VerifyError on every such site. BEFORE advice is
                        // unaffected (it fires pre-call, before any
                        // overwrites) and is emitted inline as designed.
                        //
                        // gh52 §5.13(a): constructor invokes (invoke-direct
                        // {recv, ...args}, T.<init>(...)V) return void →
                        // there is no `move-result*` after them, so the
                        // receiver and argument registers remain valid for
                        // the inline post-call hook. We allow inline-AFTER
                        // for that narrow case. The defensive
                        // resultRegisterAliasesBindings() check below
                        // surfaces any unexpected aliasing under a
                        // dedicated counter.
                        if (plan.insertionPoint() == InsertionPoint.AFTER) {
                            if (isConstructorInvoke(ins)) {
                                if (resultRegisterAliasesBindings(
                                        ins, instructions, idx, m.get())) {
                                    constructorInlineSkippedAliasing++;
                                    continue;
                                }
                                // fall through to apply the inline plan
                                constructorInlineApplied++;
                            } else {
                                plansSkippedAliasing++;
                                continue;
                            }
                        }

                        MutableMethodImplementation mut = mutCached != null
                                ? mutCached
                                : mutableSupplier.forMethod(method);
                        if (mut == null) {
                            plansSkipped++;
                            continue;
                        }
                        if (mutCached == null) mutCached = mut;
                        allocator.allocate(mut, plan.registers());
                        applyPlan(mut, idx, plan);
                        matchesApplied++;
                    }
                }
            }
        }
        return new WeaveReport(classesSeen, methodsSeen, matchesApplied,
                plansSkipped, plansSkippedAliasing, wrappersSubstituted,
                wrappersAliasedToSubtype,
                constructorInlineApplied, constructorInlineSkippedAliasing,
                plansSkippedHighRegister);
    }

    /**
     * Decide whether {@code insn} is a constructor invocation
     * ({@code invoke-direct} / {@code invoke-direct/range} of {@code <init>}).
     * Constructor invokes return {@code void}, so they are never followed by
     * {@code move-result*} and never alias their bindings — making them safe
     * targets for inline-AFTER advice even though the wrapper system cannot
     * cover them (a wrapper would have to allocate-and-construct, changing
     * call-site semantics).
     */
    private static boolean isConstructorInvoke(Instruction insn) {
        if (insn == null) return false;
        Opcode op = insn.getOpcode();
        if (op != Opcode.INVOKE_DIRECT && op != Opcode.INVOKE_DIRECT_RANGE) return false;
        if (!(insn instanceof ReferenceInstruction)) return false;
        Object refObj = ((ReferenceInstruction) insn).getReference();
        if (!(refObj instanceof MethodReference)) return false;
        return "<init>".equals(((MethodReference) refObj).getName());
    }

    /**
     * Decide whether the {@code move-result*} that immediately follows the
     * matched invoke (when present) overwrites a register that the advice's
     * binding (args / target) reads — the canonical aliasing condition that
     * makes an inline {@code after} hook produce a verifier-rejected class.
     *
     * <p>Example (cryptoapp regression that surfaced INV-INS-29):
     * <pre>
     *     const-string v0, "RSA/ECB/PKCS1Padding"      ; v0 = String
     *     invoke-static {v0}, Cipher.getInstance(String) ; matched
     *     move-result-object v0                         ; v0 = Cipher (overwritten!)
     *     invoke-static {v0}, monitor.afterEvent(String) ; would read Cipher, expect String
     * </pre>
     *
     * <p>Returns {@code true} when ANY register in the binding (every value of
     * {@code argBindings} plus {@code targetRegister}) equals the destination
     * register of the next-instruction {@code move-result*}, which is the
     * exact set of registers the runtime overwrites between the matched
     * invoke and the post-call hook.
     */
    private static boolean resultRegisterAliasesBindings(
            Instruction matched, List<Instruction> instructions, int idx, Match match) {
        if (idx + 1 >= instructions.size()) return false;
        Instruction next = instructions.get(idx + 1);
        if (!isMoveResult(next)) return false;
        if (!(next instanceof OneRegisterInstruction)) return false;
        int resultReg = ((OneRegisterInstruction) next).getRegisterA();
        for (Integer reg : match.argBindings.values()) {
            if (reg != null && reg == resultReg) return true;
        }
        if (match.targetRegister >= 0 && match.targetRegister == resultReg) return true;
        return false;
    }

    private static boolean isMoveResult(Instruction in) {
        if (in == null) return false;
        switch (in.getOpcode()) {
            case MOVE_RESULT:
            case MOVE_RESULT_OBJECT:
            case MOVE_RESULT_WIDE:
                return true;
            default:
                return false;
        }
    }

    /** Callback that returns a mutable view of the method's implementation. */
    public interface MutableImplSupplier {
        MutableMethodImplementation forMethod(Method method);
    }

    /** Cached parsing; identical expressions across advices are rare but cheap to cache. */
    private PointcutExpression parseCached(AdviceDescriptor advice) {
        String expr = advice.getExpression();
        if (expr == null || expr.isBlank()) return null;
        try {
            return PointcutExpressionParser.parse(expr);
        } catch (RuntimeException ex) {
            return null;
        }
    }

    private void applyPlan(MutableMethodImplementation mut, int idx, EmitPlan plan) {
        InstructionInjector inj = new InstructionInjector(mut);
        switch (plan.insertionPoint()) {
            case BEFORE:
                inj.insertBefore(idx, plan);
                break;
            case AFTER:
                inj.insertAfter(idx, plan);
                break;
            case METHOD_ENTRY:
                inj.insertAtMethodEntry(plan);
                break;
            case TRY_CATCH_WRAP:
            case REPLACE:
                // Pending: task 5.x integration installs try-range + handler
                // labels / swaps the invoke reference; the plan carries the
                // required data but full realization needs additional helpers
                // that live alongside WrapperEmitter rewrites.
                break;
            default:
                throw new IllegalStateException("unknown insertion point: " + plan.insertionPoint());
        }
    }

    private String monitorOwnerFor(AspectDescriptor d) {
        // Convention: the generated RuntimeMonitor lives in the "mop" package
        // under a name derived from the merged aspect name. For this
        // implementation we accept the canonical "mop.MultiSpec_1RuntimeMonitor"
        // emitted by rv-monitor; a future revision can parameterize this.
        String shortName = d.getShortName() == null ? "MultiSpec_1" : d.getShortName();
        return "Lmop/" + shortName + "RuntimeMonitor;";
    }

    public record WeaveReport(int classesSeen, int methodsSeen,
                               int matchesApplied, int plansSkipped,
                               int plansSkippedAliasing,
                               int wrappersSubstituted,
                               int wrappersAliasedToSubtype,
                               int constructorInlineApplied,
                               int constructorInlineSkippedAliasing,
                               int plansSkippedHighRegister) {}
}
