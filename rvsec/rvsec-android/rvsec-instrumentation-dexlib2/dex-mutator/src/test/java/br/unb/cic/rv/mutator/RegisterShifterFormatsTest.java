package br.unb.cic.rv.mutator;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction12x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction23x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction31i;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.iface.reference.FieldReference;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.iface.reference.StringReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableFieldReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableStringReference;
import org.junit.jupiter.api.Test;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Table-driven coverage for {@link RegisterShifter#shift(BuilderInstruction, int, int)} across
 * the dominant 8 DEX formats (task 5.7). Each test builds a synthetic input via the dexlib2
 * {@code Builder*} factory, applies {@code shift(threshold=0, delta=4)}, and asserts every
 * register reference is incremented while non-register operands (literals, references) survive
 * unchanged.
 */
class RegisterShifterFormatsTest {

    private static final int THRESHOLD = 0;
    private static final int DELTA = 4;

    @Test
    void format11x_movResult_shifted() {
        BuilderInstruction in = new BuilderInstruction11x(Opcode.MOVE_RESULT, 3);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        assertInstanceOf(BuilderInstruction11x.class, out);
        BuilderInstruction11x i = (BuilderInstruction11x) out;
        assertEquals(Opcode.MOVE_RESULT, i.getOpcode());
        assertEquals(7, i.getRegisterA());
    }

    @Test
    void format12x_move_shifted() {
        BuilderInstruction in = new BuilderInstruction12x(Opcode.MOVE, 0, 1);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        assertInstanceOf(BuilderInstruction12x.class, out);
        BuilderInstruction12x i = (BuilderInstruction12x) out;
        assertEquals(Opcode.MOVE, i.getOpcode());
        assertEquals(4, i.getRegisterA());
        assertEquals(5, i.getRegisterB());
    }

    @Test
    void format21c_constString_shifted() {
        StringReference ref = new ImmutableStringReference("hello");
        BuilderInstruction in = new BuilderInstruction21c(Opcode.CONST_STRING, 2, ref);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        assertInstanceOf(BuilderInstruction21c.class, out);
        BuilderInstruction21c i = (BuilderInstruction21c) out;
        assertEquals(Opcode.CONST_STRING, i.getOpcode());
        assertEquals(6, i.getRegisterA());
        assertSame(ref, i.getReference());
    }

    @Test
    void format22c_iput_shifted() {
        FieldReference ref = new ImmutableFieldReference(
                "Lcom/example/Foo;", "field", "Ljava/lang/Object;");
        BuilderInstruction in = new BuilderInstruction22c(Opcode.IPUT_OBJECT, 3, 4, ref);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        assertInstanceOf(BuilderInstruction22c.class, out);
        BuilderInstruction22c i = (BuilderInstruction22c) out;
        assertEquals(Opcode.IPUT_OBJECT, i.getOpcode());
        assertEquals(7, i.getRegisterA());
        assertEquals(8, i.getRegisterB());
        assertSame(ref, i.getReference());
    }

    @Test
    void format23x_aget_shifted() {
        BuilderInstruction in = new BuilderInstruction23x(Opcode.AGET, 0, 1, 2);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        assertInstanceOf(BuilderInstruction23x.class, out);
        BuilderInstruction23x i = (BuilderInstruction23x) out;
        assertEquals(Opcode.AGET, i.getOpcode());
        assertEquals(4, i.getRegisterA());
        assertEquals(5, i.getRegisterB());
        assertEquals(6, i.getRegisterC());
    }

    @Test
    void format31i_constHigh_shifted() {
        int literal = 0xDEADBEEF;
        BuilderInstruction in = new BuilderInstruction31i(Opcode.CONST, 0, literal);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        assertInstanceOf(BuilderInstruction31i.class, out);
        BuilderInstruction31i i = (BuilderInstruction31i) out;
        assertEquals(Opcode.CONST, i.getOpcode());
        assertEquals(4, i.getRegisterA());
        assertEquals(literal, i.getNarrowLiteral());
    }

    @Test
    void format35c_invokeStatic_shifted() {
        MethodReference ref = new ImmutableMethodReference(
                "Lcom/example/Foo;", "bar",
                Collections.singletonList("Ljava/lang/Object;"), "V");
        // 35c carries up to 5 register slots; only the first n are meaningful, the rest
        // are 0-padded by the format. Here n=2 → vC=0, vD=1, vE..vG unused (0).
        BuilderInstruction in = new BuilderInstruction35c(
                Opcode.INVOKE_STATIC, 2, 0, 1, 0, 0, 0, ref);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        assertInstanceOf(BuilderInstruction35c.class, out);
        BuilderInstruction35c i = (BuilderInstruction35c) out;
        assertEquals(Opcode.INVOKE_STATIC, i.getOpcode());
        assertEquals(2, i.getRegisterCount());
        assertEquals(4, i.getRegisterC());
        assertEquals(5, i.getRegisterD());
        assertSame(ref, i.getReference());
    }

    @Test
    void format3rc_invokeStaticRange_shifted() {
        MethodReference ref = new ImmutableMethodReference(
                "Lcom/example/Foo;", "bar",
                Collections.singletonList("Ljava/lang/Object;"), "V");
        BuilderInstruction in = new BuilderInstruction3rc(
                Opcode.INVOKE_STATIC_RANGE, 10, 4, ref);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        assertInstanceOf(BuilderInstruction3rc.class, out);
        BuilderInstruction3rc i = (BuilderInstruction3rc) out;
        assertEquals(Opcode.INVOKE_STATIC_RANGE, i.getOpcode());
        assertEquals(14, i.getStartRegister());
        assertEquals(4, i.getRegisterCount());
        assertSame(ref, i.getReference());
    }
}
