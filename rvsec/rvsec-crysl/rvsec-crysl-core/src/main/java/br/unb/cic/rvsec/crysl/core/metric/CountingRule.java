package br.unb.cic.rvsec.crysl.core.metric;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * The rule behind a denominator, written down so that it travels with the number.
 *
 * <p>A count of CrySL clauses is not a measurement until the rule that produced it is stated
 * beside it. The same 49 upstream rules yield different totals depending on what is taken to be
 * one clause, and the differences are not marginal: measured over
 * {@code rvsec-cognicrypt/CrySL-Rules}, {@link #R1} answers {@code 119} clauses across all 49
 * rules and {@code 80} across the 22 that have a {@code .mop} specification, while splitting the
 * top-level {@code &&} conjunctions answers {@code 125}/{@code 86} and splitting the two sides of
 * every {@code =>} answers {@code 145}/{@code 99}. A publication that prints one of those numbers
 * without its rule has printed an ambiguity.
 *
 * <p>Those two alternative totals are measured here and each agrees with an independent census of
 * the same corpus: the 6 top-level {@code &&} of {@code Cipher.crysl} take {@code 119} to
 * {@code 125}, and the 26 implications across 6 rules take it to {@code 145}. A reader coming from
 * the change's planning artifacts will find the pairs {@code 101}/{@code 71} and {@code 117}/{@code
 * 87} quoted there for the same two alternatives; neither is reproducible from this corpus under any
 * reading, and neither can be, because splitting a clause can only raise a count and {@code 101} is
 * below {@code 119}. They are recorded as unreproducible rather than chased — the rule they came
 * from was never written down, and the response to that is to publish this component's value with
 * its rule, not to invent one that agrees.
 *
 * <p>{@link #R1} is therefore not only documented here, it is <em>executable</em>: {@link
 * #countClauses(String)} applies it to the text of a rule file. That matters because the metric's
 * own denominator comes from the CrySL façade — one {@code ISLConstraint} per clause — and a
 * counting rule that could only be checked by reading a comment could not be checked at all. The
 * two routes agree on every upstream rule that parses; where they differ, the difference is a
 * finding about the rule, not a licence to pick the more convenient total.
 *
 * @param id        the rule's short name, printed beside every count
 * @param statement the rule in words, complete enough to be re-applied by hand
 */
public record CountingRule(String id, String statement) {

    /**
     * One clause per {@code ;} inside {@code CONSTRAINTS}, comments removed, {@code &&}
     * conjunctions <strong>not</strong> split.
     *
     * <p>Not splitting {@code &&} is the decision that makes the rule stable. A CrySL author
     * writes {@code alg(t) in {"RSA"} && mode(t) in {"ECB"} => pad(t) in {...}} as one obligation
     * with a compound antecedent; counting it as two would make the denominator a function of how
     * the antecedent happened to be phrased rather than of how many obligations the rule states.
     */
    public static final CountingRule R1 = new CountingRule("R1",
            "one clause per ';' inside CONSTRAINTS, comments removed, "
                    + "'&&' conjunctions not split");

    /** The section keywords of the CrySL grammar, which delimit {@code CONSTRAINTS}. */
    private static final Set<String> SECTIONS = Set.of("SPEC", "OBJECTS", "EVENTS", "ORDER",
            "CONSTRAINTS", "REQUIRES", "ENSURES", "NEGATES", "FORBIDDEN");

    public CountingRule {
        Objects.requireNonNull(id, "CountingRule.id is mandatory");
        Objects.requireNonNull(statement, "CountingRule.statement is mandatory");
    }

    /**
     * Applies R1 to the text of one {@code .crysl} file.
     *
     * <p>Comments are removed before anything is counted, because a comment is not countable and
     * must not enter a metric: a {@code ;} inside {@code // …} would otherwise add a clause the
     * rule does not state.
     *
     * @param cryslSource the rule file as it stands on disk (INV-CONF-12: read, never written)
     * @return how many clauses R1 sees in its {@code CONSTRAINTS} section, {@code 0} when it has
     *         none
     */
    public static int countClauses(String cryslSource) {
        Objects.requireNonNull(cryslSource, "cryslSource is mandatory");
        String section = constraintsSection(cryslSource);
        int clauses = 0;
        for (int i = 0; i < section.length(); i++) {
            if (section.charAt(i) == ';') {
                clauses++;
            }
        }
        return clauses;
    }

    /**
     * The text of the {@code CONSTRAINTS} section, with comments already stripped.
     *
     * <p>A section header is a keyword at the start of a line with no leading whitespace; the CrySL
     * grammar indents everything else. Reading the section this way rather than with one regular
     * expression over the whole file is what keeps a {@code REQUIRES} clause that mentions a
     * constraint out of the count.
     */
    static String constraintsSection(String cryslSource) {
        String withoutBlockComments = cryslSource.replaceAll("(?s)/\\*.*?\\*/", "");
        List<String> collected = new ArrayList<>();
        boolean inside = false;
        for (String rawLine : withoutBlockComments.split("\r?\n", -1)) {
            String line = rawLine.replaceAll("//.*", "");
            String head = line.strip().split("\\s+", 2)[0];
            boolean isHeader = !line.isEmpty() && !Character.isWhitespace(line.charAt(0))
                    && SECTIONS.contains(head);
            if (isHeader) {
                inside = "CONSTRAINTS".equals(head);
                continue;
            }
            if (inside) {
                collected.add(line);
            }
        }
        return String.join("\n", collected);
    }

    @Override
    public String toString() {
        return id + ": " + statement;
    }
}
