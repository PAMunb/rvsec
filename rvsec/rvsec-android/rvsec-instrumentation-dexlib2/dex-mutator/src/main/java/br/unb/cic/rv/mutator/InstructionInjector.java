package br.unb.cic.rv.mutator;

import br.unb.cic.rv.emitter.EmitPlan;
import br.unb.cic.rv.emitter.InsertionPoint;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.BuilderTryBlock;
import com.android.tools.smali.dexlib2.builder.Label;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.iface.ExceptionHandler;
import com.android.tools.smali.dexlib2.iface.instruction.FiveRegisterInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.RegisterRangeInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * Primitive operations that realize an {@link EmitPlan} against a
 * dexlib2 {@link MutableMethodImplementation}.
 *
 * <p>This class does NOT resolve register aliasing, synthesize {@code <clinit>}
 * when missing, or install try/catch labels — those responsibilities belong to
 * the caller ({@link DexWeaver}) because they require cross-method context
 * (e.g., ClassDef-level mutation for {@code <clinit>} synthesis).
 *
 * <p>What it does:
 * <ul>
 *   <li>{@link #insertBefore} — inserts {@code plan.toInsert()} immediately
 *       before the instruction at {@code index}.</li>
 *   <li>{@link #insertAfter} — after the instruction at {@code index}.</li>
 *   <li>{@link #replaceInvoke} — rewrites the method reference of an
 *       existing invoke at {@code index} (used by
 *       {@code advice-emitter.WrapperEmitter} to route through
 *       {@code mop.MonitorWrappers}).</li>
 * </ul>
 */
public final class InstructionInjector {

    /** DEX descriptor + signature of {@code Thread.holdsLock(Object)}. */
    private static final MethodReference HOLDS_LOCK_REF = new ImmutableMethodReference(
            "Ljava/lang/Thread;", "holdsLock", List.of("Ljava/lang/Object;"), "Z");

    private final MutableMethodImplementation impl;
    /**
     * Scratch register the executor allocates for an {@code if(...)} guard's
     * {@code move-result} (the {@link EmitPlan.GuardKind#NOT_HOLDS_LOCK} shape).
     * {@code -1} when the current plan carries no guard or needs no scratch.
     */
    private int guardScratchRegister = -1;

    public InstructionInjector(MutableMethodImplementation impl) {
        this.impl = Objects.requireNonNull(impl);
    }

    /**
     * Supply the scratch register allocated for the current plan's
     * {@code if(...)} guard (used by the {@code NOT_HOLDS_LOCK} shape to hold
     * the {@code holdsLock(...)} boolean). Returns {@code this} for chaining.
     */
    public InstructionInjector withGuardScratch(int register) {
        this.guardScratchRegister = register;
        return this;
    }

    public void insertBefore(int index, EmitPlan plan) {
        if (plan.insertionPoint() == InsertionPoint.AFTER) {
            throw new IllegalArgumentException(
                    "plan declared InsertionPoint.AFTER but insertBefore was called");
        }
        insertAll(index, plan.toInsert());
        installGuard(index, plan);
    }

    public void insertAfter(int index, EmitPlan plan) {
        if (plan.insertionPoint() == InsertionPoint.BEFORE) {
            throw new IllegalArgumentException(
                    "plan declared InsertionPoint.BEFORE but insertAfter was called");
        }
        // INV-INS-64: when the matched invoke is followed by `move-result*`,
        // skip past the move-result so the inserted instructions don't
        // separate the invoke from its pseudo-result. The DEX `move-result*`
        // family is only valid as the immediate successor of an invoke that
        // returns a value; any non-`move-result` instruction in between makes
        // the move-result read from the wrong invoke (verifier-rejected when
        // the new invoke returns void, value-corrupted otherwise).
        int insertAt = index + 1;
        if (isInvokeOpcode(instructionAt(index)) && isMoveResult(instructionAt(insertAt))) {
            insertAt++;
        }
        insertAll(insertAt, plan.toInsert());
        installGuard(insertAt, plan);
    }

    private Instruction instructionAt(int idx) {
        if (idx < 0) return null;
        List<BuilderInstruction> ins = impl.getInstructions();
        return idx < ins.size() ? ins.get(idx) : null;
    }

    private static boolean isInvokeOpcode(Instruction in) {
        if (in == null) return false;
        Opcode op = in.getOpcode();
        switch (op) {
            case INVOKE_VIRTUAL: case INVOKE_VIRTUAL_RANGE:
            case INVOKE_SUPER:   case INVOKE_SUPER_RANGE:
            case INVOKE_DIRECT:  case INVOKE_DIRECT_RANGE:
            case INVOKE_STATIC:  case INVOKE_STATIC_RANGE:
            case INVOKE_INTERFACE: case INVOKE_INTERFACE_RANGE:
            case INVOKE_POLYMORPHIC: case INVOKE_POLYMORPHIC_RANGE:
            case INVOKE_CUSTOM:  case INVOKE_CUSTOM_RANGE:
                return true;
            default:
                return false;
        }
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

    public void insertAtMethodEntry(EmitPlan plan) {
        insertAll(0, plan.toInsert());
        installGuard(0, plan);
    }

    /**
     * Install the {@code if(...)} guard around the block of {@code plan}
     * instructions just inserted at {@code blockStart}. No-op when the plan
     * carries no {@link EmitPlan.GuardSpec}.
     *
     * <p>The guard prefix is inserted immediately before the block; its
     * conditional branch targets the instruction right after the block, so the
     * block (the monitor invoke) is bypassed exactly when the guard is false:
     * <ul>
     *   <li>{@link EmitPlan.GuardKind#NULL_CHECK} ({@code <bound> == null}):
     *       {@code if-nez vBound, :skip} — non-null bound ⇒ guard false ⇒ skip.</li>
     *   <li>{@link EmitPlan.GuardKind#NOT_HOLDS_LOCK}
     *       ({@code !Thread.holdsLock(<bound>)}):
     *       {@code invoke-static {vBound}, Thread.holdsLock(Object)Z} +
     *       {@code move-result vGuard} + {@code if-nez vGuard, :skip} — lock held
     *       ⇒ guard false ⇒ skip.</li>
     * </ul>
     *
     * <p>The skip label is created on this {@code impl} via
     * {@link MutableMethodImplementation#newLabelForIndex(int)} so dexlib2
     * tracks its location as the guard prefix shifts the block down (a detached
     * label built before insertion would not re-home — verified empirically).
     */
    public void installGuard(int blockStart, EmitPlan plan) {
        EmitPlan.GuardSpec guard = plan.guardSpec();
        if (guard == null) return;

        int blockLen = plan.toInsert().size();
        // Index of the first instruction AFTER the inserted block — the skip
        // target. newLabelForIndex tracks this location as the guard prefix is
        // inserted before the block (the index auto-advances).
        Label skip = impl.newLabelForIndex(blockStart + blockLen);

        List<BuilderInstruction> prefix = new ArrayList<>(3);
        switch (guard.kind()) {
            case NULL_CHECK:
                // if-nez vBound, :skip  (skip the invoke when bound is non-null)
                prefix.add(new BuilderInstruction21t(
                        Opcode.IF_NEZ, guard.boundRegister(), skip));
                break;
            case NOT_HOLDS_LOCK:
                if (guardScratchRegister < 0) {
                    throw new IllegalStateException(
                            "NOT_HOLDS_LOCK guard requires a scratch register; "
                                    + "withGuardScratch(...) was not called");
                }
                // invoke-static {vBound}, Thread.holdsLock(Object)Z
                prefix.add(new BuilderInstruction35c(
                        Opcode.INVOKE_STATIC, /*regCount=*/ 1,
                        /*c=*/ guard.boundRegister(), 0, 0, 0, 0,
                        HOLDS_LOCK_REF));
                // move-result vGuard
                prefix.add(new BuilderInstruction11x(
                        Opcode.MOVE_RESULT, guardScratchRegister));
                // if-nez vGuard, :skip  (skip the invoke when the lock IS held)
                prefix.add(new BuilderInstruction21t(
                        Opcode.IF_NEZ, guardScratchRegister, skip));
                break;
            default:
                throw new IllegalStateException("unknown guard kind: " + guard.kind());
        }
        insertAll(blockStart, prefix);
    }

    /**
     * Install an {@code after() throwing(...)} handler around the matched
     * invoke at {@code matchedIdx}, applying the range-splitting policy
     * (design.md D14, §4.T F-decision) so the result is strictly-nested and
     * ART-verifiable.
     *
     * <p>The handler block is appended at the END of the method (it is reached
     * only via the exception edge, never by fall-through — the method's own
     * terminating instruction precedes it):
     * <pre>
     *   :handler
     *     move-exception vException          ; ART invariant — FIRST instruction
     *     [ if(...) guard prefix, when gated ]
     *     invoke-static {... vException ...}, monitor.event(...)
     *     throw vException                   ; re-throw — LAST instruction
     * </pre>
     * The {@code throwing(<name>)}-bound operand of the monitor invoke (slot
     * {@code plan.tryCatchSpec().throwingOperandIndex()}) is rewritten from the
     * emitter's placeholder to {@code vException}.
     *
     * <p>Range-splitting: every pre-existing user try-block that COVERS
     * {@code matchedIdx} is split into three sequential ranges —
     * {@code [start, matched)} (head, original handlers), {@code [matched,
     * matched+1)} (the matched invoke, NEW handler listed FIRST then the
     * originals in original order), {@code [matched+1, end)} (tail, original
     * handlers). User try-blocks that do NOT cover {@code matchedIdx} are
     * preserved verbatim. When {@code matchedIdx} sits inside NO user try-block
     * (the non-nested baseline), a single standalone {@code [matched, matched+1)}
     * range carrying only the new handler is added.
     *
     * <p>The new handler listed FIRST on the matched range matters: ART scans a
     * code unit's handler entries in declaration order ("first-most-specific"),
     * so the advice handler fires before the user {@code catch} — and the
     * {@code throw vException} re-throw ensures the user {@code catch} still
     * sees the exception afterwards.
     *
     * <p>dexlib2's {@link MutableMethodImplementation#getTryBlocks()} returns an
     * unmodifiable view, so the pre-existing user try-block cannot be removed in
     * place. The method therefore appends the handler block + installs the guard
     * on {@code this.impl}, then rebuilds a fresh MMI carrying the split
     * try-block table via {@link RegisterShifter#rebuildWithTryBlocks} and
     * RETURNS it. The caller MUST swap its reference to the returned MMI and
     * notify the {@code MutableImplSupplier} (mirrors the gh61 frame-growth
     * contract — INV-INS-87).
     *
     * @param matchedIdx        index of the matched invoke (single covered unit)
     * @param plan              the TRY_CATCH_WRAP plan (handler body + spec + optional guard)
     * @param exceptionRegister the register {@code move-exception} writes the
     *                          caught exception into (allocated by the executor)
     * @return the fresh MMI carrying the split try-block table; the caller swaps
     *         + notifies the supplier
     */
    public MutableMethodImplementation installTryCatch(
            int matchedIdx, EmitPlan plan, int exceptionRegister) {
        if (plan.tryCatchSpec() == null) {
            throw new IllegalArgumentException(
                    "installTryCatch requires a TryCatchSpec on the plan");
        }
        // 1. Snapshot pre-existing user try-blocks BEFORE mutating. Each
        //    BuilderTryBlock carries exactly one handler; a range with N
        //    handlers is N entries sharing start/end labels. We capture index
        //    coordinates so the rebuild is independent of the appended block.
        List<TryRangeSnapshot> originals = new ArrayList<>();
        for (BuilderTryBlock tb : impl.getTryBlocks()) {
            int startIdx = tb.start.getLocation().getIndex();
            int endIdx = tb.end.getLocation().getIndex();
            ExceptionHandler h = tb.getExceptionHandlers().get(0);
            int handlerIdx = tb.exceptionHandler.getHandler().getLocation().getIndex();
            originals.add(new TryRangeSnapshot(
                    startIdx, endIdx, h.getExceptionType(), handlerIdx));
        }

        // 2. Materialise the handler block at the end of the method.
        int handlerStartIdx = impl.getInstructions().size();
        List<BuilderInstruction> body = new ArrayList<>();
        // move-exception vException — ART invariant: first instruction of any
        // catch handler. Without it the verifier rejects the handler.
        body.add(new BuilderInstruction11x(Opcode.MOVE_EXCEPTION, exceptionRegister));
        // The advice invoke(s), with the throwing-bound operand rewritten to
        // vException (the emitter emitted a placeholder it could not resolve).
        int throwingSlot = plan.tryCatchSpec().throwingOperandIndex();
        for (BuilderInstruction insn : plan.toInsert()) {
            body.add(rewriteThrowingOperand(insn, throwingSlot, exceptionRegister));
        }
        // throw vException — re-throw so user catch clauses still run.
        body.add(new BuilderInstruction11x(Opcode.THROW, exceptionRegister));
        insertAll(handlerStartIdx, body);

        // The advice invoke sits at handlerStartIdx + 1 (right after
        // move-exception); an if(...) guard, when present, gates ONLY that
        // invoke block — move-exception and throw always run, so a false guard
        // re-throws without firing the advice.
        if (plan.guardSpec() != null) {
            EmitPlan invokeOnly = new EmitPlan(plan.toInsert(), plan.insertionPoint(),
                    plan.registers(), plan.tryCatchSpec(), plan.guardSpec());
            installGuard(handlerStartIdx + 1, invokeOnly);
        }

        // 3. Compute the split try-block table. The matched range lists the NEW
        //    advice handler FIRST then the original handlers in original order
        //    (ART scans declaration order — advice fires before user catch).
        //    Catch-type for the new handler: the declared throwing type (or
        //    Throwable for catch-any). The new handler targets handlerStartIdx
        //    (the move-exception we just appended).
        String newType = plan.tryCatchSpec().catchAny() ? null : plan.tryCatchSpec().catchType();
        List<RegisterShifter.TryBlockSpec> specs = new ArrayList<>();
        boolean coveredByUserBlock = false;
        for (TryRangeSnapshot o : originals) {
            boolean covers = o.startIdx <= matchedIdx && matchedIdx < o.endIdx;
            if (!covers) {
                specs.add(new RegisterShifter.TryBlockSpec(o.startIdx, o.endIdx,
                        List.of(new RegisterShifter.HandlerSpec(o.type, o.handlerIdx))));
                continue;
            }
            coveredByUserBlock = true;
            // head [start, matched) — original handler only (skip empty head).
            if (o.startIdx < matchedIdx) {
                specs.add(new RegisterShifter.TryBlockSpec(o.startIdx, matchedIdx,
                        List.of(new RegisterShifter.HandlerSpec(o.type, o.handlerIdx))));
            }
            // matched [matched, matched+1) — NEW handler FIRST, then original.
            specs.add(new RegisterShifter.TryBlockSpec(matchedIdx, matchedIdx + 1, List.of(
                    new RegisterShifter.HandlerSpec(newType, handlerStartIdx),
                    new RegisterShifter.HandlerSpec(o.type, o.handlerIdx))));
            // tail [matched+1, end) — original handler only (skip empty tail).
            if (matchedIdx + 1 < o.endIdx) {
                specs.add(new RegisterShifter.TryBlockSpec(matchedIdx + 1, o.endIdx,
                        List.of(new RegisterShifter.HandlerSpec(o.type, o.handlerIdx))));
            }
        }
        // Non-nested baseline: matched invoke not inside any user try-block.
        if (!coveredByUserBlock) {
            specs.add(new RegisterShifter.TryBlockSpec(matchedIdx, matchedIdx + 1,
                    List.of(new RegisterShifter.HandlerSpec(newType, handlerStartIdx))));
        }
        // Stable order by start offset for serialisation.
        specs.sort((a, b) -> Integer.compare(a.startIdx(), b.startIdx()));

        // 4. Rebuild the MMI with the split table (getTryBlocks() is read-only).
        return RegisterShifter.rebuildWithTryBlocks(impl, specs);
    }

    /** Captured coordinates of one pre-existing user try-block + its handler. */
    private record TryRangeSnapshot(int startIdx, int endIdx, String type, int handlerIdx) {}

    /**
     * Rewrite the operand at {@code throwingSlot} of an invoke instruction to
     * {@code exceptionRegister}. The {@code throwing(<name>)} binding maps to a
     * placeholder register at emit time (the emitter cannot know the caught-
     * exception register); this swaps it for the real one. Returns the
     * instruction unchanged when {@code throwingSlot < 0} (no exception
     * argument) or the instruction is not the monitor invoke.
     */
    private static BuilderInstruction rewriteThrowingOperand(
            BuilderInstruction insn, int throwingSlot, int exceptionRegister) {
        if (throwingSlot < 0) return insn;
        Opcode op = insn.getOpcode();
        if (op == Opcode.INVOKE_STATIC && insn instanceof FiveRegisterInstruction) {
            FiveRegisterInstruction f = (FiveRegisterInstruction) insn;
            int[] regs = {f.getRegisterC(), f.getRegisterD(), f.getRegisterE(),
                    f.getRegisterF(), f.getRegisterG()};
            if (throwingSlot >= f.getRegisterCount()) return insn;
            regs[throwingSlot] = exceptionRegister;
            return new BuilderInstruction35c(Opcode.INVOKE_STATIC, f.getRegisterCount(),
                    regs[0], regs[1], regs[2], regs[3], regs[4],
                    (MethodReference) ((com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction) insn).getReference());
        }
        if (op == Opcode.INVOKE_STATIC_RANGE && insn instanceof RegisterRangeInstruction) {
            // Range form requires the operands to be contiguous; the executor
            // only allocates the exception register adjacent to the invoke when
            // the operand window already permits it. A range invoke cannot have
            // a single non-contiguous slot rewritten, so this is left to the
            // 35c path (the corpus's sole site stays within 5 narrow operands).
            throw new IllegalStateException(
                    "after-throwing exception operand rewrite unsupported for "
                            + "invoke-static/range; allocator must keep the operand "
                            + "window in 35c form for the throwing binding");
        }
        return insn;
    }

    /**
     * Rewrite the invoke instruction at {@code index} to call {@code newRef}
     * with the same register operands. dexlib2 has no direct
     * "swap-the-reference" API, so we reconstruct the instruction with the
     * same opcode + same registers + new reference. The arity of {@code newRef}
     * MUST match the original invoke's register count (the DexWeaver
     * guarantees this when it sources {@code newRef} from
     * {@code WrapperEmitter.WrapperEntry}, which preserves the original
     * parameter list and adds no implicit receiver — wrappers are static).
     *
     * <p>Supports {@code invoke-static} (Format35c) and
     * {@code invoke-static/range} (Format3rc); other invoke kinds are
     * currently rejected because the wrapper system only generates
     * static-method substitutions.
     */
    public void replaceInvoke(int index, MethodReference newRef) {
        BuilderInstruction current = impl.getInstructions().get(index);
        Opcode op = current.getOpcode();
        BuilderInstruction rewritten;
        switch (op) {
            case INVOKE_STATIC:
            case INVOKE_VIRTUAL:
            case INVOKE_DIRECT:
            case INVOKE_SUPER:
            case INVOKE_INTERFACE:
            {
                FiveRegisterInstruction f = (FiveRegisterInstruction) current;
                rewritten = new BuilderInstruction35c(
                        Opcode.INVOKE_STATIC,
                        f.getRegisterCount(),
                        f.getRegisterC(), f.getRegisterD(), f.getRegisterE(),
                        f.getRegisterF(), f.getRegisterG(),
                        newRef);
                break;
            }
            case INVOKE_STATIC_RANGE:
            case INVOKE_VIRTUAL_RANGE:
            case INVOKE_DIRECT_RANGE:
            case INVOKE_SUPER_RANGE:
            case INVOKE_INTERFACE_RANGE:
            {
                RegisterRangeInstruction r = (RegisterRangeInstruction) current;
                rewritten = new BuilderInstruction3rc(
                        Opcode.INVOKE_STATIC_RANGE,
                        r.getStartRegister(),
                        r.getRegisterCount(),
                        newRef);
                break;
            }
            default:
                throw new IllegalStateException(
                        "replaceInvoke called on non-invoke opcode: " + op);
        }
        impl.replaceInstruction(index, rewritten);
    }

    private void insertAll(int at, List<BuilderInstruction> instructions) {
        int i = at;
        for (BuilderInstruction ins : instructions) {
            impl.addInstruction(i, ins);
            i++;
        }
    }
}
