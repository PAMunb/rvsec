package br.unb.cic.rv.mutator;

import com.android.tools.smali.dexlib2.Format;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11n;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction12x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21ih;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21lh;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21s;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22b;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22s;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction23x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction31c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction31i;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction31t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction32x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction51l;

import java.util.Collections;
import java.util.List;
import java.lang.reflect.Field;

/**
 * Register-level instruction rewriter used by {@link CoverageWeaver}'s spill path.
 *
 * <p>Given a {@link MutableMethodImplementation} whose {@code registerCount} must grow by
 * {@code delta}, this helper rewrites every instruction so that each register reference
 * {@code r &ge; threshold} becomes {@code r + delta}. Semantics-preserving: the added slots are
 * carved out of the low-end of the frame and existing high-end slots (parameters) slide up the
 * same amount the caller configures as {@code delta}.
 *
 * <h3>Why reflection on {@code registerCount}</h3>
 * {@link MutableMethodImplementation#registerCount} is declared {@code private final}. Dexlib2
 * does not expose a setter. Creating a parallel MMI and re-homing every label + try block is
 * possible but tripled the code volume — reflection on a non-static final instance field is still
 * reliably honored on the JDK versions we target (&ge; 11). If a future JDK closes that loophole
 * we can fall back to the MMI-clone path.
 *
 * <h3>Format coverage</h3>
 * All DEX formats that carry register operands are handled. Quickened formats (22cs, 35mi/ms,
 * 3rmi/ms) and Android-O polymorphic invokes (45cc, 4rcc) are skipped — they never appear in
 * non-optimized APKs (odex-only) or are exceptional enough that spill of the surrounding method
 * can be aborted by the caller.
 */
final class RegisterShifter {

    private RegisterShifter() {}

    /** Bump {@code mmi.registerCount} by {@code delta} via reflection on the final field. */
    static void bumpRegisterCount(MutableMethodImplementation mmi, int delta) {
        try {
            Field f = MutableMethodImplementation.class.getDeclaredField("registerCount");
            f.setAccessible(true);
            int newCount = mmi.getRegisterCount() + delta;
            f.setInt(mmi, newCount);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(
                    "failed to bump registerCount via reflection; JDK likely closed final-field "
                    + "mutation. Fallback: rebuild MMI.", e);
        }
    }

