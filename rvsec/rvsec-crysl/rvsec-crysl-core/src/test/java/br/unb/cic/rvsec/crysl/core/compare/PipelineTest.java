package br.unb.cic.rvsec.crysl.core.compare;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.metric.M0Result;
import br.unb.cic.rvsec.crysl.core.metric.MetricResult;
import br.unb.cic.rvsec.crysl.core.metric.MisuseAbsorption;
import br.unb.cic.rvsec.crysl.core.metric.Silence;
import br.unb.cic.rvsec.crysl.core.metric.SilenceCause;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * INV-CONF-09, in the form that can actually fail.
 *
 * <p>The half of the invariant a pipeline usually keeps is "M0 runs first". The half it loses is
 * that a refused specification receives no verdict, because computing four verdicts and filtering
 * them out afterwards satisfies the first half and leaves four verdicts in memory for somebody to
 * print. So the assertion here is not that the output is empty — it is that the downstream metrics
 * were <strong>never invoked</strong>.
 */
class PipelineTest {

    private static final Provenance SITE = new Provenance("Probe.mop", 1);

    private static M0Result result(boolean refused) {
        List<Silence> silences = refused
                ? List.of(new Silence("Probe", SilenceCause.LIVE_WITHOUT_ACCUSATION_SITE,
                        "no @fail and an empty @match", SITE))
                : List.of();
        return new M0Result("Probe", true, !refused,
                new MisuseAbsorption(false, List.of(), MisuseAbsorption.RULE), silences,
                List.of(), List.of(), List.of(), "probe rule");
    }

    @Test
    @DisplayName("INV-CONF-09: a refused specification never even computes M1-M4")
    void test_a_refused_specification_short_circuits() {
        AtomicInteger invocations = new AtomicInteger();

        Pipeline.Outcome outcome = Pipeline.run(result(true), () -> {
            invocations.incrementAndGet();
            return List.of();
        });

        assertEquals(0, invocations.get(), "the four verdicts are not filtered, they are not "
                + "produced: a verdict that was computed can be printed by the next reader");
        assertTrue(outcome.refused());
        assertTrue(outcome.verdicts().isEmpty());
        assertEquals(1, outcome.results().size(),
                "the typed refusal is the specification's whole result");
    }

    @Test
    @DisplayName("a specification M0 does not refuse reaches the downstream metrics")
    void test_a_live_specification_runs_the_rest() {
        AtomicInteger invocations = new AtomicInteger();

        Pipeline.Outcome outcome = Pipeline.run(result(false), () -> {
            invocations.incrementAndGet();
            return List.of();
        });

        assertEquals(1, invocations.get(), "the gate must be a gate and not a wall");
        assertFalse(outcome.refused());
        assertEquals("Probe", outcome.specification());
        assertEquals(List.of(outcome.m0()), outcome.results(), "M0 comes first in the report");
    }

    @Test
    @DisplayName("an Outcome that carries verdicts for a refused specification is rejected")
    void test_the_outcome_cannot_be_built_around_the_gate() {
        List<MetricResult> smuggled = List.of(result(false));

        IllegalArgumentException raised = assertThrows(IllegalArgumentException.class,
                () -> new Pipeline.Outcome(result(true), smuggled));

        assertTrue(raised.getMessage().contains("INV-CONF-09"), raised.getMessage());
    }

    @Test
    @DisplayName("the downstream supplier may not return an M0 result of its own")
    void test_m0_is_the_gate_and_not_a_product_of_it() {
        IllegalArgumentException raised = assertThrows(IllegalArgumentException.class,
                () -> Pipeline.run(result(false), () -> List.of(result(false))));

        assertTrue(raised.getMessage().contains("M0 is the gate"), raised.getMessage());
    }
}
