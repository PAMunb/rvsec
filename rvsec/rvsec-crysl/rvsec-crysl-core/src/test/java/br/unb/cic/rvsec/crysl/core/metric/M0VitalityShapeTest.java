package br.unb.cic.rvsec.crysl.core.metric;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.automata.LabelAutomaton;
import br.unb.cic.rvsec.crysl.core.model.UnreachableAccusationSite;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * What M0 decides, over automata small enough to check by hand.
 *
 * <p>These are the criteria, not the corpus. {@code M0VitalityTest} in the {@code -crysl} module
 * answers what {@code jca} and {@code jca_android} say today; a corpus count that moves is
 * ambiguous between "the corpus moved" and "the criterion moved", and these tests are what makes
 * the second one visible on its own.
 */
class M0VitalityShapeTest {

    private static final Map<String, HandlerState> FAIL_WITH_BODY =
            Map.of(MonitorFacts.FAIL, HandlerState.NON_EMPTY);

    private static M0Result examine(LabelAutomaton order, MonitorFacts facts, String... labels) {
        return M0Vitality.examine(M0Fixtures.model(labels), order, facts, Optional.empty());
    }

    @Test
    @DisplayName("M0.1: a specification with no declared parameter does not index")
    void test_no_parameter_does_not_index() {
        M0Result result = examine(M0Fixtures.loop("a"), M0Fixtures.facts(0, 1, 0, FAIL_WITH_BODY),
                "a");

        assertFalse(result.indexes(), "no declared parameter means one monitor for the whole "
                + "program, so parametric slicing is a no-op in it");
        assertTrue(result.countingRule().contains("0/N binding"),
                "the rule travels with the answer (INV-CONF-02): " + result.countingRule());
    }

    @Test
    @DisplayName("M0.1: 0/N binding does not index, and 1/N does")
    void test_binding_decides_indexing() {
        assertFalse(examine(M0Fixtures.loop("a"), M0Fixtures.facts(1, 7, 0, FAIL_WITH_BODY), "a")
                .indexes(), "0/7 binding: no event keys a slice, so there is one global monitor");
        assertTrue(examine(M0Fixtures.loop("a"), M0Fixtures.facts(1, 7, 1, FAIL_WITH_BODY), "a")
                .indexes(), "one binding event is enough for the generated monitor to index");
    }

    @Test
    @DisplayName("6.2: the AST proxy caveat is emitted with every result, refused or not")
    void test_the_proxy_caveat_is_always_emitted() {
        M0Result indexing = examine(M0Fixtures.loop("a"),
                M0Fixtures.facts(1, 1, 1, FAIL_WITH_BODY), "a");
        M0Result notIndexing = examine(M0Fixtures.loop("a"),
                M0Fixtures.facts(0, 1, 0, FAIL_WITH_BODY), "a");

        for (M0Result result : List.of(indexing, notIndexing)) {
            assertTrue(result.notes().contains(M0Vitality.INDEXING_PROXY_CAVEAT),
                    "M0.1 answers from the AST and the generated monitor is the oracle; publishing "
                            + "the proxy as if it were the oracle is the error M0 exists to "
                            + "prevent. Notes were: " + result.notes());
        }
        assertTrue(M0Vitality.INDEXING_PROXY_CAVEAT.contains("MapOfMonitor"),
                "the caveat has to name what the real oracle is, not merely that there is one");
    }