    /**
     * Clone {@code in} with all register references ({@code r &ge; threshold}) incremented by
     * {@code delta}. Returns {@code null} when the instruction has no register operands, in which
     * case the caller should leave it in place. Throws {@link UnsupportedOperationException} for
     * formats we intentionally don't rewrite.
     *
     * @throws IllegalStateException if a shifted register overflows its format's field width.
     */
    static BuilderInstruction shift(BuilderInstruction in, int threshold, int delta) {
        Format fmt = in.getOpcode().format;
        Opcode op = in.getOpcode();
        switch (fmt) {
            // No register operands.
            case Format10x:
            case Format10t:
            case Format20t:
            case Format30t:
                return null;

            // Pseudo-instructions (data tables emitted by the compiler for switch / fill-array).
            // They carry labels and raw data, never register indices — safe to skip untouched.
            case PackedSwitchPayload:
            case SparseSwitchPayload:
            case ArrayPayload:
                return null;

            case Format11x: {
                BuilderInstruction11x i = (BuilderInstruction11x) in;
                return new BuilderInstruction11x(op,
                        shift8(i.getRegisterA(), threshold, delta));
            }
            case Format11n: {
                BuilderInstruction11n i = (BuilderInstruction11n) in;
                return new BuilderInstruction11n(op,
                        shift4(i.getRegisterA(), threshold, delta),
                        i.getNarrowLiteral());
            }
            case Format12x: {
                BuilderInstruction12x i = (BuilderInstruction12x) in;
                return new BuilderInstruction12x(op,
                        shift4(i.getRegisterA(), threshold, delta),
                        shift4(i.getRegisterB(), threshold, delta));
            }

            case Format21c: {
                BuilderInstruction21c i = (BuilderInstruction21c) in;
                return new BuilderInstruction21c(op,
                        shift8(i.getRegisterA(), threshold, delta),
                        i.getReference());
            }
            case Format21ih: {
                BuilderInstruction21ih i = (BuilderInstruction21ih) in;
                return new BuilderInstruction21ih(op,
                        shift8(i.getRegisterA(), threshold, delta),
                        i.getNarrowLiteral());
            }
            case Format21lh: {
                BuilderInstruction21lh i = (BuilderInstruction21lh) in;
                return new BuilderInstruction21lh(op,
                        shift8(i.getRegisterA(), threshold, delta),
                        i.getWideLiteral());
            }
            case Format21s: {
                BuilderInstruction21s i = (BuilderInstruction21s) in;
                return new BuilderInstruction21s(op,
                        shift8(i.getRegisterA(), threshold, delta),
                        i.getNarrowLiteral());
            }
            case Format21t: {
                BuilderInstruction21t i = (BuilderInstruction21t) in;
                return new BuilderInstruction21t(op,
                        shift8(i.getRegisterA(), threshold, delta),
                        i.getTarget());
            }

            case Format22b: {
                BuilderInstruction22b i = (BuilderInstruction22b) in;
                return new BuilderInstruction22b(op,
                        shift8(i.getRegisterA(), threshold, delta),
                        shift8(i.getRegisterB(), threshold, delta),
                        i.getNarrowLiteral());
            }
            case Format22c: {
                BuilderInstruction22c i = (BuilderInstruction22c) in;
                return new BuilderInstruction22c(op,
                        shift4(i.getRegisterA(), threshold, delta),
                        shift4(i.getRegisterB(), threshold, delta),
                        i.getReference());
            }
            case Format22s: {
                BuilderInstruction22s i = (BuilderInstruction22s) in;
                return new BuilderInstruction22s(op,
                        shift4(i.getRegisterA(), threshold, delta),
                        shift4(i.getRegisterB(), threshold, delta),
                        i.getNarrowLiteral());
            }
            case Format22t: {
                BuilderInstruction22t i = (BuilderInstruction22t) in;
                return new BuilderInstruction22t(op,
                        shift4(i.getRegisterA(), threshold, delta),
                        shift4(i.getRegisterB(), threshold, delta),
                        i.getTarget());
            }
            case Format22x: {
                BuilderInstruction22x i = (BuilderInstruction22x) in;
                return new BuilderInstruction22x(op,
                        shift8(i.getRegisterA(), threshold, delta),
                        shift16(i.getRegisterB(), threshold, delta));
            }

            case Format23x: {
                BuilderInstruction23x i = (BuilderInstruction23x) in;
                return new BuilderInstruction23x(op,
                        shift8(i.getRegisterA(), threshold, delta),
                        shift8(i.getRegisterB(), threshold, delta),
                        shift8(i.getRegisterC(), threshold, delta));
            }

            case Format31c: {
                BuilderInstruction31c i = (BuilderInstruction31c) in;
                return new BuilderInstruction31c(op,
                        shift8(i.getRegisterA(), threshold, delta),
                        i.getReference());
            }
            case Format31i: {
                BuilderInstruction31i i = (BuilderInstruction31i) in;
                return new BuilderInstruction31i(op,
                        shift8(i.getRegisterA(), threshold, delta),
                        i.getNarrowLiteral());
            }
            case Format31t: {
                BuilderInstruction31t i = (BuilderInstruction31t) in;
                return new BuilderInstruction31t(op,
                        shift8(i.getRegisterA(), threshold, delta),
                        i.getTarget());
            }
            case Format32x: {
                BuilderInstruction32x i = (BuilderInstruction32x) in;
                return new BuilderInstruction32x(op,
                        shift16(i.getRegisterA(), threshold, delta),
                        shift16(i.getRegisterB(), threshold, delta));
            }

            case Format35c: {
                BuilderInstruction35c i = (BuilderInstruction35c) in;
                int n = i.getRegisterCount();
                int[] regs = new int[]{
                        i.getRegisterC(), i.getRegisterD(), i.getRegisterE(),
                        i.getRegisterF(), i.getRegisterG()
                };
                // Only shift the first n slots; keep 0 in unused slots to match dexlib2 convention.
                for (int k = 0; k < n; k++) regs[k] = shift4(regs[k], threshold, delta);
                return new BuilderInstruction35c(op, n,
                        regs[0], regs[1], regs[2], regs[3], regs[4],
                        i.getReference());
            }
            case Format3rc: {
                BuilderInstruction3rc i = (BuilderInstruction3rc) in;
                return new BuilderInstruction3rc(op,
                        shift16(i.getStartRegister(), threshold, delta),
                        i.getRegisterCount(),
                        i.getReference());
            }

            case Format51l: {
                BuilderInstruction51l i = (BuilderInstruction51l) in;
                return new BuilderInstruction51l(op,
                        shift8(i.getRegisterA(), threshold, delta),
                        i.getWideLiteral());
            }

            // Formats we don't (yet) support. Caller should treat as a spill veto.
            case Format45cc:      // invoke-polymorphic (Android O+)
            case Format4rcc:      // invoke-polymorphic/range
            case Format22cs:      // iget-quick (odex)
            case Format35mi:      // execute-inline (odex)
            case Format35ms:      // invoke-virtual-quick (odex)
            case Format3rmi:
            case Format3rms:
            case Format20bc:      // throw-verification-error — has no register ops anyway
                throw new UnsupportedOperationException(
                        "register shift not supported for format " + fmt + " (opcode " + op + ")");
            default:
                throw new UnsupportedOperationException(
                        "unknown format " + fmt + " (opcode " + op + ")");
        }
    }

