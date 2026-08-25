package br.unb.cic.rvsec.crysl.core.calibration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * What the gate does with an agreement, a disagreement and a target that cannot fail.
 *
 * <p>These read no corpus. They are about the gate's semantics — what a mismatch carries, what it
 * suppresses and what it leaves alone — and those are the properties a reader has to be able to
 * trust before any number matters. {@code CalibrationGateTest} in the {@code -crysl} module is the
 * other half: the eight real targets against the component's real measurements.
 */
class CalibrationGateSemanticsTest {

    private static final SourceStamp ROUTE_STAMP =
            new SourceStamp("rvsec", "5fbe8173", Instant.EPOCH);
    private static final Map<String, SourceStamp> RUN_STAMPS =
            Map.of("rvsec", new SourceStamp("rvsec", "6192b57a", Instant.EPOCH));

    // ── 12.1 / 12.1-bis: the targets as data, and every route foreign to the component ────────

    @Test
    @DisplayName("12.1: the eight targets each carry a value, a counting rule, a route and a stamp")
    void test_every_target_is_complete() {
        List<CalibrationTarget> targets = CalibrationTargets.eight();

        assertEquals(8, targets.size(), "the change declares eight targets");
        Set<String> ids = new HashSet<>();
        for (CalibrationTarget target : targets) {
            assertTrue(ids.add(target.id()), target.id() + " is declared twice");
            assertFalse(target.value().isBlank(), target.id() + " has no value");
            assertFalse(target.countingRule().isBlank(),
                    target.id() + " has no counting rule, which makes it a number and not a "
                            + "target");
            assertFalse(target.route().isBlank(), target.id() + " does not name its route");
            assertFalse(target.stamp().commit().isBlank(),
                    target.id() + " does not name the commit its own route was taken at (D-17)");
        }
    }

    @Test
    @DisplayName("12.1-bis: no target's route is a rule the component implements (RISK-006, D-18)")
    void test_no_target_restates_the_component() {
        for (CalibrationTarget target : CalibrationTargets.eight()) {
            assertTrue(target.routeClass().calibrates(),
                    target.id() + " is routed through " + target.routeClass() + ". A target whose "
                            + "route is a rule the component implements cannot fail, so it is not "
                            + "a calibration: it must be published as a labelled self-consistency "
                            + "check instead (D-18). Two of these eight were written that way "
                            + "once — pairing 'by name', and the MapOfMonitor census taken from "
                            + "the AST proxy — and the gate built on them could not have failed");
        }
    }

    @Test
    @DisplayName("12.1: the two stamps are per repository, and the .mop side is not the oracle's")
    void test_stamps_are_per_repository() {
        Map<String, Set<String>> commitsByRepository = new LinkedHashMap<>();
        for (CalibrationTarget target : CalibrationTargets.eight()) {
            commitsByRepository
                    .computeIfAbsent(target.stamp().repository(), key -> new HashSet<>())
                    .add(target.stamp().commit());
        }

        assertEquals(Set.of("rvsec", "rvsec-cognicrypt"), commitsByRepository.keySet(),
                "the input spans two git repositories, and a target says which one it came from");
        assertEquals(Set.of(CalibrationTargets.RVSEC_PINNED), commitsByRepository.get("rvsec"));
        assertEquals(Set.of(CalibrationTargets.ORACLE_PINNED),
                commitsByRepository.get("rvsec-cognicrypt"),
                "the oracle moves on its own clock; stamping it with the rvsec commit would "
                        + "attribute an upstream-derived number to a repository that did not "
                        + "produce it (D-17)");
    }

    @Test
    @DisplayName("a target constructed without a counting rule is refused at construction")
    void test_a_target_without_a_counting_rule_is_refused() {
        IllegalArgumentException refused = assertThrows(IllegalArgumentException.class,
                () -> new CalibrationTarget("T0", "something", "1 of 2", List.of(), "  ",
                        RouteClass.INDEPENDENT_PROBE, "somewhere", "jca_android", ROUTE_STAMP,
                        PublishedMetric.M0, ""));
        assertTrue(refused.getMessage().contains("counting rule"), refused.getMessage());
    }

    // ── 12.3 / 12.4 / 12.7: what a disagreement carries and what it stops ─────────────────────