    @Test
    @DisplayName("cause (c): no @fail and an empty @match is the refusal")
    void test_no_accusation_site_is_the_refusal() {
        M0Result result = examine(M0Fixtures.chain("vo", "gb"),
                M0Fixtures.facts(1, 2, 0, Map.of("match", HandlerState.EMPTY)), "vo", "gb");

        assertFalse(result.accusationSiteReachable());
        assertTrue(result.refused(), "INV-CONF-09: this is the one cause that stops M1-M4");

        List<Silence> refusals = result.silences().stream().filter(Silence::refusal).toList();
        assertEquals(1, refusals.size(), "exactly one refusal: " + result.silences());
        assertEquals(SilenceCause.LIVE_WITHOUT_ACCUSATION_SITE, refusals.get(0).cause());
        assertEquals(SilenceCause.Disposition.REFUSAL, refusals.get(0).cause().disposition());
        assertTrue(refusals.get(0).statement().contains("an empty handler is the only way to state "
                        + "an automaton with nothing to report"),
                "the file's own explanation of why it is written this way travels with the "
                        + "refusal: " + refusals.get(0).statement());
    }

    @Test
    @DisplayName("INV-CONF-09: the refusal is also emitted as Unknown{UnreachableAccusationSite}")
    void test_the_refusal_is_emitted_as_a_typed_unknown() {
        M0Result result = examine(M0Fixtures.chain("vo", "gb"),
                M0Fixtures.facts(1, 2, 0, Map.of("match", HandlerState.EMPTY)), "vo", "gb");

        // The Silence classifies and gates; this is the emission, in the vocabulary every refusal
        // of the report is counted in. Asserting the type and not only the count is the point: the
        // nearest existing tag, UnresolvedSignature, asserts a signature the platform lacks, which
        // is a different claim about a different subject.
        assertEquals(1, result.refusals().size(), result.refusals().toString());
        UnreachableAccusationSite refusal =
                assertInstanceOf(UnreachableAccusationSite.class, result.refusals().get(0));
        assertEquals(result.specification(), refusal.specification());
        assertTrue(refusal.evidence().contains("@fail is ABSENT"),
                "the evidence names what the file does declare, so the refusal can be checked "
                        + "against the file: " + refusal.evidence());
        assertEquals(M0Fixtures.site(), refusal.site());
    }

    @Test
    @DisplayName("cause (a): a live prefix is a divergence row and never a refusal")
    void test_live_prefix_is_a_divergence_and_not_a_refusal() {
        M0Result result = examine(M0Fixtures.chain("c1", "cl1"),
                M0Fixtures.facts(1, 2, 2, FAIL_WITH_BODY), "c1", "cl1");

        assertFalse(result.refused(), "a limit of the formalism is not a defect of the file");
        assertEquals(1, result.divergences().size(), "one divergence row: " + result.silences());
        Silence divergence = result.divergences().get(0);
        assertEquals(SilenceCause.LIVE_BLIND_TO_END_OF_TRACE, divergence.cause());
        assertEquals(SilenceCause.Disposition.DIVERGENCE_RECORD, divergence.cause().disposition());
        assertTrue(divergence.statement().contains("the monitor is live"),
                "the report must say the monitor is live: " + divergence.statement());
    }

    @Test
    @DisplayName("cause (a) excludes the initial state: 'ere : c' has no live prefix")
    void test_the_initial_state_is_not_a_live_prefix() {
        M0Result result = examine(M0Fixtures.chain("c"), M0Fixtures.facts(1, 1, 1, FAIL_WITH_BODY),
                "c");

        assertTrue(result.divergences().isEmpty(),
                "stopping before the first call is not a violation of anything the specification "
                        + "says; a finding that fires for every specification carries no "
                        + "information. Got: " + result.silences());
    }

    @Test
    @DisplayName("M0.2: an addError in an event the formula admits is an accusation site")
    void test_an_absorbing_event_is_an_accusation_site() {
        MonitorFacts withFail = M0Fixtures.absorbing(1, 2, 2,
                Map.of("match", HandlerState.NON_EMPTY), "err1");

        M0Result inFormula = examine(M0Fixtures.loop("c1", "err1"), withFail, "c1", "err1");
        assertTrue(inFormula.accusationSiteReachable(),
                "no @fail, but an event the formula admits reports the misuse itself");

        M0Result outOfFormula = examine(M0Fixtures.loop("c1"), withFail, "c1", "err1");
        assertFalse(outOfFormula.accusationSiteReachable(),
                "the addError is in an event the formula never reads, so it can never run");
    }

