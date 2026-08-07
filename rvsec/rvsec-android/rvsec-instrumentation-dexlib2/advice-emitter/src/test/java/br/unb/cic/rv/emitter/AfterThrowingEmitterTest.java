package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.List;

import static br.unb.cic.rv.emitter.EmitterTestFixtures.adviceAfterThrowing;
import static br.unb.cic.rv.emitter.EmitterTestFixtures.ctx;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Covers the {@code throwingOperandIndex} resolution fallbacks of
 * {@link AfterThrowingEmitter} — every path that resolves to {@code -1} (no
 * exception operand to rewrite) — plus {@link AfterThrowingEmitter#kind}. The
 * shape tests in {@link EmitPlanShapeTest} only exercise the two well-formed
 * cases (a bound {@code throwing(Exception t)} with the name present in the
 * monitor args → operand index {@code 0}, and an empty {@code throwing()} →
 * catch-all), leaving five distinct {@code -1} branches and {@code kind()}
 * dark (61% branch coverage).
 *
 * <p>The operand index is the slot the {@code dex-mutator} executor rewrites to
 * the {@code move-exception} register. When it is {@code -1} the executor must
 * install the {@code try}/{@code catch} without touching any operand — the
 * monitor event simply takes no exception argument. Each fallback below is a
 * legitimate "no operand to rewrite" shape; getting {@code -1} wrong would make
 * the executor rewrite an unrelated register and corrupt the invoke. Every
 * negative case carries the well-formed positive control ({@code operand index
 * 0}) in the same class so a {@code -1} cannot pass for the wrong reason.
 */
class AfterThrowingEmitterTest {

    private final AfterThrowingEmitter emitter = new AfterThrowingEmitter();

    @Test
    void boundThrowingNamePresentInArgsResolvesToOperandZero() {
        // Positive control for every -1 case below: throwing(Exception t) with
        // "t" as the sole monitor arg → the exception is operand slot 0.
        AdviceDescriptor a = adviceAfterThrowing("ath", "Exception");
        EmitPlan plan = emitter.emit(ctx(a));

        assertEquals("Ljava/lang/Exception;", plan.tryCatchSpec().catchType());
        assertEquals(List.of(0), plan.tryCatchSpec().throwingOperandIndices(),
                "bound exception name present in monitor args must map to its slot");
    }

    @Test
    void nullThrowingClauseProducesCatchAllWithNoOperand() {
        // An after advice routed here with NO throwing() clause (getThrowing()
        // == null) must install a catch-all on Throwable and resolve the operand
        // to -1 (there is no exception parameter to bind). Exercises the null
        // short-circuit of both the emit() catch-type branch and
        // throwingOperandIndex.
        AdviceDescriptor a = adviceAfterThrowing("ath", "Exception");
        a.setThrowing(null);
        a.getMonitorCalls().get(0).setArgs(Collections.emptyList());

        EmitPlan plan = emitter.emit(ctx(a));

        assertTrue(plan.tryCatchSpec().catchAny(),
                "no throwing() clause must fall back to a catch-any on Throwable");
        assertEquals("Ljava/lang/Throwable;", plan.tryCatchSpec().catchType());
        assertEquals(List.of(-1), plan.tryCatchSpec().throwingOperandIndices());
    }

    @Test
    void throwingParameterWithNullNameResolvesToNoOperand() {
        // A throwing() parameter carrying a null name cannot be matched against
        // any monitor arg → operand -1 (the invoke keeps its catch-type but binds
        // no exception register). Args emptied so the invoke build stays resolvable.
        AdviceDescriptor a = adviceAfterThrowing("ath", "Exception");
        a.setThrowing(List.of(new ParameterDescriptor("Exception", null)));
        a.getMonitorCalls().get(0).setArgs(Collections.emptyList());

        EmitPlan plan = emitter.emit(ctx(a));

        assertEquals("Ljava/lang/Exception;", plan.tryCatchSpec().catchType());
        assertEquals(List.of(-1), plan.tryCatchSpec().throwingOperandIndices());
    }

    @Test
    void missingMonitorCallResolvesToNoOperand() {
        // No monitor call at all → no invoke is emitted → the index list is empty.
        // The try/catch is still installed (a bound Exception type), just with
        // nothing in its handler to rewrite.
        AdviceDescriptor a = adviceAfterThrowing("ath", "Exception");
        a.setMonitorCalls(Collections.emptyList());

        EmitPlan plan = emitter.emit(ctx(a));

        assertEquals("Ljava/lang/Exception;", plan.tryCatchSpec().catchType());
        assertEquals(List.of(), plan.tryCatchSpec().throwingOperandIndices(),
                "no monitor call means no invoke, so there is no operand slot to report");
    }

    @Test
    void nullArgsListResolvesToNoOperand() {
        // A monitor call whose args list is null (never populated) leaves nothing
        // to search → operand -1. Distinct from the empty-args case: this hits the
        // args == null guard, not the loop-completes-without-match path below.
        AdviceDescriptor a = adviceAfterThrowing("ath", "Exception");
        MonitorCallDescriptor call = a.getMonitorCalls().get(0);
        call.setArgs(null);

        EmitPlan plan = emitter.emit(ctx(a));

        assertEquals("Ljava/lang/Exception;", plan.tryCatchSpec().catchType());
        assertEquals(List.of(-1), plan.tryCatchSpec().throwingOperandIndices());
    }

    @Test
    void throwingNameAbsentFromNonEmptyArgsResolvesToNoOperand() {
        // The throwing name "t" is searched across a non-empty args list that does
        // NOT contain it (only "it") → the loop completes without a match and falls
        // through to -1. This is the only case that actually iterates the args loop
        // to exhaustion; "it" is a resolvable binding so the invoke build succeeds.
        AdviceDescriptor a = adviceAfterThrowing("ath", "Exception");
        a.getMonitorCalls().get(0).setArgs(List.of("it"));

        EmitPlan plan = emitter.emit(ctx(a));

        assertEquals("Ljava/lang/Exception;", plan.tryCatchSpec().catchType());
        assertEquals(List.of(-1), plan.tryCatchSpec().throwingOperandIndices());
    }

    @Test
    void kindIdentifiesAfterThrowing() {
        assertEquals("after-throwing", emitter.kind());
    }
}
