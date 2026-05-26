package br.unb.cic.rv.mutator;

import com.android.tools.smali.dexlib2.Format;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderExceptionHandler;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.BuilderTryBlock;
import com.android.tools.smali.dexlib2.builder.Label;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.SwitchLabelElement;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderArrayPayload;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11n;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction12x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction20t;
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
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction30t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction31c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction31i;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction31t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction32x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction51l;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderPackedSwitchPayload;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderSparseSwitchPayload;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderSwitchElement;
import com.android.tools.smali.dexlib2.iface.reference.TypeReference;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Register-level instruction rewriter used by {@link CoverageWeaver}'s spill path.
 *
 * <p>Given a {@link MutableMethodImplementation} whose {@code registerCount} must grow by
 * {@code delta}, this helper rewrites every instruction so that each register reference
 * {@code r &ge; threshold} becomes {@code r + delta}. Semantics-preserving: the added slots are
 * carved out of the low-end of the frame and existing high-end slots (parameters) slide up the
 * same amount the caller configures as {@code delta}.
 *
 * <h3>Frame growth via clone</h3>
 * {@link MutableMethodImplementation#registerCount} is declared {@code private final}; dexlib2
 * exposes no setter and the field is invisible to a {@link DexPool} writer when mutated through
 * reflection on the host JDK shipped in our Docker image. {@link #bumpRegisterCount} allocates a
 * fresh {@code MutableMethodImplementation(oldCount + delta)} and copies every instruction,
 * re-homing labels (branch ops, switch payloads) and try blocks onto the destination MMI. The
 * caller MUST replace its reference to the source MMI with the returned MMI, and — when the
 * source MMI was obtained from a {@code MutableImplSupplier} (e.g. {@code DexFileMutator} in
 * production) — MUST notify the supplier via
 * {@code replaceImpl(method, newImpl)} so the per-method cache stops handing out the stale MMI.
 * Postcondition: serialising the containing class via {@code DexPool} and parsing the result with
 * {@code DexBackedDexFile} yields a method whose {@code getImplementation().getRegisterCount()}
 * returns {@code oldCount + delta} (INV-INS-80).
 *
 * <h3>Format coverage</h3>
 * All DEX formats that carry register operands are handled. Quickened formats (22cs, 35mi/ms,
 * 3rmi/ms) and Android-O polymorphic invokes (45cc, 4rcc) are skipped — they never appear in
 * non-optimized APKs (odex-only) or are exceptional enough that spill of the surrounding method
 * can be aborted by the caller.
 */
public final class RegisterShifter {

    // Public so sibling modules (coverage-weaver) can grow a method's
    // registerCount without re-implementing the clone shim. Only
    // bumpRegisterCount is safe to call cross-module; per-instruction
    // shift() remains package-private.
    private RegisterShifter() {}

    /**
     * Return a fresh {@link MutableMethodImplementation} whose register count is
     * {@code src.getRegisterCount() + delta}. Every instruction is copied onto
     * the new MMI; label-bearing instructions (branch ops 10t/20t/21t/22t/30t/31t,
     * and the three switch payloads — {@code PackedSwitchPayload},
     * {@code SparseSwitchPayload}, {@code ArrayPayload}) are rebuilt against
     * destination-owned labels via {@link MutableMethodImplementation#newLabelForIndex(int)}
     * with the source label's instruction index. Try blocks are re-added via
     * {@link MutableMethodImplementation#addCatch(TypeReference, Label, Label, Label)}.
     *
     * <p>Operands MUST already have been shifted by the caller — this method
     * only grows the frame; it does not rewrite register references.
     *
     * <p>Caller obligation: replace its reference to the source MMI with the
     * returned MMI AND, when the source MMI was obtained from a
     * {@code MutableImplSupplier} (canonically {@code DexFileMutator}), invoke
     * {@code supplier.replaceImpl(method, newImpl)} so the per-method cache
     * stops handing out the stale MMI (INV-INS-87).
     */
    public static MutableMethodImplementation bumpRegisterCount(
            MutableMethodImplementation src, int delta) {
        int newCount = src.getRegisterCount() + delta;
        MutableMethodImplementation dst = new MutableMethodImplementation(newCount);

        // dexlib2 validates label targets at construction / replaceInstruction
        // time, so we cannot directly emit a forward-branch label while
        // appending instructions in source order. Three-pass clone:
        //   Pass 1: pre-fill dst with N return-void no-ops, one per source
        //           instruction. This makes every src index in [0, N)
        //           resolvable via dst.newLabelForIndex.
        //   Pass 2: replace all switch-payload positions with rehomed
        //           payloads. Done before pass 3 so that packed-switch and
        //           sparse-switch references resolve to real payloads
        //           (dexlib2 validates that switch references target a
        //           payload instruction).
        //   Pass 3: replace every remaining position (branches, regular
        //           instructions, array payloads) with the rehomed form.
        List<BuilderInstruction> srcInsns = src.getInstructions();
        int n = srcInsns.size();
        for (int i = 0; i < n; i++) {
            dst.addInstruction(new com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10x(
                    Opcode.RETURN_VOID));
        }

        // Pass 2: switch payloads first.
        for (int i = 0; i < n; i++) {
            BuilderInstruction insn = srcInsns.get(i);
            Format fmt = insn.getOpcode().format;
            if (fmt == Format.PackedSwitchPayload) {
                BuilderPackedSwitchPayload p = (BuilderPackedSwitchPayload) insn;
                List<BuilderSwitchElement> elements = p.getSwitchElements();
                int startKey = elements.isEmpty() ? 0 : elements.get(0).getKey();
                List<Label> labels = new ArrayList<>(elements.size());
                for (BuilderSwitchElement el : elements) {
                    labels.add(dst.newLabelForIndex(el.getTarget().getLocation().getIndex()));
                }
                dst.replaceInstruction(i, new BuilderPackedSwitchPayload(startKey, labels));
            } else if (fmt == Format.SparseSwitchPayload) {
                BuilderSparseSwitchPayload p = (BuilderSparseSwitchPayload) insn;
                List<SwitchLabelElement> rehomed = new ArrayList<>();
                for (BuilderSwitchElement el : p.getSwitchElements()) {
                    rehomed.add(new SwitchLabelElement(el.getKey(),
                            dst.newLabelForIndex(el.getTarget().getLocation().getIndex())));
                }
                dst.replaceInstruction(i, new BuilderSparseSwitchPayload(rehomed));
            }
        }

        // Pass 3: branches, array payloads, and regular instructions.
        for (int i = 0; i < n; i++) {
            BuilderInstruction insn = srcInsns.get(i);
            Format fmt = insn.getOpcode().format;
            switch (fmt) {
                case Format10t:
                case Format20t:
                case Format30t:
                case Format21t:
                case Format22t:
                case Format31t: {
                    int targetIdx = ((com.android.tools.smali.dexlib2.builder.BuilderOffsetInstruction) insn)
                            .getTarget().getLocation().getIndex();
                    dst.replaceInstruction(i, rebuildBranchWithLabel(insn,
                            dst.newLabelForIndex(targetIdx)));
                    break;
                }
                case ArrayPayload: {
                    BuilderArrayPayload p = (BuilderArrayPayload) insn;
                    dst.replaceInstruction(i,
                            new BuilderArrayPayload(p.getElementWidth(), p.getArrayElements()));
                    break;
                }
                case PackedSwitchPayload:
                case SparseSwitchPayload:
                    // Handled in pass 2.
                    break;
                default:
                    // Non-label-bearing instruction; reuse the BuilderInstruction
                    // verbatim — dexlib2 owns a fresh MethodLocation on replace.
                    dst.replaceInstruction(i, insn);
                    break;
            }
        }

        // Pass 3: re-add try blocks with handler labels re-homed onto dst.
        for (BuilderTryBlock tb : src.getTryBlocks()) {
            int startIdx = tb.start.getLocation().getIndex();
            int endIdx = tb.end.getLocation().getIndex();
            for (BuilderExceptionHandler eh : tb.getExceptionHandlers()) {
                int handlerIdx = eh.getHandler().getLocation().getIndex();
                Label start = dst.newLabelForIndex(startIdx);
                Label end = dst.newLabelForIndex(endIdx);
                Label handler = dst.newLabelForIndex(handlerIdx);
                String type = eh.getExceptionType();
                if (type != null) {
                    dst.addCatch(type, start, end, handler);
                } else {
                    dst.addCatch(start, end, handler);
                }
            }
        }

        return dst;
    }

    /**
     * Reconstruct a branch / payload-reference instruction with a new target
     * label. Used by the two-pass clone in {@link #bumpRegisterCount} for both
     * the placeholder (self-loop) form and the final-target form.
     */
    private static BuilderInstruction rebuildBranchWithLabel(BuilderInstruction insn, Label target) {
        Opcode op = insn.getOpcode();
        Format fmt = op.format;
        switch (fmt) {
            case Format10t: return new BuilderInstruction10t(op, target);
            case Format20t: return new BuilderInstruction20t(op, target);
            case Format30t: return new BuilderInstruction30t(op, target);
            case Format21t: {
                BuilderInstruction21t i = (BuilderInstruction21t) insn;
                return new BuilderInstruction21t(op, i.getRegisterA(), target);
            }
            case Format22t: {
                BuilderInstruction22t i = (BuilderInstruction22t) insn;
                return new BuilderInstruction22t(op, i.getRegisterA(), i.getRegisterB(), target);
            }
            case Format31t: {
                BuilderInstruction31t i = (BuilderInstruction31t) insn;
                return new BuilderInstruction31t(op, i.getRegisterA(), target);
            }
            default:
                throw new IllegalStateException(
                        "rebuildBranchWithLabel called on non-branch format " + fmt);
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
    public static List<BuilderInstruction> shiftExpanding(BuilderInstruction in, int threshold,
                                                          int delta, int scratchReg) {
        try {
            BuilderInstruction shifted = shift(in, threshold, delta);
            return shifted == null ? Collections.singletonList(in) : Collections.singletonList(shifted);
        } catch (RegisterOverflow4Bit overflow) {
            List<BuilderInstruction> expanded = expandOverflow(in, threshold, delta, scratchReg);
            if (expanded != null) return expanded;
            throw overflow;
        }
    }

    /**
     * Free up {@code count} low-end register slots by shifting every existing register
     * reference up by {@code count} and growing the frame by {@code count}.
     *
     * <p>This is the **canonical way** to add scratch registers to a DEX method without
     * breaking the calling convention. Android DEX places method parameters in the
     * <i>highest</i> {@code paramRegisterCount} registers; growing {@code registerCount}
     * alone moves those slots implicitly while the bytecode still references the old
     * positions, leaving the new param slots uninitialized at method entry — which the
     * runtime verifier rejects with {@code java.lang.VerifyError: tried to get class from
     * non-reference register vN (type=Undefined)}.
     *
     * <p>Strategy:
     * <ol>
     *   <li>Walk every instruction; rewrite each register reference {@code r} →
     *       {@code r + count} via {@link #shiftExpanding} (which converts 4-bit slots to
     *       wider {@code /from16} forms when needed, using {@code scratchReg=0} as a
     *       guaranteed-dead spill slot since every original register is now &ge; count).</li>
     *   <li>Grow {@code registerCount} by {@code count}.</li>
     * </ol>
     * After this returns, registers {@code 0..count-1} are free for the caller to use.
     * Param registers, after the shift, end up at {@code regCount - paramRegs..regCount-1}
     * — exactly where the runtime initializes them after the bump.
     *
     * <p>Throws {@link RegisterOverflow4Bit} if any instruction's format cannot be widened
     * (e.g. non-move 12x ops, 22c with both operands overflowing). Callers should catch
     * and skip the offending method (the rest of the class is unaffected because the
     * caller works on a {@link MutableMethodImplementation}, which is per-method).
     *
     * <p><b>Atomicity (gh61 INV-INS-80):</b> the source MMI is never mutated. Frame
     * growth happens up-front via {@link #bumpRegisterCount}, producing a fresh clone;
     * all subsequent operand shifts and overflow expansions apply to the clone. If any
     * {@link #shiftExpanding} call throws, the clone is unreferenced and discarded by
     * the JVM, and the caller's source MMI — typically still pinned by a
     * {@code MutableImplSupplier} cache (canonically {@code DexFileMutator.mutations})
     * — remains pristine. Without this property, a mid-stream overflow would leave
     * the cache pointing at a half-shifted MMI whose {@code registerCount} no longer
     * matches its operand references, surfacing on-device as {@code VerifyError:
     * tried to get class from non-reference register vN (type=&lt;primitive&gt;)} at
     * every entry to the partially-rewritten method.
     *
     * @see <a href="https://source.android.com/docs/core/runtime/dex-format#instruction-format">
     *      Dalvik instruction format reference</a>
     */
    public static MutableMethodImplementation spillLowRegisters(
            MutableMethodImplementation src, int count) {
        if (count <= 0) return src;
        // Clone first. bumpRegisterCount produces a fresh MMI with
        // registerCount = src.getRegisterCount() + count and every instruction
        // copied (with label / try-block targets re-homed onto dst). The source
        // MMI is never touched from this point on.
        MutableMethodImplementation dst = bumpRegisterCount(src, count);
        // Shift operands in-place on the clone. shiftExpanding may throw
        // RegisterOverflow4Bit if a Format35c (or similar 4-bit-register
        // instruction) has both an operand at v15 and no expansion to a
        // wider /range form available. In that case the clone is abandoned
        // and the exception propagates to the caller (e.g.
        // CoverageWeaver.injectLogCall returns false and the surrounding
        // method is skipped). The source MMI is preserved intact.
        int i = 0;
        while (i < dst.getInstructions().size()) {
            BuilderInstruction insn = dst.getInstructions().get(i);
            List<BuilderInstruction> expanded = shiftExpanding(
                    insn, /*threshold=*/ 0, /*delta=*/ count, /*scratchReg=*/ 0);
            if (expanded.size() == 1 && expanded.get(0) == insn) {
                // No-op (payload or no-register instruction).
                i++;
                continue;
            }
            dst.replaceInstruction(i, expanded.get(0));
            for (int k = 1; k < expanded.size(); k++) {
                dst.addInstruction(i + k, expanded.get(k));
            }
            i += expanded.size();
        }
        return dst;
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
