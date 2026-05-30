package br.unb.cic.rv.mutator;

import br.unb.cic.rv.emitter.EmitPlan;
import br.unb.cic.rv.emitter.InsertionPoint;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.Label;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11x;
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
