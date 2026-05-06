package br.unb.cic.rv.emitter;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * INV-INS-69: validates the format-selection logic in
 * {@link MonitorInvokeBuilder#buildInvokeStatic(MethodReference, int[])}.
 *
 * <p>The 5-arg-with-high-reg case (covered by
 * {@link #contiguousHighRegistersUseFormat3rc} and the cli-level smoke on
 * {@code com.alovoa.expo_48.apk}) was the canonical reproducer that drove
 * the original Format3rc escalation fix.
 */
class MonitorInvokeBuilderHighRegisterTest {

    private static MethodReference syntheticRef(int paramCount) {
        String[] params = new String[paramCount];
        Arrays.fill(params, "Ljava/lang/Object;");
        return new ImmutableMethodReference(
                "Lmop/Foo;", "bar", Arrays.asList(params), "V");
    }

    @Test
    void lowRegistersUseFormat35c() {
        MethodReference ref = syntheticRef(3);
        BuilderInstruction insn = MonitorInvokeBuilder.buildInvokeStatic(ref, new int[]{0, 1, 2});

        assertInstanceOf(BuilderInstruction35c.class, insn);
        BuilderInstruction35c i = (BuilderInstruction35c) insn;
        assertEquals(Opcode.INVOKE_STATIC, i.getOpcode());
        assertEquals(3, i.getRegisterCount());
        assertEquals(0, i.getRegisterC());
        assertEquals(1, i.getRegisterD());
        assertEquals(2, i.getRegisterE());
    }

    @Test
    void fiveRegsAllLowUseFormat35c() {
        MethodReference ref = syntheticRef(5);
        BuilderInstruction insn = MonitorInvokeBuilder.buildInvokeStatic(
                ref, new int[]{5, 6, 7, 8, 9});

        assertInstanceOf(BuilderInstruction35c.class, insn);
        BuilderInstruction35c i = (BuilderInstruction35c) insn;
        assertEquals(Opcode.INVOKE_STATIC, i.getOpcode());
        assertEquals(5, i.getRegisterCount());
        assertEquals(5, i.getRegisterC());
        assertEquals(6, i.getRegisterD());
        assertEquals(7, i.getRegisterE());
        assertEquals(8, i.getRegisterF());
        assertEquals(9, i.getRegisterG());
    }

    @Test
    void contiguousHighRegistersUseFormat3rc() {
        MethodReference ref = syntheticRef(3);
        BuilderInstruction insn = MonitorInvokeBuilder.buildInvokeStatic(
                ref, new int[]{17, 18, 19});

        assertInstanceOf(BuilderInstruction3rc.class, insn);
        BuilderInstruction3rc i = (BuilderInstruction3rc) insn;
        assertEquals(Opcode.INVOKE_STATIC_RANGE, i.getOpcode());
        assertEquals(17, i.getStartRegister());
        assertEquals(3, i.getRegisterCount());
    }

    @Test
    void oneRegOverFifteenWithContiguousLowEscalates() {
        MethodReference ref = syntheticRef(4);
        BuilderInstruction insn = MonitorInvokeBuilder.buildInvokeStatic(
                ref, new int[]{14, 15, 16, 17});

        assertInstanceOf(BuilderInstruction3rc.class, insn);
        BuilderInstruction3rc i = (BuilderInstruction3rc) insn;
        assertEquals(Opcode.INVOKE_STATIC_RANGE, i.getOpcode());
        assertEquals(14, i.getStartRegister());
        assertEquals(4, i.getRegisterCount());
    }

    @Test
    void nonContiguousHighRegistersThrow() {
        MethodReference ref = syntheticRef(3);
        int[] regs = new int[]{17, 19, 20};

        MonitorInvokeBuilder.HighRegisterNonContiguous ex = assertThrows(
                MonitorInvokeBuilder.HighRegisterNonContiguous.class,
                () -> MonitorInvokeBuilder.buildInvokeStatic(ref, regs));
        assertArrayEquals(regs, ex.regs);
    }

    @Test
    void emptyRegistersUseFormat3rc() {
        // Per spec note: the "empty" path goes through Format35c per the
        // current code's `regs.length <= 5 && !anyHighReg` branch — i.e.
        // a zero-arg invoke is encoded as 35c with registerCount=0.
        MethodReference ref = syntheticRef(0);
        BuilderInstruction insn = MonitorInvokeBuilder.buildInvokeStatic(ref, new int[]{});

        assertInstanceOf(BuilderInstruction35c.class, insn);
        BuilderInstruction35c i = (BuilderInstruction35c) insn;
        assertEquals(Opcode.INVOKE_STATIC, i.getOpcode());
        assertEquals(0, i.getRegisterCount());
    }

    @Test
    void singleHighRegisterUsesFormat3rc() {
        MethodReference ref = syntheticRef(1);
        BuilderInstruction insn = MonitorInvokeBuilder.buildInvokeStatic(
                ref, new int[]{20});

        assertInstanceOf(BuilderInstruction3rc.class, insn);
        BuilderInstruction3rc i = (BuilderInstruction3rc) insn;
        assertEquals(Opcode.INVOKE_STATIC_RANGE, i.getOpcode());
        assertEquals(20, i.getStartRegister());
        assertEquals(1, i.getRegisterCount());
    }
}