    @Test
    @DisplayName("M0.2: an unparsed @fail is not read as an absent one")
    void test_unparsed_handler_does_not_refuse_a_healthy_specification() {
        M0Result result = examine(M0Fixtures.loop("a"),
                M0Fixtures.facts(1, 1, 1, Map.of(MonitorFacts.FAIL, HandlerState.UNPARSED)), "a");

        assertTrue(result.accusationSiteReachable(),
                "JavaParserAdapter swallows the exception and leaves a null block, so the body's "
                        + "content is unknown; reading unknown as empty would refuse a "
                        + "specification that does report");
        assertFalse(result.refused());
    }

    @Test
    @DisplayName("6.3: the four AST checks, each on its own witness")
    void test_the_four_ast_checks() {
        M0Result duplicate = examine(M0Fixtures.loop("c1"),
                M0Fixtures.facts(1, 2, 2, FAIL_WITH_BODY), "c1", "c1");
        assertTrue(duplicate.astViolations().stream()
                        .anyMatch(v -> v.contains("duplicate event identifier 'c1'")),
                duplicate.astViolations().toString());

        M0Result undeclared = examine(M0Fixtures.loop("c1", "c2"),
                M0Fixtures.facts(1, 1, 1, FAIL_WITH_BODY), "c1");
        assertTrue(undeclared.astViolations().stream()
                        .anyMatch(v -> v.contains("the formula names 'c2'")),
                undeclared.astViolations().toString());

        M0Result unreachable = examine(M0Fixtures.loop("c1"),
                M0Fixtures.facts(1, 2, 2, FAIL_WITH_BODY), "c1", "c3");
        assertTrue(unreachable.astViolations().stream()
                        .anyMatch(v -> v.contains("event 'c3' is declared and absent")),
                unreachable.astViolations().toString());

        M0Result unpaired = examine(M0Fixtures.loop("c1"),
                M0Fixtures.absorbing(1, 1, 1, Map.of("match", HandlerState.NON_EMPTY), "c1"), "c1");
        assertTrue(unpaired.astViolations().stream()
                        .anyMatch(v -> v.contains("@match declared with no @fail")),
                unpaired.astViolations().toString());

        assertTrue(unpaired.notes().contains(M0Vitality.AST_CHECKER_CAVEAT),
                "a violation drags the caveat with it: these files parse, generate a monitor and "
                        + "compile with zero errors");
    }

    @Test
    @DisplayName("the AST checker names the absorbs-misuse idiom instead of calling it a drop")
    void test_an_absorbing_event_outside_the_formula_is_named_as_such() {
        M0Result result = examine(M0Fixtures.loop("c1"),
                M0Fixtures.absorbing(1, 2, 2, FAIL_WITH_BODY, "err1"), "c1", "err1");

        assertTrue(result.astViolations().stream()
                        .anyMatch(v -> v.contains("event 'err1'") && v.contains("absorbs-misuse")),
                "the corpus writes error-reporting events deliberately outside the ere, and that "
                        + "is a different finding from an event the automaton forgot: "
                        + result.astViolations());
    }

    @Test
    @DisplayName("a clean specification raises no violation and carries only the standing caveat")
    void test_a_clean_specification_is_clean() {
        M0Result result = examine(M0Fixtures.loop("a", "b"),
                M0Fixtures.facts(1, 2, 2, FAIL_WITH_BODY), "a", "b");

        assertTrue(result.astViolations().isEmpty(), result.astViolations().toString());
        assertTrue(result.silences().isEmpty(), result.silences().toString());
        assertFalse(result.refused());
        assertEquals(List.of(M0Vitality.INDEXING_PROXY_CAVEAT, M0Vitality.NO_INDEX_NOTE),
                result.notes(), "without an android.jar, M0.3 did not run and the result says so "
                        + "rather than letting the absence of a refusal read as 'resolves'");
    }
}