    private static int shift4(int r, int threshold, int delta) {
        int shifted = r >= threshold ? r + delta : r;
        if (shifted > 0xF) {
            throw new RegisterOverflow4Bit(r, shifted);
        }
        return shifted;
    }

    /** Thrown when a 4-bit register shift would overflow. Carries the raw values for recovery. */
    static final class RegisterOverflow4Bit extends RuntimeException {
        RegisterOverflow4Bit(int oldReg, int shiftedReg) {
            super("4-bit overflow " + oldReg + " -> " + shiftedReg);
        }
    }

    private static int shift8(int r, int threshold, int delta) {
        int shifted = r >= threshold ? r + delta : r;
        if (shifted > 0xFF) {
            throw new IllegalStateException(
                    "8-bit register overflow after shift: " + r + " -> " + shifted);
        }
        return shifted;
    }

    private static int shift16(int r, int threshold, int delta) {
        int shifted = r >= threshold ? r + delta : r;
        if (shifted > 0xFFFF) {
            throw new IllegalStateException(
                    "16-bit register overflow after shift: " + r + " -> " + shifted);
        }
        return shifted;
    }

    /**
     * Shift the registers of {@code in} by {@code delta} (for refs {@code &ge; threshold}), with
     * automatic format conversion when a 4-bit slot would overflow. Returns a list of 1..2
     * instructions that semantically replaces the original. {@code scratchReg} (typically
     * {@code v0} after spill — guaranteed dead in shifted code when {@code threshold == 0} and
     * {@code delta == 1}) is used as a spill slot to bridge overflowed operands.
     *
     * <p>Currently handles:
     * <ul>
     *   <li>{@code move}, {@code move-wide}, {@code move-object} (12x) &rarr; {@code /from16}
     *       variant (22x) when either operand overflows.</li>
     *   <li>{@code iget*}, {@code iput*}, {@code instance-of}, {@code new-array} (22c) &rarr;
     *       prefix or suffix {@code move-*-from16} via {@code scratchReg} when exactly ONE of
     *       the two registers overflows.</li>
     * </ul>
     *
     * <p>Throws {@link RegisterOverflow4Bit} if the expansion isn't supported for the offending
     * format (non-move 12x ops, 22c with BOTH regs overflowing, 35c invokes with non-contiguous
     * high registers, etc.). Caller handles via skip.
     */
    static List<BuilderInstruction> shiftExpanding(BuilderInstruction in, int threshold, int delta,
                                                   int scratchReg) {
        try {
            BuilderInstruction shifted = shift(in, threshold, delta);
            return shifted == null ? Collections.singletonList(in) : Collections.singletonList(shifted);
        } catch (RegisterOverflow4Bit overflow) {
            List<BuilderInstruction> expanded = expandOverflow(in, threshold, delta, scratchReg);
            if (expanded != null) return expanded;
            throw overflow;
        }
    }

    private static List<BuilderInstruction> expandOverflow(BuilderInstruction in, int threshold,
                                                           int delta, int scratchReg) {
        Format fmt = in.getOpcode().format;
        Opcode op = in.getOpcode();

        // 12x move* → 22x move-*-from16
        if (fmt == Format.Format12x) {
            BuilderInstruction12x i = (BuilderInstruction12x) in;
            int a = rawShift(i.getRegisterA(), threshold, delta);
            int b = rawShift(i.getRegisterB(), threshold, delta);
            Opcode wider = widenMove12xTo22x(op);
            if (wider == null) return null;          // non-move 12x (neg/not/int-to-*, array-length)
            if (a > 0xFF || b > 0xFFFF) return null; // 22x has 8-bit dest + 16-bit src
            return Collections.singletonList(new BuilderInstruction22x(wider, a, b));
        }

        // 22c iget*/iput*/instance-of/new-array with exactly one overflowed operand
        if (fmt == Format.Format22c) {
            BuilderInstruction22c i = (BuilderInstruction22c) in;
            int a = rawShift(i.getRegisterA(), threshold, delta);
            int b = rawShift(i.getRegisterB(), threshold, delta);
            boolean aOver = a > 0xF;
            boolean bOver = b > 0xF;
            if (aOver && bOver) return null;
            if (a > 0xFF || b > 0xFFFF) return null; // scratch uses 22x (8-bit dest, 16-bit src)
            return expand22cViaScratch(op, a, b, aOver, i.getReference(), scratchReg);
        }

        return null;
    }

