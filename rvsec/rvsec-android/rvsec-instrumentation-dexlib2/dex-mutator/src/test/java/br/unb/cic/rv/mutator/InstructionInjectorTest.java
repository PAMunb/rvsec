package br.unb.cic.rv.mutator;

import br.unb.cic.rv.emitter.EmitPlan;
import br.unb.cic.rv.emitter.InsertionPoint;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
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
    void replaceInvokeRewritesInvokeStaticToNewReference() {
        // Build a method with a single invoke-static of {v0, v1}, calling
        // OldOwner.foo(I, I)V. Then replaceInvoke swaps in NewOwner.bar so
        // the rewritten instruction has the new method reference but the
        // same register operands.
        MutableMethodImplementation impl = new MutableMethodImplementation(2);
        MethodReference original = new ImmutableMethodReference(
                "Lpkg/OldOwner;", "foo", List.of("I", "I"), "V");
        impl.addInstruction(new BuilderInstruction35c(
                Opcode.INVOKE_STATIC, 2, 0, 1, 0, 0, 0, original));
        InstructionInjector inj = new InstructionInjector(impl);

        MethodReference replacement = new ImmutableMethodReference(
                "Lpkg/NewOwner;", "bar", List.of("I", "I"), "V");
        inj.replaceInvoke(0, replacement);

        BuilderInstruction rewritten = impl.getInstructions().get(0);
        assertInstanceOf(BuilderInstruction35c.class, rewritten);
        assertEquals(Opcode.INVOKE_STATIC, rewritten.getOpcode());
        BuilderInstruction35c r = (BuilderInstruction35c) rewritten;
        assertEquals(2, r.getRegisterCount());
        assertEquals(0, r.getRegisterC());
        assertEquals(1, r.getRegisterD());
        assertEquals("Lpkg/NewOwner;", ((MethodReference) r.getReference()).getDefiningClass());
        assertEquals("bar", ((MethodReference) r.getReference()).getName());
    }
}