    @Test
    @DisplayName("12.7 test_inv_conf_14_mismatch_reported: both values, both rules, the named items")
    void test_inv_conf_14_mismatch_reported() {
        // One target is given a deliberately wrong value: five specifications without MapOfMonitor
        // where the component measures four, the fifth being KeyStoreSpec. The other three targets
        // agree, and they must survive.
        List<CalibrationTarget> targets = List.of(
                target("T-indexing", "5 of 24",
                        List.of("CipherInputStreamSpec", "CipherOutputStreamSpec",
                                "HMACParameterSpecSpec", "KeyStoreSpec", "RandomStringPassword"),
                        "the regenerated monitor's MapOfMonitor fields", PublishedMetric.M0),
                target("T-lift", "215 files, 215 ok, 0 fail", List.of(), "Census.java",
                        PublishedMetric.MOP_LIFT),
                target("T-pairing", "22 of 24", List.of("IvChainJunction", "RandomStringPassword"),
                        "the alphabet map's declared skips", PublishedMetric.PAIRING),
                target("T-denominator", "80 of 119", List.of(), "the raw-text R1 census",
                        PublishedMetric.M3));

        Map<String, Measurement> measured = new LinkedHashMap<>();
        measured.put("T-indexing", new Measurement("T-indexing", "4 of 24",
                List.of("CipherInputStreamSpec", "CipherOutputStreamSpec", "HMACParameterSpecSpec",
                        "RandomStringPassword"),
                "M0.1's AST proxy: at least one declared parameter and at least one event binding "
                        + "it"));
        measured.put("T-lift", Measurement.of("T-lift", "215 files, 215 ok, 0 fail",
                "MopLifter.read over every *.mop of the five corpora"));
        measured.put("T-pairing", new Measurement("T-pairing", "22 of 24",
                List.of("IvChainJunction", "RandomStringPassword"), "SpecRulePairing"));
        measured.put("T-denominator", Measurement.of("T-denominator", "80 of 119",
                "one clause per ISLConstraint of the CrySL facade"));

        CalibrationMismatch raised = assertThrows(CalibrationMismatch.class,
                () -> CalibrationGate.verify(targets, measured, RUN_STAMPS, List.of()));

        assertEquals(1, raised.mismatches().size(), "one target disagreed, not four");
        TargetOutcome outcome = raised.mismatches().get(0);
        assertEquals("T-indexing", outcome.target().id());
        assertEquals(List.of("KeyStoreSpec"), outcome.onlyInRoute(),
                "'4 versus 5' is unactionable; 'the fifth is KeyStoreSpec' is a finding someone "
                        + "can adjudicate");
        assertTrue(outcome.onlyInComponent().isEmpty());

        String message = raised.getMessage();
        assertTrue(message.contains("5 of 24") && message.contains("4 of 24"),
                "both measurements travel with the exception: " + message);
        assertTrue(message.contains("the regenerated monitor's MapOfMonitor fields")
                        && message.contains("AST proxy"),
                "both counting rules travel with it too, which is what makes the disagreement "
                        + "adjudicable rather than merely visible: " + message);
        assertTrue(message.contains("KeyStoreSpec"),
                "and the differing item is named individually: " + message);

        // 12.4: the affected metric and nothing else.
        CalibrationReport report = raised.report();
        assertFalse(report.publishes(PublishedMetric.M0), "the metric the target vouches for");
        assertTrue(report.publishes(PublishedMetric.MOP_LIFT));
        assertTrue(report.publishes(PublishedMetric.PAIRING));
        assertTrue(report.publishes(PublishedMetric.M3),
                "one wrong metric must not suppress the right ones: a gate that failed whole runs "
                        + "would teach its users to switch it off");
        assertTrue(report.publicationSummary().contains("SUPPRESSED by T-indexing"),
                "and the refusal names the target that caused it: "
                        + report.publicationSummary());
    }

    @Test
    @DisplayName("12.3: equal counts over different items are a mismatch, not a pass")
    void test_equal_counts_over_different_items_disagree() {
        List<CalibrationTarget> targets = List.of(
                target("T-indexing", "5 of 24", List.of("A", "B", "C", "D", "KeyStoreSpec"),
                        "the regenerated monitor", PublishedMetric.M0));
        Map<String, Measurement> measured = Map.of("T-indexing",
                new Measurement("T-indexing", "5 of 24", List.of("A", "B", "C", "D", "MacSpec"),
                        "the AST proxy"));

        CalibrationReport report =
                CalibrationGate.check(targets, measured, RUN_STAMPS, List.of());

        assertEquals(1, report.mismatches().size(),
                "the two counts coincide over different specifications, and a gate that only "
                        + "compared totals would call that a pass");
        assertEquals(List.of("KeyStoreSpec"), report.mismatches().get(0).onlyInRoute());
        assertEquals(List.of("MacSpec"), report.mismatches().get(0).onlyInComponent());
    }

