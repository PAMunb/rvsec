package br.unb.cic.rv.mutator;

import br.unb.cic.rv.emitter.EmitPlan;
import br.unb.cic.rv.emitter.InsertionPoint;
import br.unb.cic.rv.emitter.RegisterRequest;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.BuilderTryBlock;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableExceptionHandler;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.ImmutableTryBlock;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction11x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link InstructionInjector} primitive contracts left dark by the base test:
 *
 * <ul>
 *   <li><b>INV-INS-64 placement</b>: {@code insertAfter} on an invoke followed
 *       by {@code move-result*} must land the block AFTER the move-result —
 *       any instruction between an invoke and its {@code move-result*} either
 *       corrupts the read value or is verifier-rejected outright. Positive
 *       control: with no move-result follower the block lands immediately
 *       after the invoke.</li>
 *   <li><b>{@code insertAtMethodEntry}</b>: prepends the whole block at
 *       index 0 preserving plan order (the METHOD_ENTRY route used by
 *       staticinit prepends).</li>
 *   <li><b>Fail-loud guards</b>: {@code replaceInvoke} on a non-invoke opcode
 *       and {@code installTryCatch} without a {@link EmitPlan.TryCatchSpec}
 *       must throw instead of silently corrupting the method.</li>
 *   <li><b>§4.T range preservation</b>: a pre-existing user try-block that
 *       does NOT cover the matched invoke must survive the try-table rebuild
 *       VERBATIM (same range, same handler, same catch type) while the new
 *       standalone advice range is added — dropping or widening a
 *       non-covering user range would re-route the app's own exception
 *       handling.</li>
 * </ul>
 */
class InstructionInjectorEdgeTest {

    private static final MethodReference CALLEE_INT = new ImmutableMethodReference(
            "Lpkg/O;", "f", List.of(), "I");
    private static final MethodReference CALLEE_A = new ImmutableMethodReference(
            "Lpkg/O;", "a", List.of(), "V");
    private static final MethodReference CALLEE_B = new ImmutableMethodReference(
            "Lpkg/O;", "b", List.of(), "V");
    private static final MethodReference MONITOR_EVENT = new ImmutableMethodReference(
            "Lmop/MultiSpec_1RuntimeMonitor;", "SampleSpec_t1Event",
            List.of("Ljava/lang/Throwable;"), "V");

    // ------------------------------------------------------------------
    // INV-INS-64: insertAfter placement relative to move-result
    // ------------------------------------------------------------------

    @Test
    void insertAfterLandsPastTheMoveResult() {
        // idx0: invoke-static {}, O.f()I
        // idx1: move-result v0        ← must stay glued to the invoke
        // idx2: return-void
        MutableMethodImplementation impl = new MutableMethodImplementation(2);
        impl.addInstruction(new BuilderInstruction35c(
                Opcode.INVOKE_STATIC, 0, 0, 0, 0, 0, 0, CALLEE_INT));
        impl.addInstruction(new com.android.tools.smali.dexlib2.builder.instruction
                .BuilderInstruction11x(Opcode.MOVE_RESULT, 0));
        impl.addInstruction(new BuilderInstruction10x(Opcode.RETURN_VOID));

        EmitPlan plan = EmitPlan.of(
                List.of(new BuilderInstruction10x(Opcode.NOP)), InsertionPoint.AFTER);
        new InstructionInjector(impl).insertAfter(0, plan);

        List<BuilderInstruction> after = new ArrayList<>(impl.getInstructions());
        assertEquals(4, after.size());
        assertEquals(Opcode.INVOKE_STATIC, after.get(0).getOpcode());
        assertEquals(Opcode.MOVE_RESULT, after.get(1).getOpcode(),
                "move-result must remain the invoke's immediate successor");
        assertEquals(Opcode.NOP, after.get(2).getOpcode(),
                "the AFTER block lands past the move-result, not between");
        assertEquals(Opcode.RETURN_VOID, after.get(3).getOpcode());
    }

