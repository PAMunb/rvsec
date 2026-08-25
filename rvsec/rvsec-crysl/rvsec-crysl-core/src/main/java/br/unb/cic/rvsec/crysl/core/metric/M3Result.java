package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Unknown;
import java.util.Collections;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Census of the rule's {@code CONSTRAINTS} clauses by the idiom that implements each of them in the
 * specification.
 *
 * <p>The two ceilings are separate fields and are never summed. They err in different places: the
 * ceiling of the subject counts clauses of rules that have no specification at all, the ceiling of
 * the instrument counts idioms this reader does not follow. Adding them would produce a single
 * number that describes neither.
 *
 * @param specification the specification
 * @param rule          the rule it was paired with
 * @param byIdiom       how many clauses each idiom accounts for
 * @param implemented   clauses found implemented, the numerator
 * @param denominator   clauses the rule declares under {@code countingRule}
 * @param subjectCeiling clauses in rules with no specification
 * @param instrumentCeiling clauses whose idiom the reader does not follow
 * @param refusals      the typed refusals; an unrecognised idiom lands here, never in "absent"
 * @param countingRule  the rule behind the denominator, e.g. R1
 * @param rows          one row per clause of the rule, in the rule's own order, so that every
 *                      aggregate above is re-derivable and a reader who distrusts the total can
 *                      check it clause by clause; each row also carries whether the check goes
 *                      through the alias table, which is what turns a literally identical
 *                      allow-list into a more permissive one
 */
public record M3Result(String specification, String rule, Map<Idiom, Integer> byIdiom,
                       int implemented, int denominator, int subjectCeiling, int instrumentCeiling,
                       List<Unknown> refusals, String countingRule,
                       List<ClauseVerdict> rows) implements MetricResult {

    /** The idioms a specification uses to implement a CrySL constraint. */
    public enum Idiom {
        /** {@code Arrays.asList(...)} plus {@code ConscryptAliasTable.matches(...)}. */
        A_ALIAS_TABLE,
        /** Direct arithmetic in a {@code condition(...)} or event body over {@code args()}. */
        B_INLINE_ARITHMETIC,
        /** A helper method declared inside the specification. */
        C_LOCAL_HELPER,
        /** An external helper class in {@code rvsec-core}. */
        D_EXTERNAL_HELPER
    }

    public M3Result {
        Objects.requireNonNull(specification, "M3Result.specification is mandatory");
        Objects.requireNonNull(rule, "M3Result.rule is mandatory");
        Objects.requireNonNull(countingRule, "M3Result.countingRule is mandatory (INV-CONF-02)");
        // An EnumMap and not Map.copyOf: this map is serialized straight into the JSON report, so
        // its iteration order is published. Map.copyOf's order is salted per JVM, and the same
        // corpus therefore emitted the four idiom keys in a different order on every run - a
        // published table whose content moves while its stamp does not (INV-CONF-02). EnumMap
        // iterates in declaration order, which is a rule a reader can check.
        byIdiom = Collections.unmodifiableMap(byIdiom.isEmpty()
                ? new EnumMap<>(Idiom.class) : new EnumMap<>(byIdiom));
        refusals = List.copyOf(refusals);
        rows = List.copyOf(rows);
    }

    @Override
    public String metric() {
        return "M3";
    }

    /**
     * Clauses that are genuinely not implemented — neither an idiom nor a refusal.
     *
     * <p>Derived rather than stored, so that it cannot drift from the rows and cannot quietly
     * absorb a refusal. "Could not read" is never added to "is not there".
     */
    public int absent() {
        return (int) rows.stream().filter(ClauseVerdict::absent).count();
    }

    /** Clauses whose check is widened by the {@code ConscryptAliasTable}. */
    public int widenedByAliasTable() {
        return (int) rows.stream().filter(ClauseVerdict::widenedByAliasTable).count();
    }
}
