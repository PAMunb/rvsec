package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Constraint;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import br.unb.cic.rvsec.crysl.core.model.UnrecognizedConstraint;
import br.unb.cic.rvsec.crysl.core.model.UntranslatableConstraint;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * M3 — the census of a rule's {@code CONSTRAINTS} clauses by the idiom that implements each of them
 * in the specification, or by the reason nothing could be said about it.
 *
 * <h2>What the number means, and what it does not</h2>
 *
 * <p>Every clause of the paired rule lands in exactly one of three places: an <strong>idiom</strong>
 * (A, B, C or D), a typed <strong>refusal</strong>, or <strong>absent</strong>. The middle one is
 * why this class is written the way it is. A reader that only knew idiom A would find eleven clauses
 * of the current corpus unreadable and, without the third category, would report all eleven as
 * missing — a limitation of the instrument published as a defect of the subject, in a table that
 * looks like measurement. So an idiom the reader does not recognise emits {@code
 * Unknown{UnrecognizedConstraint}} and is counted in the M3 {@code Unknown} total, never as absent.
 *
 * <p>The count is a census of <em>idioms</em>, not a proof of semantic equality. A clause is
 * "implemented" when the specification contains a site of a known idiom over that clause's names or
 * values; whether the site says exactly what the rule says is a divergence, and adjudicating
 * divergences is the corpus record's job, not this metric's. Each row therefore carries the matched
 * text so a reader can see what was counted.
 *
 * <h2>The denominator, and the rule behind it</h2>
 *
 * <p>The denominator is {@link CountingRule#R1} applied to the paired rule: one clause per {@code ;}
 * inside {@code CONSTRAINTS}, comments removed, {@code &&} not split. It travels with every result
 * because the same corpus answers differently under other rules — splitting {@code &&} gives
 * {@code 125}/{@code 86} over the 49 upstream rules and the 22 paired ones, splitting the sides of
 * {@code =>} gives {@code 145}/{@code 99}, against R1's {@code 119}/{@code 80}. A number without its
 * rule is not a measurement.
 *
 * <h2>The families the abandoned oracle had erased</h2>
 *
 * <p>Three families occur upstream that the generated {@code api30} corpus did not have, and each
 * has a route declared in {@link ClauseFamily} rather than re-derived here: {@code instanceOf} (4
 * occurrences, all in {@code Cipher.crysl}), the {@code alg}/{@code mode}/{@code pad} string parts
 * (26, also all in {@code Cipher.crysl}), and {@code notHardCoded} (4 clauses in 4 rules). Declaring
 * the route is what stops a later reader from doing either of the two wrong things: adding a
 * speculative recogniser for a family nobody measured, or counting the family absent because the
 * reader was never taught to look.
 */
public final class M3Constraints {

    /** {@code type name} pairs of the façade's rendering; the name is what a specification binds. */
    private static final Pattern TYPED_NAME = Pattern.compile(
            "([\\w.$]+(?:\\[\\])?)\\s+([A-Za-z_]\\w*)");

    /** The last value-constraint atom of a clause, which is its consequent. */
    private static final Pattern LAST_VALUE_ATOM = Pattern.compile(
            "(?s)^(\\S+)\\s+(\\S+)\\s+-\\s+(.*)$");

    /**
     * Entry points of the external transformation helper, for
     * {@link ClauseFamily#TRANSFORMATION_PART}, <strong>in precedence order</strong>.
     *
     * <p>Order, and a {@code List} to carry it, because the first match is the site that reaches the
     * published {@code mop_line} column and {@code CipherSpec} matches two of these names. The
     * whole-transformation check comes first — {@code isValid} decides the clause, where {@code alg}
     * decides only one part of it — and the three parts follow in the order the transformation
     * string writes them.
     */
    private static final List<String> TRANSFORMATION_HELPERS =
            List.of("isValid", "alg", "mode", "pad");

    /**
     * Entry points a runtime type test could hide behind, for {@link ClauseFamily#INSTANCE_OF}, in
     * precedence order for the same reason.
     */
    private static final List<String> TYPE_TEST_HELPERS = List.of("isInstance", "instanceOf");

    private M3Constraints() {
    }

    /**
     * Runs the census for one paired specification.
     *
     * @param mop           the lifted specification, for its identity
     * @param rule          the upstream rule it pairs with — the single oracle (D-06)
     * @param specification the specification's own text, which is where idioms C and D live
     * @return the census, with one row per clause of the rule
     */
    public static M3Result census(SpecModel mop, SpecModel rule, SpecificationIdioms specification) {
        Objects.requireNonNull(mop, "mop is mandatory");
        Objects.requireNonNull(rule, "rule is mandatory");
        Objects.requireNonNull(specification, "specification is mandatory");

        List<ClauseVerdict> rows = new ArrayList<>();
        for (Constraint clause : rule.constraints()) {
            rows.add(classify(clause, specification));
        }

        Map<M3Result.Idiom, Integer> byIdiom = new EnumMap<>(M3Result.Idiom.class);
        for (M3Result.Idiom idiom : M3Result.Idiom.values()) {
            byIdiom.put(idiom, 0);
        }
        List<Unknown> refusals = new ArrayList<>();
        int implemented = 0;
        for (ClauseVerdict row : rows) {
            row.idiom().ifPresent(idiom -> byIdiom.merge(idiom, 1, Integer::sum));
            row.refusal().ifPresent(refusals::add);
            if (row.implemented()) {
                implemented++;
            }
        }
        int instrumentCeiling = (int) rows.stream()
                .filter(row -> row.refusal().orElse(null) instanceof UnrecognizedConstraint)
                .count();

        // subjectCeiling is 0 for a paired specification, by definition: the ceiling of the subject
        // counts clauses of rules that have no specification, and this one has one. It is an
        // aggregate over the corpus, not a per-pair quantity - see ceilings(...).
        return new M3Result(specification.file(), ruleNameOf(rule), byIdiom, implemented,
                rows.size(), 0, instrumentCeiling, refusals, CountingRule.R1.toString(), rows);
    }

    /**
     * The two ceilings of a whole run, computed together so that nobody has to remember which is
     * which — and so that no caller is tempted to add them.
     *
     * @param paired         the per-pair results of the run
     * @param unpairedRules  the lifted rules that no specification pairs with
     * @return both ceilings, with the counting rule attached
     */
    public static M3Ceilings ceilings(List<M3Result> paired, List<SpecModel> unpairedRules) {
        Objects.requireNonNull(paired, "paired is mandatory");
        Objects.requireNonNull(unpairedRules, "unpairedRules is mandatory");
        int subject = unpairedRules.stream().mapToInt(rule -> rule.constraints().size()).sum();
        int instrument = paired.stream().mapToInt(M3Result::instrumentCeiling).sum();
        return new M3Ceilings(subject, instrument, CountingRule.R1);
    }

    // ── classification ────────────────────────────────────────────────────────────────────────

    private static ClauseVerdict classify(Constraint clause, SpecificationIdioms specification) {
        String text = clause.text();
        Provenance ruleSite = clause.site();
        ClauseFamily family = ClauseFamily.of(text);

        return switch (family) {
            case NEVER_TYPE_OF, NOT_HARD_CODED, CALL_TO ->
                    refused(text, family, ruleSite,
                            new UntranslatableConstraint(text, family.label(), ruleSite));
            case NO_CALL_TO, OTHER ->
                    refused(text, family, ruleSite, new UnrecognizedConstraint(text, ruleSite));
            case INSTANCE_OF -> instanceOf(text, family, ruleSite, specification);
            case TRANSFORMATION_PART -> transformationPart(text, family, ruleSite, specification);
            case VALUE_LIST -> valueList(text, family, ruleSite, specification);
            case ARITHMETIC -> arithmetic(text, family, ruleSite, specification);
        };
    }

    private static ClauseVerdict instanceOf(String text, ClauseFamily family, Provenance ruleSite,
                                            SpecificationIdioms specification) {
        if (specification.usesInstanceof()) {
            Optional<SpecificationIdioms.Site> site = specification.statementWith("instanceof");
            return implemented(text, family, ruleSite, M3Result.Idiom.B_INLINE_ARITHMETIC,
                    site.orElse(null), specification);
        }
        Optional<SpecificationIdioms.Site> helper = specification.externalHelper(TYPE_TEST_HELPERS);
        if (helper.isPresent()) {
            return implemented(text, family, ruleSite, M3Result.Idiom.D_EXTERNAL_HELPER,
                    helper.get(), specification);
        }
        return absent(text, family, ruleSite);
    }

    private static ClauseVerdict transformationPart(String text, ClauseFamily family,
                                                    Provenance ruleSite,
                                                    SpecificationIdioms specification) {
        Optional<SpecificationIdioms.Site> helper =
                specification.externalHelper(TRANSFORMATION_HELPERS);
        if (helper.isPresent()) {
            return implemented(text, family, ruleSite, M3Result.Idiom.D_EXTERNAL_HELPER,
                    helper.get(), specification);
        }
        Set<String> values = consequentValues(text);
        if (values.isEmpty()) {
            return unreadable(text, family, ruleSite);
        }
        Optional<SpecificationIdioms.Site> list = specification.allowListFor(values);
        if (list.isPresent()) {
            return implemented(text, family, ruleSite, idiomOf(list.get(), M3Result.Idiom.A_ALIAS_TABLE),
                    list.get(), specification);
        }
        return absent(text, family, ruleSite);
    }

    /**
     * A value clause: an allow-list, or an equality against one of its values.
     *
     * <p>Which of the two searches runs first depends on whether the clause is an implication, and
     * that is not a micro-optimisation. A plain clause — {@code algorithm in {"AES", "HmacSHA256"}}
     * — is implemented by a list whose <em>values</em> identify it; the specification names the
     * argument {@code alg} where the rule names it {@code algorithm}, so searching by variable would
     * find nothing. An implication — {@code algorithm in {"EC"} => keysize in {256}} — states its
     * consequent variable, and its values are bare numbers that appear all over a file, so there the
     * variable-aware search is the precise one and the values-only search is the fallback.
     */
    private static ClauseVerdict valueList(String text, ClauseFamily family, Provenance ruleSite,
                                           SpecificationIdioms specification) {
        Set<String> values = consequentValues(text);
        String variable = consequentVariable(text);
        boolean implication = text.contains("implies");

        if (values.isEmpty()) {
            return unreadable(text, family, ruleSite);
        }

        Optional<SpecificationIdioms.Site> first = implication
                ? specification.comparisonWithValue(variable, values)
                : specification.allowListFor(values);
        if (first.isPresent()) {
            return implemented(text, family, ruleSite,
                    idiomOf(first.get(), implication ? M3Result.Idiom.B_INLINE_ARITHMETIC
                            : M3Result.Idiom.A_ALIAS_TABLE), first.get(), specification);
        }
        Optional<SpecificationIdioms.Site> second = implication
                ? specification.allowListFor(values)
                : specification.comparisonWithValue(variable, values);
        if (second.isPresent()) {
            return implemented(text, family, ruleSite,
                    idiomOf(second.get(), implication ? M3Result.Idiom.A_ALIAS_TABLE
                            : M3Result.Idiom.B_INLINE_ARITHMETIC), second.get(), specification);
        }
        return absent(text, family, ruleSite);
    }

    private static ClauseVerdict arithmetic(String text, ClauseFamily family, Provenance ruleSite,
                                            SpecificationIdioms specification) {
        Set<String> names = boundNames(text);
        if (names.isEmpty()) {
            return unreadable(text, family, ruleSite);
        }
        Optional<SpecificationIdioms.Site> comparison = specification.comparisonOver(names);
        if (comparison.isPresent()) {
            return implemented(text, family, ruleSite,
                    idiomOf(comparison.get(), M3Result.Idiom.B_INLINE_ARITHMETIC), comparison.get(),
                    specification);
        }
        return absent(text, family, ruleSite);
    }

    /** A site inside a method the specification declares for itself is idiom C, whatever it does. */
    private static M3Result.Idiom idiomOf(SpecificationIdioms.Site site, M3Result.Idiom otherwise) {
        return site.helper().isPresent() ? M3Result.Idiom.C_LOCAL_HELPER : otherwise;
    }

    private static ClauseVerdict implemented(String text, ClauseFamily family, Provenance ruleSite,
                                             M3Result.Idiom idiom, SpecificationIdioms.Site site,
                                             SpecificationIdioms specification) {
        Optional<String> service = site == null ? Optional.empty()
                : specification.aliasServiceOf(site);
        return new ClauseVerdict(text, family, Optional.of(idiom), service,
                site == null ? Optional.empty() : Optional.of(site.evidence()),
                site == null ? Optional.empty() : Optional.of(site.where()),
                Optional.empty(), ruleSite);
    }

    private static ClauseVerdict refused(String text, ClauseFamily family, Provenance ruleSite,
                                         Unknown refusal) {
        return new ClauseVerdict(text, family, Optional.empty(), Optional.empty(), Optional.empty(),
                Optional.empty(), Optional.of(refusal), ruleSite);
    }

    /**
     * The clause is of a family this reader follows, but nothing could be read out of its rendering
     * to search the specification for — no value atom, or no bound name.
     *
     * <p>This is a refusal and not an absence, and the distinction is the reason
     * {@link UnrecognizedConstraint} exists. Searching for an empty set of values, or for an empty
     * set of names, matches nothing by construction: the search cannot succeed, so its failure says
     * nothing whatever about the specification. Reporting that as {@code absent} publishes a
     * limitation of this reader as a defect of the subject, in a table that looks like measurement —
     * which is the failure the class-level note names. It is counted in the M3 {@code Unknown} total
     * and in the ceiling of the instrument, where a reader can see how far the instrument reaches.
     */
    private static ClauseVerdict unreadable(String text, ClauseFamily family, Provenance ruleSite) {
        return refused(text, family, ruleSite, new UnrecognizedConstraint(text, ruleSite));
    }

    private static ClauseVerdict absent(String text, ClauseFamily family, Provenance ruleSite) {
        return new ClauseVerdict(text, family, Optional.empty(), Optional.empty(), Optional.empty(),
                Optional.empty(), Optional.empty(), ruleSite);
    }

    // ── reading the façade's rendering of a clause ────────────────────────────────────────────

    /**
     * The values the clause finally demands.
     *
     * <p>An implication renders as {@code VC:… - antecedent,impliesVC:… - consequent,} and what a
     * specification implements is the consequent — {@code algorithm in {"AES"} => keysize in {128,
     * 192, 256}} is a clause about key sizes. Taking the last value atom is therefore the right
     * read, and it is right for a plain clause too, which has exactly one.
     */
    static Set<String> consequentValues(String clause) {
        int last = clause.lastIndexOf("VC:");
        if (last < 0) {
            return Set.of();
        }
        Matcher matcher = LAST_VALUE_ATOM.matcher(clause.substring(last + 3));
        if (!matcher.matches()) {
            return Set.of();
        }
        Set<String> values = new LinkedHashSet<>();
        for (String value : matcher.group(3).split(",")) {
            String trimmed = value.strip();
            if (!trimmed.isEmpty()) {
                values.add(trimmed);
            }
        }
        return values;
    }

    /** The name the last value atom constrains, e.g. {@code keysize}. */
    static String consequentVariable(String clause) {
        int last = clause.lastIndexOf("VC:");
        if (last < 0) {
            return "";
        }
        Matcher matcher = LAST_VALUE_ATOM.matcher(clause.substring(last + 3));
        return matcher.matches() ? matcher.group(2) : "";
    }

    /**
     * The names an arithmetic clause is about.
     *
     * <p>The façade renders every operand as {@code type name}, and constants as {@code int 0},
     * which the pattern does not match because {@code 0} is not an identifier. So {@code
     * length(byte[] iv) + int 0 >= int offset + int 0 + int len + int 0} yields exactly
     * {@code {iv, offset, len}} — the three names a specification would have to bind to implement
     * it.
     */
    static Set<String> boundNames(String clause) {
        Set<String> names = new LinkedHashSet<>();
        Matcher matcher = TYPED_NAME.matcher(clause);
        while (matcher.find()) {
            names.add(matcher.group(2));
        }
        return names;
    }

    private static String ruleNameOf(SpecModel rule) {
        String type = rule.type();
        int dot = type.lastIndexOf('.');
        return dot < 0 ? type : type.substring(dot + 1);
    }
}
