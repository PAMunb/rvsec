package br.unb.cic.rvsec.crysl.core.calibration;

import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * What the gate found, in full: every target's outcome, the two stamps of every corpus side by
 * side, what may still be published, and the figures that reproduce under no rule at all.
 *
 * <h2>The stamp table is two columns and that is the point</h2>
 *
 * <p>Each row names a corpus, the stamp <em>the route</em> was taken at and the stamp <em>this
 * run</em> read it at. One column for the whole run would hide precisely the case that matters and
 * that actually happened during this change: the {@code rvsec} checkout moved four times while
 * {@code rvsec-cognicrypt} did not move at all. When the two differ, that is the first thing to
 * check about a disagreement, and it must not require archaeology (task 12.5, D-17).
 *
 * <h2>Publication is decided per metric</h2>
 *
 * <p>{@link #publishes(PublishedMetric)} is {@code false} only for a metric some target of that
 * metric contradicted. There is no cascade: a mismatch on the M3 denominator says nothing about M1
 * and must not silence it (task 12.4).
 *
 * @param outcomes      one per target, in the order the targets were declared
 * @param runStamps     repository to the stamp <strong>this run</strong> read it at
 * @param unreproducible figures no written rule reproduces, published with the component's own
 *                      value and rule (task 12.10)
 */
public record CalibrationReport(List<TargetOutcome> outcomes, Map<String, SourceStamp> runStamps,
                                List<UnreproducibleFigure> unreproducible) {

    public CalibrationReport {
        Objects.requireNonNull(outcomes, "CalibrationReport.outcomes is mandatory");
        outcomes = List.copyOf(outcomes);
        runStamps = Map.copyOf(runStamps);
        unreproducible = List.copyOf(unreproducible);
    }

    /** The disagreements, each carrying both measurements, both rules and the named items. */
    public List<TargetOutcome> mismatches() {
        return outcomes.stream().filter(TargetOutcome::suppresses).toList();
    }

    /** How many of the outcomes are calibration targets rather than self-consistency checks. */
    public int calibrationTargets() {
        return (int) outcomes.stream()
                .filter(outcome -> outcome.target().routeClass().calibrates())
                .count();
    }

    /** How many outcomes are labelled self-consistency checks, which cannot fail (D-18). */
    public int selfConsistencyChecks() {
        return outcomes.size() - calibrationTargets();
    }

    /** Whether the run may publish that metric. */
    public boolean publishes(PublishedMetric metric) {
        return outcomes.stream()
                .noneMatch(outcome -> outcome.suppresses() && outcome.target().blocks() == metric);
    }

    /** Every metric some target vouches for, and whether it publishes. */
    public Map<PublishedMetric, Boolean> publication() {
        Map<PublishedMetric, Boolean> decision = new EnumMap<>(PublishedMetric.class);
        for (TargetOutcome outcome : outcomes) {
            PublishedMetric metric = outcome.target().blocks();
            decision.merge(metric, !outcome.suppresses(), Boolean::logicalAnd);
        }
        return decision;
    }

    /** Whether every calibration target was reproduced. */
    public boolean reproduced() {
        return mismatches().isEmpty();
    }

    /** The per-metric publication decision, with the target that suppressed each refusal named. */
    public String publicationSummary() {
        StringBuilder text = new StringBuilder("publication, per metric (task 12.4 — a mismatch "
                + "stops the affected metric and nothing else):\n");
        for (Map.Entry<PublishedMetric, Boolean> entry : publication().entrySet()) {
            text.append("  ").append(entry.getKey()).append(": ");
            if (Boolean.TRUE.equals(entry.getValue())) {
                text.append("publishes\n");
            } else {
                List<String> blockers = outcomes.stream()
                        .filter(outcome -> outcome.suppresses()
                                && outcome.target().blocks() == entry.getKey())
                        .map(outcome -> outcome.target().id())
                        .toList();
                text.append("SUPPRESSED by ").append(String.join(", ", blockers)).append('\n');
            }
        }
        return text.toString();
    }

    /**
     * The stamp of each corpus as the route took it and as this run read it, side by side.
     *
     * <p>A corpus with no run stamp prints {@code (not supplied)} rather than being omitted: the
     * absence of a stamp is itself something a reader has to see.
     */
    public String stampTable() {
        StringBuilder text = new StringBuilder("stamps, per corpus (D-17 — never one scalar per "
                + "run):\n");
        Map<String, String[]> rows = new LinkedHashMap<>();
        for (TargetOutcome outcome : outcomes) {
            CalibrationTarget target = outcome.target();
            SourceStamp route = target.stamp();
            SourceStamp run = runStamps.get(route.repository());
            rows.putIfAbsent(target.corpus() + " (" + route.repository() + ")", new String[] {
                    route.commit(), run == null ? "(not supplied)" : run.commit()});
        }
        for (Map.Entry<String, String[]> row : rows.entrySet()) {
            String routeCommit = row.getValue()[0];
            String runCommit = row.getValue()[1];
            text.append("  ").append(row.getKey())
                    .append(": route at ").append(routeCommit)
                    .append(", this run at ").append(runCommit)
                    .append(routeCommit.equals(runCommit) ? "" : "   <- they differ")
                    .append('\n');
        }
        return text.toString();
    }

    /** The whole report as text, in the order a reader meets it. */
    public String render() {
        StringBuilder text = new StringBuilder();
        text.append("calibration: ").append(calibrationTargets()).append(" targets, ")
                .append(selfConsistencyChecks()).append(" labelled self-consistency checks; ")
                .append(mismatches().size()).append(" mismatch(es)\n\n");
        text.append(stampTable()).append('\n');
        List<String> blocks = new ArrayList<>();
        outcomes.forEach(outcome -> blocks.add(outcome.describe()));
        text.append(String.join("\n", blocks)).append('\n');
        text.append(publicationSummary());
        if (!unreproducible.isEmpty()) {
            text.append("\nfigures that reproduce under no written rule (task 12.10):\n");
            unreproducible.forEach(figure -> text.append(figure.describe()));
        }
        return text.toString();
    }
}
