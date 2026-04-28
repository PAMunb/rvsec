package br.unb.cic.rv.mutator;

import br.unb.cic.rv.emitter.EmitPlan;
import br.unb.cic.rv.emitter.InsertionPoint;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.iface.instruction.FiveRegisterInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.RegisterRangeInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;

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

    private final MutableMethodImplementation impl;

    public InstructionInjector(MutableMethodImplementation impl) {
        this.impl = Objects.requireNonNull(impl);
    }

    public void insertBefore(int index, EmitPlan plan) {
        if (plan.insertionPoint() == InsertionPoint.AFTER) {
            throw new IllegalArgumentException(
                    "plan declared InsertionPoint.AFTER but insertBefore was called");
        }
        insertAll(index, plan.toInsert());
    }

    public void insertAfter(int index, EmitPlan plan) {
        if (plan.insertionPoint() == InsertionPoint.BEFORE) {
            throw new IllegalArgumentException(
                    "plan declared InsertionPoint.BEFORE but insertAfter was called");
        }
        // INV-INS-27: when the matched invoke is followed by `move-result*`,
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
