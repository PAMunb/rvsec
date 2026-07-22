package br.unb.cic.rv.mutator;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.Label;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderArrayPayload;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11n;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction20t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21ih;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21lh;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21s;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22b;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22cs;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22s;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction30t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction31c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction31t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction32x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction51l;
import com.android.tools.smali.dexlib2.iface.reference.StringReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableStringReference;
import org.junit.jupiter.api.Test;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * Completes the {@link RegisterShifter#shift(BuilderInstruction, int, int)} format
 * table. {@code RegisterShifterFormatsTest} covered the eight formats that dominate
 * real bodies (11x, 12x, 21c, 22c, 23x, 31i, 35c, 3rc); this class exercises the
 * remaining register-bearing formats — 11n, 21ih/21lh/21s/21t, 22b/22s/22t/22x,
 * 31c/31t, 32x, 51l — plus the three families that resolve to a no-op ({@code null})
 * and the two guards that fail loud: the unsupported-format
 * {@link UnsupportedOperationException} and the 8-bit / 16-bit overflow
 * {@link IllegalStateException}s.
 *
 * <p>Every path here is on the spill hot loop ({@code spillLowRegisters} shifts
 * every instruction of a method by {@code +count}). A wrong register-field width
 * class — shifting a 4-bit slot as if it were 8-bit, or vice versa — or a missing
 * overflow guard would emit bytecode ART rejects at load time with a
 * {@code VerifyError}, which no higher-level test in this module would surface.
 * The values chosen ({@code threshold=0}, {@code delta=4}) shift every operand, so
 * each assertion of {@code reg+4} proves the exact field was rewritten; the two
 * overflow tests use {@code delta=1} against a field-maximum register so the guard,
 * not an arithmetic accident, is what throws.
 */
class RegisterShifterShiftFormatsCompletionTest {

    private static final int THRESHOLD = 0;
    private static final int DELTA = 4;

    /** A resolvable branch label from a throwaway MMI — {@code shift()} copies the
     *  target reference verbatim, so it never needs to belong to a real body. */
    private static Label scratchLabel() {
        MutableMethodImplementation mmi = new MutableMethodImplementation(1);
        mmi.addInstruction(new BuilderInstruction10x(Opcode.RETURN_VOID));
        return mmi.newLabelForIndex(0);
    }

    // ------------------------------------------------------------------
    // 4-bit-field formats: register(s) live in nibble slots (shift4).
    // ------------------------------------------------------------------

    @Test
    void format11n_const4_shiftsSingle4BitRegister() {
        BuilderInstruction in = new BuilderInstruction11n(Opcode.CONST_4, 3, 1);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        BuilderInstruction11n i = assertInstanceOf(BuilderInstruction11n.class, out);
        assertEquals(Opcode.CONST_4, i.getOpcode());
        assertEquals(7, i.getRegisterA());
        assertEquals(1, i.getNarrowLiteral(), "the 4-bit literal must be untouched");
    }

    @Test
    void format22s_addIntLit16_shiftsBoth4BitRegisters() {
        BuilderInstruction in = new BuilderInstruction22s(Opcode.ADD_INT_LIT16, 2, 3, 100);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        BuilderInstruction22s i = assertInstanceOf(BuilderInstruction22s.class, out);
        assertEquals(6, i.getRegisterA());
        assertEquals(7, i.getRegisterB());
        assertEquals(100, i.getNarrowLiteral());
    }

    @Test
    void format22t_ifEq_shiftsBoth4BitRegistersKeepingTarget() {
        Label target = scratchLabel();
        BuilderInstruction in = new BuilderInstruction22t(Opcode.IF_EQ, 1, 2, target);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        BuilderInstruction22t i = assertInstanceOf(BuilderInstruction22t.class, out);
        assertEquals(5, i.getRegisterA());
        assertEquals(6, i.getRegisterB());
        assertEquals(target, i.getTarget(), "the branch target must survive the shift verbatim");
    }

    // ------------------------------------------------------------------
    // 8-bit-field formats (shift8).
    // ------------------------------------------------------------------

    @Test
    void format21ih_constHigh16_shifts8BitRegister() {
        // const/high16 stores only the top 16 bits — the low 16 must be zero.
        BuilderInstruction in = new BuilderInstruction21ih(Opcode.CONST_HIGH16, 5, 0x7F000000);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        BuilderInstruction21ih i = assertInstanceOf(BuilderInstruction21ih.class, out);
        assertEquals(9, i.getRegisterA());
        assertEquals(0x7F000000, i.getNarrowLiteral());
    }

    @Test
    void format21lh_constWideHigh16_shifts8BitRegister() {
        // const-wide/high16 stores only the top 16 bits — the low 48 must be zero.
        BuilderInstruction in = new BuilderInstruction21lh(Opcode.CONST_WIDE_HIGH16, 5, 0x7F00000000000000L);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        BuilderInstruction21lh i = assertInstanceOf(BuilderInstruction21lh.class, out);
        assertEquals(9, i.getRegisterA());
        assertEquals(0x7F00000000000000L, i.getWideLiteral());
    }

    @Test
    void format21s_const16_shifts8BitRegister() {
        BuilderInstruction in = new BuilderInstruction21s(Opcode.CONST_16, 6, 1234);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        BuilderInstruction21s i = assertInstanceOf(BuilderInstruction21s.class, out);
        assertEquals(10, i.getRegisterA());
        assertEquals(1234, i.getNarrowLiteral());
    }

    @Test
    void format21t_ifEqz_shifts8BitRegisterKeepingTarget() {
        Label target = scratchLabel();
        BuilderInstruction in = new BuilderInstruction21t(Opcode.IF_EQZ, 6, target);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        BuilderInstruction21t i = assertInstanceOf(BuilderInstruction21t.class, out);
        assertEquals(10, i.getRegisterA());
        assertEquals(target, i.getTarget());
    }

    @Test
    void format22b_addIntLit8_shiftsBoth8BitRegisters() {
        BuilderInstruction in = new BuilderInstruction22b(Opcode.ADD_INT_LIT8, 2, 3, 5);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        BuilderInstruction22b i = assertInstanceOf(BuilderInstruction22b.class, out);
        assertEquals(6, i.getRegisterA());
        assertEquals(7, i.getRegisterB());
        assertEquals(5, i.getNarrowLiteral());
    }

    @Test
    void format22x_moveFrom16_shifts8BitDestAnd16BitSource() {
        // Mixed width: vA is 8-bit (shift8), vB is 16-bit (shift16). This is the
        // shape overflowed 4-bit moves widen into, so its own shift path must
        // apply the two different width classes to the two operands.
        BuilderInstruction in = new BuilderInstruction22x(Opcode.MOVE_FROM16, 10, 300);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        BuilderInstruction22x i = assertInstanceOf(BuilderInstruction22x.class, out);
        assertEquals(14, i.getRegisterA(), "vA is the 8-bit destination");
        assertEquals(304, i.getRegisterB(), "vB is the 16-bit source");
    }

    @Test
    void format31c_constStringJumbo_shifts8BitRegister() {
        StringReference ref = new ImmutableStringReference("jumbo");
        BuilderInstruction in = new BuilderInstruction31c(Opcode.CONST_STRING_JUMBO, 7, ref);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        BuilderInstruction31c i = assertInstanceOf(BuilderInstruction31c.class, out);
        assertEquals(11, i.getRegisterA());
        assertEquals(ref, i.getReference());
    }

    @Test
    void format31t_fillArrayData_shifts8BitRegisterKeepingTarget() {
        Label target = scratchLabel();
        BuilderInstruction in = new BuilderInstruction31t(Opcode.FILL_ARRAY_DATA, 8, target);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        BuilderInstruction31t i = assertInstanceOf(BuilderInstruction31t.class, out);
        assertEquals(12, i.getRegisterA());
        assertEquals(target, i.getTarget());
    }

    @Test
    void format51l_constWide_shifts8BitRegister() {
        BuilderInstruction in = new BuilderInstruction51l(Opcode.CONST_WIDE, 9, 0xCAFEBABEL);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        BuilderInstruction51l i = assertInstanceOf(BuilderInstruction51l.class, out);
        assertEquals(13, i.getRegisterA());
        assertEquals(0xCAFEBABEL, i.getWideLiteral());
    }

    // ------------------------------------------------------------------
    // 16-bit-field format (shift16 on both operands).
    // ------------------------------------------------------------------

    @Test
    void format32x_move16_shiftsBoth16BitRegisters() {
        BuilderInstruction in = new BuilderInstruction32x(Opcode.MOVE_16, 300, 400);
        BuilderInstruction out = RegisterShifter.shift(in, THRESHOLD, DELTA);

        BuilderInstruction32x i = assertInstanceOf(BuilderInstruction32x.class, out);
        assertEquals(304, i.getRegisterA());
        assertEquals(404, i.getRegisterB());
    }

    // ------------------------------------------------------------------
    // No-register formats resolve to null (caller leaves them in place).
    // ------------------------------------------------------------------

    @Test
    void branchOnlyFormatsReturnNull() {
        // 10t/20t/30t carry only a branch offset, no register operand → null.
        assertNull(RegisterShifter.shift(
                new BuilderInstruction10t(Opcode.GOTO, scratchLabel()), THRESHOLD, DELTA));
        assertNull(RegisterShifter.shift(
                new BuilderInstruction20t(Opcode.GOTO_16, scratchLabel()), THRESHOLD, DELTA));
        assertNull(RegisterShifter.shift(
                new BuilderInstruction30t(Opcode.GOTO_32, scratchLabel()), THRESHOLD, DELTA));
    }

    @Test
    void arrayPayloadReturnsNull() {
        // Pseudo-instruction: raw data table, no register indices → null (skipped
        // untouched). Positive control: an 11x with a register still shifts, so
        // the null above is the payload path, not a blanket null.
        BuilderArrayPayload payload = new BuilderArrayPayload(4,
                Collections.singletonList(Number.class.cast(1)));
        assertNull(RegisterShifter.shift(payload, THRESHOLD, DELTA));
        assertEquals(7, ((BuilderInstruction11x) RegisterShifter.shift(
                new BuilderInstruction11x(Opcode.MOVE_RESULT, 3), THRESHOLD, DELTA)).getRegisterA());
    }

    // ------------------------------------------------------------------
    // Fail-loud guards.
    // ------------------------------------------------------------------

    @Test
    void unsupportedQuickenedFormatThrows() {
        // 22cs (iget-quick) is an odex-only quickened format the shifter refuses
        // to rewrite — the caller treats the throw as a spill veto for the method.
        BuilderInstruction in = new BuilderInstruction22cs(Opcode.IGET_QUICK, 1, 2, 0x10);
        UnsupportedOperationException ex = assertThrows(UnsupportedOperationException.class,
                () -> RegisterShifter.shift(in, THRESHOLD, DELTA));
        org.junit.jupiter.api.Assertions.assertTrue(ex.getMessage().contains("Format22cs"),
                "the veto message must name the offending format");
    }

    @Test
    void eightBitRegisterOverflowThrows() {
        // v255 is the 8-bit field ceiling; +1 pushes it to v256 which no 8-bit
        // slot can encode → hard IllegalStateException (the method is unspillable).
        BuilderInstruction in = new BuilderInstruction11x(Opcode.MOVE_RESULT, 0xFF);
        IllegalStateException ex = assertThrows(IllegalStateException.class,
                () -> RegisterShifter.shift(in, THRESHOLD, /*delta=*/ 1));
        org.junit.jupiter.api.Assertions.assertTrue(ex.getMessage().contains("8-bit"),
                "overflow of an 8-bit slot must be reported as such");
    }

    @Test
    void sixteenBitRegisterOverflowThrows() {
        // v65535 is the widest encodable slot (32x); +1 overflows → the method is
        // unspillable and the guard throws rather than emitting a corrupt operand.
        BuilderInstruction in = new BuilderInstruction32x(Opcode.MOVE_16, 0xFFFF, 0);
        IllegalStateException ex = assertThrows(IllegalStateException.class,
                () -> RegisterShifter.shift(in, THRESHOLD, /*delta=*/ 1));
        org.junit.jupiter.api.Assertions.assertTrue(ex.getMessage().contains("16-bit"),
                "overflow of a 16-bit slot must be reported as such");
    }
}