    @Test
    @DisplayName("a target nothing measured is a mismatch, never a silent pass")
    void test_an_unmeasured_target_is_a_mismatch() {
        List<CalibrationTarget> targets = List.of(
                target("T-lift", "215 files, 215 ok, 0 fail", List.of(), "Census.java",
                        PublishedMetric.MOP_LIFT));

        CalibrationReport report = CalibrationGate.check(targets, Map.of(), RUN_STAMPS, List.of());

        assertEquals(1, report.mismatches().size());
        assertTrue(report.mismatches().get(0).measurement().value().contains("not measured"),
                "the report says the run never answered, rather than reporting nothing at all");
        assertFalse(report.publishes(PublishedMetric.MOP_LIFT));
    }

    // ── D-18: the route that is the component's own rule ──────────────────────────────────────

    @Test
    @DisplayName("D-18: a same-algorithm route is labelled a self-consistency check and cannot fail")
    void test_a_same_algorithm_route_is_not_a_calibration_target() {
        CalibrationTarget restated = new CalibrationTarget("T-restated",
                "pairing, re-run through the component's own rule", "22 of 24", List.of(),
                "the component's declared-type pairing, applied again",
                RouteClass.SAME_ALGORITHM_RESTATEMENT, "SpecRulePairing", "jca_android",
                ROUTE_STAMP, PublishedMetric.PAIRING, "");
        Map<String, Measurement> measured = Map.of("T-restated",
                Measurement.of("T-restated", "23 of 24", "SpecRulePairing"));

        CalibrationReport report =
                CalibrationGate.check(List.of(restated), measured, RUN_STAMPS, List.of());

        assertEquals(TargetOutcome.Verdict.SELF_CONSISTENCY_CHECK,
                report.outcomes().get(0).verdict(),
                "the route restates the instrument, so the comparison says nothing about it");
        assertEquals(0, report.calibrationTargets(),
                "and it is not counted among the calibration targets, so a report cannot claim "
                        + "more external validation than it has");
        assertEquals(1, report.selfConsistencyChecks());
        assertTrue(report.reproduced(), "it cannot fail the gate, because it cannot fail");
        assertTrue(report.publishes(PublishedMetric.PAIRING));
    }

    // ── 12.5: the two stamps side by side ─────────────────────────────────────────────────────

    @Test
    @DisplayName("12.5: the report prints the route's stamp and the run's, per corpus")
    void test_the_stamp_table_shows_both_columns() {
        List<CalibrationTarget> targets = List.of(
                target("T-lift", "215 files, 215 ok, 0 fail", List.of(), "Census.java",
                        PublishedMetric.MOP_LIFT));
        Map<String, Measurement> measured = Map.of("T-lift",
                Measurement.of("T-lift", "215 files, 215 ok, 0 fail", "MopLifter.read"));

        String table = CalibrationGate.check(targets, measured, RUN_STAMPS, List.of()).stampTable();

        assertTrue(table.contains("5fbe8173") && table.contains("6192b57a"),
                "both stamps, not one scalar for the run: " + table);
        assertTrue(table.contains("they differ"),
                "and when they differ the report says so, because that is the first thing to "
                        + "check about a disagreement: " + table);
    }

    // ── 12.10: the figures that reproduce under no rule ───────────────────────────────────────

    @Test
    @DisplayName("12.10: an unreproducible figure is recorded with the component's value and rule")
    void test_unreproducible_figures_are_published_with_their_rule() {
        List<UnreproducibleFigure> figures = CalibrationTargets.unreproducibleFigures();

        assertEquals(2, figures.size(), "the two the change's own artifacts still state");
        for (UnreproducibleFigure figure : figures) {
            assertFalse(figure.componentValue().isBlank(),
                    figure.figure() + " is recorded without the component's own value, which "
                            + "leaves a reader with a hole where a number was");
            assertFalse(figure.componentRule().isBlank(),
                    figure.figure() + " is recorded without the rule the component answered under");
            assertTrue(figure.whatWasTried().length() > 40,
                    "what was tried has to be legible six months later, or the figure will be "
                            + "chased again");
        }
        assertTrue(figures.get(0).figure().contains("101"),
                "101 is not merely unreproduced but impossible: splitting a clause can only raise "
                        + "a count, and 101 is below the unsplit 119");
    }

    // ── fixtures ──────────────────────────────────────────────────────────────────────────────

    private static CalibrationTarget target(String id, String value, List<String> items,
                                            String route, PublishedMetric blocks) {
        List<String> copy = new ArrayList<>(items);
        return new CalibrationTarget(id, id, value, copy, route + " (counting rule)",
                RouteClass.INDEPENDENT_PROBE, route, "jca_android", ROUTE_STAMP, blocks, "");
    }
}
