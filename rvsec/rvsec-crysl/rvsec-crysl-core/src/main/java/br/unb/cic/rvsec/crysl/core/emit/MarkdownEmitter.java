package br.unb.cic.rvsec.crysl.core.emit;

import br.unb.cic.rvsec.crysl.core.metric.M2Result;
import br.unb.cic.rvsec.crysl.core.model.Normalization;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.Version;
import br.unb.cic.rvsec.crysl.core.model.Witness;
import br.unb.cic.rvsec.crysl.core.model.WitnessStatus;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.StringJoiner;

/**
 * Evidence reports in the shape of {@code data/gh104/evidence/harness/*.md}: an H1, the stamp as
 * the bullet block directly under it, the table, then the prose sections.
 *
 * <p>Two refusals live here, and both are about not letting a rendering say more than the
 * measurement does.
 *
 * <p>The first is INV-CONF-08. A witness with {@code status = ABSTRACT} is a word the product
 * search found; it is not a trace anyone ran. {@code javax.crypto.Cipher} carries a mode state
 * machine that neither the {@code .mop} nor the rule models, so a word this component accepts can
 * throw {@code IllegalStateException} before a monitor ever sees it. Calling such a word a false
 * positive or a false negative asserts a runtime behaviour that was never observed, so the emitter
 * refuses to render the pair rather than printing it with a hedge in the caption.
 *
 * <p>The second is INV-CONF-13. Every M2 verdict is printed under the label {@code M2-decl} and
 * accompanied by the statement that a declared-automaton verdict says nothing about what the
 * generated monitor accuses - measured on {@code KeyGeneratorSpec}, whose {@code ORDER} is
 * equivalent to its {@code ere} and whose generated monitor still accuses order against a program
 * the rule accepts. The normalizations are printed beside every verdict for the same reason:
 * "equivalent under two erasures" and "equivalent" are different claims.
 */
public final class MarkdownEmitter {

    /**
     * The statement INV-CONF-13 requires beside every M2 verdict.
     *
     * <p>A constant rather than a sentence per report, so that no verdict can be published without
     * it.
     */
    public static final String M2_DECL_QUALIFIER =
            "INV-CONF-13: every verdict below is labelled `" + M2Result.LABEL + "` and is a "
                    + "statement about the *declared* automata. It says nothing about what the "
                    + "generated monitor accuses at runtime: `KeyGeneratorSpec` was measured with "
                    + "an `ORDER` equivalent to its `ere` and a monitor that still accuses order "
                    + "against a program the rule accepts.";

    /** What a report may claim about a verdict beyond the verdict itself. */
    public enum Claim {
        /** No runtime claim is attached; the verdict stands alone. */
        NONE,
        /** The specification accuses a program the rule accepts. */
        FALSE_POSITIVE,
        /** The specification accepts a program the rule accuses. */
        FALSE_NEGATIVE;

        boolean isRuntimeClaim() {
            return this != NONE;
        }
    }

    /**
     * One verdict and the claim a report wants to place beside it.
     *
     * @param result the M2 verdict
     * @param claim  what the report asserts about runtime behaviour, {@link Claim#NONE} when it
     *               asserts nothing
     */
    public record VerdictEntry(M2Result result, Claim claim) {

        public VerdictEntry {
            Objects.requireNonNull(result, "VerdictEntry.result is mandatory");
            Objects.requireNonNull(claim, "VerdictEntry.claim is mandatory (use Claim.NONE)");
        }
    }

    private static final List<String> ORDER_COLUMNS = List.of(
            "spec", "rule", "verdict", "witness", "witness status", "normalizations", "claim",
            "refusals");

    private static final List<String> M4_COLUMNS = List.of(
            "file", "predicate", "site verdict", "site disposition", "clause fidelity", "origin");

    /**
     * The M2 order report.
     *
     * @throws IllegalArgumentException when a runtime claim sits beside an abstract witness
     *                                  (INV-CONF-08)
     */
    public String orderReport(String title, Version mopVersion, Version oracleVersion,
                              String countingRule, List<VerdictEntry> entries) {
        Map<String, String> normalizations = new LinkedHashMap<>();
        List<List<String>> rows = new ArrayList<>(entries.size());
        for (VerdictEntry entry : entries) {
            M2Result result = entry.result();
            refuseClaimOnAbstractWitness(result, entry.claim());
            for (Normalization normalization : result.normalizations()) {
                normalizations.putIfAbsent(normalization.id(), normalization.description());
            }
            rows.add(List.of(
                    result.specification(),
                    result.rule(),
                    M2Result.LABEL + ": " + result.verdict(),
                    result.witness().map(MarkdownEmitter::renderWord).orElse("—"),
                    result.witness().map(w -> w.status().name()).orElse("—"),
                    renderNormalizationIds(result.normalizations()),
                    entry.claim().name(),
                    String.valueOf(result.refusals().size())));
        }

        List<String> sections = new ArrayList<>();
        sections.add("## Verdict scope\n\n" + M2_DECL_QUALIFIER + "\n");
        sections.add(renderNormalizationSection(normalizations));
        return new StampedTable(title, mopVersion, oracleVersion, countingRule, ORDER_COLUMNS, rows)
                .markdown(sections);
    }

