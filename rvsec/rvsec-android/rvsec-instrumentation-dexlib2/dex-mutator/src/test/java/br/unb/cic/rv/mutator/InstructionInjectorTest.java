package br.unb.cic.rv.mutator;

import br.unb.cic.rv.emitter.EmitPlan;
import br.unb.cic.rv.emitter.InsertionPoint;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10x;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class InstructionInjectorTest {

    @Test
    void insertBeforeRejectsAfterPlan() {
        MutableMethodImplementation impl = new MutableMethodImplementation(1);
        impl.addInstruction(new BuilderInstruction10x(Opcode.RETURN_VOID));
        InstructionInjector inj = new InstructionInjector(impl);
        EmitPlan plan = EmitPlan.of(
                List.of(new BuilderInstruction10x(Opcode.NOP)),
                InsertionPoint.AFTER);
        assertThrows(IllegalArgumentException.class, () -> inj.insertBefore(0, plan));
    }

    @Test
    void insertAfterRejectsBeforePlan() {
        MutableMethodImplementation impl = new MutableMethodImplementation(1);
        impl.addInstruction(new BuilderInstruction10x(Opcode.RETURN_VOID));
        InstructionInjector inj = new InstructionInjector(impl);
        EmitPlan plan = EmitPlan.of(
                List.of(new BuilderInstruction10x(Opcode.NOP)),
                InsertionPoint.BEFORE);
        assertThrows(IllegalArgumentException.class, () -> inj.insertAfter(0, plan));
    }

    @Test
    void insertBeforeAppendsInstructions() {
        MutableMethodImplementation impl = new MutableMethodImplementation(1);
        impl.addInstruction(new BuilderInstruction10x(Opcode.RETURN_VOID));
        InstructionInjector inj = new InstructionInjector(impl);
        EmitPlan plan = EmitPlan.of(
                List.of(new BuilderInstruction10x(Opcode.NOP),
                        new BuilderInstruction10x(Opcode.NOP)),
                InsertionPoint.BEFORE);
        inj.insertBefore(0, plan);
        long count = 0;
        for (BuilderInstruction ignored : impl.getInstructions()) count++;
        assertTrue(count >= 3, "expected 2 NOPs + 1 return-void, got " + count);
    }

    @Test
    void replaceInvokeIsNotYetWired() {
        MutableMethodImplementation impl = new MutableMethodImplementation(1);
        InstructionInjector inj = new InstructionInjector(impl);
        assertThrows(UnsupportedOperationException.class,
                () -> inj.replaceInvoke(0, null));
    }
}
