package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import org.junit.jupiter.api.Test;

import static br.unb.cic.rv.emitter.EmitterTestFixtures.adviceAfter;
import static br.unb.cic.rv.emitter.EmitterTestFixtures.adviceAfterReturning;
import static br.unb.cic.rv.emitter.EmitterTestFixtures.adviceAfterThrowing;
import static br.unb.cic.rv.emitter.EmitterTestFixtures.adviceBefore;
import static br.unb.cic.rv.emitter.EmitterTestFixtures.adviceStaticInit;
import static br.unb.cic.rv.emitter.EmitterTestFixtures.ctx;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Per-emitter shape assertions (task 4.5). Verifies that each emitter returns
 * an {@link EmitPlan} with the correct {@link InsertionPoint}, register
 * demand, and (where relevant) try/catch spec. Byte-exact instruction
 * validation is covered by {@code dex-mutator}'s integration tests once a
 * real DEX fixture is available.
 */
class EmitPlanShapeTest {

    @Test
    void beforeEmitterTargetsBeforeInsertionPoint() {
        EmitPlan plan = new BeforeEmitter().emit(ctx(adviceBefore("before")));
        assertEquals(InsertionPoint.BEFORE, plan.insertionPoint());
        assertEquals(RegisterRequest.NONE, plan.registers());
        assertNull(plan.tryCatchSpec());
        assertFalse(plan.toInsert().isEmpty(), "plan must emit at least the monitor invoke");
    }

    @Test
    void afterEmitterTargetsAfterInsertionPoint() {
        EmitPlan plan = new AfterEmitter().emit(ctx(adviceAfter("after")));
        assertEquals(InsertionPoint.AFTER, plan.insertionPoint());
    }

    @Test
    void afterReturningEmitterRequestsNoScratchRegister() {
        // INV-INS-66 / D5: AFTER advice with returning() flows through the
        // wrapper-substitution path (mop.MonitorWrappers.X), which captures
        // the original return value in the wrapper's local frame. The inline
        // emitter therefore does NOT need to allocate a caller-side scratch
        // register — that was the buggy behavior that earlier surfaced as
        // VerifyError on cryptoapp (commit 54307992 removed the request).
        EmitPlan plan = new AfterReturningEmitter().emit(ctx(adviceAfterReturning("aret")));
        assertEquals(InsertionPoint.AFTER, plan.insertionPoint());
        assertEquals(0, plan.registers().scratchCount(),
                "AfterReturning routes through wrapper system; no inline scratch needed");
    }

    @Test
    void afterThrowingEmitterProducesTryCatchSpec() {
        AdviceDescriptor a = adviceAfterThrowing("ath", "Exception");
        EmitPlan plan = new AfterThrowingEmitter().emit(ctx(a));
        assertEquals(InsertionPoint.TRY_CATCH_WRAP, plan.insertionPoint());
        assertNotNull(plan.tryCatchSpec());
        assertFalse(plan.tryCatchSpec().catchAny(),
                "specific thrown type must not produce a catch-any");
        assertEquals("Ljava/lang/Exception;", plan.tryCatchSpec().catchType());
    }

    @Test
    void afterThrowingWithoutBoundTypeCatchesAnyThrowable() {
        AdviceDescriptor a = adviceAfterThrowing("ath", "Throwable");
        a.setThrowing(java.util.Collections.emptyList());
        // Pre-gh56 this test relied on registersFor's literal-0 fallback for
        // the dangling 't' reference in monitorCall.args. That fallback was
        // the VerifyError vector (INV-INS-71); the contract is now
        // "consistent monitor invoke or skip". The test's actual intent is
        // to verify the TryCatchSpec catch-any shape, so we drop the
        // inconsistent 't' arg to match a real "no throwing parameter"
        // scenario where the monitor event takes no exception register.
        a.getMonitorCalls().get(0).setArgs(java.util.Collections.emptyList());
        EmitPlan plan = new AfterThrowingEmitter().emit(ctx(a));
        assertEquals(InsertionPoint.TRY_CATCH_WRAP, plan.insertionPoint());
        assertNotNull(plan.tryCatchSpec());
        assertTrue(plan.tryCatchSpec().catchAny());
        assertEquals("Ljava/lang/Throwable;", plan.tryCatchSpec().catchType());
    }

    @Test
    void staticInitEmitterTargetsMethodEntry() {
        AdviceDescriptor a = adviceStaticInit("si", "java.util.ArrayList+");
        EmitPlan plan = new StaticInitializationEmitter().emit(ctx(a));
        assertEquals(InsertionPoint.METHOD_ENTRY, plan.insertionPoint());
    }

    @Test
    void ifGuardNullCheckCarriesGuardSpecWithoutScratch() {
        BeforeEmitter base = new BeforeEmitter();
        IfGuardEmitter guard = new IfGuardEmitter().wrapping(base);
        EmitPlan plan = guard.emit(ctx(EmitterTestFixtures.adviceWithIfGuard("g")));
        assertEquals(InsertionPoint.BEFORE, plan.insertionPoint());
        assertNotNull(plan.guardSpec(), "null-check guard must attach a GuardSpec");
        assertEquals(EmitPlan.GuardKind.NULL_CHECK, plan.guardSpec().kind());
        assertEquals(0, plan.registers().scratchCount(),
                "null-check branches on vBound directly; no scratch needed");
    }

    @Test
    void ifGuardHoldsLockAddsOneScratchForMoveResult() {
        BeforeEmitter base = new BeforeEmitter();
        IfGuardEmitter guard = new IfGuardEmitter().wrapping(base);
        EmitPlan plan = guard.emit(ctx(EmitterTestFixtures.adviceWithHoldsLockGuard("g")));
        assertEquals(EmitPlan.GuardKind.NOT_HOLDS_LOCK, plan.guardSpec().kind());
        assertEquals(1, plan.registers().scratchCount(),
                "holdsLock guard adds one scratch for the move-result");
    }

    @Test
    void rawIfGuardEmitterWithoutDelegateFailsFast() {
        IfGuardEmitter guard = new IfGuardEmitter();
        assertThrows(IllegalStateException.class,
                () -> guard.emit(ctx(EmitterTestFixtures.adviceBefore("x"))));
    }
}