    /**
     * The M4 report, carrying the site vocabulary and the clause vocabulary side by side.
     *
     * <p>The counting rule is extended with the INV-CONF-15 caveat exactly as the CSV emitter does
     * it, so the two renderings of the same aggregate cannot disagree about how much of it is human
     * judgement.
     */
    public String predicateReport(String title, Version mopVersion, Version oracleVersion,
                                  String countingRule, List<CsvEmitter.M4Row> rows) {
        List<List<String>> cells = new ArrayList<>(rows.size());
        int derived = 0;
        for (CsvEmitter.M4Row row : rows) {
            cells.add(List.of(row.file(), row.predicate(), emptyToDash(row.verdict()),
                    emptyToDash(row.disposition()), row.fidelity().name(), row.origin().csv()));
            if (row.origin() == CsvEmitter.Origin.DERIVED) {
                derived++;
            }
        }
        String rule = countingRule == null || countingRule.isBlank()
                ? countingRule
                : countingRule + " | " + CsvSchema.M4_JUDGEMENT_CAVEAT;
        List<String> sections = List.of(
                "## Origin of the classification\n\n- derived rows: " + derived
                        + "\n- inherited rows: " + (rows.size() - derived) + "\n- "
                        + CsvSchema.M4_JUDGEMENT_CAVEAT + "\n");
        return new StampedTable(title, mopVersion, oracleVersion, rule, M4_COLUMNS, cells)
                .markdown(sections);
    }

    /** Write a rendered report, through the package's only filesystem access. */
    public Path write(Path outputDir, String fileName, String markdown) {
        Path target = outputDir.resolve(fileName);
        StampedTable.write(target, markdown);
        return target;
    }

    private static void refuseClaimOnAbstractWitness(M2Result result, Claim claim) {
        if (!claim.isRuntimeClaim()) {
            return;
        }
        Witness witness = result.witness().orElse(null);
        if (witness == null) {
            throw new IllegalArgumentException("INV-CONF-08: " + claim + " is claimed for "
                    + result.specification() + " with no witness at all; a runtime claim needs a "
                    + "trace, and there is not even a word here");
        }
        if (witness.status() == WitnessStatus.ABSTRACT) {
            throw new IllegalArgumentException("INV-CONF-08: " + claim + " is claimed for "
                    + result.specification() + " beside an ABSTRACT witness. A word accepted by an "
                    + "automaton is not an executable trace, and this one was never run; publish "
                    + "the verdict without the claim, or execute the word and stamp the harness "
                    + "that ran it");
        }
    }

    private static String renderWord(Witness witness) {
        StringJoiner joiner = new StringJoiner(" · ");
        for (Signature signature : witness.word()) {
            joiner.add(signature.declaringType() + "." + signature.name());
        }
        String word = joiner.toString();
        String harness = witness.harness().map(h -> " (harness: " + h + ")").orElse("");
        return (word.isEmpty() ? "ε" : word) + harness;
    }

    private static String renderNormalizationIds(List<Normalization> normalizations) {
        if (normalizations.isEmpty()) {
            return "none";
        }
        StringJoiner joiner = new StringJoiner(", ");
        for (Normalization normalization : normalizations) {
            joiner.add(normalization.id());
        }
        return joiner.toString();
    }

    private static String renderNormalizationSection(Map<String, String> normalizations) {
        StringBuilder section = new StringBuilder("## Normalizations\n\n");
        if (normalizations.isEmpty()) {
            section.append("No transformation was applied to either side before comparison.\n");
            return section.toString();
        }
        for (Map.Entry<String, String> entry : normalizations.entrySet()) {
            section.append("- **").append(entry.getKey()).append("** ")
                    .append(entry.getValue()).append('\n');
        }
        return section.toString();
    }

    private static String emptyToDash(String value) {
        return value == null || value.isBlank() ? "—" : value;
    }
}