    @Test
    void insertAfterLandsImmediatelyAfterWhenNoMoveResult() {
        // Positive control: void-returning invoke, no move-result follower —
        // the block must land directly at index+1 (no gratuitous skip).
        MutableMethodImplementation impl = new MutableMethodImplementation(1);
        impl.addInstruction(new BuilderInstruction35c(
                Opcode.INVOKE_STATIC, 0, 0, 0, 0, 0, 0, CALLEE_A));
        impl.addInstruction(new BuilderInstruction10x(Opcode.RETURN_VOID));

        EmitPlan plan = EmitPlan.of(
                List.of(new BuilderInstruction10x(Opcode.NOP)), InsertionPoint.AFTER);
        new InstructionInjector(impl).insertAfter(0, plan);

        List<BuilderInstruction> after = new ArrayList<>(impl.getInstructions());
        assertEquals(3, after.size());
        assertEquals(Opcode.INVOKE_STATIC, after.get(0).getOpcode());
        assertEquals(Opcode.NOP, after.get(1).getOpcode(),
                "no move-result → block lands immediately after the invoke");
        assertEquals(Opcode.RETURN_VOID, after.get(2).getOpcode());
    }

    // ------------------------------------------------------------------
    // insertAtMethodEntry
    // ------------------------------------------------------------------

    @Test
    void insertAtMethodEntryPrependsBlockInPlanOrder() {
        MutableMethodImplementation impl = new MutableMethodImplementation(1);
        impl.addInstruction(new BuilderInstruction10x(Opcode.RETURN_VOID));

        // Two distinguishable instructions to lock the ORDER, not just the spot.
        EmitPlan plan = EmitPlan.of(List.of(
                new BuilderInstruction35c(
                        Opcode.INVOKE_STATIC, 0, 0, 0, 0, 0, 0, CALLEE_A),
                new BuilderInstruction10x(Opcode.NOP)),
                InsertionPoint.METHOD_ENTRY);
        new InstructionInjector(impl).insertAtMethodEntry(plan);

        List<BuilderInstruction> after = new ArrayList<>(impl.getInstructions());
        assertEquals(3, after.size());
        assertEquals(Opcode.INVOKE_STATIC, after.get(0).getOpcode(),
                "first plan instruction lands at method entry");
        assertEquals(Opcode.NOP, after.get(1).getOpcode(),
                "plan order preserved");
        assertEquals(Opcode.RETURN_VOID, after.get(2).getOpcode());
    }

    // ------------------------------------------------------------------
    // fail-loud guards
    // ------------------------------------------------------------------

    @Test
    void replaceInvokeRejectsNonInvokeOpcode() {
        MutableMethodImplementation impl = new MutableMethodImplementation(1);
        impl.addInstruction(new BuilderInstruction10x(Opcode.RETURN_VOID));
        InstructionInjector inj = new InstructionInjector(impl);

        IllegalStateException ex = assertThrows(IllegalStateException.class,
                () -> inj.replaceInvoke(0, CALLEE_A),
                "rewriting a non-invoke would corrupt the method silently");
        assertTrue(ex.getMessage().contains("non-invoke"),
                "message must name the failure: " + ex.getMessage());
    }

    @Test
    void installTryCatchRequiresTryCatchSpec() {
        MutableMethodImplementation impl = new MutableMethodImplementation(2);
        impl.addInstruction(new BuilderInstruction35c(
                Opcode.INVOKE_STATIC, 0, 0, 0, 0, 0, 0, CALLEE_A));
        impl.addInstruction(new BuilderInstruction10x(Opcode.RETURN_VOID));

        // A TRY_CATCH_WRAP plan built without its spec — the injector cannot
        // know the catch type or throwing slot, so it must fail loud.
        EmitPlan noSpec = EmitPlan.of(
                List.of(new BuilderInstruction10x(Opcode.NOP)),
                InsertionPoint.TRY_CATCH_WRAP);
        InstructionInjector inj = new InstructionInjector(impl);
        assertThrows(IllegalArgumentException.class,
                () -> inj.installTryCatch(0, noSpec, /*exceptionRegister=*/ 1));
    }