    private static List<BuilderInstruction> expand22cViaScratch(
            Opcode op, int a, int b, boolean aOver,
            com.android.tools.smali.dexlib2.iface.reference.Reference ref, int scratch) {
        boolean aIsWrite = isDestWrite22c(op);
        boolean aIsWide  = (op == Opcode.IGET_WIDE || op == Opcode.IPUT_WIDE);
        Opcode moveForA = aIsWide ? Opcode.MOVE_WIDE_FROM16
                : (isObjectSlot22cA(op) ? Opcode.MOVE_OBJECT_FROM16 : Opcode.MOVE_FROM16);

        if (aOver) {
            int highA = a;
            if (aIsWrite) {
                // iget / instance-of / new-array — vA is destination. Write into scratch,
                // then move scratch → highA.
                BuilderInstruction22c core = new BuilderInstruction22c(op, scratch, b, ref);
                BuilderInstruction22x back = new BuilderInstruction22x(moveForA, highA, scratch);
                return java.util.Arrays.asList(core, back);
            } else {
                // iput — vA is READ. Move highA → scratch, then iput with scratch.
                BuilderInstruction22x prep = new BuilderInstruction22x(moveForA, scratch, highA);
                BuilderInstruction22c core = new BuilderInstruction22c(op, scratch, b, ref);
                return java.util.Arrays.asList(prep, core);
            }
        } else {
            // vB overflowed. vB is always a READ (receiver / size / src for instance-of).
            Opcode moveForB = isObjectSlot22cB(op) ? Opcode.MOVE_OBJECT_FROM16 : Opcode.MOVE_FROM16;
            int highB = b;
            BuilderInstruction22x prep = new BuilderInstruction22x(moveForB, scratch, highB);
            BuilderInstruction22c core = new BuilderInstruction22c(op, a, scratch, ref);
            return java.util.Arrays.asList(prep, core);
        }
    }

    private static int rawShift(int r, int threshold, int delta) {
        return r >= threshold ? r + delta : r;
    }

    private static Opcode widenMove12xTo22x(Opcode op) {
        switch (op) {
            case MOVE:         return Opcode.MOVE_FROM16;
            case MOVE_WIDE:    return Opcode.MOVE_WIDE_FROM16;
            case MOVE_OBJECT:  return Opcode.MOVE_OBJECT_FROM16;
            default:           return null;
        }
    }

    private static boolean isDestWrite22c(Opcode op) {
        switch (op) {
            case IGET: case IGET_WIDE: case IGET_OBJECT:
            case IGET_BOOLEAN: case IGET_BYTE: case IGET_CHAR: case IGET_SHORT:
            case INSTANCE_OF:
            case NEW_ARRAY:
                return true;
            default:
                return false; // iput* — vA is READ
        }
    }

    /** Type of vA (destination for iget*; value for iput*): object vs. int-domain. */
    private static boolean isObjectSlot22cA(Opcode op) {
        return op == Opcode.IGET_OBJECT || op == Opcode.IPUT_OBJECT || op == Opcode.NEW_ARRAY;
    }

    /** Type of vB (receiver for iget/iput; src for instance-of; size for new-array). */
    private static boolean isObjectSlot22cB(Opcode op) {
        switch (op) {
            case IGET: case IGET_WIDE: case IGET_OBJECT:
            case IGET_BOOLEAN: case IGET_BYTE: case IGET_CHAR: case IGET_SHORT:
            case IPUT: case IPUT_WIDE: case IPUT_OBJECT:
            case IPUT_BOOLEAN: case IPUT_BYTE: case IPUT_CHAR: case IPUT_SHORT:
            case INSTANCE_OF:
                return true;
            case NEW_ARRAY:
                return false; // vB is size (int)
            default:
                return false;
        }
    }
}
