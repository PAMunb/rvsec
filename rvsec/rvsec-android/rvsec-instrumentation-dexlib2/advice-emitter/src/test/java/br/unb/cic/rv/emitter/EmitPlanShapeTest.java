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

    // ------------------------------------------------------------------
    // IfGuardEmitter error paths (INV-INS-66 fail-loud contract): a guard is
    // NEVER silently dropped to an always-match, which would weave an invoke the
    // source intended to gate. Each of these raises UnsupportedAspectConstructError
    // rather than emitting an ungated plan. These paths (and the exception class
    // itself) were entirely dark.
    // ------------------------------------------------------------------

    @Test
    void ifGuardWithoutIfClauseFailsLoud() {
        // The emitter is selected but the advice expression carries NO if(...)
        // clause — extractIfExpression returns null → fail loud (never an
        // ungated always-match plan).
        IfGuardEmitter guard = new IfGuardEmitter().wrapping(new BeforeEmitter());
        assertThrows(UnsupportedAspectConstructError.class,
                () -> guard.emit(ctx(adviceBefore("noif"))),
                "an if-guard emitter over an expression with no if(...) clause MUST fail loud");
    }

    @Test
    void ifGuardWithUnsupportedShapeFailsLoud() {
        // if(it.size() > 0) matches neither NULL_CHECK nor NOT_HOLDS_LOCK — the
        // only two lowered shapes — so it MUST be rejected, not woven ungated.
        IfGuardEmitter guard = new IfGuardEmitter().wrapping(new BeforeEmitter());
        assertThrows(UnsupportedAspectConstructError.class,
                () -> guard.emit(ctx(EmitterTestFixtures.adviceWithUnsupportedIfGuard("bad"))),
                "an if(...) shape outside the two lowered forms MUST fail loud");
    }

    @Test
    void ifGuardWithUnresolvableBoundFailsLoud() {
        // if(ghost == null) has a lowered shape (NULL_CHECK), but 'ghost' is not a
        // resolvable target/args binding for this match — the guard cannot be gated
        // to a real register, so it MUST fail loud rather than gate on garbage.
        AdviceDescriptor a = adviceBefore("g");
        a.setExpression("call(public boolean Iterator.hasNext()) && target(it) && if(ghost == null)");
        IfGuardEmitter guard = new IfGuardEmitter().wrapping(new BeforeEmitter());
        assertThrows(UnsupportedAspectConstructError.class,
                () -> guard.emit(ctx(a)),
                "a null-check over an unresolvable bound MUST fail loud (no register to gate on)");
    }

    @Test
    void ifGuardKindNamesTheWrappedDelegate() {
        // kind() composes the delegate's kind; the raw (delegate-less) form
        // reports the placeholder marker.
        assertEquals("if-guarded[before]",
                new IfGuardEmitter().wrapping(new BeforeEmitter()).kind());
        assertEquals("if-guarded[-]", new IfGuardEmitter().kind());
    }
}
