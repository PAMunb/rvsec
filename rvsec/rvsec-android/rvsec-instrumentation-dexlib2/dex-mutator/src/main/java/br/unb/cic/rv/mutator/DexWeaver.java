package br.unb.cic.rv.mutator;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.emitter.AdviceEmitter;
import br.unb.cic.rv.emitter.EmitContext;
import br.unb.cic.rv.emitter.EmitPlan;
import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.emitter.InsertionPoint;
import br.unb.cic.rv.emitter.StaticInitializationEmitter;
import br.unb.cic.rv.emitter.UnsupportedAspectConstructError;
import br.unb.cic.rv.pointcut.CombinedPC;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.NamedRefPC;
import br.unb.cic.rv.pointcut.NotWithinPC;
import br.unb.cic.rv.pointcut.PointcutExpression;
import br.unb.cic.rv.pointcut.PointcutExpressionParser;
import br.unb.cic.rv.pointcut.PointcutMatcher;
import br.unb.cic.rv.pointcut.TypeResolver;
import br.unb.cic.rv.pointcut.WithinPC;

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
 * side effect-free.) {@code <clinit>} synthesis, try/catch installation, and
 * wrapper-invoke rewrites are all realized within this same weave pass — via
 * {@code StaticInitSynthesizer} for a missing {@code <clinit>},
 * {@link InstructionInjector#installTryCatch} for {@code after() throwing}
 * ranges, and the {@code wrapperReplacements} map (INV-INS-66) for wrapped
 * callees — and are recorded in the returned {@link WeaveReport}.
 */
public final class DexWeaver {

    private final EmitterDispatch emitterDispatch;
    private final RegisterAllocator allocator;
    /**
     * Original {@link MethodReference} → wrapper {@link MethodReference}.
     * When an invoke instruction matches a key, the weaver REPLACES the
     * invoke's reference with the wrapper (instead of inserting an inline
     * hook), eliminating the register-aliasing class of bug (INV-INS-66):
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

    /**
     * §4.PERF.P2.1 instrumentation counter: number of times the class-invariant
     * {@code commonPointcut} verdict was evaluated during the last {@link #weave} call.
     * With the per-class hoist this is O(classes), not O(classes x methods x
     * instructions x advices). Exposed for the performance non-regression test.
     */
    private int commonAstEvals;

    public int getCommonAstEvals() {
        return commonAstEvals;
    }

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
        // Fail loud on a rebinding (D-B1). The key is the call site's own
        // signature and cannot be widened to tell two wrappers apart, so a
        // second wrapper for the same key has nowhere to go: the last write
        // would win and the earlier wrapper's monitor events would never fire
        // at that site, with the site attributed to whichever specification
        // registered last. WrapperEmitter now merges every advice that wraps a
        // call into ONE wrapper, so reaching this branch means the emitter and
        // the registry disagree about what counts as the same call — a build
        // defect, not a data one, and a silent overwrite here is exactly how it
        // stayed invisible for fifteen months.
        MethodReference bound = wrapperReplacements.get(key);
        if (bound != null && !bound.equals(wrapperRef)) {
            throw new IllegalStateException(
                    "wrapper registry key already bound to a different wrapper: " + key
                            + " -> " + bound.getName() + ", rebinding to " + w.wrapperName
                            + ". WrapperEmitter must emit one wrapper per original call.");
        }
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

        // §4.D.0: parse the descriptor's commonPointcut ONCE and AND-compose it onto every advice
        // expression before matching. The commonPointcut carries the class-level exclusions
        // (`BaseAspect.notwithin()`, `!within(...RVMObject+)`) that NEVER appear in an advice's own
        // expression; without this composition those exclusions never reach the matcher and §4.B/§4.D
        // are inert. Parsed once per weave (the commonPointcut is identical across all advices).
        PointcutExpression commonAst = parseCommonPointcut(descriptor);
        List<String> baseAspectExclusions = descriptor.getBaseAspectExclusions();
        String aspectName = descriptor.getAspectName();

        // §4.PERF.P2.1: the commonPointcut verdict depends ONLY on the class — its clauses
        // (within / notwithin / adviceexecution / BaseAspect.notwithin()) read only classDef and
        // bind nothing. When the parsed tree is class-invariant we evaluate it once per class (a
        // synthetic-probe gate at the top of the for-ClassDef loop) instead of AND-ing it into
        // every (instruction x advice) match. If the tree ever carried an instruction-dependent
        // clause (call/execution/staticinitialization/this/target/args) we fall back to the
        // per-instruction composition for correctness.
        boolean hoistCommon = commonAst != null && isClassInvariant(commonAst);
        commonAstEvals = 0;

        int classesSeen = 0;
        int methodsSeen = 0;
        int matchesApplied = 0;
        int plansSkipped = 0;
        int plansSkippedAliasing = 0;
        int wrappersSubstituted = 0;
        int constructorInlineApplied = 0;
        int constructorInlineSkippedAliasing = 0;
        int plansSkippedHighRegister = 0;
        // gh56 INV-INS-71: emission sites where the named-binding resolver
        // returned null because monitorCall.args referenced a name the matcher
        // could not bind to a register. Replaces the prior literal-v0 fallback
        // which produced ART VerifyError on every constructor + returning
        // advice (see docs/20260514_erro.md).
        int plansSkippedUnresolvedBinding = 0;

        // §4.Y staticinit pre-pass: deliver the Signature event for every
        // staticinitialization(T+) advice across every matching class —
        // synthesizing a <clinit> when one is absent, or prepending into the
        // existing one. Runs before the per-method loop (which skips
        // staticinit advice) so synthesized methods are registered ahead of
        // serialization. Returns the two emit counters.
        StaticInitResult siResult = weaveStaticInit(dexFile, descriptor, matcher,
                commonAst, baseAspectExclusions, aspectName, mutableSupplier);
        int staticInitSynthesized = siResult.synthesized;
        int staticInitPrepended = siResult.prepended;
        matchesApplied += staticInitSynthesized + staticInitPrepended;

        for (ClassDef classDef : dexFile.getClasses()) {
            classesSeen++;
            // §4.PERF.P2.1: per-class commonPointcut gate. The commonPointcut is class-invariant
            // (§4.D.0 — its exclusions gate the match at the class level). When hoisted we evaluate
            // it ONCE here; a class it rejects emits NOTHING (the `continue` skips every method,
            // instruction, and advice — exactly the per-instruction AND would have done). When
            // hoisted, `perInstructionCommon` is null so the inner loop matches the advice pe alone.
            PointcutExpression perInstructionCommon = commonAst;
            if (hoistCommon) {
                commonAstEvals++;
                if (!classMatchesCommon(matcher, commonAst, classDef,
                        baseAspectExclusions, aspectName)) {
                    continue;
                }
                perInstructionCommon = null;
            }
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
                        // staticinitialization(...) advice is owned entirely by
                        // the staticinit pre-pass (§4.Y): it must run for classes
                        // with NO <clinit> (never visited by this per-method loop)
                        // and for classes WITH one, uniformly. Skipping it here
                        // avoids a double-emit on existing <clinit>.
                        if (isStaticInitAdvice(advice)) continue;
                        PointcutExpression pe = parseCached(advice);
                        if (pe == null) { plansSkipped++; continue; }
                        // §4.D.0: AND-compose the commonPointcut so its class-level exclusions gate
                        // the match. The matcher resolves BaseAspect.notwithin() against the
                        // descriptor's baseAspectExclusions (passed below). §4.PERF.P2.1: when the
                        // commonPointcut was hoisted to the per-class gate above, perInstructionCommon
                        // is null and we match the advice pe alone (the class already passed the gate).
                        PointcutExpression effective = (perInstructionCommon == null) ? pe
                                : new CombinedPC(CombinedPC.Op.AND, perInstructionCommon, pe);
                        Optional<Match> m = matcher.match(effective, classDef, method, ins,
                                idx, instructions.size(), instructions,
                                baseAspectExclusions, aspectName);
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
                            // INV-INS-69: bindings include a register > v15 and
                            // are non-contiguous, so neither Format35c (4-bit)
                            // nor Format3rc (contiguous) can encode the invoke.
                            // Defensive skip + counter; future fix is to emit
                            // move-from16 preambles into a contiguous low
                            // window before the invoke.
                            plansSkippedHighRegister++;
                            continue;
                        } catch (br.unb.cic.rv.emitter.MonitorInvokeBuilder.UnresolvedBindingException ex) {
                            // gh56 INV-INS-71: at least one binding name in
                            // monitorCall.args has no register in the resolved
                            // map (e.g. an args(name) the matcher could not
                            // locate, or a returning(name) with no $return key
                            // and no constructor targetRegister). Emitting v0
                            // here would VerifyError at runtime, so we surface
                            // the gap at a counter and continue.
                            plansSkippedUnresolvedBinding++;
                            // The WARN below is intentionally terse — the
                            // counter + adviceName/bindingName carry the
                            // actionable info, full context (className,
                            // methodName, insnIndex) is available from the
                            // surrounding loop variables for richer logging
                            // when --log-level=DEBUG is wired in.
                            System.err.println("[gh56] skipping advice '"
                                    + ex.adviceName
                                    + "' at " + classDef.getType()
                                    + " idx=" + idx
                                    + ": unresolved binding '" + ex.bindingName + "'");
                            continue;
                        }

                        // INV-INS-66: AFTER advice that didn't get wrapper
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
                        // Ordering invariant (INV-INS-87): allocate MAY grow the
                        // frame and hand back a fresh clone, so the swap+replaceImpl
                        // for that clone MUST land BEFORE applyPlan runs — applyPlan
                        // (and any §4.T rebuild it triggers) must mutate the grown
                        // MMI, and the supplier must be pointed at it before
                        // serialization reads the method. Doing applyPlan on the
                        // pre-growth `mut` would emit into an MMI the supplier no
                        // longer serves, losing the extra registers on disk.
                        RegisterAllocation alloc = allocator.allocate(mut, plan.registers());
                        if (alloc.newImpl() != null) {
                            // Frame growth via clone returned a fresh MMI;
                            // swap the local + cached refs and notify the
                            // supplier so subsequent forMethod lookups see
                            // the post-spill MMI (gh61 INV-INS-87 / D5).
                            mut = alloc.newImpl();
                            mutCached = mut;
                            mutableSupplier.replaceImpl(method, mut);
                        }
                        MutableMethodImplementation rebuilt =
                                applyPlan(mut, idx, plan, alloc);
                        if (rebuilt != null) {
                            // §4.T range-splitting rebuilt the MMI (dexlib2's
                            // try-block list is read-only); adopt it as the
                            // current + cached impl and notify the supplier so
                            // serialisation sees the split try-table + handler.
                            mut = rebuilt;
                            mutCached = rebuilt;
                            mutableSupplier.replaceImpl(method, rebuilt);
                        }
                        matchesApplied++;
                    }
                }
            }
        }
        return new WeaveReport(classesSeen, methodsSeen, matchesApplied,
                plansSkipped, plansSkippedAliasing, wrappersSubstituted,
                wrappersAliasedToSubtype,
                constructorInlineApplied, constructorInlineSkippedAliasing,
                plansSkippedHighRegister,
                plansSkippedUnresolvedBinding,
                staticInitSynthesized, staticInitPrepended);
    }

    /** Outcome of the §4.Y staticinit pre-pass. */
    private record StaticInitResult(int synthesized, int prepended) {}

    /**
     * §4.Y: deliver the {@code *staticinitEvent(Signature)} for every
     * {@code staticinitialization(T+)} advice across every matching class.
     *
     * <p>For each class, each staticinit advice is matched via a synthetic
     * {@code <clinit>} probe so the full matcher pipeline (type pattern,
     * subtype expansion, {@code commonPointcut} exclusions) decides the match.
     * On a match:
     * <ul>
     *   <li><b>No {@code <clinit>}</b>: synthesize one via
     *       {@link StaticInitSynthesizer} carrying the Signature-delivery body,
     *       and register it through {@code addSynthesizedMethod}.</li>
     *   <li><b>Existing {@code <clinit>}</b>: spill two low registers (so the
     *       const-class + new-instance have a verifier-valid frame) and prepend
     *       the delivery body at method entry.</li>
     * </ul>
     */
    private StaticInitResult weaveStaticInit(DexFile dexFile, AspectDescriptor descriptor,
                                             PointcutMatcher matcher, PointcutExpression commonAst,
                                             List<String> baseAspectExclusions, String aspectName,
                                             MutableImplSupplier mutableSupplier) {
        List<AdviceDescriptor> siAdvices = new ArrayList<>();
        for (AdviceDescriptor a : descriptor.getAdvices()) {
            if (isStaticInitAdvice(a)) siAdvices.add(a);
        }
        if (siAdvices.isEmpty()) return new StaticInitResult(0, 0);

        String monitorOwner = monitorOwnerFor(descriptor);
        int synthesized = 0;
        int prepended = 0;

        // §4.PERF.P2.1: hoist the class-invariant commonPointcut gate out of the per-advice loop
        // here too — evaluate it once per class instead of AND-ing it into every staticinit probe.
        boolean hoistCommon = commonAst != null && isClassInvariant(commonAst);

        for (ClassDef classDef : dexFile.getClasses()) {
            PointcutExpression perAdviceCommon = commonAst;
            if (hoistCommon) {
                commonAstEvals++;
                if (!classMatchesCommon(matcher, commonAst, classDef,
                        baseAspectExclusions, aspectName)) {
                    continue;
                }
                perAdviceCommon = null;
            }
            Method existingClinit = findClinit(classDef);
            for (AdviceDescriptor advice : siAdvices) {
                PointcutExpression pe = parseCached(advice);
                if (pe == null) continue;
                PointcutExpression effective = (perAdviceCommon == null) ? pe
                        : new CombinedPC(CombinedPC.Op.AND, perAdviceCommon, pe);
                if (!staticInitMatchesClass(matcher, effective, classDef,
                        baseAspectExclusions, aspectName)) {
                    continue;
                }

                if (!StaticInitializationEmitter.deliversSignature(advice)) {
                    // Non-Signature staticinit advice is out of §4.Y's scope;
                    // skip rather than emit a malformed event. The corpus's
                    // staticinit advices all carry the getSignature() token.
                    continue;
                }
                // One event per monitor call the advice carries (INV-INS-104).
                // A fused staticinit advice delivers the same ClassSignature to
                // each of them.
                List<String> events = StaticInitializationEmitter.eventMethodNames(advice);

                if (existingClinit == null) {
                    // Synthesize a fresh <clinit>: deliver against v0/v1 in a
                    // 2-register private frame.
                    List<BuilderInstruction> body =
                            StaticInitializationEmitter.signatureDelivery(
                                    monitorOwner, events, classDef.getType(),
                                    /*regClass=*/ 0, /*regSig=*/ 1);
                    Method clinit = StaticInitSynthesizer.synthesize(
                            classDef.getType(), body, /*registerCount=*/ 2);
                    mutableSupplier.addSynthesizedMethod(classDef.getType(), clinit);
                    synthesized++;
                } else {
                    MutableMethodImplementation mut =
                            mutableSupplier.forMethod(existingClinit);
                    if (mut == null) continue;
                    // Free v0/v1 at the low end so the delivery body's
                    // const-class/new-instance have a verifier-valid frame;
                    // spillLowRegisters returns a fresh MMI (notify supplier).
                    MutableMethodImplementation grown;
                    try {
                        grown = RegisterShifter.spillLowRegisters(mut, 2);
                    } catch (RuntimeException ex) {
                        // Spill veto (rare format); skip this site conservatively.
                        continue;
                    }
                    mutableSupplier.replaceImpl(existingClinit, grown);
                    List<BuilderInstruction> body =
                            StaticInitializationEmitter.signatureDelivery(
                                    monitorOwner, events, classDef.getType(),
                                    /*regClass=*/ 0, /*regSig=*/ 1);
                    int at = 0;
                    for (BuilderInstruction ins : body) {
                        grown.addInstruction(at++, ins);
                    }
                    prepended++;
                }
            }
        }
        return new StaticInitResult(synthesized, prepended);
    }

    private static boolean isStaticInitAdvice(AdviceDescriptor advice) {
        String expr = advice.getExpression();
        return expr != null && expr.contains("staticinitialization(");
    }

    private static Method findClinit(ClassDef classDef) {
        for (Method m : classDef.getMethods()) {
            if ("<clinit>".equals(m.getName())) return m;
        }
        return null;
    }

    /**
     * Probe whether {@code pe} (a staticinit pointcut, possibly AND-composed
     * with the commonPointcut) matches {@code classDef} at the class level. The
     * staticinit matcher gates on a {@code <clinit>} method at instruction
     * index 0, so a synthetic single-instruction {@code <clinit>} probe is
     * passed; the remaining PCDs (type pattern, {@code !within}, named-ref
     * exclusions) read only {@code classDef}.
     */
    private boolean staticInitMatchesClass(PointcutMatcher matcher, PointcutExpression pe,
                                           ClassDef classDef, List<String> baseAspectExclusions,
                                           String aspectName) {
        MutableMethodImplementation probeImpl = new MutableMethodImplementation(1);
        BuilderInstruction probeInsn = new com.android.tools.smali.dexlib2.builder.instruction
                .BuilderInstruction10x(Opcode.RETURN_VOID);
        probeImpl.addInstruction(probeInsn);
        Method probe = new com.android.tools.smali.dexlib2.immutable.ImmutableMethod(
                classDef.getType(), "<clinit>", Collections.emptyList(), "V",
                com.android.tools.smali.dexlib2.AccessFlags.STATIC.getValue()
                        | com.android.tools.smali.dexlib2.AccessFlags.CONSTRUCTOR.getValue(),
                null, null, probeImpl);
        List<Instruction> probeList = new ArrayList<>();
        for (Instruction ins : probeImpl.getInstructions()) probeList.add(ins);
        try {
            return matcher.match(pe, classDef, probe, probeList.get(0),
                    0, probeList.size(), probeList,
                    baseAspectExclusions, aspectName).isPresent();
        } catch (RuntimeException ex) {
            // A LegacyDescriptorException (empty exclusions) or unresolved
            // named-ref fails the match closed — consistent with the main
            // loop's conservative behaviour.
            return false;
        }
    }

    /**
     * §4.PERF.P2.1: evaluate the class-invariant {@code commonPointcut} verdict ONCE for a class.
     * The commonPointcut's clauses (within / notwithin / adviceexecution / BaseAspect.notwithin())
     * read only {@code classDef}, so the {@code <clinit>} synthetic probe used by
     * {@link #staticInitMatchesClass} resolves the verdict identically regardless of method or
     * instruction — {@link #isClassInvariant} guarantees no instruction-dependent clause is present.
     * Returning {@code false} makes the caller skip the entire class, which preserves §4.D.0 exactly
     * (a class the commonPointcut rejects emits nothing).
     */
    private boolean classMatchesCommon(PointcutMatcher matcher, PointcutExpression commonAst,
                                       ClassDef classDef, List<String> baseAspectExclusions,
                                       String aspectName) {
        return staticInitMatchesClass(matcher, commonAst, classDef,
                baseAspectExclusions, aspectName);
    }

    /**
     * §4.PERF.P2.1: true iff the pointcut tree's match verdict depends solely on the class — i.e.
     * it is built only from {@link WithinPC}, {@link NotWithinPC}, the class-only {@link NamedRefPC}
     * forms ({@code BaseAspect.notwithin()} which expands to a NotWithinPC AND-chain, and the
     * vacuously-true {@code adviceexecution()} / {@code !adviceexecution()}), combined with
     * {@code &&}/{@code ||}. Such a tree can be hoisted to a per-class gate. Any instruction-dependent
     * clause (call / execution / staticinitialization / target / args / if / generic negation) makes
     * it false, forcing the per-instruction fallback. The canonical commonPointcut
     * ({@code !within(RVMObject+) && !adviceexecution() && BaseAspect.notwithin()}) is class-invariant.
     */
    private boolean isClassInvariant(PointcutExpression pe) {
        if (pe instanceof CombinedPC combined) {
            return isClassInvariant(combined.left()) && isClassInvariant(combined.right());
        }
        if (pe instanceof NamedRefPC named) {
            String name = named.name();
            return "BaseAspect.notwithin()".equals(name) || name.contains("adviceexecution");
        }
        return pe instanceof WithinPC || pe instanceof NotWithinPC;
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
     * <p>Example (cryptoapp regression that surfaced INV-INS-66):
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

    /**
     * Callback that returns a mutable view of the method's implementation.
     *
     * <p>{@link #replaceImpl(Method, MutableMethodImplementation)} is the
     * companion update hook used by frame-growth operations
     * ({@code RegisterShifter.bumpRegisterCount} /
     * {@code spillLowRegisters}) — after they allocate a fresh MMI to grow
     * the register frame, the caller MUST notify the supplier so subsequent
     * {@link #forMethod} lookups return the new MMI (otherwise the serialised
     * dex would drop the frame growth and any instructions injected onto the
     * new MMI; gh59 5-APK {@code VerifyError} residual, design.md D5).
     *
     * <p>Default no-op: in-process test suppliers (per-fixture maps with no
     * frame growth) do not need to override. The canonical implementation
     * lives in {@code DexFileMutator.replaceImpl}.
     */
    public interface MutableImplSupplier {
        MutableMethodImplementation forMethod(Method method);

        default void replaceImpl(Method method, MutableMethodImplementation newImpl) { }

        /**
         * Register a brand-new method to be appended to the class identified by
         * {@code definingClassDescriptor} ({@code Lcls;}) at serialization.
         * Used by the staticinit pre-pass (§4.Y) to add a synthesized
         * {@code <clinit>} to a class that has none — that method cannot be
         * obtained through {@link #forMethod} (no original implementation to
         * mutate). Default no-op for test suppliers that assert against an
         * in-memory mutable view; the canonical implementation delegates to
         * {@code DexFileMutator.addSynthesizedMethod}.
         */
        default void addSynthesizedMethod(String definingClassDescriptor, Method method) { }
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

    /**
     * §4.D.0: parse the descriptor's {@code commonPointcut} once per weave. Returns {@code null}
     * when absent or blank, in which case each advice expression is matched alone. A non-null
     * result is AND-composed onto every advice match.
     *
     * <p>An expression that is present but unparseable fails the weave. It used to be swallowed
     * into {@code null}, which reads as graceful degradation and is not: the commonPointcut is
     * where the class-level exclusions live ({@code BaseAspect.notwithin()},
     * {@code !within(...RVMObject+)}), and they appear in no advice's own expression. Dropping it
     * silently weaves every site those clauses exist to exclude — instrumentation that is wrong
     * with neither error nor warning, over machine-generated source no reviewer reads. Failing
     * here names the expression and the aspect, so the parser gets extended deliberately, in its
     * own change.
     */
    private PointcutExpression parseCommonPointcut(AspectDescriptor descriptor) {
        String cp = descriptor.getCommonPointcut();
        if (cp == null || cp.isBlank()) return null;
        try {
            return PointcutExpressionParser.parse(cp);
        } catch (RuntimeException ex) {
            throw new UnsupportedAspectConstructError(
                    "unparseable commonPointcut in aspect '" + descriptor.getAspectName()
                            + "': " + cp, ex);
        }
    }

    /**
     * Apply {@code plan} to {@code mut} at {@code idx}. Returns a fresh MMI when
     * the plan rebuilds the implementation (the §4.T TRY_CATCH_WRAP path, whose
     * range-splitting must reconstruct the MMI because dexlib2's try-block list
     * is read-only); {@code null} for the in-place insertion points. The caller
     * swaps + notifies the supplier when a non-null MMI is returned.
     */
    private MutableMethodImplementation applyPlan(MutableMethodImplementation mut, int idx,
                           EmitPlan plan, RegisterAllocation alloc) {
        InstructionInjector inj = new InstructionInjector(mut);
        if (plan.guardSpec() != null
                && plan.guardSpec().kind() == EmitPlan.GuardKind.NOT_HOLDS_LOCK
                && plan.insertionPoint() != InsertionPoint.TRY_CATCH_WRAP) {
            // The emitter stacked +1 scratch for the holdsLock move-result on
            // top of the delegate's demand; it is the highest allocated slot.
            // (TRY_CATCH_WRAP sets its own guard scratch below — the highest
            // slot there is the exception register, not the move-result.)
            List<Integer> scratch = alloc.scratch();
            if (scratch.isEmpty()) {
                throw new IllegalStateException(
                        "NOT_HOLDS_LOCK guard plan carried no allocated scratch register");
            }
            inj.withGuardScratch(scratch.get(scratch.size() - 1));
        }
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
            case TRY_CATCH_WRAP: {
                // §4.T (D14 F-decision): install the after() throwing(...)
                // handler with range-splitting. The exception register is the
                // scratch slot the allocator grew the frame for (scratch(1));
                // move-exception writes the caught exception into it. The
                // range-splitting + strictly-nested layout is realised by
                // InstructionInjector.installTryCatch.
                List<Integer> scratch = alloc.scratch();
                if (scratch.isEmpty()) {
                    throw new IllegalStateException(
                            "after-throwing plan carried no allocated scratch register "
                                    + "for the move-exception target");
                }
                int exceptionRegister = scratch.get(scratch.size() - 1);
                if (plan.guardSpec() != null
                        && plan.guardSpec().kind() == EmitPlan.GuardKind.NOT_HOLDS_LOCK) {
                    // §4.T×§4.I composition: the holdsLock shape needs a second
                    // scratch for its move-result; it is the next-highest slot
                    // below the exception register (the emitter stacked +1 over
                    // the after-throwing scratch(1) demand).
                    inj.withGuardScratch(scratch.get(scratch.size() - 2));
                }
                return inj.installTryCatch(idx, plan, exceptionRegister);
            }
            case REPLACE:
                // Invoke-reference replacement is not applied per-site here: the
                // weaver rewrites wrapped invokes through the wrapperReplacements
                // map (see field doc, INV-INS-66), swapping the callee reference
                // during instruction iteration rather than through a REPLACE plan.
                // This branch therefore makes no MMI change and falls through to
                // return null.
                break;
            default:
                throw new IllegalStateException("unknown insertion point: " + plan.insertionPoint());
        }
        return null;
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
                               int plansSkippedHighRegister,
                               // gh56 INV-INS-71: count of emission sites where
                               // MonitorInvokeBuilder.buildInvoke returned null
                               // because at least one binding name in
                               // monitorCall.args could not be resolved to a
                               // real register. Replaces the previous behaviour
                               // of substituting literal v0 (which caused the
                               // 2026-05-08 VerifyError campaign). Thread-safe
                               // as long as DexWeaver processes classes
                               // sequentially within a single weave() call
                               // (current behaviour). If parallel class weaving
                               // is ever introduced, this counter must migrate
                               // to LongAdder and aggregation lifted out of the
                               // record.
                               int plansSkippedUnresolvedBinding,
                               // §4.Y: staticinitialization(T+) Signature
                               // deliveries. staticInitSynthesized counts
                               // classes that had no <clinit> and got one
                               // synthesized; staticInitPrepended counts
                               // classes whose existing <clinit> received the
                               // delivery at method entry. Both feed
                               // matchesApplied.
                               int staticInitSynthesized,
                               int staticInitPrepended) {}
}
