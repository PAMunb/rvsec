package br.unb.cic.rv.mutator;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.Label;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction12x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction23x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction31i;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction31t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderPackedSwitchPayload;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedMethod;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.reference.FieldReference;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.iface.reference.StringReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableFieldReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableStringReference;
import com.android.tools.smali.dexlib2.writer.pool.DexPool;
import org.junit.jupiter.api.Test;

import java.io.BufferedInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

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

    // ------------------------------------------------------------------
    // gh61 Group D — frame growth via clone (INV-INS-80, INV-INS-87).
    // ------------------------------------------------------------------

    private static final String OWNER = "LFoo;";

    /** Wrap an MMI as the only method of a synthetic class, write to a
     *  temp .dex, parse back, and return the {@link DexBackedDexFile}. */
    private static DexBackedDexFile roundtrip(MutableMethodImplementation impl, Path tmp) throws Exception {
        ImmutableMethod m = new ImmutableMethod(
                OWNER, "spilled",
                Collections.emptyList(),
                "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef cd = new ImmutableClassDef(
                OWNER, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;",
                Collections.emptyList(),
                null, null,
                Collections.emptyList(),
                List.of(m));
        DexFile file = new ImmutableDexFile(Opcodes.getDefault(), List.of(cd));
        DexPool.writeTo(tmp.toString(), file);
        try (InputStream in = new BufferedInputStream(Files.newInputStream(tmp))) {
            return DexBackedDexFile.fromInputStream(Opcodes.getDefault(), in);
        }
    }

    private static DexBackedMethod findMethod(DexBackedDexFile parsed, String name) {
        for (com.android.tools.smali.dexlib2.dexbacked.DexBackedClassDef cd : parsed.getClasses()) {
            if (!OWNER.equals(cd.getType())) continue;
            for (DexBackedMethod m : cd.getMethods()) {
                if (name.equals(m.getName())) return m;
            }
        }
        throw new AssertionError("method " + name + " not found in parsed dex");
    }

    @Test
    void spillGrowsDexRegistersSize() throws Exception {
        // 2-register body: return-void only (no real ops to shift — keeps
        // the test focused on the frame-growth assertion).
        MutableMethodImplementation src = new MutableMethodImplementation(2);
        src.addInstruction(new com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10x(
                Opcode.RETURN_VOID));
        MutableMethodImplementation grown = RegisterShifter.spillLowRegisters(src, 1);
        assertNotSame(src, grown, "spillLowRegisters MUST return a fresh MMI (clone path)");
        assertEquals(3, grown.getRegisterCount(),
                "in-process MMI registerCount must equal oldCount + count");

        Path tmp = Files.createTempFile("gh61-spill-", ".dex");
        try {
            DexBackedDexFile parsed = roundtrip(grown, tmp);
            DexBackedMethod m = findMethod(parsed, "spilled");
            MethodImplementation parsedImpl = m.getImplementation();
            assertNotNull(parsedImpl);
            assertEquals(3, parsedImpl.getRegisterCount(),
                    "INV-INS-80: serialised dex registers_size MUST equal oldCount + count");
        } finally {
            Files.deleteIfExists(tmp);
        }

        // Repeat for the yu5.<init> scenario: registerCount = 34 → 35.
        MutableMethodImplementation src34 = new MutableMethodImplementation(34);
        src34.addInstruction(new com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10x(
                Opcode.RETURN_VOID));
        MutableMethodImplementation grown35 = RegisterShifter.spillLowRegisters(src34, 1);
        Path tmp34 = Files.createTempFile("gh61-spill-34-", ".dex");
        try {
            DexBackedDexFile parsed = roundtrip(grown35, tmp34);
            assertEquals(35, findMethod(parsed, "spilled").getImplementation().getRegisterCount(),
                    "yu5.<init> shape: 34 → 35 must survive serialisation");
        } finally {
            Files.deleteIfExists(tmp34);
        }
    }

    @Test
    void clonePreservesLabelsAndTryBlocks() {
        // Body:
        //   v0: const 0
        //   if-eqz v0, :back   (backward branch — target is index 0)
        //   const 1
        //   goto :forward
        //   packed-switch v0, :sw_payload
        //   const 2
        //   :forward (target of goto)
        //   const 3
        //   :sw_target (case 0 / 1 / 2 of switch)
        //   return-void
        //   :sw_payload (the payload — referenced by packed-switch)
        //   packed-switch-payload {sw_target, sw_target, sw_target}
        //
        // The test isn't trying to be runnable — it's exercising every
        // label-bearing format the rehome path supports.
        MutableMethodImplementation src = new MutableMethodImplementation(2);

        // dexlib2's newLabelForIndex(idx) validates that idx is in-bounds at
        // call time, so we use a two-pass pattern: add all instructions with
        // a backward-pointing placeholder Label (newLabelForIndex(0) — always
        // valid once idx 0 is added), then replace forward-branching insns
        // post-hoc with the correct labels.
        com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10x returnVoid =
                new com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10x(
                        Opcode.RETURN_VOID);

        // idx 0
        src.addInstruction(new BuilderInstruction21c(
                Opcode.CONST_STRING, 0, new ImmutableStringReference("hello")));

        Label placeholder = src.newLabelForIndex(0);

        // idx 1: if-eqz v0, idx 0 (backward, real)
        src.addInstruction(new BuilderInstruction21t(Opcode.IF_EQZ, 0, placeholder));

        // idx 2: const-string
        src.addInstruction(new BuilderInstruction21c(
                Opcode.CONST_STRING, 1, new ImmutableStringReference("two")));

        // idx 3: goto placeholder — will be patched to idx 6.
        src.addInstruction(new BuilderInstruction10t(Opcode.GOTO, placeholder));

        // idx 4: packed-switch placeholder — will be patched to idx 8.
        src.addInstruction(new BuilderInstruction31t(
                Opcode.PACKED_SWITCH, 0, placeholder));

        // idx 5: const-string
        src.addInstruction(new BuilderInstruction21c(
                Opcode.CONST_STRING, 1, new ImmutableStringReference("five")));

        // idx 6: const-string (forward goto target)
        src.addInstruction(new BuilderInstruction21c(
                Opcode.CONST_STRING, 1, new ImmutableStringReference("six")));

        // idx 7: return-void (try handler target, switch case target)
        src.addInstruction(returnVoid);

        // idx 8: packed-switch payload — three cases all pointing to idx 7.
        src.addInstruction(new BuilderPackedSwitchPayload(0,
                Arrays.asList(placeholder, placeholder, placeholder)));

        // Second pass: replace branches with correct forward targets.
        Label idx6 = src.newLabelForIndex(6);
        Label idx7 = src.newLabelForIndex(7);
        Label idx8 = src.newLabelForIndex(8);
        src.replaceInstruction(3, new BuilderInstruction10t(Opcode.GOTO, idx6));
        src.replaceInstruction(4, new BuilderInstruction31t(
                Opcode.PACKED_SWITCH, 0, idx8));
        src.replaceInstruction(8, new BuilderPackedSwitchPayload(0,
                Arrays.asList(idx7, idx7, idx7)));

        // Try block: protect idx 1..idx 5 with handler at idx 7.
        Label tryStart = src.newLabelForIndex(1);
        Label tryEnd = src.newLabelForIndex(5);
        Label tryHandler = src.newLabelForIndex(7);
        src.addCatch("Ljava/lang/RuntimeException;", tryStart, tryEnd, tryHandler);

        // Pre-clone instruction count — dexlib2 may auto-insert a nop for
        // packed-switch payload alignment so we don't assert a fixed value;
        // we only require that the clone preserves whatever the source has.
        int srcSize = src.getInstructions().size();

        MutableMethodImplementation dst = RegisterShifter.bumpRegisterCount(src, 1);
        assertEquals(3, dst.getRegisterCount());
        assertEquals(srcSize, dst.getInstructions().size(),
                "every instruction is copied — none lost in clone");

        // Locate the cloned branch/payload instructions by scanning the dst
        // instruction list (positions can shift if dexlib2 inserted a nop
        // for switch-payload alignment between src and dst).
        BuilderInstruction21t ifEqz = null;
        BuilderInstruction10t goto_ = null;
        BuilderInstruction31t packedSwitch = null;
        BuilderPackedSwitchPayload payload = null;
        int payloadIdx = -1;
        for (int i = 0; i < dst.getInstructions().size(); i++) {
            BuilderInstruction insn = dst.getInstructions().get(i);
            if (insn instanceof BuilderInstruction21t && ifEqz == null) {
                ifEqz = (BuilderInstruction21t) insn;
            } else if (insn instanceof BuilderInstruction10t && goto_ == null) {
                goto_ = (BuilderInstruction10t) insn;
            } else if (insn instanceof BuilderInstruction31t && packedSwitch == null) {
                packedSwitch = (BuilderInstruction31t) insn;
            } else if (insn instanceof BuilderPackedSwitchPayload) {
                payload = (BuilderPackedSwitchPayload) insn;
                payloadIdx = i;
            }
        }
        assertNotNull(ifEqz, "if-eqz cloned");
        assertNotNull(goto_, "goto cloned");
        assertNotNull(packedSwitch, "packed-switch cloned");
        assertNotNull(payload, "packed-switch payload cloned");

        // Branch targets resolve in dst.
        assertEquals(0, ifEqz.getTarget().getLocation().getIndex(),
                "if-eqz back-branch target re-homed to dst idx 0");

        // The goto/return-void/switch-payload all carry through the clone;
        // exact dst indices may include a dexlib2-inserted alignment nop, so
        // verify symbolically by walking from the goto target.
        int gotoTargetIdx = goto_.getTarget().getLocation().getIndex();
        Opcode atGotoTarget = dst.getInstructions().get(gotoTargetIdx).getOpcode();
        assertEquals(Opcode.CONST_STRING, atGotoTarget,
                "goto forward-branch target re-homed to a cloned CONST_STRING (idx 6 in src)");

        int switchPayloadTargetIdx = packedSwitch.getTarget().getLocation().getIndex();
        assertEquals(payloadIdx, switchPayloadTargetIdx,
                "packed-switch payload-reference re-homed to the cloned payload");

        assertEquals(3, payload.getSwitchElements().size());
        // All cases should target the cloned return-void.
        for (com.android.tools.smali.dexlib2.builder.instruction.BuilderSwitchElement el
                : payload.getSwitchElements()) {
            int caseIdx = el.getTarget().getLocation().getIndex();
            assertEquals(Opcode.RETURN_VOID, dst.getInstructions().get(caseIdx).getOpcode(),
                    "switch payload case labels MUST be re-homed onto cloned return-void");
        }

        // Try block re-added on dst.
        assertEquals(1, dst.getTryBlocks().size(),
                "try block MUST be re-added to dst");
        com.android.tools.smali.dexlib2.builder.BuilderTryBlock tb = dst.getTryBlocks().get(0);
        // Verify the start/end/handler labels point at the cloned instructions
        // (opcodes match — dst index may differ from src by dexlib2's
        // alignment-nop insertion).
        assertEquals(Opcode.IF_EQZ,
                dst.getInstructions().get(tb.start.getLocation().getIndex()).getOpcode(),
                "try start label re-homed to the cloned IF_EQZ (src idx 1)");
        assertEquals(1, tb.getExceptionHandlers().size());
        assertEquals(Opcode.RETURN_VOID,
                dst.getInstructions().get(
                        tb.getExceptionHandlers().get(0).getHandler().getLocation().getIndex()
                ).getOpcode(),
                "try handler label re-homed to the cloned RETURN_VOID (src idx 7)");
        assertEquals("Ljava/lang/RuntimeException;",
                tb.getExceptionHandlers().get(0).getExceptionType(),
                "exception type preserved across clone");
    }

    @Test
    void injectionViaDexFileMutatorReplaceImplPersistsRegisters() throws Exception {
        // gh61 task 4.8b — unit-level mirror of the production failure mode.
        // Constructs a real DexFileMutator, requests an MMI for a synthetic
        // method whose body needs spilling (registerCount=1, params=1 → no
        // free locals), runs the spill + replaceImpl + injection by hand
        // (mirroring CoverageWeaver.injectLogCall), serialises via the
        // mutator's toDexFile(), and asserts the parsed registers_size
        // equals oldCount+1 AND an injected invoke-static is present at idx 0.
        ImmutableMethod m = new ImmutableMethod(
                OWNER, "needsSpill",
                Collections.emptyList(),
                "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null,
                new com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation(
                        /*registerCount=*/ 1,
                        Collections.singletonList(
                                new com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x(
                                        Opcode.RETURN_VOID)),
                        Collections.emptyList(),
                        Collections.emptyList()));
        ClassDef cd = new ImmutableClassDef(
                OWNER, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;",
                Collections.emptyList(),
                null, null,
                Collections.emptyList(),
                List.of(m));
        DexFile original = new ImmutableDexFile(Opcodes.getDefault(), List.of(cd));

        DexFileMutator mutator = new DexFileMutator(original);

        // Look up the method via the original dex; the mutator keys by descriptor
        // so the Method instance identity doesn't matter.
        Method srcMethod = original.getClasses().iterator().next().getMethods().iterator().next();
        MutableMethodImplementation impl = mutator.forMethod(srcMethod);
        assertNotNull(impl);
        assertEquals(1, impl.getRegisterCount());

        // Spill + cache-update mirroring CoverageWeaver.injectLogCall.
        impl = RegisterShifter.spillLowRegisters(impl, 1);
        mutator.replaceImpl(srcMethod, impl);

        // Inject the coverage marker: invoke-static v0 → java.lang.System.gc()
        // (any well-formed invoke works for the test; we just need a recognisable
        // instruction at idx 0 of the serialised method body).
        MethodReference gcRef = new ImmutableMethodReference(
                "Ljava/lang/System;", "gc", Collections.emptyList(), "V");
        impl.addInstruction(0, new BuilderInstruction35c(
                Opcode.INVOKE_STATIC, /*regCount=*/ 0,
                0, 0, 0, 0, 0, gcRef));

        // Sanity: the in-process MMI is the post-spill one, contains the
        // injection, and is the same identity the mutator hands back now.
        assertSame(impl, mutator.forMethod(srcMethod),
                "DexFileMutator.replaceImpl must update the per-method cache to the new MMI");

        // Serialise via the mutator (production path) and parse back.
        Path tmp = Files.createTempFile("gh61-injection-", ".dex");
        try {
            DexPool.writeTo(tmp.toString(), mutator.toDexFile());
            try (InputStream in = new BufferedInputStream(Files.newInputStream(tmp))) {
                DexBackedDexFile parsed = DexBackedDexFile.fromInputStream(Opcodes.getDefault(), in);
                DexBackedMethod parsedMethod = findMethod(parsed, "needsSpill");
                MethodImplementation parsedImpl = parsedMethod.getImplementation();
                assertNotNull(parsedImpl);
                assertEquals(2, parsedImpl.getRegisterCount(),
                        "INV-INS-87: production-path serialised registers_size MUST be oldCount+1");
                Opcode firstOp = parsedImpl.getInstructions().iterator().next().getOpcode();
                assertEquals(Opcode.INVOKE_STATIC, firstOp,
                        "injected invoke-static MUST be present on the post-spill MMI "
                                + "(would be absent if cache returned the stale pre-spill MMI)");
            }
        } finally {
            Files.deleteIfExists(tmp);
        }
    }
}
