package br.unb.cic.rv.mutator;

import br.unb.cic.rv.emitter.EmitPlan;
import br.unb.cic.rv.emitter.InsertionPoint;
import br.unb.cic.rv.emitter.RegisterRequest;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.builder.BuilderDebugItem;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.BuilderOffsetInstruction;
import com.android.tools.smali.dexlib2.builder.BuilderSwitchPayload;
import com.android.tools.smali.dexlib2.builder.BuilderTryBlock;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.SwitchLabelElement;
import com.android.tools.smali.dexlib2.builder.debug.BuilderLineNumber;
import com.android.tools.smali.dexlib2.builder.debug.BuilderStartLocal;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction31t;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderPackedSwitchPayload;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderSparseSwitchPayload;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedClassDef;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedMethod;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.OffsetInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.writer.pool.DexPool;

import org.junit.jupiter.api.Test;

import java.io.BufferedInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * INV-INS-161: a {@code before} block inserted at a call is executed by every path
 * that reaches the call. Each fixture is a {@link MutableMethodImplementation} built
 * directly, with the hooked call {@code Cipher.init(int, Key)} as the target of an
 * {@code if-*}, a {@code goto}, or a switch case; {@link InstructionInjector#insertBefore}
 * must move that target, and the call's line entry, onto the first inserted
 * instruction, while try-range boundaries and local-variable entries stay on the call.
 */
class InstructionInjectorBranchTargetTest {

    private static final MethodReference CIPHER_INIT = new ImmutableMethodReference(
            "Ljavax/crypto/Cipher;", "init", List.of("I", "Ljava/security/Key;"), "V");
    private static final MethodReference MONITOR_EVENT = new ImmutableMethodReference(
            "Lmop/MultiSpec_1RuntimeMonitor;", "CipherSpec_i1Event",
            List.of("Ljavax/crypto/Cipher;"), "V");

    @Test
    void ifTargetLandsOnTheInsertedBlock() throws Exception {
        //   0: if-eqz v0, :call
        //   1: nop
        //   2: :call invoke-virtual {v2, v0, v1}, Cipher.init(I, Key)V
        //   3: return-void
        MutableMethodImplementation impl = method(4, 2);
        impl.replaceInstruction(0, new BuilderInstruction21t(Opcode.IF_EQZ, 0, impl.newLabelForIndex(2)));
        BuilderInstruction call = impl.getInstructions().get(2);

        new InstructionInjector(impl).insertBefore(2, monitorPlan(null));

        List<BuilderInstruction> ins = impl.getInstructions();
        assertEquals(Opcode.INVOKE_STATIC, ins.get(2).getOpcode(), "the block sits at the call's index");
        assertEquals(3, call.getLocation().getIndex(), "the call follows the block");
        assertEquals(2, targetIndex(ins.get(0)), "if-eqz lands on the first inserted instruction");
        // Fall-through: nop (1) -> block (2) -> call (3), the block exactly once.
        assertEquals(Opcode.NOP, ins.get(1).getOpcode());
        assertEquals(1, countMonitorCalls(ins), "one monitor call on every path");

        // The rewritten method serialises and reloads with the branch still on the block.
        MethodImplementation reloaded = roundTrip(impl);
        List<Instruction> out = new ArrayList<>();
        reloaded.getInstructions().forEach(out::add);
        int ifAddress = addressOf(out, 0);
        int target = ifAddress + ((OffsetInstruction) out.get(0)).getCodeOffset();
        Instruction landed = instructionAt(out, target);
        assertEquals(Opcode.INVOKE_STATIC, landed.getOpcode());
        assertEquals(MONITOR_EVENT, ((ReferenceInstruction) landed).getReference());
    }

    @Test
    void gotoTargetLandsOnTheInsertedBlock() {
        //   0: goto :call
        //   1: return-void
        //   2: :call invoke-virtual Cipher.init
        //   3: return-void
        MutableMethodImplementation impl = method(4, 2);
        impl.replaceInstruction(0, new BuilderInstruction10t(Opcode.GOTO, impl.newLabelForIndex(2)));
        impl.replaceInstruction(1, new BuilderInstruction10x(Opcode.RETURN_VOID));

        new InstructionInjector(impl).insertBefore(2, monitorPlan(null));

        List<BuilderInstruction> ins = impl.getInstructions();
        assertEquals(2, targetIndex(ins.get(0)), "goto lands on the first inserted instruction");
        assertEquals(Opcode.INVOKE_STATIC, ins.get(2).getOpcode());
        assertEquals(Opcode.INVOKE_VIRTUAL, ins.get(3).getOpcode());
    }

    @Test
    void packedSwitchCaseLandsOnTheInsertedBlock() {
        //   0: packed-switch v0, :payload
        //   1: return-void                      ; default and case 1
        //   2: :call invoke-virtual Cipher.init ; case 0
        //   3: return-void
        //   4: :payload packed-switch-payload { 0 -> :call, 1 -> 1 }
        MutableMethodImplementation impl = method(5, 2);
        impl.replaceInstruction(1, new BuilderInstruction10x(Opcode.RETURN_VOID));
        impl.replaceInstruction(4, new BuilderPackedSwitchPayload(0,
                List.of(impl.newLabelForIndex(2), impl.newLabelForIndex(1))));
        impl.replaceInstruction(0, new BuilderInstruction31t(Opcode.PACKED_SWITCH, 0,
                impl.newLabelForIndex(4)));

        new InstructionInjector(impl).insertBefore(2, monitorPlan(null));

        List<BuilderInstruction> ins = impl.getInstructions();
        BuilderSwitchPayload payload = payload(ins);
        assertEquals(2, payload.getSwitchElements().get(0).getTarget().getLocation().getIndex(),
                "case 0 lands on the first inserted instruction");
        assertEquals(1, payload.getSwitchElements().get(1).getTarget().getLocation().getIndex(),
                "a case that does not target the call is untouched");
        assertEquals(Opcode.INVOKE_STATIC, ins.get(2).getOpcode());
        assertEquals(Opcode.INVOKE_VIRTUAL, ins.get(3).getOpcode());
    }

    @Test
    void sparseSwitchCaseLandsOnTheInsertedBlock() {
        //   0: sparse-switch v0, :payload
        //   1: return-void
        //   2: :call invoke-virtual Cipher.init ; case 7
        //   3: return-void
        //   4: :payload sparse-switch-payload { 7 -> :call }
        MutableMethodImplementation impl = method(5, 2);
        impl.replaceInstruction(1, new BuilderInstruction10x(Opcode.RETURN_VOID));
        impl.replaceInstruction(4, new BuilderSparseSwitchPayload(
                List.of(new SwitchLabelElement(7, impl.newLabelForIndex(2)))));
        impl.replaceInstruction(0, new BuilderInstruction31t(Opcode.SPARSE_SWITCH, 0,
                impl.newLabelForIndex(4)));

        new InstructionInjector(impl).insertBefore(2, monitorPlan(null));

        List<BuilderInstruction> ins = impl.getInstructions();
        assertEquals(2, payload(ins).getSwitchElements().get(0).getTarget().getLocation().getIndex(),
                "case 7 lands on the first inserted instruction");
        assertEquals(Opcode.INVOKE_VIRTUAL, ins.get(3).getOpcode());
    }

    @Test
    void guardedBlockAtABranchTargetKeepsItsSkip() {
        //   0: if-eqz v0, :call
        //   1: nop
        //   2: :call invoke-virtual Cipher.init
        //   3: return-void
        // with a before plan guarded by if(v1 == null).
        MutableMethodImplementation impl = method(4, 2);
        impl.replaceInstruction(0, new BuilderInstruction21t(Opcode.IF_EQZ, 0, impl.newLabelForIndex(2)));
        BuilderInstruction call = impl.getInstructions().get(2);

        new InstructionInjector(impl).insertBefore(2,
                monitorPlan(new EmitPlan.GuardSpec(EmitPlan.GuardKind.NULL_CHECK, 1)));

        List<BuilderInstruction> ins = impl.getInstructions();
        // 0 if-eqz, 1 nop, 2 if-nez v1 (guard), 3 monitor, 4 call, 5 return-void
        assertEquals(Opcode.IF_NEZ, ins.get(2).getOpcode(), "the guard prefix is the first inserted instruction");
        assertEquals(2, targetIndex(ins.get(0)), "the branch lands on the guard, not past it");
        assertEquals(Opcode.INVOKE_STATIC, ins.get(3).getOpcode());
        assertEquals(4, call.getLocation().getIndex());
        assertEquals(4, targetIndex(ins.get(2)),
                "guard false skips to the call without running the monitor call");
    }

    @Test
    void lineEntryMovesAndTryRangeAndLocalsStayOnTheCall() {
        //   0: packed-switch v0, :payload
        //   1: return-void
        //   2: :call invoke-virtual Cipher.init    ; line 69, start local v2, try start
        //   3: return-void                          ; try end
        //   4: move-exception v1                    ; handler
        //   5: throw v1
        //   6: :payload packed-switch-payload { 0 -> :call }
        MutableMethodImplementation impl = method(7, 2);
        impl.replaceInstruction(1, new BuilderInstruction10x(Opcode.RETURN_VOID));
        impl.replaceInstruction(4, new BuilderInstruction11x(Opcode.MOVE_EXCEPTION, 1));
        impl.replaceInstruction(5, new BuilderInstruction11x(Opcode.THROW, 1));
        impl.replaceInstruction(6, new BuilderPackedSwitchPayload(0, List.of(impl.newLabelForIndex(2))));
        impl.replaceInstruction(0, new BuilderInstruction31t(Opcode.PACKED_SWITCH, 0,
                impl.newLabelForIndex(6)));
        BuilderInstruction call = impl.getInstructions().get(2);
        call.getLocation().addLineNumber(69);
        call.getLocation().addStartLocal(2, null, null, null);
        impl.addCatch(impl.newLabelForIndex(2), impl.newLabelForIndex(3), impl.newLabelForIndex(4));

        new InstructionInjector(impl).insertBefore(2, monitorPlan(null));

        List<BuilderInstruction> ins = impl.getInstructions();
        BuilderInstruction first = ins.get(2);
        assertEquals(Opcode.INVOKE_STATIC, first.getOpcode());
        assertEquals(2, payload(ins).getSwitchElements().get(0).getTarget().getLocation().getIndex(),
                "the switch case lands on the first inserted instruction");

        assertEquals(List.of(69), lineNumbers(first.getLocation().getDebugItems()),
                "the first inserted instruction carries the call's line");
        assertEquals(List.of(), lineNumbers(call.getLocation().getDebugItems()),
                "the line entry left the call");
        assertTrue(call.getLocation().getDebugItems().stream().anyMatch(d -> d instanceof BuilderStartLocal),
                "the local-variable entry stays on the call");

        BuilderTryBlock tryBlock = impl.getTryBlocks().get(0);
        assertEquals(call.getLocation().getIndex(), tryBlock.start.getLocation().getIndex(),
                "the try range still begins at the call, not at the block");
        assertEquals(call.getLocation().getIndex() + 1, tryBlock.end.getLocation().getIndex());
    }

    // --- fixtures -----------------------------------------------------------

    /**
     * A method of {@code size} {@code nop}s with {@code invoke-virtual {v2, v0, v1},
     * Cipher.init(I, Key)V} at {@code callIdx} and {@code return-void} right after it.
     * Callers replace placeholders with branches once every target index exists.
     */
    private static MutableMethodImplementation method(int size, int callIdx) {
        MutableMethodImplementation impl = new MutableMethodImplementation(3);
        for (int i = 0; i < size; i++) impl.addInstruction(new BuilderInstruction10x(Opcode.NOP));
        impl.replaceInstruction(callIdx, new BuilderInstruction35c(
                Opcode.INVOKE_VIRTUAL, 3, 2, 0, 1, 0, 0, CIPHER_INIT));
        impl.replaceInstruction(callIdx + 1, new BuilderInstruction10x(Opcode.RETURN_VOID));
        return impl;
    }

    private static EmitPlan monitorPlan(EmitPlan.GuardSpec guard) {
        return new EmitPlan(
                List.of(new BuilderInstruction35c(Opcode.INVOKE_STATIC, 1, 2, 0, 0, 0, 0, MONITOR_EVENT)),
                InsertionPoint.BEFORE, RegisterRequest.NONE, null, guard);
    }

    private static int targetIndex(BuilderInstruction branch) {
        return ((BuilderOffsetInstruction) branch).getTarget().getLocation().getIndex();
    }

    private static BuilderSwitchPayload payload(List<BuilderInstruction> ins) {
        for (BuilderInstruction i : ins) {
            if (i instanceof BuilderSwitchPayload p) return p;
        }
        throw new AssertionError("no switch payload");
    }

    private static int countMonitorCalls(List<BuilderInstruction> ins) {
        int n = 0;
        for (BuilderInstruction i : ins) {
            if (i.getOpcode() == Opcode.INVOKE_STATIC
                    && MONITOR_EVENT.equals(((ReferenceInstruction) i).getReference())) n++;
        }
        return n;
    }

    private static List<Integer> lineNumbers(Iterable<? extends BuilderDebugItem> items) {
        List<Integer> out = new ArrayList<>();
        for (BuilderDebugItem item : items) {
            if (item instanceof BuilderLineNumber l) out.add(l.getLineNumber());
        }
        return out;
    }

    private static int addressOf(List<Instruction> ins, int index) {
        int address = 0;
        for (int i = 0; i < index; i++) address += ins.get(i).getCodeUnits();
        return address;
    }

    private static Instruction instructionAt(List<Instruction> ins, int address) {
        int a = 0;
        for (Instruction i : ins) {
            if (a == address) return i;
            a += i.getCodeUnits();
        }
        throw new AssertionError("no instruction at address " + address);
    }

    /** Write {@code impl} as the body of {@code LFoo;->m()V} through DexPool and reload it. */
    private static MethodImplementation roundTrip(MutableMethodImplementation impl) throws Exception {
        ImmutableMethod m = new ImmutableMethod("LFoo;", "m", Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(), null, null, impl);
        ImmutableClassDef foo = new ImmutableClassDef("LFoo;", AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", Collections.emptyList(), null, null,
                Collections.emptyList(), List.of(m));
        Path tmp = Files.createTempFile("branch-target-", ".dex");
        try {
            DexPool.writeTo(tmp.toString(), new ImmutableDexFile(Opcodes.getDefault(), List.of(foo)));
            try (InputStream in = new BufferedInputStream(Files.newInputStream(tmp))) {
                DexBackedDexFile parsed = DexBackedDexFile.fromInputStream(Opcodes.getDefault(), in);
                for (DexBackedClassDef cd : parsed.getClasses()) {
                    for (DexBackedMethod method : cd.getMethods()) {
                        MethodImplementation body = method.getImplementation();
                        assertNotNull(body);
                        return body;
                    }
                }
            }
        } finally {
            Files.deleteIfExists(tmp);
        }
        throw new AssertionError("method not reloaded");
    }
}