    // ------------------------------------------------------------------
    // §4.T: non-covering user try-block preserved verbatim
    // ------------------------------------------------------------------

    @Test
    void nonCoveringUserTryBlockSurvivesRebuildVerbatim() {
        // idx0: invoke-static {}, O.a()V   [user try covers ONLY this]  3 units
        // idx1: invoke-static {}, O.b()V   ← matchedIdx (outside the try) 3 units
        // idx2: return-void                                             1 unit
        // idx3: move-exception v0          (user handler)               1 unit
        // idx4: return-void                                             1 unit
        List<ImmutableInstruction> body = new ArrayList<>();
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_STATIC, 0, 0, 0, 0, 0, 0, CALLEE_A));
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_STATIC, 0, 0, 0, 0, 0, 0, CALLEE_B));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        body.add(new ImmutableInstruction11x(Opcode.MOVE_EXCEPTION, 0));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));

        // User try-block over idx0 only: startAddr=0, 3 code units; handler at
        // idx3 (addr 7), catching RuntimeException.
        ImmutableTryBlock userTry = new ImmutableTryBlock(0, 3, List.of(
                new ImmutableExceptionHandler("Ljava/lang/RuntimeException;", 7)));
        ImmutableMethodImplementation immutable = new ImmutableMethodImplementation(
                /*registerCount=*/ 2, body, List.of(userTry), Collections.emptyList());
        MutableMethodImplementation impl = new MutableMethodImplementation(immutable);

        // catch-all after() throwing plan: handler body is one monitor invoke
        // whose slot 0 receives the caught exception.
        EmitPlan plan = EmitPlan.tryCatch(
                List.of(new BuilderInstruction35c(
                        Opcode.INVOKE_STATIC, 1, 0, 0, 0, 0, 0, MONITOR_EVENT)),
                RegisterRequest.NONE,
                EmitPlan.TryCatchSpec.catchAll(/*throwingOperandIndices=*/ List.of(0)));

        MutableMethodImplementation rebuilt = new InstructionInjector(impl)
                .installTryCatch(/*matchedIdx=*/ 1, plan, /*exceptionRegister=*/ 1);

        // Handler block appended at the end: move-exception, invoke, throw.
        List<BuilderInstruction> after = new ArrayList<>(rebuilt.getInstructions());
        assertEquals(8, after.size(), "5 original + 3 appended handler instructions");
        assertEquals(Opcode.MOVE_EXCEPTION, after.get(5).getOpcode());
        assertEquals(Opcode.INVOKE_STATIC, after.get(6).getOpcode());
        assertEquals(Opcode.THROW, after.get(7).getOpcode());

        // Two try ranges, sorted by start: the user's untouched + the new one.
        List<BuilderTryBlock> tries = new ArrayList<>(rebuilt.getTryBlocks());
        assertEquals(2, tries.size(),
                "non-covering user range preserved + one standalone advice range");

        BuilderTryBlock user = tries.get(0);
        assertEquals(0, user.start.getLocation().getIndex(),
                "user range start untouched (idx0)");
        assertEquals(1, user.end.getLocation().getIndex(),
                "user range end untouched (exclusive idx1)");
        assertEquals("Ljava/lang/RuntimeException;",
                user.getExceptionHandlers().get(0).getExceptionType(),
                "user catch type untouched");
        assertEquals(3, user.exceptionHandler.getHandler().getLocation().getIndex(),
                "user handler target untouched (idx3 move-exception)");

        BuilderTryBlock advice = tries.get(1);
        assertEquals(1, advice.start.getLocation().getIndex(),
                "advice range covers exactly the matched invoke");
        assertEquals(2, advice.end.getLocation().getIndex());
        assertNull(advice.getExceptionHandlers().get(0).getExceptionType(),
                "catch-all advice handler has null (any) exception type");
        assertEquals(5, advice.exceptionHandler.getHandler().getLocation().getIndex(),
                "advice handler targets the appended move-exception (idx5)");
    }
}
